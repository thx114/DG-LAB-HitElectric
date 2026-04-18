#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HitElectric 公共库函数
包含截图、颜色提取等公共函数
"""

import ctypes
import ctypes.wintypes
import os
import sys

# Windows API 常量
SRCCOPY = 0x00CC0020

# DXGI 全局状态
dxgi_factory = None
dxgi_output_dup = None
dxgi_device = None
dxgi_initialized = False
dxgi_available = False

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', ctypes.c_uint32),
        ('biWidth', ctypes.c_long),
        ('biHeight', ctypes.c_long),
        ('biPlanes', ctypes.c_uint16),
        ('biBitCount', ctypes.c_uint16),
        ('biCompression', ctypes.c_uint32),
        ('biSizeImage', ctypes.c_uint32),
        ('biXPelsPerMeter', ctypes.c_long),
        ('biYPelsPerMeter', ctypes.c_long),
        ('biClrUsed', ctypes.c_uint32),
        ('biClrImportant', ctypes.c_uint32),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', ctypes.c_uint32 * 1),
    ]

def _print(msg,level="INFO"):
    print(f"[{level}] {msg}")

def find_window_by_keywords(keyword):
    """通过关键词查找窗口"""
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
    """获取游戏窗口句柄"""
    # 尝试通过进程名查找（如果有 psutil）
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
    
    # 通过窗口标题查找
    hwnds = find_window_by_keywords(process_title)
    if hwnds:
        return hwnds[0]
    
    return None

def try_init_dxgi():
    """初始化 DXGI Desktop Duplication
    
    注意：此功能需要 Windows 10+ 且显卡驱动支持
    虚拟机、远程桌面、某些集成显卡可能不支持
    """
    global dxgi_factory, dxgi_output_dup, dxgi_device, dxgi_initialized, dxgi_available
    
    if dxgi_initialized:
        return dxgi_available
    dxgi_initialized = True

    _comtypes_ok = False
    try:
        import comtypes
        from comtypes import GUID
        _comtypes_ok = True
    except ImportError:
        try:
            import os as _os
            _plugin_dir = _os.path.dirname(_os.path.abspath(__file__))
            _comtypes_dir = _os.path.join(_plugin_dir, "comtypes-1.4.16")
            if _os.path.isdir(_comtypes_dir) and _comtypes_dir not in sys.path:
                sys.path.insert(0, _comtypes_dir)
            import comtypes
            from comtypes import GUID
            _comtypes_ok = True
        except ImportError:
            print("[DXGI] 无法导入 comtypes，将使用 GDI 截图")
            return False

    if not _comtypes_ok:
        print("[DXGI] comtypes 导入失败，将使用 GDI 截图")
        return False

    _factory = None
    _adapter = None
    _output = None
    
    try:
        ctypes.windll.ole32.CoInitialize(None)

        IID_IDXGIFactory1 = GUID('{770aae78-f26f-4dba-a829-253c83d1b387}')
        
        CreateDXGIFactory1 = ctypes.windll.dxgi.CreateDXGIFactory1
        CreateDXGIFactory1.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
        CreateDXGIFactory1.restype = ctypes.c_long

        factory_ptr = ctypes.c_void_p()
        hr = CreateDXGIFactory1(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(factory_ptr))
        if hr != 0 or not factory_ptr.value:
            print(f"[DXGI] CreateDXGIFactory1 失败，hr=0x{hr & 0xFFFFFFFF:08X}")
            return False
        _factory = factory_ptr.value

        EnumAdapters = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p)
        )
        factory_vt = ctypes.cast(_factory, ctypes.POINTER(ctypes.c_void_p))
        
        try:
            enum_fn_ptr = factory_vt[7]
            if not enum_fn_ptr:
                raise ValueError("vtable[7] is NULL")
            enum_fn = ctypes.cast(enum_fn_ptr, EnumAdapters)
        except Exception as e:
            print(f"[DXGI] 获取 EnumAdapters 失败：{e}")
            return False

        adapter_ptr = ctypes.c_void_p()
        hr = enum_fn(_factory, 0, ctypes.byref(adapter_ptr))
        if hr != 0 or not adapter_ptr.value:
            print(f"[DXGI] EnumAdapters 失败，hr=0x{hr & 0xFFFFFFFF:08X}")
            return False
        _adapter = adapter_ptr.value

        EnumOutputs = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_uint,
            ctypes.POINTER(ctypes.c_void_p)
        )
        adapter_vt = ctypes.cast(_adapter, ctypes.POINTER(ctypes.c_void_p))
        
        try:
            enum_out_fn_ptr = adapter_vt[7]
            if not enum_out_fn_ptr:
                raise ValueError("vtable[7] is NULL")
            enum_out_fn = ctypes.cast(enum_out_fn_ptr, EnumOutputs)
        except Exception as e:
            print(f"[DXGI] 获取 EnumOutputs 失败：{e}")
            return False

        output_ptr = ctypes.c_void_p()
        hr = enum_out_fn(_adapter, 0, ctypes.byref(output_ptr))
        if hr != 0 or not output_ptr.value:
            print(f"[DXGI] EnumOutputs 失败，hr=0x{hr & 0xFFFFFFFF:08X}")
            return False
        _output = output_ptr.value

        DuplicateOutput = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p)
        )
        output_vt = ctypes.cast(_output, ctypes.POINTER(ctypes.c_void_p))

        is_64bit = ctypes.sizeof(ctypes.c_void_p) == 8
        
        dup_offsets_to_try = [22, 21, 20, 23, 24] if is_64bit else [18, 17, 16, 19, 20]
        dup_fn_found = False
        
        for offset in dup_offsets_to_try:
            try:
                fn_ptr = output_vt[offset]
                if not fn_ptr or fn_ptr == 0:
                    continue
                    
                dup_fn = ctypes.cast(fn_ptr, DuplicateOutput)
                test_dup = ctypes.c_void_p()
                test_hr = dup_fn(_output, None, ctypes.byref(test_dup))
                
                if test_hr == 0 or (test_hr & 0xFFFFFFFF) == 0x887A0004:
                    if test_dup.value:
                        ReleaseDup = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
                        try:
                            dup_vt2 = ctypes.cast(test_dup.value, ctypes.POINTER(ctypes.c_void_p))
                            rel_fn = ctypes.cast(dup_vt2[2], ReleaseDup)
                            rel_fn(test_dup.value)
                        except:
                            pass
                    dup_fn_found = True
                    dup_output_fn = dup_fn
                    break
            except (OSError, WindowsError, Exception):
                continue
        
        if not dup_fn_found:
            print(f"[DXGI] 未找到有效的 DuplicateOutput (尝试偏移：{dup_offsets_to_try})")
            print("[DXGI] 可能原因：显卡驱动不支持/虚拟机/远程桌面")
            print("[DXGI] 将使用 GDI 截图")
            return False

        dup_ptr = ctypes.c_void_p()
        hr = dup_output_fn(_output, None, ctypes.byref(dup_ptr))
        if hr != 0 or not dup_ptr.value:
            err_code = hr & 0xFFFFFFFF
            err_name = {
                0x887A0004: "ACCESS_DENIED(已被占用)",
                0x887A0026: "INVALID_CALL",
                0x887A002D: "NOT_CURRENTLY_AVAILABLE",
                0x887A0005: "INSUFFICIENT_BUFFER",
            }.get(err_code, f"0x{err_code:08X}")
            print(f"[DXGI] DuplicateOutput 失败：{err_name}")
            print("[DXGI] 将使用 GDI 截图")
            return False

        dxgi_factory = _factory
        dxgi_output_dup = dup_ptr.value
        dxgi_available = True
        print("[DXGI] 初始化成功，将使用 DXGI 截图")
        return True

    except (OSError, WindowsError) as e:
        print(f"[DXGI] Windows 错误：{type(e).__name__}: {e}")
        print("[DXGI] 将使用 GDI 截图")
        dxgi_available = False
        return False
    except Exception as e:
        print(f"[DXGI] 初始化异常：{type(e).__name__}: {e}")
        print("[DXGI] 将使用 GDI 截图")
        dxgi_available = False
        return False

def capture_screen_dxgi(region=None):
    """使用 DXGI Desktop Duplication 截图（当前为占位实现）"""
    global dxgi_output_dup
    if not dxgi_output_dup:
        return None
    try:
        AcquireNextFrame = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p))
        dup_vtable = ctypes.cast(dxgi_output_dup, ctypes.POINTER(ctypes.c_void_p))
        acquire_fn = ctypes.cast(dup_vtable[3], AcquireNextFrame)

        frame_info = ctypes.c_void_p()
        resource_ptr = ctypes.c_void_p()
        dirty_rects = ctypes.c_void_p()
        hr = acquire_fn(dxgi_output_dup, 0, ctypes.byref(frame_info), ctypes.byref(resource_ptr), ctypes.byref(dirty_rects))
        if hr != 0:
            return None

        if resource_ptr.value:
            ReleaseFrame = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)
            release_fn = ctypes.cast(dup_vtable[5], ReleaseFrame)
            release_fn(dxgi_output_dup)

        return None
    except:
        return None

def capture_screen_fast(region=None, hwnd=None):
    """
    快速截图游戏窗口客户区
    
    Args:
        region: 可选的裁剪区域 [x, y, width, height]，相对于窗口客户区
        hwnd: 游戏窗口句柄，如果为 None 则自动获取
    
    Returns:
        tuple: (bmp_data, rx, ry, rw, rh, img_width)
            - bmp_data: BMP 原始数据（BGRA 格式）
            - rx, ry: 裁剪区域左上角坐标
            - rw, rh: 裁剪区域宽高
            - img_width: 图像宽度（用于像素索引计算）
    """
    if not hwnd:
        hwnd = get_game_window()
    
    if hwnd:
        # 获取客户区大小
        client_rect = RECT()
        ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        client_width = client_rect.right - client_rect.left
        client_height = client_rect.bottom - client_rect.top
        
        # 获取客户区左上角在屏幕上的位置
        client_point = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(client_point))
        client_left, client_top = client_point.x, client_point.y
        
        # 确保宽高为正数
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
    else:
        # 无游戏窗口时截图全屏
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
    """截图指定屏幕区域 - 带错误处理"""
    # 限制最大截图尺寸，避免内存问题
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
        
        # 从屏幕指定位置截图
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
        if buf_size <= 0 or buf_size > 100 * 1024 * 1024:  # 最大 100MB
            raise Exception(f"缓冲区大小无效：{buf_size}")
            
        BufType = ctypes.c_ubyte * buf_size
        buf = BufType()
        
        result = ctypes.windll.gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmi), 0)
        if result == 0:
            raise Exception("GetDIBits 失败")
        
        # 复制数据，因为 buf 是局部变量
        return bytes(buf)
        
    finally:
        if bitmap:
            ctypes.windll.gdi32.DeleteObject(bitmap)
        if mem_dc:
            ctypes.windll.gdi32.DeleteDC(mem_dc)
        if desktop_dc:
            ctypes.windll.user32.ReleaseDC(0, desktop_dc)

def get_pixel_color(bmp_data, x, y, img_width):
    """
    从 BMP 数据中提取指定位置的像素颜色
    
    Args:
        bmp_data: BMP 原始数据（BGRA 格式）
        x: 像素 X 坐标
        y: 像素 Y 坐标
        img_width: 图像宽度
    
    Returns:
        tuple: (R, G, B) 颜色值
    """
    idx = (y * img_width + x) * 4
    if idx + 3 < len(bmp_data):
        b = bmp_data[idx]
        g = bmp_data[idx + 1]
        r = bmp_data[idx + 2]
        return (r, g, b)
    return (0, 0, 0)

def get_cursor_position():
    """
    获取鼠标在屏幕上的位置
    
    Returns:
        tuple: (x, y) 鼠标坐标
    """
    point = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y

def get_client_offset(hwnd):
    """
    获取窗口客户区左上角在屏幕上的位置
    
    Args:
        hwnd: 窗口句柄
    
    Returns:
        tuple: (x, y) 客户区左上角屏幕坐标
    """
    if hwnd:
        point = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(point))
        return point.x, point.y
    return 0, 0

def sample_color_at_cursor(hwnd=None):
    """
    在鼠标位置采样颜色 - 使用 capture_screen_fast 保持一致

    Args:
        hwnd: 游戏窗口句柄，如果为 None 则自动获取

    Returns:
        dict: {
            'abs_x': 鼠标屏幕绝对 X 坐标，
            'abs_y': 鼠标屏幕绝对 Y 坐标，
            'rel_x': 相对于窗口客户区的 X 坐标，
            'rel_y': 相对于窗口客户区的 Y 坐标，
            'color': (R, G, B) 颜色值，
            'hex_color': '#RRGGBB' 十六进制颜色字符串
        }
    """
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

        # 使用相对于窗口客户区的坐标计算截图内的位置
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
        'abs_x': abs_x,
        'abs_y': abs_y,
        'rel_x': rel_x,
        'rel_y': rel_y,
        'color': color,
        'hex_color': hex_color
    }

def parse_coordinate(coord):
    """解析坐标，支持列表或字符串格式"""
    if isinstance(coord, list):
        try:
            parsed = [int(str(x).strip()) for x in coord]
            while len(parsed) < 2:
                parsed.append(0)
            return parsed
        except:
            return [0, 0]
    elif isinstance(coord, str):
        try:
            parsed = [int(x.strip()) for x in coord.split(',')]
            while len(parsed) < 2:
                parsed.append(0)
            return parsed
        except:
            return [0, 0]
    return [0, 0]

def parse_coordinates(coords):
    """解析多个坐标，支持列表或字符串格式"""
    if isinstance(coords, list):
        result = []
        for coord in coords:
            parsed = parse_coordinate(coord)
            if isinstance(parsed, list) and len(parsed) >= 2:
                result.append(parsed)
        return result
    elif isinstance(coords, str):
        try:
            return [parse_coordinate(coord) for coord in coords.split('|')]
        except:
            return []
    return []

def parse_color(color):
    """解析颜色，支持列表或字符串格式"""
    if isinstance(color, list):
        try:
            return [int(x) for x in color]
        except:
            return [0, 0, 0]
    elif isinstance(color, str):
        try:
            color = color.strip()
            if color.startswith('#'):
                color = color.lstrip('#')
                return [int(color[i:i+2], 16) for i in (0, 2, 4)]
            else:
                return [int(x.strip()) for x in color.split(',')]
        except:
            return [0, 0, 0]
    return [0, 0, 0]

def parse_colors(colors):
    """解析多个颜色"""
    if isinstance(colors, list):
        result = []
        for color in colors:
            parsed = parse_color(color)
            if isinstance(parsed, list) and len(parsed) >= 3:
                result.append(parsed)
        return result
    elif isinstance(colors, str):
        try:
            return [parse_color(color) for color in colors.split('|')]
        except:
            return []
    return []

def color_match(pixel, target_colors, tolerance=30):
    """
    颜色匹配检查

    Args:
        pixel: 像素颜色 (R, G, B)
        target_colors: 目标颜色或颜色列表
        tolerance: 颜色容差

    Returns:
        bool: 是否匹配
    """
    if isinstance(target_colors[0], list):
        for color in target_colors:
            if not isinstance(color, list):
                color = parse_color(color)
            if (abs(pixel[0] - color[0]) <= tolerance and
                abs(pixel[1] - color[1]) <= tolerance and
                abs(pixel[2] - color[2]) <= tolerance):
                return True
        return False
    else:
        target_colors = parse_color(target_colors)
        return (abs(pixel[0] - target_colors[0]) <= tolerance and
                abs(pixel[1] - target_colors[1]) <= tolerance and
                abs(pixel[2] - target_colors[2]) <= tolerance)

def check_positions_match(bmp_data, positions, colors, capture_region, img_width, tolerance=30, extra_colors=None):
    """
    通用位置颜色匹配检查函数

    Args:
        bmp_data: BMP 原始数据
        positions: 位置列表 [[x,y], ...]
        colors: 对应的颜色列表 [[r,g,b], ...]
        capture_region: 截图区域 [x, y, width, height]
        img_width: 图像宽度
        tolerance: 颜色容差
        extra_colors: 额外的备用颜色列表（当颜色数量多于位置时使用）

    Returns:
        tuple: (all_match, result_str)
            - all_match: 是否所有位置都匹配
            - result_str: 匹配结果字符串（'1'表示匹配，'0'表示不匹配）
    """
    if not positions or not colors:
        return False, ""

    capture_offset_x, capture_offset_y = capture_region[0], capture_region[1]
    result = []
    all_match = True

    outcolors = []
    has_extra_colors = False
    if extra_colors is not None and len(colors) > len(positions):
        outcolors = colors[len(positions):]
        has_extra_colors = True

    for i, pos in enumerate(positions):
        if i < len(colors):
            if isinstance(pos, list) and len(pos) >= 2:
                rel_x = pos[0] - capture_offset_x
                rel_y = pos[1] - capture_offset_y
                if 0 <= rel_x < capture_region[2] and 0 <= rel_y < capture_region[3]:
                    pixel = get_pixel_color(bmp_data, rel_x, rel_y, img_width)
                    match = color_match(pixel, colors[i], tolerance)
                    if not match and has_extra_colors:
                        for out_color in outcolors:
                            if color_match(pixel, out_color, tolerance):
                                match = True
                                break
                    result.append('1' if match else '0')
                    if not match:
                        all_match = False
                else:
                    result.append('0')
                    all_match = False
            else:
                result.append('0')
                all_match = False

    return all_match, ''.join(result)

def check_positions_count_match(bmp_data, positions, colors, capture_region, img_width, tolerance=30, match_threshold=0.75):
    """
    通用位置颜色计数匹配检查函数（用于需要达到一定匹配比例的场景）

    Args:
        bmp_data: BMP 原始数据
        positions: 位置列表 [[x,y], ...]
        colors: 对应的颜色列表 [[r,g,b], ...]
        capture_region: 截图区域 [x, y, width, height]
        img_width: 图像宽度
        tolerance: 颜色容差
        match_threshold: 匹配阈值比例（0-1）

    Returns:
        tuple: (is_matched, result_str, match_count)
    """
    if not positions or not colors:
        return False, "0" * min(len(positions) if positions else 4, 4), 0

    capture_offset_x, capture_offset_y = capture_region[0], capture_region[1]
    result = []
    match_count = 0

    for i, pos in enumerate(positions):
        if i < len(colors):
            if isinstance(pos, list) and len(pos) >= 2:
                rel_x = pos[0] - capture_offset_x
                rel_y = pos[1] - capture_offset_y
                if 0 <= rel_x < capture_region[2] and 0 <= rel_y < capture_region[3]:
                    pixel = get_pixel_color(bmp_data, rel_x, rel_y, img_width)
                    match = color_match(pixel, colors[i], tolerance)
                    result.append('1' if match else '0')
                    if match:
                        match_count += 1
                else:
                    result.append('0')
            else:
                result.append('0')

    while len(result) < 4:
        result.append('0')

    is_matched = match_count >= len(positions) * match_threshold
    return is_matched, ''.join(result), match_count


def save_screenshot_sync(bmp_data, width, height, filename):
    """
    保存截图到文件
    
    Args:
        bmp_data: BMP 原始数据（BGRA 格式）
        width: 图像宽度
        height: 图像高度
        filename: 文件名
    
    Returns:
        str: 保存的文件路径
    """
    base_path = os.path.abspath(os.path.dirname(__file__))
    screenshot_dir = os.path.join(base_path, "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    
    buf_size = width * height * 4
    if len(bmp_data) < buf_size:
        raise ValueError(f"截图数据不足: {len(bmp_data)} < {buf_size}")
    
    try:
        # 尝试使用 PIL 保存为 PNG
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
        # 无 PIL 时保存为 BMP 格式
        img_path = os.path.join(screenshot_dir, filename.replace('.png', '.bmp'))
        
        with open(img_path, 'wb') as f:
            # BMP 文件头 (14字节)
            bmp_header = bytearray(14)
            bmp_header[0:2] = b'BM'
            bmp_header[2:6] = (54 + buf_size).to_bytes(4, 'little')
            bmp_header[10:14] = (54).to_bytes(4, 'little')
            
            # BMP 信息头 (40字节)
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


def take_screenshot(prefix="screenshot", log=_print,hwnd=None):
    """
    截图游戏窗口并保存到文件
    
    Args:
        prefix: 文件名前缀
        log: 可选的日志函数，如果不提供则使用 print
    
    Returns:
        str: 保存的文件路径，失败返回 None
    """
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"

    if not hwnd:
        msg = f"{prefix}截图失败: 未找到游戏窗口"
        log(msg)
        return None

    try:
        bmp_data, rx, ry, rw, rh, img_width = capture_screen_fast(hwnd=hwnd)
        if bmp_data and len(bmp_data) > 0:
            full_path = save_screenshot_sync(bmp_data, rw, rh, filename)
            log(f"{prefix}截图已保存: {full_path} ({rw}x{rh})")
            return full_path
        else:
            log(f"{prefix}截图失败: 截图数据为空")
            return None
    except Exception as e:
        log(f"{prefix}截图失败: {e}")
        return None

_ocr_process = None
_ocr_server_url = "http://127.0.0.1:1395"
_ocr_port = 1395

def get_ocr_server_url(port=None):
    """获取OCR服务端URL
    
    Args:
        port: 端口号，None则使用默认端口
        
    Returns:
        str: OCR服务端URL
    """
    if port is None:
        port = _ocr_port
    return f"http://127.0.0.1:{port}"

def set_ocr_port(port):
    """设置OCR服务端端口
    
    Args:
        port: 端口号
    """
    global _ocr_port, _ocr_server_url
    _ocr_port = port
    _ocr_server_url = f"http://127.0.0.1:{port}"
    print(f"[OCR] 端口设置为: {port}")

def get_plugin_dir():
    """获取插件目录路径"""
    
    import os, sys
    return os.path.dirname(os.path.abspath(__file__))



def check_ocr_server(port=None):
    """
    检查OCR服务端是否运行中（新版API）
    
    Args:
        port: 端口号，None则使用默认端口1395
        
    Returns:
        bool: 是否运行中
    """
    import requests
    if port is None:
        port = 1395
    url = f"http://127.0.0.1:{port}/api/ocr"
    try:
        # 发送一个简单的空请求测试服务是否可用
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
        return r.status_code == 200
    except:
        return False

def crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=_print, use_bmp=True, filter_colors=None, filter_tolerance=0):
    """
    从截图数据中裁剪指定区域用于OCR识别
    
    Args:
        bmp_data: 截图原始数据 (BGRA格式，bytes类型)
        x1, y1: 左上角坐标
        x2, y2: 右下角坐标
        img_width: 图片宽度
        use_bmp: 是否使用BMP格式（默认True，比PNG编码快10-20倍）
        filter_colors: 滤镜目标颜色列表 [(R,G,B), ...]，None表示不使用滤镜
        filter_tolerance: 滤镜容差值
        
    Returns:
        bytes: 图片数据（BMP或PNG格式），失败返回None
    """
    try:
        width = x2 - x1
        height = y2 - y1
        
        if width <= 0 or height <= 0:
            log(f"[OCR] 裁剪区域无效: width={width}, height={height}")
            return None
        
        # 确保 bmp_data 是 bytes 类型
        try:
            if not isinstance(bmp_data, bytes):
                bmp_data = bytes(bmp_data)
        except Exception as e:
            log(f"[OCR] 数据类型转换失败: {e}, 类型: {type(bmp_data)}")
            return None
            
        
        # 检查输入数据
        if bmp_data is None or len(bmp_data) == 0:
            log(f"[OCR] 输入数据为空")
            return None
        
        expected_data_len = img_width * 4 * (y2 + 1)  # 至少需要的行数
        if len(bmp_data) < expected_data_len:
            log(f"[OCR] 输入数据不足: 需要至少{expected_data_len} bytes, 实际{len(bmp_data)} bytes, img_width={img_width}")
            return None
        
        cropped_bytes = bytearray()  # 使用 bytearray 更高效
        for y in range(y1, y2):
            row_start = (y * img_width + x1) * 4
            row_end = row_start + width * 4
            # 检查边界
            if row_end > len(bmp_data):
                log(f"[OCR] 裁剪超出数据范围: y={y}, row_end={row_end}, data_len={len(bmp_data)}, img_width={img_width}")
                return None
            cropped_bytes.extend(bmp_data[row_start:row_end])
        
        cropped_bytes = bytes(cropped_bytes)
        
        expected_cropped_len = width * height * 4
        if len(cropped_bytes) != expected_cropped_len:
            log(f"[OCR] 裁剪数据长度不匹配: 预期{expected_cropped_len}, 实际{len(cropped_bytes)}")
            return None
        
        # 应用OCR滤镜（如果指定了颜色）
        if filter_colors and filter_tolerance > 0:
            cropped_bytes = apply_ocr_filter(cropped_bytes, width, height, filter_colors, filter_tolerance)
        
        if use_bmp:
            image_data = create_bmp_from_bgra(cropped_bytes, width, height)
        else:
            image_data = create_png_from_bgra(cropped_bytes, width, height)
        
        if image_data is None:
            log(f"[OCR] 图片编码返回None")
            return None
            
        return image_data
    except Exception as e:
        log(f"[OCR] 裁剪失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def apply_ocr_filter(bgra_data, width, height, target_colors, tolerance):
    """
    应用OCR滤镜：保留目标颜色（在容差范围内）变成黑色，其他颜色变成白色
    
    Args:
        bgra_data: BGRA格式像素数据 (bytes)
        width: 宽度
        height: 高度
        target_colors: 目标颜色列表 [(R,G,B), ...]
        tolerance: 容差值
        
    Returns:
        bytes: 处理后的BGRA数据
    """
    if not target_colors:
        return bgra_data
    
    # 确保 bgra_data 是 bytearray（可修改）
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    
    # 黑色和白色
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    
    # 处理每个像素
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            if idx + 2 >= len(bgra_data):
                continue
            
            # 获取当前像素颜色 (BGRA)
            b = bgra_data[idx]
            g = bgra_data[idx + 1]
            r = bgra_data[idx + 2]
            
            # 检查是否匹配任何目标颜色
            is_target = False
            for target_color in target_colors:
                tr, tg, tb = target_color
                # 计算颜色差值
                diff = abs(r - tr) + abs(g - tg) + abs(b - tb)
                if diff <= tolerance * 3:  # 容差判断
                    is_target = True
                    break
            
            # 目标颜色变成黑色，其他颜色变成白色
            if is_target:
                bgra_data[idx] = BLACK[2]      # B = 0
                bgra_data[idx + 1] = BLACK[1]  # G = 0
                bgra_data[idx + 2] = BLACK[0]  # R = 0
            else:
                bgra_data[idx] = WHITE[2]      # B = 255
                bgra_data[idx + 1] = WHITE[1]  # G = 255
                bgra_data[idx + 2] = WHITE[0]  # R = 255
            # Alpha保持不变
    
    return bytes(bgra_data)

def create_png_from_bgra(bgra_data, width, height):
    """
    从BGRA像素数据创建PNG图片
    
    Args:
        bgra_data: BGRA格式像素数据 (bytes 或 list)
        width: 宽度
        height: 高度
        
    Returns:
        bytes: PNG格式数据
    """
    import zlib
    import struct
    
    # 确保 bgra_data 是 bytes 类型
    if not isinstance(bgra_data, bytes):
        try:
            bgra_data = bytes(bgra_data)
        except Exception as e:
            print(f"[PNG] 数据转换失败: {e}, 类型: {type(bgra_data)}")
            return None
    
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xffffffff
        return struct.pack('>I', len(data)) + c + struct.pack('>I', crc)
    
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    
    raw_data = bytearray()
    for y in range(height):
        raw_data.append(0)  # filter byte
        row_start = y * width * 4
        for x in range(width):
            idx = row_start + x * 4
            if idx + 3 < len(bgra_data):
                b = bgra_data[idx]
                g = bgra_data[idx + 1]
                r = bgra_data[idx + 2]
                a = bgra_data[idx + 3]
                raw_data.extend([r, g, b, a])
            else:
                # 数据不足，填充白色
                raw_data.extend([255, 255, 255, 255])
    
    compressed = zlib.compress(bytes(raw_data))
    
    png_data = signature
    png_data += chunk(b'IHDR', ihdr)
    png_data += chunk(b'IDAT', compressed)
    png_data += chunk(b'IEND', b'')
    
    return png_data

def create_bmp_from_bgra(bgra_data, width, height):
    """
    从BGRA像素数据创建BMP图片（无压缩，编码速度比PNG快10-20倍）
    
    Args:
        bgra_data: BGRA格式像素数据 (bytes 或 list)
        width: 宽度
        height: 高度
        
    Returns:
        bytes: BMP格式数据，失败返回None
    """
    import struct
    
    # 确保 bgra_data 是 bytes 类型
    if not isinstance(bgra_data, bytes):
        try:
            bgra_data = bytes(bgra_data)
        except Exception as e:
            print(f"[BMP] 数据转换失败: {e}, 类型: {type(bgra_data)}")
            return None
    
    # 检查数据有效性
    if bgra_data is None:
        return None
    
    expected_len = width * height * 4
    if len(bgra_data) < expected_len:
        # 数据不足，填充0
        bgra_data = bgra_data + b'\x00' * (expected_len - len(bgra_data))
    
    row_size = width * 4  # BGRA = 4 bytes per pixel
    # BMP行大小必须是4的倍数
    padding = (4 - row_size % 4) % 4
    image_size = (row_size + padding) * height
    file_size = 14 + 40 + image_size
    
    # BMP 文件头 (14字节)
    file_header = b'BM'                           # 签名
    file_header += struct.pack('<I', file_size)   # 文件大小
    file_header += struct.pack('<HH', 0, 0)       # 保留
    file_header += struct.pack('<I', 54)          # 数据偏移 (14 + 40)
    
    # DIB 头 (40字节, BITMAPINFOHEADER)
    dib_header = struct.pack('<I', 40)            # 头大小
    dib_header += struct.pack('<i', width)        # 宽度
    dib_header += struct.pack('<i', height)       # 高度（正数=倒向存储）
    dib_header += struct.pack('<HH', 1, 32)       # 平面数(1), 位深度(32)
    dib_header += struct.pack('<I', 0)            # 压缩方式 (0=无压缩)
    dib_header += struct.pack('<I', image_size)   # 图像大小
    dib_header += struct.pack('<i', 2835)         # X像素/米 (72 DPI)
    dib_header += struct.pack('<i', 2835)         # Y像素/米 (72 DPI)
    dib_header += struct.pack('<I', 0)            # 调色板颜色数
    dib_header += struct.pack('<I', 0)            # 重要颜色数
    
    # 像素数据（BMP是倒向存储，从底行到顶行）
    pixel_data = bytearray()
    for y in range(height - 1, -1, -1):  # 倒序遍历行
        row_start = y * row_size
        row = bgra_data[row_start:row_start + row_size]
        # 确保 row 是 bytes
        if not isinstance(row, bytes):
            row = bytes(row)
        # 如果行数据不足，填充黑色
        if len(row) < row_size:
            row = row + b'\x00' * (row_size - len(row))
        pixel_data.extend(row)
        pixel_data.extend(b'\x00' * padding)
    
    return file_header + dib_header + bytes(pixel_data)

def ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, port=None, log=_print, filter_colors=None, filter_tolerance=0):
    """
    使用OCR识别指定区域的数字（新版HTTP API）
    
    Args:
        bmp_data: 截图原始数据
        x1, y1: 左上角坐标（相对于游戏窗口客户区）
        x2, y2: 右下角坐标（相对于游戏窗口客户区）
        img_width: 截图宽度
        port: 端口号，None则使用默认端口1395
        filter_colors: 滤镜目标颜色列表 [(R,G,B), ...]
        filter_tolerance: 滤镜容差值
        
    Returns:
        tuple: (识别到的数字或None, 耗时秒数)
    """
    import requests
    import time
    import json
    import base64
    
    start_time = time.time()
    
    # 新后端默认端口1395
    if port is None:
        port = 1395
    
    if not check_ocr_server(port):
        log(f"[OCR] 服务端未运行: {port}", "ERROR")
        return None, 0
    
    image_data = crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=log, filter_colors=filter_colors, filter_tolerance=filter_tolerance)
    if image_data is None:
        log(f"[OCR] 裁剪失败: {x1}, {y1}, {x2}, {y2}", "ERROR")
        return None, 0
    
    url = f"http://127.0.0.1:{port}/api/ocr"
    try:
        # 将图片转为base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        data = {
            "base64": base64_image,
            "options": {
                "data.format": "text",
                "ocr.language": "models/config_en.txt",
                "ocr.cls": False,
                "tbpu.parser": "none"
            }
        }
        headers = {"Content-Type": "application/json"}
        
        r = requests.post(
            url,
            data=json.dumps(data),
            headers=headers,
            timeout=10
        )
        
        elapsed = time.time() - start_time
        
        if r.status_code == 200:
            res = r.json()
            if res.get('code') == 100:
                # 成功识别
                text = str(res.get('data', '')).strip()
                number = extract_number(text)
                return number, elapsed
            else:
                return None, elapsed
        
        log(f"[OCR] 请求失败: HTTP {r.status_code} ({elapsed:.3f}s)")
        return None, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        log(f"[OCR] 请求异常: {e} ({elapsed:.3f}s)")
        return None, elapsed

def extract_number(text):
    """
    从文本中提取数字
    
    Args:
        text: OCR识别的文本
        
    Returns:
        int or None: 提取的数字，无法提取返回None
    """
    import re
    
    text = text.replace(' ', '').replace(',', '').replace('O', '0').replace('o', '0')
    
    numbers = re.findall(r'-?\d+', text)
    
    if numbers:
        try:
            num = int(numbers[0])
            if num != 0:
                return num
        except:
            pass
    
    return None

import os
if __name__ == "__main__":
    print(os.path.dirname(os.path.abspath(__file__)))
    
    # 测试OCR滤镜功能
    def test_ocr_filter():
        """测试OCR滤镜：对目标PNG图标应用滤镜并输出结果"""
        import glob
        
        # 查找当前目录下的PNG文件
        png_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "*.png"))
        
        if not png_files:
            print("[Filter Test] 未找到PNG文件，跳过测试")
            return
        
        # 使用第一个找到的PNG文件进行测试
        test_png = png_files[0]
        print(f"[Filter Test] 使用文件: {test_png}")
        
        try:
            from PIL import Image
            
            # 打开PNG文件
            img = Image.open(test_png)
            
            # 转换为RGBA格式
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            width, height = img.size
            print(f"[Filter Test] 图片尺寸: {width}x{height}")
            
            # 获取像素数据 (RGBA格式)
            img_data = img.tobytes()
            
            # 转换为BGRA格式
            bgra_data = bytearray()
            for i in range(0, len(img_data), 4):
                r, g, b, a = img_data[i], img_data[i+1], img_data[i+2], img_data[i+3]
                bgra_data.extend([b, g, r, a])
            
            # 定义测试用的目标颜色（白色/浅色文字）
            target_colors = [
                (202, 70, 255)
            ]
            tolerance = 1
            
            print(f"[Filter Test] 目标颜色: {target_colors}, 容差: {tolerance}")
            
            # 应用滤镜
            filtered_data = apply_ocr_filter(bytes(bgra_data), width, height, target_colors, tolerance)
            
            # 将BGRA转换回RGBA用于保存
            rgba_data = bytearray()
            for i in range(0, len(filtered_data), 4):
                b, g, r, a = filtered_data[i], filtered_data[i+1], filtered_data[i+2], filtered_data[i+3]
                rgba_data.extend([r, g, b, a])
            
            # 保存滤镜后的图片
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "filter_test_output.png")
            
            filtered_img = Image.frombytes('RGBA', (width, height), bytes(rgba_data))
            filtered_img.save(output_path)
            
            print(f"[Filter Test] 滤镜结果已保存: {output_path}")
            print(f"[Filter Test] 目标颜色 -> 黑色, 其他颜色 -> 白色")
            
        except ImportError:
            print("[Filter Test] 需要PIL库，请安装: pip install Pillow")
        except Exception as e:
            print(f"[Filter Test] 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行滤镜测试
    test_ocr_filter()