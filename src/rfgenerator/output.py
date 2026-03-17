"""
Signal output / export module.

Provides exporters that write generated signals to standard file formats:

* :class:`WavExporter` – 16-bit PCM WAV (suitable for audio-band signals
  and playback via standard audio tools).
* :class:`CsvExporter` – plain CSV with ``time_s`` and ``voltage_V`` columns
  (suitable for import into MATLAB, Python, Excel, etc.).
"""

from __future__ import annotations

import csv
import struct
import wave
from pathlib import Path

import numpy as np


class WavExporter:
    """Export a signal to a 16-bit PCM WAV file.

    Parameters
    ----------
    sample_rate:
        Sample rate in Hz.  Defaults to 44 100 Hz (CD quality).  For RF
        signals whose frequency exceeds 22 kHz the sample rate must be at
        least twice the signal frequency (Nyquist).
    """

    BITS_PER_SAMPLE: int = 16
    MAX_AMPLITUDE: int = 2**15 - 1  # 32 767

    def __init__(self, sample_rate: int = 44_100) -> None:
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        self.sample_rate = sample_rate

    def export(
        self,
        path: str | Path,
        signal: np.ndarray,
        normalise: bool = True,
    ) -> Path:
        """Write *signal* to a WAV file at *path*.

        Parameters
        ----------
        path:
            Destination file path.  Parent directories must exist.
        signal:
            1-D array of voltage samples.
        normalise:
            If ``True`` (default), scale the signal so that its peak
            magnitude maps to the full 16-bit range.  If ``False``,
            clip values outside ±1 V to ±1 V and scale by
            :attr:`MAX_AMPLITUDE`.

        Returns
        -------
        Path
            Resolved path to the written WAV file.
        """
        path = Path(path)
        signal = np.asarray(signal, dtype=float)

        if signal.ndim != 1:
            raise ValueError("signal must be a 1-D array")

        if normalise:
            peak = np.max(np.abs(signal))
            if peak == 0.0:
                normalised = signal
            else:
                normalised = signal / peak
        else:
            normalised = np.clip(signal, -1.0, 1.0)

        int_samples = (normalised * self.MAX_AMPLITUDE).astype(np.int16)

        with wave.open(str(path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.BITS_PER_SAMPLE // 8)
            wf.setframerate(self.sample_rate)
            wf.writeframes(int_samples.tobytes())

        return path.resolve()


class CsvExporter:
    """Export a (time, signal) pair to a CSV file.

    The CSV file contains a header row and two columns:
    ``time_s`` and ``voltage_V``.

    Parameters
    ----------
    delimiter:
        Column delimiter character.  Defaults to ``','``.
    """

    def __init__(self, delimiter: str = ",") -> None:
        self.delimiter = delimiter

    def export(
        self,
        path: str | Path,
        time: np.ndarray,
        signal: np.ndarray,
    ) -> Path:
        """Write *time* and *signal* arrays to a CSV file at *path*.

        Parameters
        ----------
        path:
            Destination file path.  Parent directories must exist.
        time:
            1-D array of time values in seconds.
        signal:
            1-D array of voltage values in Volts.  Must have the same
            length as *time*.

        Returns
        -------
        Path
            Resolved path to the written CSV file.
        """
        path = Path(path)
        time = np.asarray(time, dtype=float)
        signal = np.asarray(signal, dtype=float)

        if time.shape != signal.shape:
            raise ValueError(
                f"time and signal must have the same shape, "
                f"got {time.shape} vs {signal.shape}"
            )

        with path.open("w", newline="") as fh:
            writer = csv.writer(fh, delimiter=self.delimiter)
            writer.writerow(["time_s", "voltage_V"])
            for t, v in zip(time, signal):
                writer.writerow([f"{t:.9e}", f"{v:.9e}"])

        return path.resolve()
