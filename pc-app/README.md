# PC Controller

Cross-platform desktop GUI for sending UART commands to the RF generator
firmware. Built with **customtkinter** (Tkinter under the hood, dark modern
look) and **pyserial**.

## Install

Python 3.10 or newer. From this folder:

```bash
pip install -r requirements.txt
```

## Run

```bash
python rf_controller.py
```

A window opens. No CLI arguments — port and baud are chosen from dropdowns.

## What the firmware expects

The PC app and firmware speak a simple line-oriented protocol over the
Nucleo's ST-Link virtual COM port at **115200 baud, 8N1**. Full command
reference is in [../Core/README.md](../Core/README.md#uart-command-protocol).
The app just sends those strings followed by `\r\n` and prints the firmware's
replies in the console pane.

This means you can also drive the firmware from any serial terminal
(PuTTY, screen, minicom). The GUI is a convenience, not a requirement.

## UI walkthrough

```
┌──────────────────────────────────────────────────────┐
│ Connection                                           │
│  [COM3 ▼] [↻] [115200 ▼] [Connect]                   │
│  ●  Disconnected                                     │
├──────────────────────────────────────────────────────┤
│ Output Frequency                                     │
│         7.7 MHz                                      │
│  ─────●──────────────────────────                    │
│  0 Hz                          10 MHz                │
│  [7.7][MHz ▼] [Set Frequency]                        │
│  Presets: [1 MHz][3.5 MHz][7 MHz][7.7 MHz][10 MHz]   │
├──────────────────────────────────────────────────────┤
│ VGA Gain (AD603)   0 V → 0 dB  1 V → 80 dB  CAP 1.0V │
│         0.0 dB                                       │
│  Vctl = 0.000 V    ×1.0 V/V                          │
│  ●─────────────────────────────                      │
│  0 dB                          80 dB                 │
│  [0–80] dB [Set Gain] [Mute] [Sweep] [Calibrate…]    │
│  Presets: [0 dB][20 dB][40 dB][60 dB][80 dB]         │
├──────────────────────────────────────────────────────┤
│ Console                                       [Clear]│
│  [12:34:56] Connected to COM3 at 115200 baud         │
│  [12:34:56] [DDS] Applied 7700000 Hz                 │
│  …                                                   │
└──────────────────────────────────────────────────────┘
```

### Connection panel
- **Port dropdown**: lists available serial ports. Hit ↻ if you plugged the
  Nucleo in after launching.
- **Baud**: 115200 is correct for this firmware. Other rates are listed for
  convenience only.
- **Connect / Disconnect**: green when disconnected, red when connected.

### Frequency panel
- Slider: drag to sweep 0–10 MHz. Sends the new frequency 120 ms after you
  stop moving (debounced so it doesn't flood UART).
- Manual entry: type a number, pick a unit, click **Set Frequency** or
  press Enter. Equivalent to typing `7.7 MHz` in a terminal.
- Presets: one-click common values.

### VGA Gain panel
- Slider: drag 0–80 dB. Sub-line shows the corresponding control voltage and
  linear gain so the relationship is visible.
- Manual entry: type dB, click **Set Gain** or press Enter.
- **Mute** (red): drops gain to 0. Use this when in doubt.
- **Sweep** (purple): runs the firmware's blocking `sweep` command. Output
  ramps 0 → 80 dB in 5 dB / 200 ms steps over ~3.4 seconds, then ends
  muted. **The UART is unresponsive during the sweep** — wait for the
  `Sweep done. Muted.` line.
- **Calibrate…**: opens a small dialog asking for `V1, Gain1, V2, Gain2`
  (two-point calibration). The values are sent as `cal v1 db1 v2 db2`.
  Calibration is **RAM only** — lost on reset.

### Console pane
- Shows everything sent (lines starting with `>`) and everything received
  from the firmware (timestamped).
- **Clear** wipes the pane (does not reset the firmware).

## Common workflows

### "Set 7.7 MHz at 40 dB gain"

1. Connect to the COM port.
2. Type `7.7` in the frequency entry, unit `MHz`, press Enter (or click a
   preset).
3. Drag the gain slider to 40 dB, or type `40` and press Enter.

The output is on the AD603's RF OUT. Mute first if anything looks off.

### "Verify the firmware before connecting the AD603"

Follow the pre-flight checklist in [../docs/WIRING.md](../docs/WIRING.md#pre-flight-checklist--verify-in-this-order)
— this app is what you use to issue the test commands (`vctl 0.5`, etc.)
while watching PA4 on a multimeter.

### "Run a calibration"

1. With known RF amplitude into the AD603 RF input, send `vctl 0.20` and
   measure the actual cascaded gain on a scope (output / input in dB).
   Note the result, e.g. 18 dB.
2. Send `vctl 0.80`, measure again — e.g. 62 dB.
3. Click **Calibrate…**, fill in `V1=0.2, Gain1=18, V2=0.8, Gain2=62`,
   click **Apply Calibration**.
4. Subsequent `gain X` commands now use the corrected slope/offset.
5. `status` will show the new slope and offset.

## Modifying the app

The app is one file (~340 lines): `rf_controller.py`. Structure:

- `RFGeneratorApp.__init__` — creates the window, calls `_build_ui` and
  `_refresh_ports`.
- `_build_ui` — lays out the connection, frequency, gain, and console
  frames using `customtkinter` widgets.
- `_connect` / `_disconnect` / `_read_loop` — serial port lifecycle.
  `_read_loop` runs in a background thread and reposts incoming lines onto
  the Tk event loop via `self.after(0, …)`.
- `_send_from_*_entry`, `_apply_*`, `_on_*_slider_move`, `_send_*_command` —
  command emitters for frequency and gain. Slider movement is debounced
  through a 120 ms `self.after` timer.
- `_send_raw` — single chokepoint that actually writes to the serial port
  and logs the action. Add new commands here.

### To add a new button or command

1. In `_build_ui`, create the widget and wire its `command=…` to a new
   method on `self`.
2. In that method, call `self._send_raw("yourcmd <args>\r\n", "log message")`.
3. If the firmware doesn't accept the command yet, add a parser branch in
   `Core/Src/main.c` (see [../Core/README.md](../Core/README.md#adding-or-modifying-commands)).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| No ports in dropdown | Nucleo not plugged in, or ST-Link drivers missing. Plug in and hit ↻. |
| "Failed to connect: could not open port" | Another program owns the port (CubeIDE console, PuTTY, etc). Close it. |
| Connected but no output in console | Wrong baud, or firmware not flashed with the AD603-safe version. Press the Nucleo's reset button — you should see the boot banner. |
| `[WARN] Not connected` after clicking Set | The Connect button wasn't pressed (or the connection dropped). Reconnect. |
| Slider moves but value doesn't update on the board | Connection dropped mid-session. Disconnect and reconnect. |
