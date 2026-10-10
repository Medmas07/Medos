# IoT

## Status

IoT is OPTIONAL. PlatformIO preparation is IMPLEMENTED, but no product IoT behavior, hardware, board, embedded framework, or protocol is selected.

## Purpose

This directory is reserved for embedded or connected-device components if required by the final challenge.

## PlatformIO

PlatformIO is the prepared project tooling for embedded development if IoT is required.

The target platform, board and framework will be selected after the hardware requirements are known.

## Architecture

Embedded code should preserve clear boundaries between business/application logic and hardware-specific code when practical.

## Structure

- `src/` — firmware source code
- `include/` — project headers
- `lib/` — project-specific libraries
- `test/` — embedded/unit tests
- `platformio.ini` — PlatformIO configuration
