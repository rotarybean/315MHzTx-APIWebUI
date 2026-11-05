# 315MHzTx-APIWebUI

A web interface and HTTP API for replaying captured 315 MHz remote-control signals from a Raspberry Pi, plus an [Oobabooga text-generation-webui](https://github.com/oobabooga/text-generation-webui) extension that lets a locally hosted LLM trigger those commands from its replies.

```
 Browser / curl / other apps ──┐
                               ▼
 LLM reply with [CMD:TAG] ──► Oobabooga extension (script.py) ──HTTP──► Raspberry Pi (Flask) ──GPIO 17──► 315 MHz Tx ))) device
```

## How it came about

I used an RTL-SDR dongle and [Universal Radio Hacker](https://github.com/jopohl/urh) to capture and record the 315 MHz signals from a transmitter (remote). I wanted those signals to be sendable from a web UI, and also by my locally hosted Oobabooga LLM server.

A basic 315 MHz transmitter module is wired to GPIO 17 of a Raspberry Pi 3. `315MHz_Control_API_WebUI.py` runs as a service on the Pi, hosting the web interface and the API endpoints. `script.py` is the Oobabooga extension that watches the model's output for command tags and forwards them to the Pi.

## Contents

| File | Purpose |
|---|---|
| `315MHz_Control_API_WebUI.py` | Flask app for the Pi: web UI, REST API, and GPIO signal playback |
| `script.py` | Oobabooga extension that turns `[CMD:TAG]` tags in LLM output into API calls |

## Hardware

- Raspberry Pi (developed on a Pi 3) with GPIO access
- 315 MHz transmitter module, data pin on **GPIO 17** (BCM numbering, physical pin 11). Power and antenna per your module's specs.
- A remote and receiver you own, with signals captured beforehand (I used an RTL-SDR dongle and URH)

## Installation

### 1. Raspberry Pi: API and web UI

```bash
pip install flask RPi.GPIO
python3 315MHz_Control_API_WebUI.py
```

The server listens on port `5000`, and the UI is at `http://<pi-ip>:5000`. Device state is persisted to `device_state.json` in the directory the script is run from.

To keep it running as a service, a systemd unit along these lines works (adjust paths and user):

```ini
# /etc/systemd/system/315mhz-control.service
[Unit]
Description=315 MHz control API and web UI
After=network.target

[Service]
WorkingDirectory=/opt/315MHzTx-APIWebUI
ExecStart=/usr/bin/python3 /opt/315MHzTx-APIWebUI/315MHz_Control_API_WebUI.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now 315mhz-control
```

### 2. LLM server: Oobabooga extension

1. Create a folder for the extension, named whatever you like, so the structure is:
   ```
   text-generation-webui/extensions/[ext_name]/script.py
   ```
2. Open `script.py` and set `self.pi_endpoint` to your Pi's address (the placeholder is `http://[ENDPOINT_IP]:5000`).
3. Restart the LLM service. The extension will then appear in the WebUI under **Session → Extensions & Flags**; enable it there.

The extension needs the `requests` package, which is normally already present in the text-generation-webui environment.

## Using it

### Web UI

Open `http://<pi-ip>:5000`. The page has buttons for power toggle, faster, slower, and mode, along with a status card and a command log. Status refreshes every 5 seconds.

### API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Current device state |
| `GET` | `/api/state` | Same as `/status`, for external applications |
| `POST` | `/execute` | Send a command |
| `POST` | `/api/command` | Same as `/execute`, for external applications |

Commands: `power_toggle`, `faster`, `slower`, `mode`.

```bash
# Get state
curl http://<pi-ip>:5000/api/state
# {"mode": 0, "power": false, "speed": 0}

# Send a command
curl -X POST http://<pi-ip>:5000/api/command \
     -H "Content-Type: application/json" \
     -d '{"command": "faster"}'
# {"command": "faster", "message": "Speed increased to level 1",
#  "new_state": {"mode": 0, "power": false, "speed": 1}, "status": "success"}
```

An unknown command returns `{"status": "error", "message": "Unknown command: ..."}`.

The Pi keeps a simple tracked state: `power` (on/off), `speed` (0 to 5), and `mode` (cycles through 3 modes, shown as 1 to 3).

### LLM control

Once the Pi service is running and the extension is installed, the model needs to know it has control capabilities. The extension looks for tags of the form `[CMD:TAG]` in the model's replies, sends the matching command to the Pi, and strips the tag from the text shown to you.

This is a very basic "Device Controller" character for Oobabooga WebUI, SillyTavern, etc.:

```json
{
    "char_name": "Device Controller",
    "char_persona": "You control devices using [CMD:TAG] commands. Available commands: [CMD:POWER_TOGGLE], [CMD:FASTER], [CMD:SLOWER], [CMD:MODE]. Always include exactly one [CMD:TAG] when controlling devices.",
    "example_dialogue": "User: turn on the device\nAssistant: I'll turn it on. [CMD:POWER_TOGGLE]\n\nUser: make it faster\nAssistant: Increasing speed. [CMD:FASTER]\n\nUser: change mode\nAssistant: Changing mode now. [CMD:MODE]\n\nUser: slow down\nAssistant: Slowing it down. [CMD:SLOWER]\n\nUser: turn it off\nAssistant: Turning off. [CMD:POWER_TOGGLE]"
}
```

I've found it works best to fold the `char_persona` instructions into an existing character, if you have one. During initial setup and training, keep an eye on the Pi's WebUI. You'll want to be sure the AI is only sending the *right* commands at the *right* times.

## Adapting it to your own device

Command signals live in the `COMMAND_SIGNALS` dictionary in `315MHz_Control_API_WebUI.py`. Each is a list of bits that is played out on GPIO 17 at **1 ms per bit**, ending with the pin driven low. To control a different device:

1. Capture its remote with an RTL-SDR and URH, and demodulate the signal to bits.
2. Replace or add entries in `COMMAND_SIGNALS`.
3. If you add commands, add matching handling in `execute_command()` and the buttons in `HTML_TEMPLATE`, and update `available_commands` in `script.py` and your character's persona.

## Notes and limitations

- **State is assumed, not read back.** A 315 MHz transmitter is one-way, so the tracked power, speed, and mode are the Pi's best guess based on commands it has sent. If the device is also operated with its physical remote, or a transmission is missed, the displayed state will drift out of sync.
- **Timing is software-generated.** Bits are timed with `time.sleep(0.001)` on a non-real-time OS, so bit timing can jitter. If a device is unreliable, this is a likely cause.
- **No authentication.** The server binds to `0.0.0.0` and anyone who can reach port 5000 can send commands. Keep it on your local network and do not expose it to the internet.
- **LLMs can misfire.** A model might send a command you did not intend or send several in one reply, so test the character before relying on it.
- **Use responsibly.** Only transmit to equipment you own and keep within your local radio regulations.

## Credits

- [Universal Radio Hacker](https://github.com/jopohl/urh) by @jopohl for signal capture and analysis
- [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui)
- Written by Spenser Fenton ([@rotarybean](https://github.com/rotarybean))
