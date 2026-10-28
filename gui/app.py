"""Main window: a CustomTkinter app with six tabs."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import customtkinter as ctk

from . import appearance, settings
from .tabs.about import AboutTab
from .tabs.config import ConfigTab
from .tabs.auto_label import AutoLabelTab
from .tabs.check_labels import CheckLabelsTab
from .tabs.convert import ConvertTab
from .tabs.fix_phonemes import FixPhonemesTab
from .tabs.transcribe import TranscribeTab

APP_TITLE = "Norwegian for DiffSinger"


class LogBox(ctk.CTkTextbox):
    """Read-only log that can be written to from any thread via ``post``."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, height=160, state="disabled")
        self._queue: queue.Queue[str] = queue.Queue()
        self.after(100, self._drain)

    def write(self, line: str) -> None:
        self._queue.put(line)

    def _drain(self) -> None:
        try:
            while True:
                line = self._queue.get_nowait()
                self.configure(state="normal")
                self.insert("end", line + "\n")
                self.see("end")
                self.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._drain)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x720")
        self.minsize(760, 600)

        self.settings = settings.load()
        appearance.apply(self, self.settings)

        self.log = LogBox(self)
        self.log.pack(side="bottom", fill="x", padx=10, pady=(0, 10))

        tabs = ctk.CTkTabview(self)
        tabs.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        for name, tab_cls in [
            ("About", AboutTab),
            ("Transcribe", TranscribeTab),
            ("Auto Label", AutoLabelTab),
            ("Convert Format", ConvertTab),
            ("Fix Phonemes", FixPhonemesTab),
            ("Check Auto-Label Errors", CheckLabelsTab),
            ("Config", ConfigTab),
        ]:
            tab = tabs.add(name)
            tab_cls(tab, self)

    def run_task(
        self,
        func: Callable[[Callable[[str], None]], object],
        on_done: Callable[[], None] | None = None,
    ) -> None:
        """Run ``func(emit)`` on a worker thread, logging its output and errors.

        ``emit`` writes a line to the log. Errors are shown in the log too, so
        the GUI never freezes on a long operation.
        """

        def worker() -> None:
            try:
                func(self.log.write)
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                self.log.write(f"ERROR: {exc}")
            else:
                if on_done is not None:
                    self.after(0, on_done)
            finally:
                self.after(0, lambda: self._finish_task())

        self._busy = True
        threading.Thread(target=worker, daemon=True).start()

    def _finish_task(self) -> None:
        self._busy = False


def main() -> None:
    App().mainloop()
