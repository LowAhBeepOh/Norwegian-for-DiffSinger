"""Main window: a CustomTkinter app with eight tabs.

Long jobs run on a worker thread. They report progress through ``Task``,
which queues updates for the UI thread, so the window stays responsive and
only one job runs at a time.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import customtkinter as ctk

from . import appearance, settings
from .logic.process import CancelledError
from .tabs.about import AboutTab
from .tabs.auto_label import AutoLabelTab
from .tabs.check_labels import CheckLabelsTab
from .tabs.config import ConfigTab
from .tabs.convert import ConvertTab
from .tabs.fix_phonemes import FixPhonemesTab
from .tabs.pipeline import PipelineTab
from .tabs.transcribe import TranscribeTab

APP_TITLE = "Norwegian for DiffSinger"
MAX_LOG_LINES = 5000


class LogBox(ctk.CTkTextbox):
    """Read-only log that can be written to from any thread via ``write``.

    Lines are queued and inserted in batches, so a chatty tool such as MFA
    cannot flood the UI with one redraw per line.
    """

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, height=160, state="disabled")
        self._queue: queue.Queue[str] = queue.Queue()
        self.after(100, self._drain)

    def write(self, line: str) -> None:
        self._queue.put(line)

    def _drain(self) -> None:
        lines: list[str] = []
        try:
            while len(lines) < MAX_LOG_LINES:
                lines.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.configure(state="normal")
            self.insert("end", "\n".join(lines) + "\n")
            self._trim()
            self.see("end")
            self.configure(state="disabled")
        self.after(100, self._drain)

    def _trim(self) -> None:
        """Keep only the last ``MAX_LOG_LINES`` lines so long runs stay fast."""
        total = int(self.index("end-1c").split(".")[0])
        if total > MAX_LOG_LINES:
            self.delete("1.0", f"{total - MAX_LOG_LINES + 1}.0")


class Task:
    """Handle a running job uses to log, report progress and check for cancel."""

    def __init__(self, app: "App") -> None:
        self._app = app
        self._cancelled = threading.Event()

    def emit(self, line: str) -> None:
        self._app.log.write(line)

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        """Raise CancelledError when the user pressed Cancel."""
        if self._cancelled.is_set():
            raise CancelledError()

    def progress(self, done: float, total: float, text: str | None = None) -> None:
        fraction = 0.0 if total <= 0 else min(max(done / total, 0.0), 1.0)
        self._app.post_progress(fraction, text)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x760")
        self.minsize(760, 640)

        self.settings = settings.load()
        appearance.apply(self, self.settings)

        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._task: Task | None = None
        self._job_buttons: list[ctk.CTkButton] = []
        self._build_status_bar()

        self.log = LogBox(self)
        self.log.pack(side="bottom", fill="x", padx=10, pady=(0, 4))

        tabs = ctk.CTkTabview(self)
        tabs.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        for name, tab_cls in [
            ("About", AboutTab),
            ("Pipeline", PipelineTab),
            ("Transcribe", TranscribeTab),
            ("Auto Label", AutoLabelTab),
            ("Convert Format", ConvertTab),
            ("Fix Phonemes", FixPhonemesTab),
            ("Check Auto-Label Errors", CheckLabelsTab),
            ("Config", ConfigTab),
        ]:
            tab = tabs.add(name)
            tab_cls(tab, self)

        self.after(50, self._drain_events)

    def _build_status_bar(self) -> None:
        self._status_bar = ctk.CTkFrame(self)
        self._status_bar.pack(side="bottom", fill="x", padx=10, pady=(0, 8))

        self.status_label = ctk.CTkLabel(self._status_bar, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=(10, 8), pady=6)

        self.cancel_button = ctk.CTkButton(
            self._status_bar,
            text="Cancel",
            width=80,
            command=self._cancel,
            state="disabled",
        )
        self.cancel_button.pack(side="right", padx=10, pady=6)

        self.progress = ctk.CTkProgressBar(self._status_bar, width=240)
        self.progress.pack(side="right", padx=8)
        self.progress.set(0)

    # ------------------------------------------------------------- threading
    def post(self, callback: Callable[[], None]) -> None:
        """Run ``callback`` on the UI thread; safe to call from any thread."""
        self._events.put(("call", callback))

    def post_progress(self, fraction: float, text: str | None = None) -> None:
        self._events.put(("progress", (fraction, text)))

    def _drain_events(self) -> None:
        latest_progress: tuple[float, str | None] | None = None
        callbacks: list[Callable[[], None]] = []
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "progress":
                    latest_progress = payload  # type: ignore[assignment]
                else:
                    callbacks.append(payload)  # type: ignore[arg-type]
        except queue.Empty:
            pass

        if latest_progress is not None:
            fraction, text = latest_progress
            self.progress.set(fraction)
            if text:
                self.status_label.configure(text=text)
        for callback in callbacks:
            try:
                callback()
            except Exception as exc:  # noqa: BLE001 - a UI error must not kill the loop
                self.log.write(f"ERROR: {exc}")
        self.after(50, self._drain_events)

    def run_task(
        self,
        func: Callable[[Task], None],
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Run ``func(task)`` on a worker thread, logging output and errors.

        Only one job runs at a time. While a job runs, job buttons are
        disabled and the Cancel button is enabled.
        """
        if self._task is not None:
            self.log.write(
                "A task is already running. Wait for it to finish or press Cancel."
            )
            return

        task = Task(self)
        self._task = task
        self.progress.set(0)
        self.status_label.configure(text="Working...")
        self._set_busy(True)

        def worker() -> None:
            succeeded = False
            try:
                func(task)
                succeeded = True
            except CancelledError:
                task.emit("Cancelled.")
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                task.emit(f"ERROR: {exc}")
            finally:
                self.post(lambda: self._finish(task, on_done if succeeded else None))

        threading.Thread(target=worker, daemon=True).start()

    def run_background(
        self, func: Callable[[], object], on_result: Callable[[object], None]
    ) -> None:
        """Run a quick query off the UI thread and pass its result back."""

        def worker() -> None:
            try:
                result = func()
            except Exception as exc:  # noqa: BLE001 - surfaced in the log
                self.log.write(f"ERROR: {exc}")
                return
            self.post(lambda: on_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _finish(self, task: Task, on_done: Callable[[], None] | None) -> None:
        if self._task is not task:
            return
        self._task = None
        self.progress.set(0)
        self.status_label.configure(text="Ready")
        self._set_busy(False)
        if on_done is not None:
            try:
                on_done()
            except Exception as exc:  # noqa: BLE001
                self.log.write(f"ERROR: {exc}")

    def _cancel(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self.status_label.configure(text="Cancelling...")

    # ------------------------------------------------------------- busy state
    def register_job_button(self, button: ctk.CTkButton) -> None:
        """Register a button that should be disabled while a job runs."""
        self._job_buttons.append(button)
        if self._task is not None:
            button.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        for button in self._job_buttons:
            button.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")


def main() -> None:
    App().mainloop()
