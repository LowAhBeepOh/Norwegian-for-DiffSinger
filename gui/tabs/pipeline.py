"""Pipeline tab: run the whole dataset preparation in one go."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import pipeline, transcribe
from ..tooltip import add_tip
from .common import FolderPicker
from .transcribe import DEFAULT_FAMILY, DEFAULT_SIZE


class PipelineTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        info = ctk.CTkLabel(
            self,
            text="Runs every step on one dataset folder.\n"
            "Expected layout: your_folder/wavs  ->  transcriptions/  ->  labs/",
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(
            info,
            "Transcribe audio, auto-label it with MFA, convert the TextGrids to HTK, "
            "simplify the phones (and detect breaths), then check the labels.",
        )

        self.picker = FolderPicker(
            self,
            button_text="Choose dataset folder",
            dialog_title="Choose the dataset folder (the one with a 'wavs' subfolder)",
            tip="Pick the folder with your 'wavs' subfolder. Missing folders are created.",
        )
        self.picker.pack(fill="x", padx=10, pady=4)

        self.skip_breathing = ctk.CTkCheckBox(self, text="Skip breathing detection")
        self.skip_breathing.pack(anchor="w", padx=10, pady=(6, 0))
        add_tip(
            self.skip_breathing,
            "Leave every pause as SP instead of detecting breaths (AP) in the audio.",
        )

        model_row = ctk.CTkFrame(self, fg_color="transparent")
        model_row.pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(model_row, text="Model:", anchor="w").pack(side="left", padx=(0, 6))
        self.family = ctk.CTkOptionMenu(
            model_row, values=list(transcribe.FAMILIES), command=lambda _: self._refresh_sizes()
        )
        self.family.set(DEFAULT_FAMILY)
        self.family.pack(side="left", padx=(0, 8))
        add_tip(
            self.family,
            "Model family for the transcribe step. NB-Whisper is trained on Norwegian.",
        )
        self.size = ctk.CTkOptionMenu(
            model_row, values=[""], command=lambda _: self._refresh_status()
        )
        self.size.pack(side="left", padx=(0, 8))
        add_tip(self.size, "Model size: bigger is more accurate but slower.")
        self.model_status = ctk.CTkLabel(model_row, text="")
        self.model_status.pack(side="left", padx=(0, 8))
        install = ctk.CTkButton(model_row, text="Install model", width=110, command=self._install)
        install.pack(side="left")
        add_tip(install, "Downloads the selected model once, for the transcribe step.")
        self.app.register_job_button(install)

        run = ctk.CTkButton(self, text="Run pipeline", command=self._run)
        run.pack(anchor="w", padx=10, pady=12)
        add_tip(
            run,
            "Runs every step in order. You can cancel while it runs; the log shows "
            "which step is busy.",
        )
        self.app.register_job_button(run)

        self._refresh_sizes()

    def _current_repo(self) -> str:
        return transcribe.repo_id(self.family.get(), self.size.get())

    def _refresh_sizes(self) -> None:
        sizes = list(transcribe.FAMILIES[self.family.get()])
        self.size.configure(values=sizes)
        self.size.set(DEFAULT_SIZE if DEFAULT_SIZE in sizes else sizes[0])
        self._refresh_status()

    def _refresh_status(self) -> None:
        installed = transcribe.is_installed(self._current_repo())
        self.model_status.configure(text="Installed" if installed else "Not installed")

    def _install(self) -> None:
        repo = self._current_repo()
        self.app.run_task(
            lambda task: transcribe.install_model(repo, task.emit),
            on_done=self._refresh_status,
        )

    def _run(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        options = pipeline.Options(
            breathing=not bool(self.skip_breathing.get()),
            repo=self._current_repo(),
            force_cpu=self.app.settings.force_cpu,
        )
        self.app.run_task(
            lambda task: pipeline.run(
                folder,
                options,
                task.emit,
                should_cancel=task.check,
                progress=task.progress,
            )
        )
