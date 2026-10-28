import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gui import appearance, settings
from gui.logic import transcribe


class FontOrderTests(unittest.TestCase):
    def test_prefers_inter_tight_first(self):
        installed = ["Arial", "Inter", "Inter Tight", "Roboto"]
        self.assertEqual(appearance.pick_font(installed, "Segoe UI"), "Inter Tight")

    def test_falls_back_to_inter_then_current_then_arial(self):
        self.assertEqual(appearance.pick_font(["Inter", "Arial"], "Segoe UI"), "Inter")
        self.assertEqual(appearance.pick_font(["Roboto", "Arial"], "Segoe UI"), "Roboto")
        self.assertEqual(appearance.pick_font(["Arial"], "Segoe UI"), "Arial")

    def test_uses_system_font_when_none_installed(self):
        self.assertEqual(appearance.pick_font(["Times New Roman"], "Segoe UI"), "Segoe UI")

    def test_font_match_ignores_case(self):
        self.assertEqual(appearance.pick_font(["inter tight"], "Segoe UI"), "Inter Tight")


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = mock.patch.object(
            settings, "SETTINGS_FILE", Path(self._tmp.name) / "settings.json"
        )
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_missing_file_gives_defaults(self):
        self.assertEqual(settings.load(), settings.Settings())

    def test_round_trip(self):
        saved = settings.Settings(light_mode=True, high_contrast=True, force_cpu=True)
        settings.save(saved)
        self.assertEqual(settings.load(), saved)

    def test_bad_values_fall_back_to_defaults(self):
        settings.SETTINGS_FILE.write_text(
            json.dumps({"light_mode": "yes", "high_contrast": 1, "force_cpu": None}),
            encoding="utf-8",
        )
        loaded = settings.load()
        self.assertIsNone(loaded.light_mode)
        self.assertTrue(loaded.high_contrast)
        self.assertFalse(loaded.force_cpu)

    def test_corrupt_file_gives_defaults(self):
        settings.SETTINGS_FILE.write_text("{not json", encoding="utf-8")
        self.assertEqual(settings.load(), settings.Settings())


class ForceCpuTests(unittest.TestCase):
    def test_force_cpu_passes_through_to_pipeline_factory(self):
        seen = {}

        class FakeAsr:
            def __call__(self, *args, **kwargs):
                return {"text": "hei"}

        def factory(path, force_cpu=False):
            seen["force_cpu"] = force_cpu
            return FakeAsr()

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "a.wav").write_bytes(b"")
            with mock.patch.object(transcribe, "is_installed", return_value=True), \
                 mock.patch.object(transcribe, "_load_audio", return_value=[0.0]):
                transcribe.transcribe_folder(
                    folder, "NbAiLab/nb-whisper-small", lambda _: None,
                    force_cpu=True, pipeline_factory=factory,
                )
        self.assertTrue(seen["force_cpu"])

    def test_default_model_is_nb_whisper_small(self):
        from gui.tabs import transcribe as tab

        self.assertEqual(tab.DEFAULT_FAMILY, "NB-Whisper")
        self.assertEqual(tab.DEFAULT_SIZE, "small")
        self.assertEqual(transcribe.repo_id(tab.DEFAULT_FAMILY, tab.DEFAULT_SIZE),
                         "NbAiLab/nb-whisper-small")


if __name__ == "__main__":
    unittest.main()
