import network
import socket
from time import sleep, ticks_ms, ticks_diff
import machine
from machine import Pin
import urequests
import os
import json

# VERSION - Update this when you make changes
VERSION = "1.0.1"

# Import config
try:
    from config import *
except:
    print("Error loading config.py, using defaults")
    WIFI_NETWORKS = []
    AP_SSID = "ballast"
    AP_PASSWORD = "ballast123"
    STATIC_IP = '172.20.10.5'
    SUBNET = '255.255.255.240'
    GATEWAY = '172.20.10.1'
    DNS = '8.8.8.8'
    AP_IP = '192.168.4.1'
    AP_SUBNET = '255.255.255.0'
    AP_GATEWAY = '192.168.4.1'
    GITHUB_USER = "joelevy1"
    GITHUB_REPO = "ballast"
    GITHUB_BRANCH = "main"
    DEBOUNCE_MS = 50

# GitHub URLs
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.txt"
CODE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/main.py"
CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/config.py"

# Setup GPIO pins for flow meters with pulse counters
flow_pins = []
pulse_counts = [0] * 8
last_pulse_time = [0] * 8

# Interrupt handlers for each pin with debouncing
def make_counter(pin_num):
    def counter(pin):
        global pulse_counts, last_pulse_time
        current_time = ticks_ms()
        
        if ticks_diff(current_time, last_pulse_time[pin_num]) > DEBOUNCE_MS:
            pulse_counts[pin_num] += 1
            last_pulse_time[pin_num] = current_time
    return counter

# Setup pins with interrupts
for i in range(8):
    pin = Pin(i, Pin.IN, Pin.PULL_UP)
    pin.irq(trigger=Pin.IRQ_FALLING, handler=make_counter(i))
    flow_pins.append(pin)

print(f"Boat Monitor v{VERSION}")
print("Pulse counters initialized with debouncing")

# Save config to file
def save_config():
    try:
        config_content = f"""# config.py - WiFi configuration storage

# List of WiFi networks to try (in order)
# Format: [SSID, PASSWORD]
WIFI_NETWORKS = {WIFI_NETWORKS}

# Fallback AP settings
AP_SSID = "{AP_SSID}"
AP_PASSWORD = "{AP_PASSWORD}"
AP_HOSTNAME = "{AP_HOSTNAME}"

# Static IP configuration for iPhone hotspot
STATIC_IP = '{STATIC_IP}'
SUBNET = '{SUBNET}'
GATEWAY = '{GATEWAY}'
DNS = '{DNS}'

# AP mode IP (when acting as hotspot)
AP_IP = '{AP_IP}'
AP_SUBNET = '{AP_SUBNET}'
AP_GATEWAY = '{AP_GATEWAY}'

# GitHub settings
GITHUB_USER = "{GITHUB_USER}"
GITHUB_REPO = "{GITHUB_REPO}"
GITHUB_BRANCH = "{GITHUB_BRANCH}"

# Flow meter settings
DEBOUNCE_MS = {DEBOUNCE_MS}
"""
        with open('config.py', 'w') as f:
            f.write(config_content)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Connect to WiFi - try all networks in order
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    sleep(2)
    
    # Try each network in the list
    for ssid, password in WIFI_NETWORKS:
        print(f'Trying to connect to "{ssid}"...')
        wlan.connect(ssid, password)
        
        max_wait = 15
        while max_wait > 0:
            status = wlan.status()
            if status < 0 or status >= 3:
                break
            max_wait -= 1
            print(f'Waiting for connection... (status: {status})')
            sleep(1)
        
        if wlan.status() == 3:
            wlan.ifconfig((STATIC_IP, SUBNET, GATEWAY, DNS))
            print(f'\nConnected to "{ssid}"!')
            status = wlan.ifconfig()
            print('IP address:', status[0])
            return status[0]
        else:
            print(f'Failed to connect to "{ssid}"')
    
    print('\nAll WiFi networks failed')
    return None

# Start Access Point mode
def start_ap_mode():
    print('\nStarting Access Point mode...')
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    try:
        ap.config(hostname=AP_HOSTNAME)
    except:
        pass
    ap.ifconfig((AP_IP, AP_SUBNET, AP_GATEWAY, AP_GATEWAY))
    
    while not ap.active():
        sleep(0.1)
    
    print(f'Access Point "{AP_SSID}" active')
    print(f'Connect to SSID: {AP_SSID}')
    print(f'Password: {AP_PASSWORD}')
    print(f'Then access: http://{AP_IP}')
    
    return AP_IP

# Check for updates
def check_for_updates():
    try:
        print("Checking for updates...")
        response = urequests.get(VERSION_URL)
        latest_version = response.text.strip()
        response.close()
        
        print(f"Current version: {VERSION}")
        print(f"Latest version: {latest_version}")
        
        if latest_version != VERSION:
            print("New version available! Downloading...")
            return download_update()
        else:
            print("Already on latest version")
            return False
            
    except Exception as e:
        print(f"Update check failed: {e}")
        return False

# Download and install update
def download_update():
    try:
        # Download new main.py
        print(f"Downloading main.py from {CODE_URL}")
        response = urequests.get(CODE_URL)
        new_code = response.text
        response.close()
        
        # Download new config.py
        print(f"Downloading config.py from {CONFIG_URL}")
        response = urequests.get(CONFIG_URL)
        new_config = response.text
        response.close()
        
        # Backup current versions
        try:
            os.rename('main.py', 'main.py.bak')
        except:
            pass
        try:
            os.rename('config.py', 'config.py.bak')
        except:
            pass
        
        # Write new versions
        with open('main.py', 'w') as f:
            f.write(new_code)
        with open('config.py', 'w') as f:
            f.write(new_config)
        
        print("Update downloaded successfully!")
        print("Rebooting in 3 seconds...")
        sleep(3)
        machine.reset()
        
    except Exception as e:
        print(f"Update failed: {e}")
        # Restore backups if update failed
        try:
            os.remove('main.py')
            os.rename('main.py.bak', 'main.py')
        except:
            pass
        try:
            os.remove('config.py')
            os.rename('config.py.bak', 'config.py')
        except:
            pass
        return False

# HTML for the main webpage
def get_html():
    pin_states = ""
    for i in range(8):
        state = flow_pins[i].value()
        status_text = "HIGH" if state == 1 else "LOW"
        color = "#00ff00" if state == 1 else "#ff0000"
        pin_states += f'''<tr>
            <td>Flow Meter {i+1} (GP{i})</td>
            <td><span style="color: {color}; font-weight: bold;">{status_text}</span></td>
            <td style="font-weight: bold; font-size: 18px;">{pulse_counts[i]}</td>
        </tr>\n'''
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Boat Monitor v{VERSION}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="2">
    <style>
        body {{ font-family: Arial; margin: 20px; background-color: #f0f0f0; }}
        h1 {{ color: #333; }}
        .container {{ background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .version {{ color: #999; font-size: 12px; margin-top: 20px; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }}
        .nav a:hover {{ background-color: #45a049; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/wifi">WiFi Settings</a>
    </div>
    <div class="container">
        <h1>Boat Flow Meter Monitor</h1>
        <table>
            <tr>
                <th>Flow Meter</th>
                <th>Status</th>
                <th>Total Pulses</th>
            </tr>
            {pin_states}
        </table>
        <p style="color: #666; font-size: 12px; margin-top: 20px;">Page auto-refreshes every 2 seconds</p>
        <p class="version">Version {VERSION}</p>
    </div>
</body>
</html>
"""
    return html

# HTML for WiFi settings page
def get_wifi_html():
    networks_html = ""
    for i, (ssid, password) in enumerate(WIFI_NETWORKS):
        networks_html += f'''<tr>
            <td>{i+1}</td>
            <td>{ssid}</td>
            <td>{'*' * len(password)}</td>
            <td>
                <form method="POST" action="/wifi/delete" style="display:inline;">
                    <input type="hidden" name="index" value="{i}">
                    <button type="submit" style="background-color: #f44336; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 3px;">Delete</button>
                </form>
            </td>
        </tr>\n'''
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>WiFi Settings - Boat Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial; margin: 20px; background-color: #f0f0f0; }}
        h1, h2 {{ color: #333; }}
        .container {{ background-color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .nav {{ margin-bottom: 20px; }}
        .nav a {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }}
        .nav a:hover {{ background-color: #45a049; }}
        input[type="text"], input[type="password"] {{ width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }}
        button {{ background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; border-radius: 5px; }}
        button:hover {{ background-color: #45a049; }}
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/wifi">WiFi Settings</a>
    </div>
    <div class="container">
        <h1>WiFi Network Settings</h1>
        <h2>Current Networks</h2>
        <table>
            <tr>
                <th>Priority</th>
                <th>SSID</th>
                <th>Password</th>
                <th>Action</th>
            </tr>
            {networks_html}
        </table>
    </div>
    <div class="container">
        <h2>Add New Network</h2>
        <form method="POST" action="/wifi/add">
            <label>SSID:</label><br>
            <input type="text" name="ssid" required><br><br>
            <label>Password:</label><br>
            <input type="password" name="password" required><br><br>
            <button type="submit">Add Network</button>
        </form>
    </div>
    <div class="container">
        <form method="POST" action="/reboot">
            <button type="submit" style="background-color: #ff9800;">Reboot Device</button>
        </form>
    </div>
</body>
</html>
"""
    return html

# Parse POST data
def parse_post_data(data):
    params = {}
    try:
        pairs = data.decode('utf-8').split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                # URL decode
                value = value.replace('+', ' ')
                params[key] = value
    except:
        pass
    return params

# Start web server
def start_server(ip):
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(1)
    
    print(f'\nWeb server running on http://{ip}')
    print('=' * 50)
    
    while True:
        try:
            cl, addr = s.accept()
            print('Client connected from', addr)
            request = cl.recv(2048).decode('utf-8')
            
            # Parse request
            lines = request.split('\r\n')
            if len(lines) > 0:
                request_line = lines[0]
                parts = request_line.split(' ')
                if len(parts) >= 2:
                    method = parts[0]
                    path = parts[1]
                    
                    print(f"Request: {method} {path}")
                    
                    # Handle different routes
                    if path == '/' or path.startswith('/?'):
                        response = get_html()
                        cl.send('HTTP/1.1 200 OK\r\n')
                        cl.send('Content-Type: text/html\r\n')
                        cl.send('Connection: close\r\n\r\n')
                        cl.sendall(response)
                    
                    elif path == '/wifi':
                        response = get_wifi_html()
                        cl.send('HTTP/1.1 200 OK\r\n')
                        cl.send('Content-Type: text/html\r\n')
                        cl.send('Connection: close\r\n\r\n')
                        cl.sendall(response)
                    
                    elif path == '/wifi/add' and method == 'POST':
                        # Get POST data
                        post_data = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else ''
                        params = parse_post_data(post_data.encode())
                        
                        if 'ssid' in params and 'password' in params:
                            WIFI_NETWORKS.append([params['ssid'], params['password']])
                            save_config()
                            print(f"Added network: {params['ssid']}")
                        
                        # Redirect to wifi page
                        cl.send('HTTP/1.1 303 See Other\r\n')
                        cl.send('Location: /wifi\r\n')
                        cl.send('Connection: close\r\n\r\n')
                    
                    elif path == '/wifi/delete' and method == 'POST':
                        # Get POST data
                        post_data = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else ''
                        params = parse_post_data(post_data.encode())
                        
                        if 'index' in params:
                            try:
                                index = int(params['index'])
                                if 0 <= index < len(WIFI_NETWORKS):
                                    removed = WIFI_NETWORKS.pop(index)
                                    save_config()
                                    print(f"Removed network: {removed[0]}")
                            except:
                                pass
                        
                        # Redirect to wifi page
                        cl.send('HTTP/1.1 303 See Other\r\n')
                        cl.send('Location: /wifi\r\n')
                        cl.send('Connection: close\r\n\r\n')
                    
                    elif path == '/reboot' and method == 'POST':
                        cl.send('HTTP/1.1 200 OK\r\n')
                        cl.send('Content-Type: text/html\r\n')
                        cl.send('Connection: close\r\n\r\n')
                        cl.sendall('<html><body><h1>Rebooting...</h1><p>Please wait 10 seconds then refresh.</p></body></html>')
                        cl.close()
                        sleep(2)
                        machine.reset()
                    
                    else:
                        cl.send('HTTP/1.1 404 Not Found\r\n')
                        cl.send('Connection: close\r\n\r\n')
            
            cl.close()
            
        except Exception as e:
            print('Error:', e)
            try:
                cl.close()
            except:
                pass

# Main execution
try:
    # Try to connect to WiFi first
    ip = connect_wifi()
    
    # If connection failed, start AP mode
    if ip is None:
        print('\nFalling back to Access Point mode')
        ip = start_ap_mode()
    else:
        # Only check for updates if connected to internet (not in AP mode)
        check_for_updates()
    
    start_server(ip)
    
except Exception as e:
    print('Failed to start:', e)
    sleep(5)
    machine.reset()
