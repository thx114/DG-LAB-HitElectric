import json
import os
import sys
import copy
_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from image import parse_coordinate, parse_coordinates, parse_colors

_DEFAULTS = {
    "plugins": {
        "toggle_key": "f9",
        "setting_mode_key": "f10",
        "overlay_toggle_key": "f6",
        "scan_interval": 0.1,
        "log": False,
        "game": {
            "process_exeName": "",
            "process_title": "",
            "region": {
                "top_left": [0, 1300],
                "bottom_right": [1500, 1500]
            }
        },
        "plus_sign": {
            "enabled": True,
            "positions": "",
            "colors": "",
            "negative_positions": "",
            "negative_colors": "",
            "tolerance": 30
        },
        "spectate": {
            "enabled": True,
            "positions": "",
            "colors": "",
            "tolerance": 30
        },
        "health_bar": {
            "enabled": False,
            "start": [0, 0],
            "end": [0, 0],
            "colors": "",
            "tolerance": 30,
            "sample_points": 20,
            "strength": 24,
            "strength_b": 24,
            "ocr_top_left": [0, 0],
            "ocr_bottom_right": [100, 100],
            "ocr_end_trigger": False,
            "ocr_number_color": "",
            "ocr_number_tolerance": 30,
            "drop_threshold": 0,
            "ocr_filters": None,
            "ocr_api_ip": "",
            "ocr_api_data": ""
        },
        "shield_bar": {
            "enabled": False,
            "start": [0, 0],
            "end": [0, 0],
            "colors": "",
            "tolerance": 25,
            "sample_points": 12,
            "strength": 20,
            "strength_b": 20,
            "ocr_top_left": [0, 0],
            "ocr_bottom_right": [100, 100],
            "ocr_end_trigger": False,
            "ocr_number_color": "",
            "ocr_number_tolerance": 25,
            "blocks_health": True,
            "ocr_filters": None,
            "ocr_api_ip": "",
            "ocr_api_data": ""
        },
        "overlay": {
            "enabled": True
        },
        "overlap": {
            "enabled": True,
            "strength_add": 1,
            "strength_max": 200,
            "duration_multiplier": 2
        },
        "ocr": {
            "enabled": False,
            "port": 1395,
            "health_shield_detect": False
        },
        "multi_character": {
            "enabled": False,
            "character_keys": "1,2,3",
            "gamepad_enabled": True,
            "gamepad_buttons": "0x1000,0x2000,0x4000,0x8000",
            "switch_immunity_frames": 5,
            "switch_delay_frames": 1
        },
        "damage_detect": {
            "enabled": False,
            "mid_value": 5000,
            "max_bonus": 10
        }
    },
    "waveform": {
        "health_pulse": [
            "1414141464646464",
            "1414141464646464",
            "0A0A0A0A50505050",
            "0A0A0A0A50505050",
            "0A0A0A0A3C3C3C3C",
            "0A0A0A0A3C3C3C3C",
            "0A0A0A0A28282828",
            "0A0A0A0A28282828",
            "0A0A0A0A14141414",
            "0A0A0A0A0A0A0A0A"
        ],
        "shield_pulse": [
            "0A0A0A0A50505050",
            "0A0A0A0A50505050",
            "0A0A0A0A28282828",
            "0A0A0A0A0A0A0A0A"
        ]
    }
}


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _migrate_legacy_filters(data):
    for bar_key in ("health_bar", "shield_bar"):
        bar = data.get("plugins", {}).get(bar_key, {})
        if bar.get("ocr_filters") is not None:
            continue
        color = bar.get("ocr_number_color", "")
        tolerance = bar.get("ocr_number_tolerance", 30)
        if color:
            bar["ocr_filters"] = [
                {
                    "type": "replace_color",
                    "colors": color if isinstance(color, str) else str(color),
                    "tolerance": tolerance
                }
            ]
        else:
            bar["ocr_filters"] = []
    return data


def _ensure_defaults(data):
    """确保所有新增配置项都有默认值，用于兼容旧版本 config.json"""
    plugins = data.setdefault("plugins", {})

    # overlap 配置
    overlap = plugins.setdefault("overlap", {})
    if "duration_multiplier" not in overlap:
        overlap["duration_multiplier"] = 2

    # damage_detect 配置
    damage = plugins.setdefault("damage_detect", {})
    if "enabled" not in damage:
        damage["enabled"] = False
    if "mid_value" not in damage:
        damage["mid_value"] = 5000
    if "max_bonus" not in damage:
        damage["max_bonus"] = 10

    # health_bar / shield_bar 新增字段
    for bar_key in ("health_bar", "shield_bar"):
        bar = plugins.setdefault(bar_key, {})
        if "ocr_api_ip" not in bar:
            bar["ocr_api_ip"] = ""
        if "ocr_api_data" not in bar:
            bar["ocr_api_data"] = ""

    return data


class Config:
    def __init__(self):
        self._data = copy.deepcopy(_DEFAULTS)
        self._cache = {}
        self._config_path = None

    def load(self, config_path):
        self._config_path = config_path
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                if isinstance(file_data, dict) and "config" in file_data:
                    file_data = file_data["config"]
                self._data = _deep_merge(_DEFAULTS, file_data)
                self._data = _migrate_legacy_filters(self._data)
                self._data = _ensure_defaults(self._data)
            except (json.JSONDecodeError, IOError):
                pass
        self._cache = {}
        self._build_cache()

    def save(self, config_path=None):
        path = config_path or self._config_path
        if not path:
            return False
        try:
            output = {"config": self._data}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            return True
        except IOError:
            return False

    def _build_cache(self):
        self._cache = {}
        plugins = self._data.get("plugins", {})

        plus_config = plugins.get("plus_sign", {})
        self._cache["plus_enabled"] = plus_config.get("enabled", True)
        self._cache["plus_positions"] = parse_coordinates(plus_config.get("positions", ""))
        self._cache["plus_colors"] = parse_colors(plus_config.get("colors", ""))
        self._cache["plus_negative_positions"] = parse_coordinates(plus_config.get("negative_positions", ""))
        self._cache["plus_negative_colors"] = parse_colors(plus_config.get("negative_colors", ""))
        self._cache["plus_tolerance"] = plus_config.get("tolerance", 30)

        spectate_config = plugins.get("spectate", {})
        self._cache["spectate_enabled"] = spectate_config.get("enabled", True)
        self._cache["spectate_positions"] = parse_coordinates(spectate_config.get("positions", ""))
        self._cache["spectate_colors"] = parse_colors(spectate_config.get("colors", ""))
        self._cache["spectate_tolerance"] = spectate_config.get("tolerance", 30)

        health_config = plugins.get("health_bar", {})
        self._cache["health_enabled"] = health_config.get("enabled", False)
        self._cache["health_start"] = parse_coordinate(health_config.get("start", [0, 0]))
        self._cache["health_end"] = parse_coordinate(health_config.get("end", [0, 0]))
        self._cache["health_colors"] = parse_colors(health_config.get("colors", ""))
        self._cache["health_tolerance"] = health_config.get("tolerance", 30)
        self._cache["health_sample_points"] = health_config.get("sample_points", 20)
        self._cache["health_ocr_top_left"] = parse_coordinate(health_config.get("ocr_top_left", [0, 0]))
        self._cache["health_ocr_bottom_right"] = parse_coordinate(health_config.get("ocr_bottom_right", [100, 100]))
        self._cache["health_ocr_end_trigger"] = health_config.get("ocr_end_trigger", False)
        self._cache["health_ocr_number_color"] = health_config.get("ocr_number_color", "")
        self._cache["health_ocr_number_tolerance"] = health_config.get("ocr_number_tolerance", 30)
        self._cache["health_drop_threshold"] = health_config.get("drop_threshold", 0)
        self._cache["health_ocr_filters"] = health_config.get("ocr_filters", [])
        self._cache["health_ocr_api_ip"] = health_config.get("ocr_api_ip", "")
        self._cache["health_ocr_api_data"] = health_config.get("ocr_api_data", "")

        shield_config = plugins.get("shield_bar", {})
        self._cache["shield_enabled"] = shield_config.get("enabled", False)
        self._cache["shield_start"] = parse_coordinate(shield_config.get("start", [0, 0]))
        self._cache["shield_end"] = parse_coordinate(shield_config.get("end", [0, 0]))
        self._cache["shield_colors"] = parse_colors(shield_config.get("colors", ""))
        self._cache["shield_tolerance"] = shield_config.get("tolerance", 25)
        self._cache["shield_sample_points"] = shield_config.get("sample_points", 12)
        self._cache["shield_ocr_top_left"] = parse_coordinate(shield_config.get("ocr_top_left", [0, 0]))
        self._cache["shield_ocr_bottom_right"] = parse_coordinate(shield_config.get("ocr_bottom_right", [100, 100]))
        self._cache["shield_ocr_end_trigger"] = shield_config.get("ocr_end_trigger", False)
        self._cache["shield_ocr_number_color"] = shield_config.get("ocr_number_color", "")
        self._cache["shield_ocr_number_tolerance"] = shield_config.get("ocr_number_tolerance", 25)
        self._cache["shield_blocks_health"] = shield_config.get("blocks_health", True)
        self._cache["shield_ocr_filters"] = shield_config.get("ocr_filters", [])
        self._cache["shield_ocr_api_ip"] = shield_config.get("ocr_api_ip", "")
        self._cache["shield_ocr_api_data"] = shield_config.get("ocr_api_data", "")

        overlap_config = plugins.get("overlap", {})
        self._cache["overlap_enabled"] = overlap_config.get("enabled", True)
        self._cache["overlap_strength_add"] = overlap_config.get("strength_add", 1)
        self._cache["overlap_strength_max"] = overlap_config.get("strength_max", 200)
        self._cache["overlap_duration_multiplier"] = overlap_config.get("duration_multiplier", 2)

        ocr_config = plugins.get("ocr", {})
        self._cache["ocr_enabled"] = ocr_config.get("enabled", False)
        self._cache["ocr_port"] = ocr_config.get("port", 1395)
        self._cache["ocr_health_shield_detect"] = ocr_config.get("health_shield_detect", False)

        multi_char_config = plugins.get("multi_character", {})
        self._cache["multi_char_enabled"] = multi_char_config.get("enabled", False)
        self._cache["character_keys_str"] = multi_char_config.get("character_keys", "1,2,3")
        self._cache["gamepad_enabled"] = multi_char_config.get("gamepad_enabled", True)
        self._cache["gamepad_buttons_str"] = multi_char_config.get("gamepad_buttons", "0x1000,0x2000,0x4000,0x8000")
        self._cache["switch_immunity_frames"] = multi_char_config.get("switch_immunity_frames", 5)
        self._cache["switch_delay_frames"] = multi_char_config.get("switch_delay_frames", 1)

        damage_config = plugins.get("damage_detect", {})
        self._cache["damage_enabled"] = damage_config.get("enabled", False)
        self._cache["damage_mid_value"] = damage_config.get("mid_value", 5000)
        self._cache["damage_max_bonus"] = damage_config.get("max_bonus", 10)

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def get_raw(self, path, default=None):
        keys = path.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def set_raw(self, path, value):
        keys = path.split(".")
        current = self._data
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        self._build_cache()

    @property
    def data(self):
        return self._data

    @property
    def plugins(self):
        return self._data.get("plugins", {})

    @property
    def waveform(self):
        return self._data.get("waveform", {})

    def get_capture_region(self):
        game_config = self.plugins.get("game", {})
        region_config = game_config.get("region", {})
        top_left = region_config.get("top_left", [0, 1300])
        bottom_right = region_config.get("bottom_right", [1500, 1500])
        if isinstance(top_left, list) and len(top_left) >= 2 and isinstance(bottom_right, list) and len(bottom_right) >= 2:
            x = max(0, top_left[0])
            y = max(0, top_left[1])
            w = max(10, bottom_right[0] - top_left[0])
            h = max(10, bottom_right[1] - top_left[1])
            return [int(x), int(y), int(w), int(h)]
        return [0, 1300, 1500, 200]
