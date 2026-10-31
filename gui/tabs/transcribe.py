"""Transcribe tab: pick a folder of .wav files and a Whisper model."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import transcribe
from ..tooltip import add_tip
from .common import FolderPicker

DEFAULT_FAMILY = "NB-Whisper"
DEFAULT_SIZE = "small"


class TranscribeTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        self.picker = FolderPicker(
            self,
            button_text="Choose folder with .wav files",
            dialog_title="Choose folder with .wav files",
            tip="Pick the folder that contains your .wav files. The transcriptions go into a "
            "'transcriptions' folder next to it.",
        )
        self.picker.pack(anchor="w", padx=10, pady=(12, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=10, pady=10)
        self.family = ctk.CTkOptionMenu(
            row, values=list(transcribe.FAMILIES), command=lambda _: self._refresh_sizes()
        )
        self.family.set(DEFAULT_FAMILY)
        self.family.pack(side="left", padx=(0, 8))
        add_tip(
            self.family,
            "Which Whisper model family to use. NB-Whisper is trained on Norwegian and is "
            "usually the better choice for Norwegian lyrics or speech.",
        )
        self.size = ctk.CTkOptionMenu(row, values=[""], command=lambda _: self._refresh_status())
        self.size.pack(side="left", padx=(0, 8))
        add_tip(
            self.size,
            "Model size. Bigger models are more accurate but slower and use more disk and memory.",
        )
        self.status = ctk.CTkLabel(row, text="")
        self.status.pack(side="left", padx=8)
        add_tip(self.status, "Whether the selected model is already downloaded.")
        self._refresh_sizes()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(anchor="w", padx=10, pady=4)
        install = ctk.CTkButton(buttons, text="Install model", command=self._install)
        install.pack(side="left", padx=(0, 8))
        add_tip(
            install,
            "Downloads the selected model from Hugging Face so transcription can run offline. "
            "Only needed once per model.",
        )
        self.app.register_job_button(install)
        transcribe_button = ctk.CTkButton(
            buttons, text="Transcribe audio", command=self._transcribe
        )
        transcribe_button.pack(side="left")
        add_tip(
            transcribe_button,
            "Transcribes every .wav in the chosen folder into a 'transcriptions' folder next to it. "
            "Needs the model installed first.",
        )
        self.app.register_job_button(transcribe_button)

    def _refresh_sizes(self) -> None:
        sizes = list(transcribe.FAMILIES[self.family.get()])
        self.size.configure(values=sizes)
        self.size.set(DEFAULT_SIZE if DEFAULT_SIZE in sizes else sizes[0])
        self._refresh_status()

    def _current_repo(self) -> str:
        return transcribe.repo_id(self.family.get(), self.size.get())

    def _refresh_status(self) -> None:
        installed = transcribe.is_installed(self._current_repo())
        self.status.configure(text="Installed" if installed else "Not installed")

    def _install(self) -> None:
        repo = self._current_repo()
        self.app.run_task(
            lambda task: transcribe.install_model(repo, task.emit),
            on_done=self._refresh_status,
        )

    def _transcribe(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        repo = self._current_repo()
        self.app.run_task(
            lambda task: transcribe.transcribe_folder(
                folder,
                repo,
                task.emit,
                force_cpu=self.app.settings.force_cpu,
                should_cancel=task.check,
                progress=task.progress,
            )
        )
