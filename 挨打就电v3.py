import asyncio
import ctypes
import ctypes.wintypes
import threading
import time
import json
import tkinter as tk
import os
import sys

debug_mode = True

_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

import lib
from config import Config

name = "卡丘-挨打就电"
author = "F_thx"

base_dir = None
PULSE_DATA = None
stop_event = None
msg_queue = None
server = None
logger = None

game_hwnd = None
is_monitoring = False
hwnd = None
cfg = Config()
main_loop = None
overlay_hwnd = None

current_health = 100
current_shield = 0
current_electric_strength = 0
is_spectating = False
has_healthbar = False

multi_char_enabled = False
active_character = 0
target_character = -1
character_count = 0
character_states = {}
switch_immunity_frames = 0
switch_immunity_frames_config = 5
switch_delay_frames_config = 1
pending_switch_index = -1
switch_delay_counter = 0
pre_switch_health = None
pre_switch_shield = None
switch_value_unchanged = False
switch_immunity_extensions = 0
switch_max_extensions = 2

prev_has_healthbar = False
healthbar_appear_immunity = False
character_key_codes = []
gamepad_enabled = False
gamepad_button_codes = []
xinput_dll = None
health_drop_threshold = 0

ocr_health_suspect = False
ocr_shield_suspect = False
ocr_suspected_health_value = None
ocr_suspected_shield_value = None
ocr_health_suspect_count = 0
ocr_shield_suspect_count = 0
OCR_SUSPECT_THRESHOLD = 2

overlay_text = "等待启动... (使用F9启动检测)"
overlay_update_event = threading.Event()

setting_mode = False
setting_target = 0
setting_event = threading.Event()

strength_values = {
    "health_a": 24,
    "health_b": 24,
    "shield_a": 20,
    "shield_b": 20
}

current_strength_a = None
current_strength_b = None

electric_active_until = 0.0
electric_trigger_message = ""
electric_trigger_count = 0

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_RETURN = 0x0D
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27

VK_0 = 0x30
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_4 = 0x34
VK_5 = 0x35
VK_6 = 0x36
VK_7 = 0x37
VK_8 = 0x38
VK_9 = 0x39

CHAR_KEY_MAP = {
    '0': VK_0, '1': VK_1, '2': VK_2, '3': VK_3,
    '4': VK_4, '5': VK_5, '6': VK_6, '7': VK_7,
    '8': VK_8, '9': VK_9,
}

capture_method = "GDI"

def cache_config():
    global config, cached_config
    config = cfg.plugins
    cached_config = cfg._cache

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

def get_health_pulse_data():
    global PULSE_DATA
    if PULSE_DATA and isinstance(PULSE_DATA, dict):
        health_pulse = PULSE_DATA.get("health_pulse", [])
        if isinstance(health_pulse, list) and len(health_pulse) > 0:
            return health_pulse
    return ["0A0A0A0A64646464"]

def get_shield_pulse_data():
    global PULSE_DATA
    if PULSE_DATA and isinstance(PULSE_DATA, dict):
        shield_pulse = PULSE_DATA.get("shield_pulse", [])
        if isinstance(shield_pulse, list) and len(shield_pulse) > 0:
            return shield_pulse
    return ["0A0A0A0A64646464"]

def log(msg_a, lvl="INFO"):
    # 日志系统（兼容 V2 server / 旧版 msg_queue）
    message = '[挨打就电]: {}'.format(msg_a)
    if server is not None and hasattr(server, 'logger'):
        try:
            logger = server.logger
            if lvl == "SUCCESS":
                logger.success(message)
            elif lvl == "INFO":
                logger.info(message)
            elif lvl == "WARNING":
                logger.warn(message)
            elif lvl == "ERROR":
                logger.error(message)
            elif lvl == "DEBUG":
                logger.debug(message)
            return
        except Exception:
            pass
    if msg_queue is not None:
        send_data = {
            'action': "logger",
            'log_level': lvl,
            'message': message
        }
        msg_queue.put(send_data)

def debug(msg_a):
    if debug_mode:
        log(msg_a, lvl="DEBUG")

def count_digit_changes(old_value, new_value):
    """
    计算两个数字之间的位数变化数量
    例如: 80 -> 30, 变化了1位(十位从8变成3)
          18 -> 13, 变化了1位(个位从8变成3)
          83 -> 38, 变化了2位(十位和个位都变了)
    
    Args:
        old_value: 之前的数值
        new_value: 新的数值
        
    Returns:
        int: 变化的位数
    """
    old_str = str(old_value)
    new_str = str(new_value)
    
    # 对齐长度，前面补0
    max_len = max(len(old_str), len(new_str))
    old_str = old_str.zfill(max_len)
    new_str = new_str.zfill(max_len)
    
    changes = 0
    for i in range(max_len):
        if old_str[i] != new_str[i]:
            changes += 1
    
    return changes

def is_suspect_change(old_value, new_value):
    """
    检测是否是需要怀疑的变化
    1. 截断数字：例如 135 -> 35, 135 -> 13, 135 -> 5, 135 -> 1
    2. 突然变为0：例如 135 -> 0
    3. 数字变动不超过2位：例如 80 -> 30(变1位), 18 -> 13(变1位), 但 83 -> 38(变2位)不检测
    
    Args:
        old_value: 之前的数值
        new_value: 新的数值
        
    Returns:
        bool: 是否需要怀疑
    """
    if old_value is None or new_value is None:
        return False
    if old_value <= 0:
        return False
    
    # 情况1：突然变为0
    if new_value == 0:
        return True
    
    # 情况2：截断数字（且变动1位）
    old_str = str(old_value)
    new_str = str(new_value)
    if len(new_str) < len(old_str) and old_str.endswith(new_str):
        return True

    return False

def validate_ocr_value(value_type, new_value, old_value):
    """
    验证OCR数值是否可信
    
    Args:
        value_type: 'health' 或 'shield'
        new_value: 新的OCR识别值
        old_value: 当前存储的值
        
    Returns:
        tuple: (is_valid, final_value)
            - is_valid: 是否可信
            - final_value: 最终应该使用的值
    """
    global ocr_health_suspect, ocr_shield_suspect
    global ocr_suspected_health_value, ocr_suspected_shield_value
    global ocr_health_suspect_count, ocr_shield_suspect_count
    global OCR_SUSPECT_THRESHOLD
    
    if value_type == 'health':
        suspect_flag = ocr_health_suspect
        suspected_value = ocr_suspected_health_value
        suspect_count = ocr_health_suspect_count
    else:
        suspect_flag = ocr_shield_suspect
        suspected_value = ocr_suspected_shield_value
        suspect_count = ocr_shield_suspect_count
    
    # 如果之前没有怀疑，检测是否需要怀疑
    if not suspect_flag:
        if is_suspect_change(old_value, new_value):
            if value_type == 'health':
                ocr_health_suspect = True
                ocr_suspected_health_value = new_value
                ocr_health_suspect_count = 1
            else:
                if new_value == 0:
                    return True, new_value
                else:
                    ocr_shield_suspect = True
                    ocr_suspected_shield_value = new_value
                    ocr_shield_suspect_count = 1
            return False, old_value  # 忽略此次变化，保持原值
        else:
            return True, new_value  # 可信，使用新值
    
    # 如果之前有怀疑，检查这次是否和怀疑的值一致
    else:
        if new_value == suspected_value:
            # 连续相同，增加计数
            suspect_count += 1
            if value_type == 'health':
                ocr_health_suspect_count = suspect_count
            else:
                ocr_shield_suspect_count = suspect_count
            
            # 达到阈值(4帧)，信任此次处理
            if suspect_count >= OCR_SUSPECT_THRESHOLD:
                if value_type == 'health':
                    ocr_health_suspect = False
                    ocr_suspected_health_value = None
                    ocr_health_suspect_count = 0
                else:
                    ocr_shield_suspect = False
                    ocr_suspected_shield_value = None
                    ocr_shield_suspect_count = 0
                return True, new_value  # 可信，使用新值
            else:
                return False, old_value  # 继续观察，保持原值
        else:
            if value_type == 'health':
                ocr_health_suspect = False
                ocr_suspected_health_value = None
                ocr_health_suspect_count = 0
            else:
                ocr_shield_suspect = False
                ocr_suspected_shield_value = None
                ocr_shield_suspect_count = 0
            return True, new_value  # 使用新值
        

def check_healthbar_exists(bmp_data, img_width):
    global has_healthbar
    if is_spectating:
        return False, "--------"

    if not cached_config.get("plus_enabled", True):
        has_healthbar = True
        return True, "++++++"

    debug("--check_healthbar_exists--")


    positions = cached_config.get("plus_positions", [])
    colors = cached_config.get("plus_colors", [])
    negative_positions = cached_config.get("plus_negative_positions", [])
    negative_colors = cached_config.get("plus_negative_colors", [])
    tolerance = cached_config.get("plus_tolerance", 30)
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])

    # 调试日志
    debug(f"positions: {positions}")
    debug(f"negative_positions: {negative_positions}, type: {type(negative_positions)}")
    debug(f"negative_colors: {negative_colors}")

    plus_result = []
    if not positions or not colors:
        has_healthbar = False

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
        # 反向检测：只要有一个反向位置匹配（有'1'），血条就为no
        neg_any_match = '1' in neg_result_str
        debug(f"[DEBUG] neg_any_match: {neg_any_match}")
        if neg_any_match:
            all_match = False

    has_healthbar = all_match
    # 计算总位置数（正向 + 反向），用于确定结果字符串长度
    total_positions = len(positions) + len(negative_positions)
    result_str = ''.join(plus_result)
    # 根据总位置数填充或截断
    result_str = result_str.ljust(total_positions, '0')[:total_positions]
    return has_healthbar, result_str

def check_spectating(bmp_data, img_width):
    global is_spectating
    debug("--check_spectating--")

    if not cached_config.get("spectate_enabled", True):
        is_spectating = False
        return is_spectating, "0"

    positions = cached_config.get("spectate_positions", [])
    colors = cached_config.get("spectate_colors", [])
    tolerance = cached_config.get("spectate_tolerance", 30)
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])

    is_spectating, spectate_result, _ = lib.check_positions_count_match(
        bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold=0.75
    )

    return is_spectating, spectate_result

def detect_bar_length(bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points):
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])
    return lib.detect_bar_length(bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points, capture_region)

def check_health_and_shield(bmp_data, img_width):
    global current_health, current_shield
    result = {"health_dropped": False, "shield_dropped": False, "health_color_result": "0", "shield_color_result": "0"}
    if not has_healthbar:
        return result
    debug("--check_health_and_shield--")

    if cached_config.get("shield_enabled", False):
        shield_pct, shield_color_result = detect_bar_length(
            bmp_data, img_width,
            cached_config["shield_start"], cached_config["shield_end"],
            cached_config["shield_colors"], cached_config["shield_tolerance"],
            cached_config["shield_sample_points"]
        )
        shield_pct = min(shield_pct, 100.0)
        if shield_pct < current_shield and has_healthbar:
            current_shield = shield_pct
            result["shield_dropped"] = True
        else:
            current_shield = shield_pct
        result["shield_color_result"] = shield_color_result

    if cached_config.get("health_enabled", False):
        health_pct, health_color_result = detect_bar_length(
            bmp_data, img_width,
            cached_config["health_start"], cached_config["health_end"],
            cached_config["health_colors"], cached_config["health_tolerance"],
            cached_config["health_sample_points"]
        )
        health_pct = min(health_pct, 100.0)
        if health_pct < current_health and has_healthbar:
            drop_amount = current_health - health_pct
            shield_blocks = cached_config.get("shield_blocks_health", True) and current_shield > 0
            if shield_blocks:
                current_health = health_pct
            else:
                current_health = health_pct
                if drop_amount >= health_drop_threshold:
                    result["health_dropped"] = True
        else:
            current_health = health_pct
        result["health_color_result"] = health_color_result

    return result

def check_healthbar_ocr(bmp_data, img_width):
    """使用OCR检测血条是否存在"""
    global has_healthbar
    
    ocr_top_left = cached_config.get("health_ocr_top_left", [0, 0])
    ocr_bottom_right = cached_config.get("health_ocr_bottom_right", [100, 100])

    debug("--check_healthbar_ocr--")
    
    if not isinstance(ocr_top_left, list) or len(ocr_top_left) < 2:
        has_healthbar = False
        return False, None, 0, 0
    
    if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
        has_healthbar = False
        return False, None, 0, 0
    
    # 获取截图区域偏移
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])
    offset_x = capture_region[0] if len(capture_region) >= 1 else 0
    offset_y = capture_region[1] if len(capture_region) >= 2 else 0
    
    # OCR坐标转换为相对于截图区域的坐标
    x1 = ocr_top_left[0] - offset_x
    y1 = ocr_top_left[1] - offset_y
    x2 = ocr_bottom_right[0] - offset_x
    y2 = ocr_bottom_right[1] - offset_y

    health_filters = cached_config.get("health_ocr_filters", [])
    health_api_ip = cached_config.get("health_ocr_api_ip", "")
    health_api_data = cached_config.get("health_ocr_api_data", "")

    number, ocr_time, filter_time = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=cached_config["ocr_port"],
                                                  filters=health_filters, parse_color_func=lib.parse_colors,
                                                  api_ip=health_api_ip or None, api_data=health_api_data or None)
    
    if number is not None and number != 0:
        has_healthbar = True
        return True, number, ocr_time, filter_time
    else:
        has_healthbar = False
        return False, None, ocr_time, filter_time

def check_shield_ocr(bmp_data, img_width):
    """使用OCR检测盾条"""
    global current_shield
    debug("--check_shield_ocr--")
    
    ocr_top_left = cached_config.get("shield_ocr_top_left", [0, 0])
    ocr_bottom_right = cached_config.get("shield_ocr_bottom_right", [100, 100])
    
    if not isinstance(ocr_top_left, list) or len(ocr_top_left) < 2:
        return None, 0
    
    if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
        return None, 0
    
    # 获取截图区域偏移
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])
    offset_x = capture_region[0] if len(capture_region) >= 1 else 0
    offset_y = capture_region[1] if len(capture_region) >= 2 else 0
    
    # OCR坐标转换为相对于截图区域的坐标
    x1 = ocr_top_left[0] - offset_x
    y1 = ocr_top_left[1] - offset_y
    x2 = ocr_bottom_right[0] - offset_x
    y2 = ocr_bottom_right[1] - offset_y
    
    shield_filters = cached_config.get("shield_ocr_filters", [])
    shield_api_ip = cached_config.get("shield_ocr_api_ip", "")
    shield_api_data = cached_config.get("shield_ocr_api_data", "")
    
    number, ocr_time, filter_time = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=cached_config["ocr_port"],
                                                  filters=shield_filters, parse_color_func=lib.parse_colors,
                                                  api_ip=shield_api_ip or None, api_data=shield_api_data or None)
    
    return number, ocr_time, filter_time

def check_bar_pixel_match(bmp_data, img_width, capture_region, bar_type, position_type):
    """检查条形指定位置(起始/结束)的像素颜色是否匹配
    
    Args:
        bar_type: 'health' 或 'shield'
        position_type: 'start' 或 'end'
    
    Returns:
        bool: 像素颜色是否匹配
    """
    pos = cached_config.get(f"{bar_type}_{position_type}", [0, 0])
    colors = cached_config.get(f"{bar_type}_colors", [])
    tolerance = cached_config.get(f"{bar_type}_tolerance", 25)
    
    if not pos or not colors:
        return False
    
    pixel = lib.get_pixel_color(bmp_data, pos[0] - capture_region[0], pos[1] - capture_region[1], img_width)
    for color in colors:
        if lib.color_match(pixel, color, tolerance):
            return True
    return False

def _send_set_strength(channel, strength):
    if server is not None and hasattr(server, 'set_strength'):
        server.set_strength(channel, strength)
    elif msg_queue:
        msg_queue.put({'action': "set_strength", 'channel': channel, 'strength': strength})

def _send_pluses(pulse_data, channel, punish_time):
    if server is not None and hasattr(server, 'send_pluses_message'):
        server.send_pluses_message(pulse_data, channel, punish_time)
    elif msg_queue:
        pluses_str = str(pulse_data) if isinstance(pulse_data, list) else pulse_data
        msg_queue.put({'action': "send_pluses", 'pluses': pluses_str, 'punish_time': punish_time, 'channel': channel})

def _clear_pluses(channel="All"):
    if server is not None and hasattr(server, 'clear_pluses'):
        server.clear_pluses(channel)
    elif msg_queue:
        msg_queue.put({'action': "clear_pluses", 'channel': channel})

async def trigger_electric(strength_a=20, strength_b=20, pulse_type="health"):
    global current_electric_strength, current_strength_a, current_strength_b, electric_active_until
    global electric_trigger_message, electric_trigger_count

    now = time.time()
    if pulse_type == "health":
        pulse_data = get_health_pulse_data()
    else:
        pulse_data = get_shield_pulse_data()
    pulse_duration = get_pulse_duration(pulse_data)

    # 检查是否是overlap叠加（用于强度增加）
    is_overlap = now < electric_active_until * 2

    if is_overlap and cached_config.get("overlap_enabled", True):
        overlap_add = cached_config.get("overlap_strength_add", 1)
        overlap_max = cached_config.get("overlap_strength_max", 200)
        strength_a = min(strength_a + overlap_add, overlap_max)
        strength_b = min(strength_b + overlap_add, overlap_max)
        _clear_pluses("All")

    # 感叹号计数：electric_active_until过期后重置为1，否则叠加
    if now >= electric_active_until:
        # 上次触发的显示时间已过，这是新的触发
        electric_trigger_count = 1
    else:
        # 还在显示时间内，叠加感叹号
        electric_trigger_count += 1

    # 构建触发信息
    exclamation_marks = "！" * min(electric_trigger_count, 5)  # 最多5个感叹号
    electric_trigger_message = f"⚡触发!{exclamation_marks}"

    if strength_a == strength_b:
        if strength_a != current_strength_a or strength_b != current_strength_b:
            _send_set_strength("All", strength_a)
            current_strength_a = strength_a
            current_strength_b = strength_b
    else:
        if strength_a != current_strength_a:
            _send_set_strength("A", strength_a)
            current_strength_a = strength_a
        if strength_b != current_strength_b:
            _send_set_strength("B", strength_b)
            current_strength_b = strength_b

    _send_pluses(pulse_data, "All", 1)
    current_electric_strength = max(strength_a, strength_b)
    electric_active_until = now + pulse_duration
    await asyncio.sleep(0.05)
    current_electric_strength = 0

async def trigger_electric_health(strength_a=20, strength_b=20):
    await trigger_electric(strength_a, strength_b, "health")

async def trigger_electric_shield(strength_a=20, strength_b=20):
    await trigger_electric(strength_a, strength_b, "shield")

def on_toggle_monitoring():
    global is_monitoring
    is_monitoring = not is_monitoring
    if is_monitoring:
        log("监控已开启 - 持续检测血条")
    else:
        log("监控已关闭")

def check_key_state(vk_code):
    return user32.GetAsyncKeyState(vk_code) & 0x8001 != 0

def request_switch_character(new_index):
    global pending_switch_index, switch_delay_counter
    global multi_char_enabled, switch_value_unchanged
    global switch_immunity_extensions, target_character

    if not multi_char_enabled:
        return False
    if new_index < 0 or new_index >= character_count:
        return False
    if new_index == active_character:
        return False
    if not has_healthbar:
        return False

    if switch_value_unchanged:
        switch_value_unchanged = False
        target_character = -1
        switch_immunity_extensions = 0
        debug(f"新切换取消前次未确认切换, active_character仍为{active_character + 1}")

    pending_switch_index = new_index
    switch_delay_counter = switch_delay_frames_config
    debug(f"请求切换到角色 {new_index + 1}, 延迟 {switch_delay_frames_config} 帧")
    return True

def execute_switch_character(new_index):
    global switch_immunity_frames, target_character
    global current_health, current_shield
    global multi_char_enabled, character_states
    global pre_switch_health, pre_switch_shield, switch_value_unchanged

    if not multi_char_enabled:
        return False
    if new_index < 0 or new_index >= character_count:
        return False
    if new_index == active_character:
        return False

    character_states[active_character] = {
        'health': current_health,
        'shield': current_shield,
    }

    pre_switch_health = current_health
    pre_switch_shield = current_shield

    target_character = new_index
    switch_immunity_frames = switch_immunity_frames_config
    switch_value_unchanged = True
    switch_immunity_extensions = 0

    new_state = character_states.get(target_character, {'health': 100, 'shield': 0})
    current_health = new_state['health']
    current_shield = new_state['shield']

    log(f"切换到角色 {target_character + 1} (血:{current_health:.0f} 盾:{current_shield:.0f}) [待确认]")
    return True

def take_screenshot(prefix="screenshot"):
    global game_hwnd
    """调用 lib.take_screenshot 进行截图"""
    return lib.take_screenshot(prefix, log_func=log, hwnd=game_hwnd)

def take_debug_screenshots():
    """F9开启监控时产出调试截图和OCR输出"""
    global game_hwnd
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    capture_region = cached_config.get("capture_region", None)
    if not capture_region or len(capture_region) < 4:
        game_config = config.get("game", {})
        region_config = game_config.get("region", {})
        top_left = lib.parse_coordinate(region_config.get("top_left", [0, 0]))
        bottom_right = lib.parse_coordinate(region_config.get("bottom_right", [0, 0]))
        if isinstance(top_left, list) and len(top_left) >= 2 and isinstance(bottom_right, list) and len(bottom_right) >= 2:
            x = max(0, top_left[0])
            y = max(0, top_left[1])
            w = max(10, bottom_right[0] - top_left[0])
            h = max(10, bottom_right[1] - top_left[1])
            capture_region = [int(x), int(y), int(w), int(h)]
    
    if not capture_region or len(capture_region) < 4:
        log("调试截图: 截图区域未设置")
        return
    
    bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region, hwnd=game_hwnd)
    if not bmp_data or len(bmp_data) == 0:
        log("调试截图: 截图失败，数据为空")
        return
    
    base_path = os.path.abspath(os.path.dirname(__file__))
    screenshot_dir = os.path.join(base_path, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    
    lib.save_screenshot_sync(bmp_data, rw, rh, f"debug_region_{timestamp}.png")
    log(f"调试截图-区域: {os.path.join(screenshot_dir, f'debug_region_{timestamp}.png')} ({rw}x{rh})")
    
    full_bmp = lib.capture_screen_fast(hwnd=game_hwnd)
    if full_bmp and len(full_bmp) > 0:
        lib.save_screenshot_sync(full_bmp[0], full_bmp[3], full_bmp[4], f"debug_full_{timestamp}.png")
        log(f"调试截图-全窗口: {os.path.join(screenshot_dir, f'debug_full_{timestamp}.png')} ({full_bmp[3]}x{full_bmp[4]})")
    
    ocr_enabled = cached_config.get("ocr_enabled", False)
    if ocr_enabled:
        ocr_port = cached_config.get("ocr_port", 1395)
        
        health_ocr_top_left = cached_config.get("health_ocr_top_left", [0, 0])
        health_ocr_bottom_right = cached_config.get("health_ocr_bottom_right", [100, 100])
        if isinstance(health_ocr_top_left, list) and len(health_ocr_top_left) >= 2 and isinstance(health_ocr_bottom_right, list) and len(health_ocr_bottom_right) >= 2:
            offset_x = capture_region[0]
            offset_y = capture_region[1]
            x1 = health_ocr_top_left[0] - offset_x
            y1 = health_ocr_top_left[1] - offset_y
            x2 = health_ocr_bottom_right[0] - offset_x
            y2 = health_ocr_bottom_right[1] - offset_y
            
            health_filters = cached_config.get("health_ocr_filters", [])
            health_api_ip = cached_config.get("health_ocr_api_ip", "")
            health_api_data = cached_config.get("health_ocr_api_data", "")
            
            ocr_image_result = lib.crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=log, filters=health_filters, parse_color_func=lib.parse_colors)
            if ocr_image_result and ocr_image_result[0]:
                ocr_preview_path = os.path.join(screenshot_dir, f"debug_ocr_health_{timestamp}.png")
                try:
                    with open(ocr_preview_path, 'wb') as f:
                        f.write(ocr_image_result[0])
                    log(f"调试截图-血量OCR预览: {ocr_preview_path}")
                except Exception as e:
                    log(f"调试截图-血量OCR预览保存失败: {e}")
            
            number, ocr_time, _ = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=ocr_port, filters=health_filters, parse_color_func=lib.parse_colors,
                                                            api_ip=health_api_ip or None, api_data=health_api_data or None)
            log(f"调试OCR-血量: 识别结果={number}, 耗时={ocr_time:.3f}s")
        
        shield_enabled = cached_config.get("shield_enabled", False)
        if shield_enabled:
            shield_ocr_top_left = cached_config.get("shield_ocr_top_left", [0, 0])
            shield_ocr_bottom_right = cached_config.get("shield_ocr_bottom_right", [100, 100])
            if isinstance(shield_ocr_top_left, list) and len(shield_ocr_top_left) >= 2 and isinstance(shield_ocr_bottom_right, list) and len(shield_ocr_bottom_right) >= 2:
                offset_x = capture_region[0]
                offset_y = capture_region[1]
                x1 = shield_ocr_top_left[0] - offset_x
                y1 = shield_ocr_top_left[1] - offset_y
                x2 = shield_ocr_bottom_right[0] - offset_x
                y2 = shield_ocr_bottom_right[1] - offset_y
                
                shield_filters = cached_config.get("shield_ocr_filters", [])
                shield_api_ip = cached_config.get("shield_ocr_api_ip", "")
                shield_api_data = cached_config.get("shield_ocr_api_data", "")
                
                ocr_image_result = lib.crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=log, filters=shield_filters, parse_color_func=lib.parse_colors)
                if ocr_image_result and ocr_image_result[0]:
                    ocr_preview_path = os.path.join(screenshot_dir, f"debug_ocr_shield_{timestamp}.png")
                    try:
                        with open(ocr_preview_path, 'wb') as f:
                            f.write(ocr_image_result[0])
                        log(f"调试截图-盾量OCR预览: {ocr_preview_path}")
                    except Exception as e:
                        log(f"调试截图-盾量OCR预览保存失败: {e}")
                
                number, ocr_time, _ = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=ocr_port, filters=shield_filters, parse_color_func=lib.parse_colors,
                                                                api_ip=shield_api_ip or None, api_data=shield_api_data or None)
                log(f"调试OCR-盾量: 识别结果={number}, 耗时={ocr_time:.3f}s")

def key_monitor_loop():
    global is_monitoring, setting_mode, setting_target
    global character_key_codes, multi_char_enabled, gamepad_enabled

    toggle_key_str = config.get("toggle_key", "f9").lower()
    setting_key_str = config.get("setting_mode_key", "f10").lower()
    overlay_toggle_key_str = config.get("overlay_toggle_key", "f6").lower()

    key_map = {
        "f9": VK_F9,
        "f10": VK_F10,
        "f8": VK_F8,
        "f7": VK_F7,
        "f6": VK_F6
    }

    toggle_key = key_map.get(toggle_key_str, VK_F9)
    setting_key = key_map.get(setting_key_str, VK_F10)
    overlay_toggle_key = key_map.get(overlay_toggle_key_str, VK_F6)

    toggle_pressed = False
    setting_pressed = False
    overlay_toggle_pressed = False
    f7_pressed = False
    up_pressed = False
    down_pressed = False
    left_pressed = False
    right_pressed = False

    char_key_pressed = [False] * len(character_key_codes)

    gamepad_prev_buttons = 0
    gamepad_char_pressed = [False] * len(character_key_codes)

    while not stop_event.is_set():
        toggle_state = check_key_state(toggle_key)
        setting_state = check_key_state(setting_key)
        overlay_toggle_state = check_key_state(overlay_toggle_key)
        f7_state = check_key_state(VK_F7)
        up_state = check_key_state(VK_UP)
        down_state = check_key_state(VK_DOWN)
        left_state = check_key_state(VK_LEFT)
        right_state = check_key_state(VK_RIGHT)

        if toggle_state and not toggle_pressed:
            toggle_pressed = True
            on_toggle_monitoring()
            if is_monitoring:
                threading.Thread(target=take_debug_screenshots, daemon=True).start()
        elif not toggle_state:
            toggle_pressed = False

        if setting_state and not setting_pressed:
            setting_pressed = True
            setting_mode = not setting_mode
            if setting_mode:
                setting_target = 0
                log("进入设置模式 | 左右切换目标 | 上下调整强度")
            else:
                log("退出设置模式")
            setting_event.set()
        elif not setting_state:
            setting_pressed = False

        if overlay_toggle_state and not overlay_toggle_pressed:
            overlay_toggle_pressed = True
            overlay_event.set()
        elif not overlay_toggle_state:
            overlay_toggle_pressed = False

        if setting_mode:
            if up_state and not up_pressed:
                up_pressed = True
                targets = ["health_a", "health_b", "shield_a", "shield_b"]
                if setting_target < len(targets):
                    target = targets[setting_target]
                    strength_values[target] = min(200, strength_values[target] + 1)
                    log(f"{target} 强度增加到 {strength_values[target]}")
                    setting_event.set()
            elif not up_state:
                up_pressed = False

            if down_state and not down_pressed:
                down_pressed = True
                targets = ["health_a", "health_b", "shield_a", "shield_b"]
                if setting_target < len(targets):
                    target = targets[setting_target]
                    strength_values[target] = max(0, strength_values[target] - 1)
                    log(f"{target} 强度减少到 {strength_values[target]}")
                    setting_event.set()
            elif not down_state:
                down_pressed = False

            if left_state and not left_pressed:
                left_pressed = True
                setting_target = (setting_target - 1) % 4
                setting_event.set()
            elif not left_state:
                left_pressed = False

            if right_state and not right_pressed:
                right_pressed = True
                setting_target = (setting_target + 1) % 4
                setting_event.set()
            elif not right_state:
                right_pressed = False

        if multi_char_enabled:
            for i, vk_code in enumerate(character_key_codes):
                if i < len(char_key_pressed):
                    key_state = check_key_state(vk_code)
                    if key_state and not char_key_pressed[i]:
                        char_key_pressed[i] = True
                        request_switch_character(i)
                    elif not key_state:
                        char_key_pressed[i] = False

            if gamepad_enabled and gamepad_button_codes:
                gamepad_buttons = lib.read_xinput_buttons(0)

                for i in range(min(character_count, len(gamepad_button_codes))):
                    try:
                        btn = int(str(gamepad_button_codes[i]), 0)
                    except Exception:
                        continue
                    
                    is_pressed = (gamepad_buttons & btn) != 0
                    was_pressed = (gamepad_prev_buttons & btn) != 0

                    if is_pressed and not was_pressed:
                        if i < len(gamepad_char_pressed):
                            gamepad_char_pressed[i] = True
                            request_switch_character(i)

                    if not is_pressed:
                        if i < len(gamepad_char_pressed):
                            gamepad_char_pressed[i] = False

                gamepad_prev_buttons = gamepad_buttons

        time.sleep(0.02)

overlay_event = threading.Event()
overlay_visible = True

def create_overlay_window():
    global overlay_hwnd, overlay_text, overlay_update_event, overlay_visible

    overlay_text = "等待启动..."

    log("启动 tkinter 悬浮窗...")

    root = tk.Tk()
    root.title("HitElectric Status")

    window_width = 1500
    window_height = 40
    window_x = 10
    window_y = 10

    root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-transparentcolor', 'black')
    root.configure(bg='black')

    label = tk.Label(
        root,
        text=overlay_text,
        bg='black',
        fg='lime',
        font=('Consolas', 10, 'bold'),
        justify=tk.LEFT,
        anchor='w',
        padx=5,
        pady=5
    )
    label.pack(fill=tk.BOTH, expand=True)

    overlay_hwnd = root
    log(f"悬浮窗已创建")

    def update_display():
        try:
            if stop_event.is_set():
                try:
                    root.destroy()
                except:
                    pass
                return

            global overlay_visible

            if overlay_event.is_set():
                overlay_event.clear()
                overlay_visible = not overlay_visible
                try:
                    if overlay_visible:
                        root.deiconify()
                    else:
                        root.withdraw()
                except Exception as e:
                    pass

            if setting_event.is_set():
                setting_event.clear()
                update_label_text()

            if overlay_update_event.is_set():
                overlay_update_event.clear()
                update_label_text()

            root.after(100, update_display)
        except Exception as e:
            try:
                root.after(100, update_display)
            except:
                pass

    def update_label_text():
        try:
            targets = ["health_a", "health_b", "shield_a", "shield_b"]

            parts = []
            for i, target in enumerate(targets):
                value = strength_values[target]
                if setting_mode and i == setting_target:
                    parts.append(f">{value}<")
                else:
                    parts.append(f"{value}")

            healthbar_status = 'yes' if has_healthbar else 'no'
            spectating_status = 'yes' if is_spectating else 'no'

            char_info = ""
            if multi_char_enabled:
                if switch_value_unchanged and target_character >= 0:
                    char_info = f" 角色{active_character+1}→{target_character+1}/{character_count}"
                else:
                    char_info = f" 角色{active_character+1}/{character_count}"
                if pending_switch_index >= 0:
                    char_info += f"[延迟{switch_delay_counter}]"
                if switch_immunity_frames > 0:
                    char_info += f"[免疫{switch_immunity_frames}]"
                if switch_value_unchanged:
                    char_info += "[待确认]"
                if switch_immunity_extensions > 0:
                    char_info += f"[延长{switch_immunity_extensions}]"
                if healthbar_appear_immunity:
                    char_info += "[出现免疫]"

            try:
                last_capture_time = getattr(monitoring_loop, 'last_capture_time', 0)
            except:
                last_capture_time = 0

            try:
                health_val = current_health
                shield_val = current_shield
            except:
                health_val = 0
                shield_val = 0

            try:
                plus_result = getattr(monitoring_loop, 'plus_result', '00000000')
                spectate_result = getattr(monitoring_loop, 'spectate_result', '0004')
                health_color_result = getattr(monitoring_loop, 'health_color_result', '0')
                shield_color_result = getattr(monitoring_loop, 'shield_color_result', '0')
                ocr_warning = getattr(monitoring_loop, 'ocr_warning', '')
                ocr_total_time = getattr(monitoring_loop, 'ocr_total_time', 0)
                filter_total_time = getattr(monitoring_loop, 'filter_total_time', 0)
            except:
                plus_result = '00000000'
                spectate_result = '0000'
                health_color_result = '0'
                shield_color_result = '0'
                ocr_warning = ''
                ocr_total_time = 0
                filter_total_time = 0

            # 构建延迟显示字符串（ocr_total_time和filter_total_time是秒，需要转换为毫秒）
            delay_str = f"{last_capture_time:.1f}ms"
            if filter_total_time > 0:
                delay_str += f" + {filter_total_time*1000:.1f}ms(滤镜)"
            if ocr_total_time > 0:
                delay_str += f" + {ocr_total_time*1000:.0f}ms(ocr)"
            
            # 检查是否显示触发信息（在 electric_active_until 时间内显示）
            global electric_trigger_message, electric_active_until
            trigger_info = ""
            if electric_trigger_message and time.time() < electric_active_until:
                trigger_info = f" {electric_trigger_message}"
            else:
                # 过期后清空触发信息
                electric_trigger_message = ""
            
            status_line = f"[{capture_method}] 血条:{healthbar_status} 观战:{spectating_status} 血:{health_val:.0f} 盾:{shield_val:.0f}{char_info} 延迟:{delay_str}{trigger_info}"
            detail_line = f"| {plus_result},{spectate_result},{health_color_result},{shield_color_result} "
            strength_line = f"| {parts[0]} {parts[1]} | {parts[2]} {parts[3]} |"

            if setting_mode:
                strength_line += "⚙"
            
            if ocr_warning:
                status_line += f" {ocr_warning}"

            display_text = f"{status_line} {detail_line} {strength_line}"

            label.config(text=display_text)
        except Exception as e:
            pass

    update_label_text()
    root.after(50, update_display)

    try:
        root.mainloop()
    except Exception as e:
        log(f"悬浮窗主循环出错: {e}")
    finally:
        overlay_hwnd = None
        log("悬浮窗已关闭")

key_monitor_thread = None

async def monitoring_loop():
    global current_health, current_shield, game_hwnd, last_loop_time
    global switch_immunity_frames, prev_has_healthbar, healthbar_appear_immunity
    global multi_char_enabled, active_character, character_states, target_character
    global pending_switch_index, switch_delay_counter, switch_value_unchanged
    global pre_switch_health, pre_switch_shield
    global switch_immunity_extensions
    global health_drop_threshold
    scan_interval = config.get("scan_interval", 0.1)

    game_config = config.get("game", {})
    region_config = game_config.get("region", {})
    top_left = region_config.get("top_left", [0, 1300])
    bottom_right = region_config.get("bottom_right", [1500, 1500])

    top_left = lib.parse_coordinate(top_left)
    bottom_right = lib.parse_coordinate(bottom_right)

    if not isinstance(top_left, list) or len(top_left) < 2 or not isinstance(bottom_right, list) or len(bottom_right) < 2:
        x, y, width, height = 0, 1300, 1500, 200
    else:
        x = top_left[0]
        y = top_left[1]
        width = bottom_right[0] - top_left[0]
        height = bottom_right[1] - top_left[1]
        x = max(0, x)
        y = max(0, y)
        width = max(10, width)
        height = max(10, height)

    capture_region = [int(x), int(y), int(width), int(height)]
    monitoring_loop.capture_region = capture_region
    monitoring_loop.last_capture_time = 0
    cached_config["capture_region"] = capture_region

    log(f"设置截图区域: {capture_region} (窗口相对坐标)")

    # 帧计数器（每5帧检查一次是否需要更新）
    frame_counter = 0

    while not stop_event.is_set():
        if not is_monitoring:
            await asyncio.sleep(0.1)
            continue
        loopTime1 = time.time()

        loop_start = time.time()

        try:
            t1 = time.time()
            bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region, hwnd=game_hwnd)
            current_capture_time = (time.time() - t1) * 1000
            monitoring_loop.last_capture_time = current_capture_time

            ocr_enabled = cached_config.get("ocr_enabled", False)
            ocr_total_time = 0
            filter_total_time = 0
            
            if ocr_enabled:
                # 检测观战状态（OCR模式下仍然需要）
                is_spectating, spectate_result = check_spectating(bmp_data, img_width)
                monitoring_loop.spectate_result = spectate_result
                
                # 如果正在观战，跳过OCR识别
                if is_spectating:
                    monitoring_loop.plus_result = "OCR"
                    monitoring_loop.health_color_result = "0"
                    monitoring_loop.shield_color_result = "0"
                    monitoring_loop.ocr_total_time = 0
                    monitoring_loop.filter_total_time = 0
                else:
                    has_healthbar, health_number, health_ocr_time, health_filter_time = check_healthbar_ocr(bmp_data, img_width)
                    ocr_total_time += health_ocr_time
                    filter_total_time += health_filter_time
                    
                    pre_detected_shield = None
                    if not has_healthbar and cached_config.get("ocr_health_shield_detect", False) and cached_config.get("shield_enabled", False):
                        shield_number, shield_ocr_time, shield_filter_time = check_shield_ocr(bmp_data, img_width)
                        ocr_total_time += shield_ocr_time
                        filter_total_time += shield_filter_time
                        if shield_number is not None and shield_number != 0:
                            has_healthbar = True
                            pre_detected_shield = shield_number
                            debug(f"血量OCR未识别到，但盾量OCR识别到{shield_number}，判定血条存在")
                    
                    if multi_char_enabled and has_healthbar and not prev_has_healthbar:
                        healthbar_appear_immunity = True
                        debug("血条突然出现(OCR)，1帧免疫电击")
                    
                    monitoring_loop.plus_result = "OCR"
                    monitoring_loop.ocr_total_time = ocr_total_time
                    monitoring_loop.filter_total_time = filter_total_time
                    
                    if has_healthbar:
                        # 处理盾条
                        if cached_config.get("shield_enabled", False):
                            shield_number = None
                            
                            if pre_detected_shield is not None:
                                shield_number = pre_detected_shield
                            else:
                                shield_number, shield_ocr_time, shield_filter_time = check_shield_ocr(bmp_data, img_width)
                                ocr_total_time += shield_ocr_time
                                filter_total_time += shield_filter_time
                            
                            if shield_number is not None:
                                shield_valid, validated_shield = validate_ocr_value('shield', shield_number, current_shield)
                                if shield_valid:
                                    if validated_shield < current_shield:
                                        should_trigger = True
                                        if cached_config.get("shield_ocr_end_trigger", True):
                                            should_trigger = not check_bar_pixel_match(bmp_data, img_width, capture_region, "shield", "end")
                                        if should_trigger:
                                            if multi_char_enabled and (switch_immunity_frames > 0 or healthbar_appear_immunity or switch_value_unchanged or pending_switch_index >= 0):
                                                debug(f"盾条电击被免疫跳过: switch_immunity={switch_immunity_frames}, appear_immunity={healthbar_appear_immunity}, value_unchanged={switch_value_unchanged}, pending={pending_switch_index}")
                                            else:
                                                await trigger_electric_shield(
                                                    strength_a=strength_values["shield_a"],
                                                    strength_b=strength_values["shield_b"]
                                                )
                                    current_shield = max(0, validated_shield)
                                monitoring_loop.shield_color_result = str(validated_shield) if validated_shield else "0"
                            else:
                                monitoring_loop.shield_color_result = "0"
                        else:
                            monitoring_loop.shield_color_result = "0"
                            current_shield = 0
                        
                        # 处理血量
                        if health_number is not None:
                            health_valid, validated_health = validate_ocr_value('health', health_number, current_health)
                            if health_valid:
                                if validated_health < current_health:
                                    health_drop_amount = current_health - validated_health
                                    should_trigger = True
                                    shield_blocks = cached_config.get("shield_blocks_health", True) and current_shield > 0
                                    if shield_blocks:
                                        should_trigger = False
                                        debug(f"盾存在时阻止血量电击 (盾={current_shield})")
                                    if should_trigger and cached_config.get("health_ocr_end_trigger", True):
                                        should_trigger = not check_bar_pixel_match(bmp_data, img_width, capture_region, "health", "end")
                                    if should_trigger and health_drop_threshold > 0:
                                        if health_drop_amount < health_drop_threshold:
                                            should_trigger = False
                                            debug(f"血量减少{health_drop_amount:.0f}未达阈值{health_drop_threshold}, 跳过电击")
                                    if should_trigger:
                                        if multi_char_enabled and (switch_immunity_frames > 0 or healthbar_appear_immunity or switch_value_unchanged or pending_switch_index >= 0):
                                            debug(f"血条电击被免疫跳过: switch_immunity={switch_immunity_frames}, appear_immunity={healthbar_appear_immunity}, value_unchanged={switch_value_unchanged}, pending={pending_switch_index}")
                                        else:
                                            await trigger_electric_health(
                                                strength_a=strength_values["health_a"],
                                                strength_b=strength_values["health_b"]
                                            )
                                current_health = max(0, validated_health)
                            monitoring_loop.health_color_result = str(validated_health) if validated_health else "0"
                        else:
                            monitoring_loop.health_color_result = "0"
                    else:
                        monitoring_loop.health_color_result = "0"
                        monitoring_loop.shield_color_result = "0"
                    
                    scan_interval_sec = config.get("scan_interval", 0.1)

                    if scan_interval_sec > 0 and (ocr_total_time / 1000 + current_capture_time / 1000) > scan_interval_sec * 0.8:
                        monitoring_loop.ocr_warning = f"!ocr性能瓶颈: {scan_interval_sec:.3f}s < {ocr_total_time/1000:.3f}s+{current_capture_time/1000:.3f}s"
                    else:
                        monitoring_loop.ocr_warning = ""
            else:
                has_healthbar, plus_result = check_healthbar_exists(bmp_data, img_width)
                is_spectating, spectate_result = check_spectating(bmp_data, img_width)

                if multi_char_enabled and has_healthbar and not prev_has_healthbar:
                    healthbar_appear_immunity = True
                    debug("血条突然出现，1帧免疫电击")

                monitoring_loop.plus_result = plus_result
                monitoring_loop.spectate_result = spectate_result
                monitoring_loop.ocr_warning = ""

                if has_healthbar and not is_spectating:
                    result = check_health_and_shield(bmp_data, img_width)

                    monitoring_loop.health_color_result = result.get("health_color_result", "0")
                    monitoring_loop.shield_color_result = result.get("shield_color_result", "0")

                    if result["health_dropped"]:
                        if multi_char_enabled and (switch_immunity_frames > 0 or healthbar_appear_immunity or switch_value_unchanged or pending_switch_index >= 0):
                            debug(f"血条电击被免疫跳过: switch_immunity={switch_immunity_frames}, appear_immunity={healthbar_appear_immunity}, value_unchanged={switch_value_unchanged}, pending={pending_switch_index}")
                        else:
                            await trigger_electric_health(
                                strength_a=strength_values["health_a"],
                                strength_b=strength_values["health_b"]
                            )
                    elif result["shield_dropped"]:
                        if multi_char_enabled and (switch_immunity_frames > 0 or healthbar_appear_immunity or switch_value_unchanged or pending_switch_index >= 0):
                            debug(f"盾条电击被免疫跳过: switch_immunity={switch_immunity_frames}, appear_immunity={healthbar_appear_immunity}, value_unchanged={switch_value_unchanged}, pending={pending_switch_index}")
                        else:
                            await trigger_electric_shield(
                                strength_a=strength_values["shield_a"],
                                strength_b=strength_values["shield_b"]
                            )
                    
                else:
                    monitoring_loop.health_color_result = "0"
                    monitoring_loop.shield_color_result = "0"

            # 每5帧检查一次是否需要更新悬浮窗
            frame_counter += 1
            if frame_counter >= 1:
                frame_counter = 0
                try:
                    overlay_update_event.set()
                except Exception as e:
                    log(f"设置悬浮窗更新事件失败{e}")

            if multi_char_enabled:
                if switch_value_unchanged and pre_switch_health is not None:
                    detected_health = current_health
                    detected_shield = current_shield
                    if detected_health != pre_switch_health or detected_shield != pre_switch_shield:
                        switch_value_unchanged = False
                        switch_immunity_frames = max(switch_immunity_frames, 3)
                        active_character = target_character
                        target_character = -1
                        log(f"切换确认: 角色{active_character + 1} (血:{detected_health:.0f} 盾:{detected_shield:.0f})")

                if pending_switch_index >= 0:
                    switch_delay_counter -= 1
                    if switch_delay_counter <= 0:
                        execute_switch_character(pending_switch_index)
                        pending_switch_index = -1
                        switch_delay_counter = 0

                if switch_immunity_frames > 0 or switch_value_unchanged:
                    saved_state = character_states.get(active_character, {'health': 100, 'shield': 0})
                    current_health = saved_state['health']
                    current_shield = saved_state['shield']

                if switch_immunity_frames > 0:
                    switch_immunity_frames -= 1
                elif switch_value_unchanged and target_character >= 0:
                    if switch_immunity_extensions < switch_max_extensions:
                        switch_immunity_extensions += 1
                        switch_immunity_frames = 1
                        debug(f"免疫帧耗尽但数值未变, 延长免疫 ({switch_immunity_extensions}/{switch_max_extensions})")
                    else:
                        switch_value_unchanged = False
                        target_character = -1
                        switch_immunity_extensions = 0
                        saved_state = character_states.get(active_character, {'health': 100, 'shield': 0})
                        current_health = saved_state['health']
                        current_shield = saved_state['shield']
                        log(f"切换失败, 保持角色{active_character + 1}")

                healthbar_appear_immunity = False
                prev_has_healthbar = has_healthbar
                character_states[active_character] = {
                    'health': current_health,
                    'shield': current_shield,
                }
        except Exception as e:
            log(f"检测出错: {e}")

        loopTime2 = time.time()
        last_loop_time = loopTime2 - loopTime1

        elapsed = time.time() - loop_start
        sleep_time = max(0.02, scan_interval - elapsed)
        await asyncio.sleep(sleep_time)

async def main(put_server, data, loggerr=None):
    global msg_queue, stop_event, PULSE_DATA, config, main_loop, is_monitoring, current_health, key_monitor_thread, server, logger, game_hwnd
    global multi_char_enabled, character_count, character_states, character_key_codes, gamepad_enabled, active_character
    global switch_immunity_frames, prev_has_healthbar, healthbar_appear_immunity
    global switch_immunity_frames_config, switch_delay_frames_config
    global pending_switch_index, switch_delay_counter, switch_value_unchanged
    global pre_switch_health, pre_switch_shield, target_character
    global switch_immunity_extensions
    global health_drop_threshold, gamepad_button_codes
    server = put_server
    logger = loggerr
    msg_queue = None if hasattr(put_server, 'set_strength') else put_server
    if msg_queue is not None:
        server = None
    stop_event = asyncio.Event()
    main_loop = asyncio.get_event_loop()
    
    config_path = os.path.join(_plugin_dir, "config.json")
    cfg.load(config_path)

    config = cfg.plugins
    cached_config = cfg._cache
    PULSE_DATA = cfg.waveform

    global strength_values
    strength_values["health_a"] = config.get("health_bar", {}).get("strength", 24)
    strength_values["health_b"] = config.get("health_bar", {}).get("strength_b", 24)
    strength_values["shield_a"] = config.get("shield_bar", {}).get("strength", 20)
    strength_values["shield_b"] = config.get("shield_bar", {}).get("strength_b", 20)

    health_drop_threshold = config.get("health_bar", {}).get("drop_threshold", 0)

    cache_config()

    multi_char_enabled = cached_config.get("multi_char_enabled", False)
    gamepad_enabled = cached_config.get("gamepad_enabled", True)
    character_keys_str = cached_config.get("character_keys_str", "1,2,3")

    if multi_char_enabled:
        key_strs = [k.strip() for k in character_keys_str.split(',') if k.strip()]
        character_key_codes = []
        for ks in key_strs:
            vk = CHAR_KEY_MAP.get(ks)
            if vk is not None:
                character_key_codes.append(vk)
        character_count = len(character_key_codes)
        character_states = {}
        for i in range(character_count):
            character_states[i] = {'health': 100, 'shield': 0}
        active_character = 0
        target_character = -1
        switch_immunity_frames = 0
        switch_immunity_frames_config = cached_config.get("switch_immunity_frames", 5)
        switch_delay_frames_config = cached_config.get("switch_delay_frames", 1)
        pending_switch_index = -1
        switch_delay_counter = 0
        switch_value_unchanged = False
        switch_immunity_extensions = 0
        pre_switch_health = None
        pre_switch_shield = None
        prev_has_healthbar = False
        healthbar_appear_immunity = False

        gamepad_buttons_str = cached_config.get("gamepad_buttons_str", "0x1000,0x2000,0x4000,0x8000")
        gamepad_button_codes = []
        for btn_str in gamepad_buttons_str.split(','):
            btn_str = btn_str.strip()
            if btn_str:
                try:
                    gamepad_button_codes.append(int(btn_str, 16))
                except ValueError:
                    log(f"手柄按钮码无效: {btn_str}")

        log(f"多角色模式已启用 | 角色数: {character_count} | 按键: {key_strs} | 手柄: {'开' if gamepad_enabled else '关'} | 手柄按钮: {[hex(b) for b in gamepad_button_codes]} | 免疫帧: {switch_immunity_frames_config} | 延迟帧: {switch_delay_frames_config}")
    else:
        character_count = 0
        character_key_codes = []
        character_states = {}
        log("多角色模式未启用")

    ocr_enabled = cached_config.get("ocr_enabled", False)
    if ocr_enabled:
        log("OCR模式已启用，正在启动OCR服务端...")
        ocr_port = cached_config.get("ocr_port", 1395)
        lib.set_ocr_port(ocr_port)
        if lib.check_ocr_server(ocr_port):
            log("OCR服务端已启动")
        else:
            log("警告: OCR服务端启动失败，将回退到传统检测模式")
            cached_config["ocr_enabled"] = False

    log("插件已启动 | 截图方式: GDI")

    gameTitle = config.get("game", {}).get("process_title", "QQ")

    game_hwnd = lib.get_game_window(process_title=gameTitle)
    if game_hwnd is None:
        log("错误: 未找到游戏窗口" + gameTitle)
        return
    else:
        log("游戏窗口已找到" + gameTitle)

    key_monitor_thread = threading.Thread(target=key_monitor_loop, daemon=True)
    key_monitor_thread.start()

    overlay_enabled = config.get("overlay", {}).get("enabled", True)
    if overlay_enabled:
        overlay_thread = threading.Thread(target=create_overlay_window, daemon=True)
        overlay_thread.start()
        log("悬浮窗已启动 (F6切换显示, F10设置模式)")
    else:
        log("悬浮窗已禁用")

    monitoring_task = asyncio.create_task(monitoring_loop())
    log("插件运行中 | F9:开关监控 | F10:设置模式 | 方向键:调整强度")
    try:
        while not stop_event.is_set():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        log("主任务已取消")
    finally:
        is_monitoring = False
        monitoring_task.cancel()
        stop_event.set()
        log("监听已关闭")

async def stop():
    global is_monitoring
    if stop_event:
        is_monitoring = False
        stop_event.set()
        log("监听已关闭")

if __name__ == "__main__":
    print("HitElectric 插件 - 请通过惩罚姬主程序加载")
    print("配置工具请运行 HitElectricConfig.exe")
