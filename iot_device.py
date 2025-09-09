# iot_devices.py
# This script simulates the behavior of home security IoT devices.
# It connects to the same MQTT broker as the backend server.
# It listens for commands on the 'command' topic and publishes its status
# changes to the 'status' topic.

import paho.mqtt.client as mqtt
import time
import json
import random
from threading import Thread

# --- Configuration ---
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "home/security/command"
MQTT_TOPIC_STATUS = "home/security/status"

# --- Device Simulation Class ---
class SimulatedDevice:
    """A base class for our simulated IoT devices."""
    def __init__(self, device_id, initial_state, client):
        self.device_id = device_id
        self.state = initial_state
        self.client = client
        self.publish_status()

    def publish_status(self):
        """Publishes the current state of the device to the MQTT status topic."""
        payload = json.dumps({"device_id": self.device_id, "state": self.state})
        self.client.publish(MQTT_TOPIC_STATUS, payload)
        print(f"Device '{self.device_id}': Published status -> {payload}")
        
    def process_command(self, command):
        """Processes a command and updates the device state if applicable."""
        # This method should be overridden by subclasses
        pass

# --- Specific Device Implementations ---
class DoorLock(SimulatedDevice):
    def process_command(self, command):
        if command in ["lock", "unlock"]:
            new_state = "locked" if command == "lock" else "unlocked"
            if self.state != new_state:
                print(f"Device '{self.device_id}': Changing state from '{self.state}' to '{new_state}'.")
                self.state = new_state
                self.publish_status()
            else:
                print(f"Device '{self.device_id}': Already in '{new_state}' state.")

class AlarmSystem(SimulatedDevice):
    def process_command(self, command):
        if command in ["armed", "disarmed"]:
            if self.state != command:
                print(f"Device '{self.device_id}': Changing state from '{self.state}' to '{command}'.")
                self.state = command
                self.publish_status()
            else:
                print(f"Device '{self.device_id}': Already in '{command}' state.")

class MotionSensor(SimulatedDevice):
    """A sensor that randomly detects motion when the alarm is armed."""
    def __init__(self, device_id, initial_state, client, alarm_system):
        super().__init__(device_id, initial_state, client)
        self.alarm = alarm_system
        # Start a background thread to simulate motion detection
        self.simulation_thread = Thread(target=self.simulate_motion)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()

    def process_command(self, command):
        """Process activation/deactivation commands sent from the broker."""
        try:
            cmd = (command or "").lower()
        except Exception:
            cmd = str(command).lower()

        # Accept both noun/states and verb forms
        if cmd in ("active", "activate", "on", "enable"):
            new_state = "active"
        elif cmd in ("inactive", "deactivate", "off", "disable"):
            new_state = "inactive"
        else:
            # unknown command for this device
            print(f"Device '{self.device_id}': Unsupported command '{command}'")
            return

        if self.state != new_state:
            print(f"Device '{self.device_id}': Changing state from '{self.state}' to '{new_state}'.")
            self.state = new_state
            self.publish_status()
        else:
            print(f"Device '{self.device_id}': Already in '{new_state}' state.")

    def simulate_motion(self):
        """Periodically checks if it should trigger a motion event."""
        while True:
            time.sleep(random.randint(10, 25)) # Check for motion every 10-25 seconds
            # Only trigger motion if the alarm is armed and the sensor is inactive
            if self.alarm.state == "armed" and self.state == "inactive" and random.random() < 0.3: # 30% chance
                print(f"Device '{self.device_id}': Motion Detected!")
                self.state = "active"
                self.publish_status()
                # Reset to inactive after a short period
                time.sleep(5)
                self.state = "inactive"
                self.publish_status()

# --- MQTT Client for Devices ---
def on_connect(client, userdata, flags, rc):
    """Callback for MQTT connection."""
    if rc == 0:
        print("IoT Devices: Connected to MQTT Broker.")
        client.subscribe(MQTT_TOPIC_COMMAND)
    else:
        print(f"IoT Devices: Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Callback for processing received commands."""
    try:
        payload = msg.payload.decode()
        print(f"IoT Devices: Received command -> {payload}")
        data = json.loads(payload)
        device_id = data.get("device_id")
        command = data.get("command")
        
        # Route the command to the correct device object
        if device_id in devices:
            devices[device_id].process_command(command)
        else:
            print(f"IoT Devices: Received command for unknown device '{device_id}'")

    except json.JSONDecodeError:
        print("IoT Devices: Received malformed JSON command.")
    except Exception as e:
        print(f"IoT Devices: Error processing command: {e}")

# --- Main Script Execution ---
if __name__ == "__main__":
    print("Starting IoT Device Simulator...")
    
    device_client = mqtt.Client()
    device_client.on_connect = on_connect
    device_client.on_message = on_message
    
    try:
        device_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except ConnectionRefusedError:
        print("\n--- MQTT Connection Error ---")
        print(f"Could not connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}.")
        print("Please ensure an MQTT broker (like Mosquitto) is running before starting the devices.")
        exit(1) # Exit if the broker isn't available

    # Initialize all our simulated devices
    alarm = AlarmSystem("alarm_system", "disarmed", device_client)
    devices = {
        "door_lock_1": DoorLock("door_lock_1", "locked", device_client),
        "alarm_system": alarm,
        "motion_sensor_1": MotionSensor("motion_sensor_1", "inactive", device_client, alarm)
    }

    print("IoT devices are running and listening for commands.")
    # The loop_forever() call is blocking and will keep the script running.
    device_client.loop_forever()
