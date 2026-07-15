"""
obs-quickstart — OBS configurator module.

Configures OBS video, audio, output, and stream settings
via the WebSocket API.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("obs-quickstart")


def configure_obs_settings(obs, settings: dict) -> bool:
    """Apply optimal settings to OBS via WebSocket API.

    Args:
        obs: Connected obsws_python.ReqClient instance.
        settings: Settings dict from hardware.suggest_optimal_settings().

    Returns:
        True if all settings applied successfully.
    """
    success = True

    # --- Video settings ---
    base_w, base_h = settings.get("base_resolution", (1920, 1080))
    out_w, out_h = settings.get("output_resolution", (1920, 1080))
    fps = settings.get("fps", 60)
    fps_num, fps_den = fps, 1

    try:
        obs.set_video_settings(
            fps_numerator=fps_num,
            fps_denominator=fps_den,
            base_width=base_w,
            base_height=base_h,
            output_width=out_w,
            output_height=out_h,
        )
        logger.info(f"Video: {base_w}x{base_h} → {out_w}x{out_h} @ {fps}fps")
    except Exception as e:
        logger.warning(f"Failed to set video settings: {e}")
        success = False

    # --- Audio settings ---
    sample_rate = settings.get("sample_rate", 48000)
    channels = "Stereo"
    try:
        # Set audio sample rate via profile
        import obsws_python as obs_api
        obs.set_profile_parameter("Audio", "SampleRate", str(sample_rate))
        obs.set_profile_parameter("Audio", "Channels", "2")  # Stereo
        obs.set_profile_parameter("Audio", "ChannelSetup", "Stereo")
        logger.info(f"Audio: {sample_rate} Hz, {channels}")
    except Exception as e:
        logger.warning(f"Failed to set audio settings: {e}")

    # --- Output settings (Simple mode) ---
    encoder = settings.get("encoder", "x264")
    bitrate = settings.get("bitrate", 6000)
    audio_bitrate = settings.get("audio_bitrate", 160)

    try:
        # Set output mode to Simple
        obs.set_profile_parameter("Output", "Mode", "Simple")

        # Map encoder name to OBS profile parameter
        encoder_map = {
            "NVENC": "nvenc",
            "AMF": "amd",
            "QSV": "qsv",
            "Apple VT": "apple_vt",
            "x264": "x264",
            "Hardware": "hardware",
        }
        encoder_key = encoder_map.get(encoder, "x264")

        # Set streaming encoder
        obs.set_profile_parameter("SimpleOutput", "StreamEncoder", encoder_key)
        obs.set_profile_parameter("SimpleOutput", "VBitrate", str(bitrate))
        obs.set_profile_parameter("SimpleOutput", "ABitrate", str(audio_bitrate))

        # Set recording encoder
        rec_quality = settings.get("recording_quality", "High")
        rec_quality_map = {"High": "Small", "Medium": "Stream", "Low": "Stream"}
        rec_quality_val = rec_quality_map.get(rec_quality, "Small")
        obs.set_profile_parameter("SimpleOutput", "RecQuality", rec_quality_val)

        # Set recording encoder to same as streaming or optimized
        rec_encoder = settings.get("recording_encoder", encoder_key)
        obs.set_profile_parameter("SimpleOutput", "RecEncoder", rec_encoder)

        logger.info(f"Output: encoder={encoder}, bitrate={bitrate}kbps, audio={audio_bitrate}kbps")
    except Exception as e:
        logger.warning(f"Failed to set output settings: {e}")
        success = False

    # --- Advanced output settings ---
    try:
        # Keyframe interval
        keyint = settings.get("keyframe_interval", 2)
        obs.set_profile_parameter("Video", "KeyintSec", str(keyint))

        # Color settings
        obs.set_profile_parameter("Video", "ColorFormat", "NV12")
        obs.set_profile_parameter("Video", "ColorSpace", "Rec. 709")
        obs.set_profile_parameter("Video", "ColorRange", "Partial")
    except Exception as e:
        logger.warning(f"Failed to set advanced video settings: {e}")

    # --- Recording format ---
    try:
        # Set recording format to MKV (safer than MP4)
        obs.set_profile_parameter("Output", "RecFormat", "mkv")
        obs.set_profile_parameter("Output", "FilenameFormatting",
                                  "%CCYY-%MM-%DD %hh-%mm-%ss")
    except Exception as e:
        logger.warning(f"Failed to set recording format: {e}")

    return success


def configure_stream(obs, platform: str, stream_key: str,
                     server: str = "") -> bool:
    """Configure stream settings for the selected platform.

    Args:
        obs: Connected obsws_python.ReqClient instance.
        platform: twitch, youtube, kick, or custom.
        stream_key: Stream key / ingest token.
        server: Optional custom RTMP server URL.

    Returns:
        True if successful.
    """
    try:
        # Determine service type and server
        if platform == "twitch":
            service_name = "Twitch"
            service_type = "rtmp_common"
        elif platform == "youtube":
            service_name = "YouTube - RTMPS"
            service_type = "rtmp_common"
        elif platform == "kick":
            service_name = "Kick"
            service_type = "rtmp_common"
        else:
            service_name = "Custom"
            service_type = "rtmp_custom"

        # Create service settings
        import obsws_python as obs_api

        # Get current stream service
        try:
            current = obs.get_stream_service_settings()
            logger.info(f"Current stream service: {current}")
        except Exception:
            pass

        # Set stream key (available via OBS WebSocket v5+)
        # We use SetStreamServiceSettings or SetProfileParameter
        try:
            obs.set_stream_service_settings(
                type=service_type,
                settings={
                    "service": service_name,
                    "key": stream_key,
                    "server": server if server else "auto",
                }
            )
            logger.info(f"Stream configured: {service_name}")
        except Exception as e:
            logger.warning(f"Failed to set stream service: {e}")

    except Exception as e:
        logger.warning(f"Stream configuration failed: {e}")
        return False

    return True


def configure_hotkeys(obs) -> bool:
    """Configure basic hotkeys for streaming control.

    Args:
        obs: Connected obsws_python.ReqClient instance.

    Returns:
        True if successful.
    """
    try:
        # Set hotkeys via profile parameters
        # OBS uses a specific format: "OBSKey:Modifiers"
        hotkeys = {
            "StartStreaming": "OBS_KEY_F1",
            "StopStreaming": "OBS_KEY_F2",
            "StartRecording": "OBS_KEY_F3",
            "StopRecording": "OBS_KEY_F4",
            "StartReplayBuffer": "OBS_KEY_F5",
            "SaveReplayBuffer": "OBS_KEY_F6",
            "ToggleMute": "OBS_KEY_F7",
        }

        for action, key in hotkeys.items():
            try:
                obs.set_profile_parameter("Hotkeys", action, key)
            except Exception:
                pass

        # Scene switching hotkeys
        scene_hotkeys = {
            "SceneHotkey1": "OBS_KEY_1",
            "SceneHotkey2": "OBS_KEY_2",
            "SceneHotkey3": "OBS_KEY_3",
            "SceneHotkey4": "OBS_KEY_4",
            "SceneHotkey5": "OBS_KEY_5",
        }
        for action, key in scene_hotkeys.items():
            try:
                obs.set_profile_parameter("Hotkeys", action, key)
            except Exception:
                pass

        logger.info("Hotkeys configured")
    except Exception as e:
        logger.warning(f"Failed to set hotkeys: {e}")
        return False

    return True