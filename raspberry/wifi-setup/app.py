from flask import Flask, render_template, request, redirect, flash
import subprocess
import os
import logging

app = Flask(__name__)
app.secret_key = 'dux-secret-key'  # Needed for flashing messages

logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    # Get available Wi-Fi networks
    try:
        scan_output = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan']).decode()
        networks = []
        for line in scan_output.split('\n'):
            line = line.strip()
            if line.startswith('ESSID:'):
                ssid = line.split(':')[1].replace('"', '')
                if ssid and ssid not in networks:
                    networks.append(ssid)
        logging.info("🔍 Found networks: %s", networks)
        return render_template('index.html', networks=networks)
    except Exception as e:
        logging.error("❌ Error scanning networks: %s", e)
        return "Error scanning Wi-Fi networks."

@app.route('/connect', methods=['POST'])
def connect():
    ssid = request.form.get('ssid')
    password = request.form.get('password')

    logging.info("📡 Received connection request to SSID: %s", ssid)

    if not ssid or not password:
        logging.warning("⚠️ Missing SSID or password")
        flash("SSID or password missing. Please try again.")
        return redirect('/')

    config = f'''ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

network={{
    ssid="{ssid}"
    psk="{password}"
}}
'''

    try:
        with open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w') as f:
            f.write(config)
        logging.info("✅ Wi-Fi config written successfully")
    except Exception as e:
        logging.error("❌ Failed to write Wi-Fi config: %s", e)
        flash("Failed to save Wi-Fi config.")
        return redirect('/')

    try:
        output = subprocess.check_output(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure']).decode()
        logging.info("🔁 Reconfigure output: %s", output)
        flash("Wi-Fi credentials applied! Pi will now try to connect.")
    except Exception as e:
        logging.error("❌ Reconfigure failed: %s", e)
        flash("Reconfigure failed. Please reboot manually.")

    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
