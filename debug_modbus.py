#!/usr/bin/env python3
"""
Debug script for Victron QW Modbus connection.
Run this to test connectivity and identify issues.
"""

import sys
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ConnectionException

def test_modbus_connection(ip_address, port=502, slave_id=100):
    """Test Modbus connection and read some registers."""
    print(f"Testing Modbus connection to {ip_address}:{port} (slave {slave_id})")

    client = ModbusTcpClient(ip_address, port=port)

    try:
        # Test connection
        if not client.connect():
            print("❌ Failed to connect to device")
            return False

        print("✅ Connected successfully")

        # Test reading some common registers
        test_registers = [
            (820, "Grid L1 Power", 1),
            (840, "Battery Voltage", 1),
            (1052, "Total PV Power", 2),  # 32-bit register
        ]

        for reg_addr, reg_name, count in test_registers:
            try:
                print(f"\nTesting register {reg_addr} ({reg_name}):")

                # Try input registers
                result = client.read_input_registers(address=reg_addr, count=count, slave=slave_id)
                if not result.isError():
                    print(f"  ✅ Input register {reg_addr}: {result.registers}")
                else:
                    print(f"  ❌ Input register {reg_addr}: Error {result.function_code}, Exception {getattr(result, 'exception_code', 'N/A')}")

                # Try holding registers
                result = client.read_holding_registers(address=reg_addr, count=count, slave=slave_id)
                if not result.isError():
                    print(f"  ✅ Holding register {reg_addr}: {result.registers}")
                else:
                    print(f"  ❌ Holding register {reg_addr}: Error {result.function_code}, Exception {getattr(result, 'exception_code', 'N/A')}")

            except Exception as e:
                print(f"  ❌ Exception reading register {reg_addr}: {e}")

        client.close()
        return True

    except ConnectionException as e:
        print(f"❌ Connection exception: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def scan_slave_ids(ip_address, port=502):
    """Scan for active slave IDs."""
    print(f"\nScanning for active slave IDs on {ip_address}:{port}")

    client = ModbusTcpClient(ip_address, port=port)

    if not client.connect():
        print("❌ Cannot connect to scan slave IDs")
        return

    active_slaves = []

    for slave_id in range(1, 248):  # Valid Modbus slave ID range
        try:
            result = client.read_holding_registers(address=820, count=1, slave=slave_id)
            if not result.isError():
                print(f"✅ Slave ID {slave_id} responded")
                active_slaves.append(slave_id)
        except:
            pass

    client.close()

    if active_slaves:
        print(f"\nActive slave IDs found: {active_slaves}")
    else:
        print("\nNo active slave IDs found")

    return active_slaves

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_modbus.py <ip_address> [port] [slave_id]")
        print("Example: python debug_modbus.py 192.168.1.100 502 100")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 502
    slave_id = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    print("Victron QW Modbus Debug Tool")
    print("=" * 40)

    # Test connection
    if test_modbus_connection(ip, port, slave_id):
        # Scan for slave IDs
        scan_slave_ids(ip, port)
    else:
        print("\n❌ Basic connection test failed. Check:")
        print("  - IP address is correct")
        print("  - Device is powered on")
        print("  - Network connectivity")
        print("  - Firewall settings")