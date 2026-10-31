"""Fix Phonemes tab: simplify labels and turn silent pauses into breaths."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import phonemes
from ..tooltip import add_tip
from .common import FolderPicker


class FixPhonemesTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        info = ctk.CTkLabel(self, text="Simplify the phones in the .lab files and detect breaths.")
        info.pack(anchor="w", padx=10, pady=(12, 8))

        self.picker = FolderPicker(
            self,
            button_text="Choose folder",
            dialog_title="Choose the folder with .lab files",
            tip="Pick the folder that contains the .lab files to fix.",
        )
        self.picker.pack(fill="x", padx=10, pady=4)

        self.skip_breathing = ctk.CTkCheckBox(
            self, text="Skip breathing detection"
        )
        self.skip_breathing.pack(anchor="w", padx=10, pady=(8, 4))
        add_tip(
            self.skip_breathing,
            "Leave every pause as SP. Turn this on if you do not want breath sounds "
            "(AP) detected from the audio, or if the .wav files are not available.",
        )

        fix = ctk.CTkButton(self, text="Fix phonemes", command=self._fix)
        fix.pack(anchor="w", padx=10, pady=8)
        add_tip(
            fix,
            "Overwrites the .lab files in the chosen folder with the fixed labels.",
        )
        self.app.register_job_button(fix)

    def _fix(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        breathing = not bool(self.skip_breathing.get())

        def job(task):
            phonemes.fix_folder(
                folder,
                phonemes.load_simplified_phonemes(),
                task.emit,
                breathing=breathing,
                should_cancel=task.check,
                progress=task.progress,
            )

        self.app.run_task(job)
