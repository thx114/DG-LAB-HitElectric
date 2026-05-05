"""
挨打就电v4.py - 挨打就电主程序 (重构版)

架构:
- HitElectricLogic: 判断辅助库 (DamageDetector, OverlapProcessor, TriggerConditions, OCRValidator)
- 本文件: 主循环、截图、电击触发、悬浮窗、按键监听
"""

import asyncio
import ctypes
import ctypes.wintypes
import importlib
import threading
import time
import json
import tkinter as tk
import os
import sys

debug_mode = False

_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

import lib
from config import Config
from HitElectricLogic import DamageDetector, OverlapProcessor, TriggerConditions, OCRValidator
from keycodes import VK_F6, VK_F7, VK_F8, VK_F9, VK_F10, VK_RETURN, VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT, CHAR_KEY_MAP, user32, is_key_down
from overlay import OverlayWindow

name = "卡丘-挨打就电"
author = "F_thx"

# ============================================================
# 全局状态
# ============================================================

class GlobalState:
    """全局状态容器，减少散落的全局变量"""

    def __init__(self):
        self.base_dir = None
        self.PULSE_DATA = None
        self.stop_event = None
        self.msg_queue = None
        self.server = None
        self.logger = None

        self.game_hwnd = None
        self.is_monitoring = False
        self.hwnd = None
        self.cfg = Config()
        self.main_loop = None
        self.overlay_hwnd = None

        self.current_health = 100
        self.current_shield = 0
        self.current_electric_strength = 0
        self.is_spectating = False
        self.has_healthbar = False

        self.multi_char_enabled = False
        self.active_character = 0
        self.target_character = -1
        self.character_count = 0
        self.character_states = {}
        self.switch_immunity_frames = 0
        self.switch_immunity_frames_config = 5
        self.switch_delay_frames_config = 1
        self.pending_switch_index = -1
        self.switch_delay_counter = 0
        self.pre_switch_health = None
        self.pre_switch_shield = None
        self.switch_value_unchanged = False
        self.switch_immunity_extensions = 0
        self.switch_max_extensions = 2

        self.prev_has_healthbar = False
        self.healthbar_appear_immunity = False
        self.character_key_codes = []
        self.gamepad_enabled = False
        self.gamepad_button_codes = []

        self.strength_values = {
            "health_a": 24, "health_b": 24,
            "shield_a": 20, "shield_b": 20
        }

        self.current_strength_a = None
        self.current_strength_b = None

        self.electric_trigger_message = ""
        self.electric_trigger_count = 0

        self.overlay_text = "等待启动... (使用F9启动检测)"
        self.overlay_update_event = threading.Event()
        self.install_status = ""
        self.install_status_until = 0

        self.setting_mode = False
        self.setting_target = 0
        self.setting_event = threading.Event()

        self.capture_method = "GDI"

        self.config = {}
        self.cached_config = {}

        self.last_loop_time = 0


gs = GlobalState()

# 模块实例 (在 main 中初始化)
damage_detector = None
overlap_processor = None
trigger_conditions = None
ocr_validator = None
key_monitor_thread = None


def _cfg_get(key, default=None):
    """配置获取函数，供 HitElectricLogic 模块使用"""
    return gs.cached_config.get(key, default)


RELOAD_TRIGGER_FILE = os.path.join(_plugin_dir, ".reload_trigger")

DXGI_MIRRORS = [
    ("清华大学", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
    ("中国科学技术大学", "https://pypi.mirrors.ustc.edu.cn/simple/"),
    ("腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple"),
    ("豆瓣", "https://pypi.doubanio.com/simple"),
]


def _get_site_packages_dir():
    """获取 site-packages 目录（优先使用应用 lib 目录）"""
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    plugins_dir = os.path.dirname(plugin_dir)
    app_lib_dir = os.path.join(os.path.dirname(plugins_dir), "lib")
    if os.path.isdir(app_lib_dir):
        return app_lib_dir
    import site
    for sp in site.getsitepackages():
        if os.path.isdir(sp):
            return sp
    user_site = site.getusersitepackages()
    if user_site:
        os.makedirs(user_site, exist_ok=True)
        return user_site
    fallback = os.path.join(plugin_dir, "_libs")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def _find_dxcam_wheel_url(index_url):
    """从 PyPI 镜像查找适合当前平台的 dxcam wheel 下载地址"""
    import urllib.request
    import urllib.parse
    import re
    platform_tag = "win_amd64"
    py_ver = f"cp{sys.version_info.major}{sys.version_info.minor}"
    py_fallbacks = [py_ver, "py3", "py2.py3"]
    for minor in range(sys.version_info.minor, 0, -1):
        tag = f"cp{sys.version_info.major}{minor}"
        if tag not in py_fallbacks:
            py_fallbacks.append(tag)

    api_url = index_url.rstrip("/") + "/dxcam/"
    req = urllib.request.Request(api_url, headers={"Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)

    candidates = []
    for match in re.finditer(r'href="([^"]+\.whl[^"]*)"', html):
        raw_url = match.group(1)
        fname = urllib.parse.unquote(raw_url.split("/")[-1].split("#")[0])
        parts = fname.replace(".whl", "").split("-")
        if len(parts) < 5:
            continue
        name, ver, py_tag, abi, plat = parts[0], parts[1], parts[2], parts[3], parts[4]
        if platform_tag not in plat.split("."):
            continue
        py_ok = any(t in py_fallbacks for t in py_tag.split("."))
        if not py_ok:
            continue
        is_exact_py = py_ver in py_tag.split(".")
        candidates.append((fname, raw_url, ver, is_exact_py))

    if not candidates:
        return None, f"未找到匹配的 wheel (需要 {py_ver}-{platform_tag})"

    candidates.sort(key=lambda x: (x[3], x[2]), reverse=True)
    best = candidates[0]
    raw_url = best[1]
    if raw_url.startswith("http"):
        full_url = raw_url.split("#")[0]
    else:
        full_url = urllib.parse.urljoin(api_url, raw_url).split("#")[0]
    return full_url, None


def _download_and_install_wheel(wheel_url, dest_dir):
    """下载 wheel 并解压到 site-packages"""
    import urllib.request
    import zipfile
    import tempfile

    fname = wheel_url.split("/")[-1].split("?")[0]
    tmp_dir = tempfile.mkdtemp(prefix="dxcam_install_")
    whl_path = os.path.join(tmp_dir, fname)

    try:
        gs.install_status = f"下载 {fname[:30]}..."
        try:
            gs.overlay_update_event.set()
        except Exception:
            pass
        urllib.request.urlretrieve(wheel_url, whl_path)

        if not zipfile.is_zipfile(whl_path):
            return False, "下载的文件不是有效的 wheel 包"

        gs.install_status = "解压安装中..."
        try:
            gs.overlay_update_event.set()
        except Exception:
            pass

        with zipfile.ZipFile(whl_path, 'r') as zf:
            zf.extractall(dest_dir)

        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.remove(whl_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass


def _install_dxcam_background():
    """后台线程安装 dxcam，安装完成后自动切换到 DXGI"""
    try:
        try:
            gs.install_status = "正在安装 dxcam..."
            gs.install_status_until = time.time() + 600
            gs.overlay_update_event.set()
        except Exception:
            pass

        dest_dir = _get_site_packages_dir()
        if dest_dir not in sys.path:
            sys.path.insert(0, dest_dir)

        for name, url in DXGI_MIRRORS:
            try:
                log(f"正在从 {name} 查找 dxcam...")
                try:
                    gs.install_status = f"查找 dxcam: {name}..."
                    gs.overlay_update_event.set()
                except Exception:
                    pass

                wheel_url, err = _find_dxcam_wheel_url(url)
                if not wheel_url:
                    log(f"dxcam 从 {name} 查找失败: {err}")
                    continue

                log(f"正在下载 dxcam ({name})...")
                success, err = _download_and_install_wheel(wheel_url, dest_dir)
                if not success:
                    log(f"dxcam 从 {name} 安装失败: {err}")
                    continue

                importlib.invalidate_caches()
                import capture_dxgi
                capture_dxgi._DXCAM_AVAILABLE = None
                import lib
                if lib.is_dxgi_available():
                    log("dxcam 安装成功，已切换到 DXGI")
                    gs.capture_method = "DXGI"
                    try:
                        gs.install_status = "dxcam 安装成功，已切换DXGI"
                        gs.install_status_until = time.time() + 3.0
                        gs.overlay_update_event.set()
                    except Exception:
                        pass
                    return
                else:
                    log("dxcam 安装成功但无法初始化")
            except Exception as e:
                log(f"dxcam 从 {name} 安装异常: {e}")

        log("dxcam 安装失败，将使用 GDI 截图方式")
        try:
            gs.install_status = "dxcam 安装失败，使用GDI"
            gs.install_status_until = time.time() + 3.0
            gs.overlay_update_event.set()
        except Exception:
            pass
    except Exception as e:
        try:
            log(f"dxcam 安装线程异常: {e}")
        except Exception:
            pass


def trigger_config_reload():
    """触发配置重载（供外部调用）"""
    try:
        with open(RELOAD_TRIGGER_FILE, 'w', encoding='utf-8') as f:
            f.write(str(time.time()))
        return True
    except Exception as e:
        log(f"触发配置重载失败: {e}")
        return False


def check_and_reload_config():
    """检查并重载配置"""
    global damage_detector, overlap_processor, trigger_conditions

    if not os.path.exists(RELOAD_TRIGGER_FILE):
        return False

    try:
        os.remove(RELOAD_TRIGGER_FILE)
    except Exception:
        pass

    try:
        log("正在重载配置...")

        config_path = os.path.join(_plugin_dir, "config.json")
        gs.cfg.load(config_path)
        gs.config = gs.cfg.plugins
        gs.cached_config = gs.cfg._cache
        gs.PULSE_DATA = gs.cfg.waveform

        gs.strength_values["health_a"] = gs.config.get("health_bar", {}).get("strength", 24)
        gs.strength_values["health_b"] = gs.config.get("health_bar", {}).get("strength_b", 24)
        gs.strength_values["shield_a"] = gs.config.get("shield_bar", {}).get("strength", 20)
        gs.strength_values["shield_b"] = gs.config.get("shield_bar", {}).get("strength_b", 20)

        damage_detector = DamageDetector(_cfg_get)
        overlap_processor = OverlapProcessor(_cfg_get)
        trigger_conditions = TriggerConditions(_cfg_get, debug)
        ocr_validator = OCRValidator()

        gs.multi_char_enabled = gs.cached_config.get("multi_char_enabled", False)
        gs.gamepad_enabled = gs.cached_config.get("gamepad_enabled", True)

        ocr_enabled = gs.cached_config.get("ocr_enabled", False)
        if ocr_enabled:
            ocr_port = gs.cached_config.get("ocr_port", 1395)
            lib.set_ocr_port(ocr_port)

        capture_method_config = gs.cached_config.get("capture_method", "gdi")
        if capture_method_config == "auto":
            capture_method_config = "gdi"
        if capture_method_config == "dxgi":
            if lib.is_dxgi_available():
                gs.capture_method = "DXGI"
            else:
                gs.capture_method = "GDI"
                threading.Thread(target=_install_dxcam_background, daemon=True).start()
        else:
            gs.capture_method = "GDI"

        game_config = gs.config.get("game", {})
        region_config = game_config.get("region", {})
        top_left = lib.parse_coordinate(region_config.get("top_left", [0, 1300]))
        bottom_right = lib.parse_coordinate(region_config.get("bottom_right", [1500, 1500]))
        if isinstance(top_left, list) and len(top_left) >= 2 and isinstance(bottom_right, list) and len(bottom_right) >= 2:
            x = max(0, top_left[0])
            y = max(0, top_left[1])
            w = max(10, bottom_right[0] - top_left[0])
            h = max(10, bottom_right[1] - top_left[1])
            new_region = [int(x), int(y), int(w), int(h)]
        else:
            new_region = monitoring_loop.capture_region
        monitoring_loop.capture_region = new_region
        gs.cached_config["capture_region"] = new_region

        gs.current_health = 100
        gs.current_shield = 0

        log(f"配置已重载 | 截图方式: {gs.capture_method} | OCR: {'开' if ocr_enabled else '关'}")
        return True
    except Exception as e:
        log(f"配置重载失败: {e}")
        return False


gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


# ============================================================
# 日志
# ============================================================

def log(msg_a, lvl="INFO"):
    message = '[挨打就电]: {}'.format(msg_a)
    if gs.server is not None and hasattr(gs.server, 'logger'):
        try:
            logger = gs.server.logger
            if lvl == "SUCCESS": logger.success(message)
            elif lvl == "INFO": logger.info(message)
            elif lvl == "WARNING": logger.warn(message)
            elif lvl == "ERROR": logger.error(message)
            elif lvl == "DEBUG": logger.debug(message)
            return
        except Exception:
            pass
    if gs.msg_queue is not None:
        gs.msg_queue.put({'action': "logger", 'log_level': lvl, 'message': message})


def debug(msg_a):
    if debug_mode:
        log(msg_a, lvl="DEBUG")


# ============================================================
# 脉冲数据
# ============================================================

def get_pulse_duration(pulse_data):
    if isinstance(pulse_data, list):
        return len(pulse_data) * 0.1
    elif isinstance(pulse_data, str):
        try:
            parsed = eval(pulse_data)
            if isinstance(parsed, list):
                return len(parsed) * 0.1
        except:
            pass
    return 0.5


def get_pulse_data(pulse_type):
    if gs.PULSE_DATA and isinstance(gs.PULSE_DATA, dict):
        data = gs.PULSE_DATA.get(f"{pulse_type}_pulse", [])
        if isinstance(data, list) and len(data) > 0:
            return data
    return ["0A0A0A0A64646464"]


# ============================================================
# 截图与检测辅助
# ============================================================

def check_bar_pixel_match(bmp_data, img_width, capture_region, bar_type, position_type):
    pos = gs.cached_config.get(f"{bar_type}_{position_type}", [0, 0])
    colors = gs.cached_config.get(f"{bar_type}_colors", [])
    tolerance = gs.cached_config.get(f"{bar_type}_tolerance", 25)
    if not pos or not colors:
        return False
    pixel = lib.get_pixel_color(bmp_data, pos[0] - capture_region[0], pos[1] - capture_region[1], img_width)
    for color in colors:
        if lib.color_match(pixel, color, tolerance):
            return True
    return False


def check_healthbar_exists(bmp_data, img_width):
    if gs.is_spectating:
        return False, "--------"
    if not gs.cached_config.get("plus_enabled", True):
        gs.has_healthbar = True
        return True, "++++++"
    debug("--check_healthbar_exists--")

    positions = gs.cached_config.get("plus_positions", [])
    colors = gs.cached_config.get("plus_colors", [])
    negative_positions = gs.cached_config.get("plus_negative_positions", [])
    negative_colors = gs.cached_config.get("plus_negative_colors", [])
    tolerance = gs.cached_config.get("plus_tolerance", 30)
    capture_region = gs.cached_config.get("capture_region", [0, 0, 0, 0])

    debug(f"positions: {positions}")
    debug(f"negative_positions: {negative_positions}, type: {type(negative_positions)}")
    debug(f"negative_colors: {negative_colors}")

    if not positions or not colors:
        gs.has_healthbar = False
        return False, "!配置中没有配置点位或颜色!"

    all_match, result_str = lib.check_positions_match(
        bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors=colors
    )
    plus_result = list(result_str)

    if negative_positions and negative_colors:
        _, neg_result_str = lib.check_positions_match(
            bmp_data, negative_positions, negative_colors, capture_region, img_width,
            tolerance, extra_colors=negative_colors
        )
        debug(f"[DEBUG] neg_result_str: {neg_result_str}")
        if '1' in neg_result_str:
            all_match = False

    gs.has_healthbar = all_match
    total_positions = len(positions) + len(negative_positions)
    result_str = ''.join(plus_result)
    result_str = result_str.ljust(total_positions, '0')[:total_positions]
    return gs.has_healthbar, result_str


def check_spectating(bmp_data, img_width):
    debug("--check_spectating--")
    if not gs.cached_config.get("spectate_enabled", True):
        gs.is_spectating = False
        return gs.is_spectating, "0"

    positions = gs.cached_config.get("spectate_positions", [])
    colors = gs.cached_config.get("spectate_colors", [])
    tolerance = gs.cached_config.get("spectate_tolerance", 30)
    capture_region = gs.cached_config.get("capture_region", [0, 0, 0, 0])

    gs.is_spectating, spectate_result, _ = lib.check_positions_count_match(
        bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold=0.75
    )
    return gs.is_spectating, spectate_result


def check_healthbar_ocr(bmp_data, img_width):
    debug("--check_healthbar_ocr--")
    ocr_top_left = gs.cached_config.get("health_ocr_top_left", [0, 0])
    ocr_bottom_right = gs.cached_config.get("health_ocr_bottom_right", [100, 100])

    if not isinstance(ocr_top_left, list) or len(ocr_top_left) < 2:
        gs.has_healthbar = False
        return False, None, 0, 0
    if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
        gs.has_healthbar = False
        return False, None, 0, 0

    capture_region = gs.cached_config.get("capture_region", [0, 0, 0, 0])
    offset_x = capture_region[0] if len(capture_region) >= 1 else 0
    offset_y = capture_region[1] if len(capture_region) >= 2 else 0

    x1 = ocr_top_left[0] - offset_x
    y1 = ocr_top_left[1] - offset_y
    x2 = ocr_bottom_right[0] - offset_x
    y2 = ocr_bottom_right[1] - offset_y

    health_filters = gs.cached_config.get("health_ocr_filters", [])
    health_api_ip = gs.cached_config.get("health_ocr_api_ip", "")
    health_api_data = gs.cached_config.get("health_ocr_api_data", "")

    number, ocr_time, filter_time = lib.ocr_recognize_number(
        bmp_data, x1, y1, x2, y2, img_width, log=log,
        port=gs.cached_config.get("ocr_port", 1395),
        filters=health_filters, parse_color_func=lib.parse_colors,
        api_ip=health_api_ip or None, api_data=health_api_data or None
    )

    if number is not None and number != 0:
        gs.has_healthbar = True
        return True, number, ocr_time, filter_time
    else:
        gs.has_healthbar = False
        return False, None, ocr_time, filter_time


def check_shield_ocr(bmp_data, img_width):
    debug("--check_shield_ocr--")
    ocr_top_left = gs.cached_config.get("shield_ocr_top_left", [0, 0])
    ocr_bottom_right = gs.cached_config.get("shield_ocr_bottom_right", [100, 100])

    if not isinstance(ocr_top_left, list) or len(ocr_top_left) < 2:
        return None, 0, 0
    if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
        return None, 0, 0

    capture_region = gs.cached_config.get("capture_region", [0, 0, 0, 0])
    offset_x = capture_region[0] if len(capture_region) >= 1 else 0
    offset_y = capture_region[1] if len(capture_region) >= 2 else 0

    x1 = ocr_top_left[0] - offset_x
    y1 = ocr_top_left[1] - offset_y
    x2 = ocr_bottom_right[0] - offset_x
    y2 = ocr_bottom_right[1] - offset_y

    shield_filters = gs.cached_config.get("shield_ocr_filters", [])
    shield_api_ip = gs.cached_config.get("shield_ocr_api_ip", "")
    shield_api_data = gs.cached_config.get("shield_ocr_api_data", "")

    number, ocr_time, filter_time = lib.ocr_recognize_number(
        bmp_data, x1, y1, x2, y2, img_width, log=log,
        port=gs.cached_config.get("ocr_port", 1395),
        filters=shield_filters, parse_color_func=lib.parse_colors,
        api_ip=shield_api_ip or None, api_data=shield_api_data or None
    )
    return number, ocr_time, filter_time


def check_health_and_shield(bmp_data, img_width):
    result = {
        "health_dropped": False, "shield_dropped": False,
        "health_color_result": "0", "shield_color_result": "0",
        "health_drop_amount": 0, "shield_drop_amount": 0
    }
    if not gs.has_healthbar:
        return result
    debug("--check_health_and_shield--")

    capture_region = gs.cached_config.get("capture_region", [0, 0, 0, 0])

    if gs.cached_config.get("shield_enabled", False):
        shield_pct, shield_color_result = lib.detect_bar_length(
            bmp_data, img_width,
            gs.cached_config["shield_start"], gs.cached_config["shield_end"],
            gs.cached_config["shield_colors"], gs.cached_config["shield_tolerance"],
            gs.cached_config["shield_sample_points"], capture_region
        )
        shield_pct = min(shield_pct, 100.0)
        if shield_pct < gs.current_shield and gs.has_healthbar:
            shield_drop_amount = gs.current_shield - shield_pct
            gs.current_shield = shield_pct
            ok, _ = trigger_conditions.drop_threshold("shield", shield_drop_amount, True)
            if ok:
                result["shield_dropped"] = True
                result["shield_drop_amount"] = shield_drop_amount
        else:
            gs.current_shield = shield_pct
        result["shield_color_result"] = shield_color_result

    if gs.cached_config.get("health_enabled", False):
        health_pct, health_color_result = lib.detect_bar_length(
            bmp_data, img_width,
            gs.cached_config["health_start"], gs.cached_config["health_end"],
            gs.cached_config["health_colors"], gs.cached_config["health_tolerance"],
            gs.cached_config["health_sample_points"], capture_region
        )
        health_pct = min(health_pct, 100.0)
        if health_pct < gs.current_health and gs.has_healthbar:
            drop_amount = gs.current_health - health_pct
            blocked, _ = trigger_conditions.shield_blocks_health(gs.current_shield)
            if blocked:
                gs.current_health = health_pct
            else:
                gs.current_health = health_pct
                ok, _ = trigger_conditions.drop_threshold("health", drop_amount, True)
                if ok:
                    result["health_dropped"] = True
                    result["health_drop_amount"] = drop_amount
        else:
            gs.current_health = health_pct
        result["health_color_result"] = health_color_result

    return result


# ============================================================
# 电击触发
# ============================================================

def _send_set_strength(channel, strength):
    if gs.server is not None and hasattr(gs.server, 'set_strength'):
        gs.server.set_strength(channel, strength)
    elif gs.msg_queue:
        gs.msg_queue.put({'action': "set_strength", 'channel': channel, 'strength': strength})


def _send_pluses(pulse_data, channel, punish_time):
    if gs.server is not None and hasattr(gs.server, 'send_pluses_message'):
        gs.server.send_pluses_message(pulse_data, channel, punish_time)
    elif gs.msg_queue:
        pluses_str = str(pulse_data) if isinstance(pulse_data, list) else pulse_data
        gs.msg_queue.put({'action': "send_pluses", 'pluses': pluses_str, 'punish_time': punish_time, 'channel': channel})


def _clear_pluses(channel="All"):
    if gs.server is not None and hasattr(gs.server, 'clear_pluses'):
        gs.server.clear_pluses(channel)
    elif gs.msg_queue:
        gs.msg_queue.put({'action': "clear_pluses", 'channel': channel})


async def trigger_electric(strength_a=20, strength_b=20, pulse_type="health", damage_bonus=0):
    """触发一次电击"""
    now = time.time()
    pulse_data = get_pulse_data(pulse_type)
    pulse_duration = get_pulse_duration(pulse_data)

    # Overlap 处理
    base_strength = gs.strength_values.get(f"{pulse_type}_a", 20)
    overlap_add, total_add, proximity, damage_bonus = overlap_processor.compute(
        now, base_strength, damage_bonus, pulse_duration
    )

    # 如果 overlap 启用且在基础脉冲时间内，清除脉冲（不重复发送）
    if now < overlap_processor.base_until and gs.cached_config.get("overlap_enabled", True):
        _clear_pluses("All")

    overlap_max = gs.cached_config.get("overlap_strength_max", 200)
    strength_a = min(strength_a + total_add, overlap_max)
    strength_b = min(strength_b + total_add, overlap_max)

    # 日志
    log_msg = overlap_processor.format_log(damage_bonus, overlap_add, total_add, strength_a, strength_b)
    if log_msg:
        log(log_msg)

    # 感叹号计数
    if now >= overlap_processor.active_until:
        gs.electric_trigger_count = 1
    else:
        gs.electric_trigger_count += 1

    exclamation_marks = "！" * min(gs.electric_trigger_count, 5)
    gs.electric_trigger_message = f"⚡触发!{exclamation_marks}"

    # 发送强度
    if strength_a == strength_b:
        if strength_a != gs.current_strength_a or strength_b != gs.current_strength_b:
            _send_set_strength("All", int(strength_a))
            gs.current_strength_a = strength_a
            gs.current_strength_b = strength_b
    else:
        if strength_a != gs.current_strength_a:
            _send_set_strength("A", int(strength_a))
            gs.current_strength_a = strength_a
        if strength_b != gs.current_strength_b:
            _send_set_strength("B", int(strength_b))
            gs.current_strength_b = strength_b

    # 发送脉冲
    _send_pluses(pulse_data, "All", 1)
    gs.current_electric_strength = max(strength_a, strength_b)

    await asyncio.sleep(0.05)
    gs.current_electric_strength = 0


# ============================================================
# 触发处理流程 (核心重构)
# ============================================================

async def process_shield_drop(shield_drop_amount, bmp_data=None, img_width=None, capture_region=None):
    """处理盾量下降的完整流程"""
    should_trigger = True

    # OCR 末端触发检测
    if bmp_data and gs.cached_config.get("shield_ocr_end_trigger", True):
        should_trigger = not check_bar_pixel_match(bmp_data, img_width, capture_region, "shield", "end")

    # 阈值检测
    should_trigger, _ = trigger_conditions.drop_threshold("shield", shield_drop_amount, should_trigger)

    # 免疫检测
    if trigger_conditions.immune_check(
        gs.multi_char_enabled, gs.switch_immunity_frames,
        gs.healthbar_appear_immunity, gs.switch_value_unchanged, gs.pending_switch_index
    ):
        debug(f"盾条电击被免疫跳过")
        return

    if not should_trigger:
        return

    # 受伤检测
    damage_bonus = damage_detector.apply(shield_drop_amount)

    # 触发电击
    await trigger_electric(
        strength_a=gs.strength_values["shield_a"],
        strength_b=gs.strength_values["shield_b"],
        pulse_type="shield",
        damage_bonus=damage_bonus
    )


async def process_health_drop(health_drop_amount, extra_hp=0, bmp_data=None, img_width=None, capture_region=None):
    """处理血量下降的完整流程"""
    should_trigger = True

    # 盾存在时阻止血量电击
    blocked, block_msg = trigger_conditions.shield_blocks_health(gs.current_shield)
    if blocked:
        debug(block_msg)
        return

    # OCR 末端触发检测
    if bmp_data and gs.cached_config.get("health_ocr_end_trigger", True):
        should_trigger = not check_bar_pixel_match(bmp_data, img_width, capture_region, "health", "end")

    # 阈值检测
    should_trigger, _ = trigger_conditions.drop_threshold("health", health_drop_amount, should_trigger)

    # 免疫检测
    if trigger_conditions.immune_check(
        gs.multi_char_enabled, gs.switch_immunity_frames,
        gs.healthbar_appear_immunity, gs.switch_value_unchanged, gs.pending_switch_index
    ):
        debug(f"血条电击被免疫跳过")
        return

    if not should_trigger:
        return

    # 受伤检测
    damage_bonus = damage_detector.apply(health_drop_amount, extra_hp)

    # 触发电击
    await trigger_electric(
        strength_a=gs.strength_values["health_a"],
        strength_b=gs.strength_values["health_b"],
        pulse_type="health",
        damage_bonus=damage_bonus
    )


# ============================================================
# 多角色切换
# ============================================================

def request_switch_character(new_index):
    if not gs.multi_char_enabled:
        return False
    if new_index < 0 or new_index >= gs.character_count:
        return False
    if new_index == gs.active_character:
        return False
    if not gs.has_healthbar:
        return False

    if gs.switch_value_unchanged:
        gs.switch_value_unchanged = False
        gs.target_character = -1
        gs.switch_immunity_extensions = 0
        debug(f"新切换取消前次未确认切换, active_character仍为{gs.active_character + 1}")

    gs.pending_switch_index = new_index
    gs.switch_delay_counter = gs.switch_delay_frames_config
    debug(f"请求切换到角色 {new_index + 1}, 延迟 {gs.switch_delay_frames_config} 帧")
    return True


def execute_switch_character(new_index):
    if not gs.multi_char_enabled:
        return False
    if new_index < 0 or new_index >= gs.character_count:
        return False
    if new_index == gs.active_character:
        return False

    gs.character_states[gs.active_character] = {
        'health': gs.current_health, 'shield': gs.current_shield,
    }
    gs.pre_switch_health = gs.current_health
    gs.pre_switch_shield = gs.current_shield
    gs.target_character = new_index
    gs.switch_immunity_frames = gs.switch_immunity_frames_config
    gs.switch_value_unchanged = True
    gs.switch_immunity_extensions = 0

    new_state = gs.character_states.get(gs.target_character, {'health': 100, 'shield': 0})
    gs.current_health = new_state['health']
    gs.current_shield = new_state['shield']
    log(f"切换到角色 {gs.target_character + 1} (血:{gs.current_health:.0f} 盾:{gs.current_shield:.0f}) [待确认]")
    return True


def update_multi_char_state():
    """更新多角色状态 (每帧调用)"""
    if not gs.multi_char_enabled:
        return

    if gs.switch_value_unchanged and gs.pre_switch_health is not None:
        if gs.current_health != gs.pre_switch_health or gs.current_shield != gs.pre_switch_shield:
            gs.switch_value_unchanged = False
            gs.switch_immunity_frames = max(gs.switch_immunity_frames, 3)
            gs.active_character = gs.target_character
            gs.target_character = -1
            log(f"切换确认: 角色{gs.active_character + 1} (血:{gs.current_health:.0f} 盾:{gs.current_shield:.0f})")

    if gs.pending_switch_index >= 0:
        gs.switch_delay_counter -= 1
        if gs.switch_delay_counter <= 0:
            execute_switch_character(gs.pending_switch_index)
            gs.pending_switch_index = -1
            gs.switch_delay_counter = 0

    if gs.switch_immunity_frames > 0 or gs.switch_value_unchanged:
        saved_state = gs.character_states.get(gs.active_character, {'health': 100, 'shield': 0})
        gs.current_health = saved_state['health']
        gs.current_shield = saved_state['shield']

    if gs.switch_immunity_frames > 0:
        gs.switch_immunity_frames -= 1
    elif gs.switch_value_unchanged and gs.target_character >= 0:
        if gs.switch_immunity_extensions < gs.switch_max_extensions:
            gs.switch_immunity_extensions += 1
            gs.switch_immunity_frames = 1
            debug(f"免疫帧耗尽但数值未变, 延长免疫 ({gs.switch_immunity_extensions}/{gs.switch_max_extensions})")
        else:
            gs.switch_value_unchanged = False
            gs.target_character = -1
            gs.switch_immunity_extensions = 0
            saved_state = gs.character_states.get(gs.active_character, {'health': 100, 'shield': 0})
            gs.current_health = saved_state['health']
            gs.current_shield = saved_state['shield']
            log(f"切换失败, 保持角色{gs.active_character + 1}")

    gs.healthbar_appear_immunity = False
    gs.prev_has_healthbar = gs.has_healthbar
    gs.character_states[gs.active_character] = {
        'health': gs.current_health, 'shield': gs.current_shield,
    }


# ============================================================
# 监控主循环
# ============================================================

async def monitoring_loop():
    game_config = gs.config.get("game", {})
    region_config = game_config.get("region", {})
    top_left = lib.parse_coordinate(region_config.get("top_left", [0, 1300]))
    bottom_right = lib.parse_coordinate(region_config.get("bottom_right", [1500, 1500]))

    if not isinstance(top_left, list) or len(top_left) < 2 or not isinstance(bottom_right, list) or len(bottom_right) < 2:
        x, y, width, height = 0, 1300, 1500, 200
    else:
        x = max(0, top_left[0])
        y = max(0, top_left[1])
        width = max(10, bottom_right[0] - top_left[0])
        height = max(10, bottom_right[1] - top_left[1])

    capture_region = [int(x), int(y), int(width), int(height)]
    monitoring_loop.capture_region = capture_region
    monitoring_loop.last_capture_time = 0
    gs.cached_config["capture_region"] = capture_region
    log(f"设置截图区域: {capture_region} (窗口相对坐标)")

    frame_counter = 0
    reload_check_counter = 0

    while not gs.stop_event.is_set():
        if not gs.is_monitoring:
            await asyncio.sleep(0.1)
            continue

        loop_start = time.time()
        scan_interval = gs.config.get("scan_interval", 0.1)

        reload_check_counter += 1
        if reload_check_counter >= 10:
            reload_check_counter = 0
            check_and_reload_config()

        capture_region = monitoring_loop.capture_region

        try:
            await _process_frame(capture_region)
        except Exception as e:
            log(f"检测出错: {e}")

        # 持续处理 overlap 回落
        now = time.time()
        overlap_processor.reset_if_expired(now)
        overlap_processor.apply_decay(now)

        # 更新悬浮窗
        frame_counter += 1
        if frame_counter >= 1:
            frame_counter = 0
            try:
                gs.overlay_update_event.set()
            except Exception:
                pass

        update_multi_char_state()

        elapsed = time.time() - loop_start
        sleep_time = max(0.02, scan_interval - elapsed)
        await asyncio.sleep(sleep_time)


async def _process_frame(capture_region):
    """处理单帧截图"""
    t1 = time.time()
    if gs.capture_method == "DXGI":
        bmp_data, rx, ry, rw, rh, img_width = lib.capture_dxgi_fast(capture_region, hwnd=gs.game_hwnd)
        if bmp_data is None:
            bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region, hwnd=gs.game_hwnd)
    else:
        bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region, hwnd=gs.game_hwnd)
    current_capture_time = (time.time() - t1) * 1000
    monitoring_loop.last_capture_time = current_capture_time

    ocr_enabled = gs.cached_config.get("ocr_enabled", False)

    if ocr_enabled:
        await _process_ocr_frame(bmp_data, img_width, capture_region, current_capture_time)
    else:
        await _process_pixel_frame(bmp_data, img_width, capture_region)


async def _process_ocr_frame(bmp_data, img_width, capture_region, current_capture_time):
    """OCR 模式帧处理"""
    ocr_total_time = 0
    filter_total_time = 0

    is_spectating, spectate_result = check_spectating(bmp_data, img_width)
    monitoring_loop.spectate_result = spectate_result

    if is_spectating:
        monitoring_loop.plus_result = "OCR"
        monitoring_loop.health_color_result = "0"
        monitoring_loop.shield_color_result = "0"
        monitoring_loop.ocr_total_time = 0
        monitoring_loop.filter_total_time = 0
        return

    has_healthbar, health_number, health_ocr_time, health_filter_time = check_healthbar_ocr(bmp_data, img_width)
    ocr_total_time += health_ocr_time
    filter_total_time += health_filter_time

    pre_detected_shield = None
    if not has_healthbar and gs.cached_config.get("ocr_health_shield_detect", False) and gs.cached_config.get("shield_enabled", False):
        shield_number, shield_ocr_time, shield_filter_time = check_shield_ocr(bmp_data, img_width)
        ocr_total_time += shield_ocr_time
        filter_total_time += shield_filter_time
        if shield_number is not None and shield_number != 0:
            has_healthbar = True
            pre_detected_shield = shield_number
            debug(f"血量OCR未识别到，但盾量OCR识别到{shield_number}，判定血条存在")

    if gs.multi_char_enabled and has_healthbar and not gs.prev_has_healthbar:
        gs.healthbar_appear_immunity = True
        debug("血条突然出现(OCR)，1帧免疫电击")

    monitoring_loop.plus_result = "OCR"
    monitoring_loop.ocr_total_time = ocr_total_time
    monitoring_loop.filter_total_time = filter_total_time

    if not has_healthbar:
        monitoring_loop.health_color_result = "0"
        monitoring_loop.shield_color_result = "0"
        _check_ocr_performance(ocr_total_time, filter_total_time, current_capture_time)
        return

    # 处理盾条
    validated_shield = gs.current_shield
    if gs.cached_config.get("shield_enabled", False):
        shield_number = pre_detected_shield
        if shield_number is None:
            shield_number, shield_ocr_time, shield_filter_time = check_shield_ocr(bmp_data, img_width)
            ocr_total_time += shield_ocr_time
            filter_total_time += shield_filter_time

        if shield_number is not None:
            shield_valid, validated_shield = ocr_validator.validate('shield', shield_number, gs.current_shield)
            if shield_valid and validated_shield < gs.current_shield:
                shield_drop_amount = gs.current_shield - validated_shield
                await process_shield_drop(
                    shield_drop_amount, bmp_data, img_width, capture_region
                )
            if shield_valid:
                gs.current_shield = max(0, validated_shield)
            monitoring_loop.shield_color_result = str(validated_shield) if validated_shield else "0"
        else:
            validated_shield = gs.current_shield
            monitoring_loop.shield_color_result = "0"
    else:
        monitoring_loop.shield_color_result = "0"
        gs.current_shield = 0
        validated_shield = 0

    # 处理血量
    if health_number is not None:
        health_valid, validated_health = ocr_validator.validate('health', health_number, gs.current_health)
        if health_valid and validated_health < gs.current_health:
            health_drop_amount = gs.current_health - validated_health
            extra_hp = (gs.current_shield - validated_shield) if gs.current_shield > validated_shield else 0
            await process_health_drop(
                health_drop_amount, extra_hp, bmp_data, img_width, capture_region
            )
        if health_valid:
            gs.current_health = max(0, validated_health)
        monitoring_loop.health_color_result = str(validated_health) if validated_health else "0"
    else:
        monitoring_loop.health_color_result = "0"

    _check_ocr_performance(ocr_total_time, filter_total_time, current_capture_time)


async def _process_pixel_frame(bmp_data, img_width, capture_region):
    """像素检测模式帧处理"""
    has_healthbar, plus_result = check_healthbar_exists(bmp_data, img_width)
    is_spectating, spectate_result = check_spectating(bmp_data, img_width)

    if gs.multi_char_enabled and has_healthbar and not gs.prev_has_healthbar:
        gs.healthbar_appear_immunity = True
        debug("血条突然出现，1帧免疫电击")

    monitoring_loop.plus_result = plus_result
    monitoring_loop.spectate_result = spectate_result
    monitoring_loop.ocr_warning = ""

    if not has_healthbar or is_spectating:
        monitoring_loop.health_color_result = "0"
        monitoring_loop.shield_color_result = "0"
        return

    result = check_health_and_shield(bmp_data, img_width)
    monitoring_loop.health_color_result = result.get("health_color_result", "0")
    monitoring_loop.shield_color_result = result.get("shield_color_result", "0")

    if result["health_dropped"]:
        extra_hp = result.get("shield_drop_amount", 0) if result.get("shield_dropped", False) else 0
        await process_health_drop(result.get("health_drop_amount", 0), extra_hp)
    elif result["shield_dropped"]:
        await process_shield_drop(result.get("shield_drop_amount", 0))


def _check_ocr_performance(ocr_total_time, filter_total_time, current_capture_time):
    scan_interval_sec = gs.config.get("scan_interval", 0.1)
    if scan_interval_sec > 0 and (ocr_total_time / 1000 + current_capture_time / 1000) > scan_interval_sec * 0.8:
        monitoring_loop.ocr_warning = f"!ocr性能瓶颈: {scan_interval_sec:.3f}s < {ocr_total_time/1000:.3f}s+{current_capture_time/1000:.3f}s"
    else:
        monitoring_loop.ocr_warning = ""


# ============================================================
# 按键监听
# ============================================================

def on_toggle_monitoring():
    gs.is_monitoring = not gs.is_monitoring
    if gs.is_monitoring:
        log("监控已开启 - 持续检测血条")
    else:
        log("监控已关闭")


def check_key_state(vk_code):
    return is_key_down(vk_code)


def key_monitor_loop():
    toggle_key_str = gs.config.get("toggle_key", "f9").lower()
    setting_key_str = gs.config.get("setting_mode_key", "f10").lower()
    overlay_toggle_key_str = gs.config.get("overlay_toggle_key", "f6").lower()

    key_map = {"f9": VK_F9, "f10": VK_F10, "f8": VK_F8, "f7": VK_F7, "f6": VK_F6}
    toggle_key = key_map.get(toggle_key_str, VK_F9)
    setting_key = key_map.get(setting_key_str, VK_F10)
    overlay_toggle_key = key_map.get(overlay_toggle_key_str, VK_F6)

    toggle_pressed = False
    setting_pressed = False
    overlay_toggle_pressed = False
    up_pressed = False
    down_pressed = False
    left_pressed = False
    right_pressed = False
    char_key_pressed = [False] * len(gs.character_key_codes)
    gamepad_prev_buttons = 0
    gamepad_char_pressed = [False] * len(gs.character_key_codes)

    while not gs.stop_event.is_set():
        toggle_state = check_key_state(toggle_key)
        setting_state = check_key_state(setting_key)
        overlay_toggle_state = check_key_state(overlay_toggle_key)
        up_state = check_key_state(VK_UP)
        down_state = check_key_state(VK_DOWN)
        left_state = check_key_state(VK_LEFT)
        right_state = check_key_state(VK_RIGHT)

        if toggle_state and not toggle_pressed:
            toggle_pressed = True
            on_toggle_monitoring()
        elif not toggle_state:
            toggle_pressed = False

        if setting_state and not setting_pressed:
            setting_pressed = True
            gs.setting_mode = not gs.setting_mode
            if gs.setting_mode:
                gs.setting_target = 0
                log("进入设置模式 | 左右切换目标 | 上下调整强度")
            else:
                log("退出设置模式")
            gs.setting_event.set()
        elif not setting_state:
            setting_pressed = False

        if overlay_toggle_state and not overlay_toggle_pressed:
            overlay_toggle_pressed = True
            overlay_event.set()
        elif not overlay_toggle_state:
            overlay_toggle_pressed = False

        if gs.setting_mode:
            targets = ["health_a", "health_b", "shield_a", "shield_b"]
            if up_state and not up_pressed:
                up_pressed = True
                if gs.setting_target < len(targets):
                    target = targets[gs.setting_target]
                    gs.strength_values[target] = min(200, gs.strength_values[target] + 1)
                    log(f"{target} 强度增加到 {gs.strength_values[target]}")
                    gs.setting_event.set()
            elif not up_state:
                up_pressed = False

            if down_state and not down_pressed:
                down_pressed = True
                if gs.setting_target < len(targets):
                    target = targets[gs.setting_target]
                    gs.strength_values[target] = max(0, gs.strength_values[target] - 1)
                    log(f"{target} 强度减少到 {gs.strength_values[target]}")
                    gs.setting_event.set()
            elif not down_state:
                down_pressed = False

            if left_state and not left_pressed:
                left_pressed = True
                gs.setting_target = (gs.setting_target - 1) % 4
                gs.setting_event.set()
            elif not left_state:
                left_pressed = False

            if right_state and not right_pressed:
                right_pressed = True
                gs.setting_target = (gs.setting_target + 1) % 4
                gs.setting_event.set()
            elif not right_state:
                right_pressed = False

        if gs.multi_char_enabled:
            for i, vk_code in enumerate(gs.character_key_codes):
                if i < len(char_key_pressed):
                    key_state = check_key_state(vk_code)
                    if key_state and not char_key_pressed[i]:
                        char_key_pressed[i] = True
                        request_switch_character(i)
                    elif not key_state:
                        char_key_pressed[i] = False

            if gs.gamepad_enabled and gs.gamepad_button_codes:
                gamepad_buttons = lib.read_xinput_buttons(0)
                for i in range(min(gs.character_count, len(gs.gamepad_button_codes))):
                    try:
                        btn = int(str(gs.gamepad_button_codes[i]), 0)
                    except Exception:
                        continue
                    is_pressed = (gamepad_buttons & btn) != 0
                    was_pressed = (gamepad_prev_buttons & btn) != 0
                    if is_pressed and not was_pressed and i < len(gamepad_char_pressed):
                        gamepad_char_pressed[i] = True
                        request_switch_character(i)
                    if not is_pressed and i < len(gamepad_char_pressed):
                        gamepad_char_pressed[i] = False
                gamepad_prev_buttons = gamepad_buttons

        time.sleep(0.02)


# ============================================================
# 悬浮窗
# ============================================================

overlay_event = threading.Event()
overlay_visible = True
_overlay_window = None


def _get_monitoring_attrs():
    return {
        'last_capture_time': getattr(monitoring_loop, 'last_capture_time', 0),
        'plus_result': getattr(monitoring_loop, 'plus_result', ''),
        'spectate_result': getattr(monitoring_loop, 'spectate_result', ''),
        'health_color_result': getattr(monitoring_loop, 'health_color_result', '0'),
        'shield_color_result': getattr(monitoring_loop, 'shield_color_result', '0'),
        'ocr_warning': getattr(monitoring_loop, 'ocr_warning', ''),
        'ocr_total_time': getattr(monitoring_loop, 'ocr_total_time', 0),
        'filter_total_time': getattr(monitoring_loop, 'filter_total_time', 0),
    }


def create_overlay_window():
    global _overlay_window
    _overlay_window = OverlayWindow(gs, _get_monitoring_attrs, lambda: overlap_processor)
    _overlay_window.create(
        toggle_event=overlay_event,
        setting_event=gs.setting_event,
        stop_event=gs.stop_event,
        on_log=log,
    )



# ============================================================
# 调试截图
# ============================================================

def take_debug_screenshots():
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_region = gs.cached_config.get("capture_region", None)
    if not capture_region or len(capture_region) < 4:
        game_config = gs.config.get("game", {})
        region_config = game_config.get("region", {})
        top_left = lib.parse_coordinate(region_config.get("top_left", [0, 0]))
        bottom_right = lib.parse_coordinate(region_config.get("bottom_right", [0, 0]))
        if isinstance(top_left, list) and len(top_left) >= 2 and isinstance(bottom_right, list) and len(bottom_right) >= 2:
            capture_region = [max(0, top_left[0]), max(0, top_left[1]),
                              max(10, bottom_right[0] - top_left[0]), max(10, bottom_right[1] - top_left[1])]
    if not capture_region or len(capture_region) < 4:
        log("调试截图: 截图区域未设置")
        return

    if gs.capture_method == "DXGI":
        bmp_data, rx, ry, rw, rh, img_width = lib.capture_dxgi_fast(capture_region, hwnd=gs.game_hwnd)
    else:
        bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region, hwnd=gs.game_hwnd)
    if not bmp_data or len(bmp_data) == 0:
        log("调试截图: 截图失败，数据为空")
        return

    base_path = os.path.abspath(os.path.dirname(__file__))
    screenshot_dir = os.path.join(base_path, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    lib.save_screenshot_sync(bmp_data, rw, rh, f"debug_region_{timestamp}.png")
    log(f"调试截图-区域: {os.path.join(screenshot_dir, f'debug_region_{timestamp}.png')} ({rw}x{rh})")

    if gs.capture_method == "DXGI":
        full_bmp = lib.capture_dxgi_fast(hwnd=gs.game_hwnd)
    else:
        full_bmp = lib.capture_screen_fast(hwnd=gs.game_hwnd)
    if full_bmp and len(full_bmp) > 0:
        lib.save_screenshot_sync(full_bmp[0], full_bmp[3], full_bmp[4], f"debug_full_{timestamp}.png")
        log(f"调试截图-全窗口: {os.path.join(screenshot_dir, f'debug_full_{timestamp}.png')} ({full_bmp[3]}x{full_bmp[4]})")


# ============================================================
# 入口
# ============================================================

async def main(put_server, data, loggerr=None):
    global damage_detector, overlap_processor, trigger_conditions, ocr_validator
    global key_monitor_thread

    gs.server = put_server
    gs.logger = loggerr
    gs.base_dir = _plugin_dir
    gs.msg_queue = None if hasattr(put_server, 'set_strength') else put_server
    if gs.msg_queue is not None:
        gs.server = None
    gs.stop_event = asyncio.Event()
    gs.main_loop = asyncio.get_event_loop()

    config_path = os.path.join(_plugin_dir, "config.json")
    gs.cfg.load(config_path)

    gs.config = gs.cfg.plugins
    gs.cached_config = gs.cfg._cache
    gs.PULSE_DATA = gs.cfg.waveform

    gs.strength_values["health_a"] = gs.config.get("health_bar", {}).get("strength", 24)
    gs.strength_values["health_b"] = gs.config.get("health_bar", {}).get("strength_b", 24)
    gs.strength_values["shield_a"] = gs.config.get("shield_bar", {}).get("strength", 20)
    gs.strength_values["shield_b"] = gs.config.get("shield_bar", {}).get("strength_b", 20)

    # 初始化模块
    damage_detector = DamageDetector(_cfg_get)
    overlap_processor = OverlapProcessor(_cfg_get)
    trigger_conditions = TriggerConditions(_cfg_get, debug)
    ocr_validator = OCRValidator()

    # 多角色配置
    gs.multi_char_enabled = gs.cached_config.get("multi_char_enabled", False)
    gs.gamepad_enabled = gs.cached_config.get("gamepad_enabled", True)
    character_keys_str = gs.cached_config.get("character_keys_str", "1,2,3")

    if gs.multi_char_enabled:
        key_strs = [k.strip() for k in character_keys_str.split(',') if k.strip()]
        gs.character_key_codes = [CHAR_KEY_MAP[ks] for ks in key_strs if ks in CHAR_KEY_MAP]
        gs.character_count = len(gs.character_key_codes)
        gs.character_states = {i: {'health': 100, 'shield': 0} for i in range(gs.character_count)}
        gs.active_character = 0
        gs.target_character = -1
        gs.switch_immunity_frames = 0
        gs.switch_immunity_frames_config = gs.cached_config.get("switch_immunity_frames", 5)
        gs.switch_delay_frames_config = gs.cached_config.get("switch_delay_frames", 1)
        gs.pending_switch_index = -1
        gs.switch_delay_counter = 0
        gs.switch_value_unchanged = False
        gs.switch_immunity_extensions = 0
        gs.pre_switch_health = None
        gs.pre_switch_shield = None
        gs.prev_has_healthbar = False
        gs.healthbar_appear_immunity = False

        gamepad_buttons_str = gs.cached_config.get("gamepad_buttons_str", "0x1000,0x2000,0x4000,0x8000")
        gs.gamepad_button_codes = []
        for btn_str in gamepad_buttons_str.split(','):
            btn_str = btn_str.strip()
            if btn_str:
                try: gs.gamepad_button_codes.append(int(btn_str, 16))
                except ValueError: log(f"手柄按钮码无效: {btn_str}")

        log(f"多角色模式已启用 | 角色数: {gs.character_count} | 按键: {key_strs} | 手柄: {'开' if gs.gamepad_enabled else '关'} | 手柄按钮: {[hex(b) for b in gs.gamepad_button_codes]} | 免疫帧: {gs.switch_immunity_frames_config} | 延迟帧: {gs.switch_delay_frames_config}")
    else:
        gs.character_count = 0
        gs.character_key_codes = []
        gs.character_states = {}
        log("多角色模式未启用")

    ocr_enabled = gs.cached_config.get("ocr_enabled", False)
    if ocr_enabled:
        ocr_port = gs.cached_config.get("ocr_port", 1395)
        lib.set_ocr_port(ocr_port)
        if lib.check_ocr_server(ocr_port):
            log("OCR服务端已启动")
        else:
            log("警告: OCR服务端启动失败，将回退到传统检测模式")
            gs.cached_config["ocr_enabled"] = False

    # 截图方式选择
    capture_method_config = gs.cached_config.get("capture_method", "gdi")
    if capture_method_config == "auto":
        capture_method_config = "gdi"
    if capture_method_config == "dxgi":
        if lib.is_dxgi_available():
            gs.capture_method = "DXGI"
        else:
            gs.capture_method = "GDI"
            threading.Thread(target=_install_dxcam_background, daemon=True).start()
    else:
        gs.capture_method = "GDI"

    log(f"插件已启动 | 截图方式: {gs.capture_method}")

    gameTitle = gs.config.get("game", {}).get("process_title", "QQ")
    gs.game_hwnd = lib.get_game_window(process_title=gameTitle)
    if gs.game_hwnd is None:
        log("错误: 未找到游戏窗口" + gameTitle)
        return
    else:
        log("游戏窗口已找到" + gameTitle)

    key_monitor_thread = threading.Thread(target=key_monitor_loop, daemon=True)
    key_monitor_thread.start()

    overlay_enabled = gs.config.get("overlay", {}).get("enabled", True)
    if overlay_enabled:
        overlay_thread = threading.Thread(target=create_overlay_window, daemon=True)
        overlay_thread.start()
        log("悬浮窗已启动 (F6切换显示, F10设置模式)")
    else:
        log("悬浮窗已禁用")

    monitoring_task = asyncio.create_task(monitoring_loop())
    log("插件运行中 | F9:开关监控 | F10:设置模式 | 方向键:调整强度")
    try:
        while not gs.stop_event.is_set():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log("主任务已取消")
    finally:
        gs.is_monitoring = False
        monitoring_task.cancel()
        gs.stop_event.set()
        log("监听已关闭")


async def stop():
    gs.is_monitoring = False
    if gs.stop_event:
        gs.stop_event.set()
        lib.release_dxgi()
        log("监听已关闭")


if __name__ == "__main__":
    print("HitElectric 插件 - 请通过惩罚姬主程序加载")
    print("配置工具请运行 HitElectricConfig.exe")
