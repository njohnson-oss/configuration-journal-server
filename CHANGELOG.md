# Changelog

## [Unreleased]

### Added

- A weekly workflow that fails when Agate has a release newer than the one pinned. Agate is the one service unattended upgrades cannot update, so the README now says so and how to update it.

### Fixed

- Apt takes only Caddy from Caddy's repository, whatever else it publishes.
- Unattended upgrades now update Caddy. They take packages only from the distribution's own archives by default, so Caddy from its own repository was updated only by a redeploy.
- Caddy's package signing key is pinned by checksum, so a key server serving a different key fails the deploy instead of installing it.

## [1.0.0] - 2026-10-08

### Added

- Initial release: nine roles deploying a hardened Debian web, Gemini and Git server over clearnet, Tor and I2P.

[1.0.0]: https://github.com/njohnson-oss/configuration-journal-server/releases/tag/v1.0.0
