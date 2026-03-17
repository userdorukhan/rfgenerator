"""
Modulation module.

Implements Amplitude Modulation (AM) and Frequency Modulation (FM)
applied on top of a :class:`~rfgenerator.signal_generator.SignalGenerator`
carrier.
"""

from __future__ import annotations

import math

import numpy as np

from .signal_generator import SignalGenerator, Waveform


class AmplitudeModulation:
    """Amplitude-modulate a carrier with a sinusoidal message signal.

    The AM output is::

        s(t) = A_c · [1 + m · cos(2π·f_m·t + φ_m)] · cos(2π·f_c·t + φ_c)

    Parameters
    ----------
    carrier:
        The carrier :class:`SignalGenerator` instance.
    modulation_frequency:
        Frequency of the message (modulating) signal in Hz.
    modulation_index:
        Modulation index *m* in the range [0, 1].  A value of 1 produces
        100% AM modulation.
    modulation_phase:
        Phase of the message signal in degrees.  Defaults to 0°.
    """

    def __init__(
        self,
        carrier: SignalGenerator,
        modulation_frequency: float,
        modulation_index: float = 1.0,
        modulation_phase: float = 0.0,
    ) -> None:
        if modulation_frequency <= 0:
            raise ValueError(
                f"modulation_frequency must be positive, got {modulation_frequency}"
            )
        if not 0.0 <= modulation_index <= 1.0:
            raise ValueError(
                f"modulation_index must be in [0, 1], got {modulation_index}"
            )

        self.carrier = carrier
        self.modulation_frequency = modulation_frequency
        self.modulation_index = modulation_index
        self.modulation_phase = modulation_phase

    def generate(self, duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Generate an AM signal of the given *duration* (seconds).

        Returns
        -------
        time : np.ndarray
            Time axis in seconds.
        signal : np.ndarray
            AM-modulated output voltage in Volts.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        num_samples = int(self.carrier.sample_rate * duration)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)

        phase_c = math.radians(self.carrier.phase)
        phase_m = math.radians(self.modulation_phase)

        carrier_wave = np.cos(2.0 * math.pi * self.carrier.frequency * t + phase_c)
        message_wave = np.cos(2.0 * math.pi * self.modulation_frequency * t + phase_m)

        signal = (
            self.carrier.amplitude
            * (1.0 + self.modulation_index * message_wave)
            * carrier_wave
        )
        return t, signal

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AmplitudeModulation(carrier_freq={self.carrier.frequency} Hz, "
            f"mod_freq={self.modulation_frequency} Hz, "
            f"mod_index={self.modulation_index})"
        )


class FrequencyModulation:
    """Frequency-modulate a carrier with a sinusoidal message signal.

    The FM output is::

        s(t) = A_c · cos(2π·f_c·t + β·sin(2π·f_m·t + φ_m) + φ_c)

    where β = Δf / f_m is the modulation index (deviation ratio).

    Parameters
    ----------
    carrier:
        The carrier :class:`SignalGenerator` instance.
    modulation_frequency:
        Frequency of the message (modulating) signal in Hz.
    frequency_deviation:
        Peak frequency deviation Δf in Hz.  Must be positive.
    modulation_phase:
        Phase of the message signal in degrees.  Defaults to 0°.
    """

    def __init__(
        self,
        carrier: SignalGenerator,
        modulation_frequency: float,
        frequency_deviation: float,
        modulation_phase: float = 0.0,
    ) -> None:
        if modulation_frequency <= 0:
            raise ValueError(
                f"modulation_frequency must be positive, got {modulation_frequency}"
            )
        if frequency_deviation <= 0:
            raise ValueError(
                f"frequency_deviation must be positive, got {frequency_deviation}"
            )

        self.carrier = carrier
        self.modulation_frequency = modulation_frequency
        self.frequency_deviation = frequency_deviation
        self.modulation_phase = modulation_phase

    @property
    def modulation_index(self) -> float:
        """FM modulation index β = Δf / f_m."""
        return self.frequency_deviation / self.modulation_frequency

    def generate(self, duration: float) -> tuple[np.ndarray, np.ndarray]:
        """Generate an FM signal of the given *duration* (seconds).

        Returns
        -------
        time : np.ndarray
            Time axis in seconds.
        signal : np.ndarray
            FM-modulated output voltage in Volts.
        """
        if duration <= 0:
            raise ValueError(f"duration must be positive, got {duration}")

        num_samples = int(self.carrier.sample_rate * duration)
        t = np.linspace(0.0, duration, num_samples, endpoint=False)

        phase_c = math.radians(self.carrier.phase)
        phase_m = math.radians(self.modulation_phase)

        beta = self.modulation_index
        instantaneous_phase = (
            2.0 * math.pi * self.carrier.frequency * t
            + beta * np.sin(2.0 * math.pi * self.modulation_frequency * t + phase_m)
            + phase_c
        )

        signal = self.carrier.amplitude * np.cos(instantaneous_phase)
        return t, signal

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FrequencyModulation(carrier_freq={self.carrier.frequency} Hz, "
            f"mod_freq={self.modulation_frequency} Hz, "
            f"deviation={self.frequency_deviation} Hz, "
            f"beta={self.modulation_index:.3f})"
        )
