"""Fix Phonemes tab: rewrite .lab labels to the simplified NoFAbet set."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..logic import phonemes
from ..tooltip import add_tip


class FixPhonemesTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app
        self.folder: str | None = None

        info = ctk.CTkLabel(
            self,
            text="Rewrite standard NoFAbet labels (e.g. AH2) to the simplified set (ah).\n"
            "Phones that can't be mapped are listed in the log and left unchanged.",
            justify="left",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(
            info,
            "Strips stress digits (AH2 becomes ah) so labels match the project's phone set. "
            "Anything it can't map is reported in the log.",
        )

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=10, pady=4)
        choose = ctk.CTkButton(row, text="Choose folder", command=self._choose)
        choose.pack(side="left", padx=(0, 8))
        add_tip(choose, "Pick the folder that contains the .lab files to fix.")
        fix = ctk.CTkButton(row, text="Fix phonemes", command=self._fix)
        fix.pack(side="left")
        add_tip(
            fix,
            "Rewrites the .lab files in the chosen folder in place. Keep a backup if you're unsure.",
        )

        self.folder_label = ctk.CTkLabel(self, text="No folder selected")
        self.folder_label.pack(anchor="w", padx=10, pady=8)
        add_tip(self.folder_label, "The folder whose labels will be fixed.")

    def _choose(self) -> None:
        folder = filedialog.askdirectory(title="Choose the folder with .lab files")
        if folder:
            self.folder = folder
            self.folder_label.configure(text=folder)

    def _fix(self) -> None:
        if not self.folder:
            self.app.log.write("Choose a folder first.")
            return
        folder = Path(self.folder)
        self.app.run_task(
            lambda emit: phonemes.fix_labels_folder(folder, phonemes.load_simplified_phonemes(), emit)
        )
