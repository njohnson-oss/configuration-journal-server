# Configuration - Journal Server

[![Lint](https://github.com/njohnson-oss/configuration-journal-server/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/njohnson-oss/configuration-journal-server/actions/workflows/lint.yml)

Ansible playbook that serves a website, Gemini capsule, and cgit
instance, each reachable over the clearnet, a Tor onion address, and an
I2P destination.

**Note:** Preventing correlation of the clearnet transport with the
hidden transports is not a design goal. The hidden transports are made
available to offer clients anonymous means to connect, not to hide the
server's IP.

```
  clearnet                     Tor network         I2P network
     │ TCP 22, 80, 443, 1965         ▲                 ▲   │ TCP and UDP
     │ UDP 443 (QUIC)                │                 │   │ i2p_router_port,
     │                               │    outbound     │   │ if set
 ┌───▼──────── nftables ─────────────┼─────────────────┼───▼─────────┐
 │  sshd   :22                      tor              i2pd            │
 │  caddy  :80 :443   web, cgit      │                 │             │
 │  agate  :1965      gemini         │                 │             │
 │    ▲                              │                 │             │
 │    └─────── over 127.0.0.1 ───────┴─────────────────┘             │
 └───────────────────────────────────────────────────────────────────┘
```

## Layout

| Path | Purpose |
| --- | --- |
| `site.yml` | installs sudo and Python, then runs the roles in order |
| `inventory/group_vars/all/main.yml` | **every** deployment-specific value |
| `filter_plugins/tor.py` | derives a `.onion` address from a v3 service secret key |
| `filter_plugins/i2p.py` | derives a `.b32.i2p` address from a destination key |
| `roles/addresses` | the names the server publishes: checks the onion and I2P keys exist and derives the addresses from them |
| `roles/common` | what every role builds on: refuses anything but Debian 12 and 13, holds the invariants (not user-modifiable settings) and SSH access, installs base packages, creates the admin account, enables unattended upgrades |
| `roles/firewall` | nftables, default-deny inbound |
| `roles/ssh_hardening` | PQ-only key exchange, key-only auth |
| `roles/tor` | the onion service, from a user-supplied key |
| `roles/i2p` | i2pd server tunnels from user-supplied keys |
| `roles/caddy` | global config, TLS policy, shared snippets |
| `roles/website` | content + vhosts (clearnet, onion, I2P) |
| `roles/gemini` | Agate, certificates, capsule content |
| `roles/cgit` | repositories, fcgiwrap under its own user, vhosts |

Each role's `meta/main.yml` lists the roles it needs, such as `common`
for every role and `caddy` for the website and cgit. Ansible runs those
first, once each, so a role also works as the only one in a play.

## Requirements

* **Controller:** `ansible-core`, then `ansible-galaxy install -r requirements.yml`.
  Also `pip install libnacl` (and libsodium itself, e.g. `apt install
  libsodium23`) — the `onion_address` filter derives the `.onion` from the
  service secret key with libsodium's Ed25519 scalar multiplication.
  `rsync` too, which pushes the site and capsule content.
* **Target:** Debian 12/13 that the first run can log in to as root over
  SSH. The play installs sudo and Python itself if either is missing.
* Your **SSH client** needs one of the key exchanges sshd offers (see
  Key exchange) — check with `ssh -Q kex | grep -E 'mlkem|sntrup'` before
  you lock yourself out.

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
`--tags ssh`. `ssh` and `firewall` each run both roles, so a change to
`ssh_port` reaches sshd and the firewall together. Every role depends on
`common`, so a run with tags runs it too, and needs
`admin_authorized_keys` as a full run does.

To update only the website and capsule content on a host already
deployed, use `--tags content`, or `--tags web_content` or
`--tags gemini_content` for one of them. These sync each from its
`website_source` or `gemini_capsule_source`, and leave one without a
source as it is. Besides that they run only what runs with any tags:
`addresses` and each role's check of its inventory values, neither of
which changes the host.

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
without one is created as an empty bare repository that the accounts in
`cgit_pushers` (`admin_user` by default) push to over SSH:
`git remote add origin deploy@host:/srv/git/dotfiles.git`. The play adds
them to the `cgit` group and shares the repositories with it.

The index's Idle column shows each repository's newest commit, not when it
was last pushed or fetched: cgit's `post-receive.agefile` hook writes that
date to `info/web/last-modified` on every push, and every play run does the
same for mirrors, so cgit reads it instead of the refs' mtimes.

Clones are served by `git-http-backend` (smart HTTP) over all three
transports; `git-receive-pack` is never enabled, so HTTP access is read-only.

## Updates

Caddy is installed and upgraded from Caddy's own repository, which is
**pinned** so that apt takes only `caddy` from it, whatever else it
publishes. Unattended upgrades update Caddy from there too: by default
they take only the distribution's own packages, so the role adds Caddy's
repository to the ones they take from.

**Agate is updated only by a redeploy.** Debian does not package it,
so the role installs the upstream release binary, pinned by checksum,
and unattended upgrades cannot update it. That includes its TLS: Agate
bundles rustls, so TLS fixes for Gemini arrive only with a new Agate
release. To update, bump `gemini_version` and both checksums in
`roles/gemini/vars/main.yml` and redeploy. The `Agate release`
workflow checks weekly and fails when a newer release is out:

[![Agate release](https://github.com/njohnson-oss/configuration-journal-server/actions/workflows/agate.yml/badge.svg?branch=main)](https://github.com/njohnson-oss/configuration-journal-server/actions/workflows/agate.yml)

## Key exchange

* **SSH** is post-quantum only: sshd's `KexAlgorithms` lists only
  `sntrup761x25519-sha512@openssh.com` on Debian 12 (OpenSSH 9.2), and
  `mlkem768x25519-sha256` too on Debian 13 (OpenSSH 10.0).
* **HTTPS** is post-quantum only: Caddy's `tls` directive sets `curves`
  to the hybrid `x25519mlkem768` group alone. That group needs
  Caddy ≥ 2.10, which the role gets by installing Caddy from Caddy's
  own repository (see Updates).
* **Gemini is TLS 1.3 only, not post-quantum.** Agate (as of 3.3.24) uses
  rustls's `ring` provider, which offers only X25519, P-256 and P-384, and
  has no option to choose key exchange groups. The hybrid group is
  enforced for HTTPS only.

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
curl -sI https://example.com/ | grep -i onion-location  # Tor Browser's "onion available"
curl -I http://<b32>.b32.i2p/ --proxy http://127.0.0.1:4444  # via a local i2pd

# cgit clones over smart HTTP, on every transport
git clone https://git.example.com/dotfiles.git
torsocks git clone http://git.<onion>/dotfiles.git
git -c http.proxy=http://127.0.0.1:4444 clone http://<cgit-b32>.b32.i2p/dotfiles.git  # cgit's own destination
```