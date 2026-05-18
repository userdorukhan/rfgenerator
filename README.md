# rfgenerator

Main project files for the RF Generator for Engineering Solutions at Berkeley Consulting.

## Repository layout

```
.
├── Core/                  STM32 application code (main.c, drivers, BSP config)
│   ├── Inc/               headers (main.h, ad9851.h, ad603.h, …)
│   └── Src/               sources (main.c, ad9851.c, ad603.c, …)
├── Drivers/               STM32 HAL + Nucleo BSP (vendor code)
├── cmake/                 CubeMX-generated CMake configuration
├── pc-app/                PC-side controller GUI (Python)
│   ├── rf_controller.py
│   └── requirements.txt
├── CMakeLists.txt         Top-level build (firmware)
├── CMakePresets.json
├── RFGeneratormain.ioc    STM32CubeMX project
├── STM32H723XG_FLASH.ld   Linker script
└── startup_stm32h723xx.s  Startup assembly
```

## Firmware (STM32H723ZG Nucleo)

Open `RFGeneratormain.ioc` in STM32CubeMX, or build directly via CMake with the
provided presets. Flash to a Nucleo-H723ZG.

## PC controller

```bash
cd pc-app
pip install -r requirements.txt
python rf_controller.py
```

Sends UART commands over the Nucleo's ST-Link virtual COM port @ 115200 baud:

- `<num>[ Hz|kHz|MHz]` — set DDS output frequency (0 – 10 MHz)
- `gain <dB>` — AD603 VGA gain (0 – 80 dB, hard-capped at 1.0 V Vctl)
- `vctl <volts>` — AD603 control voltage directly
- `mute` — drop VGA gain to 0
- `sweep` — ramp 0 → 80 dB in 5 dB / 200 ms steps, ends muted
- `cal <v1> <db1> <v2> <db2>` — two-point gain calibration (RAM only)
- `status` — current frequency, Vctl, gain, calibration
