from flask import Flask, request, jsonify, render_template_string
import RPi.GPIO as GPIO
import time
import json
import os
import threading
import atexit
import signal
import sys

app = Flask(__name__)

# GPIO setup for radio transmitter
RF_PIN = 17

# Global variable to track GPIO state
gpio_initialized = False

def initialize_gpio():
    #Initialize GPIO
    global gpio_initialized
    try:
        # Cleanup any existing GPIO state
        GPIO.cleanup()
        time.sleep(0.1)
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RF_PIN, GPIO.OUT)
        GPIO.output(RF_PIN, 0)
        gpio_initialized = True
        print("✅ GPIO initialized successfully")
    except Exception as e:
        print(f"❌ GPIO initialization failed: {e}")
        gpio_initialized = False

def cleanup_gpio():
    #Cleanup GPIO on exit
    global gpio_initialized
    if gpio_initialized:
        try:
            GPIO.output(RF_PIN, 0)
            GPIO.cleanup()
            gpio_initialized = False
            print("✅ GPIO cleaned up")
        except Exception as e:
            print(f"⚠️ Warning during GPIO cleanup: {e}")

def handle_exit(signum, frame):
    #Handle shutdown signals
    print(f"🛑 Received signal {signum}, shutting down...")
    cleanup_gpio()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
atexit.register(cleanup_gpio)

# Initialize GPIO on startup
initialize_gpio()

# State file to persist device state
STATE_FILE = "device_state.json"

# Command mappings
COMMAND_SIGNALS = {
    "power_toggle": [1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,1,1,0,1,1,1,0,1],
    "faster": [1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,1,1,0,1,1,1,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1],
    "slower": [1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,0,0,0,1,1,1,0,1,1,1,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1],
    "mode": [1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,1,1,0,1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,1,1,0,1,1,1,0,1,0,0,0,1,0,0,0,1]
}

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Device Controller</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .status-card {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        .controls {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .control-group {
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        button {
            background: #2196F3;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
            width: 100%;
        }
        button:hover {
            background: #1976D2;
        }
        button:active {
            background: #0D47A1;
        }
        .power-btn {
            background: #4CAF50;
        }
        .power-btn.off {
            background: #f44336;
        }
        .log {
            background: #333;
            color: #0f0;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            height: 200px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .log-entry {
            margin: 5px 0;
        }
        .timestamp {
            color: #888;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎛️ Device Controller</h1>
        
        <div class="status-card">
            <h2>📊 Current Status</h2>
            <div id="status">
                <p><strong>Power:</strong> <span id="power-status">Loading...</span></p>
                <p><strong>Speed Level:</strong> <span id="speed-status">Loading...</span></p>
                <p><strong>Mode:</strong> <span id="mode-status">Loading...</span></p>
                <p><strong>Last Update:</strong> <span id="last-update">-</span></p>
            </div>
        </div>

        <div class="controls">
            <div class="control-group">
                <h3>⚡ Power Control</h3>
                <button class="power-btn" onclick="sendCommand('power_toggle')" id="power-btn">
                    Toggle Power
                </button>
            </div>
            
            <div class="control-group">
                <h3>🎚️ Speed Control</h3>
                <button onclick="sendCommand('faster')">Faster ⬆️</button>
                <button onclick="sendCommand('slower')">Slower ⬇️</button>
            </div>
            
            <div class="control-group">
                <h3>🔄 Mode Control</h3>
                <button onclick="sendCommand('mode')">Change Mode</button>
            </div>
            
            <div class="control-group">
                <h3>🛠️ Utilities</h3>
                <button onclick="refreshStatus()">Refresh Status</button>
                <button onclick="clearLog()" style="background: #ff9800;">Clear Log</button>
            </div>
        </div>

        <div>
            <h3>📋 Command Log</h3>
            <div class="log" id="log">
                <div class="log-entry">System started...</div>
            </div>
        </div>
    </div>

    <script>
        let commandLog = [];
        
        function updateStatus(status) {
            document.getElementById('power-status').textContent = status.power ? 'ON 🟢' : 'OFF 🔴';
            document.getElementById('speed-status').textContent = status.speed;
            document.getElementById('mode-status').textContent = status.mode + 1;
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            
            // Update power button text
            const powerBtn = document.getElementById('power-btn');
            powerBtn.textContent = status.power ? 'Turn OFF' : 'Turn ON';
            powerBtn.className = status.power ? 'power-btn off' : 'power-btn';
        }
        
        function addLogEntry(message, type = 'info') {
            const log = document.getElementById('log');
            const timestamp = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
            
            commandLog.push({timestamp, message, type});
        }
        
        async function sendCommand(command) {
            addLogEntry(`Sending command: ${command}`, 'command');
            
            try {
                const response = await fetch('/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({command: command})
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    addLogEntry(`✅ ${result.message}`, 'success');
                    updateStatus(result.new_state);
                } else {
                    addLogEntry(`❌ Error: ${result.message}`, 'error');
                }
            } catch (error) {
                addLogEntry(`❌ Network error: ${error}`, 'error');
            }
        }
        
        async function refreshStatus() {
            addLogEntry('Refreshing status...', 'info');
            try {
                const response = await fetch('/status');
                const status = await response.json();
                updateStatus(status);
                addLogEntry('Status updated successfully', 'success');
            } catch (error) {
                addLogEntry(`❌ Failed to refresh status: ${error}`, 'error');
            }
        }
        
        function clearLog() {
            document.getElementById('log').innerHTML = '<div class="log-entry">Log cleared...</div>';
            commandLog = [];
        }
        
        // Auto-refresh status every 5 seconds
        setInterval(refreshStatus, 5000);
        
        // Initial load
        refreshStatus();
        
        // WebSocket for real-time updates (optional enhancement)
        function setupWebSocket() {
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'status_update') {
                    updateStatus(data.status);
                    addLogEntry(`🔄 Status updated via WebSocket`, 'info');
                }
            };
        }
        
        // Try to setup WebSocket (if supported)
        try {
            setupWebSocket();
        } catch (e) {
            console.log('WebSocket not available, using polling');
        }
    </script>
</body>
</html>
'''

def load_device_state():
    #Load current device state from file
    default_state = {"power": False, "speed": 0, "mode": 0}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return default_state

def save_device_state(state):
    #Save current device state to file
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def send_radio_signal(signal_pattern):
    #Convert command pattern to radio signals
    global gpio_initialized
    
    # Reinitialize GPIO if needed
    if not gpio_initialized:
        initialize_gpio()
    
    if not gpio_initialized:
        print("❌ Cannot send signal - GPIO not available")
        return False
        
    print(f"📡 Sending radio signal: {signal_pattern}")
    try:
        for bit in signal_pattern:
            GPIO.output(RF_PIN, bit)
            time.sleep(0.001)
        GPIO.output(RF_PIN, 0)
        return True
    except Exception as e:
        print(f"❌ Error sending radio signal: {e}")
        gpio_initialized = False
        return False

@app.route('/')
def index():
    #Serve the web interface
    return render_template_string(HTML_TEMPLATE)

@app.route('/execute', methods=['POST'])
def execute_command():
    data = request.json
    command = data.get('command')
    current_state = load_device_state()
    
    print(f"🎯 Received command: {command}")
    
    if command in COMMAND_SIGNALS:
        if command == "power_toggle":
            send_radio_signal(COMMAND_SIGNALS[command])
            current_state["power"] = not current_state["power"]
            save_device_state(current_state)
            response_msg = f"Device turned {'on' if current_state['power'] else 'off'}"
            
        elif command == "faster":
            send_radio_signal(COMMAND_SIGNALS[command])
            current_state["speed"] = min(5, current_state["speed"] + 1)
            save_device_state(current_state)
            response_msg = f"Speed increased to level {current_state['speed']}"
            
        elif command == "slower":
            send_radio_signal(COMMAND_SIGNALS[command])
            current_state["speed"] = max(0, current_state["speed"] - 1)
            save_device_state(current_state)
            response_msg = f"Speed decreased to level {current_state['speed']}"
            
        elif command == "mode":
            send_radio_signal(COMMAND_SIGNALS[command])
            current_state["mode"] = (current_state["mode"] + 1) % 3
            save_device_state(current_state)
            response_msg = f"Mode changed to {current_state['mode'] + 1}"
        
        print(f"✅ Command executed: {response_msg}")
        return jsonify({
            "status": "success", 
            "command": command,
            "new_state": current_state,
            "message": response_msg
        })
    else:
        error_msg = f"Unknown command: {command}"
        print(f"❌ {error_msg}")
        return jsonify({"status": "error", "message": error_msg})

@app.route('/status', methods=['GET'])
def get_status():
    status = load_device_state()
    return jsonify(status)

@app.route('/api/state', methods=['GET'])
def api_get_state():
    #API endpoint for getting state (for external applications)
    return jsonify(load_device_state())

@app.route('/api/command', methods=['POST'])
def api_send_command():
    #API endpoint for sending commands (for external applications)
    return execute_command()

if __name__ == '__main__':
    print("🚀 Starting Raspberry Pi Device Controller...")
    print("📡 Web interface available at: http://0.0.0.0:5000")
    print("⚡ Running as system service (production mode)")
    print("🎯 API endpoints:")
    print("   GET  http://0.0.0.0:5000/status")
    print("   POST http://0.0.0.0:5000/execute")
    print("   GET  http://0.0.0.0:5000/api/state")
    print("   POST http://0.0.0.0:5000/api/command")
    
    try:
        # Use production settings - no debug mode
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:

        cleanup_gpio()

