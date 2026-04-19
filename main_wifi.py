"""
Ballast Flow Meter Monitor - WiFi Web Version v3.0
Features: Tank pair display, pump failure alerts, GitHub updates, calibration
"""

import network
import socket
from time import sleep, time
from flow_meters import FlowMeterManager
import json
import urequests
from config import *

try:
    from urllib.parse import quote_plus
except ImportError:
    def quote_plus(s):
        return str(s).replace(" ", "+")

# Global settings
settings = {
    "show_pounds": False,
    "calibration": [0] * 8,
    "pulses_per_gallon": PULSES_PER_GALLON
}

# Flow rate tracking for alerts
flow_history = {i: [] for i in range(8)}  # Last 5 seconds of flow data

# Load settings
def load_settings():
    global settings
    try:
        with open('ballast_settings.json', 'r') as f:
            settings = json.load(f)
        print("Loaded saved settings")
    except:
        print("No saved settings, using defaults")
        save_settings()

def save_settings():
    try:
        with open('ballast_settings.json', 'w') as f:
            json.dump(settings, f)
        print("Settings saved")
    except Exception as e:
        print(f"Error saving settings: {e}")

# Initialize
load_settings()
flow_manager = FlowMeterManager()
last_counts = [0] * 8
last_check_time = time()

# Connect to WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    try:
        hn = DHCP_HOSTNAME
    except NameError:
        hn = "Ballast-Monitor"
    try:
        wlan.config(dhcp_hostname=hn)
        print("DHCP hostname:", hn)
    except Exception as e:
        print("dhcp_hostname not set:", e)

    for network_config in WIFI_NETWORKS:
        ssid = network_config["ssid"]
        password = network_config["password"]
        
        print(f'Trying {ssid}...')
        wlan.connect(ssid, password)
        
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            sleep(1)
        
        if wlan.status() == 3:
            status = wlan.ifconfig()
            print(f'Connected to {ssid}! IP: {status[0]}')
            return status[0]
    
    raise RuntimeError('WiFi connection failed')

# Update flow rate history
def update_flow_history():
    global last_counts, last_check_time
    
    current_time = time()
    time_diff = current_time - last_check_time
    
    if time_diff >= 1.0:  # Update every second
        counts = flow_manager.get_all_pulse_counts()
        
        for i in range(8):
            pulses_per_sec = (counts[i] - last_counts[i]) / time_diff
            gallons_per_min = (pulses_per_sec * 60) / settings["pulses_per_gallon"]
            
            # Keep last 5 seconds
            flow_history[i].append(gallons_per_min)
            if len(flow_history[i]) > 5:
                flow_history[i].pop(0)
        
        last_counts = counts.copy()
        last_check_time = current_time

# Check for pump failures
def check_pump_failures():
    alerts = []
    
    for tank_name, tank_info in TANK_CONFIG.items():
        meters = tank_info["meters"]
        
        if len(flow_history[meters[0]]) >= 5 and len(flow_history[meters[1]]) >= 5:
            # Average flow rate over last 5 seconds
            pump1_flow = sum(flow_history[meters[0]]) / len(flow_history[meters[0]])
            pump2_flow = sum(flow_history[meters[1]]) / len(flow_history[meters[1]])
            
            # Check if one pump running but not the other
            pump1_running = pump1_flow > MIN_FLOW_RATE
            pump2_running = pump2_flow > MIN_FLOW_RATE
            
            if pump1_running and not pump2_running:
                alerts.append(f"{tank_name} Tank: Only pump 1 running!")
            elif pump2_running and not pump1_running:
                alerts.append(f"{tank_name} Tank: Only pump 2 running!")
    
    return alerts

# Check GitHub for updates
def check_github_updates():
    updates_available = []
    
    try:
        for filename in UPDATE_FILES:
            url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
            
            try:
                response = urequests.get(url, timeout=5)
                if response.status_code == 200:
                    remote_content = response.text
                    
                    # Try to read local file
                    try:
                        with open(filename, 'r') as f:
                            local_content = f.read()
                        
                        if remote_content != local_content:
                            updates_available.append(filename)
                    except:
                        # File doesn't exist locally
                        updates_available.append(filename)
                
                response.close()
            except Exception as e:
                print(f"Error checking {filename}: {e}")
        
    except Exception as e:
        print(f"GitHub check failed: {e}")
    
    return updates_available

# Download and install updates
def install_github_updates(files):
    results = []
    
    for filename in files:
        url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{filename}"
        
        try:
            response = urequests.get(url, timeout=10)
            if response.status_code == 200:
                with open(filename, 'w') as f:
                    f.write(response.text)
                results.append(f"OK {filename}")
            else:
                results.append(f"FAIL {filename} (HTTP {response.status_code})")
            response.close()
        except Exception as e:
            results.append(f"FAIL {filename} ({str(e)})")
    
    return results

def _version_line_for_file(filename):
    try:
        with open(filename, "r") as f:
            for line in f:
                if "Version:" in line:
                    return line.split("Version:", 1)[1].strip().strip('"').strip("'")
    except:
        pass
    return "unknown"

def build_file_versions():
    out = {}
    for fn in ["main.py", "main_wifi.py", "flow_meters.py", "ble_service.py", "ble_advertising.py", "config.py"]:
        out[fn] = _version_line_for_file(fn)
    return out

# Generate HTML
def get_html():
    update_flow_history()
    counts = flow_manager.get_all_pulse_counts()
    alerts = check_pump_failures()
    
    # Alert banner
    alert_html = ""
    if alerts:
        alert_list = "<br>".join(f"WARNING: {alert}" for alert in alerts)
        alert_html = f'''
        <div class="alert-banner">
            {alert_list}
        </div>
        '''
    
    # Build tank cards
    tank_cards = ""
    total_gallons = 0
    
    for tank_name, tank_info in TANK_CONFIG.items():
        meters = tank_info["meters"]
        names = tank_info["names"]
        
        # Calculate values for both pumps
        pump_data = []
        tank_total = 0
        
        for i, meter_idx in enumerate(meters):
            pulses = counts[meter_idx]
            gallons = pulses / settings["pulses_per_gallon"]
            tank_total += gallons
            
            # Get flow rate for status
            if len(flow_history[meter_idx]) > 0:
                flow_rate = sum(flow_history[meter_idx]) / len(flow_history[meter_idx])
                is_running = flow_rate > MIN_FLOW_RATE
            else:
                is_running = False
            
            # Display value
            if settings["show_pounds"]:
                display_val = f"{gallons * LBS_PER_GALLON:.1f} lbs"
            else:
                display_val = f"{gallons:.1f} gal"
            
            status = "RUNNING" if is_running else "STOPPED"
            status_class = "running" if is_running else "stopped"
            
            pump_data.append({
                "name": names[i],
                "value": display_val,
                "status": status,
                "status_class": status_class,
                "meter_idx": meter_idx
            })
        
        total_gallons += tank_total
        
        # Calculate tank percentage
        max_pulses = max(settings["calibration"][meters[0]], settings["calibration"][meters[1]])
        if max_pulses > 0:
            tank_pulses = counts[meters[0]] + counts[meters[1]]
            percent = min(100, (tank_pulses / (max_pulses * 2)) * 100)
        else:
            percent = 0
        
        # Display tank total
        if settings["show_pounds"]:
            tank_display = f"{tank_total * LBS_PER_GALLON:.1f} lbs"
        else:
            tank_display = f"{tank_total:.1f} gal"
        
        # Build pump rows
        pump_rows = ""
        for pump in pump_data:
            pump_rows += f'''
            <tr>
                <td>{pump["name"]}</td>
                <td class="{pump["status_class"]}">{pump["status"]} {pump["value"]}</td>
                <td>
                    <form method="POST" action="/reset" style="display:inline;">
                        <input type="hidden" name="meter" value="{pump["meter_idx"]}">
                        <button type="submit" class="btn-small">Reset</button>
                    </form>
                </td>
            </tr>
            '''
        
        tank_cards += f'''
        <div class="tank-card">
            <div class="tank-header">
                <h3>{tank_name} Tank</h3>
                <div class="tank-total">{tank_display} ({percent:.0f}%)</div>
            </div>
            <table class="pump-table">
                {pump_rows}
            </table>
        </div>
        '''
    
    # Total display
    if settings["show_pounds"]:
        total_display = f"{total_gallons * LBS_PER_GALLON:.1f} lbs"
    else:
        total_display = f"{total_gallons:.1f} gal"
    
    units_btn_text = "Show Gallons" if settings["show_pounds"] else "Show Pounds"
    fv = build_file_versions()

    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Ballast Monitor v{VERSION}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="2">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: #1a1a1a;
            color: #fff;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 32px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .alert-banner {{
            background: #ff3b30;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: bold;
            font-size: 18px;
            text-align: center;
            animation: pulse 1s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.8; }}
        }}
        .controls {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .total {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }}
        .tank-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .tank-card {{
            background: #2a2a2a;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }}
        .tank-header {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            padding: 20px;
            color: white;
        }}
        .tank-header h3 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        .tank-total {{
            font-size: 20px;
            opacity: 0.9;
        }}
        .pump-table {{
            width: 100%;
        }}
        .pump-table td {{
            padding: 15px 20px;
            border-bottom: 1px solid #3a3a3a;
        }}
        .pump-table tr:last-child td {{
            border-bottom: none;
        }}
        .running {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .stopped {{
            color: #666;
        }}
        button {{
            background: #2196F3;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
        }}
        button:hover {{
            background: #0b7dda;
        }}
        .btn-small {{
            padding: 6px 12px;
            font-size: 14px;
        }}
        .btn-units {{
            background: #ff9800;
        }}
        .btn-units:hover {{
            background: #e68900;
        }}
        .btn-danger {{
            background: #f44336;
        }}
        .btn-danger:hover {{
            background: #da190b;
        }}
        .btn-update {{
            background: #9c27b0;
        }}
        .btn-update:hover {{
            background: #7b1fa2;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Ballast Monitor</h1>
        
        {alert_html}
        
        <div class="controls">
            <form method="POST" action="/toggle_units">
                <button type="submit" class="btn-units">{units_btn_text}</button>
            </form>
            <form method="POST" action="/reset_all">
                <button type="submit" class="btn-danger">Reset All</button>
            </form>
            <form method="POST" action="/check_updates">
                <button type="submit" class="btn-update">Check for Updates</button>
            </form>
        </div>
        
        <div class="total">
            Total Water: {total_display}
        </div>
        
        <div class="tank-grid">
            {tank_cards}
        </div>
        
        <div class="footer">
            <strong>System Version: {VERSION}</strong><br>
            Pulses/Gal: {settings["pulses_per_gallon"]} | Auto-refresh: 2s<br>
            <details style="margin-top: 10px;">
                <summary style="cursor: pointer; color: #2196F3;">File Versions</summary>
                <div style="margin-top: 10px; font-family: monospace; font-size: 12px;">
                    main_wifi.py: {fv.get("main_wifi.py", "unknown")}<br>
                    flow_meters.py: {fv.get("flow_meters.py", "unknown")}<br>
                    ble_service.py: {fv.get("ble_service.py", "unknown")}<br>
                    ble_advertising.py: {fv.get("ble_advertising.py", "unknown")}<br>
                    config.py: {fv.get("config.py", "unknown")}
                </div>
            </details>
        </div>
    </div>
</body>
</html>
'''
    return html

# Parse POST data
def parse_post(data):
    params = {}
    try:
        pairs = data.split('&')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
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
    
    print(f'\n{"=" * 60}')
    print(f'Web server running!')
    print(f'Open: http://{ip}')
    print(f'{"=" * 60}\n')
    
    while True:
        try:
            cl, addr = s.accept()
            request = cl.recv(2048).decode('utf-8')
            
            lines = request.split('\r\n')
            if len(lines) > 0:
                request_line = lines[0]
                parts = request_line.split(' ')
                if len(parts) >= 2:
                    method = parts[0]
                    path = parts[1]
                    
                    if path == '/' or path.startswith('/?'):
                        response = get_html()
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n')
                        cl.sendall(response)
                    
                    elif path == '/toggle_units' and method == 'POST':
                        settings["show_pounds"] = not settings["show_pounds"]
                        save_settings()
                        cl.send('HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n')
                    
                    elif path == '/reset' and method == 'POST':
                        post_data = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else ''
                        params = parse_post(post_data)
                        if 'meter' in params:
                            meter = int(params['meter'])
                            flow_manager.reset_counter(meter)
                        cl.send('HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n')
                    
                    elif path == '/reset_all' and method == 'POST':
                        flow_manager.reset_all_counters()
                        cl.send('HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n')
                    
                    elif path == '/check_updates' and method == 'POST':
                        updates = check_github_updates()
                        if updates:
                            response = f'''<!DOCTYPE html>
<html><head><title>Updates Available</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; padding: 20px; background: #1a1a1a; color: #fff;">
<h2>Updates Available</h2>
<p>Files to update: {', '.join(updates)}</p>
<form method="POST" action="/install_updates">
<input type="hidden" name="files" value="{','.join(updates)}">
<button style="background:#4CAF50; color:white; border:none; padding:15px 30px; font-size:18px; border-radius:8px; cursor:pointer;">Install Updates</button>
</form>
<br><a href="/" style="color:#2196F3;">Back</a>
</body></html>'''
                        else:
                            response = '''<!DOCTYPE html>
<html><head><title>No Updates</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: Arial; padding: 20px; background: #1a1a1a; color: #fff;">
<h2>No Updates Available</h2>
<p>All files are up to date!</p>
<br><a href="/" style="color:#2196F3;">Back</a>
</body></html>'''
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n')
                        cl.sendall(response)
                    
                    elif path == '/install_updates' and method == 'POST':
                        post_data = request.split('\r\n\r\n')[1] if '\r\n\r\n' in request else ''
                        params = parse_post(post_data)
                        if 'files' in params:
                            files = params['files'].split(',')
                            results = install_github_updates(files)
                            result_html = '<br>'.join(results)
                            response = f'''<!DOCTYPE html>
<html><head><title>Update Complete</title><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="3;url=/" /></head>
<body style="font-family: Arial; padding: 20px; background: #1a1a1a; color: #fff;">
<h2>Update Results</h2>
<p>{result_html}</p>
<p><strong>Restarting in 3 seconds...</strong></p>
</body></html>'''
                            cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n')
                            cl.sendall(response)
                            cl.close()
                            # Auto-restart after sending response
                            import machine
                            sleep(3)
                            machine.reset()
                        else:
                            response = '<html><body>Error</body></html>'
                            cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n')
                            cl.sendall(response)
                    
                    elif path == '/api/pulses' and method == 'GET':
                        update_flow_history()
                        counts = flow_manager.get_all_pulse_counts()
                        body = json.dumps({"pulses": counts})
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n')
                        cl.sendall(body.encode('utf-8'))
                    
                    elif path == '/api/info' and method == 'GET':
                        update_flow_history()
                        counts = flow_manager.get_all_pulse_counts()
                        body = json.dumps({
                            "version": VERSION,
                            "ip": ip,
                            "pulses": counts,
                            "files": build_file_versions(),
                        })
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n')
                        cl.sendall(body.encode('utf-8'))
                    
                    elif path == '/reboot_to_ble' and method == 'POST':
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nOK')
                        cl.close()
                        import machine
                        sleep(0.3)
                        machine.reset()
                    
                    else:
                        cl.send('HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n')
            
            cl.close()
            
        except Exception as e:
            print(f'Error: {e}')
            try:
                cl.close()
            except:
                pass

def notify_wifi_ip(ip_addr):
    msg = "Ballast WiFi " + str(ip_addr) + " — open http://" + str(ip_addr) + "/ (v" + VERSION + ")"
    title = "Ballast Monitor"

    try:
        topic = NTFY_TOPIC
    except NameError:
        topic = ""
    if topic:
        try:
            url = "https://ntfy.sh/" + topic
            r = urequests.post(url, data=msg.encode("utf-8"), timeout=10)
            r.close()
            print("ntfy notification sent")
        except Exception as e:
            print("ntfy notify failed:", e)

    try:
        uk = PUSHOVER_USER_KEY
        at = PUSHOVER_APP_TOKEN
    except NameError:
        uk = ""
        at = ""
    if uk and at:
        try:
            body = (
                "token="
                + quote_plus(at)
                + "&user="
                + quote_plus(uk)
                + "&title="
                + quote_plus(title)
                + "&message="
                + quote_plus(msg)
            )
            r = urequests.post(
                "https://api.pushover.net/1/messages.json",
                data=body.encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=12,
            )
            r.close()
            print("Pushover notification sent")
        except Exception as e:
            print("Pushover notify failed:", e)

def run():
    print(f"\nBallast Monitor v{VERSION} - WiFi Mode")
    print("=" * 60)
    ip = connect_wifi()
    notify_wifi_ip(ip)
    start_server(ip)

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
