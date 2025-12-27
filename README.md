# 315MHzTx-APIWebUI
A simple API WebUI package for sending 315MHz commands via a Tx-enabled RaspberryPi

Using an RTL-SDR dongle and Universal Radio Hacker software from @jopohl/urh, I captured and recorded 315MHz radio signals from a transmitter.  I needed these signals to be transmittable via WebUI commands or via commands with my locally-hosted Oobabooga LLM server. 

Using a basic 315MHz Tx connected to GPIO pin 17 of a RaspberryPi 3, I wrote 315MHz_Control_API_WebUI.py to run as a service on the Pi, hosting a web interface and API endpoint.  

The extension script, aptly named 'script.py', is to be placed in the Oobabooga extension folder with its own subfolder - name it whatever you want, so long as the structure is `text-generation-webui/extensions/[ext_name]/script.py`.  Restart the LLM service to find the extension listed in the Oobabooga WebUI Session/Extensions & Flags menu.  

Once the RaspberryPi is running the 315MHz_Control_API_WebUI.py script and the extension has been embedded in the LLM installation, you'll need to indicate to the LLM that it has control capabilities.  The following is a very basic example of a "Device Controller" character to be used in Ooobabooga WebUI, SillyTavern, etc:

{
    "char_name": "Device Controller",
    "char_persona": "You control devices using [CMD:TAG] commands. Available commands: [CMD:POWER_TOGGLE], [CMD:FASTER], [CMD:SLOWER], [CMD:MODE]. Always include exactly one [CMD:TAG] when controlling devices.",
    "example_dialogue": "User: turn on the device\nAssistant: I'll turn it on. [CMD:POWER_TOGGLE]\n\nUser: make it faster\nAssistant: Increasing speed. [CMD:FASTER]\n\nUser: change mode\nAssistant: Changing mode now. [CMD:MODE]\n\nUser: slow down\nAssistant: Slowing it down. [CMD:SLOWER]\n\nUser: turn it off\nAssistant: Turning off. [CMD:POWER_TOGGLE]"
}

However I have found it's best to integrate the information in "char_persona" into an existing character, if one exists.  When using an LLM to control signal outputs, during inital setup and training, keep an eye on the WebUI for the Pi - you'll want to make sure the AI is only sending the *right* commands at the *right* times.  
