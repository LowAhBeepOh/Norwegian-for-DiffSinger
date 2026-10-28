"""Applies saved settings (light mode, high contrast, font) to CustomTkinter.

Call ``apply`` once, after the root window exists and before any widgets are
built. Colour and font changes only reach widgets created afterwards, so the
Config tab asks for a restart for those.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Iterable

import customtkinter as ctk

from .settings import Settings

# First installed font wins. "Roboto" is CustomTkinter's current default font.
# If none of these are installed, the operating system's default font is used.
PREFERRED_FONTS = ["Inter Tight", "Inter", "Roboto", "Arial"]

# Colours as (light mode, dark mode) pairs, the format CustomTkinter expects.
HIGH_CONTRAST: dict[str, dict[str, list[str]]] = {
    "CTkButton": {
        "fg_color": ["#0000B0", "#FFD400"],
        "hover_color": ["#000080", "#FFE54D"],
        "text_color": ["#FFFFFF", "#000000"],
        "border_color": ["#000000", "#FFFFFF"],
    },
    "CTkOptionMenu": {
        "fg_color": ["#0000B0", "#FFD400"],
        "button_color": ["#000080", "#FFE54D"],
        "text_color": ["#FFFFFF", "#000000"],
    },
    "CTkLabel": {"text_color": ["#000000", "#FFFFFF"]},
    "CTkFrame": {
        "fg_color": ["#FFFFFF", "#000000"],
        "border_color": ["#000000", "#FFFFFF"],
    },
    "CTkEntry": {
        "fg_color": ["#FFFFFF", "#000000"],
        "text_color": ["#000000", "#FFFFFF"],
        "border_color": ["#000000", "#FFFFFF"],
    },
}


def pick_font(installed: Iterable[str], system_font: str) -> str:
    """Return the first preferred font that is installed, else the system font."""
    lowered = {name.lower() for name in installed}
    for name in PREFERRED_FONTS:
        if name.lower() in lowered:
            return name
    return system_font


def apply(root: tk.Misc, settings: Settings) -> str:
    """Apply the saved settings and return the font family that was chosen."""
    if settings.light_mode is None:
        ctk.set_appearance_mode("system")
    else:
        ctk.set_appearance_mode("light" if settings.light_mode else "dark")

    if settings.high_contrast:
        for widget, values in HIGH_CONTRAST.items():
            ctk.ThemeManager.theme[widget].update(values)

    system_font = tkfont.nametofont("TkDefaultFont").actual("family")
    family = pick_font(tkfont.families(root), system_font)
    ctk.ThemeManager.theme["CTkFont"]["family"] = family
    return family
