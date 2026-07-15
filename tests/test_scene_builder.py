from pathlib import Path
from unittest import TestCase

from obs_quickstart.scene_builder import SCENE_CONFIG, _get_source_kind_for_platform


class SceneBuilderTests(TestCase):
    def test_macos_source_kinds(self):
        self.assertEqual(
            _get_source_kind_for_platform("video_capture", True, False),
            "av_capture_input",
        )
        self.assertEqual(
            _get_source_kind_for_platform("game_capture", True, False),
            "window_capture",
        )

    def test_animated_scenes_reference_packaged_mp4_files(self):
        asset_dir = Path(__file__).parents[1] / "obs_quickstart" / "assets"
        animated = [
            source
            for scene in SCENE_CONFIG
            for source in scene["sources"]
            if source["kind"] == "ffmpeg_source"
        ]

        self.assertEqual(len(animated), 3)
        for source in animated:
            self.assertTrue(source["settings"]["looping"])
            self.assertTrue((asset_dir / source["asset_file"]).is_file())

