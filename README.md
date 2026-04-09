# Ballast Monitor
Version: 4-5-2026-v1.0

Monitor ballast tank flow meters via Raspberry Pi Pico W.

## Files (upload all 6 to Pico)
1. main.py
2. main_wifi.py
3. ble_service.py
4. ble_advertising.py
5. flow_meters.py
6. config.py

## Switch Modes
Edit `config.py`:
- `MODE = "wifi"` - Web interface for testing
- `MODE = "ble"` - Bluetooth for boat/iPhone

## Features
- 8 flow meter channels (GP0-GP7)
- Tank pairs: Port, Starboard, Mid, Forward
- Pump failure alerts
- Gallons/Pounds toggle
- Calibration ("Set Full" buttons)
