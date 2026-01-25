# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2026-01-26

### Fixed
- Fixed protobuf version compatibility warning by regenerating proto files with protobuf 6.31.1 ([#2](https://github.com/xykong/prometheus-remote-writer/issues/2))
- Resolved version mismatch between generated code (5.29.0) and runtime requirements (>=6.31.1)

### Changed
- Updated all protobuf generated code from version 5.29.0 to 6.31.1
- Version bumped from 0.1.2 to 1.1.3 (major version increase to reflect protobuf compatibility update)

### Documentation
- Added comprehensive SSL certificate verification examples in README
- Added authentication examples (Basic auth and Bearer token) in README
- Improved proxy configuration documentation

## [0.1.2] - 2025-08-26

### Changed
- Previous stable release

## [0.1.1] - 2025-08-26

### Changed
- Minor bug fixes and improvements

## [0.0.12] - 2025-02-11

### Added
- Initial public release with core functionality
- Support for Prometheus Remote Write protocol
- Batch data sending capability
- Custom HTTP headers and authentication support
- SSL certificate verification options
- Proxy configuration support

[1.1.3]: https://github.com/xykong/prometheus-remote-writer/compare/v0.1.2...v1.1.3
[0.1.2]: https://github.com/xykong/prometheus-remote-writer/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/xykong/prometheus-remote-writer/compare/v0.0.12...v0.1.1
[0.0.12]: https://github.com/xykong/prometheus-remote-writer/releases/tag/v0.0.12
