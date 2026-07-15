from __future__ import annotations

"""
obs-quickstart — Main CLI wizard.

Interactive wizard that:
1. Detects hardware
2. Tests connection speed
3. Configures OBS optimally
4. Creates complete scene collection
5. Sets up transitions and audio
"""

import argparse
import getpass
import logging
import sys
import time
from typing import Optional

try:
    import obsws_python as obs_api
    HAS_OBS_WS = True
except ImportError:
    HAS_OBS_WS = False

from .hardware import (
    detect_platform, detect_obs_encoders, detect_obs_devices,
    suggest_optimal_settings, test_connection, HardwareInfo
)
from .configurator import (
    configure_obs_settings, configure_stream, configure_hotkeys
)
from .scene_builder import (
    create_scene_collection, setup_transitions, configure_audio_devices
)

logger = logging.getLogger("obs-quickstart")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


# ─── ANSI colors ───────────────────────────────────────────────
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def cprint(text: str, color: str = "", bold: bool = False):
    """Print with color."""
    prefix = color
    if bold:
        prefix += Colors.BOLD
    suffix = Colors.RESET if color or bold else ""
    print(f"{prefix}{text}{suffix}")


def line():
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")


def prompt(question: str, default: str = "",
           choices: list[str] | None = None) -> str:
    """Ask user for input with optional choices."""
    if choices:
        choices_str = "/".join(choices)
        prompt_str = f"{Colors.CYAN}❓ {question} [{choices_str}]"
        if default:
            prompt_str += f" (default: {default})"
        prompt_str += f": {Colors.RESET}"
    else:
        prompt_str = f"{Colors.CYAN}❓ {question}"
        if default:
            prompt_str += f" (default: {default})"
        prompt_str += f": {Colors.RESET}"

    while True:
        answer = input(prompt_str).strip()
        if not answer and default:
            return default
        if not answer:
            continue
        if choices and answer.lower() not in choices:
            print(f"  {Colors.RED}Choose from: {', '.join(choices)}{Colors.RESET}")
            continue
        return answer.lower()


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Ask a yes/no question."""
    default_str = "Y/n" if default else "y/N"
    answer = prompt(question, default="y" if default else "n",
                    choices=["y", "n"])
    return answer == "y"


def banner():
    """Display the banner."""
    line()
    cprint(r"""
   ___  _     ___        _   _            _   _
  / _ \| |__ / _ \ _   _| |_| |_ __ _ ___| |_| |_
 | | | | '_ \ | | | | | | __| __/ _` / __| __| __|
 | |_| | |_) | |_| | |_| | |_| || (_| \__ \ |_| |_
  \___/|_.__/ \___/ \__,_|\__|\__\__,_|___/\__|\__|
  """, Colors.CYAN, bold=True)
    cprint("  Plug-and-Play OBS Studio Auto-Configurator", Colors.DIM)
    cprint(f"  v1.0.0 | Python {sys.version.split()[0]}\n", Colors.DIM)
    line()


def check_obs_connection(host: str = "localhost",
                         port: int = 4455,
                         password: str = "") -> Optional[obs_api.ReqClient]:
    """Check if OBS is running and WebSocket is accessible.

    Returns:
        ReqClient instance if connected, None otherwise.
    """
    if not HAS_OBS_WS:
        cprint("  ✗ obsws-python not installed. Run: pip install obsws-python", Colors.RED)
        return None

    try:
        cprint(f"  🔌 Connecting to OBS at {host}:{port}...", Colors.DIM)
        obs = obs_api.ReqClient(host=host, port=port, password=password)
        # Test connection
        version = obs.get_version()
        cprint(f"  ✅ Connected! OBS v{version.obs_version}", Colors.GREEN)
        return obs
    except Exception as e:
        cprint(f"  ✗ Cannot connect to OBS: {e}", Colors.RED)
        cprint("  ℹ️  Make sure OBS Studio is running and WebSocket is enabled:", Colors.YELLOW)
        cprint("     Tools → WebSocket Server Settings → Enable WebSocket server", Colors.DIM)
        return None


def show_hardware_report(info: HardwareInfo):
    """Display detected hardware information."""
    cprint("\n  💻 Hardware Report:", Colors.BOLD)
    print(f"    CPU:    {info.cpu_cores} cores / {info.cpu_logical} logical")
    if info.ram_gb:
        print(f"    RAM:    {info.ram_gb:.1f} GB")
    print(f"    GPU:    {info.gpu_vendor.title()}")
    print(f"    OS:     {'Windows' if info.is_windows else 'macOS' if info.is_macos else 'Linux'}")
    if info.is_apple_silicon:
        print(f"    Chip:   Apple Silicon")

    if info.has_nvenc:
        print(f"    🎬  Encoder: NVIDIA NVENC ✓")
    elif info.has_amf:
        print(f"    🎬  Encoder: AMD AMF ✓")
    elif info.has_qsv:
        print(f"    🎬  Encoder: Intel QuickSync ✓")
    elif info.has_apple_vt:
        print(f"    🎬  Encoder: Apple VideoToolbox ✓")
    else:
        print(f"    🎬  Encoder: x264 (CPU)")


def show_settings_report(settings: dict):
    """Display suggested settings."""
    cprint("\n  ⚙️  Suggested Settings:", Colors.BOLD)
    base_w, base_h = settings["base_resolution"]
    out_w, out_h = settings["output_resolution"]
    print(f"    Canvas:     {base_w}×{base_h}")
    print(f"    Output:     {out_w}×{out_h}")
    print(f"    FPS:        {settings['fps']}")
    print(f"    Encoder:    {settings['encoder']}")
    print(f"    Bitrate:    {settings['bitrate']} kbps")
    print(f"    Audio:      {settings['audio_bitrate']} kbps @ {settings['sample_rate']} Hz")
    print(f"    Keyframe:   {settings['keyframe_interval']}s")
    print(f"    Recording:  {settings['recording_quality']} quality")


def wizard(host: str = "localhost",
           port: int = 4455,
           password: str = "",
           settings_only: bool = False,
           scenes_only: bool = False,
           no_interactive: bool = False):
    """Main setup wizard."""
    banner()

    # ─── Step 1: Connect to OBS ──────────────────────────────
    obs = check_obs_connection(host, port, password)
    if obs is None and not password and not no_interactive:
        password = getpass.getpass(
            f"{Colors.CYAN}❓ OBS WebSocket password (leave blank to cancel): {Colors.RESET}"
        ).strip()
        if password:
            obs = check_obs_connection(host, port, password)
    if obs is None:
        cprint("\n  ❌ Cannot continue without OBS connection.", Colors.RED)
        cprint("  Start OBS Studio, enable WebSocket (Tools → WebSocket Server Settings),", Colors.YELLOW)
        cprint("  then run this tool again.", Colors.YELLOW)
        return

    # ─── Step 2: Hardware detection ──────────────────────────
    cprint("\n  🔍 Detecting hardware...", Colors.DIM)
    platform_info = detect_platform()
    try:
        hw_info = detect_obs_encoders(obs)
    except Exception as e:
        cprint(f"  ⚠️  Encoder detection failed: {e}", Colors.YELLOW)
        hw_info = platform_info

    # Merge platform info into hw_info
    hw_info.cpu_cores = hw_info.cpu_cores or platform_info.cpu_cores
    hw_info.cpu_logical = hw_info.cpu_logical or platform_info.cpu_logical
    hw_info.ram_gb = hw_info.ram_gb or platform_info.ram_gb
    hw_info.is_windows = platform_info.is_windows
    hw_info.is_macos = platform_info.is_macos
    hw_info.is_linux = platform_info.is_linux
    hw_info.is_apple_silicon = platform_info.is_apple_silicon

    show_hardware_report(hw_info)

    # ─── Step 3: Connection test ─────────────────────────────
    cprint("\n  🌐 Testing internet connection...", Colors.DIM)
    upload_mbps = test_connection(timeout=15)
    if upload_mbps > 0:
        print(f"    Upload: {upload_mbps} Mbps")
    else:
        print(f"    Upload: unknown (speedtest-cli not installed)")
        print(f"    {Colors.DIM}  Install: pip install speedtest-cli{Colors.RESET}")

    # ─── Step 4: Interactive questions ───────────────────────
    if no_interactive:
        use_case = "streaming"
        platform = "twitch"
        stream_key = ""
        have_camera = False
    else:
        line()
        cprint("\n  📋 Setup Wizard", Colors.BOLD)

        # Use case
        use_case = prompt(
            "What do you want to do?",
            default="streaming",
            choices=["streaming", "recording", "both"]
        )

        # Platform selection
        if use_case in ("streaming", "both"):
            platform = prompt(
                "Streaming platform?",
                default="twitch",
                choices=["twitch", "youtube", "kick", "custom"]
            )
            if platform == "custom":
                stream_key = getpass.getpass(f"{Colors.CYAN}❓ Stream key / URL: {Colors.RESET}")
            else:
                stream_key = getpass.getpass(
                    f"{Colors.CYAN}❓ Stream key (leave blank to set later): {Colors.RESET}"
                ).strip()
        else:
            platform = ""
            stream_key = ""

        # Camera
        have_camera = prompt_yes_no("Do you have a webcam/camera?", default=True)

    # ─── Step 5: Calculate optimal settings ──────────────────
    cprint("\n  🧮 Calculating optimal settings...", Colors.DIM)
    settings = suggest_optimal_settings(hw_info, platform, upload_mbps)

    # Adjust for non-streaming
    if use_case == "recording":
        settings["bitrate"] = min(settings["bitrate"] * 2, 50000)
        settings["recording_quality"] = "High"

    show_settings_report(settings)

    # ─── Step 6: Confirm and apply ───────────────────────────
    if not no_interactive:
        line()
        if not prompt_yes_no("\nApply these settings to OBS?", default=True):
            cprint("  ✗ Cancelled by user.", Colors.YELLOW)
            return

    # ─── Step 7: Apply settings ──────────────────────────────
    cprint("\n  ⚙️  Applying settings to OBS...", Colors.BOLD)

    if not scenes_only:
        cprint("  Configuring OBS settings...", Colors.DIM)
        if configure_obs_settings(obs, settings):
            cprint("  ✅ OBS settings configured!", Colors.GREEN)
        else:
            cprint("  ⚠️  Some settings could not be applied.", Colors.YELLOW)

    if use_case in ("streaming", "both") and stream_key and not scenes_only:
        cprint("  Configuring stream...", Colors.DIM)
        if configure_stream(obs, platform, stream_key):
            cprint("  ✅ Stream configured!", Colors.GREEN)
        else:
            cprint("  ⚠️  Stream could not be configured.", Colors.YELLOW)

    if not scenes_only:
        cprint("  Configuring hotkeys...", Colors.DIM)
        configure_hotkeys(obs)

    # ─── Step 8: Create scenes ───────────────────────────────
    if not settings_only:
        line()
        cprint("\n  🎬 Creating scene collection...", Colors.BOLD)

        # Detect devices
        devices = detect_obs_devices(obs) if not no_interactive else None
        video_devices = devices.video_devices if devices else []
        if have_camera and not video_devices:
            video_devices = ["Camera"]

        # Configure audio devices first
        configure_audio_devices(obs)

        # Create scenes
        create_scene_collection(
            obs, settings,
            scene_collection_name="obs-quickstart",
            video_devices=video_devices,
        )

        # Set up transitions
        cprint("  Setting up transitions...", Colors.DIM)
        setup_transitions(obs)

        cprint("  ✅ Scene collection created!", Colors.GREEN)

    # ─── Step 9: Done ────────────────────────────────────────
    line()
    cprint("\n  🎉  obs-quickstart setup complete!", Colors.GREEN, bold=True)
    cprint("\n  📋 What was done:", Colors.BOLD)
    if settings_only:
        print("     ✅ Settings applied (no scenes created)")
    elif scenes_only:
        print("     ✅ 5 scenes created (settings unchanged)")
        print("     ✅ Transitions and audio sources configured")
    else:
        print("     ✅ Optimal settings applied (video, audio, output)")
        if use_case in ("streaming", "both") and stream_key:
            print("     ✅ Stream configured")
        print("     ✅ Hotkeys configured (F1-F7)")
        print("     ✅ 5 scenes created: Starting Soon, Gameplay, Just Chatting, BRB, Ending")
        print("     ✅ Transitions set (Fade)")
        print("     ✅ Audio sources configured")
    cprint("\n  📝 Next steps:", Colors.BOLD)
    print("     1. In OBS, go to each scene and verify sources")
    print("     2. If you have a camera, select the correct device")
    print("     3. Do a test recording/stream")
    print("     4. Use F1 to start streaming, F3 to start recording")
    print(f"     {Colors.DIM}    (or use the OBS Start Streaming button){Colors.RESET}")
    print()


def cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="obs-quickstart — Plug-and-Play OBS Studio auto-configurator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  obs-quickstart                          # Interactive wizard
  obs-quickstart --settings-only          # Only configure settings, no scenes
  obs-quickstart --scenes-only            # Only create scenes, no settings
  obs-quickstart --no-interactive         # No prompts, use defaults
  obs-quickstart --host 192.168.1.5 --port 4455 --password secret
        """,
    )
    parser.add_argument("--host", default="localhost",
                        help="OBS WebSocket host (default: localhost)")
    parser.add_argument("--port", type=int, default=4455,
                        help="OBS WebSocket port (default: 4455)")
    parser.add_argument("--password", default="",
                        help="OBS WebSocket password")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--settings-only", action="store_true",
                      help="Only apply settings, skip scene creation")
    mode.add_argument("--scenes-only", action="store_true",
                      help="Only create scenes, skip settings")
    parser.add_argument("--no-interactive", action="store_true",
                        help="Run without prompts (use defaults)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        wizard(
            host=args.host,
            port=args.port,
            password=args.password,
            settings_only=args.settings_only,
            scenes_only=args.scenes_only,
            no_interactive=args.no_interactive,
        )
    except KeyboardInterrupt:
        cprint("\n\n  ✗ Setup cancelled.", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        cprint(f"\n  ❌ Error: {e}", Colors.RED)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()
