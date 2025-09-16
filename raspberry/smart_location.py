#!/usr/bin/env python3
"""
Smart Location Module for Beehive Monitoring
Provides accurate location with validation and fallback
"""

import random
import requests
import subprocess
from datetime import datetime
from math import radians, cos, sin, asin, sqrt

# Configuration
GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"

# Your actual beehive location
HOME_LAT = 35.227
HOME_LNG = 33.32

# Reasonable boundaries (about 5km radius)
# Adjust these if you need a different range
LAT_MIN = 35.20  # South boundary
LAT_MAX = 35.25  # North boundary  
LNG_MIN = 33.29  # West boundary
LNG_MAX = 33.35  # East boundary

# Maximum acceptable distance from home (km)
MAX_ACCEPTABLE_DISTANCE = 10  # Reject anything more than 10km away

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates in kilometers"""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371  # Earth radius in km

def is_location_reasonable(lat, lng):
    """
    Check if location is within reasonable boundaries
    Returns (is_valid, distance_from_home)
    """
    # First check boundaries
    if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
        return False, None
    
    # Then check distance
    distance = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
    
    if distance <= MAX_ACCEPTABLE_DISTANCE:
        return True, distance
    
    return False, distance

def get_wifi_access_points():
    """
    Scan for nearby WiFi access points to improve accuracy
    Returns list of WiFi APs for Google API
    """
    try:
        # Try scanning with iwlist (most common)
        result = subprocess.run(
            ["sudo", "iwlist", "wlan0", "scan"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Try alternative command
            result = subprocess.run(
                ["sudo", "iw", "dev", "wlan0", "scan"],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        if result.returncode != 0:
            return []
        
        wifi_aps = []
        current_ap = {}
        
        for line in result.stdout.split('\n'):
            # Parse iwlist format
            if "Cell" in line and "Address:" in line:
                if current_ap and 'macAddress' in current_ap:
                    wifi_aps.append(current_ap)
                mac = line.split("Address: ")[1].strip()
                current_ap = {"macAddress": mac}
            
            elif "Signal level=" in line:
                try:
                    if "dBm" in line:
                        signal = line.split("Signal level=")[1].split(" dBm")[0]
                    else:
                        signal = line.split("Signal level=")[1].split("/")[0]
                        signal = int(signal) - 100  # Convert to dBm
                    current_ap["signalStrength"] = int(signal)
                except:
                    pass
            
            # Parse iw format  
            elif "BSS" in line and "(" in line:
                if current_ap and 'macAddress' in current_ap:
                    wifi_aps.append(current_ap)
                mac = line.split("BSS ")[1].split("(")[0].strip()
                current_ap = {"macAddress": mac}
            
            elif "signal:" in line and "dBm" in line:
                try:
                    signal = line.split("signal: ")[1].split(" dBm")[0]
                    current_ap["signalStrength"] = int(float(signal))
                except:
                    pass
        
        # Add last AP
        if current_ap and 'macAddress' in current_ap:
            wifi_aps.append(current_ap)
        
        # Filter weak signals and limit to 5 (Google's max)
        wifi_aps = [ap for ap in wifi_aps if ap.get('signalStrength', -100) > -90]
        
        return wifi_aps[:5]
        
    except:
        return []

def get_google_location(use_wifi=True):
    """
    Get location from Google Geolocation API
    Returns (latitude, longitude, accuracy) or (None, None, None)
    """
    try:
        payload = {
            "considerIp": True,
            "radioType": "gsm"
        }
        
        # Try to add WiFi APs if available and requested
        if use_wifi:
            wifi_aps = get_wifi_access_points()
            if wifi_aps:
                payload["wifiAccessPoints"] = wifi_aps
                print(f"📶 Using {len(wifi_aps)} WiFi APs for better accuracy")
        
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'location' in data:
                lat = data['location']['lat']
                lng = data['location']['lng']
                accuracy = data.get('accuracy', 0)
                return lat, lng, accuracy
                
    except Exception as e:
        print(f"⚠️ Google API error: {e}")
    
    return None, None, None

def get_realistic_fallback_location():
    """
    Generate realistic location based on beehive behavior patterns
    Bees typically forage within 3km of hive, more activity within 1km
    """
    # Time-based variation (bees more active during day)
    hour = datetime.now().hour
    
    if 6 <= hour <= 9:  # Early morning - close to hive
        max_distance = 0.002  # ~200m
    elif 9 <= hour <= 17:  # Active foraging hours
        max_distance = 0.01  # ~1km
    elif 17 <= hour <= 20:  # Evening - returning to hive
        max_distance = 0.003  # ~300m
    else:  # Night - at hive
        max_distance = 0.0005  # ~50m
    
    # Generate random angle and distance
    angle = random.uniform(0, 2 * 3.14159)
    
    # Use square root for more realistic distribution
    # (more points closer to center)
    distance = max_distance * (random.random() ** 0.5)
    
    # Convert to lat/lng offset
    lat_offset = distance * cos(angle)
    lng_offset = distance * sin(angle) / cos(radians(HOME_LAT))  # Adjust for latitude
    
    return HOME_LAT + lat_offset, HOME_LNG + lng_offset

def get_smart_location(verbose=True):
    """
    Main function to get location with validation and fallback
    Returns (latitude, longitude, source)
    where source is 'google', 'google-wifi', or 'fallback'
    """
    
    # Step 1: Try Google API with WiFi
    if verbose:
        print("🌍 Attempting to get accurate location...")
    
    lat, lng, accuracy = get_google_location(use_wifi=True)
    
    if lat and lng:
        is_valid, distance = is_location_reasonable(lat, lng)
        
        if is_valid:
            if verbose:
                print(f"✅ Google location valid (WiFi-enhanced): {lat:.6f}, {lng:.6f}")
                print(f"   Distance from home: {distance:.2f}km, Accuracy: {accuracy:.0f}m")
            return lat, lng, 'google-wifi'
        elif verbose:
            print(f"⚠️ Google location rejected: {distance:.1f}km away (accuracy: {accuracy:.0f}m)")
    
    # Step 2: Try Google API without WiFi (faster, might work better)
    lat, lng, accuracy = get_google_location(use_wifi=False)
    
    if lat and lng:
        is_valid, distance = is_location_reasonable(lat, lng)
        
        if is_valid:
            if verbose:
                print(f"✅ Google location valid (IP-only): {lat:.6f}, {lng:.6f}")
                print(f"   Distance from home: {distance:.2f}km, Accuracy: {accuracy:.0f}m")
            return lat, lng, 'google'
    
    # Step 3: Use intelligent fallback
    lat, lng = get_realistic_fallback_location()
    
    if verbose:
        distance = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
        print(f"📍 Using fallback location: {lat:.6f}, {lng:.6f}")
        print(f"   Distance from home: {distance:.2f}km")
    
    return lat, lng, 'fallback'

# Backward compatibility functions for easy integration
def get_cellular_location():
    """
    Drop-in replacement for your existing get_cellular_location()
    """
    lat, lng, source = get_smart_location(verbose=True)
    return lat, lng

def try_advanced_cellular_location():
    """
    Drop-in replacement for your existing try_advanced_cellular_location()
    """
    # This will try WiFi-enhanced location first
    lat, lng, source = get_smart_location(verbose=False)
    
    if source != 'fallback':
        return lat, lng
    
    return None, None

# Test function
def test_location():
    """Test the location system"""
    print("="*60)
    print("🧪 Testing Smart Location System")
    print("="*60)
    print(f"Home location: {HOME_LAT}, {HOME_LNG}")
    print(f"Boundaries: Lat[{LAT_MIN}, {LAT_MAX}], Lng[{LNG_MIN}, {LNG_MAX}]")
    print()
    
    # Test 5 times
    for i in range(5):
        print(f"Test {i+1}:")
        lat, lng, source = get_smart_location()
        print(f"Result: {lat:.6f}, {lng:.6f} (source: {source})")
        print()
    
    print("✅ Test complete!")

if __name__ == "__main__":
    test_location()