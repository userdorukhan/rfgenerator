"""
RF Generator Controller
PC-side app for the STM32 AD9851 DDS board.
Requires: pip install customtkinter pyserial
"""

import threading
import time
from tkinter import StringVar, DoubleVar

import customtkinter as ctk
import serial
import serial.tools.list_ports

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

MAX_FREQ_HZ = 10_000_000
MIN_FREQ_HZ = 0


def hz_to_display(hz: float) -> str:
    if hz >= 1_000_000:
        return f"{hz / 1_000_000:.6g} MHz"
    if hz >= 1_000:
        return f"{hz / 1_000:.6g} kHz"
    return f"{hz:.0f} Hz"


def hz_to_command(hz: float) -> str:
    if hz >= 1_000_000:
        return f"{hz / 1_000_000:.6g} MHz\r\n"
    if hz >= 1_000:
        return f"{hz / 1_000:.6g} kHz\r\n"
    return f"{hz:.0f} Hz\r\n"


class RFGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("RF Generator Controller")
        self.geometry("640x900")
        self.resizable(False, False)

        self._serial: serial.Serial | None = None
        self._read_thread: threading.Thread | None = None
        self._running = False
        self._slider_debounce_id = None
        self._amp_debounce_id = None

        self._build_ui()
        self._refresh_ports()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # ── Connection ────────────────────────────────────────────────────
        conn = ctk.CTkFrame(self, corner_radius=12)
        conn.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        conn.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(conn, text="Connection",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, columnspan=5, sticky="w", padx=16, pady=(12, 6))

        self._port_var = StringVar()
        self._port_menu = ctk.CTkOptionMenu(conn, variable=self._port_var,
                                            values=[], width=130)
        self._port_menu.grid(row=1, column=0, padx=(16, 6), pady=(0, 14))

        ctk.CTkButton(conn, text="↻", width=34, height=32,
                      command=self._refresh_ports).grid(
            row=1, column=1, padx=(0, 6), pady=(0, 14), sticky="w")

        self._baud_var = StringVar(value="115200")
        ctk.CTkOptionMenu(conn, variable=self._baud_var,
                          values=["9600", "115200", "230400"],
                          width=105).grid(row=1, column=2, padx=(0, 10),
                                          pady=(0, 14))

        self._connect_btn = ctk.CTkButton(
            conn, text="Connect", width=110,
            fg_color="#2e7d32", hover_color="#1b5e20",
            command=self._toggle_connection)
        self._connect_btn.grid(row=1, column=3, padx=(0, 16), pady=(0, 14))

        self._status_lbl = ctk.CTkLabel(conn, text="●  Disconnected",
                                        text_color="#757575",
                                        font=ctk.CTkFont(size=12))
        self._status_lbl.grid(row=2, column=0, columnspan=5,
                               sticky="w", padx=16, pady=(0, 12))

        # ── Frequency display ─────────────────────────────────────────────
        freq_frame = ctk.CTkFrame(self, corner_radius=12)
        freq_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        freq_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(freq_frame, text="Output Frequency",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 4))

        self._freq_display = ctk.CTkLabel(
            freq_frame, text="7.7 MHz",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="#4fc3f7")
        self._freq_display.grid(row=1, column=0, pady=6)

        # Slider
        self._slider_var = DoubleVar(value=7_700_000)
        self._slider = ctk.CTkSlider(
            freq_frame, from_=MIN_FREQ_HZ, to=MAX_FREQ_HZ,
            variable=self._slider_var,
            command=self._on_slider_move)
        self._slider.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 2))

        bounds = ctk.CTkFrame(freq_frame, fg_color="transparent")
        bounds.grid(row=3, column=0, sticky="ew", padx=24)
        ctk.CTkLabel(bounds, text="0 Hz",
                     font=ctk.CTkFont(size=11), text_color="#9e9e9e").pack(side="left")
        ctk.CTkLabel(bounds, text="10 MHz",
                     font=ctk.CTkFont(size=11), text_color="#9e9e9e").pack(side="right")

        # Manual entry row
        entry_row = ctk.CTkFrame(freq_frame, fg_color="transparent")
        entry_row.grid(row=4, column=0, pady=(14, 6), padx=16, sticky="ew")

        self._freq_entry = ctk.CTkEntry(
            entry_row, placeholder_text="e.g. 7.7",
            width=130, height=38,
            font=ctk.CTkFont(size=15))
        self._freq_entry.pack(side="left", padx=(0, 8))
        self._freq_entry.bind("<Return>", lambda _e: self._send_from_entry())

        self._unit_var = StringVar(value="MHz")
        ctk.CTkOptionMenu(entry_row, variable=self._unit_var,
                          values=["Hz", "kHz", "MHz"],
                          width=90, height=38).pack(side="left", padx=(0, 8))

        ctk.CTkButton(entry_row, text="Set Frequency", height=38, width=150,
                      command=self._send_from_entry).pack(side="left")

        # Presets
        presets_row = ctk.CTkFrame(freq_frame, fg_color="transparent")
        presets_row.grid(row=5, column=0, pady=(8, 16), padx=16, sticky="w")

        ctk.CTkLabel(presets_row, text="Presets:",
                     font=ctk.CTkFont(size=12),
                     text_color="#9e9e9e").pack(side="left", padx=(0, 8))

        presets = [
            ("1 MHz",   1_000_000),
            ("3.5 MHz", 3_500_000),
            ("7 MHz",   7_000_000),
            ("7.7 MHz", 7_700_000),
            ("10 MHz",  10_000_000),
        ]
        for label, hz in presets:
            ctk.CTkButton(
                presets_row, text=label, width=76, height=30,
                font=ctk.CTkFont(size=12),
                fg_color="#1e3a5f", hover_color="#154360",
                command=lambda f=hz: self._apply_preset(f)
            ).pack(side="left", padx=3)

        # ── Gain (AD603 VGA) ──────────────────────────────────────────────
        gain_frame = ctk.CTkFrame(self, corner_radius=12)
        gain_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        gain_frame.grid_columnconfigure(0, weight=1)

        header_row = ctk.CTkFrame(gain_frame, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        ctk.CTkLabel(header_row, text="VGA Gain (AD603)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkLabel(header_row, text="0 V → 0 dB     1 V → 80 dB     (HARD CAP 1.0 V)",
                     font=ctk.CTkFont(size=11),
                     text_color="#9e9e9e").pack(side="right")

        self._gain_display = ctk.CTkLabel(
            gain_frame, text="0.0 dB",
            font=ctk.CTkFont(size=42, weight="bold"),
            text_color="#81c784")
        self._gain_display.grid(row=1, column=0, pady=(6, 0))

        self._gain_subtext = ctk.CTkLabel(
            gain_frame, text="Vctl = 0.000 V    ×1.0 V/V",
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e")
        self._gain_subtext.grid(row=2, column=0, pady=(0, 8))

        self._gain_var = DoubleVar(value=0.0)
        self._gain_slider = ctk.CTkSlider(
            gain_frame, from_=0.0, to=80.0,
            variable=self._gain_var,
            command=self._on_gain_slider_move)
        self._gain_slider.grid(row=3, column=0, sticky="ew", padx=24, pady=(4, 2))

        gain_bounds = ctk.CTkFrame(gain_frame, fg_color="transparent")
        gain_bounds.grid(row=4, column=0, sticky="ew", padx=24)
        ctk.CTkLabel(gain_bounds, text="0 dB",
                     font=ctk.CTkFont(size=11), text_color="#9e9e9e").pack(side="left")
        ctk.CTkLabel(gain_bounds, text="80 dB",
                     font=ctk.CTkFont(size=11), text_color="#9e9e9e").pack(side="right")

        gain_entry_row = ctk.CTkFrame(gain_frame, fg_color="transparent")
        gain_entry_row.grid(row=5, column=0, pady=(14, 6), padx=16, sticky="ew")

        self._gain_entry = ctk.CTkEntry(
            gain_entry_row, placeholder_text="0 – 80",
            width=110, height=38,
            font=ctk.CTkFont(size=15))
        self._gain_entry.pack(side="left", padx=(0, 6))
        self._gain_entry.bind("<Return>", lambda _e: self._send_from_gain_entry())

        ctk.CTkLabel(gain_entry_row, text="dB",
                     font=ctk.CTkFont(size=15)).pack(side="left", padx=(0, 10))

        ctk.CTkButton(gain_entry_row, text="Set Gain", height=38, width=110,
                      command=self._send_from_gain_entry).pack(side="left", padx=(0, 6))
        ctk.CTkButton(gain_entry_row, text="Mute", height=38, width=80,
                      fg_color="#b71c1c", hover_color="#7f0000",
                      command=self._send_mute).pack(side="left", padx=(0, 6))
        ctk.CTkButton(gain_entry_row, text="Sweep", height=38, width=90,
                      fg_color="#7b1fa2", hover_color="#4a148c",
                      command=self._send_sweep).pack(side="left", padx=(0, 6))
        ctk.CTkButton(gain_entry_row, text="Calibrate…", height=38, width=110,
                      fg_color="#37474f", hover_color="#263238",
                      command=self._open_calibrate_dialog).pack(side="left")

        gain_presets_row = ctk.CTkFrame(gain_frame, fg_color="transparent")
        gain_presets_row.grid(row=6, column=0, pady=(8, 16), padx=16, sticky="w")

        ctk.CTkLabel(gain_presets_row, text="Presets:",
                     font=ctk.CTkFont(size=12),
                     text_color="#9e9e9e").pack(side="left", padx=(0, 8))

        for label, db in [("0 dB", 0), ("20 dB", 20), ("40 dB", 40),
                          ("60 dB", 60), ("80 dB", 80)]:
            ctk.CTkButton(
                gain_presets_row, text=label, width=76, height=30,
                font=ctk.CTkFont(size=12),
                fg_color="#1a3a2a", hover_color="#0d2e1a",
                command=lambda d=db: self._apply_gain_preset(d)
            ).pack(side="left", padx=3)

        # ── Console ───────────────────────────────────────────────────────
        console_frame = ctk.CTkFrame(self, corner_radius=12)
        console_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(8, 20))
        console_frame.grid_rowconfigure(1, weight=1)
        console_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(console_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        ctk.CTkLabel(hdr, text="Console",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")
        ctk.CTkButton(hdr, text="Clear", width=60, height=26,
                      fg_color="#37474f", hover_color="#263238",
                      command=self._clear_console).pack(side="right")

        self._console = ctk.CTkTextbox(
            console_frame, state="disabled",
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color="#b0bec5")
        self._console.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        self._log("RF Generator Controller ready.")
        self._log("AD603 boots muted. Set frequency, then ramp gain via slider/Sweep.")

    # ---------------------------------------------------------------- Serial -

    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._port_menu.configure(values=ports or ["(no ports)"])
        if ports:
            self._port_var.set(ports[0])

    def _toggle_connection(self):
        if self._serial and self._serial.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_var.get()
        baud = int(self._baud_var.get())
        try:
            self._serial = serial.Serial(port, baud, timeout=0.1)
            self._running = True
            self._read_thread = threading.Thread(
                target=self._read_loop, daemon=True)
            self._read_thread.start()
            self._connect_btn.configure(
                text="Disconnect",
                fg_color="#b71c1c", hover_color="#7f0000")
            self._status_lbl.configure(
                text=f"●  Connected  —  {port}  @  {baud} baud",
                text_color="#66bb6a")
            self._log(f"[SYS] Connected to {port} at {baud} baud.")
        except Exception as exc:
            self._log(f"[ERR] {exc}")

    def _disconnect(self):
        self._running = False
        if self._serial:
            self._serial.close()
            self._serial = None
        self._connect_btn.configure(
            text="Connect",
            fg_color="#2e7d32", hover_color="#1b5e20")
        self._status_lbl.configure(
            text="●  Disconnected", text_color="#757575")
        self._log("[SYS] Disconnected.")

    def _read_loop(self):
        while self._running:
            try:
                raw = self._serial.readline()
                if raw:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        self.after(0, self._log, line)
            except Exception:
                break

    # --------------------------------------------------------------- Actions -

    def _send_from_entry(self):
        text = self._freq_entry.get().strip()
        if not text:
            return
        try:
            value = float(text)
        except ValueError:
            self._log(f"[ERR] '{text}' is not a valid number.")
            return

        unit = self._unit_var.get()
        multipliers = {"Hz": 1.0, "kHz": 1_000.0, "MHz": 1_000_000.0}
        hz = value * multipliers[unit]
        hz = max(MIN_FREQ_HZ, min(MAX_FREQ_HZ, hz))

        self._apply_frequency(hz)

    def _apply_preset(self, hz: float):
        self._apply_frequency(hz)

    def _on_slider_move(self, value):
        hz = float(value)
        # Update display immediately
        self._freq_display.configure(text=hz_to_display(hz))
        # Debounce: only send 120 ms after the slider stops moving
        if self._slider_debounce_id is not None:
            self.after_cancel(self._slider_debounce_id)
        self._slider_debounce_id = self.after(
            120, lambda: self._send_command(hz))

    def _apply_frequency(self, hz: float):
        self._slider_var.set(hz)
        self._freq_display.configure(text=hz_to_display(hz))
        self._send_command(hz)

    def _send_from_gain_entry(self):
        text = self._gain_entry.get().strip()
        if not text:
            return
        try:
            value = float(text)
        except ValueError:
            self._log(f"[ERR] '{text}' is not a valid number.")
            return
        db = max(0.0, min(80.0, value))
        self._apply_gain(db)

    def _apply_gain_preset(self, db: float):
        self._apply_gain(float(db))

    def _on_gain_slider_move(self, value):
        db = float(value)
        self._update_gain_display(db)
        if self._amp_debounce_id is not None:
            self.after_cancel(self._amp_debounce_id)
        self._amp_debounce_id = self.after(
            120, lambda: self._send_gain_command(db))

    def _apply_gain(self, db: float):
        db = max(0.0, min(80.0, db))
        self._gain_var.set(db)
        self._update_gain_display(db)
        self._send_gain_command(db)

    def _update_gain_display(self, db: float):
        # Defaults match firmware: 0 V -> 0 dB, 80 dB/V slope, 1 V cap.
        vctl = db / 80.0
        linear = 10 ** (db / 20.0)
        self._gain_display.configure(text=f"{db:.1f} dB")
        self._gain_subtext.configure(
            text=f"Vctl = {vctl:.3f} V    ×{linear:.2f} V/V")

    def _send_gain_command(self, db: float):
        self._send_raw(f"gain {db:.2f}\r\n", f"> gain {db:.2f} dB")

    def _send_mute(self):
        self._gain_var.set(0.0)
        self._update_gain_display(0.0)
        self._send_raw("mute\r\n", "> mute")

    def _send_sweep(self):
        # Default sweep: 0 -> 80 dB, 5 dB steps, 200 ms each (matches firmware).
        self._send_raw("sweep\r\n", "> sweep (0 → 80 dB, 5 dB / 200 ms)")

    def _open_calibrate_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("AD603 Two-Point Calibration")
        dlg.geometry("420x320")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg,
            text="Apply a known Vctl, measure actual gain (dB), enter both.\n"
                 "Repeat at a second point. Stays in RAM (lost on reset).",
            font=ctk.CTkFont(size=12),
            text_color="#9e9e9e",
            justify="left").pack(padx=16, pady=(16, 10), anchor="w")

        rows = ctk.CTkFrame(dlg, fg_color="transparent")
        rows.pack(padx=16, pady=4, fill="x")

        v1_e = ctk.CTkEntry(rows, placeholder_text="0.20", width=120)
        d1_e = ctk.CTkEntry(rows, placeholder_text="16.0", width=120)
        v2_e = ctk.CTkEntry(rows, placeholder_text="0.80", width=120)
        d2_e = ctk.CTkEntry(rows, placeholder_text="64.0", width=120)

        for r, (lbl, e) in enumerate([
            ("V1 (volts)", v1_e), ("Gain1 (dB)", d1_e),
            ("V2 (volts)", v2_e), ("Gain2 (dB)", d2_e)]):
            ctk.CTkLabel(rows, text=lbl, width=110,
                         anchor="e").grid(row=r, column=0, padx=(0, 8), pady=4, sticky="e")
            e.grid(row=r, column=1, pady=4, sticky="w")

        def submit():
            try:
                v1, d1, v2, d2 = (float(v1_e.get()), float(d1_e.get()),
                                  float(v2_e.get()), float(d2_e.get()))
            except ValueError:
                self._log("[ERR] Calibration: all four fields must be numbers.")
                return
            self._send_raw(f"cal {v1} {d1} {v2} {d2}\r\n",
                           f"> cal {v1} {d1} {v2} {d2}")
            dlg.destroy()

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(pady=14)
        ctk.CTkButton(btn_row, text="Cancel", width=110,
                      fg_color="#37474f", hover_color="#263238",
                      command=dlg.destroy).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="Apply Calibration", width=160,
                      command=submit).pack(side="left", padx=6)

    def _send_raw(self, cmd: str, log_msg: str):
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(cmd.encode())
                self._log(log_msg)
            except Exception as exc:
                self._log(f"[ERR] Send failed: {exc}")
        else:
            self._log("[WARN] Not connected — command not sent.")

    def _send_command(self, hz: float):
        cmd = hz_to_command(hz)
        if self._serial and self._serial.is_open:
            try:
                self._serial.write(cmd.encode())
                self._log(f"> {cmd.strip()}")
            except Exception as exc:
                self._log(f"[ERR] Send failed: {exc}")
        else:
            self._log("[WARN] Not connected — command not sent.")

    # --------------------------------------------------------------- Console -

    def _log(self, msg: str):
        self._console.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self._console.insert("end", f"[{ts}]  {msg}\n")
        self._console.see("end")
        self._console.configure(state="disabled")

    def _clear_console(self):
        self._console.configure(state="normal")
        self._console.delete("1.0", "end")
        self._console.configure(state="disabled")


if __name__ == "__main__":
    app = RFGeneratorApp()
    app.mainloop()
