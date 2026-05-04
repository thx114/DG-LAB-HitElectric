
import requests
import time
import json
import base64
import re
import struct
import zlib

_ocr_port = 1395


def _print(msg, level="INFO"):
    print(f"[{level}] {msg}")


def get_ocr_server_url(port=None):
    if port is None:
        port = _ocr_port
    return f"http://127.0.0.1:{port}"


def set_ocr_port(port):
    global _ocr_port
    _ocr_port = port
    print(f"[OCR] 端口设置为: {port}")


def check_ocr_server(port=None):
    if port is None:
        port = 1395
    try:
        r = requests.get(f"http://127.0.0.1:{port}/", timeout=2)
        return r.status_code == 200
    except:
        return False


def extract_number(text):
    replaceText = {" ":'',",":'','O':'0','o':'0','B':'8',"Z":'2'}
    text = text.replace(' ', '').replace(',', '').replace('O', '0').replace('o', '0')
    numbers = re.findall(r'-?\d+', text)
    if numbers:
        try:
            num = int(numbers[0])
            return num
        except:
            pass
    return None


def apply_filter_replace_color(bgra_data, width, height, target_colors, tolerance, feather=0):
    if not target_colors:
        return bgra_data
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    if feather > 0:
        diff_map = bytearray(width * height)
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4
                if idx + 2 >= len(bgra_data):
                    continue
                b = bgra_data[idx]
                g = bgra_data[idx + 1]
                r = bgra_data[idx + 2]
                min_diff = 999999
                for target_color in target_colors:
                    tr, tg, tb = target_color
                    diff = abs(r - tr) + abs(g - tg) + abs(b - tb)
                    if diff < min_diff:
                        min_diff = diff
                threshold = tolerance * 3
                if min_diff <= threshold:
                    diff_map[y * width + x] = 0
                elif feather > 0 and min_diff <= threshold + feather * 3:
                    ratio = 1.0 - (min_diff - threshold) / (feather * 3)
                    diff_map[y * width + x] = int((1.0 - ratio) * 255)
                else:
                    diff_map[y * width + x] = 255
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4
                v = diff_map[y * width + x]
                bgra_data[idx] = v
                bgra_data[idx + 1] = v
                bgra_data[idx + 2] = v
    else:
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4
                if idx + 2 >= len(bgra_data):
                    continue
                b = bgra_data[idx]
                g = bgra_data[idx + 1]
                r = bgra_data[idx + 2]
                is_target = False
                for target_color in target_colors:
                    tr, tg, tb = target_color
                    diff = abs(r - tr) + abs(g - tg) + abs(b - tb)
                    if diff <= tolerance * 3:
                        is_target = True
                        break
                if is_target:
                    bgra_data[idx] = 0
                    bgra_data[idx + 1] = 0
                    bgra_data[idx + 2] = 0
                else:
                    bgra_data[idx] = 255
                    bgra_data[idx + 1] = 255
                    bgra_data[idx + 2] = 255
    return bytes(bgra_data)


def apply_filter_invert(bgra_data, width, height):
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    for i in range(0, len(bgra_data) - 2, 4):
        bgra_data[i] = 255 - bgra_data[i]
        bgra_data[i + 1] = 255 - bgra_data[i + 1]
        bgra_data[i + 2] = 255 - bgra_data[i + 2]
    return bytes(bgra_data)


def apply_filter_contrast(bgra_data, width, height, contrast):
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
    for i in range(0, len(bgra_data) - 2, 4):
        for c in range(3):
            val = bgra_data[i + c]
            val = int(factor * (val - 128) + 128)
            bgra_data[i + c] = max(0, min(255, val))
    return bytes(bgra_data)


def apply_filter_channel(bgra_data, width, height, channel):
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    channel_map = {"r": 2, "g": 1, "b": 0}
    keep_idx = channel_map.get(channel.lower(), 2)
    for i in range(0, len(bgra_data) - 2, 4):
        val = bgra_data[i + keep_idx]
        bgra_data[i] = val
        bgra_data[i + 1] = val
        bgra_data[i + 2] = val
    return bytes(bgra_data)


def apply_filter_dilate(bgra_data, width, height, iterations=1):
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    data_len = len(bgra_data)
    full_iters = int(iterations)
    has_half = (iterations - full_iters) >= 0.5
    for _ in range(full_iters):
        result = bytearray(bgra_data)
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = (y * width + x) * 4
                if idx + 3 >= data_len:
                    continue
                if bgra_data[idx] < 128 or bgra_data[idx + 1] < 128 or bgra_data[idx + 2] < 128:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            nidx = ((y + dy) * width + (x + dx)) * 4
                            if nidx + 3 >= data_len:
                                continue
                            if bgra_data[nidx] > 128 and bgra_data[nidx + 1] > 128 and bgra_data[nidx + 2] > 128:
                                result[nidx] = 0
                                result[nidx + 1] = 0
                                result[nidx + 2] = 0
        bgra_data = result
    if has_half:
        result = bytearray(bgra_data)
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                idx = (y * width + x) * 4
                if idx + 3 >= data_len:
                    continue
                if bgra_data[idx] < 128 or bgra_data[idx + 1] < 128 or bgra_data[idx + 2] < 128:
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nidx = ((y + dy) * width + (x + dx)) * 4
                        if nidx + 3 >= data_len:
                            continue
                        if bgra_data[nidx] > 128 and bgra_data[nidx + 1] > 128 and bgra_data[nidx + 2] > 128:
                            result[nidx] = 0
                            result[nidx + 1] = 0
                            result[nidx + 2] = 0
        bgra_data = result
    return bytes(bgra_data)


def apply_filter_contour(bgra_data, width, height):
    if isinstance(bgra_data, bytes):
        bgra_data = bytearray(bgra_data)
    result = bytearray(len(bgra_data))
    for i in range(len(result)):
        result[i] = 255
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            idx = (y * width + x) * 4
            is_dark = bgra_data[idx] < 128
            neighbors_dark = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    nidx = ((y + dy) * width + (x + dx)) * 4
                    if bgra_data[nidx] < 128:
                        neighbors_dark += 1
            if is_dark and neighbors_dark < 8:
                result[idx] = 0
                result[idx + 1] = 0
                result[idx + 2] = 0
    return bytes(result)


FILTER_FUNCTIONS = {
    "replace_color": lambda data, w, h, params: apply_filter_replace_color(
        data, w, h, params.get("parsed_colors", []), params.get("tolerance", 30), params.get("feather", 0)
    ),
    "invert": lambda data, w, h, params: apply_filter_invert(data, w, h),
    "contrast": lambda data, w, h, params: apply_filter_contrast(data, w, h, params.get("value", 50)),
    "channel": lambda data, w, h, params: apply_filter_channel(data, w, h, params.get("channel", "r")),
    "dilate": lambda data, w, h, params: apply_filter_dilate(data, w, h, params.get("iterations", 2) / 2),
    "contour": lambda data, w, h, params: apply_filter_contour(data, w, h),
    "python": None,
}


def apply_filters_chain(bgra_data, width, height, filters, parse_color_func=None):
    for f in filters:
        f_type = f.get("type", "")
        if f_type == "replace_color" and parse_color_func:
            colors_str = f.get("colors", "")
            parsed = parse_color_func(colors_str)
            f["parsed_colors"] = parsed
        if f_type == "python":
            code = f.get("code", "")
            if code:
                try:
                    local_vars = {"data": bgra_data if isinstance(bgra_data, bytearray) else bytearray(bgra_data),
                                  "width": width, "height": height}
                    exec(code, {"__builtins__": __builtins__}, local_vars)
                    result = local_vars.get("data", bgra_data)
                    if isinstance(result, (bytes, bytearray)):
                        bgra_data = bytes(result)
                except Exception as e:
                    print(f"[OCR] Python滤镜执行失败: {e}")
            continue
        fn = FILTER_FUNCTIONS.get(f_type)
        if fn:
            bgra_data = fn(bgra_data, width, height, f)
    return bgra_data


def apply_ocr_filter(bgra_data, width, height, target_colors, tolerance):
    return apply_filter_replace_color(bgra_data, width, height, target_colors, tolerance)


def crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=_print, use_bmp=True, filter_colors=None, filter_tolerance=0, filters=None, parse_color_func=None):
    try:
        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            log(f"[OCR] 裁剪区域无效: width={width}, height={height}")
            return None
        try:
            if not isinstance(bmp_data, bytes):
                bmp_data = bytes(bmp_data)
        except Exception as e:
            log(f"[OCR] 数据类型转换失败: {e}, 类型: {type(bmp_data)}")
            return None
        if bmp_data is None or len(bmp_data) == 0:
            log(f"[OCR] 输入数据为空")
            return None
        expected_data_len = img_width * 4 * (y2 + 1)
        if len(bmp_data) < expected_data_len:
            log(f"[OCR] 输入数据不足: 需要至少{expected_data_len} bytes, 实际{len(bmp_data)} bytes, img_width={img_width}")
            return None
        cropped_bytes = bytearray()
        for y in range(y1, y2):
            row_start = (y * img_width + x1) * 4
            row_end = row_start + width * 4
            if row_end > len(bmp_data):
                log(f"[OCR] 裁剪超出数据范围: y={y}, row_end={row_end}, data_len={len(bmp_data)}, img_width={img_width}")
                return None
            cropped_bytes.extend(bmp_data[row_start:row_end])
        cropped_bytes = bytes(cropped_bytes)
        expected_cropped_len = width * height * 4
        if len(cropped_bytes) != expected_cropped_len:
            log(f"[OCR] 裁剪数据长度不匹配: 预期{expected_cropped_len}, 实际{len(cropped_bytes)}")
            return None
        if filters:
            cropped_bytes = apply_filters_chain(cropped_bytes, width, height, filters, parse_color_func)
        elif filter_colors and filter_tolerance > 0:
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


def ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, port=None, log=_print, filter_colors=None, filter_tolerance=0, filters=None, parse_color_func=None):
    start_time = time.time()
    if port is None:
        port = 1395
    if not check_ocr_server(port):
        log(f"[OCR] 服务端未运行: {port}", "ERROR")
        return None, 0
    image_data = crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=log, filter_colors=filter_colors, filter_tolerance=filter_tolerance, filters=filters, parse_color_func=parse_color_func)
    if image_data is None:
        log(f"[OCR] 裁剪失败: {x1}, {y1}, {x2}, {y2}", "ERROR")
        return None, 0
    url = f"http://127.0.0.1:{port}/api/ocr"
    try:
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
        r = requests.post(url, data=json.dumps(data), headers=headers, timeout=10)
        elapsed = time.time() - start_time
        if r.status_code == 200:
            res = r.json()
            if res.get('code') == 100:
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


def create_png_from_bgra(bgra_data, width, height):
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
        raw_data.append(0)
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
                raw_data.extend([255, 255, 255, 255])
    compressed = zlib.compress(bytes(raw_data))
    png_data = signature
    png_data += chunk(b'IHDR', ihdr)
    png_data += chunk(b'IDAT', compressed)
    png_data += chunk(b'IEND', b'')
    return png_data


def create_bmp_from_bgra(bgra_data, width, height):
    if not isinstance(bgra_data, bytes):
        try:
            bgra_data = bytes(bgra_data)
        except Exception as e:
            print(f"[BMP] 数据转换失败: {e}, 类型: {type(bgra_data)}")
            return None
    if bgra_data is None:
        return None
    expected_len = width * height * 4
    if len(bgra_data) < expected_len:
        bgra_data = bgra_data + b'\x00' * (expected_len - len(bgra_data))
    row_size = width * 4
    padding = (4 - row_size % 4) % 4
    image_size = (row_size + padding) * height
    file_size = 14 + 40 + image_size
    file_header = b'BM'
    file_header += struct.pack('<I', file_size)
    file_header += struct.pack('<HH', 0, 0)
    file_header += struct.pack('<I', 54)
    dib_header = struct.pack('<I', 40)
    dib_header += struct.pack('<i', width)
    dib_header += struct.pack('<i', height)
    dib_header += struct.pack('<HH', 1, 32)
    dib_header += struct.pack('<I', 0)
    dib_header += struct.pack('<I', image_size)
    dib_header += struct.pack('<i', 2835)
    dib_header += struct.pack('<i', 2835)
    dib_header += struct.pack('<I', 0)
    dib_header += struct.pack('<I', 0)
    pixel_data = bytearray()
    for y in range(height - 1, -1, -1):
        row_start = y * row_size
        row = bgra_data[row_start:row_start + row_size]
        if not isinstance(row, bytes):
            row = bytes(row)
        if len(row) < row_size:
            row = row + b'\x00' * (row_size - len(row))
        pixel_data.extend(row)
        pixel_data.extend(b'\x00' * padding)
    return file_header + dib_header + bytes(pixel_data)
