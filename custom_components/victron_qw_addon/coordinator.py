"""Data update coordinator handling Modbus polling."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, SLAVE_ID

_LOGGER = logging.getLogger(__name__)


@dataclass
class VictronData:
    raw: dict[int, int]
    processed: dict[str, Any]


class VictronDataCoordinator(DataUpdateCoordinator[VictronData]):
    def __init__(self, hass: HomeAssistant, host: str, port: int, update_interval) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=update_interval,
        )
        self._host = host
        self._port = port

    def _read_register(self, client, address: int) -> int | None:
        try:
            result = client.read_holding_registers(address, 1, device_id=SLAVE_ID)
            if result.isError():  # pragma: no cover
                _LOGGER.debug("Modbus error reading %s: %s", address, result)
                return None
            return result.registers[0]
        except Exception as exc:  # pragma: no cover - network/IO
            _LOGGER.debug("Exception reading register %s: %s", address, exc)
            return None

    def _sync_fetch(self) -> VictronData:
        # Local import to avoid blocking event loop during initial component import
        from pymodbus.client import ModbusTcpClient  # type: ignore
        raw: dict[int, int] = {}
        processed: dict[str, Any] = {}
        client = ModbusTcpClient(self._host, port=self._port, timeout=5)
        _LOGGER.debug("Attempting Modbus TCP connect to %s:%s (device_id %s)", self._host, self._port, SLAVE_ID)
        if not client.connect():  # pragma: no cover
            _LOGGER.warning("Victron QW Addon: Failed to connect to %s:%s", self._host, self._port)
            return VictronData(raw=raw, processed=processed)
        try:
            # TODO: Define REGISTER_MAP or implement register reading logic
            # for address, (label, unit, scale, device_class) in REGISTER_MAP.items():
            #     value = self._read_register(client, address)
            #     if value is not None:
            #         raw[address] = value
            #         scaled = value * scale
            #         processed[label] = scaled
            #         _LOGGER.debug("Register %s (%s) raw=%s scaled=%s%s", address, label, value, scaled, unit or "")
            #     else:
            #         _LOGGER.debug("Register %s read returned None", address)
            pass
        finally:
            client.close()
        if not processed:
            _LOGGER.info("Victron QW Addon: No data processed this cycle (host=%s)", self._host)
        else:
            _LOGGER.debug("Victron QW Addon processed data keys: %s", list(processed.keys()))
        return VictronData(raw=raw, processed=processed)

    async def _async_update_data(self) -> VictronData:  # coordinator entry point
        _LOGGER.debug("Coordinator update start")
        return await self.hass.async_add_executor_job(self._sync_fetch)
