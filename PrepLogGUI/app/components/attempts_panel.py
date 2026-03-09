import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any


class AttemptsPanel(ttk.LabelFrame):
    """Panel displaying attempt history with icon indicators and inline code viewer."""

    def __init__(
        self,
        parent,
        on_attempt_selected: Callable[[dict | None], None],
        on_play: Callable[[dict], None],
        on_delete: Callable[[dict], None],
        **kwargs,
    ):
        super().__init__(parent, text="Attempts", padding=10, **kwargs)
        self._on_attempt_selected = on_attempt_selected
        self._on_play = on_play
        self._on_delete = on_delete
        self._attempts: list[dict[str, Any]] = []
        self._selected_attempt: dict[str, Any] | None = None
        self._code_visible = False
        # Track recording info per attempt: {attempt_id: {duration, transcription_status, has_recording}}
        self._recording_info: dict[int, dict] = {}

        self._build_ui()

    def _build_ui(self):
        # Treeview with icon-based content column
        columns = ("num", "date", "status", "contents")
        self._tree = ttk.Treeview(self, columns=columns, show="headings", height=6)
        self._tree.heading("num", text="#")
        self._tree.heading("date", text="Date")
        self._tree.heading("status", text="Status")
        self._tree.heading("contents", text="Contents")

        self._tree.column("num", width=40, anchor=tk.CENTER)
        self._tree.column("date", width=150)
        self._tree.column("status", width=90, anchor=tk.CENTER)
        self._tree.column("contents", width=120, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Action buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        self._play_btn = ttk.Button(btn_frame, text="▶ Play", command=self._play_selected, state=tk.DISABLED)
        self._play_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._stop_play_btn = ttk.Button(btn_frame, text="■ Stop", command=self._stop_playback, state=tk.DISABLED)
        self._stop_play_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._code_btn = ttk.Button(btn_frame, text="View Code", command=self._toggle_code, state=tk.DISABLED)
        self._code_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._retranscribe_btn = ttk.Button(
            btn_frame, text="↻ Retranscribe", command=self._retranscribe, state=tk.DISABLED
        )
        self._retranscribe_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._delete_btn = ttk.Button(btn_frame, text="Delete", command=self._delete_selected, state=tk.DISABLED)
        self._delete_btn.pack(side=tk.LEFT)

        # Inline code viewer (hidden by default)
        self._code_frame = ttk.LabelFrame(self, text="Code Submission", padding=5)
        # Not packed until user clicks View Code

        code_inner = ttk.Frame(self._code_frame)
        code_inner.pack(fill=tk.BOTH, expand=True)

        self._code_text = tk.Text(code_inner, wrap=tk.NONE, height=10, state=tk.DISABLED)
        xscroll = ttk.Scrollbar(code_inner, orient=tk.HORIZONTAL, command=self._code_text.xview)
        yscroll = ttk.Scrollbar(code_inner, orient=tk.VERTICAL, command=self._code_text.yview)
        self._code_text.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)

        self._code_text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        code_inner.grid_rowconfigure(0, weight=1)
        code_inner.grid_columnconfigure(0, weight=1)

    def set_attempts(self, attempts: list[dict[str, Any]]):
        """Update the attempts list display. Attempts are sorted ascending (oldest first) by server."""
        self._attempts = attempts
        self._tree.delete(*self._tree.get_children())
        self._selected_attempt = None
        self._update_buttons()
        self._hide_code()

        for i, attempt in enumerate(attempts, 1):
            date = attempt.get("started_at", "")[:16].replace("T", " ")
            status = attempt.get("status", "in_progress")
            status_display = {"in_progress": "▶ Active", "paused": "⏸ Paused", "completed": "✓ Done"}.get(
                status, status
            )
            contents = self._build_contents_icons(attempt)
            self._tree.insert("", tk.END, iid=str(attempt["id"]), values=(i, date, status_display, contents))

    def _build_contents_icons(self, attempt: dict) -> str:
        """Build icon string: 📝=code, 🎤=recording, ✓=transcribed."""
        icons = []
        if attempt.get("code_submission"):
            icons.append("📝")
        # Check recording info cache
        info = self._recording_info.get(attempt["id"], {})
        if info.get("has_recording"):
            icons.append("🎤")
        if info.get("transcription_status") == "completed":
            icons.append("✓")
        elif info.get("transcription_status") in ("pending", "processing"):
            icons.append("⏳")
        return " ".join(icons) if icons else "—"

    def update_attempt_info(
        self,
        attempt_id: int,
        duration: str | None = None,
        transcription_status: str | None = None,
        has_recording: bool | None = None,
    ):
        """Update display info for a specific attempt and refresh its icons."""
        info = self._recording_info.setdefault(attempt_id, {})
        if duration is not None:
            info["duration"] = duration
        if transcription_status is not None:
            info["transcription_status"] = transcription_status
        if has_recording is not None:
            info["has_recording"] = has_recording

        # Re-render the contents column for this attempt
        item_id = str(attempt_id)
        if self._tree.exists(item_id):
            attempt = next((a for a in self._attempts if a["id"] == attempt_id), None)
            if attempt:
                icons = self._build_contents_icons(attempt)
                values = list(self._tree.item(item_id, "values"))
                values[3] = icons
                self._tree.item(item_id, values=values)

    def get_selected_attempt(self) -> dict[str, Any] | None:
        return self._selected_attempt

    def set_playing(self, playing: bool):
        """Update button states for playback."""
        if playing:
            self._play_btn.config(state=tk.DISABLED)
            self._stop_play_btn.config(state=tk.NORMAL)
        else:
            self._stop_play_btn.config(state=tk.DISABLED)
            if self._selected_attempt:
                self._play_btn.config(state=tk.NORMAL)

    def _on_tree_select(self, event=None):
        selection = self._tree.selection()
        if selection:
            attempt_id = int(selection[0])
            self._selected_attempt = next((a for a in self._attempts if a["id"] == attempt_id), None)
        else:
            self._selected_attempt = None

        self._update_buttons()
        self._hide_code()
        self._on_attempt_selected(self._selected_attempt)

    def _update_buttons(self):
        has_selection = self._selected_attempt is not None
        state = tk.NORMAL if has_selection else tk.DISABLED
        self._play_btn.config(state=state)
        self._delete_btn.config(state=state)

        # View code only if attempt has code
        has_code = has_selection and self._selected_attempt.get("code_submission")
        self._code_btn.config(state=tk.NORMAL if has_code else tk.DISABLED)

        # Retranscribe only if attempt has a recording
        has_rec = has_selection and self._recording_info.get(self._selected_attempt["id"], {}).get("has_recording")
        self._retranscribe_btn.config(state=tk.NORMAL if has_rec else tk.DISABLED)

    def _play_selected(self):
        if self._selected_attempt:
            self._on_play(self._selected_attempt)

    def _stop_playback(self):
        self.event_generate("<<StopPlayback>>")

    def _toggle_code(self):
        if self._code_visible:
            self._hide_code()
        else:
            self._show_code()

    def _show_code(self):
        if not self._selected_attempt:
            return
        code = self._selected_attempt.get("code_submission", "")
        if not code:
            return
        self._code_text.config(state=tk.NORMAL)
        self._code_text.delete("1.0", tk.END)
        self._code_text.insert("1.0", code)
        self._code_text.config(state=tk.DISABLED)
        self._code_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self._code_visible = True
        self._code_btn.config(text="Hide Code")

    def _hide_code(self):
        if self._code_visible:
            self._code_frame.pack_forget()
            self._code_visible = False
            self._code_btn.config(text="View Code")

    def _retranscribe(self):
        if self._selected_attempt:
            self.event_generate("<<Retranscribe>>")

    def _delete_selected(self):
        if self._selected_attempt:
            confirm = messagebox.askyesno(
                "Delete Attempt",
                "Are you sure you want to delete this attempt?",
                parent=self.winfo_toplevel(),
            )
            if confirm:
                self._on_delete(self._selected_attempt)
