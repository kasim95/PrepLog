import tkinter as tk
from tkinter import ttk


class TranscriptionPanel(ttk.LabelFrame):
    """Panel displaying transcription text for a selected attempt with retranscribe button."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text="Transcription", padding=10, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Status row with retranscribe button
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(0, 5))

        self._status_var = tk.StringVar(value="")
        self._status_label = ttk.Label(status_frame, textvariable=self._status_var, foreground="gray")
        self._status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._retranscribe_btn = ttk.Button(
            status_frame, text="↻ Retranscribe", command=self._on_retranscribe, state=tk.DISABLED
        )
        self._retranscribe_btn.pack(side=tk.RIGHT)

        # Scrollable text area
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self._text = tk.Text(text_frame, wrap=tk.WORD, height=6, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)

        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def set_transcription(self, text: str | None, status: str = "completed"):
        """Display transcription text or status."""
        status_messages = {
            "pending": "⏳ Transcription pending...",
            "processing": "⏳ Transcription in progress...",
            "completed": "",
            "failed": "✗ Transcription failed",
        }
        self._status_var.set(status_messages.get(status, status))

        # Enable retranscribe when there's a recording (completed or failed)
        if status in ("completed", "failed"):
            self._retranscribe_btn.config(state=tk.NORMAL)
        else:
            self._retranscribe_btn.config(state=tk.DISABLED)

        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        if text:
            self._text.insert("1.0", text)
        elif status == "completed":
            self._text.insert("1.0", "(No transcription available)")
        self._text.config(state=tk.DISABLED)

    def clear(self):
        """Clear the transcription display."""
        self._status_var.set("")
        self._retranscribe_btn.config(state=tk.DISABLED)
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)

    def _on_retranscribe(self):
        self.event_generate("<<Retranscribe>>")
