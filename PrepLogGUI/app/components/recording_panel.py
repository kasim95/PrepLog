import threading
import time
import tkinter as tk
from tkinter import ttk


class RecordingPanel(ttk.LabelFrame):
    """Panel with record/pause/resume/stop recording controls and duration timer."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="Recording", padding=10, **kwargs)
        self._recording = False
        self._paused = False
        self._start_time: float | None = None
        self._pause_offset: float = 0.0  # accumulated time before last pause
        self._timer_thread: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self):
        # ── Recording controls row ──────────────────────────────────
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X)

        self._record_btn = ttk.Button(controls_frame, text="● Record", command=self._on_record_click)
        self._record_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._pause_btn = ttk.Button(
            controls_frame, text="⏸ Pause", command=self._on_pause_click, state=tk.DISABLED
        )
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._stop_btn = ttk.Button(
            controls_frame, text="■ Stop", command=self._on_stop_click, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 15))

        self._duration_var = tk.StringVar(value="Duration: 00:00")
        ttk.Label(controls_frame, textvariable=self._duration_var).pack(side=tk.LEFT)

        self._status_var = tk.StringVar(value="Status: Ready")
        ttk.Label(self, textvariable=self._status_var, foreground="gray").pack(fill=tk.X, pady=(5, 0))

    # ── Recording controls ───────────────────────────────────────────

    def _on_record_click(self):
        self._recording = True
        self._paused = False
        self._pause_offset = 0.0
        self._start_time = time.time()
        self._record_btn.config(state=tk.DISABLED)
        self._pause_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._status_var.set("Status: Recording...")

        # Start timer update thread
        self._timer_thread = threading.Thread(target=self._update_timer, daemon=True)
        self._timer_thread.start()

        self.event_generate("<<RecordStart>>")

    def _on_pause_click(self):
        if not self._paused:
            # Pause
            self._paused = True
            if self._start_time:
                self._pause_offset += time.time() - self._start_time
            self._start_time = None
            self._pause_btn.config(text="▶ Resume")
            self._status_var.set("Status: Paused")
            self.event_generate("<<RecordPause>>")
        else:
            # Resume
            self._paused = False
            self._start_time = time.time()
            self._pause_btn.config(text="⏸ Pause")
            self._status_var.set("Status: Recording...")
            self.event_generate("<<RecordResume>>")

    def _on_stop_click(self):
        self._recording = False
        self._paused = False
        self._record_btn.config(state=tk.NORMAL)
        self._pause_btn.config(state=tk.DISABLED, text="⏸ Pause")
        self._stop_btn.config(state=tk.DISABLED)
        self._status_var.set("Status: Uploading...")
        self.event_generate("<<RecordStop>>")

    def set_status(self, status: str):
        self._status_var.set(f"Status: {status}")

    def set_enabled(self, enabled: bool):
        """Enable/disable recording controls."""
        if not enabled and not self._recording:
            self._record_btn.config(state=tk.DISABLED)
        elif enabled and not self._recording:
            self._record_btn.config(state=tk.NORMAL)

    def _update_timer(self):
        """Update the duration display while recording."""
        while self._recording:
            elapsed = self._pause_offset + (time.time() - self._start_time) if self._start_time else self._pause_offset
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self._duration_var.set(f"Duration: {minutes:02d}:{seconds:02d}")
            time.sleep(0.5)
