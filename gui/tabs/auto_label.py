"""Auto Label tab: run NoFA-MFA on a folder with wavs/ and transcriptions/."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import mfa
from ..tooltip import add_tip
from .common import FolderPicker


class AutoLabelTab(ctk.CTkFrame):
    STATUS_CHECKING = "Norwegian MFA: checking..."
    STATUS_READY = "Norwegian MFA: installed"
    STATUS_MISSING = "Norwegian MFA: not installed"

    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        info = ctk.CTkLabel(
            self,
            text="The chosen folder must contain 'wavs' (.wav) and 'transcriptions' (.txt) subfolders.\n"
            "Results go into a new 'labs' folder inside the chosen folder.",
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(
            info,
            "Your folder needs two subfolders: 'wavs' with the audio, and 'transcriptions' "
            "with a .txt of the same name for each .wav. Results go into 'labs'.",
        )

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(anchor="w", padx=10, pady=4)
        install = ctk.CTkButton(buttons, text="Install Norwegian MFA", command=self._install)
        install.pack(side="left", padx=(0, 8))
        add_tip(
            install,
            "Installs Montreal Forced Aligner and the Norwegian NoFA model. Only needed once. "
            "Each step is skipped if it's already installed.",
        )
        self.app.register_job_button(install)

        self.picker = FolderPicker(
            self,
            button_text="Choose folder",
            dialog_title="Choose the folder with wavs and transcriptions",
            tip="Pick the parent folder that contains the 'wavs' and 'transcriptions' subfolders.",
        )
        self.picker.pack(fill="x", padx=10, pady=(4, 8))

        start = ctk.CTkButton(self, text="Start auto-labelling", command=self._start)
        start.pack(anchor="w", padx=10)
        add_tip(
            start,
            "Aligns each audio file with its transcription and writes TextGrid files into a "
            "'labs' folder. Needs MFA installed and a folder chosen.",
        )
        self.app.register_job_button(start)

        self.status = ctk.CTkLabel(self, text=self.STATUS_CHECKING)
        self.status.pack(anchor="w", padx=10, pady=8)
        add_tip(self.status, "Whether Norwegian MFA is ready to use.")
        self._refresh_status()

    def _show_status(self, ready: object) -> None:
        self.status.configure(text=self.STATUS_READY if ready else self.STATUS_MISSING)

    def _refresh_status(self) -> None:
        self.status.configure(text=self.STATUS_CHECKING)
        self.app.run_background(mfa.is_ready, self._show_status)

    def _install(self) -> None:
        def job(task):
            mfa.install_mfa(task.emit, should_cancel=task.check)
            mfa.install_nofa(task.emit, should_cancel=task.check)

        self.app.run_task(job, on_done=self._refresh_status)

    def _start(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        self.app.run_task(
            lambda task: mfa.align_folder(folder, task.emit, should_cancel=task.check)
        )
