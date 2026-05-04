import ctypes
import ctypes.wintypes
import os

SRCCOPY = 0x00CC0020


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_uint32 * 3)]


def capture_screen_fast(region=None, hwnd=None):
    if not hwnd:
        return _capture_fullscreen()

    client_rect = RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    client_width = client_rect.right - client_rect.left
    client_height = client_rect.bottom - client_rect.top

    client_point = ctypes.wintypes.POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(client_point))
    client_left, client_top = client_point.x, client_point.y

    if client_width <= 0 or client_height <= 0:
        client_width = max(1, client_width)
        client_height = max(1, client_height)

    desktop_dc = ctypes.windll.user32.GetDC(0)
    mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(desktop_dc)
    bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(desktop_dc, client_width, client_height)
    ctypes.windll.gdi32.SelectObject(mem_dc, bitmap)
    ctypes.windll.gdi32.BitBlt(mem_dc, 0, 0, client_width, client_height, desktop_dc, client_left, client_top, SRCCOPY)

    if region:
        try:
            rx, ry, rw, rh = [int(x) for x in region]
        except:
            rx, ry, rw, rh = 0, 0, client_width, client_height
        rx = max(0, rx)
        ry = max(0, ry)
        rw = max(1, min(rw, client_width - rx))
        rh = max(1, min(rh, client_height - ry))

        mem_dc_crop = ctypes.windll.gdi32.CreateCompatibleDC(desktop_dc)
        bitmap_crop = ctypes.windll.gdi32.CreateCompatibleBitmap(desktop_dc, rw, rh)
        ctypes.windll.gdi32.SelectObject(mem_dc_crop, bitmap_crop)
        ctypes.windll.gdi32.BitBlt(mem_dc_crop, 0, 0, rw, rh, mem_dc, rx, ry, SRCCOPY)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = rw
        bmi.bmiHeader.biHeight = -rh
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buf_size = rw * rh * 4
        BufType = ctypes.c_ubyte * buf_size
        buf = BufType()
        ctypes.windll.gdi32.GetDIBits(mem_dc_crop, bitmap_crop, 0, rh, buf, ctypes.byref(bmi), 0)

        ctypes.windll.gdi32.DeleteObject(bitmap_crop)
        ctypes.windll.gdi32.DeleteDC(mem_dc_crop)
        ctypes.windll.gdi32.DeleteObject(bitmap)
        ctypes.windll.gdi32.DeleteDC(mem_dc)
        ctypes.windll.user32.ReleaseDC(0, desktop_dc)

        return buf, rx, ry, rw, rh, rw
    else:
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = client_width
        bmi.bmiHeader.biHeight = -client_height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buf_size = client_width * client_height * 4
        BufType = ctypes.c_ubyte * buf_size
        buf = BufType()
        ctypes.windll.gdi32.GetDIBits(mem_dc, bitmap, 0, client_height, buf, ctypes.byref(bmi), 0)

        ctypes.windll.gdi32.DeleteObject(bitmap)
        ctypes.windll.gdi32.DeleteDC(mem_dc)
        ctypes.windll.user32.ReleaseDC(0, desktop_dc)

        return buf, 0, 0, client_width, client_height, client_width


def _capture_fullscreen():
    width = ctypes.windll.user32.GetSystemMetrics(0)
    height = ctypes.windll.user32.GetSystemMetrics(1)
    hwnd_dc = ctypes.windll.user32.GetDC(0)
    mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    ctypes.windll.gdi32.SelectObject(mem_dc, bitmap)
    ctypes.windll.gdi32.BitBlt(mem_dc, 0, 0, width, height, hwnd_dc, 0, 0, SRCCOPY)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = width
    bmi.bmiHeader.biHeight = -height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    buf_size = width * height * 4
    BufType = ctypes.c_ubyte * buf_size
    buf = BufType()
    ctypes.windll.gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)

    ctypes.windll.gdi32.DeleteObject(bitmap)
    ctypes.windll.gdi32.DeleteDC(mem_dc)
    ctypes.windll.user32.ReleaseDC(0, hwnd_dc)

    return buf, 0, 0, width, height, width


def capture_screen_region(left, top, width, height):
    MAX_SIZE = 4000
    width = min(width, MAX_SIZE)
    height = min(height, MAX_SIZE)

    desktop_dc = None
    mem_dc = None
    bitmap = None

    try:
        desktop_dc = ctypes.windll.user32.GetDC(0)
        if not desktop_dc:
            raise Exception("无法获取屏幕 DC")
        mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(desktop_dc)
        if not mem_dc:
            raise Exception("无法创建内存 DC")
        bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(desktop_dc, width, height)
        if not bitmap:
            raise Exception("无法创建位图")
        ctypes.windll.gdi32.SelectObject(mem_dc, bitmap)
        result = ctypes.windll.gdi32.BitBlt(mem_dc, 0, 0, width, height, desktop_dc, left, top, SRCCOPY)
        if not result:
            raise Exception("BitBlt 失败")

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buf_size = width * height * 4
        if buf_size <= 0 or buf_size > 100 * 1024 * 1024:
            raise Exception(f"缓冲区大小无效：{buf_size}")
        BufType = ctypes.c_ubyte * buf_size
        buf = BufType()
        result = ctypes.windll.gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)
        if result == 0:
            raise Exception("GetDIBits 失败")
        return bytes(buf)
    finally:
        if bitmap:
            ctypes.windll.gdi32.DeleteObject(bitmap)
        if mem_dc:
            ctypes.windll.gdi32.DeleteDC(mem_dc)
        if desktop_dc:
            ctypes.windll.user32.ReleaseDC(0, desktop_dc)


def save_screenshot_sync(bmp_data, width, height, filename):
    base_path = os.path.abspath(os.path.dirname(__file__))
    screenshot_dir = os.path.join(base_path, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    buf_size = width * height * 4
    if len(bmp_data) < buf_size:
        raise ValueError(f"截图数据不足: {len(bmp_data)} < {buf_size}")

    try:
        from PIL import Image
        img_path = os.path.join(screenshot_dir, filename.replace('.bmp', '.png'))
        raw_data = bytes(bmp_data[:buf_size])
        try:
            import numpy as np
            arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
            rgb_arr = arr[:, :, 2::-1].copy()
            img = Image.fromarray(rgb_arr, 'RGB')
        except ImportError:
            rgb_data = bytearray()
            for y in range(height):
                row_offset = y * width * 4
                for x in range(width):
                    idx = row_offset + x * 4
                    rgb_data.append(raw_data[idx + 2])
                    rgb_data.append(raw_data[idx + 1])
                    rgb_data.append(raw_data[idx])
            img = Image.frombytes('RGB', (width, height), bytes(rgb_data))
        img.save(img_path, 'PNG')
        return img_path
    except ImportError:
        img_path = os.path.join(screenshot_dir, filename.replace('.png', '.bmp'))
        with open(img_path, 'wb') as f:
            bmp_header = bytearray(14)
            bmp_header[0:2] = b'BM'
            bmp_header[2:6] = (54 + buf_size).to_bytes(4, 'little')
            bmp_header[10:14] = (54).to_bytes(4, 'little')
            bmp_info = bytearray(40)
            bmp_info[0:4] = (40).to_bytes(4, 'little')
            bmp_info[4:8] = width.to_bytes(4, 'little', signed=False)
            bmp_info[8:12] = (-height).to_bytes(4, 'little', signed=True)
            bmp_info[12:14] = (1).to_bytes(2, 'little')
            bmp_info[14:16] = (32).to_bytes(2, 'little')
            f.write(bmp_header)
            f.write(bmp_info)
            f.write(bytes(bmp_data[:buf_size]))
        return img_path


def take_screenshot(prefix="screenshot", log_func=print, hwnd=None):
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"
    if not hwnd:
        log_func(f"{prefix}截图失败: 未找到游戏窗口")
        return None
    try:
        bmp_data, rx, ry, rw, rh, img_width = capture_screen_fast(hwnd=hwnd)
        if bmp_data and len(bmp_data) > 0:
            full_path = save_screenshot_sync(bmp_data, rw, rh, filename)
            log_func(f"{prefix}截图已保存: {full_path} ({rw}x{rh})")
            return full_path
        else:
            log_func(f"{prefix}截图失败: 截图数据为空")
            return None
    except Exception as e:
        log_func(f"{prefix}截图失败: {e}")
        return None
