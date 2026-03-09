import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk


class DockerPanel(ttk.LabelFrame):
    """Panel for managing Docker Compose backend services (start/stop/status)."""

    def __init__(self, parent, compose_file: str, **kwargs):
        super().__init__(parent, text="Backend Services (Docker)", padding=10, **kwargs)
        self._compose_file = compose_file
        self._compose_dir = os.path.dirname(compose_file)
        self._polling_id: str | None = None

        self._build_ui()
        # Initial status check
        self.after(500, self._refresh_status)

    def _build_ui(self):
        # Controls row
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        self._start_btn = ttk.Button(btn_frame, text="▶ Start Backend", command=self._start_backend)
        self._start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._stop_btn = ttk.Button(btn_frame, text="■ Stop Backend", command=self._stop_backend)
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._refresh_btn = ttk.Button(btn_frame, text="↻ Refresh", command=self._refresh_status)
        self._refresh_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._status_var = tk.StringVar(value="Checking...")
        self._status_indicator = ttk.Label(btn_frame, textvariable=self._status_var)
        self._status_indicator.pack(side=tk.LEFT, padx=(10, 0))

        # Service status details
        self._details_text = tk.Text(self, height=5, width=80, state=tk.DISABLED, wrap=tk.NONE)
        details_scroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._details_text.xview)
        self._details_text.configure(xscrollcommand=details_scroll.set)
        self._details_text.pack(fill=tk.X, pady=(0, 2))
        details_scroll.pack(fill=tk.X)

    def _run_compose(self, args: list[str], callback=None):
        """Run a docker compose command in a background thread."""

        def _exec():
            try:
                result = subprocess.run(
                    ["docker", "compose", "-f", self._compose_file, *args],
                    capture_output=True,
                    text=True,
                    cwd=self._compose_dir,
                    timeout=120,
                )
                output = result.stdout + result.stderr
                if callback:
                    self.after(0, callback, result.returncode, output)
            except FileNotFoundError:
                if callback:
                    self.after(
                        0,
                        callback,
                        -1,
                        "Docker not found. Please install Docker Desktop.",
                    )
            except subprocess.TimeoutExpired:
                if callback:
                    self.after(0, callback, -1, "Command timed out.")
            except Exception as e:
                if callback:
                    self.after(0, callback, -1, str(e))

        threading.Thread(target=_exec, daemon=True).start()

    def _start_backend(self):
        self._status_var.set("Starting...")
        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.DISABLED)
        self._run_compose(["up", "-d", "--build"], callback=self._on_start_complete)

    def _on_start_complete(self, returncode: int, output: str):
        if returncode == 0:
            self._status_var.set("● Running")
            self._status_indicator.config(foreground="green")
        else:
            self._status_var.set("✗ Start failed")
            self._status_indicator.config(foreground="red")
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._update_details(output)
        self.after(1000, self._refresh_status)

    def _stop_backend(self):
        self._status_var.set("Stopping...")
        self._start_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.DISABLED)
        self._run_compose(["stop"], callback=self._on_stop_complete)

    def _on_stop_complete(self, returncode: int, output: str):
        if returncode == 0:
            self._status_var.set("○ Stopped")
            self._status_indicator.config(foreground="gray")
        else:
            self._status_var.set("✗ Stop failed")
            self._status_indicator.config(foreground="red")
        self._start_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._update_details(output)

    def _refresh_status(self):
        self._run_compose(["ps", "--format", "table {{.Name}}\t{{.Status}}\t{{.Ports}}"], callback=self._on_status)

    def _on_status(self, returncode: int, output: str):
        if returncode == 0 and output.strip():
            lines = output.strip().split("\n")
            # Check if any service containers are running
            running = any("Up" in line or "running" in line.lower() for line in lines if not line.startswith("NAME"))
            if running:
                self._status_var.set("● Running")
                self._status_indicator.config(foreground="green")
            else:
                self._status_var.set("○ Stopped")
                self._status_indicator.config(foreground="gray")
        else:
            self._status_var.set("○ Stopped")
            self._status_indicator.config(foreground="gray")
        self._update_details(output if output.strip() else "No services running.")

    def _update_details(self, text: str):
        self._details_text.config(state=tk.NORMAL)
        self._details_text.delete("1.0", tk.END)
        self._details_text.insert("1.0", text.strip())
        self._details_text.config(state=tk.DISABLED)

    def cancel_polling(self):
        """Cancel any pending polling callbacks."""
        if self._polling_id:
            self.after_cancel(self._polling_id)
            self._polling_id = None
