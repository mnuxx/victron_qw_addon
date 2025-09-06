# Victron QW Addon

This is a custom integration for Home Assistant to integrate with Victron devices via Modbus TCP.

## Prerequisites

- Victron Cerbo GX must be updated to firmware version 3.60 or later.
- Home Assistant version 2025.9 or later is required.

## Installation

1.  Install [HACS](https://hacs.xyz/).
2.  Go to HACS > Integrations > Custom repositories.
3.  Add the URL to this repository.
4.  Click "Install".
5.  Restart Home Assistant.
6.  Go to Settings > Devices & Services > Add Integration.
7.  Search for "Victron QW Addon".
8.  Enter the IP address of your Victron Cerbo GX.

## Configuration

The integration is configured via the UI. You will be prompted for the IP address of your Victron Cerbo GX.

The integration will use port 502 to connect to the Cerbo GX.

### Slave IDs
- PV inverter slave ID is usually 20.
- Energy meter slave ID must be 30 for the integration to work properly.

## Changelog

### 0.3.0
- Added prerequisites: Cerbo GX firmware 3.60+, Home Assistant 2025.9+
- Documented slave IDs: PV inverter usually 20, energy meter must be 30

### 0.2.2
- Fixed PV power sensor getting stuck at 0 after nighttime unavailability
- Removed register suppression mechanism to prevent sensors from being permanently skipped after failures

### 0.2.1
- Initial release with basic Victron QW integration
