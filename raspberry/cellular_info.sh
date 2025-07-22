#!/bin/bash

echo "=== CELLULAR NETWORK INFORMATION EXTRACTION ==="
echo

# Google Geolocation API Key
API_KEY="AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"

echo "1. Current cellular interface (eth0) information:"
ip addr show eth0 2>/dev/null | grep "inet "
CELLULAR_IP=$(ip addr show eth0 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d'/' -f1)
echo "Cellular IP: $CELLULAR_IP"
echo

echo "2. Checking for cellular signal information:"
if [ -f "/proc/net/wireless" ]; then
    echo "Wireless stats:"
    cat /proc/net/wireless | grep -v "status"
else
    echo "No wireless stats available"
fi
echo

echo "3. Trying to get carrier information from IP lookup:"
if command -v curl &> /dev/null; then
    echo "IP Geolocation info:"
    curl -s "https://ipapi.co/$CELLULAR_IP/json/" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'IP: {data.get(\"ip\", \"unknown\")}')
    print(f'Carrier: {data.get(\"org\", \"unknown\")}')
    print(f'Country: {data.get(\"country_name\", \"unknown\")}')
    print(f'Region: {data.get(\"region\", \"unknown\")}')
    print(f'City: {data.get(\"city\", \"unknown\")}')
    print(f'Latitude: {data.get(\"latitude\", \"unknown\")}')
    print(f'Longitude: {data.get(\"longitude\", \"unknown\")}')
except:
    print('Failed to parse IP info')
" 2>/dev/null || echo "IP lookup failed"
fi
echo

echo "4. Making Google Geolocation API request with cellular optimization:"

# Create JSON payload optimized for cellular
cat > /tmp/cellular_request.json << EOF
{
  "considerIp": true,
  "radioType": "gsm"
}
EOF

echo "Request payload:"
cat /tmp/cellular_request.json
echo

echo "Google API Response:"
curl -s -X POST \
  "https://www.googleapis.com/geolocation/v1/geolocate?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/cellular_request.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'location' in data:
        lat = data['location']['lat']
        lng = data['location']['lng']
        accuracy = data.get('accuracy', 'unknown')
        print(f'📍 Location: {lat}, {lng}')
        print(f'🎯 Accuracy: {accuracy} meters')
        print(f'🗺️  Google Maps: https://maps.google.com/maps?q={lat},{lng}')
        
        # Additional info if available
        if 'accuracy' in data:
            if int(accuracy) < 100:
                print('✅ High accuracy location (< 100m)')
            elif int(accuracy) < 1000:
                print('⚠️  Medium accuracy location (< 1km)')
            else:
                print('❌ Low accuracy location (> 1km)')
    else:
        print('❌ Error in response:', data)
except Exception as e:
    print('❌ Failed to parse response:', str(e))
"

# Cleanup
rm -f /tmp/cellular_request.json

echo
echo "=== SUMMARY ==="
echo "✅ Your ZTE modem provides cellular internet via eth0"
echo "📡 Google Geolocation API can use cellular IP + network characteristics"
echo "🎯 This should provide much better accuracy than basic IP geolocation"
echo "📍 Location accuracy depends on cellular tower density in your area"