# Changelog

## [Unreleased]

### Fixed

- Apt takes only Caddy from Caddy's repository, whatever else it publishes.
- Unattended upgrades now update Caddy. They take packages only from the distribution's own archives by default, so Caddy from its own repository was updated only by a redeploy.

## [1.0.0] - 2026-10-08

### Added

- Initial release: nine roles deploying a hardened Debian web, Gemini and Git server over clearnet, Tor and I2P.

[1.0.0]: https://github.com/njohnson-oss/configuration-journal-server/releases/tag/v1.0.0
