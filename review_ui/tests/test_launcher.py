import unittest
from unittest import mock

from review_ui.launcher import (
    _draft_running_detail,
    _final_video_preview_html,
    _operation_status_html,
    build_launcher,
)
from review_ui.launcher_backend import launch_review_server
from review_ui.theme import APP_THEME_CSS, THEME_JS, THEME_SWITCHER_HTML


class TestLauncherPresentation(unittest.TestCase):
    def test_operation_status_escapes_dynamic_text(self):
        rendered = _operation_status_html("error", "Lỗi", "<script>alert(1)</script>")
        self.assertIn("state-error", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_draft_status_maps_kaggle_phases(self):
        self.assertIn("phân tích", _draft_running_detail("KernelWorkerStatus.RUNNING"))
        self.assertIn("tải", _draft_running_detail("kaggle kernels output"))

    def test_theme_switch_does_not_reload_page(self):
        self.assertIn("data-theme-choice", THEME_JS)
        self.assertNotIn("location.reload", THEME_JS)
        self.assertIn('html[data-app-theme="light"]', APP_THEME_CSS)
        self.assertNotIn("prefers-color-scheme: dark", APP_THEME_CSS)
        self.assertNotIn('data-theme-choice="system"', THEME_SWITCHER_HTML)
        self.assertIn('let savedTheme = "dark"', THEME_JS)

    def test_language_switch_is_bilingual_and_does_not_reload(self):
        self.assertIn('data-language-choice="vi"', THEME_SWITCHER_HTML)
        self.assertIn('data-language-choice="en"', THEME_SWITCHER_HTML)
        self.assertIn("applyLanguage", THEME_JS)
        self.assertNotIn("location.reload", THEME_JS)

    def test_final_video_preview_uses_browser_video_controls(self):
        with mock.patch("review_ui.launcher.FINAL_VIDEO") as final_video:
            final_video.is_file.return_value = True
            html = _final_video_preview_html(r"D:\project\data\final\final_video.mp4")

        self.assertIn("<video controls", html)
        self.assertIn("/gradio_api/file=D:/project/data/final/final_video.mp4", html)

    def test_launcher_does_not_restore_video_from_previous_session(self):
        with mock.patch("review_ui.launcher.FINAL_VIDEO") as final_video:
            final_video.is_file.return_value = True
            config = build_launcher().get_config_file()

        final_players = [
            component
            for component in config["components"]
            if component.get("type") == "html"
            and "final-video-empty" in str(component.get("props", {}).get("value", ""))
        ]
        self.assertEqual(len(final_players), 1)
        self.assertNotIn("<video controls", final_players[0]["props"]["value"])

    def test_launch_review_waits_until_server_is_ready(self):
        fake_process = mock.Mock()
        fake_process.poll.return_value = None
        with mock.patch("review_ui.launcher_backend.draft_status", return_value=(True, "ready")):
            with mock.patch("review_ui.launcher_backend._review_process", None):
                with mock.patch("review_ui.launcher_backend._wait_for_review_server", side_effect=[False, True]):
                    with mock.patch("review_ui.launcher_backend.subprocess.Popen", return_value=fake_process):
                        result = launch_review_server(port=7870)

        self.assertIn("Đã khởi động", result)
        self.assertIn("http://127.0.0.1:7870", result)


if __name__ == "__main__":
    unittest.main()
