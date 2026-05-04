
import ctypes
import ctypes.wintypes
import os
import sys

_plugin_dir = os.path.dirname(os.path.abspath(__file__))
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

from capture import capture_screen_fast, capture_screen_region, save_screenshot_sync, take_screenshot, BITMAPINFOHEADER, BITMAPINFO, RECT
from image import get_pixel_color, parse_coordinate, parse_coordinates, parse_color, parse_colors, color_match, check_positions_match, check_positions_count_match
from ocr import check_ocr_server, set_ocr_port, get_ocr_server_url, crop_image_for_ocr, ocr_recognize_number, extract_number, apply_ocr_filter, apply_filters_chain, create_png_from_bgra, create_bmp_from_bgra

SRCCOPY = 0x00CC0020

XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint32),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


xinput_dll = None


def init_xinput():
    global xinput_dll
    if xinput_dll is not None:
        return xinput_dll is not False
    try:
        xinput_dll = ctypes.windll.xinput1_4
        return True
    except:
        try:
            xinput_dll = ctypes.windll.xinput9_1_0
            return True
        except:
            xinput_dll = False
            return False


def read_xinput_buttons(user_index=0):
    if not init_xinput():
        return 0
    state = XINPUT_STATE()
    result = ctypes.windll.xinput1_4.XInputGetState(user_index, ctypes.byref(state))
    if result == 0:
        return state.Gamepad.wButtons
    return 0


def _print(msg, level="INFO"):
    print(f"[{level}] {msg}")


def find_window_by_keywords(keyword):
    class WindowList:
        def __init__(self):
            self.hwnds = []

    wl = WindowList()

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hWnd, lParam):
        if ctypes.windll.user32.IsWindowVisible(hWnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hWnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hWnd, buf, length + 1)
                title = buf.value
                if title:
                    if keyword.lower() in title.lower():
                        wl.hwnds.append(hWnd)
                        return False
        return True

    ctypes.windll.user32.EnumWindows(callback, 0)
    return wl.hwnds


def get_game_window(process_title="卡拉彼丘", process_exeName="Calabiyau-Win64-Shipping.exe"):
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == process_exeName:
                hwnds = find_window_by_keywords(process_exeName)
                if hwnds:
                    return hwnds[0]
    except ImportError:
        pass
    except Exception:
        pass
    hwnds = find_window_by_keywords(process_title)
    if hwnds:
        return hwnds[0]
    return None


def get_cursor_position():
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def get_client_offset(hwnd):
    if hwnd:
        point = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        return point.x, point.y
    return 0, 0


def sample_color_at_cursor(hwnd=None):
    abs_x, abs_y = get_cursor_position()
    client_x, client_y = 0, 0
    if hwnd is None:
        hwnd = get_game_window()
    if hwnd:
        client_x, client_y = get_client_offset(hwnd)
    rel_x = abs_x - client_x
    rel_y = abs_y - client_y
    try:
        bmp_data, rx, ry, rw, rh, img_width = capture_screen_fast(hwnd=hwnd)
        screen_rel_x = rel_x - rx
        screen_rel_y = rel_y - ry
        if 0 <= screen_rel_x < rw and 0 <= screen_rel_y < rh:
            color = get_pixel_color(bmp_data, screen_rel_x, screen_rel_y, img_width)
            hex_color = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        else:
            color = (0, 0, 0)
            hex_color = "#000000"
    except Exception:
        desktop_dc = ctypes.windll.user32.GetDC(0)
        mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(desktop_dc)
        bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(desktop_dc, 1, 1)
        ctypes.windll.gdi32.SelectObject(mem_dc, bitmap)
        ctypes.windll.gdi32.BitBlt(mem_dc, 0, 0, 1, 1, desktop_dc, abs_x, abs_y, SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = 1
        bmi.bmiHeader.biHeight = -1
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        buf_size = 4
        BufType = ctypes.c_ubyte * buf_size
        bmp_data = BufType()
        ctypes.windll.gdi32.GetDIBits(mem_dc, bitmap, 0, 1, bmp_data, ctypes.byref(bmi), 0)
        b = bmp_data[0]
        g = bmp_data[1]
        r = bmp_data[2]
        color = (r, g, b)
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        ctypes.windll.gdi32.DeleteObject(bitmap)
        ctypes.windll.gdi32.DeleteDC(mem_dc)
        ctypes.windll.user32.ReleaseDC(0, desktop_dc)
    return {
        'abs_x': abs_x, 'abs_y': abs_y,
        'rel_x': rel_x, 'rel_y': rel_y,
        'color': color, 'hex_color': hex_color
    }


def get_plugin_dir():
    return os.path.dirname(os.path.abspath(__file__))
