import ctypes
import ctypes.wintypes

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CANCEL = 0x03
VK_MBUTTON = 0x04
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_SNAPSHOT = 0x2C
VK_INSERT = 0x2D
VK_DELETE = 0x2E

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

VK_A = 0x41
VK_B = 0x42
VK_C = 0x43
VK_D = 0x44
VK_E = 0x45
VK_F = 0x46
VK_G = 0x47
VK_H = 0x48
VK_I = 0x49
VK_J = 0x4A
VK_K = 0x4B
VK_L = 0x4C
VK_M = 0x4D
VK_N = 0x4E
VK_O = 0x4F
VK_P = 0x50
VK_Q = 0x51
VK_R = 0x52
VK_S = 0x53
VK_T = 0x54
VK_U = 0x55
VK_V = 0x56
VK_W = 0x57
VK_X = 0x58
VK_Y = 0x59
VK_Z = 0x5A

VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

VK_NUMLOCK = 0x90
VK_SCROLL = 0x91

VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LMENU = 0xA4
VK_RMENU = 0xA5

VK_OEM_1 = 0xBA
VK_OEM_PLUS = 0xBB
VK_OEM_COMMA = 0xBC
VK_OEM_MINUS = 0xBD
VK_OEM_PERIOD = 0xBE
VK_OEM_2 = 0xBF
VK_OEM_3 = 0xC0
VK_OEM_4 = 0xDB
VK_OEM_5 = 0xDC
VK_OEM_6 = 0xDD
VK_OEM_7 = 0xDE

CHAR_KEY_MAP = {
    '0': VK_0, '1': VK_1, '2': VK_2, '3': VK_3,
    '4': VK_4, '5': VK_5, '6': VK_6, '7': VK_7,
    '8': VK_8, '9': VK_9,
}

VK_NAME_MAP = {}
_locals = dict(globals())
for _name, _val in _locals.items():
    if _name.startswith('VK_') and isinstance(_val, int):
        VK_NAME_MAP[_val] = _name[3:].lower()

user32 = ctypes.windll.user32


def is_key_down(vk_code):
    return bool(user32.GetAsyncKeyState(vk_code) & 0x8000)


def vk_to_name(vk_code):
    return VK_NAME_MAP.get(vk_code, f"0x{vk_code:02X}")


def name_to_vk(name):
    name_lower = name.strip().lower()
    for vk, vk_name in VK_NAME_MAP.items():
        if vk_name == name_lower:
            return vk
    if name_lower.startswith('0x'):
        try:
            return int(name_lower, 16)
        except ValueError:
            pass
    try:
        return int(name_lower)
    except ValueError:
        pass
    return None


def capture_next_key(timeout_sec=5):
    """等待用户按下按键，返回 (vk_code, name)"""
    import time

    ignore_set = set()
    for vk in range(0x00, 0x08):
        ignore_set.add(vk)
    for vk in range(0x0C, 0x0E):
        ignore_set.add(vk)
    for vk in range(0x80, 0x90):
        ignore_set.add(vk)
    for vk in range(0xE8, 0xF0):
        ignore_set.add(vk)

    scan_vks = [vk for vk in range(1, 254) if vk not in ignore_set]

    release_deadline = time.time() + 0.5
    while time.time() < release_deadline:
        all_released = True
        for vk in scan_vks:
            if is_key_down(vk):
                all_released = False
                break
        if all_released:
            break
        time.sleep(0.02)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        for vk in scan_vks:
            if is_key_down(vk):
                time.sleep(0.1)
                if not is_key_down(vk):
                    return vk, vk_to_name(vk)
        time.sleep(0.02)
    return None, None
