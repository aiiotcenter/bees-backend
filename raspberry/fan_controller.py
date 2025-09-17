#!/usr/bin/env python3
"""
Raspberry Pi Fan Controller
Manages fan operation based on CPU temperature and time intervals
"""

import RPi.GPIO as GPIO
import time
import threading
import logging
from datetime import datetime, timedelta

class FanController:
    def __init__(self, fan_pin=18, temp_threshold=60.0, interval_minutes=30, 
                 interval_duration=60, enable_interval_mode=True):
        """
        Initialize the fan controller for 5V RELAY control
        
        Uses a 5V relay module to safely switch fan power on/off.
        Works with any fan voltage/current within relay specifications.
        
        Args:
            fan_pin (int): GPIO pin number connected to relay IN pin (BCM numbering)
            temp_threshold (float): Temperature in Celsius to turn on fan
            interval_minutes (int): Minutes between interval fan runs
            interval_duration (int): Seconds to run fan during interval
            enable_interval_mode (bool): Enable periodic fan operation
        """
    def __init__(self, fan_pin=18, temp_threshold=60.0, interval_minutes=30, 
                 interval_duration=60, enable_interval_mode=True, active_low_relay=True):
        """
        Initialize the fan controller for 5V RELAY control
        
        Uses a 5V relay module to safely switch fan power on/off.
        Works with any fan voltage/current within relay specifications.
        
        Args:
            fan_pin (int): GPIO pin number connected to relay IN pin (BCM numbering)
            temp_threshold (float): Temperature in Celsius to turn on fan
            interval_minutes (int): Minutes between interval fan runs
            interval_duration (int): Seconds to run fan during interval
            enable_interval_mode (bool): Enable periodic fan operation
            active_low_relay (bool): True if relay activates on LOW signal (most common)
        """
        self.fan_pin = fan_pin
        self.temp_threshold = temp_threshold
        self.interval_minutes = interval_minutes
        self.interval_duration = interval_duration
        self.enable_interval_mode = enable_interval_mode
        self.active_low_relay = active_low_relay  # New parameter
        
        # Control variables
        self.running = False
        self.fan_state = False
        self.temp_control_active = False
        self.interval_control_active = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup GPIO
        self.setup_gpio()
        
        # Threading
        self.temp_thread = None
        self.interval_thread = None
        self.lock = threading.Lock()

    def setup_gpio(self):
        """Initialize GPIO settings for relay control"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.fan_pin, GPIO.OUT)
        
        # Set initial state based on relay type
        if self.active_low_relay:
            GPIO.output(self.fan_pin, GPIO.HIGH)  # HIGH = Relay OFF for active-low
            self.logger.info(f"GPIO pin {self.fan_pin} configured for ACTIVE-LOW 5V relay control")
        else:
            GPIO.output(self.fan_pin, GPIO.LOW)   # LOW = Relay OFF for active-high
            self.logger.info(f"GPIO pin {self.fan_pin} configured for ACTIVE-HIGH 5V relay control")
        
        self.logger.info("Relay provides safe switching for any fan within relay specs")

    def get_cpu_temperature(self):
        """
        Get CPU temperature from the system
        Returns temperature in Celsius
        """
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_str = f.read().strip()
                # Temperature is in millidegrees Celsius
                temp = float(temp_str) / 1000.0
                return temp
        except Exception as e:
            self.logger.error(f"Error reading temperature: {e}")
            return None

    def set_fan_state(self, state, reason=""):
        """
        Control fan state with thread safety
        
        Args:
            state (bool): True to turn fan on, False to turn off
            reason (str): Reason for state change
        """
        with self.lock:
            if self.fan_state != state:
                if self.active_low_relay:
                    # For active-low relay: LOW = ON, HIGH = OFF
                    gpio_state = GPIO.LOW if state else GPIO.HIGH
                else:
                    # For active-high relay: HIGH = ON, LOW = OFF
                    gpio_state = GPIO.HIGH if state else GPIO.LOW
                
                GPIO.output(self.fan_pin, gpio_state)
                self.fan_state = state
                status = "ON" if state else "OFF"
                gpio_level = "LOW" if gpio_state == GPIO.LOW else "HIGH"
                relay_type = "Active-LOW" if self.active_low_relay else "Active-HIGH"
                self.logger.info(f"Fan turned {status} (GPIO: {gpio_level}, {relay_type} relay) - {reason}")

    def temperature_monitor(self):
        """Monitor CPU temperature and control fan accordingly"""
        self.logger.info("Temperature monitoring started")
        hysteresis = 5.0  # Temperature difference for hysteresis
        
        while self.running:
            try:
                temp = self.get_cpu_temperature()
                if temp is not None:
                    # Turn on fan if temperature exceeds threshold
                    if temp >= self.temp_threshold and not self.temp_control_active:
                        self.temp_control_active = True
                        self.set_fan_state(True, f"CPU temp: {temp:.1f}°C >= {self.temp_threshold}°C")
                    
                    # Turn off fan if temperature drops below threshold - hysteresis
                    elif temp <= (self.temp_threshold - hysteresis) and self.temp_control_active:
                        self.temp_control_active = False
                        # Only turn off if interval control is not active
                        if not self.interval_control_active:
                            self.set_fan_state(False, f"CPU temp cooled: {temp:.1f}°C")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in temperature monitoring: {e}")
                time.sleep(10)

    def interval_controller(self):
        """Control fan at regular intervals"""
        if not self.enable_interval_mode:
            return
            
        self.logger.info(f"Interval control started - every {self.interval_minutes} minutes for {self.interval_duration} seconds")
        
        while self.running:
            try:
                # Wait for the interval
                time.sleep(self.interval_minutes * 60)
                
                if not self.running:
                    break
                
                # Turn on fan for interval duration
                self.interval_control_active = True
                if not self.temp_control_active:  # Only log if not already on for temperature
                    self.set_fan_state(True, f"Interval run ({self.interval_duration}s)")
                
                # Keep fan on for specified duration
                time.sleep(self.interval_duration)
                
                # Turn off fan if temperature control is not active
                self.interval_control_active = False
                if not self.temp_control_active:
                    self.set_fan_state(False, "Interval run completed")
                    
            except Exception as e:
                self.logger.error(f"Error in interval control: {e}")

    def start(self):
        """Start the fan controller"""
        if self.running:
            self.logger.warning("Fan controller is already running")
            return
        
        self.running = True
        self.logger.info("Starting fan controller...")
        
        # Start temperature monitoring thread
        self.temp_thread = threading.Thread(target=self.temperature_monitor, daemon=True)
        self.temp_thread.start()
        
        # Start interval control thread
        if self.enable_interval_mode:
            self.interval_thread = threading.Thread(target=self.interval_controller, daemon=True)
            self.interval_thread.start()
        
        self.logger.info("Fan controller started successfully")

    def stop(self):
        """Stop the fan controller"""
        if not self.running:
            return
        
        self.logger.info("Stopping fan controller...")
        self.running = False
        
        # Wait for threads to finish
        if self.temp_thread and self.temp_thread.is_alive():
            self.temp_thread.join(timeout=2)
        
        if self.interval_thread and self.interval_thread.is_alive():
            self.interval_thread.join(timeout=2)
        
        # Turn off fan and cleanup
        self.set_fan_state(False, "Controller stopped")
        self.cleanup()
        
        self.logger.info("Fan controller stopped")

    def force_fan_off(self):
        """Force fan off and ensure relay is in OFF state"""
        try:
            if self.active_low_relay:
                GPIO.output(self.fan_pin, GPIO.HIGH)  # HIGH = OFF for active-low
            else:
                GPIO.output(self.fan_pin, GPIO.LOW)   # LOW = OFF for active-high
            
            self.fan_state = False
            self.logger.info("Fan forcibly turned OFF")
        except Exception as e:
            self.logger.error(f"Error forcing fan off: {e}")

    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            # Ensure fan is off before cleanup
            self.force_fan_off()
            time.sleep(0.1)  # Give relay time to switch
            GPIO.cleanup()
            self.logger.info("GPIO cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup: {e}")

    def get_status(self):
        """Get current status of the fan controller"""
        temp = self.get_cpu_temperature()
        return {
            'running': self.running,
            'fan_on': self.fan_state,
            'cpu_temp': temp,
            'temp_threshold': self.temp_threshold,
            'temp_control_active': self.temp_control_active,
            'interval_control_active': self.interval_control_active,
            'interval_mode_enabled': self.enable_interval_mode
        }

def main():
    """
    Main function to run the fan controller with 5V relay
    
    5V RELAY MODULE WIRING:
    - Relay VCC → Raspberry Pi 5V
    - Relay GND → Raspberry Pi GND  
    - Relay IN  → GPIO Pin (e.g., Pin 18)
    - Fan VCC   → Relay NO (Normally Open)
    - Fan GND   → Power Supply GND
    - Power Supply +V → Relay COM (Common)
    
    Works with 5V, 12V, or any voltage fan within relay specifications!
    """
    # Configuration
    FAN_PIN = 18                    # GPIO pin connected to relay IN pin
    TEMP_THRESHOLD = 60.0          # Temperature threshold in Celsius
    INTERVAL_MINUTES = 30          # Run fan every 30 minutes
    INTERVAL_DURATION = 60         # Run for 60 seconds during interval
    ENABLE_INTERVALS = True        # Enable periodic operation
    
    print("=" * 60)
    print("5V RELAY FAN CONTROLLER")
    print("=" * 60)
    print("Safe for any fan within relay specifications!")
    print("\nWiring:")
    print("  Relay Module:")
    print("    VCC → Pi 5V")
    print("    GND → Pi GND")
    print(f"    IN  → GPIO Pin {FAN_PIN}")
    print("\n  Fan Circuit:")
    print("    Fan VCC → Relay NO (Normally Open)")
    print("    Fan GND → Power Supply GND")
    print("    Power Supply +V → Relay COM (Common)")
    print("=" * 60)
    
    # Create and start fan controller
    fan_controller = FanController(
        fan_pin=FAN_PIN,
        temp_threshold=TEMP_THRESHOLD,
        interval_minutes=INTERVAL_MINUTES,
        interval_duration=INTERVAL_DURATION,
        enable_interval_mode=ENABLE_INTERVALS,
        active_low_relay=True  # Set to False if you have an active-high relay
    )
    
    try:
        fan_controller.start()
        
        # Main loop - display status every 30 seconds
        while True:
            status = fan_controller.get_status()
            print(f"\n--- Fan Controller Status ---")
            print(f"CPU Temperature: {status['cpu_temp']:.1f}°C")
            print(f"Fan Status: {'ON' if status['fan_on'] else 'OFF'}")
            print(f"Temperature Control: {'Active' if status['temp_control_active'] else 'Inactive'}")
            print(f"Interval Control: {'Active' if status['interval_control_active'] else 'Inactive'}")
            print(f"Threshold: {status['temp_threshold']}°C")
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        fan_controller.stop()

if __name__ == "__main__":
    main()