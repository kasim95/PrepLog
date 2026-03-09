import threading
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from app.api_client import APIClient
from app.audio_player import AudioPlayer
from app.audio_recorder import AudioRecorder
from app.components.attempts_panel import AttemptsPanel
from app.components.docker_panel import DockerPanel
from app.components.problem_panel import ProblemPanel
from app.components.recording_panel import RecordingPanel
from app.components.transcription_panel import TranscriptionPanel
from app.config import (
    ATTEMPTS_POLL_INTERVAL_MS,
    DOCKER_COMPOSE_FILE,
    PROBLEMS_POLL_INTERVAL_MS,
    TRANSCRIPTION_POLL_INTERVAL_MS,
)


class PrepLogApp:
    """Main PrepLog desktop application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PrepLog - Interview Preparation Tracker")
        self.root.geometry("700x750")
        self.root.minsize(600, 600)

        # Set window icon
        icon_path = Path(__file__).parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            icon_image = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, icon_image)
            self._icon_ref = icon_image  # prevent garbage collection

        self.api = APIClient()
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()

        self._current_attempt: dict[str, Any] | None = None
        self._known_problem_ids: set[int] = set()
        self._known_attempts_data: list[dict] = []  # for change detection during polling
        self._problems_poll_id: str | None = None
        self._attempts_poll_id: str | None = None
        self._docker_panel_visible = False

        self._build_ui()
        self._bind_events()

        # Initial data load, then start auto-polling
        self.root.after(100, self._load_problems_and_start_polling)

    def _build_ui(self):
        # Scrollable wrapper: canvas + scrollbar around all content
        self._canvas = tk.Canvas(self.root, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main_frame = ttk.Frame(self._canvas, padding=10)
        self._canvas_window = self._canvas.create_window((0, 0), window=main_frame, anchor="nw")

        # Resize the inner frame to fill canvas width & update scroll region
        main_frame.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._canvas_window, width=e.width))

        # Enable mouse-wheel scrolling (macOS trackpad/mouse compatible)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Problem panel
        self.problem_panel = ProblemPanel(main_frame, on_problem_selected=self._on_problem_selected)
        self.problem_panel.pack(fill=tk.X, pady=(0, 10))

        # Recording panel (event-driven, no callbacks in constructor)
        self.recording_panel = RecordingPanel(main_frame)
        self.recording_panel.pack(fill=tk.X, pady=(0, 10))
        self.recording_panel.set_enabled(False)
        self.problem_panel.set_enabled(False)

        # Attempts panel (no on_view_code callback any more — inline)
        self.attempts_panel = AttemptsPanel(
            main_frame,
            on_attempt_selected=self._on_attempt_selected,
            on_play=self._on_play_attempt,
            on_delete=self._on_delete_attempt,
        )
        self.attempts_panel.pack(fill=tk.X, pady=(0, 10))

        # Transcription panel
        self.transcription_panel = TranscriptionPanel(main_frame)
        self.transcription_panel.pack(fill=tk.X, pady=(0, 15))

        # ── Advanced Settings section (at the bottom) ────────────────
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 10))
        ttk.Label(main_frame, text="Advanced Settings", font=("TkDefaultFont", 12, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        # Docker toggle + panel in one frame
        self._docker_section = ttk.Frame(main_frame)
        self._docker_section.pack(fill=tk.X, pady=(0, 10))

        self._docker_toggle_btn = ttk.Button(
            self._docker_section, text="▶ Backend Services (Docker)", command=self._toggle_docker_panel
        )
        self._docker_toggle_btn.pack(anchor=tk.W, pady=(0, 5))

        self._docker_panel_frame = ttk.Frame(self._docker_section)
        # Hidden by default — not packed

        self.docker_panel = DockerPanel(self._docker_panel_frame, compose_file=DOCKER_COMPOSE_FILE)
        self.docker_panel.pack(fill=tk.X)

    def _toggle_docker_panel(self):
        """Toggle visibility of the Docker panel."""
        self._docker_panel_visible = not self._docker_panel_visible
        if self._docker_panel_visible:
            self._docker_panel_frame.pack(fill=tk.X, pady=(0, 5))
            self._docker_toggle_btn.configure(text="▼ Backend Services (Docker)")
        else:
            self._docker_panel_frame.pack_forget()
            self._docker_toggle_btn.configure(text="▶ Backend Services (Docker)")

    def _bind_events(self):
        # Problem events
        self.problem_panel.bind("<<CreateProblem>>", lambda e: self._handle_create_problem())
        self.problem_panel.bind("<<RefreshProblems>>", lambda e: self._load_problems())

        # Attempt lifecycle events (now on problem_panel)
        self.problem_panel.bind("<<StartAttempt>>", lambda e: self._on_attempt_start())
        self.problem_panel.bind("<<PauseAttempt>>", lambda e: self._on_attempt_pause_toggle())
        self.problem_panel.bind("<<StopAttempt>>", lambda e: self._on_attempt_stop())

        # Recording events
        self.recording_panel.bind("<<RecordStart>>", lambda e: self._on_record_start())
        self.recording_panel.bind("<<RecordPause>>", lambda e: self._on_record_pause())
        self.recording_panel.bind("<<RecordResume>>", lambda e: self._on_record_resume())
        self.recording_panel.bind("<<RecordStop>>", lambda e: self._on_record_stop())

        # Playback / retranscribe
        self.attempts_panel.bind("<<StopPlayback>>", lambda e: self._stop_playback())
        self.attempts_panel.bind("<<Retranscribe>>", lambda e: self._handle_retranscribe())
        self.transcription_panel.bind("<<Retranscribe>>", lambda e: self._handle_retranscribe())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling, skipping for scrollable child widgets."""
        # Don't hijack scroll for Treeview, Text, or Listbox widgets
        widget = event.widget
        widget_class = widget.winfo_class()
        if widget_class in ("Treeview", "Text", "Listbox"):
            return
        # macOS sends delta as ±1 (or small values); no need to divide by 120
        self._canvas.yview_scroll(int(-1 * event.delta), "units")

    # ── Data Loading ─────────────────────────────────────────────────

    def _load_problems_and_start_polling(self):
        self._load_problems()
        self._schedule_problems_poll()

    def _load_problems(self):
        def _fetch():
            try:
                problems = self.api.get_problems()
                self.root.after(0, self._apply_problems, problems)
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to load problems: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_problems(self, problems: list[dict]):
        self._known_problem_ids = {p["id"] for p in problems}
        self.problem_panel.set_problems(problems)

    def _schedule_problems_poll(self):
        self._problems_poll_id = self.root.after(PROBLEMS_POLL_INTERVAL_MS, self._poll_problems)

    def _poll_problems(self):
        def _check():
            try:
                problems = self.api.get_problems()
                new_ids = {p["id"] for p in problems}
                if new_ids != self._known_problem_ids:
                    self.root.after(0, self._apply_problems, problems)
            except Exception:
                pass
            finally:
                self.root.after(0, self._schedule_problems_poll)

        threading.Thread(target=_check, daemon=True).start()

    # ── Attempts loading & polling ───────────────────────────────────

    def _load_attempts(self, problem_id: int):
        def _fetch():
            try:
                attempts = self.api.get_attempts(problem_id)
                self.root.after(0, self._display_attempts, attempts)
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to load attempts: {e}")

        threading.Thread(target=_fetch, daemon=True).start()

    def _display_attempts(self, attempts: list[dict]):
        self._known_attempts_data = attempts
        self.attempts_panel.set_attempts(attempts)
        self.transcription_panel.clear()

        # Load recording details for each attempt
        for attempt in attempts:
            self._load_attempt_recordings(attempt)

    def _load_attempt_recordings(self, attempt: dict):
        """Load recording info for an attempt to populate icons."""

        def _fetch():
            try:
                recordings = self.api.get_attempt_recordings(attempt["id"])
                if recordings:
                    rec = recordings[0]
                    duration = ""
                    if rec.get("duration_seconds"):
                        mins = int(rec["duration_seconds"] // 60)
                        secs = int(rec["duration_seconds"] % 60)
                        duration = f"{mins}:{secs:02d}"
                    self.root.after(
                        0,
                        self.attempts_panel.update_attempt_info,
                        attempt["id"],
                        duration,
                        rec.get("transcription_status"),
                        True,  # has_recording
                    )
                    # Start transcription polling if incomplete
                    if rec.get("transcription_status") in ("pending", "processing"):
                        self.root.after(0, self._start_transcription_polling, rec["id"])
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _schedule_attempts_poll(self):
        """Schedule next attempts poll (only when a problem is selected)."""
        self._attempts_poll_id = self.root.after(ATTEMPTS_POLL_INTERVAL_MS, self._poll_attempts)

    def _cancel_attempts_poll(self):
        if self._attempts_poll_id:
            self.root.after_cancel(self._attempts_poll_id)
            self._attempts_poll_id = None

    def _poll_attempts(self):
        """Check for attempt changes and refresh if needed."""
        problem = self.problem_panel.get_selected_problem()
        if not problem:
            return

        def _check():
            try:
                attempts = self.api.get_attempts(problem["id"])
                # Compare by serialised repr to detect any field change
                if self._attempts_changed(attempts):
                    self.root.after(0, self._display_attempts, attempts)
            except Exception:
                pass
            finally:
                self.root.after(0, self._schedule_attempts_poll)

        threading.Thread(target=_check, daemon=True).start()

    def _attempts_changed(self, new_attempts: list[dict]) -> bool:
        """Return True if attempts data differs from known."""
        if len(new_attempts) != len(self._known_attempts_data):
            return True
        for old, new in zip(self._known_attempts_data, new_attempts, strict=True):
            if old.get("id") != new.get("id"):
                return True
            if old.get("status") != new.get("status"):
                return True
            if old.get("code_submission") != new.get("code_submission"):
                return True
            if old.get("ended_at") != new.get("ended_at"):
                return True
        return False

    # ── Problem Events ───────────────────────────────────────────────

    def _on_problem_selected(self, problem: dict | None):
        self._cancel_attempts_poll()
        if problem:
            self.recording_panel.set_enabled(True)
            self.problem_panel.set_enabled(True)
            self._load_attempts(problem["id"])
            self._schedule_attempts_poll()
            # Restore attempt state
            self._update_attempt_ui_state()
        else:
            self.recording_panel.set_enabled(False)
            self.problem_panel.set_enabled(False)
            self.problem_panel.set_attempt_state("none")
            self.attempts_panel.set_attempts([])
            self.transcription_panel.clear()

    def _handle_create_problem(self):
        data = self.problem_panel.get_pending_create()
        if not data:
            return

        def _create():
            try:
                self.api.create_problem(data)
                self.root.after(0, self._load_problems)
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to create problem: {e}")

        threading.Thread(target=_create, daemon=True).start()

    # ── Attempt Lifecycle ────────────────────────────────────────────

    def _on_attempt_start(self):
        """Create a new attempt with status=in_progress."""
        problem = self.problem_panel.get_selected_problem()
        if not problem:
            return

        def _create():
            try:
                attempt = self.api.create_attempt(problem["id"], {"status": "in_progress"})
                self._current_attempt = attempt
                self.root.after(0, self.problem_panel.set_attempt_state, "in_progress")
                self.root.after(0, self.recording_panel.set_enabled, True)
                self.root.after(0, self._load_attempts, problem["id"])
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to start attempt: {e}")

        threading.Thread(target=_create, daemon=True).start()

    def _on_attempt_pause_toggle(self):
        """Toggle between paused and in_progress."""
        if not self._current_attempt:
            return
        current_status = self._current_attempt.get("status", "in_progress")
        new_status = "paused" if current_status == "in_progress" else "in_progress"

        def _update():
            try:
                updated = self.api.update_attempt(self._current_attempt["id"], {"status": new_status})
                self._current_attempt = updated
                self.root.after(0, self.problem_panel.set_attempt_state, new_status)
                problem = self.problem_panel.get_selected_problem()
                if problem:
                    self.root.after(0, self._load_attempts, problem["id"])
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to update attempt: {e}")

        threading.Thread(target=_update, daemon=True).start()

    def _on_attempt_stop(self):
        """Complete the current attempt."""
        if not self._current_attempt:
            return

        # If still recording, stop recording first
        if self.recorder.is_recording:
            self._on_record_stop()

        def _complete():
            try:
                self.api.update_attempt(
                    self._current_attempt["id"],
                    {"status": "completed", "ended_at": datetime.now(UTC).isoformat()},
                )
                self._current_attempt = None
                self.root.after(0, self.problem_panel.set_attempt_state, "none")
                self.root.after(0, self.recording_panel.set_enabled, False)
                problem = self.problem_panel.get_selected_problem()
                if problem:
                    self.root.after(0, self._load_attempts, problem["id"])
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to stop attempt: {e}")

        threading.Thread(target=_complete, daemon=True).start()

    def _update_attempt_ui_state(self):
        """Sync problem_panel attempt state with _current_attempt."""
        if self._current_attempt:
            self.problem_panel.set_attempt_state(self._current_attempt.get("status", "in_progress"))
            self.recording_panel.set_enabled(True)
        else:
            self.problem_panel.set_attempt_state("none")
            self.recording_panel.set_enabled(False)

    # ── Recording Events ─────────────────────────────────────────────

    def _on_record_start(self):
        """Start recording audio for the active attempt."""
        if not self._current_attempt:
            self.recording_panel.set_status("No active attempt! Start an attempt first.")
            return

        def _start():
            try:
                self.recorder.start()
                self.root.after(0, self.recording_panel.set_status, "Recording...")
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to start recording: {e}")
                self.root.after(0, self.recording_panel.set_status, "Error")

        threading.Thread(target=_start, daemon=True).start()

    def _on_record_pause(self):
        """Pause audio recording."""
        self.recorder.pause()

    def _on_record_resume(self):
        """Resume audio recording."""
        self.recorder.resume()

    def _on_record_stop(self):
        """Stop recording and upload."""

        def _stop_and_upload():
            try:
                audio_data = self.recorder.stop()
                self.root.after(0, self.recording_panel.set_status, "Uploading...")

                if self._current_attempt:
                    recording = self.api.upload_recording(self._current_attempt["id"], audio_data)
                    self.root.after(0, self.recording_panel.set_status, "Ready")
                    self.root.after(0, self._on_recording_uploaded, recording)
                else:
                    self.root.after(0, self.recording_panel.set_status, "Error: No active attempt")
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to upload: {e}")
                self.root.after(0, self.recording_panel.set_status, "Error")

        threading.Thread(target=_stop_and_upload, daemon=True).start()

    def _on_recording_uploaded(self, recording: dict):
        problem = self.problem_panel.get_selected_problem()
        if problem:
            self._load_attempts(problem["id"])
        self._start_transcription_polling(recording["id"])

    # ── Attempt Events ───────────────────────────────────────────────

    def _on_attempt_selected(self, attempt: dict | None):
        if attempt:
            self._load_transcription_for_attempt(attempt)
        else:
            self.transcription_panel.clear()

    def _load_transcription_for_attempt(self, attempt: dict):
        def _fetch():
            try:
                recordings = self.api.get_attempt_recordings(attempt["id"])
                if recordings:
                    rec = recordings[0]
                    self.root.after(
                        0,
                        self.transcription_panel.set_transcription,
                        rec.get("transcription"),
                        rec.get("transcription_status", "pending"),
                    )
                    if rec.get("transcription_status") in ("pending", "processing"):
                        self.root.after(0, self._start_transcription_polling, rec["id"])
                else:
                    self.root.after(0, self.transcription_panel.clear)
            except Exception:
                self.root.after(0, self.transcription_panel.clear)

        threading.Thread(target=_fetch, daemon=True).start()

    def _on_play_attempt(self, attempt: dict):
        self.attempts_panel.set_playing(True)

        def _download_and_play():
            try:
                recordings = self.api.get_attempt_recordings(attempt["id"])
                if recordings:
                    audio_data = self.api.download_audio(recordings[0]["id"])
                    self.player.play(
                        audio_data,
                        on_complete=lambda: self.root.after(0, self.attempts_panel.set_playing, False),
                    )
                else:
                    self.root.after(0, self._show_error, "No recording found for this attempt")
                    self.root.after(0, self.attempts_panel.set_playing, False)
            except Exception as e:
                self.root.after(0, self._show_error, f"Playback error: {e}")
                self.root.after(0, self.attempts_panel.set_playing, False)

        threading.Thread(target=_download_and_play, daemon=True).start()

    def _stop_playback(self):
        self.player.stop()
        self.attempts_panel.set_playing(False)

    def _on_delete_attempt(self, attempt: dict):
        def _delete():
            try:
                self.api.delete_attempt(attempt["id"])
                # If we deleted the active attempt, clear it
                if self._current_attempt and self._current_attempt["id"] == attempt["id"]:
                    self._current_attempt = None
                    self.root.after(0, self.problem_panel.set_attempt_state, "none")
                    self.root.after(0, self.recording_panel.set_enabled, False)
                problem = self.problem_panel.get_selected_problem()
                if problem:
                    self.root.after(0, self._load_attempts, problem["id"])
            except Exception as e:
                self.root.after(0, self._show_error, f"Failed to delete: {e}")

        threading.Thread(target=_delete, daemon=True).start()

    # ── Retranscribe ─────────────────────────────────────────────────

    def _handle_retranscribe(self):
        """Retranscribe the recording for the selected attempt."""
        attempt = self.attempts_panel.get_selected_attempt()
        if not attempt:
            return

        def _retranscribe():
            try:
                recordings = self.api.get_attempt_recordings(attempt["id"])
                if recordings:
                    rec = recordings[0]
                    self.api.retranscribe_recording(rec["id"])
                    self.root.after(
                        0,
                        self.transcription_panel.set_transcription,
                        None,
                        "pending",
                    )
                    self.root.after(0, self._start_transcription_polling, rec["id"])
                else:
                    self.root.after(0, self._show_error, "No recording found for this attempt")
            except Exception as e:
                self.root.after(0, self._show_error, f"Retranscribe failed: {e}")

        threading.Thread(target=_retranscribe, daemon=True).start()

    # ── Transcription Polling ────────────────────────────────────────

    def _start_transcription_polling(self, recording_id: int):
        self._poll_transcription(recording_id)

    def _poll_transcription(self, recording_id: int):
        def _check():
            try:
                result = self.api.get_transcription(recording_id)
                status = result.get("status", "pending")

                # Update attempt display
                try:
                    rec = self.api.get_recording(recording_id)
                    attempt_id = rec["attempt_id"]
                    duration = ""
                    if rec.get("duration_seconds"):
                        mins = int(rec["duration_seconds"] // 60)
                        secs = int(rec["duration_seconds"] % 60)
                        duration = f"{mins}:{secs:02d}"
                    self.root.after(
                        0,
                        self.attempts_panel.update_attempt_info,
                        attempt_id,
                        duration,
                        status,
                        True,
                    )
                except Exception:
                    pass

                # Update transcription panel if this is the selected attempt
                selected = self.attempts_panel.get_selected_attempt()
                if selected:
                    try:
                        rec = self.api.get_recording(recording_id)
                        if rec["attempt_id"] == selected["id"]:
                            self.root.after(
                                0,
                                self.transcription_panel.set_transcription,
                                result.get("transcription"),
                                status,
                            )
                    except Exception:
                        pass

                # Continue polling if not done
                if status in ("pending", "processing"):
                    self.root.after(TRANSCRIPTION_POLL_INTERVAL_MS, self._poll_transcription, recording_id)

            except Exception:
                self.root.after(TRANSCRIPTION_POLL_INTERVAL_MS, self._poll_transcription, recording_id)

        threading.Thread(target=_check, daemon=True).start()

    # ── Helpers ──────────────────────────────────────────────────────

    def _show_error(self, message: str):
        messagebox.showerror("Error", message, parent=self.root)

    def _on_close(self):
        self._cancel_attempts_poll()
        if self._problems_poll_id:
            self.root.after_cancel(self._problems_poll_id)
        self.docker_panel.cancel_polling()
        self._canvas.unbind_all("<MouseWheel>")
        self.recorder.cleanup()
        self.player.cleanup()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = PrepLogApp()
    app.run()


if __name__ == "__main__":
    main()
