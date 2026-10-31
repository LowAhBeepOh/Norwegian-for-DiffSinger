"""Check Auto-Label Errors tab: flag labels that are too short, overlapping or zero-length."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import label_check
from ..tooltip import add_tip
from .common import FolderPicker


class CheckLabelsTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        info = ctk.CTkLabel(
            self,
            text="Scan .lab files for labels under 22 ms (minor) or 10 ms (major),\n"
            "plus overlapping or zero-length labels. Review these by hand.",
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(
            info,
            "Flags labels that are suspiciously short or overlapping, which often means an "
            "alignment mistake. The results are hints, so check them by ear.",
        )

        self.picker = FolderPicker(
            self,
            button_text="Choose folder",
            dialog_title="Choose the folder with .lab files",
            tip="Pick the folder that contains the .lab files to check.",
        )
        self.picker.pack(fill="x", padx=10, pady=4)

        check = ctk.CTkButton(self, text="Check labels", command=self._check)
        check.pack(anchor="w", padx=10, pady=8)
        add_tip(
            check,
            "Scans every .lab in the chosen folder and lists the suspicious labels in the log.",
        )
        self.app.register_job_button(check)

    def _check(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        self.app.run_task(
            lambda task: label_check.check_folder(
                folder,
                task.emit,
                should_cancel=task.check,
                progress=task.progress,
            )
        )
