"""
Ballast Flow Meter Monitor - Unified Entry Point
Switches between WiFi and BLE mode based on config.py
Version: 4-5-2026-v1.0
"""

from config import VERSION, FILE_VERSIONS, MODE

print(f"\nBallast Monitor v{VERSION}")
print("=" * 50)
print(f"Mode: {MODE.upper()}")
print("File Versions:")
for filename, version in FILE_VERSIONS.items():
    print(f"  {filename}: {version}")
print("=" * 50)

if MODE == "wifi":
    print("\nStarting WiFi mode...")
    print("Loading main_wifi module...")
    import main_wifi
    
elif MODE == "ble":
    print("\nStarting BLE mode...")
    from flow_meters import FlowMeterManager
    from ble_service import BallastBLEService
    from ble_advertising import start_advertising
    from time import sleep
    
    # Initialize flow meters
    print("Initializing flow meters...")
    flow_manager = FlowMeterManager()
    
    # Initialize BLE service
    print("Starting BLE service...")
    ble_service = BallastBLEService(flow_manager)
    
    # Start advertising
    print("BLE advertising as 'Ballast Monitor'")
    start_advertising()
    
    print("\nSystem ready!")
    print("Connect with BLE app")
    print("Device name: Ballast Monitor")
    print("=" * 50)
    print()
    
    # Main loop - update BLE when clients connected
    while True:
        if ble_service.is_connected():
            ble_service.update_flow_data()
        sleep(0.1)

else:
    print(f"\nERROR: Invalid MODE '{MODE}' in config.py")
    print("Valid options: 'wifi' or 'ble'")
