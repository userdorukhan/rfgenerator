# Wiring & Hardware Setup

How to physically connect the STM32H723ZG Nucleo board to the AD9851 DDS module
and the Taidacent dual-AD603 VGA module, and how to verify it's safe before
applying power to the downstream high-voltage stage.

---

## ⚠️ READ THIS FIRST — AD603 safety

The AD603 control input **must never exceed 1.0 V**. Above ~1.2 V the device
self-oscillates, sending uncontrolled energy into the LM7171 driver → power
amplifier → step-up transformer → high-voltage electrodes. The downstream
voltage is in the kV range. Mistakes here can damage hardware and hurt people.

The firmware enforces this in three places:

1. `AD603_Init()` writes 0 V to the DAC **before** enabling the output channel,
   so PA4 is at 0 V the instant power comes up.
2. Every `gain` / `vctl` command path hard-clamps to ≤1.0 V regardless of what
   the caller asks for.
3. Boot order: `AD603_Init` runs **before** `AD9851_Init`, so the VGA is muted
   by the time RF appears at its input.

**You must still verify with a multimeter before connecting the AD603** — see
the pre-flight checklist at the bottom of this file.

---

## Pin assignments (STM32H723ZG Nucleo-144)

| Signal | STM32 pin | Nucleo header | Goes to |
|---|---|---|---|
| AD9851 W_CLK (word clock) | PG12 | CN10-16 | AD9851 module W_CLK pin |
| AD9851 FQ_UD (frequency update / latch) | PE9 | CN10-4 | AD9851 module FQ_UD pin |
| AD9851 DATA (serial data) | PE11 | CN10-6 | AD9851 module DATA pin |
| AD9851 RESET | PE14 | CN10-28 | AD9851 module RESET pin |
| AD603 control voltage | **PA4** (DAC1_OUT1) | CN7-17 | AD603 module **DA / Vgain** input |
| GND (shared) | any GND | CN7-8, CN7-11, etc. | AD9851 GND **and** AD603 AGND |
| UART TX (USART3) | PD8 | (internal to ST-Link VCP) | PC over USB |
| UART RX (USART3) | PD9 | (internal to ST-Link VCP) | PC over USB |

The UART pins are already routed internally to the Nucleo's onboard ST-Link.
Plugging the USB cable into the Nucleo gives you a virtual COM port at
115200 baud — no extra wiring needed for the PC link.

---

## STM32 ↔ AD9851 DDS module

The AD9851 is bit-banged over 4 GPIOs. No SPI peripheral is used, so the
wiring is straightforward.

```
STM32H723ZG          AD9851 module
─────────────        ─────────────
PG12  ──────────►    W_CLK
PE9   ──────────►    FQ_UD
PE11  ──────────►    DATA
PE14  ──────────►    RESET
GND   ──────────►    GND
5V (or 3.3V — see   VCC  (check your module — most accept 3.3V or 5V)
 module spec)
```

The AD9851 module's RF output (sine wave at the programmed frequency) is what
feeds the AD603's RF input.

---

## STM32 ↔ AD603 VGA module (Taidacent dual cascaded)

The AD603 is controlled by a single analog voltage from the STM32's internal
DAC. **Triple-check this connection before powering on.**

```
STM32H723ZG          AD603 module
─────────────        ────────────
PA4   ──────────►    DA  (control voltage input, sometimes labelled Vgain)
GND   ──────────►    AGND  (shared ground — mandatory)
                     +Vs / -Vs   (typically ±5 V, see module datasheet)
                     RF IN       ◄── from AD9851 sine output
                     RF OUT      ──► to LM7171 driver input
```

### Gain transfer (default firmware calibration)

| Vctl on PA4 | Cascaded gain |
|---|---|
| 0.000 V | 0 dB |
| 0.250 V | 20 dB |
| 0.500 V | 40 dB |
| 0.750 V | 60 dB |
| 1.000 V | 80 dB **(maximum allowed)** |

If your board doesn't track this exactly, run the two-point calibration
(`cal v1 db1 v2 db2` command — see [pc-app/README.md](../pc-app/README.md)).

---

## Power requirements

| Rail | Source | Notes |
|---|---|---|
| STM32 board | USB (ST-Link side) or external 5 V | Powers the MCU and ST-Link |
| AD9851 module VCC | from STM32 5 V/3.3 V or external | Check your specific module |
| AD603 ±Vs | external bench supply (typically ±5 V) | **Do not power from MCU rails** — the AD603 needs a clean analog supply |
| Common ground | wire all three GNDs together | Absolutely required for the DAC control voltage to mean anything |

---

## Pre-flight checklist — verify in this order

**Skip none of these. The cost of two minutes of multimeter work is much less
than the cost of a damaged AD603 or transformer.**

### 1. Smoke test the firmware alone (AD603 not connected yet)

1. Flash the firmware to the Nucleo. Power it from USB only.
2. Put a multimeter (DC volts, 2 V range) between PA4 and GND.
3. The reading must be **0.000 V ± a few millivolts** immediately at boot.
   - If you see ~3.3 V instead, the firmware is not the AD603-safe version.
     **Stop. Do not connect anything.** Check the boot sequence in
     [Core/README.md](../Core/README.md) and that `AD603_Init` runs before
     `AD9851_Init`.

### 2. Verify the firmware clamp holds

Open a serial terminal (or run the PC app — see
[pc-app/README.md](../pc-app/README.md)) and send these commands while
watching PA4 on the multimeter:

| Command | Expected PA4 reading |
|---|---|
| (just powered on) | 0.000 V |
| `vctl 0.25` | ~0.250 V |
| `vctl 0.5` | ~0.500 V |
| `vctl 1.0` | ~1.000 V |
| `vctl 2.5` | **still ~1.000 V** (this is the safety clamp — must hold) |
| `vctl 99` | **still ~1.000 V** |
| `gain 80` | ~1.000 V |
| `gain 200` | **still ~1.000 V** |
| `mute` | 0.000 V |
| `sweep` | ramps 0 V → 1 V over ~3.4 s, **ends back at 0 V** |

If any out-of-range command produces more than ~1.05 V on PA4, **do not connect
the AD603**. Stop and debug the firmware.

### 3. First-time AD603 connection

Only after step 2 passes:

1. Power everything off.
2. Wire PA4 → AD603 DA input. Wire STM32 GND → AD603 AGND.
3. Power on the AD603's ±Vs rails **with the RF input disconnected**.
4. Power on the STM32. Confirm with multimeter that the AD603 DA input is
   still 0 V.
5. Send `mute` from the PC app. Confirm 0 V.
6. Connect RF input from AD9851.
7. Slowly raise gain (`gain 10`, then `gain 20`, etc.) while watching the
   AD603 output on a scope. Stop and investigate at the first sign of
   oscillation, clipping, or anything unexpected.

### 4. Connecting downstream (LM7171 / PA / transformer)

This part is owned by Akshay (PA PCB) and Darren (transformer). Don't connect
the high-voltage stage until they sign off on the gain levels you should be
operating at and the input-amplitude limits the PA can handle.

---

## Bench setup photo / diagram

_(TODO: add a photo of the actual wired-up bench setup. A photo with labelled
wires is worth a lot more than this text when someone else is trying to
reproduce it.)_
