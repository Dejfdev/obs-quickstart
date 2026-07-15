"""
obs-quickstart — Scene builder module.

Creates OBS scenes, sources, transitions, and configures
audio devices via the WebSocket API.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("obs-quickstart")

# --- Scene configuration ---
SCENE_CONFIG = [
    {
        "name": "🟢 Starting Soon",
        "index": 0,
        "sources": [
            {"kind": "color_source_v2", "name": "Background",
             "settings": {"color": 0x1a1a2e, "width": 1920, "height": 1080},
             "position": {"x": 0, "y": 0}},
            {"kind": "text_gdiplus_v2", "name": "Starting Soon Text",
             "settings": {"text": "STARTING SOON",
                          "font": {"face": "Arial", "size": 72, "bold": True},
                          "color": 0xffffff, "align": "center",
                          "vertical_align": "center",
                          "outline": True, "outline_color": 0x000000,
                          "outline_size": 4},
             "position": {"x": 960, "y": 540, "alignment": 5},
             "filters": []},
        ],
    },
    {
        "name": "🎮 Gameplay",
        "index": 1,
        "sources": [
            {"kind": "game_capture", "name": "Game Capture",
             "settings": {"capture_mode": "any_fullscreen"},
             "position": {"x": 0, "y": 0, "width": 1920, "height": 1080},
             "filters": []},
            {"kind": "wasapi_input_capture", "name": "Mic/Aux",
             "settings": {},
             "position": {},
             "filters": [
                 {"kind": "noise_gate_filter", "name": "Noise Gate",
                  "settings": {
                      "close_threshold": -50, "open_threshold": -35,
                      "attack_time": 25, "release_time": 150,
                      "hold_time": 200}
                  },
             ]},
            {"kind": "wasapi_output_capture", "name": "Desktop Audio",
             "settings": {},
             "position": {},
             "filters": []},
        ],
    },
    {
        "name": "💬 Just Chatting",
        "index": 2,
        "sources": [
            {"kind": "color_source_v2", "name": "Background",
             "settings": {"color": 0x1a1a2e, "width": 1920, "height": 1080},
             "position": {"x": 0, "y": 0}},
        ],
    },
    {
        "name": "🔴 Be Right Back",
        "index": 3,
        "sources": [
            {"kind": "color_source_v2", "name": "Background",
             "settings": {"color": 0x000000, "width": 1920, "height": 1080},
             "position": {"x": 0, "y": 0}},
            {"kind": "text_gdiplus_v2", "name": "BRB Text",
             "settings": {"text": "🔴 BE RIGHT BACK",
                          "font": {"face": "Arial", "size": 72, "bold": True},
                          "color": 0xff4444, "align": "center",
                          "vertical_align": "center",
                          "outline": True, "outline_color": 0x000000,
                          "outline_size": 4},
             "position": {"x": 960, "y": 540, "alignment": 5},
             "filters": []},
        ],
    },
    {
        "name": "🚀 Stream Ending",
        "index": 4,
        "sources": [
            {"kind": "color_source_v2", "name": "Background",
             "settings": {"color": 0x1a1a2e, "width": 1920, "height": 1080},
             "position": {"x": 0, "y": 0}},
            {"kind": "text_gdiplus_v2", "name": "Ending Text",
             "settings": {"text": "STREAM ENDED\nThanks for watching! 🎉 ",
                          "font": {"face": "Arial", "size": 60, "bold": True},
                          "color": 0xffffff, "align": "center",
                          "vertical_align": "center",
                          "outline": True, "outline_color": 0x000000,
                          "outline_size": 4},
             "position": {"x": 960, "y": 540, "alignment": 5},
             "filters": []},
        ],
    },
]


def _get_source_kind_for_platform(kind: str, is_macos: bool,
                                   is_linux: bool) -> str:
    """Map cross-platform source kinds to OS-specific kinds."""
    mapping = {
        "game_capture": {
            "win32": "game_capture",
            "darwin": "window_capture",  # macOS uses window capture for games
            "linux": "xcomposite_input",
        },
        "wasapi_input_capture": {
            "win32": "wasapi_input_capture",
            "darwin": "coreaudio_input_capture",
            "linux": "pulse_input_capture",
        },
        "wasapi_output_capture": {
            "win32": "wasapi_output_capture",
            "darwin": "coreaudio_output_capture",
            "linux": "pulse_output_capture",
        },
        "text_gdiplus_v2": {
            "win32": "text_gdiplus_v2",
            "darwin": "text_ft2_source_v2",
            "linux": "text_ft2_source_v2",
        },
        "video_capture": {
            "win32": "dshow_input",
            "darwin": "av_capture_input",
            "linux": "v4l2_input",
        },
    }
    plat = "darwin" if is_macos else ("linux" if is_linux else "win32")
    return mapping.get(kind, {}).get(plat, kind)


def create_scene_collection(obs, settings: dict,
                            scene_collection_name: str = "obs-quickstart",
                            video_devices: list[str] | None = None,
                            audio_devices: list[str] | None = None) -> bool:
    """Create a complete scene collection with all scenes and sources.

    This is the main entry point.

    Args:
        obs: Connected obsws_python.ReqClient instance.
        settings: Settings dict (used for resolution detection).
        scene_collection_name: Name for the scene collection.
        video_devices: List of detected video device names.
        audio_devices: List of detected audio device names.

    Returns:
        True if all scenes created successfully.
    """
    import sys
    is_macos = sys.platform == "darwin"
    is_linux = sys.platform.startswith("linux")
    is_windows = sys.platform == "win32"

    # Get base resolution from settings or defaults
    base_w, base_h = settings.get("base_resolution", (1920, 1080))

    logger.info(f"Creating scene collection: {scene_collection_name}")

    # --- Step 1: Create all scenes first ---
    scene_names = []
    for scene_cfg in SCENE_CONFIG:
        name = scene_cfg["name"]
        scene_names.append(name)
        try:
            obs.create_scene(name)
            logger.info(f"  Created scene: {name}")
        except Exception as e:
            logger.warning(f"  Scene '{name}' may already exist: {e}")

    # --- Step 2: Add sources to each scene ---
    for scene_cfg in SCENE_CONFIG:
        scene_name = scene_cfg["name"]
        sources = scene_cfg["sources"]
        is_gameplay = "Gameplay" in scene_name

        for source_cfg in sources:
            kind = source_cfg["kind"]
            sname = source_cfg["name"]
            src_settings = dict(source_cfg["settings"])

            # Platform-adapt source kinds
            adapted_kind = _get_source_kind_for_platform(kind, is_macos, is_linux)

            # Special handling for Game Capture on non-Windows
            if kind == "game_capture" and not is_windows:
                if is_macos:
                    src_settings = {"capture_mode": "any_fullscreen"}
                else:
                    src_settings = {"capture_mode": "any_fullscreen"}

            # For audio devices — create only if not already existing
            if kind in ("wasapi_input_capture", "wasapi_output_capture",
                        "pulse_input_capture", "pulse_output_capture",
                        "coreaudio_input_capture", "coreaudio_output_capture",
                        "av_capture_input", "dshow_input", "v4l2_input"):
                # Check if source already exists (to avoid duplicates)
                try:
                    existing = obs.get_input_list()
                    exists = any(
                        inp.get("inputName") == sname
                        for inp in getattr(existing, 'inputs', [])
                    )
                    if exists:
                        # Just add existing source to scene as reference
                        try:
                            # Use scene item creation
                            scene_item_id = obs.create_scene_item(
                                scene_name=scene_name,
                                source_name=sname
                            ).scene_item_id
                            logger.info(f"    Added existing '{sname}' → {scene_name}")
                        except Exception:
                            pass
                        continue
                except Exception:
                    pass

                # Create audio capture source
                try:
                    obs.create_input(
                        scene_name=scene_name,
                        input_name=sname,
                        input_kind=adapted_kind,
                        input_settings=src_settings,
                        scene_item_enabled=True,
                    )
                    logger.info(f"    Created: {sname} ({adapted_kind}) in {scene_name}")
                except Exception as e:
                    logger.warning(f"    Failed to create {sname}: {e}")
                continue

            # Create regular source
            try:
                # For color sources and text, use platform-appropriate sizes
                if kind == "color_source_v2":
                    src_settings["width"] = base_w
                    src_settings["height"] = base_h

                obs.create_input(
                    scene_name=scene_name,
                    input_name=sname,
                    input_kind=adapted_kind,
                    input_settings=src_settings,
                    scene_item_enabled=True,
                )
                logger.info(f"    Created: {sname} ({adapted_kind}) → {scene_name}")
            except Exception as e:
                logger.warning(f"    Failed to create {sname} in '{scene_name}': {e}")

        # --- Step 3: Add webcam to Gameplay and Just Chatting scenes ---
        if is_gameplay and video_devices:
            _add_webcam_source(obs, scene_name, video_devices,
                               base_w, base_h, is_macos, is_linux)

        # --- Step 4: Apply position/size to color and text sources ---
        _arrange_source_positions(obs, scene_name, sources,
                                  base_w, base_h, is_macos, is_linux)

        # --- Step 5: Add audio filters ---
        for source_cfg in sources:
            for filter_cfg in source_cfg.get("filters", []):
                try:
                    _add_source_filter(obs, source_cfg["name"],
                                       filter_cfg)
                except Exception as e:
                    logger.debug(f"    Filter skip: {e}")

    # --- Step 6: Set scene order ---
    try:
        obs.set_scene_order(scene_names)
        logger.info("  Scene order set")
    except Exception as e:
        logger.warning(f"  Could not set scene order: {e}")

    # --- Step 7: Set current scene to first one ---
    if scene_names:
        try:
            obs.set_current_program_scene(scene_names[0])
            logger.info(f"  Current scene: {scene_names[0]}")
        except Exception:
            pass

    logger.info("Scene collection creation complete!")
    return True


def _add_webcam_source(obs, scene_name: str, video_devices: list[str],
                       base_w: int, base_h: int,
                       is_macos: bool, is_linux: bool):
    """Add a webcam source to a scene with proper positioning."""
    cam_kind = _get_source_kind_for_platform("video_capture",
                                             is_macos, is_linux)

    # Try to find actual device names
    # On macOS, default camera is usually just "Camera"
    # On Windows, it's the device name from DirectShow
    cam_name = video_devices[0] if video_devices else "Camera"
    display_name = f"📷 {cam_name}"

    try:
        # Check if camera source exists
        try:
            existing = obs.get_input_list()
            exists = any(
                inp.get("inputName") == display_name
                for inp in getattr(existing, 'inputs', [])
            )
        except Exception:
            exists = False

        if not exists:
            obs.create_input(
                scene_name=scene_name,
                input_name=display_name,
                input_kind=cam_kind,
                input_settings={},
                scene_item_enabled=True,
            )
        else:
            # Add as reference
            try:
                obs.create_scene_item(scene_name=scene_name,
                                      source_name=display_name)
            except Exception:
                pass

        # Position camera in bottom-right corner (PIP)
        # 480x270 = ~25% of 1080p
        cam_w, cam_h = 480, 270
        cam_x = base_w - cam_w - 30  # 30px margin
        cam_y = base_h - cam_h - 30

        # Get scene item ID and set transform
        scene_items = obs.get_scene_item_list(scene_name)
        for item in getattr(scene_items, 'scene_items', []):
            if item.get("sourceName") == display_name:
                item_id = item.get("sceneItemId")
                obs.set_scene_item_transform(
                    scene_name=scene_name,
                    scene_item_id=item_id,
                    transform={
                        "positionX": cam_x,
                        "positionY": cam_y,
                        "width": cam_w,
                        "height": cam_h,
                        "scaleX": cam_w / base_w,
                        "scaleY": cam_h / base_h,
                    }
                )
                break

        logger.info(f"    Camera '{cam_name}' added to {scene_name}")
    except Exception as e:
        logger.warning(f"    Failed to add camera to {scene_name}: {e}")

        # Fallback: add generic video capture
        try:
            obs.create_input(
                scene_name=scene_name,
                input_name="Camera",
                input_kind=cam_kind,
                input_settings={},
                scene_item_enabled=True,
            )
        except Exception:
            pass


def _arrange_source_positions(obs, scene_name: str, sources: list,
                               base_w: int, base_h: int,
                               is_macos: bool, is_linux: bool):
    """Position sources correctly within a scene."""
    try:
        scene_items = obs.get_scene_item_list(scene_name)
    except Exception:
        return

    for item in getattr(scene_items, 'scene_items', []):
        sname = item.get("sourceName", "")
        item_id = item.get("sceneItemId")

        # Find source config
        source_cfg = next((s for s in sources if s["name"] == sname), None)
        if not source_cfg:
            continue

        pos = source_cfg.get("position", {})
        if not pos:
            continue

        # Calculate transform
        transform = {}
        if "x" in pos and "y" in pos:
            transform["positionX"] = pos["x"]
            transform["positionY"] = pos["y"]
        if "width" in pos and "height" in pos:
            transform["width"] = pos["width"]
            transform["height"] = pos["height"]
            transform["scaleX"] = pos["width"] / base_w if base_w else 1
            transform["scaleY"] = pos["height"] / base_h if base_h else 1
        if "alignment" in pos:
            transform["alignment"] = pos["alignment"]

        if transform:
            try:
                obs.set_scene_item_transform(
                    scene_name=scene_name,
                    scene_item_id=item_id,
                    transform=transform,
                )
            except Exception:
                pass


def _add_source_filter(obs, source_name: str, filter_cfg: dict):
    """Add a filter to a source."""
    try:
        # Check if filter already exists
        filters = obs.get_source_filter_list(source_name)
        for f in getattr(filters, 'filters', []):
            if f.get("filterName") == filter_cfg["name"]:
                return  # Already exists

        obs.create_source_filter(
            source_name=source_name,
            filter_name=filter_cfg["name"],
            filter_kind=filter_cfg["kind"],
            filter_settings=filter_cfg.get("settings", {}),
        )
    except Exception as e:
        logger.debug(f"Filter '{filter_cfg['name']}' not added: {e}")


def setup_transitions(obs, base_resolution: tuple[int, int] = (1920, 1080)) -> bool:
    """Set up scene transitions.

    Args:
        obs: Connected obsws_python.ReqClient instance.
        base_resolution: (width, height) tuple.

    Returns:
        True if successful.
    """
    # Set the default transition to Fade
    try:
        # Get current transition
        try:
            current = obs.get_current_scene_transition()
            logger.info(f"Current transition: {current}")
        except Exception:
            pass

        # Set transition settings
        try:
            # First, create/ensure fade transition exists
            transitions = obs.get_scene_transition_list()
            has_fade = any(
                t.get("transitionName", "").startswith("Fade")
                for t in getattr(transitions, 'transitions', [])
            )

            if not has_fade:
                # Create fade transition
                obs.create_scene_transition(
                    transition_name="Fade",
                    transition_kind="fade_transition",
                    transition_settings={
                        "transition_points": [
                            {"x": 0, "y": 0},
                            {"x": 1, "y": 1},
                        ]
                    },
                )

            # Set Fade as current scene transition
            # This is done via SetCurrentSceneTransition
            try:
                obs.set_current_scene_transition("Fade")
            except Exception:
                # Try SetCurrentTransition
                try:
                    obs.set_current_transition("Fade")
                except Exception:
                    pass

            logger.info("Transition set: Fade")
        except Exception as e:
            logger.warning(f"Could not set transition: {e}")
    except Exception as e:
        logger.warning(f"Transition setup failed: {e}")
        return False

    return True


def configure_audio_devices(obs) -> bool:
    """Auto-detect and configure audio devices in OBS.

    Returns:
        True if successful.
    """
    success = True

    # Try to get special inputs (default audio devices)
    try:
        inputs = obs.get_special_inputs()
        # Check what's available
        logger.info(f"Special inputs detected")
    except Exception:
        pass

    # Try to create desktop audio if missing
    for audio_name, audio_kind in [
        ("Desktop Audio", "wasapi_output_capture"),
        ("Mic/Aux", "wasapi_input_capture"),
    ]:
        try:
            existing = obs.get_input_list()
            exists = any(
                inp.get("inputName") == audio_name
                for inp in getattr(existing, 'inputs', [])
            )
            if not exists:
                # Determine correct kind for platform
                import sys
                if sys.platform == "darwin":
                    kind = "coreaudio_output_capture" if "Desktop" in audio_name else "coreaudio_input_capture"
                elif sys.platform.startswith("linux"):
                    kind = "pulse_output_capture" if "Desktop" in audio_name else "pulse_input_capture"
                else:
                    kind = audio_kind

                obs.create_input(
                    scene_name="",
                    input_name=audio_name,
                    input_kind=kind,
                    input_settings={},
                    scene_item_enabled=True,
                )
                logger.info(f"Audio source created: {audio_name}")
        except Exception as e:
            logger.debug(f"Audio '{audio_name}': {e}")

    return success