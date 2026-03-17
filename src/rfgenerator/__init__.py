"""
RF Generator – Engineering Solutions at Berkeley Consulting
===========================================================

A software RF signal generator that produces, modulates, sweeps, and
exports radio-frequency waveforms for engineering analysis and testing.
"""

from .signal_generator import SignalGenerator, Waveform
from .modulation import AmplitudeModulation, FrequencyModulation
from .sweep import FrequencySweep, SweepMode
from .output import WavExporter, CsvExporter

__all__ = [
    "SignalGenerator",
    "Waveform",
    "AmplitudeModulation",
    "FrequencyModulation",
    "FrequencySweep",
    "SweepMode",
    "WavExporter",
    "CsvExporter",
]

__version__ = "1.0.0"
