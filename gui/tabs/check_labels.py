"""Check Auto-Label Errors tab: flag labels that are too short, overlapping or zero-length."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..logic import label_check
from ..tooltip import add_tip


class CheckLabelsTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app
        self.folder: str | None = None

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

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=10, pady=4)
        choose = ctk.CTkButton(row, text="Choose folder", command=self._choose)
        choose.pack(side="left", padx=(0, 8))
        add_tip(choose, "Pick the folder that contains the .lab files to check.")
        check = ctk.CTkButton(row, text="Check labels", command=self._check)
        check.pack(side="left")
        add_tip(
            check,
            "Scans every .lab in the chosen folder and lists the suspicious labels in the log.",
        )

        self.folder_label = ctk.CTkLabel(self, text="No folder selected")
        self.folder_label.pack(anchor="w", padx=10, pady=8)
        add_tip(self.folder_label, "The folder that will be checked.")

    def _choose(self) -> None:
        folder = filedialog.askdirectory(title="Choose the folder with .lab files")
        if folder:
            self.folder = folder
            self.folder_label.configure(text=folder)

    def _check(self) -> None:
        if not self.folder:
            self.app.log.write("Choose a folder first.")
            return
        folder = Path(self.folder)
        self.app.run_task(lambda emit: label_check.check_folder(folder, emit))
