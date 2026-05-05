"""
capture_dxgi.py - DXGI 截图模块

使用 dxcam 库实现高性能屏幕截图。
相比 GDI BitBlt 方式，DXGI 延迟更低，CPU 占用更少。

依赖: dxcam (pip install dxcam), numpy
兼容: Windows 8+
"""

import ctypes
import ctypes.wintypes
import logging

logger = logging.getLogger(__name__)

user32 = ctypes.windll.user32


_DXCAM_INSTANCE = None
_DXCAM_AVAILABLE = None


def _check_dxcam():
    """检查 dxcam 库是否可用"""
    global _DXCAM_AVAILABLE
    if _DXCAM_AVAILABLE is not None:
        return _DXCAM_AVAILABLE
    try:
        import dxcam
        _DXCAM_AVAILABLE = True
    except ImportError:
        _DXCAM_AVAILABLE = False
    return _DXCAM_AVAILABLE


def is_dxgi_available():
    """检查 DXGI 截图是否可用"""
    return _check_dxcam()


def capture_dxgi_fast(region=None, hwnd=None):
    """
    使用 dxcam 快速截图

    Args:
        region: [x, y, width, height] 客户区相对坐标
        hwnd: 窗口句柄

    Returns:
        (bmp_data, rx, ry, rw, rh, img_width) 与 GDI capture_screen_fast 兼容
    """
    global _DXCAM_INSTANCE

    if not _check_dxcam():
        return None, 0, 0, 0, 0, 0

    try:
        import dxcam

        user32.SetProcessDPIAware()

        if _DXCAM_INSTANCE is None:
            _DXCAM_INSTANCE = dxcam.create(output_color="BGRA")

        camera = _DXCAM_INSTANCE

        if hwnd:
            client_point = ctypes.wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(client_point))
            client_left = client_point.x
            client_top = client_point.y

            client_rect = ctypes.wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(client_rect))
            client_width = client_rect.right - client_rect.left
            client_height = client_rect.bottom - client_rect.top

            if region:
                rx, ry, rw, rh = [int(x) for x in region]
                rx = max(0, rx)
                ry = max(0, ry)
                rw = max(1, min(rw, client_width - rx))
                rh = max(1, min(rh, client_height - ry))
            else:
                rx, ry, rw, rh = 0, 0, client_width, client_height

            left = client_left + rx
            top = client_top + ry
            right = left + rw
            bottom = top + rh

            frame = camera.grab(region=(left, top, right, bottom))
        else:
            if region:
                rx, ry, rw, rh = [int(x) for x in region]
                frame = camera.grab(region=(rx, ry, rx + rw, ry + rh))
            else:
                rx, ry = 0, 0
                frame = camera.grab()
                if frame is not None:
                    rh, rw = frame.shape[:2]

        if frame is None:
            return None, 0, 0, 0, 0, 0

        bmp_data = frame.tobytes()
        img_width = rw if region or hwnd else frame.shape[1]
        return bmp_data, rx, ry, rw, rh, img_width

    except Exception as e:
        logger.debug(f"DXGI 截图失败: {e}")
        return None, 0, 0, 0, 0, 0


def release_dxgi():
    """释放 DXGI 资源"""
    global _DXCAM_INSTANCE
    if _DXCAM_INSTANCE is not None:
        try:
            _DXCAM_INSTANCE.release()
        except Exception:
            pass
        _DXCAM_INSTANCE = None
