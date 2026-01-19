import network
import socket
from time import sleep, ticks_ms, ticks_diff
import machine
from machine import Pin
import urequests
import os

# VERSION - Update this when you make changes
VERSION = "1.0.0"

# GitHub settings
GITHUB_USER = "your-github-username"
GITHUB_REPO = "boat-monitor"
GITHUB_BRANCH = "main"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.txt"
CODE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/main.py"

# WiFi credentials
SSID = "Joes iPhone"
PASSWORD = "123456789"

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

# Setup GPIO pins for flow meters with pulse counters
flow_pins = []
pulse_counts = [0] * 8
last_pulse_time = [0] * 8
DEBOUNCE_MS = 50

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

# Connect to WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    sleep(2)
    
    print(f'Connecting to "{SSID}"...')
    wlan.connect(SSID, PASSWORD)
    
    max_wait = 30
    while max_wait > 0:
        status = wlan.status()
        if status < 0 or status >= 3:
            break
        max_wait -= 1
        print(f'Waiting for connection... (status: {status})')
        sleep(1)
    
    if wlan.status() != 3:
        print(f'\nConnection to "{SSID}" failed with status: {wlan.status()}')
        return None
    else:
        wlan.ifconfig((STATIC_IP, SUBNET, GATEWAY, DNS))
        
        print('\nConnected to WiFi!')
        status = wlan.ifconfig()
        print('IP address:', status[0])
        return status[0]

# Start Access Point mode
def start_ap_mode():
    print('\nStarting Access Point mode...')
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    ap.config(hostname=AP_HOSTNAME)
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
        # Download new code
        print(f"Downloading from {CODE_URL}")
        response = urequests.get(CODE_URL)
        new_code = response.text
        response.close()
        
        # Backup current version
        try:
            os.rename('main.py', 'main.py.bak')
        except:
            pass
        
        # Write new version
        with open('main.py', 'w') as f:
            f.write(new_code)
        
        print("Update downloaded successfully!")
        print("Rebooting in 3 seconds...")
        sleep(3)
        machine.reset()
        
    except Exception as e:
        print(f"Update failed: {e}")
        # Restore backup if update failed
        try:
            os.remove('main.py')
            os.rename('main.py.bak', 'main.py')
        except:
            pass
        return False

# HTML for the webpage
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
        .container {{ background-color: white; padding: 20px; border-radius: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .version {{ color: #999; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
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
            request = cl.recv(1024)
            
            response = get_html()
            cl.send('HTTP/1.1 200 OK\r\n')
            cl.send('Content-Type: text/html\r\n')
            cl.send('Connection: close\r\n\r\n')
            cl.sendall(response)
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
