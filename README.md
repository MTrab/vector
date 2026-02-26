![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)

# Digital Dream Labs Vector (Anki Vector) for Home Assistant

This custom integration connects your Vector robot to Home Assistant over your local network.

## What You Get

After setup, Home Assistant can expose data from Vector, including:

- Current activity (sleeping, moving, charging, etc.)
- Battery percentage and battery details
- Lifetime stats (days alive, trigger-word reactions, seconds petted, distance moved)
- Stimulation data (disabled by default)
- Master volume control (disabled by default)
- Vision camera entity (disabled by default)

## Before You Start

- Home Assistant version: `2025.4.0` or newer
- Vector robot reachable on your local network
- Robot details:
  - Robot name (`Vector-XXXX` format)
  - Host (IP address or hostname)
  - Serial number

You can use either of these modes:

- EscapePod/Wire-pod mode:
  - Fill robot name, host, and serial
- DDL cloud mode:
  - Fill robot name, host, serial, email, and password
  - Email/password are only used for cloud auth data retrieval
  - Home Assistant still talks to the robot locally via host

## Installation

### ~~Option 1: HACS (recommended)~~

~~Not available yet: this integration is not in HACS at the moment.~~

### Option 2: Manual

1. Copy `custom_components/vector` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Setup in Home Assistant

1. Go to `Settings -> Devices & Services`.
2. Click `Add Integration` and search for `Vector`.
3. Enter your robot details.
4. Finish setup.

## Enabling Optional Entities

Some entities are disabled by default to keep dashboards clean.

To enable them:

1. Open your Vector device in Home Assistant.
2. Open the entity list.
3. Enable entities like `Vision`, `Volume`, `Stimulation`, and diagnostic sensors as needed.

## Troubleshooting

### Integration cannot connect

- Confirm the robot host is correct and reachable from Home Assistant.
- Confirm robot name format is `Vector-XXXX`.
- Confirm serial is set.

### DDL mode errors

- Email and password must both be set (or both left empty).
- Keep host/serial filled even when using DDL cloud mode.

### Camera shows fallback image

- This can happen while the stream is not ready.
- If Vector is sleeping, the integration intentionally returns a sleep image.

## Privacy and Security

- Communication with the robot is local-network first.
- Credentials are stored in Home Assistant config entry storage.
- This integration does not add telemetry endpoints.

## Known Status

This project is under active development. Behavior and exposed entities may improve between releases.

## Support

- Issues and feature requests: https://github.com/MTrab/vector/issues
