# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- Remove old copyright & license fields.
- Clean up KiCad project file.
- Remove old library setup instructions from CONTRIBUTING.md.

### Changed

- Remove hard-coded project metadata from tasks.py.

## [2.0.1] - 2025-05-12

### Added

- Add mounting hole outlines to `*.Fab` and `*.Assembly` layers.

### Fixed

- Fix missing layers in `kicad-cli` exports.
- Fix layer types for `F.Fab` and `B.Fab` layers.

### Changed

- Change PCB revision to `B`.

## [2.0.0] - 2025-05-09

### Added

- Add a power switch (`SW2`) attached to the the Pico's `3V3_EN` input pin.
- Add a power LED (`D1`) that turns on when the Pico is powered on.
- Add a tactile reset switch (`SW1`) connected to the Pico's `RUN` input pin (#2).
- Add a project management CLI using [Invoke](https://www.pyinvoke.org/) task runner.

### Fixed

- Switch Pico footprint to fix castellated test point issues on `v1` design (#3).

### Changed

- Migrate the design to use the [CGND KiCad Library](https://github.com/cgnd/cgnd-kicad-lib/) and internal part numbers managed by the https://cgnd-oshw.aligni.com Aligni PLM instance.

## [1.0.0] - 2025-05-04

Initial release of the `v1` design files.
