# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.3] - 2021-07-19

### Added

- Support for Blender 2.92 and 2.93 LTS (v1.0.2 works with those too).

### Fixed

- Fix FocalPlaneXResolution and FocalPlaneYResolution EXIF tags.
- Fix crash during export of sun orientation when a sun lamp is not in use.

## [1.0.2] - 2020-11-27

### Added

- Support for Blender 2.91.
- Blender version enumeration for easy version comparison.

### Fixed

- Fix project docstring format to 'docblockr'.
- Fix parameters of ray_cast API for Blender 2.91.

## [1.0.1] - 2020-11-11

### Added

- Support for Blender 2.90.
- Check exiftool filename before rendering to detect unwanted -k option.

### Fixed

- Fix default sky model on Sky Texture shader node.

## [1.0.0] - 2020-02-24

- Initial SfM Flow release.

[unreleased]: https://github.com/davidemarelli/sfm_flow/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/davidemarelli/sfm_flow/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/davidemarelli/sfm_flow/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/davidemarelli/sfm_flow/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/davidemarelli/sfm_flow/releases/tag/v1.0.0
