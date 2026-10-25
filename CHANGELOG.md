# Changelog

## [Unreleased]

### Added

- The `content` tag syncs the website and capsule from their sources without the rest of the deploy, and `web_content` and `gemini_content` sync one each. One without a source is left as it is. `--tags web` and `--tags gemini` ran their whole roles and `common` to do it.

### Changed

- `addresses` runs with a tag only for the roles that need it, as their dependency. It ran with any tags, so the content tags, `ssh` and `firewall` needed the onion and I2P keys too. A full run still runs it first, refusing a missing key before anything is deployed.
- cgit is always dark, whatever the browser prefers. Its stylesheet is upstream's dark theme, which no release has yet, loaded after Debian's `cgit.css`, whose colours it overrides.

## [2.0.0] - 2026-10-18

### Added

- A weekly workflow that fails when Agate has a release newer than the one pinned. Agate is the one service unattended upgrades cannot update, so the README now says so and how to update it.

### Changed

- sshd's key exchange algorithms are set per Debian release instead of probed with `ssh -Q kex` on the host. The probe could only fail on a release the play already refuses.
- cgit discards its access log, as the website does. It kept one at `/var/log/caddy/cgit.log`, with visitor addresses removed.
- Neither Caddy nor Agate logs requests, failed ones included. Caddy logged requests that failed with a server error, and Agate a line for every request, though neither with the visitor's address.
- cgit's FastCGI unit is locked down as Agate's is: no capabilities, a private user namespace, a hidden `/proc`, native system calls only and a 0077 umask among others. cgit and git parse repository data on every request.
- Every role lists the roles it needs in its `meta/main.yml` and runs on its own. Every role depends on `common`, which now also holds `vars/policy.yml`'s values and the Debian check, so a run with tags runs it too. The key checks and address derivation in `site.yml`'s pre_tasks moved to the `addresses` and `common` roles. The address facts are named for their role: `addresses_onion_hostname`, `addresses_cgit_onion_hostname` and `addresses_i2p`.
- Guarantees moved from role defaults to role vars, which inventory cannot override: `cgit_object_format`, `caddy_protocols`, `caddy_log_level` (whose DEBUG check went with it), Caddy's key checksum and apt pin, and Agate's version and checksums.
- Deployment choices with a working value are role defaults. Those several roles share are defaults of the role responsible for them: `common` for SSH access and `addresses` for names and keys. A value set in group_vars still overrides its default.
- `inventory/group_vars/all/main.yml` lists each deployment choice commented out, showing its default. Only `web_domain`, `acme_email` and `admin_authorized_keys` are left set there, as deploying needs them.
- Every role declares the values it reads from inventory in `meta/argument_specs.yml`, so a missing or mistyped one stops the play before the role's first task, not partway through a deploy.
- `web_hsts_include_subdomains`, a default of the `caddy` role, replaces `website_hsts` and `cgit_hsts`. It is off: both sent `includeSubDomains`, so set it true to keep covering subdomains, and if you set either, translate it to that boolean.
- HSTS's max-age of a year is a guarantee in the `caddy` role, so inventory can no longer shorten it.
- The I2P router settings inventory left to i2pd, with `~` or `false`, are optional: they default to i2pd's own behaviour, in the `i2p` role, or in `common` for the router port, which the firewall also reads. Inventory lists them commented out, with an example each.
- `i2p_ipv4` and `i2p_ipv6` are optional, with at least one on. Unset, i2pd uses IPv4 only, so `i2p_ipv6` is now off: set it true on a host with a public IPv6 address, and `i2p_ipv4` false on one without a public IPv4 address.
- `capsule_source` is now `gemini_capsule_source`, named for its role as `website_source` is; rename it if you set it.

### Removed

- `community.general` from `requirements.yml`. Nothing used it, and it was the collection that needed the newest ansible-core, 2.18.

### Fixed

- Pushing over SSH to a repository without a `source` works, as the README described. Nobody but `cgit` could write to one: the admin was not in its group, the repositories were not group-writable, and git refuses to push into a repository another user owns. The accounts in the new `cgit_pushers`, `admin_user` by default, are now added to the `cgit` group, the repositories are shared with it (existing ones on the next run), and git is told to trust them.
- Running only `--tags firewall` or only `--tags ssh` after changing `ssh_port` no longer locks you out. Each ran one role, leaving the firewall and sshd on different ports; each now runs both.
- Apt takes only Caddy from Caddy's repository, whatever else it publishes.
- Unattended upgrades now update Caddy. They take packages only from the distribution's own archives by default, so Caddy from its own repository was updated only by a redeploy.
- Caddy's package signing key is pinned by checksum, so a key server serving a different key fails the deploy instead of installing it.

## [1.0.0] - 2026-10-08

### Added

- Initial release: nine roles deploying a hardened Debian web, Gemini and Git server over clearnet, Tor and I2P.

[Unreleased]: https://github.com/njohnson-oss/configuration-journal-server/compare/v2.0.0...main
[2.0.0]: https://github.com/njohnson-oss/configuration-journal-server/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/njohnson-oss/configuration-journal-server/releases/tag/v1.0.0
