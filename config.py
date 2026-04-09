"""
Ballast Monitor Configuration
Modify these settings as needed
"""

# WiFi Networks (tried in order)
WIFI_NETWORKS = [
    {"ssid": "Levy-Guest", "password": "welcomehome"},
    {"ssid": "Levy2.4", "password": "@Sonoma4real"}
]

# GitHub repository for firmware updates
GITHUB_REPO = "joelevy1/ballast"
GITHUB_BRANCH = "main"

# Files to check for updates (relative to repo root)
# DISABLED - Line ending issues with GitHub uploads
# Update files manually via Thonny when needed
UPDATE_FILES = []

# Flow meter calibration
# Set this after running 1 gallon through a meter and counting pulses
PULSES_PER_GALLON = 450  # Default - UPDATE THIS after testing!

# Tank configuration
TANK_CONFIG = {
    "Port": {
        "meters": [1, 2],  # GP1=Port Top, GP2=Port Btm
        "names": ["Port Top (White)", "Port Btm (Green)"]
    },
    "Starboard": {
        "meters": [0, 3],  # GP0=Strb Top, GP3=Strb Btm
        "names": ["Strb Top (White)", "Strb Btm (Green)"]
    },
    "Mid": {
        "meters": [4, 5],  # GP4=Mid Port, GP5=Mid Strb
        "names": ["Mid Port (Blue)", "Mid Strb (Blue)"]
    },
    "Forward": {
        "meters": [6, 7],  # GP6=Fwd Port, GP7=Fwd Mid
        "names": ["Fwd Port (Yellow)", "Fwd Mid (Yellow)"]
    }
}

# Alert thresholds
PUMP_FAILURE_THRESHOLD = 5  # seconds - how long to check for flow difference
MIN_FLOW_RATE = 0.1  # gallons/min - minimum to consider pump "running"

# Water density
LBS_PER_GALLON = 8.34

# System info
VERSION = "4-5-2026-v1.0"

# Operating mode: "wifi" or "ble"
MODE = "wifi"  # Change to "ble" for Bluetooth mode

# File versions (update when modifying files)
FILE_VERSIONS = {
    "main.py": "4-5-2026-v1.0",
    "main_wifi.py": "4-5-2026-v1.0",
    "flow_meters.py": "4-5-2026-v1.0",
    "ble_service.py": "4-5-2026-v1.0",
    "ble_advertising.py": "4-5-2026-v1.0",
    "config.py": "4-5-2026-v1.0"
}
