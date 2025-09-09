AIoT Voice-Enabled Virtual Home Security System
This project demonstrates a virtual home security system controlled by voice commands. It integrates a web-based dashboard, a Python backend, a simulated NLP service, and MQTT-based simulated IoT devices.

Project Architecture
The system consists of four main components:

Web Dashboard (Frontend): A single-page web application built with HTML, Tailwind CSS, and JavaScript. It provides a user interface to view device statuses, see a real-time event log, and issue voice commands using the browser's Web Speech API. It communicates with the backend via WebSockets.

Backend Server (Python/Flask): The central component built with Flask and Flask-SocketIO. It serves the web dashboard, manages WebSocket connections, includes a simplified NLP engine to interpret commands, and acts as an MQTT client to send commands to the IoT devices.

MQTT Broker: A message broker (like Mosquitto) that facilitates asynchronous communication between the backend server and the simulated IoT devices. This decouples the components, making the system more scalable and resilient.

Simulated IoT Devices (Python): A separate Python script that simulates the behavior of a door lock, an alarm system, and a motion sensor. These devices connect to the MQTT broker, subscribe to a command topic to receive instructions, and publish their state changes to a status topic.

Data Flow for a Voice Command
The user clicks the microphone button on the Web Dashboard.

The browser's Web Speech API captures the audio, transcribes it to text.

The transcribed text is sent to the Backend Server via a WebSocket event.

The server's simulated NLP Service processes the text to extract intent (e.g., lock) and entities (e.g., front door).

The server translates this into a JSON command payload.

The command is published to the home/security/command topic on the MQTT Broker.

The relevant Simulated IoT Device, which is subscribed to this topic, receives the command.

The device updates its internal state (e.g., changes from unlocked to locked).

The device publishes its new state to the home/security/status topic on the MQTT Broker.

The Backend Server, subscribed to the status topic, receives the state update.

The server updates its master state list and broadcasts the change to all connected Web Dashboards via a WebSocket event.

The dashboard UI updates in real-time to reflect the new device state.

Getting Started
Follow these steps to set up and run the project on a Linux-based system (e.g., Ubuntu).

Prerequisites
Python 3.7+

An MQTT Broker. Mosquitto is recommended.

1. Install MQTT Broker
If you don't have an MQTT broker, install Mosquitto:

sudo apt-get update
sudo apt-get install mosquitto mosquitto-clients
# Start and enable the broker to run on startup
sudo systemctl start mosquitto
sudo systemctl enable mosquitto

By default, Mosquitto will run on localhost:1883.

2. Set Up Python Environment
It's recommended to use a virtual environment.

# Create a new directory for the project
mkdir home-security-system
cd home-security-system

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the required Python packages
pip install flask flask-socketio paho-mqtt

3. Save the Project Files
Save the following files into your home-security-system directory:

app.py (Backend Server)

dashboard.html (Web Dashboard)

iot_devices.py (Simulated IoT Devices)

architecture.md (Architecture Diagram)

README.md (This file)

4. Run the System
You will need to open three separate terminal windows in the home-security-system directory. Make sure you activate the virtual environment (source venv/bin/activate) in each terminal where you run a Python script.

Terminal 1: Start the Backend Server

python app.py

You should see output indicating that the web server and MQTT client have started.

Terminal 2: Start the Simulated IoT Devices

python iot_devices.py

This will start the device simulator, which will connect to the MQTT broker and begin listening for commands.

Terminal 3: (Optional) Monitor MQTT Traffic

You can use mosquitto_sub to watch the messages flowing through the broker. This is great for debugging.

# Subscribe to all topics under 'home/security'
mosquitto_sub -h localhost -t "home/security/#" -v

5. Use the Dashboard
Open a web browser and navigate to:

https://www.google.com/search?q=http://127.0.0.1:5000

You should see the dashboard with an initial status for all devices.

The "Connection Status" in the top right should change to "Connected".

Click the microphone icon, grant microphone permissions if prompted, and speak a command.

Watch the device statuses change on the dashboard and observe the logs in all three of your terminal windows.

Example Voice Commands:

"Lock the front door"

"Unlock the front door"

"Arm the alarm system"

"Disarm the alarm"

"Give me a status report"

Enjoy your virtual AIoT home security system!