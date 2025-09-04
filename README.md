
# Victron QW Addon

This is a custom integration for Home Assistant to integrate with Victron devices via Modbus TCP.

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

## Compatibility

**2025-09-04:** The `manifest.json` now allows `pymodbus` versions from 3.9.2 up to (but not including) 4.0.0 for better compatibility with Home Assistant and other integrations. If you had dependency errors, update to the latest version of this addon.
