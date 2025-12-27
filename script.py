import requests
import re

class fmachRadioController:
    def __init__(self):
        self.pi_endpoint = "http://192.168.254.154:5000"  # ← TODO: CHANGE THIS
        self.available_commands = {
            "power_toggle": "Toggle power on/off",
            "faster": "Increase speed", 
            "slower": "Decrease speed",
            "mode": "Change mode"
        }
        self.current_state = None
        self.update_status()
    
    def update_status(self):
        try:
            response = requests.get(f"{self.pi_endpoint}/status", timeout=3)
            self.current_state = response.json()
        except Exception as e:
            print(f"Status update failed: {e}")
            self.current_state = {"power": False, "speed": 0, "mode": 0}
    
    def send_to_pi(self, command):
        payload = {"command": command}
        try:
            response = requests.post(
                f"{self.pi_endpoint}/execute",
                json=payload,
                timeout=5
            )
            result = response.json()
            if result["status"] == "success":
                self.current_state = result["new_state"]
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

class CommandProcessor:
    def __init__(self):
        self.controller = fmachRadioController()
        self.command_pattern = r'\[CMD:(\w+)\]'
    
    def process_ai_response(self, text):
        # Update state before processing
        self.controller.update_status()
        
        # Find commands in the response
        commands = re.findall(self.command_pattern, text)
        
        # Execute each command
        executed_commands = []
        for command in commands:
            if command.lower() in [cmd.lower() for cmd in self.controller.available_commands]:
                result = self.controller.send_to_pi(command.lower())
                print(f"Executed {command}: {result}")
                executed_commands.append(command.lower())
        
        # Remove command tags from display
        clean_text = re.sub(self.command_pattern, '', text).strip()
        
        return clean_text

# Oobabooga integration
processor = CommandProcessor()

def input_modifier(string):
    return string

def output_modifier(string):
    return processor.process_ai_response(string)

def ui():
    # Optional: Add web UI elements
    pass