"""
Ballast Monitor - Main Entry Point
Version: 4-18-2026-v1.2
Routes to WiFi or BLE mode based on config
"""

# One-shot WiFi session: BLE command 0x04 creates wifi_once.flag then reboots.
# Next boot runs main_wifi once; flag is removed so following boots use config.MODE (default "ble").
try:
    import os
    if "wifi_once.flag" in os.listdir():
        with open("wifi_once.flag", "r") as _wf:
            if _wf.read().strip() == "1":
                try:
                    os.remove("wifi_once.flag")
                except OSError:
                    pass
                print("One-shot WiFi boot (wifi_once.flag)")
                import main_wifi
                main_wifi.run()
except Exception as _e:
    print("wifi_once check:", _e)

import config

print(f"Ballast Monitor v{config.VERSION}")
print("=" * 50)
print(f"Mode: {config.MODE.upper()}")

# Print file versions
print("File Versions:")
for fname in ["ble_service.py", "main.py", "main_wifi.py", "config.py", "ble_advertising.py", "flow_meters.py"]:
    try:
        with open(fname, 'r') as f:
            for line in f:
                if 'Version:' in line:
                    version = line.split('Version:')[1].strip().strip('"\'')
                    print(f"  {fname}: {version}")
                    break
    except:
        print(f"  {fname}: Not found")

print("=" * 50)

# Route to appropriate mode
if config.MODE == "wifi":
    import main_wifi
    main_wifi.run()
elif config.MODE == "ble":
    import bluetooth
    from ble_service import BLEService
    from ble_advertising import BLEAdvertising
    from flow_meters import FlowMeters
    import time
    
    print("Starting BLE mode...")
    
    print("Initializing flow meters...")
    flow_meters = FlowMeters(config.FLOW_METER_PINS)
    
    print("Starting BLE service...")
    ble = bluetooth.BLE()
    ble.active(True)
    
    ble_service = BLEService(ble, flow_meters, config.VERSION)
    
    advertising = BLEAdvertising(ble, config.BLE_DEVICE_NAME)
    advertising.start_advertising(services=[bluetooth.UUID(0x181A)])
    
    print("System ready!")
    print("Connect with BLE app")
    print(f"Device name: {config.BLE_DEVICE_NAME}")
    print("=" * 50)
    
    while True:
        ble_service.update_flow_values()
        time.sleep_ms(100)
else:
    print(f"Unknown mode: {config.MODE}")
