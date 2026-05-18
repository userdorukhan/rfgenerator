# RF Generator

Programmable RF source for the Engineering Solutions @ Berkeley project. A
**STM32H723ZG Nucleo** drives an **AD9851 DDS** (sine wave 0–10 MHz) into a
**dual-cascaded AD603 VGA** (0–80 dB gain, controlled by a single analog
voltage), which feeds an LM7171 driver, a power amplifier, and a step-up
transformer that produces the high-voltage output used by the rest of the
system.

This repository contains the **firmware** for the STM32 and a **PC-side GUI**
for controlling it over the Nucleo's USB virtual COM port. Other parts of the
project (simulations, PA PCB, transformer research) live in separate
sub-projects owned by other team members — see [Team & contacts](#team--contacts)
below.

---

## ⚠️ Safety first

The output stage produces ~1.5 kV. The AD603 VGA control voltage **must never
exceed 1.0 V** — above ~1.2 V the VGA self-oscillates and slams uncontrolled
energy down the chain.

The firmware enforces this in multiple layers (boot order, command clamps,
mute-on-init). Before connecting hardware downstream of the STM32, **follow
the multimeter pre-flight checklist** in
[docs/WIRING.md](docs/WIRING.md#pre-flight-checklist--verify-in-this-order).

---

## Repository structure

```
rfgenerator/
├── Core/                          Application firmware (your starting point)
│   ├── Inc/                       Headers (main.h, ad9851.h, ad603.h, …)
│   ├── Src/                       Sources (main.c, ad9851.c, ad603.c, …)
│   └── README.md                  ◄── firmware architecture, commands, build
│
├── pc-app/                        Python GUI to drive the firmware
│   ├── rf_controller.py
│   ├── requirements.txt
│   └── README.md                  ◄── install, UI walkthrough, workflows
│
├── docs/
│   └── WIRING.md                  ◄── pinout, hookup, pre-flight checklist
│
├── Drivers/                       STM32 HAL + Nucleo BSP (vendor — don't edit)
├── cmake/                         CubeMX-generated build config
├── CMakeLists.txt                 Top-level build
├── CMakePresets.json
├── RFGeneratormain.ioc            STM32CubeMX project file
├── STM32H723XG_FLASH.ld           Linker script
└── startup_stm32h723xx.s          Startup assembly
```

Every folder you might actually need to read or edit has its own README.
`Drivers/` and `cmake/` are vendor / auto-generated and shouldn't be touched
by hand.

---

## Quick start

If you've never touched this project before, do these three things in order:

1. **Read the safety section** above and skim
   [docs/WIRING.md](docs/WIRING.md). Do not skip this if you're going to
   power anything up.
2. **Build & flash the firmware** — see
   [Core/README.md](Core/README.md#build--flash). The Nucleo's onboard
   ST-Link makes this a USB-cable-and-go affair.
3. **Run the PC controller** — see
   [pc-app/README.md](pc-app/README.md). With the Nucleo plugged in, the
   app finds the COM port, you click Connect, and you can start sending
   commands.

You can also drive the firmware from any serial terminal at 115200 baud —
the GUI is convenience, not a hard requirement. Full command syntax lives
in [Core/README.md](Core/README.md#uart-command-protocol).

---

## What can someone with minimal context actually do here?

| Goal | Where to look |
|---|---|
| Build & flash the firmware to a Nucleo | [Core/README.md → Build & flash](Core/README.md#build--flash) |
| Understand the boot sequence and why the order matters | [Core/README.md → SAFETY-CRITICAL boot order](Core/README.md#safety-critical-boot-order) |
| Add a new UART command | [Core/README.md → Adding or modifying commands](Core/README.md#adding-or-modifying-commands) |
| Change the DDS reference clock or output range | [Core/README.md → Modifying the DDS reference clock](Core/README.md#modifying-the-dds-reference-clock-or-output-range) |
| Wire up the AD603 / AD9851 to the STM32 | [docs/WIRING.md](docs/WIRING.md) |
| Verify the AD603 control voltage clamp is working | [docs/WIRING.md → Pre-flight checklist](docs/WIRING.md#pre-flight-checklist--verify-in-this-order) |
| Run the PC GUI and send commands | [pc-app/README.md](pc-app/README.md) |
| Calibrate the gain curve to a specific board | [pc-app/README.md → Run a calibration](pc-app/README.md#run-a-calibration) |
| Add a new button or control to the GUI | [pc-app/README.md → Modifying the app](pc-app/README.md#modifying-the-app) |

---

## Hardware bill of materials (firmware/UI portion)

| Item | Notes |
|---|---|
| ST Nucleo-H723ZG | Microcontroller dev board. USB-C cable for power + ST-Link. |
| AD9851 DDS module | Generic AD9851 board; 30 MHz reference assumed in firmware (changeable). |
| Taidacent dual-AD603 VGA module | Two AD603s cascaded. ~80 dB cascaded gain at 1.0 V Vctl. |
| ±5 V bench supply | For the AD603 module. Do not power from MCU rails. |
| Jumper wires | 5 for AD9851, 2 for AD603 (control + GND), shared ground. |

The downstream stages (LM7171 driver, power amplifier, step-up transformer,
electrodes) are owned by other team members — see below.

---

## Team & contacts

| Area | Owner | Folder in this repo |
|---|---|---|
| Firmware (STM32) | Dorukhan, Krish | [`Core/`](Core/) |
| PC controller (Python GUI) | Dorukhan, Krish | [`pc-app/`](pc-app/) |
| Wiring & hookup | Dorukhan, Krish | [`docs/WIRING.md`](docs/WIRING.md) |
| Simulations | Carolyn | _(separate folder, TBD)_ |
| Power amplifier PCB | Akshay | _(separate folder, TBD)_ |
| Transformer research | Darren | _(separate folder, TBD)_ |

For repo access ask Dorukhan.

---

## Future work / handoff notes

- **No persistent calibration.** AD603 cal is RAM-only, redone after every
  power cycle. If long-term cal stability matters, add flash storage.
- **No watchdog.** A firmware hang with Vctl > 0 stays at Vctl > 0 until
  manual reset. Adding the IWDG would force a recovery to the muted boot
  state.
- **Sweep is blocking.** While `sweep` is running the UART can't accept
  other commands. A non-blocking, abortable variant would be useful for
  longer sweeps or for emergency-mute scenarios.
- **No closed-loop amplitude control.** Gain is open-loop; if the user wants
  the actual output to track a setpoint, you'd need to feed back a measured
  amplitude (peak-detect + ADC) and run a control loop in firmware.
