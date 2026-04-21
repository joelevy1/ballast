"""
BLE Advertising Helper
Version: 4-19-2026-v1.3
"""

import bluetooth
import struct
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    """Generate BLE advertising payload"""
    payload = bytearray()
    
    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack('BB', len(value) + 1, adv_type) + value
    
    _append(0x01, struct.pack('B', (0x01 if limited_disc else 0x02) + (0x00 if br_edr else 0x04)))
    
    if name:
        _append(0x09, name.encode())
    
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(0x03, b)
            elif len(b) == 4:
                _append(0x05, b)
            elif len(b) == 16:
                _append(0x07, b)
    
    if appearance:
        _append(0x19, struct.pack('<H', appearance))
    
    return payload

class BLEAdvertising:
    def __init__(self, ble, name="Ballast Monitor"):
        self._ble = ble
        self._name = name
        self._payload = None
        
    def start_advertising(self, services=None):
        """Start BLE advertising"""
        self._payload = advertising_payload(
            name=self._name,
            services=services
        )
        self._ble.gap_advertise(100000, adv_data=self._payload)
        print(f"BLE advertising as '{self._name}'")
        print(f"BLE advertising started (v4-18-2026-v1.2)")
    
    def stop_advertising(self):
        """Stop BLE advertising"""
        self._ble.gap_advertise(None)
        print("BLE advertising stopped")
