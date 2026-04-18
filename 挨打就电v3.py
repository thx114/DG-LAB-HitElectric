import asyncio
import ctypes
import ctypes.wintypes
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
name = "卡丘-挨打就电"
author = "F_thx"

base_dir = None
PULSE_DATA = None
stop_event = None
msg_queue = None
server = None
logger = None
dxgi_available = False

game_hwnd = None
is_monitoring = False
hwnd = None
config = {}
main_loop = None
overlay_hwnd = None

current_health = 100
current_shield = 0
current_electric_strength = 0
is_spectating = False
has_healthbar = False

# OCR 错误检测全局变量
ocr_health_suspect = False  # 血量是否被怀疑有误
ocr_shield_suspect = False  # 盾量是否被怀疑有误
ocr_suspected_health_value = None  # 怀疑的血量值
ocr_suspected_shield_value = None  # 怀疑的盾量值
ocr_health_suspect_count = 0  # 血量怀疑连续帧数
ocr_shield_suspect_count = 0  # 盾量怀疑连续帧数
OCR_SUSPECT_THRESHOLD = 2  # 需要1帧连续一样才信任（降低延迟）


overlay_text = "等待启动..."
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
# 电击触发信息显示相关
electric_trigger_message = ""  # 当前显示的触发信息
electric_trigger_count = 0     # 触发次数（用于overlap叠加）

cached_config = {}

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

capture_method = "GDI"

def cache_config():
    global cached_config
    plus_config = config.get("plus_sign", {})
    cached_config["plus_positions"] = lib.parse_coordinates(plus_config.get("positions", []))
    cached_config["plus_colors"] = lib.parse_colors(plus_config.get("colors", []))
    cached_config["plus_negative_positions"] = lib.parse_coordinates(plus_config.get("negative_positions", []))
    cached_config["plus_negative_colors"] = lib.parse_colors(plus_config.get("negative_colors", []))
    cached_config["plus_tolerance"] = plus_config.get("tolerance", 30)

    spectate_config = config.get("spectate", {})
    cached_config["spectate_positions"] = lib.parse_coordinates(spectate_config.get("positions", []))
    cached_config["spectate_colors"] = lib.parse_colors(spectate_config.get("colors", []))
    cached_config["spectate_tolerance"] = spectate_config.get("tolerance", 30)

    health_config = config.get("health_bar", {})
    cached_config["health_enabled"] = health_config.get("enabled", False)
    cached_config["health_start"] = lib.parse_coordinate(health_config.get("start", [0, 0]))
    cached_config["health_end"] = lib.parse_coordinate(health_config.get("end", [0, 0]))
    cached_config["health_colors"] = lib.parse_colors(health_config.get("colors", []))
    cached_config["health_tolerance"] = health_config.get("tolerance", 30)
    cached_config["health_sample_points"] = health_config.get("sample_points", 20)
    cached_config["health_ocr_top_left"] = lib.parse_coordinate(health_config.get("ocr_top_left", [0, 0]))
    cached_config["health_ocr_bottom_right"] = lib.parse_coordinate(health_config.get("ocr_bottom_right", [100, 100]))
    # OCR专属配置：结束点检测成功后是否不触发电击
    cached_config["health_ocr_end_trigger"] = health_config.get("ocr_end_trigger", False)
    # OCR专属配置：数字颜色和容差（用于滤镜）
    cached_config["health_ocr_number_color"] = lib.parse_colors(health_config.get("ocr_number_color", []))
    cached_config["health_ocr_number_tolerance"] = health_config.get("ocr_number_tolerance", 30)

    shield_config = config.get("shield_bar", {})
    cached_config["shield_enabled"] = shield_config.get("enabled", False)
    cached_config["shield_start"] = lib.parse_coordinate(shield_config.get("start", [0, 0]))
    cached_config["shield_end"] = lib.parse_coordinate(shield_config.get("end", [0, 0]))
    cached_config["shield_colors"] = lib.parse_colors(shield_config.get("colors", []))
    cached_config["shield_tolerance"] = shield_config.get("tolerance", 25)
    cached_config["shield_sample_points"] = shield_config.get("sample_points", 12)
    cached_config["shield_ocr_top_left"] = lib.parse_coordinate(shield_config.get("ocr_top_left", [0, 0]))
    cached_config["shield_ocr_bottom_right"] = lib.parse_coordinate(shield_config.get("ocr_bottom_right", [100, 100]))
    # OCR专属配置：结束点检测成功后是否不触发电击
    cached_config["shield_ocr_end_trigger"] = shield_config.get("ocr_end_trigger", False)
    # 配置：盾存在时不扣血
    cached_config["shield_blocks_health"] = shield_config.get("blocks_health", True)
    # OCR专属配置：数字颜色和容差（用于滤镜）
    cached_config["shield_ocr_number_color"] = lib.parse_colors(shield_config.get("ocr_number_color", []))
    cached_config["shield_ocr_number_tolerance"] = shield_config.get("ocr_number_tolerance", 25)

    overlap_config = config.get("overlap", {})
    cached_config["overlap_strength_add"] = overlap_config.get("strength_add", 1)
    cached_config["overlap_strength_max"] = overlap_config.get("strength_max", 200)

    ocr_config = config.get("ocr", {})
    cached_config["ocr_enabled"] = ocr_config.get("enabled", False)
    cached_config["ocr_port"] = ocr_config.get("port", 1395)

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
    capture_offset_x, capture_offset_y = capture_region[0], capture_region[1]
    debug("--detect_bar_length--")

    if not isinstance(start_pos, list) or len(start_pos) < 2 or not isinstance(end_pos, list) or len(end_pos) < 2:
        return 0, "0"

    sx, sy = start_pos[0] - capture_offset_x, start_pos[1] - capture_offset_y
    ex, ey = end_pos[0] - capture_offset_x, end_pos[1] - capture_offset_y
    sx = max(0, min(sx, capture_region[2] - 1))
    sy = max(0, min(sy, capture_region[3] - 1))
    ex = max(0, min(ex, capture_region[2] - 1))
    ey = max(0, min(ey, capture_region[3] - 1))

    if sx == ex:
        points = [(sx, sy + int((ey - sy) * i / sample_points)) for i in range(sample_points + 1)]
    else:
        points = [(sx + int((ex - sx) * i / sample_points), sy) for i in range(sample_points + 1)]

    lib.color_matches = [0] * len(bar_colors)
    filled_count = 0

    for i, (px, py) in enumerate(points):
        if 0 <= px < capture_region[2] and 0 <= py < capture_region[3]:
            pixel = lib.get_pixel_color(bmp_data, px, py, img_width)
            for color_idx, color in enumerate(bar_colors):
                if lib.color_match(pixel, color, tolerance):
                    lib.color_matches[color_idx] += 1
                    filled_count += 1
                    break

    percentage = (filled_count / sample_points) * 100
    color_result = '+'.join(map(str, lib.color_matches)) if lib.color_matches else '0'

    return percentage, color_result

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
            if current_shield > 0:
                current_health = health_pct
            else:
                current_health = health_pct
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
        return False, None, 0
    
    if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
        has_healthbar = False
        return False, None, 0
    
    # 获取截图区域偏移
    capture_region = cached_config.get("capture_region", [0, 0, 0, 0])
    offset_x = capture_region[0] if len(capture_region) >= 1 else 0
    offset_y = capture_region[1] if len(capture_region) >= 2 else 0
    
    # OCR坐标转换为相对于截图区域的坐标
    x1 = ocr_top_left[0] - offset_x
    y1 = ocr_top_left[1] - offset_y
    x2 = ocr_bottom_right[0] - offset_x
    y2 = ocr_bottom_right[1] - offset_y

    # 获取OCR滤镜配置
    filter_colors = cached_config.get("health_ocr_number_color", [])
    filter_tolerance = cached_config.get("health_ocr_number_tolerance", 2)

    number, ocr_time = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=cached_config["ocr_port"],
                                                  filter_colors=filter_colors, filter_tolerance=filter_tolerance)
    
    if number is not None and number != 0:
        has_healthbar = True
        return True, number, ocr_time
    else:
        has_healthbar = False
        return False, None, ocr_time

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
    
    # 获取OCR滤镜配置
    filter_colors = cached_config.get("shield_ocr_number_color", [])
    filter_tolerance = cached_config.get("shield_ocr_number_tolerance", 2)
    
    number, ocr_time = lib.ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, log=log, port=cached_config["ocr_port"],
                                                  filter_colors=filter_colors, filter_tolerance=filter_tolerance)
    
    return number, ocr_time

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

    if is_overlap:
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

def take_screenshot(prefix="screenshot"):
    global game_hwnd
    """调用 lib.take_screenshot 进行截图"""
    return lib.take_screenshot(prefix, log_func=log, hwnd=game_hwnd)

def key_monitor_loop():
    global is_monitoring, setting_mode, setting_target

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
                threading.Thread(target=take_screenshot, args=("F9",), daemon=True).start()
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
            except:
                plus_result = '00000000'
                spectate_result = '0000'
                health_color_result = '0'
                shield_color_result = '0'
                ocr_warning = ''
                ocr_total_time = 0

            # 构建延迟显示字符串（ocr_total_time是秒，需要转换为毫秒）
            if ocr_total_time > 0:
                delay_str = f"{last_capture_time:.1f}ms + {ocr_total_time*1000:.0f}ms(ocr) + {last_loop_time:.1f}ms(loop)"
            else:
                delay_str = f"{last_capture_time:.1f}ms + {last_loop_time:.1f}ms(loop)"
            
            # 检查是否显示触发信息（在 electric_active_until 时间内显示）
            global electric_trigger_message, electric_active_until
            trigger_info = ""
            if electric_trigger_message and time.time() < electric_active_until:
                trigger_info = f" {electric_trigger_message}"
            else:
                # 过期后清空触发信息
                electric_trigger_message = ""
            
            status_line = f"[{capture_method}] 血条:{healthbar_status} 观战:{spectating_status} 血:{health_val:.0f} 盾:{shield_val:.0f} 延迟:{delay_str}{trigger_info}"
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
            bmp_data = None
            if dxgi_available:
                bmp_data = lib.capture_screen_dxgi(capture_region)
            if bmp_data is None:
                bmp_data, rx, ry, rw, rh, img_width = lib.capture_screen_fast(capture_region,hwnd=game_hwnd)
            else:
                rx, ry, rw, rh = capture_region[0], capture_region[1], capture_region[2], capture_region[3]
                img_width = rw
            current_capture_time = (time.time() - t1) * 1000
            monitoring_loop.last_capture_time = current_capture_time

            ocr_enabled = cached_config.get("ocr_enabled", False)
            ocr_total_time = 0
            
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
                else:
                    has_healthbar, health_number, health_ocr_time = check_healthbar_ocr(bmp_data, img_width)
                    ocr_total_time += health_ocr_time
                    
                    monitoring_loop.plus_result = "OCR"
                    monitoring_loop.ocr_total_time = ocr_total_time  # 保存OCR延迟用于显示
                    
                    if has_healthbar:
                        # 先处理盾条（如果启用）
                        if cached_config.get("shield_enabled", False):
                            # 检查盾起始位置是否存在（OCR模式下）
                            shield_start = cached_config.get("shield_start", [0, 0])
                            shield_colors = cached_config.get("shield_colors", [])
                            shield_tolerance = cached_config.get("shield_tolerance", 25)
                            shield_start_exists = False
                            if shield_start and shield_colors:
                                start_pixel = lib.get_pixel_color(bmp_data, shield_start[0] - capture_region[0], shield_start[1] - capture_region[1], img_width)
                                for color in shield_colors:
                                    if lib.color_match(start_pixel, color, shield_tolerance):
                                        shield_start_exists = True
                                        break
                            
                            if shield_start_exists:
                                # 盾起始存在，进行OCR识别
                                shield_number, shield_ocr_time = check_shield_ocr(bmp_data, img_width)
                                ocr_total_time += shield_ocr_time
                                
                                # 使用OCR错误检测系统验证盾量
                                if shield_number is not None:
                                    shield_valid, validated_shield = validate_ocr_value('shield', shield_number, current_shield)
                                    if shield_valid:
                                        # 先检查是否需要触发（使用验证后的值与之前的值比较）
                                        if validated_shield < current_shield:
                                            # OCR专属配置：是否检测结束点
                                            shield_ocr_end_trigger = cached_config.get("shield_ocr_end_trigger", True)
                                            should_trigger = True
                                            
                                            if shield_ocr_end_trigger:
                                                # 检查盾条结束点颜色
                                                shield_end = cached_config.get("shield_end", [0, 0])
                                                shield_end_color_match = False
                                                if shield_end and shield_colors:
                                                    end_pixel = lib.get_pixel_color(bmp_data, shield_end[0] - capture_region[0], shield_end[1] - capture_region[1], img_width)
                                                    for color in shield_colors:
                                                        if lib.color_match(end_pixel, color, shield_tolerance):
                                                            shield_end_color_match = True
                                                            break
                                                # 结束点颜色存在时不触发电击
                                                should_trigger = not shield_end_color_match
                                            
                                            if should_trigger:
                                                await trigger_electric_shield(
                                                    strength_a=strength_values["shield_a"],
                                                    strength_b=strength_values["shield_b"]
                                                )
                                        # 然后更新当前盾量
                                        current_shield = max(0, validated_shield)
                                    monitoring_loop.shield_color_result = str(validated_shield) if validated_shield else "0"
                                else:
                                    monitoring_loop.shield_color_result = "0"
                            else:
                                # 盾起始不存在，盾值直接为0，覆盖OCR识别
                                current_shield = 0
                                monitoring_loop.shield_color_result = "0"
                        else:
                            monitoring_loop.shield_color_result = "0"
                            current_shield = 0
                        
                        # 处理血量：只有盾为0时才进行OCR错误检测和触发电击
                        if True:
                            # 使用OCR错误检测系统验证血量
                            if health_number is not None:
                                health_valid, validated_health = validate_ocr_value('health', health_number, current_health)
                                if health_valid:
                                    # 先检查是否需要触发（使用验证后的值与之前的值比较）
                                    if validated_health < current_health:
                                        # OCR专属配置：是否检测结束点
                                        health_ocr_end_trigger = cached_config.get("health_ocr_end_trigger", True)
                                        should_trigger = True
                                        
                                        if health_ocr_end_trigger:
                                            # 检查血条结束点颜色
                                            health_end = cached_config.get("health_end", [0, 0])
                                            health_colors = cached_config.get("health_colors", [])
                                            health_tolerance = cached_config.get("health_tolerance", 30)
                                            health_end_color_match = False
                                            if health_end and health_colors:
                                                end_pixel = lib.get_pixel_color(bmp_data, health_end[0] - capture_region[0], health_end[1] - capture_region[1], img_width)
                                                for color in health_colors:
                                                    if lib.color_match(end_pixel, color, health_tolerance):
                                                        health_end_color_match = True
                                                        break
                                            # 结束点颜色存在时不触发电击
                                            should_trigger = not health_end_color_match
                                        
                                        if should_trigger:
                                            await trigger_electric_health(
                                                strength_a=strength_values["health_a"],
                                                strength_b=strength_values["health_b"]
                                            )
                                    # 然后更新当前血量
                                    current_health = max(0, validated_health)
                                monitoring_loop.health_color_result = str(validated_health) if validated_health else "0"
                            else:
                                monitoring_loop.health_color_result = "0"
                        else:
                            # 盾存在时，根据配置决定是否处理血量
                            shield_blocks_health = cached_config.get("shield_blocks_health", True)
                            if shield_blocks_health:
                                # 直接更新血量显示，不进行错误检测和电击
                                if health_number is not None:
                                    current_health = max(0, health_number)
                                monitoring_loop.health_color_result = str(health_number) if health_number else "0"
                            else:
                                # 仍然进行错误检测，但不触发电击
                                if health_number is not None:
                                    health_valid, validated_health = validate_ocr_value('health', health_number, current_health)
                                    if health_valid:
                                        current_health = max(0, validated_health)
                                    monitoring_loop.health_color_result = str(validated_health) if validated_health else "0"
                                else:
                                    monitoring_loop.health_color_result = "0"
                    else:
                        monitoring_loop.health_color_result = "0"
                        monitoring_loop.shield_color_result = "0"
                        # 血条不存在时保持上一次的数值，不重置为0
                    
                    scan_interval_sec = config.get("scan_interval", 0.1)

                    if scan_interval_sec > 0 and (ocr_total_time / 1000 + current_capture_time / 1000) > scan_interval_sec * 0.8:
                        monitoring_loop.ocr_warning = f"!ocr性能瓶颈: {scan_interval_sec:.3f}s < {ocr_total_time/1000:.3f}s+{current_capture_time/1000:.3f}s"
                    else:
                        monitoring_loop.ocr_warning = ""
            else:
                has_healthbar, plus_result = check_healthbar_exists(bmp_data, img_width)
                is_spectating, spectate_result = check_spectating(bmp_data, img_width)

                monitoring_loop.plus_result = plus_result
                monitoring_loop.spectate_result = spectate_result
                monitoring_loop.ocr_warning = ""

                if has_healthbar and not is_spectating:
                    result = check_health_and_shield(bmp_data, img_width)

                    monitoring_loop.health_color_result = result.get("health_color_result", "0")
                    monitoring_loop.shield_color_result = result.get("shield_color_result", "0")

                    if result["health_dropped"]:
                        await trigger_electric_health(
                            strength_a=strength_values["health_a"],
                            strength_b=strength_values["health_b"]
                        )
                    elif result["shield_dropped"]:
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
        except Exception as e:
            log(f"检测出错: {e}")

        loopTime2 = time.time()
        last_loop_time = loopTime2 - loopTime1

        elapsed = time.time() - loop_start
        sleep_time = max(0.02, scan_interval - elapsed)
        await asyncio.sleep(sleep_time)

async def main(put_server, data, loggerr=None):
    global msg_queue, stop_event, PULSE_DATA, config, main_loop, is_monitoring, current_health, key_monitor_thread, server, logger, game_hwnd
    server = put_server
    logger = loggerr
    msg_queue = None if hasattr(put_server, 'set_strength') else put_server
    if msg_queue is not None:
        server = None
    stop_event = asyncio.Event()
    main_loop = asyncio.get_event_loop()
    
    if data is None:
        log("错误: 未获取到配置文件数据，请检查插件是否正确加载")
        config = {}
        PULSE_DATA = {}
    else:
        config = data.get("plugins", {})
        PULSE_DATA = data.get("waveform")
        if not config:
            log("警告: 插件配置为空，将使用默认配置")

    global strength_values
    strength_values["health_a"] = config.get("health_bar", {}).get("strength", 24)
    strength_values["health_b"] = config.get("health_bar", {}).get("strength_b", 24)
    strength_values["shield_a"] = config.get("shield_bar", {}).get("strength", 20)
    strength_values["shield_b"] = config.get("shield_bar", {}).get("strength_b", 20)

    cache_config()

    ocr_enabled = cached_config.get("ocr_enabled", False)
    if ocr_enabled:
        log("OCR模式已启用，正在启动OCR服务端...")
        ocr_port = config.get("ocr_port", 1395)
        lib.set_ocr_port(ocr_port)
        if lib.check_ocr_server(ocr_port):
            log("OCR服务端已启动")
        else:
            log("警告: OCR服务端启动失败，将回退到传统检测模式")
            cached_config["ocr_enabled"] = False

    global capture_method
    if lib.try_init_dxgi():
        capture_method = "DXGI"
        dxgi_available = True
    else:
        capture_method = "GDI"
    log(f"插件已启动 | 截图方式: {capture_method}")

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
