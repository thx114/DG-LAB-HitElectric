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
        "capture_method": "gdi",
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
            "drop_threshold": 0,
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
            "duration_multiplier": 1.5,
            "decay_enabled": True,
            "decay_mode": "instant",
            "decay_value": 1,
            "decay_percent": 10,
            "decay_ratio_accel": 0.5,
            "decay_script": ""
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
            "switch_immunity_frames": 2,
            "switch_delay_frames": 1
        },
        "damage_detect": {
            "enabled": False,
            "mid_value": 5000,
            "max_bonus": 10,
            "formula": "default",
            "script": ""
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

_CACHE_MAP = [
    (None, "capture_method", "capture_method", None),

    ("plus_sign", "enabled", "plus_enabled", None),
    ("plus_sign", "positions", "plus_positions", parse_coordinates),
    ("plus_sign", "colors", "plus_colors", parse_colors),
    ("plus_sign", "negative_positions", "plus_negative_positions", parse_coordinates),
    ("plus_sign", "negative_colors", "plus_negative_colors", parse_colors),
    ("plus_sign", "tolerance", "plus_tolerance", None),

    ("spectate", "enabled", "spectate_enabled", None),
    ("spectate", "positions", "spectate_positions", parse_coordinates),
    ("spectate", "colors", "spectate_colors", parse_colors),
    ("spectate", "tolerance", "spectate_tolerance", None),

    ("health_bar", "enabled", "health_enabled", None),
    ("health_bar", "start", "health_start", parse_coordinate),
    ("health_bar", "end", "health_end", parse_coordinate),
    ("health_bar", "colors", "health_colors", parse_colors),
    ("health_bar", "tolerance", "health_tolerance", None),
    ("health_bar", "sample_points", "health_sample_points", None),
    ("health_bar", "ocr_top_left", "health_ocr_top_left", parse_coordinate),
    ("health_bar", "ocr_bottom_right", "health_ocr_bottom_right", parse_coordinate),
    ("health_bar", "ocr_end_trigger", "health_ocr_end_trigger", None),
    ("health_bar", "ocr_number_color", "health_ocr_number_color", None),
    ("health_bar", "ocr_number_tolerance", "health_ocr_number_tolerance", None),
    ("health_bar", "drop_threshold", "health_drop_threshold", None),
    ("health_bar", "ocr_filters", "health_ocr_filters", None),
    ("health_bar", "ocr_api_ip", "health_ocr_api_ip", None),
    ("health_bar", "ocr_api_data", "health_ocr_api_data", None),

    ("shield_bar", "enabled", "shield_enabled", None),
    ("shield_bar", "start", "shield_start", parse_coordinate),
    ("shield_bar", "end", "shield_end", parse_coordinate),
    ("shield_bar", "colors", "shield_colors", parse_colors),
    ("shield_bar", "tolerance", "shield_tolerance", None),
    ("shield_bar", "sample_points", "shield_sample_points", None),
    ("shield_bar", "ocr_top_left", "shield_ocr_top_left", parse_coordinate),
    ("shield_bar", "ocr_bottom_right", "shield_ocr_bottom_right", parse_coordinate),
    ("shield_bar", "ocr_end_trigger", "shield_ocr_end_trigger", None),
    ("shield_bar", "ocr_number_color", "shield_ocr_number_color", None),
    ("shield_bar", "ocr_number_tolerance", "shield_ocr_number_tolerance", None),
    ("shield_bar", "blocks_health", "shield_blocks_health", None),
    ("shield_bar", "drop_threshold", "shield_drop_threshold", None),
    ("shield_bar", "ocr_filters", "shield_ocr_filters", None),
    ("shield_bar", "ocr_api_ip", "shield_ocr_api_ip", None),
    ("shield_bar", "ocr_api_data", "shield_ocr_api_data", None),

    ("overlap", "enabled", "overlap_enabled", None),
    ("overlap", "strength_add", "overlap_strength_add", None),
    ("overlap", "strength_max", "overlap_strength_max", None),
    ("overlap", "duration_multiplier", "overlap_duration_multiplier", None),
    ("overlap", "decay_enabled", "overlap_decay_enabled", None),
    ("overlap", "decay_mode", "overlap_decay_mode", None),
    ("overlap", "decay_value", "overlap_decay_value", None),
    ("overlap", "decay_percent", "overlap_decay_percent", None),
    ("overlap", "decay_ratio_accel", "overlap_decay_ratio_accel", None),
    ("overlap", "decay_script", "overlap_decay_script", None),

    ("ocr", "enabled", "ocr_enabled", None),
    ("ocr", "port", "ocr_port", None),
    ("ocr", "health_shield_detect", "ocr_health_shield_detect", None),

    ("multi_character", "enabled", "multi_char_enabled", None),
    ("multi_character", "character_keys", "character_keys_str", None),
    ("multi_character", "gamepad_enabled", "gamepad_enabled", None),
    ("multi_character", "gamepad_buttons", "gamepad_buttons_str", None),
    ("multi_character", "switch_immunity_frames", "switch_immunity_frames", None),
    ("multi_character", "switch_delay_frames", "switch_delay_frames", None),

    ("damage_detect", "enabled", "damage_enabled", None),
    ("damage_detect", "mid_value", "damage_mid_value", None),
    ("damage_detect", "max_bonus", "damage_max_bonus", None),
    ("damage_detect", "formula", "damage_formula", None),
    ("damage_detect", "script", "damage_script", None),
]


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
    plugins = data.setdefault("plugins", {})
    defaults_plugins = _DEFAULTS.get("plugins", {})

    for key, default_val in defaults_plugins.items():
        if isinstance(default_val, dict):
            section = plugins.setdefault(key, {})
            _deep_fill(section, default_val)
        elif key not in plugins:
            plugins[key] = copy.deepcopy(default_val)

    return data


def _deep_fill(target, defaults):
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(default_val)
        elif isinstance(default_val, dict) and isinstance(target.get(key), dict):
            _deep_fill(target[key], default_val)


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

        for section_key, field_key, cache_key, parser in _CACHE_MAP:
            if section_key is None:
                section = plugins
                default_val = _DEFAULTS.get("plugins", {}).get(field_key)
            else:
                section = plugins.get(section_key, {})
                default_val = _DEFAULTS.get("plugins", {}).get(section_key, {}).get(field_key)
            raw_val = section.get(field_key, default_val)
            if parser and raw_val is not None:
                self._cache[cache_key] = parser(raw_val)
            else:
                self._cache[cache_key] = raw_val

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
