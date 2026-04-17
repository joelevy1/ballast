"""
BLE Advertising Helper
Version: 4-5-2026-v1.0
"""

import bluetooth
import struct
from micropython import const

VERSION = "4-5-2026-v1.0"

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None):
    payload = bytearray()
    
    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack('BB', len(value) + 1, adv_type) + value
    
    # Flags
    _append(_ADV_TYPE_FLAGS, struct.pack('B', (0x01 if limited_disc else 0x06) + (0x00 if br_edr else 0x04)))
    
    # Name
    if name:
        _append(_ADV_TYPE_NAME, name.encode('utf-8'))
    
    # Services
    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
    
    return payload

def start_advertising(name="Ballast Monitor", interval_us=500000):
    import struct
    
    ble = bluetooth.BLE()
    ble.active(True)
    
    # Environmental Sensing service UUID
    services = [bluetooth.UUID(0x181A)]
    
    payload = advertising_payload(name=name, services=services)
    
    ble.gap_advertise(interval_us, adv_data=payload, connectable=True)
    
    print(f"BLE advertising started (v{VERSION})")
