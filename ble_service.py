"""
BLE GATT Service for Ballast Monitor
Version: 4-19-2026-v1.3
Adds file transfer support for OTA updates via BLE
"""

import bluetooth
import struct
from micropython import const

_SERVICE_UUID = bluetooth.UUID(0x181A)
_FLOW_CHAR_UUID = bluetooth.UUID(0x2A6E)
_CONTROL_CHAR_UUID = bluetooth.UUID(0x2A6F)
_VERSION_CHAR_UUID = bluetooth.UUID(0x2A26)
_FILE_TRANSFER_UUID = bluetooth.UUID(0x2A6D)
_FILE_CONTROL_UUID = bluetooth.UUID(0x2A6C)

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
        
        self._file_transfer_active = False
        self._file_name = None
        self._file_data = bytearray()
        self._file_size = 0
        self._bytes_received = 0
        
        self._register_services()
        self._ble.irq(self._irq)
        self.set_version_info(version)

        print(f"BLE GATT services registered (v{version})")
    
    def _register_services(self):
        flow_char = (_FLOW_CHAR_UUID, _FLAG_READ | _FLAG_NOTIFY)
        control_char = (_CONTROL_CHAR_UUID, _FLAG_WRITE)
        version_char = (_VERSION_CHAR_UUID, _FLAG_READ)
        file_transfer_char = (_FILE_TRANSFER_UUID, _FLAG_READ | _FLAG_WRITE)
        file_control_char = (_FILE_CONTROL_UUID, _FLAG_WRITE)
        
        service = (_SERVICE_UUID, (flow_char, control_char, version_char, file_transfer_char, file_control_char))
        
        ((self._flow_handle, self._control_handle, self._version_handle, 
          self._file_transfer_handle, self._file_control_handle),) = self._ble.gatts_register_services((service,))
    
    def _irq(self, event, data):
        if event == 1:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            print(f"BLE client connected: {conn_handle}")
            
        elif event == 2:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            print(f"BLE client disconnected: {conn_handle}")
            
        elif event == 3:
            conn_handle, attr_handle = data
            value = self._ble.gatts_read(attr_handle)
            
            if attr_handle == self._control_handle:
                self._handle_control_command(value)
            elif attr_handle == self._file_control_handle:
                self._handle_file_control(value)
            elif attr_handle == self._file_transfer_handle:
                self._handle_file_chunk(value)
    
    def _handle_control_command(self, data):
        if len(data) < 1:
            return
            
        cmd = data[0]
        
        if cmd == 0x01:
            print("Command: Reset all meters")
            for i in range(8):
                self._flow_meters.reset_meter(i)
                
        elif cmd == 0x02:
            if len(data) >= 2:
                meter_id = data[1]
                if 0 <= meter_id < 8:
                    print(f"Command: Reset meter {meter_id}")
                    self._flow_meters.reset_meter(meter_id)

        elif cmd == 0x04:
            # Next boot: main.py runs WiFi web UI once (wifi_once.flag). config.MODE stays "ble".
            print("Command: Schedule one-shot WiFi boot")
            try:
                with open("wifi_once.flag", "w") as f:
                    f.write("1")
                import time
                import machine

                time.sleep_ms(500)
                machine.reset()
            except Exception as e:
                print(f"wifi_once schedule error: {e}")

    def _handle_file_control(self, data):
        if len(data) < 1:
            return
            
        cmd = data[0]
        
        if cmd == 0x01:
            if len(data) >= 6:
                file_size = struct.unpack('<I', data[1:5])[0]
                filename_len = data[5]
                filename = data[6:6+filename_len].decode('utf-8')
                
                self._file_transfer_active = True
                self._file_name = filename
                self._file_size = file_size
                self._file_data = bytearray()
                self._bytes_received = 0
                
                print(f"Starting file transfer: {filename} ({file_size} bytes)")
                
        elif cmd == 0x02:
            if self._file_transfer_active:
                print(f"File transfer complete: {self._file_name} ({self._bytes_received} bytes)")
                
                try:
                    with open(self._file_name, 'wb') as f:
                        f.write(self._file_data)
                    print(f"File saved: {self._file_name}")
                    self._ble.gatts_write(self._file_control_handle, bytes([0x01]))
                except Exception as e:
                    print(f"Error saving file: {e}")
                    self._ble.gatts_write(self._file_control_handle, bytes([0x00]))
                
                self._file_transfer_active = False
                self._file_name = None
                self._file_data = bytearray()
                self._file_size = 0
                self._bytes_received = 0
                
        elif cmd == 0x03:
            print("Restart command received - rebooting in 3 seconds...")
            import time
            import machine
            time.sleep(3)
            machine.reset()
    
    def _handle_file_chunk(self, data):
        if not self._file_transfer_active:
            return
        
        self._file_data.extend(data)
        self._bytes_received += len(data)
        
        progress = int((self._bytes_received / self._file_size) * 100) if self._file_size > 0 else 0
        self._ble.gatts_write(self._file_transfer_handle, struct.pack('<I', progress))
        
        if self._bytes_received % 1024 == 0:
            print(f"Received {self._bytes_received}/{self._file_size} bytes ({progress}%)")
    
    def update_flow_values(self):
        if not self._connections:
            return
        
        data = bytearray(32)
        for i in range(8):
            count = self._flow_meters.get_count(i)
            struct.pack_into('<I', data, i * 4, count)
        
        # Notify all connected clients
        for conn_handle in self._connections:
            try:
                self._ble.gatts_notify(conn_handle, self._flow_handle, data)
            except:
                pass
    
    def set_version_info(self, version):
        version_bytes = version.encode('utf-8')[:20]
        self._ble.gatts_write(self._version_handle, version_bytes)
