"""About tab: program info, GUI sources and one-click installation of the tools."""

from __future__ import annotations

import sys

import customtkinter as ctk

from .. import GUI_VERSION, PHONEMIZER_VERSION
from ..logic import mfa, transcribe
from ..logic.process import run_streamed
from ..paths import REQUIREMENTS_FILE
from ..tooltip import add_tip

# Sources for the GUI and its tools only. The phonemizer and G2P sources are listed in CREDITS.md.
GUI_SOURCES: list[tuple[str, str]] = [
    (
        "NoFA (Norwegian forced-alignment model and lexicon)",
        "Språkbanken, National Library of Norway. Used by Auto Label. CC0.",
    ),
    (
        "Montreal Forced Aligner",
        "Montreal Corpus Tools. Aligns audio to text for Auto Label.",
    ),
    (
        "NB-Whisper",
        "NbAiLab, National Library of Norway. Norwegian speech recognition for Transcribe.",
    ),
    (
        "Whisper",
        "OpenAI. Speech recognition models used by Transcribe.",
    ),
    (
        "CustomTkinter",
        "Tom Schimansky. The GUI framework this program is built with.",
    ),
    (
        "Hugging Face",
        "Model hosting and the transformers library, used to download and run the Whisper models.",
    ),
]

# NB-Whisper Small is the model the one-click installer fetches.
DEFAULT_MODEL_REPO = transcribe.repo_id("NB-Whisper", "small")


class AboutTab(ctk.CTkFrame):
    def __init__(self, master: ctk.CTkBaseClass, app: ctk.CTk) -> None:
        super().__init__(master, fg_color="transparent")
        self.pack(fill="both", expand=True)
        self.app = app

        ctk.CTkLabel(
            self,
            text="Norwegian for DiffSinger",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(self, text="Created by LowAhBeepOh / LoaBeepo").pack(anchor="w", padx=10)
        ctk.CTkLabel(
            self,
            text=f"GUI version {GUI_VERSION} / phonemizer version {PHONEMIZER_VERSION}",
            text_color=("gray35", "gray70"),
        ).pack(anchor="w", padx=10, pady=(2, 10))

        ctk.CTkLabel(self, text="Sources for the GUI and the tools it uses:").pack(
            anchor="w", padx=10
        )
        sources = ctk.CTkScrollableFrame(self, height=200)
        sources.pack(fill="x", padx=10, pady=(4, 10))
        self._fill_sources(sources)

        thanks = ctk.CTkLabel(
            self,
            text=(
                "Also huge thanks to the National Library of Norway (Nasjonalbiblioteket) for "
                "making this project easier than I originally thought it would be. They've made "
                "a lot of the things here, like NB-Whisper, NoFAbet, and the word dictionary "
                "that the G2p was trained on. Love y'all <3"
            ),
            wraplength=820,
            justify="left",
            anchor="w",
        )
        thanks.pack(anchor="w", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            self,
            text="Not set up yet? This installs everything the GUI needs. Each step is skipped "
            "if it's already done.",
        ).pack(anchor="w", padx=10)
        install_all = ctk.CTkButton(
            self, text="Install everything for me", command=self._install_everything
        )
        install_all.pack(anchor="w", padx=10, pady=(8, 4))
        add_tip(
            install_all,
            "Installs the Python packages, Norwegian MFA with its dictionary, and NB-Whisper "
            "Small. It's a big download, so it can take a while. Steps that already exist are skipped.",
        )

    def _fill_sources(self, parent: ctk.CTkScrollableFrame) -> None:
        for title, description in GUI_SOURCES:
            card = ctk.CTkFrame(parent, corner_radius=10)
            card.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                justify="left",
                wraplength=640,
            ).pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(
                card,
                text=description,
                anchor="w",
                justify="left",
                wraplength=640,
                text_color=("gray35", "gray70"),
            ).pack(anchor="w", padx=12, pady=(2, 8))

    def _install_everything(self) -> None:
        def job(emit):
            def install_packages() -> None:
                run_streamed(
                    [sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE], emit
                )

            def install_mfa_and_dictionary() -> None:
                mfa.install_mfa(emit)
                mfa.install_nofa(emit)

            def install_whisper() -> None:
                transcribe.install_model(DEFAULT_MODEL_REPO, emit)

            steps = [
                ("Python packages", install_packages),
                ("Norwegian MFA and dictionary", install_mfa_and_dictionary),
                ("NB-Whisper Small", install_whisper),
            ]
            failed: list[str] = []
            for name, step in steps:
                emit(f"== {name} ==")
                try:
                    step()
                except Exception as exc:  # noqa: BLE001 - keep going so one failure doesn't stop the rest
                    emit(f"ERROR in {name}: {exc}")
                    failed.append(name)
            if failed:
                emit("Finished with errors in: " + ", ".join(failed))
            else:
                emit("Everything is installed.")

        self.app.run_task(job)
