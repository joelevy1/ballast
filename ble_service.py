"""
BLE GATT Service for Ballast Monitor
Version: 4-5-2026-v1.0
"""

import bluetooth
from micropython import const
import struct

VERSION = "4-5-2026-v1.0"

# BLE Service/Characteristic UUIDs (standard 16-bit)
_ENV_SENSE_UUID = const(0x181A)
_FLOW_METERS_UUID = const(0x2A6E)
_CONTROL_UUID = const(0x2A6F)
_VERSION_UUID = const(0x2A26)

# BLE IRQ events
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

class BallastBLEService:
    def __init__(self, flow_manager):
        self.flow_manager = flow_manager
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._connections = set()
        
        # Register GATT service
        self._register_services()
        
        print(f"BLE GATT services registered (v{VERSION})")
    
    def _register_services(self):
        # Flow Meters Characteristic (32 bytes = 8 x 4-byte uint32)
        FLOW_METERS = (
            bluetooth.UUID(_FLOW_METERS_UUID),
            bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
        )
        
        # Control Characteristic (write-only for commands)
        CONTROL = (
            bluetooth.UUID(_CONTROL_UUID),
            bluetooth.FLAG_WRITE,
        )
        
        # Version Characteristic (read-only)
        VERSION_CHAR = (
            bluetooth.UUID(_VERSION_UUID),
            bluetooth.FLAG_READ,
        )
        
        # Define service
        BALLAST_SERVICE = (
            bluetooth.UUID(_ENV_SENSE_UUID),
            (FLOW_METERS, CONTROL, VERSION_CHAR),
        )
        
        # Register service
        ((self._flow_handle, self._control_handle, self._version_handle),) = self._ble.gatts_register_services((BALLAST_SERVICE,))
        
        # Set initial version value
        from config import VERSION as SYSTEM_VERSION
        self._ble.gatts_write(self._version_handle, SYSTEM_VERSION.encode('utf-8'))
    
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print(f"BLE client connected: {conn_handle}")
        
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print(f"BLE client disconnected: {conn_handle}")
        
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if attr_handle == self._control_handle:
                value = self._ble.gatts_read(self._control_handle)
                self._handle_command(value.decode('utf-8'))
    
    def _handle_command(self, command):
        print(f"Received command: {command}")
        
        if command == "RESET_ALL":
            self.flow_manager.reset_all_counters()
            print("Reset all counters")
        
        elif command.startswith("RESET:"):
            try:
                meter_id = int(command.split(':')[1])
                if 0 <= meter_id < 8:
                    self.flow_manager.reset_counter(meter_id)
                    print(f"Reset counter {meter_id}")
            except:
                print(f"Invalid reset command: {command}")
    
    def update_flow_data(self):
        # Pack 8 pulse counts as uint32 (little-endian)
        counts = self.flow_manager.get_all_pulse_counts()
        data = struct.pack('<8I', *counts)
        
        # Notify all connected clients
        for conn_handle in self._connections:
            try:
                self._ble.gatts_notify(conn_handle, self._flow_handle, data)
            except:
                pass
    
    def is_connected(self):
        return len(self._connections) > 0
