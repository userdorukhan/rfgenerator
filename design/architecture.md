# RF Generator – Architecture and Design

*Engineering Solutions at Berkeley Consulting*

---

## 1. Overview

The RF Generator is a pure-software signal synthesis library and command-line
tool written in Python.  It produces accurate periodic waveforms, applies
standard analogue-domain modulation schemes, and exports results to standard
file formats.

The software is designed for:

* Hardware-in-the-loop (HIL) testing where a software source feeds a DAC.
* Rapid prototyping and verification of RF receiver algorithms.
* Teaching and demonstration of fundamental RF concepts.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        rfgenerator                           │
│                                                              │
│  ┌──────────────────┐   ┌──────────────────┐                │
│  │  SignalGenerator │   │  FrequencySweep  │                │
│  │  (carrier)       │   │  (chirp)         │                │
│  └────────┬─────────┘   └────────┬─────────┘                │
│           │                      │                          │
│  ┌────────▼──────────────────────▼─────────┐                │
│  │            Modulation Layer             │                │
│  │   AmplitudeModulation  FrequencyModulation               │
│  └────────────────────────┬────────────────┘                │
│                           │                                  │
│  ┌────────────────────────▼────────────────┐                │
│  │            Output / Export              │                │
│  │   WavExporter (PCM WAV)  CsvExporter    │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │        CLI (rfgenerator / __main__)      │                │
│  │   generate │ modulate am/fm │ sweep      │                │
│  └─────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Module Descriptions

### 3.1 `signal_generator.py` – Core Signal Synthesis

**Class:** `SignalGenerator`

Generates a periodic waveform at a fixed carrier frequency.

| Parameter     | Type    | Description                          |
|---------------|---------|--------------------------------------|
| `frequency`   | float   | Carrier frequency (Hz)               |
| `amplitude`   | float   | Peak amplitude (V, default 1.0)      |
| `phase`       | float   | Initial phase offset (degrees)       |
| `waveform`    | Waveform| Sine / Square / Triangle / Sawtooth  |
| `sample_rate` | int     | Samples per second (default 1 MHz)   |
| `dc_offset`   | float   | DC bias voltage (V, default 0)       |

**Key methods:**

* `generate(duration)` → `(time_array, signal_array)`
* `generate_samples(time_axis)` → `signal_array`

**Supported waveforms:**

| Waveform  | Mathematical Form                                    |
|-----------|------------------------------------------------------|
| Sine      | `A · sin(2πft + φ)`                                 |
| Square    | `A · sgn(sin(2πft + φ))`                            |
| Triangle  | `A · (2/π) · arcsin(sin(2πft + φ))`                |
| Sawtooth  | `A · 2(ft − ⌊ft + ½⌋)` (rising ramp)               |

---

### 3.2 `modulation.py` – Analogue Modulation

#### `AmplitudeModulation`

Produces a DSB-LC AM signal:

```
s(t) = Ac · [1 + m · cos(2π·fm·t + φm)] · cos(2π·fc·t + φc)
```

| Parameter              | Description                           |
|------------------------|---------------------------------------|
| `carrier`              | `SignalGenerator` instance            |
| `modulation_frequency` | Message signal frequency (Hz)         |
| `modulation_index`     | m ∈ [0, 1]; 1.0 = 100% AM            |
| `modulation_phase`     | Message phase offset (degrees)        |

#### `FrequencyModulation`

Produces a narrowband or wideband FM signal:

```
s(t) = Ac · cos(2π·fc·t + β·sin(2π·fm·t + φm) + φc)
```

where β = Δf / fm is the modulation index (deviation ratio).

| Parameter              | Description                           |
|------------------------|---------------------------------------|
| `carrier`              | `SignalGenerator` instance            |
| `modulation_frequency` | Message signal frequency (Hz)         |
| `frequency_deviation`  | Peak deviation Δf (Hz)                |
| `modulation_phase`     | Message phase offset (degrees)        |

---

### 3.3 `sweep.py` – Frequency Sweep (Chirp)

**Class:** `FrequencySweep`

Generates a signal whose instantaneous frequency changes continuously from
`start_frequency` to `stop_frequency` over the given duration.  The phase
is obtained by analytically integrating the instantaneous frequency, ensuring
phase continuity throughout the sweep.

| Mode          | Frequency Profile                        |
|---------------|------------------------------------------|
| `LINEAR`      | f(t) = f₀ + (f₁ − f₀) · t / T          |
| `LOGARITHMIC` | f(t) = f₀ · (f₁/f₀)^(t/T)              |

---

### 3.4 `output.py` – Signal Export

#### `WavExporter`

Writes a 16-bit mono PCM WAV file.  Supports optional peak normalisation.
Suitable for audio-band signals and direct DAC playback.

#### `CsvExporter`

Writes a two-column CSV (`time_s`, `voltage_V`) for import into MATLAB,
Python (pandas/numpy), Excel, or oscilloscope analysis tools.

---

### 3.5 `cli.py` – Command-Line Interface

Three sub-commands are provided:

```
rfgenerator generate --frequency HZ [--waveform SHAPE] [--duration S] ...
rfgenerator modulate {am|fm} --carrier-frequency HZ --mod-frequency HZ ...
rfgenerator sweep --start HZ --stop HZ [--mode {linear|logarithmic}] ...
```

All sub-commands accept `--output FILE` where the format is inferred from
the file extension (`.csv` or `.wav`).

---

## 4. Data Flow

```
User / CLI
    │
    ▼
SignalGenerator.generate(duration)
    │   Returns (t: ndarray, signal: ndarray)
    │
    ├──► AmplitudeModulation.generate(duration)
    │        Wraps carrier with envelope
    │
    ├──► FrequencyModulation.generate(duration)
    │        Modulates carrier instantaneous phase
    │
    └──► FrequencySweep.generate(duration)
             Integrates instantaneous frequency
    │
    ▼
WavExporter.export(path, signal)
    or
CsvExporter.export(path, t, signal)
```

---

## 5. Design Decisions

### 5.1 Pure NumPy implementation

All signal generation uses NumPy array operations on pre-allocated time
arrays.  This avoids Python-level loops and achieves near-native performance
for signals with millions of samples.

### 5.2 Exact phase integration for sweeps

Rather than stepping the frequency sample-by-sample (which accumulates
numerical error), the sweep phase is computed analytically from the closed-
form integral of the instantaneous frequency.  This ensures the waveform
has no glitches or phase discontinuities.

### 5.3 Format-agnostic export

Exporters are separate from the generator classes, following the
single-responsibility principle.  New formats (HDF5, binary float32, etc.)
can be added without modifying the core generation logic.

### 5.4 Validation at construction time

Invalid parameters (negative frequency, out-of-range modulation index, etc.)
raise `ValueError` immediately at object construction so errors surface as
early as possible.

---

## 6. Testing Strategy

| Test module          | Coverage area                                |
|----------------------|----------------------------------------------|
| `test_signal_generator.py` | Validation, waveform shape, amplitude, phase |
| `test_modulation.py` | AM/FM validation, output shape, physics      |
| `test_sweep.py`      | Sweep validation, frequency profile accuracy |
| `test_output.py`     | WAV metadata, CSV round-trip, edge cases     |
| `test_cli.py`        | End-to-end CLI integration tests             |

Run the full suite with:

```bash
pytest
```

---

## 7. Future Enhancements

* **Pulse modulation (OOK / ASK / PSK / QAM)** – digital modulation schemes.
* **Noise injection** – AWGN and coloured noise addition.
* **IQ output** – complex-baseband (I/Q) signal pairs for SDR workflows.
* **Streaming / real-time output** – integration with PyAudio or sounddevice
  for live DAC playback.
* **GUI front-end** – a browser-based or desktop control panel.
* **Hardware abstraction layer** – driver bindings for bench instruments
  (Keysight, Rohde & Schwarz, National Instruments).
