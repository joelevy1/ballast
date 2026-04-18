"""
BLE GATT Service for Ballast Monitor
Version: 4-18-2026-v1.2
Adds file transfer support for OTA updates via BLE
"""

import bluetooth
import struct
from micropython import const

# GATT Service/Characteristic UUIDs (Environmental Sensing)
_SERVICE_UUID = bluetooth.UUID(0x181A)
_FLOW_CHAR_UUID = bluetooth.UUID(0x2A6E)  # Flow meters data (Read/Notify)
_CONTROL_CHAR_UUID = bluetooth.UUID(0x2A6F)  # Control commands (Write)
_VERSION_CHAR_UUID = bluetooth.UUID(0x2A26)  # Firmware version (Read)
_FILE_TRANSFER_UUID = bluetooth.UUID(0x2A6D)  # File transfer (Read/Write)
_FILE_CONTROL_UUID = bluetooth.UUID(0x2A6C)  # File control (Write)

# Characteristic flags
_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

class BLEService:
    def __init__(self, ble, flow_meters, version="4-18-2026-v1.2"):
        self._ble = ble
        self._flow_meters = flow_meters
        self._version = version
        self._connections = set()
        self._flow_handle = None
        self._control_handle = None
        self._version_handle = None
        self._file_transfer_handle = None
        self._file_control_handle = None
        
        # File transfer state
        self._file_transfer_active = False
        self._file_name = None
        self._file_data = bytearray()
        self._file_size = 0
        self._bytes_received = 0
        
        self._register_services()
        self._ble.irq(self._irq)
        
        print(f"BLE GATT services registered (v{version})")
    
    def _register_services(self):
        """Register GATT services and characteristics"""
        # Flow meters characteristic (32 bytes = 8 x uint32)
        flow_char = (
            _FLOW_CHAR_UUID,
            _FLAG_READ | _FLAG_NOTIFY,
        )
        
        # Control characteristic (write commands)
        control_char = (
            _CONTROL_CHAR_UUID,
            _FLAG_WRITE,
        )
        
        # Version characteristic (read firmware version)
        version_char = (
            _VERSION_CHAR_UUID,
            _FLAG_READ,
        )
        
        # File transfer characteristic (512 byte chunks)
        file_transfer_char = (
            _FILE_TRANSFER_UUID,
            _FLAG_READ | _FLAG_WRITE,
        )
        
        # File control characteristic (start/end transfer commands)
        file_control_char = (
            _FILE_CONTROL_UUID,
            _FLAG_WRITE,
        )
        
        # Register service with all characteristics
        service = (
            _SERVICE_UUID,
            (flow_char, control_char, version_char, file_transfer_char, file_control_char),
        )
        
        ((self._flow_handle, self._control_handle, self._version_handle, 
          self._file_transfer_handle, self._file_control_handle),) = self._ble.gatts_register_services((service,))
    
    def _irq(self, event, data):
        """Handle BLE events"""
        if event == 1:  # _IRQ_CENTRAL_CONNECT
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print(f"BLE client connected: {conn_handle}")
            
        elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print(f"BLE client disconnected: {conn_handle}")
            
        elif event == 3:  # _IRQ_GATTS_WRITE
            conn_handle, attr_handle = data
            value = self._ble.gatts_read(attr_handle)
            
            if attr_handle == self._control_handle:
                self._handle_control_command(value)
            elif attr_handle == self._file_control_handle:
                self._handle_file_control(value)
            elif attr_handle == self._file_transfer_handle:
                self._handle_file_chunk(value)
    
    def _handle_control_command(self, data):
        """Handle control commands from app"""
        if len(data) < 1:
            return
            
        cmd = data[0]
        
        if cmd == 0x01:  # Reset all
            print("Command: Reset all meters")
            for i in range(8):
                self._flow_meters.reset_meter(i)
                
        elif cmd == 0x02:  # Reset specific meter
            if len(data) >= 2:
                meter_id = data[1]
                if 0 <= meter_id < 8:
                    print(f"Command: Reset meter {meter_id}")
                    self._flow_meters.reset_meter(meter_id)
    
    def _handle_file_control(self, data):
        """Handle file transfer control commands"""
        if len(data) < 1:
            return
            
        cmd = data[0]
        
        if cmd == 0x01:  # Start file transfer
            if len(data) >= 6:
                # Format: 0x01 | file_size(4 bytes) | filename_len(1 byte) | filename
                file_size = struct.unpack('<I', data[1:5])[0]
                filename_len = data[5]
                filename = data[6:6+filename_len].decode('utf-8')
                
                self._file_transfer_active = True
                self._file_name = filename
                self._file_size = file_size
                self._file_data = bytearray()
                self._bytes_received = 0
                
                print(f"Starting file transfer: {filename} ({file_size} bytes)")
                
        elif cmd == 0x02:  # End file transfer
            if self._file_transfer_active:
                print(f"File transfer complete: {self._file_name} ({self._bytes_received} bytes)")
                
                # Write file to filesystem
                try:
                    with open(self._file_name, 'wb') as f:
                        f.write(self._file_data)
                    print(f"File saved: {self._file_name}")
                    
                    # Send success response
                    self._ble.gatts_write(self._file_control_handle, bytes([0x01]))  # Success
                    
                except Exception as e:
                    print(f"Error saving file: {e}")
                    self._ble.gatts_write(self._file_control_handle, bytes([0x00]))  # Error
                
                # Reset state
                self._file_transfer_active = False
                self._file_name = None
                self._file_data = bytearray()
                self._file_size = 0
                self._bytes_received = 0
                
        elif cmd == 0x03:  # Restart Pico
            print("Restart command received - rebooting in 3 seconds...")
            import time
            import machine
            time.sleep(3)
            machine.reset()
    
    def _handle_file_chunk(self, data):
        """Handle incoming file data chunk"""
        if not self._file_transfer_active:
            return
        
        self._file_data.extend(data)
        self._bytes_received += len(data)
        
        # Send progress update via file_transfer characteristic
        progress = int((self._bytes_received / self._file_size) * 100) if self._file_size > 0 else 0
        self._ble.gatts_write(self._file_transfer_handle, struct.pack('<I', progress))
        
        if self._bytes_received % 1024 == 0:  # Log every KB
            print(f"Received {self._bytes_received}/{self._file_size} bytes ({progress}%)")
    
    def update_flow_values(self):
        """Update flow meter values and notify connected clients"""
        if not self._connections:
            return
        
        # Pack 8 x uint32 values (32 bytes total)
        data = bytearray(32)
        for i in range(8):
            count = self._flow_meters.get_count(i)
            struct.pack_into('<I', data, i * 4, count)
        
        # Notify all connected clients
        self._ble.gatts_notify(None, self._flow_handle, data)
    
    def set_version_info(self, version):
        """Update version characteristic"""
        version_bytes = version.encode('utf-8')[:20]  # Max 20 chars
        self._ble.gatts_write(self._version_handle, version_bytes)
