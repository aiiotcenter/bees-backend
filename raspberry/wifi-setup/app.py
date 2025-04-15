# 📁 wifi-setup/app.py

from flask import Flask, render_template, request, redirect
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def index():
    # Get available Wi-Fi networks
    scan_output = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan']).decode()
    networks = []
    for line in scan_output.split('\n'):
        line = line.strip()
        if line.startswith('ESSID:'):
            ssid = line.split(':')[1].replace('"', '')
            if ssid and ssid not in networks:
                networks.append(ssid)
    return render_template('index.html', networks=networks)

@app.route('/connect', methods=['POST'])
def connect():
    ssid = request.form['ssid']
    password = request.form['password']

    # Write new Wi-Fi config
    config = f'''ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid=\"{ssid}\"
    psk=\"{password}\"
}}
'''

    with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
        f.write(config)

    # Restart networking
    os.system('sudo wpa_cli -i wlan0 reconfigure')
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)