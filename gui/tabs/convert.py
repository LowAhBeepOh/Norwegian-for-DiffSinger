"""Convert Format tab: TextGrid -> HTK labels in a 'labs' folder."""

from __future__ import annotations

import customtkinter as ctk

from ..logic import htk
from ..tooltip import add_tip
from .common import FolderPicker


class ConvertTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        info = ctk.CTkLabel(
            self,
            text="Convert TextGrid files to HTK .lab files in a 'labs' folder.",
        )
        info.pack(anchor="w", padx=10, pady=(12, 8))
        add_tip(info, "Turns the TextGrid files from MFA into the HTK .lab format DiffSinger uses.")

        self.picker = FolderPicker(
            self,
            button_text="Choose folder",
            dialog_title="Choose the folder with TextGrid files",
            tip="Pick the folder that contains your .TextGrid files.",
        )
        self.picker.pack(fill="x", padx=10, pady=4)

        convert = ctk.CTkButton(self, text="Convert to HTK", command=self._convert)
        convert.pack(anchor="w", padx=10, pady=8)
        add_tip(
            convert,
            "Converts every TextGrid in the chosen folder to a .lab file in a 'labs' folder "
            "next to it, then deletes the TextGrid folder.",
        )
        self.app.register_job_button(convert)

    def _convert(self) -> None:
        folder = self.picker.require(self.app)
        if folder is None:
            return
        self.app.run_task(
            lambda task: htk.convert_folder(
                folder,
                task.emit,
                should_cancel=task.check,
                progress=task.progress,
            )
        )
