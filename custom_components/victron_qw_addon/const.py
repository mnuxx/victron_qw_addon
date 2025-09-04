"""Constants for the Victron QW Addon integration."""
from __future__ import annotations
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)

DOMAIN = "victron_qw_addon"
CONF_IP_ADDRESS = "ip_address"
CONF_SLAVE_ID = "slave_id"
DEFAULT_PORT = 502
SLAVE_ID = 21
DEFAULT_BATTERY_TEMPERATURE_C = 25.0  # Fallback when temperature register is unavailable


@dataclass
class VictronSensorDescription(SensorEntityDescription):
    """Describes a Victron sensor entity.

    All added fields have defaults so we don't violate dataclass ordering rules
    imposed by the parent (which defines defaulted fields).
    """

    register: int = 0
    data_type: str = "int16"  # one of: "int16", "uint16"
    multiplier: float = 1.0    # raw_value * multiplier
    slave_id: int = 100      # default, can override per sensor


# NOTE: Victron voltage registers usually contain value * 10 (e.g. 230.5V -> 2305),
# so multiplier 0.1 converts to proper unit. Same for some power values if specified.
GRID_SENSORS: tuple[VictronSensorDescription, ...] = (
    # Grid power per phase (signed int16, already Watts)
    VictronSensorDescription(
        key="victron_qw_grid_l1",
        name="Victron QW Grid L1",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=820,
        data_type="int16",
        multiplier=1.0,
    ),
    VictronSensorDescription(
        key="victron_qw_grid_l2",
        name="Victron QW Grid L2",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=821,
        data_type="int16",
        multiplier=1.0,
    ),
    VictronSensorDescription(
        key="victron_qw_grid_l3",
        name="Victron QW Grid L3",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=822,
        data_type="int16",
        multiplier=1.0,
    ),
    # Grid frequency (int16, Hz). Assumes value is provided in Hz without scaling.
    VictronSensorDescription(
        key="victron_qw_grid_frequency",
        name="Victron QW Grid Frequency",
        native_unit_of_measurement="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        register=2644,
        data_type="uint16",
        multiplier=0.01,
        slave_id=SLAVE_ID,
        suggested_display_precision=2,
    ),
    # Input voltages (unsigned, need /10 => multiplier 0.1)
    VictronSensorDescription(
        key="victron_qw_input_voltage_phase_1",
        name="Victron QW Input Voltage Phase 1",
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        register=3,
        data_type="uint16",
        multiplier=0.1,
        slave_id=227,
    ),
    VictronSensorDescription(
        key="victron_qw_input_voltage_phase_2",
        name="Victron QW Input Voltage Phase 2",
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        register=4,
        data_type="uint16",
        multiplier=0.1,
        slave_id=227,
    ),
    VictronSensorDescription(
        key="victron_qw_input_voltage_phase_3",
        name="Victron QW Input Voltage Phase 3",
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        register=5,
        data_type="uint16",
        multiplier=0.1,
        slave_id=227,
    ),
    # AC Consumption per phase (uint16, Watts)
    VictronSensorDescription(
        key="victron_qw_ac_consumption_l1",
        name="Victron QW AC Consumption L1",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=817,
        data_type="uint16",
        multiplier=1.0,
        slave_id=100,
    ),
    VictronSensorDescription(
        key="victron_qw_ac_consumption_l2",
        name="Victron QW AC Consumption L2",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=818,
        data_type="uint16",
        multiplier=1.0,
        slave_id=100,
    ),
    VictronSensorDescription(
        key="victron_qw_ac_consumption_l3",
        name="Victron QW AC Consumption L3",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=819,
        data_type="uint16",
        multiplier=1.0,
        slave_id=100,
    ),
)

BATTERY_SENSORS: tuple[VictronSensorDescription, ...] = (
    VictronSensorDescription(
        key="victron_qw_battery_voltage",
        name="Victron QW Battery Voltage",
        native_unit_of_measurement="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        register=840,
        data_type="uint16",
        multiplier=0.1,  # Scale factor 10 means we need 0.1 to get actual volts
        slave_id=100,
        suggested_display_precision=1,
    ),
    VictronSensorDescription(
        key="victron_qw_battery_current",
        name="Victron QW Battery Current",
        native_unit_of_measurement="A",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        register=841,
        data_type="int16",
        multiplier=0.1,  # Scale factor 10 means we need 0.1 to get actual amps
        slave_id=100,
    ),
    VictronSensorDescription(
        key="victron_qw_battery_temperature",
        name="Victron QW Battery Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        register=262,
        data_type="int16",
        multiplier=0.1,  # Scale factor 10 => 25.3°C stored as 253
        slave_id=225,
        suggested_display_precision=1,
    ),
    # Calculated battery power = voltage * current (W)
    VictronSensorDescription(
        key="victron_qw_battery_power",
        name="Victron QW Battery Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=0,  # calculated, no direct Modbus read
    ),
    VictronSensorDescription(
        key="victron_qw_battery_soc",
        name="Victron QW Battery State of Charge",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        register=843,
        data_type="uint16",
        multiplier=1.0,
        slave_id=100,
    ),
)

# PV related sensors
PV_SENSORS: tuple[VictronSensorDescription, ...] = (
    VictronSensorDescription(
    key="total_pv_power",
        name="Total PV Power",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        register=1052,
        data_type="int32",
        multiplier=1.0,
        slave_id=SLAVE_ID,
    ),
)

# Combined register map for backward compatibility
REGISTER_MAP = {}
for sensor in GRID_SENSORS + BATTERY_SENSORS + PV_SENSORS:
    REGISTER_MAP[sensor.register] = (
        sensor.key,
        sensor.native_unit_of_measurement,
        sensor.multiplier,
        sensor.device_class
    )
