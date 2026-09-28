# Configuration - Journal Server

Ansible playbook that serves a website, Gemini capsule, and cgit
instance, each reachable over the clearnet, a Tor onion address, and an
I2P destination.

```
                 ┌──────────── nftables: 22, 80, 443, 1965 ───┐
   clearnet ───► │  caddy (web, cgit)   ssh   agate (gemini)  │
   tor      ───► │   :80 :443           :22      :1965        │
   i2p      ───► │                                            │
                 └────────────────────────────────────────────┘
```

## Layout

| Path | Purpose |
| --- | --- |
| `site.yml` | installs sudo and Python, then the main play: asserts inputs, resolves addresses, runs the roles |
| `inventory/group_vars/all/main.yml` | **every** deployment-specific value |
| `vars/policy.yml` | invariants, not user-modifiable settings |
| `filter_plugins/tor.py` | derives a `.onion` address from a v3 service secret key |
| `filter_plugins/i2p.py` | derives a `.b32.i2p` address from a destination key |
| `roles/common` | packages, admin account, unattended upgrades |
| `roles/firewall` | nftables, default-deny inbound |
| `roles/ssh_hardening` | PQ-only key exchange, key-only auth |
| `roles/tor` | the onion service, from a user-supplied key |
| `roles/i2p` | i2pd server tunnels from user-supplied keys |
| `roles/caddy` | global config, TLS policy, shared snippets |
| `roles/website` | content + vhosts (clearnet, onion, I2P) |
| `roles/gemini` | Agate, certificates, capsule content |
| `roles/cgit` | repositories, fcgiwrap under its own user, vhosts |

## Requirements

* **Controller:** `ansible-core` ≥ 2.15, then `ansible-galaxy install -r requirements.yml`.
  Also `pip install libnacl` (and libsodium itself, e.g. `apt install
  libsodium23`) — the `onion_address` filter derives the `.onion` from the
  service secret key with libsodium's Ed25519 scalar multiplication.
  `rsync` too, which pushes the site and capsule content.
* **Target:** Debian 12/13 with Python 3.
* **OpenSSH ≥ 8.5** on the target for `sntrup761x25519-sha512@openssh.com`,
  or **≥ 9.9** for `mlkem768x25519-sha256`. The play probes `ssh -Q kex` and
  refuses to continue if neither is available, rather than silently falling
  back to a classical key exchange.
* **Caddy ≥ 2.10** for the `x25519mlkem768` curve. Installed from the
  official Caddy repository by the role, so this is satisfied by default.
* Your **SSH client** also needs one of those algorithms — check with
  `ssh -Q kex | grep -E 'mlkem|sntrup'` before you lock yourself out.

## Material you supply at deploy time

`secrets/` is the only place the playbook reads keys from.

```
secrets/
├── onion/hs_ed25519_secret_key
├── i2p/{web.dat,gemini.dat,cgit.dat}
└── gemini/  # optional; self-signed certs are generated otherwise
```

**One onion.** The website, capsule and cgit share a single onion:
the capsule on port 1965, and cgit at `<cgit_onion_subdomain>.<onion>`.
I2P has no equivalent — a `.b32.i2p` address takes no subdomains — so
each service keeps its own I2P destination.

**Onion keys.** Only `hs_ed25519_secret_key` is needed: the playbook
computes the `.onion` address from it on the controller
(`filter_plugins/tor.py`). Either let a local Tor generate a service
directory, or use [`mkp224o`](https://github.com/cathugger/mkp224o) for
a vanity prefix:

```sh
mkp224o -d secrets -n 1 mysite
mv secrets/mysiteXXXX.onion secrets/onion
```

Any `hs_ed25519_public_key` and `hostname` already on the host are
deleted whenever the secret key changes, so swapping a key does not
leave tor with a public key that contradicts its secret one.

**I2P destination keys.** `i2pd-tools keygen -o secrets/i2p/web.dat`, or
let i2pd create them and copy `/var/lib/i2pd/*.dat`. The playbook derives
the `.b32.i2p` address from the key on the controller.

**Gemini certificates.** Optional. List them per hostname in
`gemini_certificates`. Any hostname not listed gets a 10-year
self-signed Ed25519 certificate generated on the host. Gemini is
trust-on-first-use, so self-signed is the norm — but keep the generated
keys if you rebuild, or clients will warn about the change.

Ansible owns the PEM material in `/etc/agate/pem`; Agate reads the DER
beside it at `/etc/agate/certs/<hostname>/{cert,key}.der`. Each name
gets its own key and certificate on purpose: clients check the name
against the certificate, so with separate certificates, replacing one
doesn't break the certificates clients have already saved for the
others. (This is not about keeping the transports unlinked.)

## Deploying

```sh
ansible-galaxy install -r requirements.yml

# edit inventory/hosts.yml and inventory/group_vars/all/main.yml, then:
ansible-playbook site.yml -e '{"admin_authorized_keys":["ssh-ed25519 AAAA... you@laptop"]}'
```

After the first run, switch the inventory to the hardened account:

```yaml
ansible_user: deploy
ansible_port: 22  # or whatever you set ssh_port to
```

Useful tag selections: `--tags web`, `--tags gemini`, `--tags cgit`,
`--tags firewall,ssh`.

## Publishing repositories

```yaml
cgit_repositories:
  - name: dotfiles
    description: "shell, editor and wm configuration"
    owner: alice
    section: personal
  - name: upstream-mirror
    description: "read-only mirror"
    source: "https://github.com/someone/project.git"
```

An entry with `source` is mirrored and re-fetched on every run; an entry
without one is created as an empty bare repository you push to over SSH
(`git remote add origin deploy@host:/srv/git/dotfiles.git` — the `cgit`
user owns the repositories, so either push as a member of that group or
run `git push` as `cgit`).

Clones are served by `git-http-backend` (smart HTTP) over all three
transports; `git-receive-pack` is never enabled, so HTTP access is read-only.

## Verifying

```sh
# post-quantum key exchange only
ssh -o KexAlgorithms=mlkem768x25519-sha256 deploy@host true
ssh -o KexAlgorithms=curve25519-sha256 deploy@host true  # must fail

# TLS 1.3 + hybrid PQ group (OpenSSL 3.5+ / a recent curl)
openssl s_client -connect example.com:443 -tls1_3 -groups X25519MLKEM768 </dev/null | grep -i 'negotiated\|protocol'

# the firewall really is default-deny
nmap -Pn -p- example.com

# hidden transports
torsocks curl -I http://<onion>/
curl -I http://<b32>.b32.i2p/ --proxy http://127.0.0.1:4444  # via a local i2pd
git clone https://git.example.com/dotfiles.git
```