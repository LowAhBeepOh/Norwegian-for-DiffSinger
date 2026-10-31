"""Config tab: saved display and processing settings."""

from __future__ import annotations

import customtkinter as ctk

from .. import settings
from ..tooltip import add_tip


class ConfigTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        ctk.CTkLabel(
            self,
            text="Settings are saved automatically.",
            text_color=("gray35", "gray70"),
        ).pack(anchor="w", padx=10, pady=(10, 8))

        self.light_mode = ctk.CTkSwitch(
            self,
            text="Light mode (off = dark mode)",
            command=self._on_light_mode,
        )
        self.light_mode.pack(anchor="w", padx=10, pady=6)
        add_tip(
            self.light_mode,
            "Switch between light and dark colours. Applies straight away.",
        )
        is_light = app.settings.light_mode
        if is_light is None:
            is_light = ctk.get_appearance_mode() == "Light"
        if is_light:
            self.light_mode.select()

        self.high_contrast = ctk.CTkSwitch(
            self, text="High contrast (restart needed)", command=self._save
        )
        self.high_contrast.pack(anchor="w", padx=10, pady=6)
        add_tip(
            self.high_contrast,
            "Stronger colours and borders so buttons and text are easier to see. "
            "Takes effect after you restart the app.",
        )
        if app.settings.high_contrast:
            self.high_contrast.select()

        self.force_cpu = ctk.CTkSwitch(
            self, text="Force CPU (not recommended)", command=self._save
        )
        self.force_cpu.pack(anchor="w", padx=10, pady=6)
        add_tip(
            self.force_cpu,
            "Runs transcription on the processor even if a GPU is available. It is much "
            "slower, so only use it if the GPU causes problems.",
        )
        if app.settings.force_cpu:
            self.force_cpu.select()

    def _on_light_mode(self) -> None:
        light = bool(self.light_mode.get())
        ctk.set_appearance_mode("light" if light else "dark")
        self._save()

    def _save(self) -> None:
        self.app.settings = settings.Settings(
            light_mode=bool(self.light_mode.get()),
            high_contrast=bool(self.high_contrast.get()),
            force_cpu=bool(self.force_cpu.get()),
        )
        settings.save(self.app.settings)
