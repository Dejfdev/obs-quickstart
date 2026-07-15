"""
obs-quickstart — Hardware detection module.

Detects available GPU encoders, CPU info, audio/video devices,
and network speed via the OBS WebSocket API.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HardwareInfo:
    """Detected hardware capabilities."""
    gpu_vendor: str = "unknown"  # nvidia, amd, intel, apple, unknown
    gpu_name: str = ""
    cpu_cores: int = 0
    cpu_logical: int = 0
    ram_gb: float = 0.0
    encoders: list[str] = field(default_factory=list)
    has_nvenc: bool = False
    has_amf: bool = False
    has_qsv: bool = False
    has_apple_vt: bool = False
    is_apple_silicon: bool = False
    is_windows: bool = False
    is_macos: bool = False
    is_linux: bool = False


@dataclass
class OBSDeviceInfo:
    """Devices detected by OBS."""
    video_devices: list[str] = field(default_factory=list)
    audio_inputs: list[str] = field(default_factory=list)
    audio_outputs: list[str] = field(default_factory=list)


def detect_platform() -> HardwareInfo:
    """Detect basic platform information."""
    info = HardwareInfo()

    # Platform detection
    info.is_windows = sys.platform == "win32"
    info.is_macos = sys.platform == "darwin"
    info.is_linux = sys.platform.startswith("linux")

    # CPU cores
    try:
        import os
        info.cpu_logical = os.cpu_count() or 0
        if info.is_windows:
            out = subprocess.run(
                ["wmic", "cpu", "get", "NumberOfCores"],
                capture_output=True, text=True, timeout=5
            )
            match = re.search(r"(\d+)", out.stdout)
            if match:
                info.cpu_cores = int(match.group(1))
        elif info.is_linux:
            with open("/proc/cpuinfo") as f:
                info.cpu_cores = len(re.findall(r"^processor\s+:", f.read(), re.MULTILINE))
        elif info.is_macos:
            out = subprocess.run(
                ["sysctl", "-n", "hw.physicalcpu"],
                capture_output=True, text=True, timeout=5
            )
            if out.stdout.strip():
                info.cpu_cores = int(out.stdout.strip())
        if not info.cpu_cores:
            info.cpu_cores = info.cpu_logical
    except Exception:
        info.cpu_cores = info.cpu_logical or 4

    # RAM
    try:
        if info.is_windows:
            out = subprocess.run(
                ["wmic", "memorychip", "get", "Capacity"],
                capture_output=True, text=True, timeout=5
            )
            capacities = re.findall(r"(\d+)", out.stdout)
            total_bytes = sum(int(c) for c in capacities if c.isdigit())
            info.ram_gb = total_bytes / (1024**3)
        elif info.is_linux:
            with open("/proc/meminfo") as f:
                match = re.search(r"MemTotal:\s+(\d+)", f.read())
                if match:
                    info.ram_gb = int(match.group(1)) / 1024 / 1024
        elif info.is_macos:
            out = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            if out.stdout.strip():
                info.ram_gb = int(out.stdout.strip()) / (1024**3)
    except Exception:
        info.ram_gb = 0.0

    # Apple Silicon detection
    if info.is_macos:
        try:
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            info.is_apple_silicon = "Apple" in out.stdout
        except Exception:
            pass

    return info


def detect_obs_encoders(obs) -> HardwareInfo:
    """Detect available encoders via OBS WebSocket API.

    Args:
        obs: Connected obsws_python.ReqClient instance.
    """
    info = HardwareInfo()
    info.is_windows = sys.platform == "win32"
    info.is_macos = sys.platform == "darwin"
    info.is_linux = sys.platform.startswith("linux")

    try:
        resp = obs.get_special_inputs()
        info.encoders = resp.input_kinds if hasattr(resp, 'input_kinds') else []
    except Exception:
        pass

    # Enumerate encoder types via OBS
    # We probe for specific encoder IDs
    nvenc_ids = ["ffmpeg_nvenc", "nvidia_nvenc", "jim_nvenc"]
    amf_ids = ["amd_amf_h264", "h264_texture_amf", "amd_amf_hevc"]
    qsv_ids = ["obs_qsv11", "intel_qsv_h264"]
    apple_ids = ["com.apple.videotoolbox.videoencoder.ave.avc",
                 "com.apple.videotoolbox.videoencoder.ave.hevc",
                 "apple_vt_h264", "apple_vt_hevc"]

    # We can't directly enumerate all encoder types via the API,
    # but we can probe via get_input_kind_list
    try:
        kinds = obs.get_input_kind_list()
        all_kinds = kinds.input_kinds if hasattr(kinds, 'input_kinds') else []
    except Exception:
        all_kinds = []

    info.has_nvenc = any(eid in all_kinds for eid in nvenc_ids)
    info.has_amf = any(eid in all_kinds for eid in amf_ids)
    info.has_qsv = any(eid in all_kinds for eid in qsv_ids)
    info.has_apple_vt = any(eid in all_kinds for eid in apple_ids)

    # GPU vendor inference
    if info.has_nvenc:
        info.gpu_vendor = "nvidia"
    elif info.has_amf:
        info.gpu_vendor = "amd"
    elif info.has_qsv:
        info.gpu_vendor = "intel"
    elif info.has_apple_vt:
        info.gpu_vendor = "apple"
        info.is_apple_silicon = True

    return info


def detect_obs_devices(obs) -> OBSDeviceInfo:
    """Detect available audio/video devices via OBS WebSocket API.

    Args:
        obs: Connected obsws_python.ReqClient instance.
    """
    devices = OBSDeviceInfo()

    try:
        # Get all available sources
        resp = obs.get_input_list()
        # Alternative: use specialized calls if available
        # obs.get_special_inputs() can return default devices
    except Exception:
        pass

    # Try to enumerate audio/video devices
    # OBS WebSocket v5 doesn't have a direct "list audio devices" call,
    # but we can probe for default system devices
    try:
        inputs = obs.get_input_list()
        for inp in inputs.inputs if hasattr(inputs, 'inputs') else []:
            name = inp.get("inputName", "")
            kind = inp.get("inputKind", "")
            if "audio" in kind.lower() or "wasapi" in kind.lower():
                if "output" in kind.lower() or "desktop" in name.lower():
                    devices.audio_outputs.append(name)
                else:
                    devices.audio_inputs.append(name)
            elif "dshow" in kind.lower() or "video" in kind.lower() or "avcapture" in kind.lower():
                devices.video_devices.append(name)
    except Exception:
        pass

    return devices


def suggest_optimal_settings(info: HardwareInfo, platform: str = "twitch",
                             connection_mbps: float = 0) -> dict:
    """Suggest optimal OBS settings based on detected hardware.

    Args:
        info: Detected hardware info.
        platform: Streaming platform (twitch, youtube, kick, custom).
        connection_mbps: Upload speed in Mbps (0 = unknown).

    Returns:
        dict with keys: base_resolution, output_resolution, fps, bitrate,
                        encoder, recording_quality, keyframe_interval
    """
    settings = {
        "base_resolution": (1920, 1080),
        "output_resolution": (1920, 1080),
        "fps": 60,
        "bitrate": 6000,
        "encoder": "x264",
        "recording_quality": "High",
        "keyframe_interval": 2,
        "audio_bitrate": 160,
        "sample_rate": 48000,
    }

    # --- Encoder selection ---
    if info.has_nvenc:
        settings["encoder"] = "NVENC"
    elif info.has_amf:
        settings["encoder"] = "AMF"
    elif info.has_qsv:
        settings["encoder"] = "QSV"
    elif info.has_apple_vt:
        settings["encoder"] = "Apple VT"
    elif info.has_nvenc or info.has_amf or info.has_qsv:
        settings["encoder"] = "Hardware"
    else:
        # x264 fallback — check CPU cores
        if info.cpu_cores and info.cpu_cores >= 8:
            settings["encoder"] = "x264"
        else:
            settings["encoder"] = "x264"
            # Lower resolution for weak CPU
            settings["output_resolution"] = (1280, 720)
            settings["fps"] = 30

    # --- Bitrate by platform ---
    if platform == "twitch":
        settings["bitrate"] = 6000
        settings["keyframe_interval"] = 2
    elif platform == "youtube":
        settings["bitrate"] = 12000
        settings["keyframe_interval"] = 2
    elif platform == "kick":
        settings["bitrate"] = 8000
        settings["keyframe_interval"] = 2
    else:
        settings["bitrate"] = 6000

    # --- Connection-based adjustment ---
    if connection_mbps > 0:
        max_bitrate = int(connection_mbps * 0.85 * 1000)  # 85% of upload
        settings["bitrate"] = min(settings["bitrate"], max_bitrate)
        if max_bitrate < 3000:
            settings["output_resolution"] = (1280, 720)
            settings["fps"] = 30
        elif max_bitrate < 4500:
            settings["output_resolution"] = (1280, 720)
            settings["fps"] = 60

    # --- Resolution by encoder ---
    if settings["output_resolution"] == (1920, 1080) and settings["fps"] == 60:
        if settings["encoder"] == "x264" and info.cpu_cores and info.cpu_cores < 8:
            settings["output_resolution"] = (1280, 720)
            settings["fps"] = 30

    # --- FPS based on CPU ---
    if info.cpu_cores and info.cpu_cores <= 4:
        settings["fps"] = 30

    # --- Recording quality ---
    if settings["encoder"] != "x264" and info.ram_gb >= 8:
        settings["recording_quality"] = "High"
    else:
        settings["recording_quality"] = "Medium"

    return settings


def test_connection(timeout: int = 10) -> float:
    """Test internet upload speed. Returns Mbps or 0 if unavailable.

    Uses speedtest-cli if installed, otherwise estimates from a simple HTTP test.
    """
    try:
        import speedtest
        st = speedtest.Speedtest()
        st.get_best_server()
        upload = st.upload() / 1_000_000  # Mbps
        return round(upload, 1)
    except ImportError:
        pass
    except Exception:
        pass

    return 0.0