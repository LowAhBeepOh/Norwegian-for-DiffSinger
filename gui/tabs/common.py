"""Small widgets shared by several tabs."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ..tooltip import add_tip


class FolderPicker(ctk.CTkFrame):
    """A button that asks for a folder plus a label showing the choice."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        button_text: str,
        dialog_title: str,
        tip: str | None = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._folder: Path | None = None
        self._dialog_title = dialog_title

        self.button = ctk.CTkButton(self, text=button_text, command=self._choose)
        self.button.pack(side="left")
        if tip is not None:
            add_tip(self.button, tip)

        self.label = ctk.CTkLabel(
            self,
            text="No folder selected",
            anchor="w",
            justify="left",
            wraplength=540,
        )
        self.label.pack(side="left", padx=(8, 0))

    @property
    def folder(self) -> Path | None:
        return self._folder

    def _choose(self) -> None:
        folder = filedialog.askdirectory(
            title=self._dialog_title, parent=self.winfo_toplevel()
        )
        if folder:
            self._folder = Path(folder)
            self.label.configure(text=folder)

    def require(self, app: ctk.CTk) -> Path | None:
        """Return the chosen folder, or log a hint and return None."""
        if self._folder is None:
            app.log.write("Choose a folder first.")
            return None
        return self._folder
