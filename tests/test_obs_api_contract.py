from types import SimpleNamespace
from unittest import TestCase

from obs_quickstart.configurator import configure_obs_settings, configure_stream
from obs_quickstart.hardware import HardwareInfo, suggest_optimal_settings


class RecordingOBS:
    def __init__(self):
        self.video = None
        self.profile = []
        self.stream = None

    def set_video_settings(
        self, numerator, denominator, base_width, base_height, out_width, out_height
    ):
        self.video = (
            numerator,
            denominator,
            base_width,
            base_height,
            out_width,
            out_height,
        )

    def set_profile_parameter(self, category, name, value):
        self.profile.append((category, name, value))

    def get_stream_service_settings(self):
        return SimpleNamespace()

    def set_stream_service_settings(self, ss_type, ss_settings):
        self.stream = (ss_type, ss_settings)


class OBSAPIContractTests(TestCase):
    def test_configurator_uses_obsws_python_argument_names(self):
        obs = RecordingOBS()
        settings = suggest_optimal_settings(
            HardwareInfo(cpu_cores=10, ram_gb=16, has_apple_vt=True),
            platform="twitch",
            connection_mbps=20,
        )

        self.assertTrue(configure_obs_settings(obs, settings))
        self.assertEqual(obs.video, (60, 1, 1920, 1080, 1920, 1080))
        self.assertIn(("SimpleOutput", "StreamEncoder", "apple_vt"), obs.profile)

    def test_stream_configuration_does_not_report_false_success(self):
        obs = RecordingOBS()
        self.assertTrue(configure_stream(obs, "twitch", "secret"))
        self.assertEqual(obs.stream[0], "rtmp_common")
        self.assertEqual(obs.stream[1]["key"], "secret")

        obs.set_stream_service_settings = lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("rejected")
        )
        self.assertFalse(configure_stream(obs, "twitch", "secret"))

