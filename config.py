"""
Configuration for Ballast Monitor
Version: 4-18-2026-v1.2
"""

# System version
VERSION = "4-18-2026-v1.2"

# Mode: "wifi" or "ble"
MODE = "ble"

# WiFi credentials
WIFI_SSID = "Levy-Guest"
WIFI_PASSWORD = "welcomehome"

# Backup WiFi
WIFI_SSID_BACKUP = "Levy2.4"
WIFI_PASSWORD_BACKUP = "@Sonoma4real"

# GitHub OTA update settings
GITHUB_USER = "joelevy1"
GITHUB_REPO = "ballast"
GITHUB_BRANCH = "main"

# Files to check for updates (only used in WiFi mode)
UPDATE_FILES = [
    "main.py",
    "main_wifi.py",
    "ble_service.py",
    "ble_advertising.py",
    "flow_meters.py",
    "config.py"
]

# Flow meter GPIO pins (GP0-GP7)
FLOW_METER_PINS = [0, 1, 2, 3, 4, 5, 6, 7]

# Tank configuration
# Each tank has two pumps (top and bottom)
TANKS = {
    'port': {
        'pumps': [1, 2],  # GP1 (Top White), GP2 (Bottom Green)
        'name': 'Port Tank'
    },
    'starboard': {
        'pumps': [0, 3],  # GP0 (Top White), GP3 (Bottom Green)
        'name': 'Starboard Tank'
    },
    'mid': {
        'pumps': [4, 5],  # GP4 (Port Blue), GP5 (Starboard Blue)
        'name': 'Mid Tank'
    },
    'forward': {
        'pumps': [6, 7],  # GP6 (Port Yellow), GP7 (Mid Yellow)
        'name': 'Forward Tank'
    }
}

# Flow meter calibration
PULSES_PER_GALLON = 450  # Estimated, needs physical calibration
POUNDS_PER_GALLON = 8.34

# BLE settings
BLE_DEVICE_NAME = "Ballast Monitor"
