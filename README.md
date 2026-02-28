![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)

# Digital Dream Labs Vector (Anki Vector) for Home Assistant

This custom integration connects your Vector robot to Home Assistant over your local network.

## What You Get

After setup, Home Assistant can expose data from Vector, including:

- Current activity (sleeping, moving, charging, etc.)
- Battery percentage and battery details
- Lifetime stats (days alive, trigger-word reactions, seconds petted, distance moved)
- Orientation and lift diagnostics
- Stimulation data (disabled by default)
- Master volume control (disabled by default)
- Eye color preset control (disabled by default)
- Quick actions as buttons (sleep, go home, explore, dance, fetch cube)
- Vision camera entity (disabled by default)
- Home Assistant actions/services:
  - `vector.say_text`
  - `vector.set_eye_color`

## Before You Start

- Home Assistant version: `2026.3.0` or newer
- Vector robot reachable on your local network
- Robot details:
  - Robot name (`Vector-XXXX` format)
  - Host (IP address or hostname)
  - Serial number (optional but recommended)

You can use either of these modes:

- EscapePod/Wire-pod mode:
  - Fill robot name, host, and serial
- DDL cloud mode:
  - Fill robot name, host, serial, email, and password
  - Email/password are only used for cloud auth data retrieval
  - Home Assistant still talks to the robot locally via host

## Installation

### ~~Option 1: HACS (recommended)~~

1. ~~Open HACS in Home Assistant.~~
2. ~~Add this repository as a custom repository (category: Integration).~~
3. ~~Install `Vector`.~~
4. ~~Restart Home Assistant.~~

### Option 2: HACS via custom repository

1. Open HACS in Home Assistant.
2. Go to the custom repositories section.
3. Add `https://github.com/MTrab/vector` as category `Integration`.
4. Find and install `Vector` in HACS.
5. Restart Home Assistant.

### Option 3: Manual file copy

1. Copy `custom_components/vector` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

## Setup in Home Assistant

1. Go to `Settings -> Devices & Services`.
2. Click `Add Integration` and search for `Vector`.
3. Enter your robot details.
4. Discovery is supported via DHCP and Zeroconf/mDNS when available.
5. Finish setup.

## Enabling Optional Entities

Some entities are disabled by default to keep dashboards clean.

To enable them:

1. Open your Vector device in Home Assistant.
2. Open the entity list.
3. Enable entities like `Vision`, `Volume`, `Stimulation`, and diagnostic sensors as needed.

## Actions for Automations

Use Home Assistant `Actions` (or services) under the `vector` domain:

- `vector.say_text`
  - Required: `text`
  - Optional: `device_id`, `use_vector_voice`, `duration_scalar`, `pitch_scalar`
- `vector.set_eye_color`
  - Required: `rgb_color` (RGB)
  - Optional: `device_id`

If you have multiple Vector devices, pass `device_id` to target a specific robot.

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

This project is under active development. Behavior and exposed entities may improve or change between releases.

## Support

- Issues and feature requests: https://github.com/MTrab/vector/issues
