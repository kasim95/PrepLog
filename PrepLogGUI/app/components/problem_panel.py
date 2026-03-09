import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any


class ProblemPanel(ttk.LabelFrame):
    """Panel for selecting/creating problems and managing attempt lifecycle."""

    def __init__(self, parent, on_problem_selected: Callable[[dict | None], None], **kwargs):
        super().__init__(parent, text="Problem", padding=10, **kwargs)
        self._on_problem_selected = on_problem_selected
        self._problems: list[dict[str, Any]] = []
        self._selected_problem: dict[str, Any] | None = None
        self._form_visible = False
        self._pending_create: dict | None = None

        self._build_ui()

    def _build_ui(self):
        # Problem selector row
        select_frame = ttk.Frame(self)
        select_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(select_frame, text="Problem:").pack(side=tk.LEFT, padx=(0, 5))

        self._combo_var = tk.StringVar()
        self._combo = ttk.Combobox(select_frame, textvariable=self._combo_var, state="readonly", width=50)
        self._combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self._combo.bind("<<ComboboxSelected>>", self._on_combo_select)

        self._new_btn = ttk.Button(select_frame, text="+ New Problem", command=self._toggle_form)
        self._new_btn.pack(side=tk.LEFT)

        self._refresh_btn = ttk.Button(select_frame, text="↻", width=3, command=self._request_refresh)
        self._refresh_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Info row
        self._info_var = tk.StringVar(value="Select a problem to begin")
        ttk.Label(self, textvariable=self._info_var, foreground="gray").pack(fill=tk.X)

        # Attempt lifecycle row
        attempt_frame = ttk.LabelFrame(self, text="Attempt", padding=5)
        attempt_frame.pack(fill=tk.X, pady=(8, 0))

        self._start_attempt_btn = ttk.Button(
            attempt_frame, text="▶ Start Attempt", command=self._emit_start_attempt
        )
        self._start_attempt_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._pause_attempt_btn = ttk.Button(
            attempt_frame, text="⏸ Pause Attempt", command=self._emit_pause_attempt, state=tk.DISABLED
        )
        self._pause_attempt_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._stop_attempt_btn = ttk.Button(
            attempt_frame, text="■ Stop Attempt", command=self._emit_stop_attempt, state=tk.DISABLED
        )
        self._stop_attempt_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._attempt_status_var = tk.StringVar(value="No active attempt")
        ttk.Label(attempt_frame, textvariable=self._attempt_status_var, foreground="gray").pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Inline new-problem form (hidden by default)
        self._form_frame = ttk.LabelFrame(self, text="New Problem", padding=10)
        # Not packed until user clicks "+ New Problem"

        ttk.Label(self._form_frame, text="Title:").pack(anchor=tk.W)
        self._title_var = tk.StringVar()
        ttk.Entry(self._form_frame, textvariable=self._title_var, width=60).pack(fill=tk.X, pady=(0, 8))

        ttk.Label(self._form_frame, text="Difficulty:").pack(anchor=tk.W)
        self._difficulty_var = tk.StringVar()
        ttk.Combobox(
            self._form_frame,
            textvariable=self._difficulty_var,
            values=["Easy", "Medium", "Hard"],
            state="readonly",
        ).pack(fill=tk.X, pady=(0, 8))

        ttk.Label(self._form_frame, text="Description (optional):").pack(anchor=tk.W)
        self._desc_text = tk.Text(self._form_frame, height=4, width=60)
        self._desc_text.pack(fill=tk.X, pady=(0, 8))

        btn_row = ttk.Frame(self._form_frame)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="Create", command=self._submit_form).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Cancel", command=self._toggle_form).pack(side=tk.LEFT)

    # ── Form toggle ──────────────────────────────────────────────────

    def _toggle_form(self):
        if self._form_visible:
            self._form_frame.pack_forget()
            self._form_visible = False
            self._new_btn.config(text="+ New Problem")
        else:
            self._form_frame.pack(fill=tk.X, pady=(8, 0))
            self._form_visible = True
            self._new_btn.config(text="Cancel")
            self._title_var.set("")
            self._difficulty_var.set("")
            self._desc_text.delete("1.0", tk.END)

    def _submit_form(self):
        title = self._title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a problem title.", parent=self.winfo_toplevel())
            return
        self._pending_create = {
            "title": title,
            "difficulty": self._difficulty_var.get() or None,
            "description": self._desc_text.get("1.0", tk.END).strip() or None,
            "source": "custom",
        }
        self.event_generate("<<CreateProblem>>")
        self._toggle_form()

    # ── Public API ───────────────────────────────────────────────────

    def set_problems(self, problems: list[dict[str, Any]]):
        """Update the problem list (already sorted ascending by server)."""
        self._problems = problems
        display = [self._format_problem(p) for p in problems]
        self._combo["values"] = display

        # Restore selection if possible
        if self._selected_problem:
            for i, p in enumerate(problems):
                if p["id"] == self._selected_problem["id"]:
                    self._combo.current(i)
                    self._selected_problem = p
                    self._update_info()
                    return

        # Reset selection
        self._combo_var.set("")
        self._selected_problem = None
        self._info_var.set("Select a problem to begin")

    def get_selected_problem(self) -> dict[str, Any] | None:
        return self._selected_problem

    def get_pending_create(self) -> dict | None:
        data = self._pending_create
        self._pending_create = None
        return data

    # ── Internal ─────────────────────────────────────────────────────

    def _format_problem(self, problem: dict) -> str:
        difficulty = f" [{problem.get('difficulty', '')}]" if problem.get("difficulty") else ""
        source = f" ({problem['source']})" if problem.get("source") else ""
        return f"{problem['title']}{difficulty}{source}"

    def _on_combo_select(self, event=None):
        idx = self._combo.current()
        if 0 <= idx < len(self._problems):
            self._selected_problem = self._problems[idx]
            self._update_info()
            self._on_problem_selected(self._selected_problem)

    def _update_info(self):
        if self._selected_problem:
            parts = []
            if self._selected_problem.get("difficulty"):
                parts.append(f"Difficulty: {self._selected_problem['difficulty']}")
            parts.append(f"Source: {self._selected_problem['source']}")
            self._info_var.set("  |  ".join(parts))
        else:
            self._info_var.set("Select a problem to begin")

    def _request_refresh(self):
        self.event_generate("<<RefreshProblems>>")

    # ── Attempt lifecycle events ─────────────────────────────────────

    def _emit_start_attempt(self):
        self.event_generate("<<StartAttempt>>")

    def _emit_pause_attempt(self):
        self.event_generate("<<PauseAttempt>>")

    def _emit_stop_attempt(self):
        self.event_generate("<<StopAttempt>>")

    def set_attempt_state(self, state: str):
        """Update attempt button states. state: 'none' | 'in_progress' | 'paused'."""
        if state == "none":
            self._start_attempt_btn.config(state=tk.NORMAL)
            self._pause_attempt_btn.config(state=tk.DISABLED)
            self._stop_attempt_btn.config(state=tk.DISABLED)
            self._attempt_status_var.set("No active attempt")
        elif state == "in_progress":
            self._start_attempt_btn.config(state=tk.DISABLED)
            self._pause_attempt_btn.config(state=tk.NORMAL, text="⏸ Pause Attempt")
            self._stop_attempt_btn.config(state=tk.NORMAL)
            self._attempt_status_var.set("Attempt in progress")
        elif state == "paused":
            self._start_attempt_btn.config(state=tk.DISABLED)
            self._pause_attempt_btn.config(state=tk.NORMAL, text="▶ Resume Attempt")
            self._stop_attempt_btn.config(state=tk.NORMAL)
            self._attempt_status_var.set("Attempt paused")

    def set_enabled(self, enabled: bool):
        """Enable/disable attempt controls based on whether a problem is selected."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self._start_attempt_btn.config(state=state)
        if not enabled:
            self._pause_attempt_btn.config(state=tk.DISABLED)
            self._stop_attempt_btn.config(state=tk.DISABLED)
