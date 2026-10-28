"""Auto Label tab: run NoFA-MFA on a folder with wavs/ and transcriptions/."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..logic import mfa
from ..tooltip import add_tip


class AutoLabelTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app
        self.folder: str | None = None

        info = ctk.CTkLabel(
            self,
            text="The chosen folder must contain 'wavs' (.wav) and 'transcriptions' (.txt) subfolders.\n"
            "Results go into a new 'labels' folder inside the chosen folder.",
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(
            info,
            "Your folder needs two subfolders: 'wavs' with the audio, and 'transcriptions' "
            "with a .txt of the same name for each .wav. Results go into 'labels'.",
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
        choose = ctk.CTkButton(buttons, text="Choose folder", command=self._choose)
        choose.pack(side="left", padx=(0, 8))
        add_tip(
            choose,
            "Pick the parent folder that contains the 'wavs' and 'transcriptions' subfolders.",
        )
        start = ctk.CTkButton(buttons, text="Start auto-labelling", command=self._start)
        start.pack(side="left")
        add_tip(
            start,
            "Aligns each audio file with its transcription and writes TextGrid files into a "
            "'labels' folder. Needs MFA installed and a folder chosen.",
        )

        self.folder_label = ctk.CTkLabel(self, text="No folder selected")
        self.folder_label.pack(anchor="w", padx=10, pady=8)
        add_tip(self.folder_label, "The folder that auto-labelling will run on.")
        self.status = ctk.CTkLabel(self, text=self._status_text())
        self.status.pack(anchor="w", padx=10)
        add_tip(self.status, "Whether Norwegian MFA is ready to use.")

    @staticmethod
    def _status_text() -> str:
        return "Norwegian MFA: installed" if mfa.is_ready() else "Norwegian MFA: not installed"

    def _choose(self) -> None:
        folder = filedialog.askdirectory(title="Choose the folder with wavs and transcriptions")
        if folder:
            self.folder = folder
            self.folder_label.configure(text=folder)

    def _install(self) -> None:
        def job(emit):
            mfa.install_mfa(emit)
            mfa.install_nofa(emit)
            self.after(0, lambda: self.status.configure(text=self._status_text()))

        self.app.run_task(job)

    def _start(self) -> None:
        if not self.folder:
            self.app.log.write("Choose a folder first.")
            return
        folder = Path(self.folder)
        self.app.run_task(lambda emit: mfa.align_folder(folder, emit))
