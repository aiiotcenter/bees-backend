#!/usr/bin/env python3
"""
Test smart fallback location with validation
Run with: python3 test_fallback_location.py
"""

import random
import requests
import time
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

# Configuration
GOOGLE_API_KEY = "AIzaSyCysMdMd_f01vX0vF6EOJtohcAe0YvtipY"

# Your actual location
HOME_LAT = 35.227
HOME_LNG = 33.32

# Reasonable boundaries for your area (adjust as needed)
# These create a box around your expected location
LAT_MIN = 35.20  # South boundary
LAT_MAX = 35.25  # North boundary  
LNG_MIN = 33.29  # West boundary
LNG_MAX = 33.35  # East boundary

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two coordinates in kilometers"""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371  # Earth radius in km

def is_location_reasonable(lat, lng):
    """Check if location is within reasonable boundaries"""
    if LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX:
        distance = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
        return True, distance
    return False, None

def get_google_location():
    """Get location from Google API"""
    try:
        payload = {"considerIp": True}
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'location' in data:
                return data['location']['lat'], data['location']['lng'], data.get('accuracy', 0)
    except:
        pass
    
    return None, None, None

def get_fallback_location_simple():
    """Simple fallback with small random offset"""
    # Add random offset within ~100 meters
    lat_offset = random.uniform(-0.001, 0.001)
    lng_offset = random.uniform(-0.001, 0.001)
    
    return HOME_LAT + lat_offset, HOME_LNG + lng_offset

def get_fallback_location_realistic():
    """Realistic fallback simulating bee movement patterns"""
    # Bees typically forage within 3km of hive
    # More activity within 1km
    
    # Time-based variation (bees more active during day)
    hour = datetime.now().hour
    if 6 <= hour <= 18:  # Daytime
        max_distance = 0.01  # ~1km
    else:  # Night
        max_distance = 0.001  # ~100m
    
    # Generate random angle and distance
    angle = random.uniform(0, 2 * 3.14159)
    distance = random.uniform(0, max_distance)
    
    # Convert to lat/lng offset
    lat_offset = distance * cos(angle)
    lng_offset = distance * sin(angle)
    
    return HOME_LAT + lat_offset, HOME_LNG + lng_offset

def get_smart_location():
    """Smart location with validation and fallback"""
    print("\n🌍 Getting smart location...")
    
    # Step 1: Try Google API
    print("   Step 1: Trying Google Geolocation API...")
    lat, lng, accuracy = get_google_location()
    
    if lat and lng:
        print(f"   Google returned: {lat:.6f}, {lng:.6f} (accuracy: {accuracy}m)")
        
        # Step 2: Validate the location
        is_reasonable, distance = is_location_reasonable(lat, lng)
        
        if is_reasonable:
            print(f"   ✅ Location is reasonable (distance: {distance:.2f}km)")
            return lat, lng, "google"
        else:
            if distance:
                print(f"   ⚠️ Location unreasonable (distance: {distance:.2f}km)")
            else:
                print(f"   ⚠️ Location outside boundaries")
    else:
        print("   ❌ Google API failed")
    
    # Step 3: Use fallback
    print("   Step 2: Using fallback location...")
    lat, lng = get_fallback_location_realistic()
    print(f"   Fallback location: {lat:.6f}, {lng:.6f}")
    
    return lat, lng, "fallback"

def test_location_validation():
    """Test the validation logic"""
    print("\n🧪 Testing location validation...")
    
    test_cases = [
        (HOME_LAT, HOME_LNG, "Home location"),
        (35.262, 33.5, "Your current Google result"),
        (35.235, 33.325, "Nearby location"),
        (35.5, 33.8, "Far location"),
        (34.0, 32.0, "Very far location"),
    ]
    
    for lat, lng, description in test_cases:
        is_reasonable, distance = is_location_reasonable(lat, lng)
        
        if is_reasonable:
            print(f"   ✅ {description}: {lat}, {lng} - Valid (distance: {distance:.2f}km)")
        else:
            if distance:
                d = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
                print(f"   ❌ {description}: {lat}, {lng} - Invalid (distance: {d:.2f}km)")
            else:
                print(f"   ❌ {description}: {lat}, {lng} - Outside boundaries")

def test_multiple_attempts():
    """Test multiple location attempts"""
    print("\n📊 Testing 10 location attempts...")
    
    google_count = 0
    fallback_count = 0
    
    for i in range(10):
        print(f"\n   Attempt {i+1}:")
        lat, lng, source = get_smart_location()
        
        if source == "google":
            google_count += 1
        else:
            fallback_count += 1
        
        distance = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
        print(f"   Result: {lat:.6f}, {lng:.6f} from {source} (distance: {distance:.3f}km)")
        
        time.sleep(1)  # Small delay between attempts
    
    print(f"\n   Summary: {google_count} from Google, {fallback_count} from fallback")

def main():
    print("="*60)
    print("🧪 Smart Fallback Location Test")
    print("="*60)
    print(f"Home location: {HOME_LAT}, {HOME_LNG}")
    print(f"Boundaries: Lat[{LAT_MIN}, {LAT_MAX}], Lng[{LNG_MIN}, {LNG_MAX}]")
    
    # Test 1: Validation logic
    test_location_validation()
    
    # Test 2: Single smart location
    print("\n" + "="*60)
    print("Single location test:")
    lat, lng, source = get_smart_location()
    distance = calculate_distance(lat, lng, HOME_LAT, HOME_LNG)
    print(f"\nFinal result: {lat:.6f}, {lng:.6f}")
    print(f"Source: {source}")
    print(f"Distance from home: {distance:.3f}km")
    
    # Test 3: Multiple attempts
    print("\n" + "="*60)
    test_multiple_attempts()
    
    print("\n" + "="*60)
    print("✅ Test complete!")

if __name__ == "__main__":
    main()