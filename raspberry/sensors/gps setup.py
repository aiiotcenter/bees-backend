import time
from sensors.gps_module import get_gps_location  # Assuming you have this method already

def initialize_gps():
    try:
        # Initialize your GPS module here
        print("🌍 Initializing GPS module...")
        return True
    except Exception as e:
        print(f"⚠️ Error initializing GPS module: {e}")
        return False

def wait_for_gps_connection():
    while True:
        print("🔄 Waiting for GPS connection...")
        
        # Try to get GPS location
        location = get_gps_location()  # This is where your GPS reading function comes in

        if location:
            print(f"📍 GPS location acquired: {location}")
            return location  # Successfully acquired GPS, exit the loop
        else:
            time.sleep(1)  # Retry after 1 second if no location is found

def main():
    # Initialize GPS module
    if initialize_gps():
        # Wait for GPS connection
        location = wait_for_gps_connection()
        
        # After connection is successful, print the location and exit
        print(f"🚀 Successfully connected to satellite! Location: {location}")
        print("🎯 Terminating script now.")
    else:
        print("⚠️ Failed to initialize GPS module.")

if __name__ == "__main__":
    main()
