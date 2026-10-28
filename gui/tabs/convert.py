"""Convert Format tab: TextGrid -> HTK labels for a folder of .TextGrid files."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..logic import htk
from ..tooltip import add_tip


class ConvertTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app
        self.folder: str | None = None

        info = ctk.CTkLabel(
            self,
            text="Convert TextGrid files to HTK .lab files, next to each TextGrid.",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(info, "Turns the TextGrid files from MFA into the HTK .lab format DiffSinger uses.")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w", padx=10, pady=4)
        choose = ctk.CTkButton(row, text="Choose folder", command=self._choose)
        choose.pack(side="left", padx=(0, 8))
        add_tip(choose, "Pick the folder that contains your .TextGrid files.")
        label = ctk.CTkLabel(row, text="Tier name:")
        label.pack(side="left", padx=(8, 4))
        add_tip(
            label,
            "The TextGrid tier with the phone labels. MFA usually calls it 'phones'. "
            "Leave it as is unless your tier has a different name.",
        )
        self.tier = ctk.CTkEntry(row, width=140)
        self.tier.insert(0, "phones")
        self.tier.pack(side="left", padx=(0, 8))
        add_tip(self.tier, "Name of the TextGrid tier to convert. Default: phones.")
        convert = ctk.CTkButton(row, text="Convert to HTK", command=self._convert)
        convert.pack(side="left")
        add_tip(
            convert,
            "Converts every TextGrid in the chosen folder to a .lab file with the same name, "
            "in the same folder.",
        )

        self.folder_label = ctk.CTkLabel(self, text="No folder selected")
        self.folder_label.pack(anchor="w", padx=10, pady=8)
        add_tip(self.folder_label, "The folder that will be converted.")

    def _choose(self) -> None:
        folder = filedialog.askdirectory(title="Choose the folder with TextGrid files")
        if folder:
            self.folder = folder
            self.folder_label.configure(text=folder)

    def _convert(self) -> None:
        if not self.folder:
            self.app.log.write("Choose a folder first.")
            return
        tier = self.tier.get().strip() or "phones"
        folder = Path(self.folder)
        self.app.run_task(lambda emit: htk.convert_folder(folder, tier, emit))
