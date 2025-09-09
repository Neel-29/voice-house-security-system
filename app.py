# app.py
# Main backend application using Flask, Flask-SocketIO, and Paho-MQTT.
# This server handles web dashboard requests, manages WebSocket communication for real-time updates,
# processes voice commands via a simulated NLP service, and communicates with IoT devices via MQTT.

import json
import time
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
from threading import Thread, Lock

# --- Basic Configuration ---
# Flask & SocketIO App Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="https://voice-house-security-system.vercel.app/")

# MQTT Broker Configuration
MQTT_BROKER = 'localhost'
MQTT_PORT = 1883
# Topics for device commands and status updates
MQTT_TOPIC_COMMAND = "home/security/command"
MQTT_TOPIC_STATUS = "home/security/status"

# --- In-Memory State Management ---
# Using a dictionary to store the current state of all simulated devices.
# A lock is used to ensure thread-safe access to this shared state.
device_states = {
    "door_lock_1": {"name": "Front Door Lock", "state": "locked"},
    "alarm_system": {"name": "Alarm System", "state": "disarmed"},
    "motion_sensor_1": {"name": "Living Room Sensor", "state": "inactive"}
}
state_lock = Lock()

# --- MQTT Client Setup ---
# Handles communication with the simulated IoT devices.

def on_connect(client, userdata, flags, rc):
    """Callback for when the client connects to the MQTT broker."""
    if rc == 0:
        print("MQTT Client: Connected to broker successfully.")
        # Subscribe to the status topic to receive updates from devices
        client.subscribe(MQTT_TOPIC_STATUS)
    else:
        print(f"MQTT Client: Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    """Callback for when a message is received from the MQTT broker."""
    try:
        payload = msg.payload.decode()
        print(f"MQTT Client: Received status update -> {payload}")
        data = json.loads(payload)
        device_id = data.get("device_id")
        state = data.get("state")

        # Update the state in a thread-safe manner
        with state_lock:
            if device_id in device_states:
                device_states[device_id]["state"] = state
                # Log the event and notify the web dashboard of the change
                log_event(f"Device '{device_states[device_id]['name']}' updated state to '{state}'.")
                socketio.emit('status_update', {"devices": device_states})
    except json.JSONDecodeError:
        print("MQTT Client: Received malformed JSON.")
    except Exception as e:
        print(f"MQTT Client: Error processing message: {e}")

# Initialize and configure the MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def start_mqtt_client():
    """Connects to the MQTT broker and starts the network loop in a background thread."""
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except ConnectionRefusedError:
        print("\n--- MQTT Connection Error ---")
        print(f"Could not connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}.")
        print("Please ensure an MQTT broker (like Mosquitto) is running.")
        print("You can install it with: 'sudo apt-get install mosquitto mosquitto-clients'")
        print("And start it with: 'sudo systemctl start mosquitto'")
        print("---------------------------\n")
    except Exception as e:
        print(f"MQTT Client: An unexpected error occurred: {e}")

# --- Event Logging ---
def log_event(message):
    """Logs an event with a timestamp and sends it to the web dashboard."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    print(f"Log: {log_entry}")
    socketio.emit('log_event', {'log': log_entry})

# --- NLP Simulation ---
def process_nlp(text):
    """
    A simplified NLP function that returns a list of device/action dicts for a given text.
    Example return: [{"device": "door_lock_1", "action": "unlock"}, {"device": "motion_sensor_1", "action": "active"}]
    """
    text = (text or "").lower()
    commands = []

    # Front door lock
    if "front door" in text or "front-door" in text:
        # prefer explicit "unlock" over "lock" if both words appear
        if "unlock" in text:
            commands.append({"device": "door_lock_1", "action": "unlock"})
        elif "lock" in text:
            commands.append({"device": "door_lock_1", "action": "lock"})

    # Alarm system
    if "alarm" in text:
        if "disarm" in text:
            commands.append({"device": "alarm_system", "action": "disarmed"})
        elif "arm" in text:
            commands.append({"device": "alarm_system", "action": "armed"})

    # Motion / living room sensor
    if "living room" in text or "living-room" in text:
        if any(k in text for k in ("activate", "turn on", "enable", "on")):
            commands.append({"device": "motion_sensor_1", "action": "active"})
        if any(k in text for k in ("deactivate", "turn off", "disable", "off")):
            commands.append({"device": "motion_sensor_1", "action": "inactive"})

    # Status query (special action)
    if "status" in text or "what is the status" in text or "report" in text:
        commands.append({"device": None, "action": "query_status"})

    return commands

# Helper to normalize action -> state for optimistic UI updates
def normalize_action_to_state(device_id, action):
    if device_id == "door_lock_1":
        if action == "unlock":
            return "unlocked"
        if action == "lock":
            return "locked"
        # if action already a state
        if action in ("locked", "unlocked"):
            return action
    if device_id == "alarm_system":
        if action in ("armed", "disarmed"):
            return action
    if device_id == "motion_sensor_1":
        if action in ("active", "inactive"):
            return action
    # fallback: return action as-is
    return action

# --- Web Server (Flask) and WebSocket (SocketIO) Routes ---

@app.route('/')
def index():
    """Serves the main web dashboard."""
    with open("dashboard.html", "r") as f:
        return render_template_string(f.read())

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection to the WebSocket."""
    print('Client connected')
    log_event("Web dashboard connected to server.")
    # Send the initial state of all devices to the newly connected client
    with state_lock:
        emit('status_update', {"devices": device_states})

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    print('Client disconnected')

@socketio.on('process_command')
def handle_voice_command(data):
    """
    Receives a transcribed voice command from the dashboard, processes it,
    and publishes the corresponding command(s) to the MQTT broker.
    """
    text_command = data.get('text') if isinstance(data, dict) else None
    if not text_command:
        return

    log_event(f"Received voice command: '{text_command}'")
    nlp_results = process_nlp(text_command)

    if not nlp_results:
        log_event(f"Could not understand command: '{text_command}'. No action taken.")
        return

    # First, handle any status query by reporting current states (but continue to process other actions)
    for res in nlp_results:
        if res.get("action") == "query_status":
            log_event("Processing status query.")
            with state_lock:
                status_report = "Current Status Report: "
                statuses = [f"{details['name']} is {details['state']}" for _, details in device_states.items()]
                status_report += "; ".join(statuses) + "."
                log_event(status_report)
            # don't return here — allow other commands in the same utterance to be executed

    # Publish all actionable commands to MQTT
    for res in nlp_results:
        device = res.get("device")
        action = res.get("action")
        if device and action and action != "query_status":
            log_event(f"NLP parsed: Control '{device}' to state '{action}'.")
            command_payload = json.dumps({"device_id": device, "command": action})
            try:
                mqtt_client.publish(MQTT_TOPIC_COMMAND, command_payload)
                log_event(f"Published command to MQTT: {command_payload}")
            except Exception as e:
                log_event(f"Failed to publish MQTT command: {e}")

# --- Main Application Execution ---
if __name__ == '__main__':
    print("Starting AIoT Home Security System...")
    # Start the MQTT client in a separate thread
    mqtt_thread = Thread(target=start_mqtt_client)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    # Start the Flask-SocketIO web server
    print("Starting web server on http://127.0.0.1:5000")
    socketio.run(app, host='0.0.0.0', port=5000)