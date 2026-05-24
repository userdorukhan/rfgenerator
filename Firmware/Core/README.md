# Firmware (STM32H723ZG)

Application code for the RF generator. Targets a Nucleo-H723ZG board.

## What it does

1. Boots with the **AD603 VGA muted** (control voltage = 0 V).
2. Initializes the **AD9851 DDS** at 1 MHz (becomes the RF source feeding the
   VGA).
3. Listens on UART (USART3 → ST-Link virtual COM port @ 115200 baud) for
   single-line text commands from the PC.
4. Applies frequency changes to the AD9851 and gain changes to the AD603 as
   commands arrive.

The AD603 control path goes through the STM32's internal DAC (DAC1 channel 1
on pin **PA4**), driven directly via registers — no HAL DAC driver in the
build.

## Source file map

| File | Purpose |
|---|---|
| `Src/main.c` | Boot sequence, main loop, UART command parser |
| `Src/ad9851.c` / `Inc/ad9851.h` | AD9851 DDS driver (bit-bang over 4 GPIOs) |
| `Src/ad603.c` / `Inc/ad603.h` | AD603 VGA driver (direct DAC register access, safety clamps) |
| `Src/stm32h7xx_it.c` | Interrupt vectors — most importantly `USART3_IRQHandler` |
| `Src/stm32h7xx_hal_msp.c` | HAL MSP init (mostly empty, BSP COM init handled by Nucleo BSP) |
| `Src/system_stm32h7xx.c` | Clock-tree boot code (CMSIS-generated) |
| `Src/syscalls.c`, `Src/sysmem.c` | newlib stubs (printf goes to UART via BSP) |
| `Inc/main.h` | Pin definitions for AD9851 (see [docs/WIRING.md](../docs/WIRING.md)) |
| `Inc/stm32h7xx_hal_conf.h` | Which HAL modules are compiled in |
| `Inc/stm32h7xx_nucleo_conf.h` | Enables `USE_BSP_COM_FEATURE` and `USE_COM_LOG` |

`Drivers/` and `cmake/` at the repo root are vendor / auto-generated code and
should not be hand-edited.

## SAFETY-CRITICAL boot order

In `main()` the order is:

```
MX_GPIO_Init()      // DDS pins
AD603_Init(&hvga)   // ← VGA muted FIRST (PA4 = 0 V)
AD9851_Init(&hdds)  // ← RF only enabled AFTER VGA is safe
BSP_COM_Init(...)   // UART up
HAL_NVIC_EnableIRQ(USART3_IRQn)
Console_StartRx()   // start listening for commands
```

**Do not reorder these.** If `AD9851_Init` runs before `AD603_Init`, RF
appears at the VGA input while the DAC is in an unknown state — the VGA may
briefly sit at high gain and slam the downstream amplifier and transformer.
See [docs/WIRING.md](../docs/WIRING.md#-read-this-first--ad603-safety) for
the consequences.

## UART command protocol

Send any of these as a single ASCII line terminated with CR, LF, or both.
Commands are case-sensitive. Empty lines are ignored. A 250 ms idle timeout
also acts as a line terminator.

### Frequency

| Command | Effect |
|---|---|
| `7.7 MHz` | Set DDS to 7,700,000 Hz |
| `1.1 kHz` | Set DDS to 1,100 Hz |
| `7700000 Hz` or `7700000` | Set DDS to 7,700,000 Hz |
| `7.7M` / `1.1k` | Shorthand forms |

Range is hard-clamped to 0–10 MHz.

### Amplitude (AD603 VGA)

| Command | Effect |
|---|---|
| `gain 40` | Set VGA gain to 40 dB |
| `vctl 0.5` | Set AD603 control voltage to 0.5 V directly |
| `mute` | Drive VGA to 0 V (≈ 0 dB / minimum gain) |
| `sweep` | Ramp 0 → 80 dB in 5 dB / 200 ms steps, end muted |
| `sweep <s> <e> <step> <ms>` | Custom sweep, e.g. `sweep 20 60 2 100` |
| `cal <v1> <db1> <v2> <db2>` | Two-point calibration of the gain curve (RAM only, lost on reset) |

All gain and voltage paths are hard-clamped to ≤1.0 V (≈ 80 dB) in the driver.

### Diagnostics

| Command | Effect |
|---|---|
| `status` | Print current frequency, Vctl, gain, calibration coefficients |

The boot banner prints these too, so just opening the serial terminal shows
the syntax.

## Build & flash

### Option A — STM32CubeIDE (recommended for someone new)

1. Open STM32CubeIDE.
2. `File → Open Projects from File System…` → select the repo root.
3. Right-click the project → `Build`.
4. Right-click → `Run As → STM32 C/C++ Application`.

The Nucleo's ST-Link is recognized automatically over USB.

### Option B — Command-line CMake (used by `CMakePresets.json`)

```bash
cmake --preset Debug
cmake --build --preset Debug
# Resulting ELF is in build/Debug/RFGeneratormain.elf
# Flash with: STM32_Programmer_CLI -c port=SWD -w build/Debug/RFGeneratormain.elf -rst
```

You need: `arm-none-eabi-gcc` toolchain, `cmake ≥ 3.22`, `ninja`, and ST's
`STM32_Programmer_CLI` for flashing.

## Adding or modifying commands

All command parsing lives in `Console_ProcessCommand()` in `Src/main.c`. To
add a new command:

1. Add a `strncmp(command, "yourcmd ", N) == 0` branch alongside `gain`,
   `vctl`, `mute`, etc.
2. Parse arguments with `strtod` / `strtoul`.
3. Print an acknowledgement so the user sees their command was handled.
4. If your command needs to do work in the main loop (not synchronously
   inside the parser), set a flag and handle it in the `while(1)` block.

When adding a UI-facing command, also update [pc-app/README.md](../pc-app/README.md)
and `rf_controller.py` if it should have a button or field.

## Modifying the DDS reference clock or output range

If you swap the AD9851 module for one with a different reference oscillator,
edit these in `main.c`:

```c
hdds.reference_clock_hz = 30000000U;   // change to your module's xtal Hz
hdds.enable_x6_multiplier = 1U;        // 1 = 6× PLL on, 0 = bypass
```

Also update `DDS_MAX_FREQUENCY_HZ` near the top of `main.c` if you want the
input clamp to allow more (e.g. higher with a faster reference).

## Modifying the AD603 calibration default

Default cascaded transfer (0 V → 0 dB, 1 V → 80 dB) is set in
`Inc/ad603.h`:

```c
#define AD603_DEFAULT_DB_PER_V    (80.0f)
#define AD603_DEFAULT_DB_AT_0V    (0.0f)
```

The hard safety cap is also there:

```c
#define AD603_MAX_VCTL_V          (1.0f)   // ← do NOT raise this
```

**Do not increase `AD603_MAX_VCTL_V` past 1.0 V**. The downstream high-voltage
chain depends on this cap being enforced.

## Known limitations / future work

- The sweep command is blocking — UART is unresponsive for the ~3.4 s
  duration. A non-blocking, abortable variant would be nice if longer or
  slower sweeps become useful.
- Calibration is RAM-only. After every reboot, the default cal is used.
  Add flash storage (e.g. one of the small data sectors) if persistent cal
  becomes important.
- No watchdog. If the firmware hangs with Vctl > 0, the VGA stays at gain
  until reset. Adding the IWDG and feeding it in the main loop would force
  a recovery to the muted boot state.
