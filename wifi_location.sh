#!/bin/bash

# Google Geolocation API Key - Replace with your actual API key
API_KEY="AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"

echo "=== Google WiFi Geolocation ==="

if [ "$API_KEY" = "YOUR_GOOGLE_GEOLOCATION_API_KEY" ]; then
    echo "ERROR: Please set your Google Geolocation API key in the script"
    echo "Get one from: https://developers.google.com/maps/documentation/geolocation/get-api-key"
    exit 1
fi

# Scan for WiFi networks
echo "Scanning WiFi networks..."
WIFI_SCAN=$(sudo iwlist wlan0 scan | grep -E "Address|ESSID|Signal level|Quality")

# Parse WiFi data and create JSON for Google API
echo "Parsing WiFi data..."

# Create temporary file for JSON payload
JSON_FILE=$(mktemp)

echo '{
  "considerIp": true,
  "wifiAccessPoints": [' > "$JSON_FILE"

# Extract WiFi access points (simplified parsing)
sudo iwlist wlan0 scan | awk '
BEGIN {
    first = 1
}
/Address/ {
    if (!first) print "    },"
    first = 0
    gsub(/.*Address: /, "", $0)
    printf "    {\n      \"macAddress\": \"%s\"", $0
}
/Signal level/ {
    gsub(/.*Signal level=/, "", $0)
    gsub(/ dBm.*/, "", $0)
    printf ",\n      \"signalStrength\": %d", $0
}
END {
    if (!first) print "\n    }"
}' >> "$JSON_FILE"

echo '
  ]
}' >> "$JSON_FILE"

echo "Sending request to Google Geolocation API..."

# Make API request
RESPONSE=$(curl -s -X POST \
  "https://www.googleapis.com/geolocation/v1/geolocate?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d @"$JSON_FILE")

# Clean up
rm "$JSON_FILE"

# Parse and display response
if command -v python3 &> /dev/null; then
    echo "Response:"
    echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'location' in data:
        lat = data['location']['lat']
        lng = data['location']['lng']
        accuracy = data.get('accuracy', 'unknown')
        print(f'Latitude: {lat}')
        print(f'Longitude: {lng}')
        print(f'Accuracy: {accuracy} meters')
        print(f'Google Maps: https://maps.google.com/maps?q={lat},{lng}')
    else:
        print('Error:', data)
except:
    print('Failed to parse response:', sys.stdin.read())
"
else
    echo "Raw response:"
    echo "$RESPONSE"
fi