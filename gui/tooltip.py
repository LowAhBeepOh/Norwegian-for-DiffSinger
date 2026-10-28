"""Hover tooltips: a small tip box that appears after the pointer rests on a widget."""

from __future__ import annotations

import tkinter as tk
from typing import Any

HOVER_DELAY_MS = 850  # the tip appears after roughly 0.85 s of hovering

_BG = "#2b2b2b"
_FG = "#f2f2f2"


class _Tip:
    def __init__(self, widget: Any, text: str, delay_ms: int) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event: object = None) -> None:
        self._cancel_pending()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        if self._window is not None:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6

        window = tk.Toplevel(self.widget)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        tk.Label(
            window,
            text=self.text,
            justify="left",
            wraplength=340,
            background=_BG,
            foreground=_FG,
            padx=10,
            pady=6,
        ).pack()
        window.geometry(f"+{x}+{y}")
        window.deiconify()
        self._window = window

    def _hide(self, _event: object = None) -> None:
        self._cancel_pending()
        if self._window is not None:
            self._window.destroy()
            self._window = None


def add_tip(widget: Any, text: str, delay_ms: int = HOVER_DELAY_MS) -> None:
    """Attach a tooltip to ``widget``. Works with CustomTkinter and plain tkinter widgets."""
    _Tip(widget, text, delay_ms)
