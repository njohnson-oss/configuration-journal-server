# Changelog

## [Unreleased]

### Added

- A weekly workflow that fails when Agate has a release newer than the one pinned. Agate is the one service unattended upgrades cannot update, so the README now says so and how to update it.

### Changed

- sshd's key exchange algorithms are set per Debian release instead of probed with `ssh -Q kex` on the host. The probe could only fail on a release the play already refuses.
- cgit discards its access log, as the website does. It kept one at `/var/log/caddy/cgit.log`, with visitor addresses removed.

### Fixed

- Pushing over SSH to a repository without a `source` works, as the README described. Nobody but `cgit` could write to one: the admin was not in its group, the repositories were not group-writable, and git refuses to push into a repository another user owns. The accounts in the new `cgit_pushers`, `admin_user` by default, are now added to the `cgit` group, the repositories are shared with it (existing ones on the next run), and git is told to trust them.
- Apt takes only Caddy from Caddy's repository, whatever else it publishes.
- Unattended upgrades now update Caddy. They take packages only from the distribution's own archives by default, so Caddy from its own repository was updated only by a redeploy.
- Caddy's package signing key is pinned by checksum, so a key server serving a different key fails the deploy instead of installing it.

## [1.0.0] - 2026-10-08

### Added

- Initial release: nine roles deploying a hardened Debian web, Gemini and Git server over clearnet, Tor and I2P.

[1.0.0]: https://github.com/njohnson-oss/configuration-journal-server/releases/tag/v1.0.0
