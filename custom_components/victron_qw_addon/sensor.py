"""Platform for sensor integration."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    CONF_IP_ADDRESS,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    SLAVE_ID,
    GRID_SENSORS,
    BATTERY_SENSORS,
    PV_SENSORS,
    VictronSensorDescription,
    DEFAULT_BATTERY_TEMPERATURE_C,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=10)


class VictronDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Victron device."""

    def __init__(self, hass: HomeAssistant, client: ModbusTcpClient, descriptions: tuple[VictronSensorDescription, ...]) -> None:
        """Initialize."""
        self.client = client
        self._descriptions = descriptions
        self._fail_counts: dict[int, int] = {}
        self._suppressed: set[int] = set()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Victron device."""
        try:
            data = {}
            failures = 0
            for description in self._descriptions:
                base_address = description.register
                # Skip direct Modbus read for calculated battery power; compute later
                if description.key == "victron_qw_battery_power":
                    continue

                if base_address in self._suppressed:
                    continue  # Skip permanently noisy register

                attempts = []  # (label, func_result)

                def try_read(fn_name: str, addr: int, count: int = 1):
                    try:
                        slave = description.slave_id
                        if fn_name == 'input':
                            return self.client.read_input_registers(address=addr, count=count, slave=slave)
                        return self.client.read_holding_registers(address=addr, count=count, slave=slave)
                    except Exception as exc:  # noqa: BLE001
                        return exc

                reg_count = 2 if description.data_type in ("int32", "uint32") else 1
                attempts.append((f"input@{base_address}", try_read('input', base_address, reg_count)))
                attempts.append((f"holding@{base_address}", try_read('holding', base_address, reg_count)))
                if base_address > 0:
                    attempts.append((f"input@{base_address-1}", try_read('input', base_address - 1, reg_count)))
                    attempts.append((f"holding@{base_address-1}", try_read('holding', base_address - 1, reg_count)))

                chosen_result = None
                chosen_label = None
                alt_address_used = None
                for label, res in attempts:
                    if isinstance(res, Exception):
                        continue
                    if not res.isError():
                        chosen_result = res
                        chosen_label = label
                        if '@' in label:
                            addr_part = int(label.split('@')[1])
                            if addr_part != base_address:
                                alt_address_used = addr_part
                        break

                if not chosen_result:
                    # Update failure count
                    self._fail_counts[base_address] = self._fail_counts.get(base_address, 0) + 1
                    count = self._fail_counts[base_address]
                    fc_summary = []
                    for label, res in attempts:
                        if hasattr(res, 'isError') and res.isError():
                            fc_summary.append(
                                f"{label}:fc={getattr(res,'function_code','?')} ex={getattr(res,'exception_code','?')}"
                            )
                    if fc_summary:
                        # Only log every 3rd failure after first 3 to reduce noise
                        if count <= 3 or count % 3 == 0:
                            _LOGGER.warning(
                                "Register %s (key=%s, slave=%s) read failed (attempt %s): %s",
                                base_address,
                                description.key,
                                description.slave_id,
                                count,
                                '; '.join(fc_summary),
                            )
                    else:
                        _LOGGER.warning("Register %s read error: no response", base_address)

                    # Suppress after 12 consecutive failures
                    if self._fail_counts[base_address] >= 12:
                        self._suppressed.add(base_address)
                        _LOGGER.error(
                            "Register %s suppressed after %s consecutive failures. Remove or correct mapping in const.py.",
                            base_address, self._fail_counts[base_address]
                        )
                    # Count gateway target failures (ex=10) for reconnect heuristic
                    if any('ex=10' in s for s in fc_summary):
                        failures += 1
                        if count <= 3 or count % 3 == 0:
                            _LOGGER.warning(
                                "Modbus exception 10 (gateway target no response) for key=%s at slave=%s. "
                                "This may indicate the device is temporarily unavailable or using a different slave ID.",
                                description.key,
                                description.slave_id,
                            )
                    # For PV sensors, be more tolerant of failures since they might be on separate devices
                    if description.key == "total_pv_power" and count >= 5:
                        _LOGGER.info(
                            "PV sensor failed %s times. If you have a separate PV inverter, ensure it's powered on and connected. "
                            "If not, set the slave ID to %s (same as main device).",
                            count, SLAVE_ID
                        )
                    continue

                # Success path: reset fail count
                if base_address in self._fail_counts:
                    if self._fail_counts[base_address] > 0:
                        _LOGGER.info(
                            "Register %s recovered after %s failures.", base_address, self._fail_counts[base_address]
                        )
                    self._fail_counts[base_address] = 0

                if not getattr(chosen_result, 'registers', None):
                    _LOGGER.warning("Register %s returned empty data (via %s)", base_address, chosen_label)
                    continue

                regs = chosen_result.registers
                if description.data_type in ("uint32", "int32"):
                    if len(regs) < 2:
                        _LOGGER.warning("Register %s expected 2 words for 32-bit value", base_address)
                        continue
                    high, low = regs[0], regs[1]
                    raw32 = (high << 16) | low
                    if description.data_type == "int32":
                        value = raw32 - 0x100000000 if raw32 >= 0x80000000 else raw32
                    else:
                        value = raw32
                else:
                    raw = regs[0]
                    if description.data_type == "uint16":
                        value = raw
                    else:
                        value = raw - 0x10000 if raw >= 0x8000 else raw

                if description.multiplier != 1.0:
                    try:
                        value = float(value) * description.multiplier
                    except (TypeError, ValueError):
                        _LOGGER.debug("Multiplier application failed for %s", description.key)
                data[description.key] = value

                # Log successful PV data reads
                if description.key == "total_pv_power" and base_address in self._fail_counts and self._fail_counts[base_address] > 0:
                    _LOGGER.info("PV sensor recovered - reading %s watts from slave %s", value, description.slave_id)

                if alt_address_used is not None:
                    _LOGGER.info(
                        "Register %s served from adjusted address %s (%s). Consider updating const.py.",
                        base_address, alt_address_used, chosen_label
                    )

            if failures == len(self._descriptions):
                try:
                    self.client.close()
                    self.client.connect()
                except Exception:  # noqa: BLE001
                    pass
            # Post-process: calculate battery power if voltage and current are present
            try:
                v = data.get("victron_qw_battery_voltage")
                c = data.get("victron_qw_battery_current")
                if v is not None and c is not None:
                    # Both v and c already have correct scaling (V and A)
                    data["victron_qw_battery_power"] = round(float(v) * float(c))
            except Exception:  # noqa: BLE001
                pass

            # Ensure a default battery temperature in Celsius if register is missing/unavailable
            if "victron_qw_battery_temperature" not in data:
                data["victron_qw_battery_temperature"] = DEFAULT_BATTERY_TEMPERATURE_C
            
            # Ensure Total PV Power shows 0 when sensor is not available
            if "total_pv_power" not in data:
                data["total_pv_power"] = 0
            return data
        except ConnectionException as error:
            raise UpdateFailed(f"Connection failed: {error}") from error


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Prefer options over data to allow changes via OptionsFlow
    ip_address = entry.options.get(CONF_IP_ADDRESS, entry.data[CONF_IP_ADDRESS])
    client = ModbusTcpClient(ip_address, port=DEFAULT_PORT)

    try:
        if not client.connect():
            raise ConfigEntryNotReady("Initial Modbus connection failed")
        _LOGGER.info("Successfully connected to Victron device at %s:%s", ip_address, DEFAULT_PORT)
    except ConnectionException as ex:
        raise ConfigEntryNotReady(f"Could not connect to Victron device: {ex}") from ex

    # Build final descriptions with configured PV slave
    configured_slave_id = entry.options.get(CONF_SLAVE_ID, entry.data.get(CONF_SLAVE_ID, SLAVE_ID))
    _LOGGER.info("Using slave ID %s for PV inverter (configured: %s, default: %s)",
                 configured_slave_id, entry.options.get(CONF_SLAVE_ID), SLAVE_ID)

    # Check if PV slave ID is different from main device
    pv_slave_different = configured_slave_id != SLAVE_ID
    if pv_slave_different:
        _LOGGER.warning("PV inverter configured with different slave ID (%s) than main device (%s). "
                       "If no PV inverter is connected, set slave ID to %s or remove PV sensors.",
                       configured_slave_id, SLAVE_ID, SLAVE_ID)

    final_descriptions: list[VictronSensorDescription] = []
    for description in (*GRID_SENSORS, *BATTERY_SENSORS):
        final_descriptions.append(description)

    # Only add PV sensors if configured with different slave ID (separate PV inverter)
    # or if using same slave ID (PV data from Cerbo)
    if configured_slave_id == SLAVE_ID:
        _LOGGER.info("Using same slave ID for PV sensors - assuming PV data comes from Cerbo GX")
        for description in PV_SENSORS:
            final_descriptions.append(description)
    elif pv_slave_different:
        _LOGGER.info("Adding PV sensors with separate slave ID %s", configured_slave_id)
        for description in PV_SENSORS:
            from dataclasses import replace
            final_descriptions.append(replace(description, slave_id=configured_slave_id))

    coordinator = VictronDataUpdateCoordinator(hass, client, tuple(final_descriptions))
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(f"Initial data refresh failed: {err}") from err

    sensors = []
    for description in final_descriptions:
        sensors.append(VictronSensor(coordinator, description))

    async_add_entities(sensors)


class VictronSensor(SensorEntity):
    """Representation of a Victron sensor."""

    entity_description: VictronSensorDescription

    def __init__(
        self,
        coordinator: VictronDataUpdateCoordinator,
        description: VictronSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entity_description = description
        # unique_id: keep stable & concise
        self._attr_unique_id = description.key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "victron_device")},
            "name": "Victron Energy",
            "manufacturer": "Victron Energy",
        }
        self._attr_force_update = True

    @property
    def native_value(self) -> float | int | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            value = self.coordinator.data.get(self.entity_description.key)
            # For Total PV Power, return 0 instead of None when data is missing
            if value is None and self.entity_description.key == "total_pv_power":
                return 0
            return value
        # For Total PV Power, return 0 when coordinator has no data
        if self.entity_description.key == "total_pv_power":
            return 0
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
