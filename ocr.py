
import requests
import time
import json
import base64
import re

from image import (
    apply_filters_chain,
    apply_ocr_filter,
    create_bmp_from_bgra,
    create_png_from_bgra,
)

_ocr_port = 1395
_session_cache = {}


def _get_session(key):
    if key not in _session_cache:
        _session_cache[key] = requests.Session()
    return _session_cache[key]


def _print(msg, level="INFO"):
    print(f"[{level}] {msg}")


def _extract_ocr_text(res):
    if not isinstance(res, dict):
        return str(res).strip()
    if res.get('code') == 100:
        return str(res.get('data', '')).strip()
    for key in ('data', 'result', 'text', 'content', 'output'):
        if key in res:
            val = res[key]
            if isinstance(val, str):
                return val.strip()
            if isinstance(val, list):
                texts = []
                for item in val:
                    if isinstance(item, dict):
                        for tk in ('text', 'content', 'result'):
                            if tk in item:
                                texts.append(str(item[tk]))
                    elif isinstance(item, str):
                        texts.append(item)
                if texts:
                    return ' '.join(texts).strip()
            return str(val).strip()
    return str(res).strip()


def _parse_options_data(api_data):
    if not api_data:
        return None
    if isinstance(api_data, dict):
        return api_data
    if isinstance(api_data, str):
        try:
            return json.loads(api_data)
        except (json.JSONDecodeError, TypeError):
            pass
    return None


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


def check_ocr_api(ip, port):
    try:
        r = requests.get(f"http://{ip}:{port}/", timeout=2)
        return r.status_code < 500
    except:
        return False


def extract_number(text):
    replaceText = {" ":'',",":'','O':'0','o':'0','B':'8',"Z":'2'}
    for replace, replace_with in replaceText.items():
        text = text.replace(replace, replace_with)
    numbers = re.findall(r'-?\d+', text)
    if numbers:
        try:
            num = int(numbers[0])
            return num
        except:
            pass
    return None


def crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=_print, use_bmp=True, filter_colors=None, filter_tolerance=0, filters=None, parse_color_func=None):
    filter_time = 0
    try:
        width = x2 - x1
        height = y2 - y1
        if width <= 0 or height <= 0:
            log(f"[OCR] 裁剪区域无效: width={width}, height={height}")
            return None, filter_time
        try:
            if not isinstance(bmp_data, bytes):
                bmp_data = bytes(bmp_data)
        except Exception as e:
            log(f"[OCR] 数据类型转换失败: {e}, 类型: {type(bmp_data)}")
            return None, filter_time
        if bmp_data is None or len(bmp_data) == 0:
            log(f"[OCR] 输入数据为空")
            return None, filter_time
        expected_data_len = img_width * 4 * (y2 + 1)
        if len(bmp_data) < expected_data_len:
            log(f"[OCR] 输入数据不足: 需要至少{expected_data_len} bytes, 实际{len(bmp_data)} bytes, img_width={img_width}")
            return None, filter_time
        cropped_bytes = bytearray()
        for y in range(y1, y2):
            row_start = (y * img_width + x1) * 4
            row_end = row_start + width * 4
            if row_end > len(bmp_data):
                log(f"[OCR] 裁剪超出数据范围: y={y}, row_end={row_end}, data_len={len(bmp_data)}, img_width={img_width}")
                return None, filter_time
            cropped_bytes.extend(bmp_data[row_start:row_end])
        cropped_bytes = bytes(cropped_bytes)
        expected_cropped_len = width * height * 4
        if len(cropped_bytes) != expected_cropped_len:
            log(f"[OCR] 裁剪数据长度不匹配: 预期{expected_cropped_len}, 实际{len(cropped_bytes)}")
            return None, filter_time
        if filters:
            ft0 = time.time()
            cropped_bytes = apply_filters_chain(cropped_bytes, width, height, filters, parse_color_func)
            filter_time = time.time() - ft0
        elif filter_colors and filter_tolerance > 0:
            ft0 = time.time()
            cropped_bytes = apply_ocr_filter(cropped_bytes, width, height, filter_colors, filter_tolerance)
            filter_time = time.time() - ft0
        if use_bmp:
            image_data = create_bmp_from_bgra(cropped_bytes, width, height)
        else:
            image_data = create_png_from_bgra(cropped_bytes, width, height)
        if image_data is None:
            log(f"[OCR] 图片编码返回None")
            return None, filter_time
        return image_data, filter_time
    except Exception as e:
        log(f"[OCR] 裁剪失败: {e}")
        import traceback
        traceback.print_exc()
        return None, filter_time


def ocr_recognize_number(bmp_data, x1, y1, x2, y2, img_width, port=None, log=_print, filter_colors=None, filter_tolerance=0, filters=None, parse_color_func=None, api_ip=None, api_data=None):
    start_time = time.time()
    if port is None:
        port = 1395
    image_data, filter_time = crop_image_for_ocr(bmp_data, x1, y1, x2, y2, img_width, log=log, filter_colors=filter_colors, filter_tolerance=filter_tolerance, filters=filters, parse_color_func=parse_color_func)
    if image_data is None:
        log(f"[OCR] 裁剪失败: {x1}, {y1}, {x2}, {y2}", "ERROR")
        return None, 0, filter_time
    base64_image = base64.b64encode(image_data).decode('utf-8')

    if api_ip:
        ip = api_ip
    else:
        ip = "127.0.0.1"

    url = f"http://{ip}:{port}/api/ocr"
    options = _parse_options_data(api_data)
    if not options or not isinstance(options, dict):
        options = {
            "data.format": "text",
            "ocr.language": "models/config_en.txt",
            "ocr.cls": False,
            "tbpu.parser": "none"
        }
    data = {"base64": base64_image, "options": options}
    headers = {"Content-Type": "application/json"}
    session = _get_session(ip)
    try:
        r = session.post(url, data=json.dumps(data), headers=headers, timeout=10)
        elapsed = time.time() - start_time - filter_time
        if r.status_code == 200:
            try:
                res = r.json()
            except Exception:
                text = r.text.strip()
            else:
                text = _extract_ocr_text(res)
            number = extract_number(text)
            return number, elapsed, filter_time
        label = "自定义API" if api_ip else "OCR"
        log(f"[{label}] 请求失败: HTTP {r.status_code} ({elapsed:.3f}s)")
        return None, elapsed, filter_time
    except Exception as e:
        elapsed = time.time() - start_time - filter_time
        label = "自定义API" if api_ip else "OCR"
        log(f"[{label}] 请求异常: {e} ({elapsed:.3f}s)")
        return None, elapsed, filter_time
