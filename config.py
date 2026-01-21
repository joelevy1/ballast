# config.py - Default configuration (updated from GitHub)

# Default WiFi networks
DEFAULT_WIFI_NETWORKS = [
    ["Joes iPhone", "123456789"],
]

# Fallback AP settings
AP_SSID = "ballast"
AP_PASSWORD = "ballast123"
AP_HOSTNAME = "ballast"

# Static IP configuration for iPhone hotspot
STATIC_IP = '172.20.10.5'
SUBNET = '255.255.255.240'
GATEWAY = '172.20.10.1'
DNS = '8.8.8.8'

# AP mode IP (when acting as hotspot)
AP_IP = '192.168.4.1'
AP_SUBNET = '255.255.255.0'
AP_GATEWAY = '192.168.4.1'

# GitHub settings
GITHUB_USER = "joelevy1"
GITHUB_REPO = "ballast"
GITHUB_BRANCH = "main"

# Flow meter settings
DEBOUNCE_MS = 50
