# RF Generator

**Engineering Solutions at Berkeley Consulting**

A Python software RF signal generator that synthesises, modulates, sweeps, and
exports radio-frequency waveforms for engineering analysis and testing.

---

## Features

| Feature | Details |
|---------|---------|
| **Waveforms** | Sine, Square, Triangle, Sawtooth |
| **Modulation** | Amplitude Modulation (AM), Frequency Modulation (FM) |
| **Frequency sweep** | Linear and Logarithmic chirp signals |
| **Export formats** | 16-bit PCM WAV, CSV (time + voltage) |
| **CLI** | `generate`, `modulate`, `sweep` sub-commands |
| **Pure NumPy** | Fast, vectorised implementation – no sample-level Python loops |

---

## Installation

```bash
pip install -e ".[dev]"
```

Requires Python ≥ 3.9 and NumPy ≥ 1.24.

---

## Quick Start

### Python API

```python
from rfgenerator import SignalGenerator, Waveform, CsvExporter

# 1 MHz sine wave, 1 ms duration, 1 V peak
gen = SignalGenerator(frequency=1e6, amplitude=1.0, waveform=Waveform.SINE,
                      sample_rate=10_000_000)
t, signal = gen.generate(duration=1e-3)

CsvExporter().export("output.csv", t, signal)
```

```python
from rfgenerator import SignalGenerator, FrequencyModulation, WavExporter

carrier = SignalGenerator(frequency=100_000, amplitude=1.0, sample_rate=1_000_000)
fm = FrequencyModulation(carrier, modulation_frequency=1000, frequency_deviation=5000)
t, signal = fm.generate(duration=1e-3)

WavExporter(sample_rate=1_000_000).export("fm_signal.wav", signal)
```

```python
from rfgenerator import FrequencySweep, SweepMode

sweep = FrequencySweep(start_frequency=1e6, stop_frequency=10e6,
                       amplitude=1.0, mode=SweepMode.LINEAR, sample_rate=50_000_000)
t, signal = sweep.generate(duration=1e-3)
```

### Command-Line Interface

```bash
# Generate a 1 kHz square wave and save as WAV
python -m rfgenerator generate \
    --frequency 1000 --waveform square --duration 0.1 \
    --sample-rate 44100 --output square.wav

# AM modulation: 100 kHz carrier, 1 kHz message, 80% modulation
python -m rfgenerator modulate am \
    --carrier-frequency 100000 --mod-frequency 1000 \
    --mod-index 0.8 --duration 0.01 --output am_signal.csv

# FM modulation: 100 kHz carrier, 1 kHz message, 5 kHz deviation
python -m rfgenerator modulate fm \
    --carrier-frequency 100000 --mod-frequency 1000 \
    --deviation 5000 --duration 0.01 --output fm_signal.csv

# Linear frequency sweep: 1 kHz → 10 kHz over 100 ms
python -m rfgenerator sweep \
    --start 1000 --stop 10000 --mode linear \
    --duration 0.1 --sample-rate 44100 --output sweep.wav
```

Run `python -m rfgenerator --help` for full usage information.

---

## Project Structure

```
rfgenerator/
├── src/
│   └── rfgenerator/
│       ├── __init__.py          # Public API
│       ├── __main__.py          # python -m rfgenerator entry point
│       ├── signal_generator.py  # Core waveform synthesis
│       ├── modulation.py        # AM / FM modulation
│       ├── sweep.py             # Frequency sweep (chirp)
│       ├── output.py            # WAV and CSV exporters
│       └── cli.py               # Command-line interface
├── tests/
│   ├── test_signal_generator.py
│   ├── test_modulation.py
│   ├── test_sweep.py
│   ├── test_output.py
│   └── test_cli.py
├── design/
│   └── architecture.md          # Architecture and design document
├── examples/
│   └── quickstart.py            # Runnable usage examples
├── pyproject.toml
└── requirements.txt
```

---

## Running the Tests

```bash
pytest
# or with coverage
pytest --cov=rfgenerator --cov-report=term-missing
```

---

## Design Documentation

See [`design/architecture.md`](design/architecture.md) for:

* System architecture diagram
* Module descriptions and signal-processing formulae
* Design decisions (phase-accurate sweeps, pure-NumPy implementation, etc.)
* Testing strategy
* Future enhancement roadmap
