import struct
import zlib
import numpy as np


def get_pixel_color(bmp_data, x, y, img_width):
    idx = (y * img_width + x) * 4
    if idx + 2 < len(bmp_data):
        b = bmp_data[idx]
        g = bmp_data[idx + 1]
        r = bmp_data[idx + 2]
        return (r, g, b)
    return (0, 0, 0)


def parse_coordinate(coord):
    if isinstance(coord, list):
        if len(coord) >= 2:
            return [int(coord[0]), int(coord[1])]
        return [0, 0]
    if isinstance(coord, str):
        parts = coord.replace(' ', '').split(',')
        if len(parts) >= 2:
            try:
                return [int(parts[0]), int(parts[1])]
            except ValueError:
                return [0, 0]
    if isinstance(coord, (tuple, list)):
        try:
            return [int(coord[0]), int(coord[1])]
        except (ValueError, TypeError, IndexError):
            return [0, 0]
    return [0, 0]


def parse_coordinates(coords):
    if not coords:
        return []
    if isinstance(coords, list):
        if len(coords) > 0 and isinstance(coords[0], (list, tuple)):
            return [parse_coordinate(c) for c in coords]
        return [parse_coordinate(coords)]
    if isinstance(coords, str):
        result = []
        groups = coords.split('|')
        for group in groups:
            group = group.strip()
            if not group:
                continue
            parts = group.replace(' ', '').split(',')
            if len(parts) >= 2:
                try:
                    result.append([int(parts[0]), int(parts[1])])
                except ValueError:
                    continue
        return result
    return []


def parse_color(color):
    if isinstance(color, (list, tuple)):
        if len(color) >= 3:
            return (int(color[0]), int(color[1]), int(color[2]))
        return None
    if isinstance(color, str):
        color = color.strip()
        if color.startswith('#'):
            hex_color = color[1:]
            if len(hex_color) == 6:
                try:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    return (r, g, b)
                except ValueError:
                    return None
    return None


def parse_colors(colors):
    if not colors:
        return []
    if isinstance(colors, list):
        if len(colors) > 0 and isinstance(colors[0], (list, tuple)):
            result = []
            for c in colors:
                parsed = parse_color(c)
                if parsed:
                    result.append(parsed)
            return result
        parsed = parse_color(colors)
        return [parsed] if parsed else []
    if isinstance(colors, str):
        result = []
        parts = colors.split('|')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            parsed = parse_color(part)
            if parsed:
                result.append(parsed)
        return result
    return []


def color_match(pixel, target_colors, tolerance=30):
    if not target_colors:
        return False
    r, g, b = pixel
    if isinstance(target_colors, (list, tuple)) and len(target_colors) >= 3 and not isinstance(target_colors[0], (list, tuple)):
        target_colors = [target_colors]
    for target in target_colors:
        if isinstance(target, (list, tuple)) and len(target) >= 3:
            tr, tg, tb = target[0], target[1], target[2]
            diff = abs(r - tr) + abs(g - tg) + abs(b - tb)
            if diff <= tolerance * 3:
                return True
    return False


def detect_bar_length(bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points, capture_region=None):
    if capture_region is None:
        capture_region = [0, 0, 0, 0]
    capture_offset_x, capture_offset_y = capture_region[0], capture_region[1]

    if not isinstance(start_pos, (list, tuple)) or len(start_pos) < 2 or not isinstance(end_pos, (list, tuple)) or len(end_pos) < 2:
        return 0, "0"

    sx, sy = start_pos[0] - capture_offset_x, start_pos[1] - capture_offset_y
    ex, ey = end_pos[0] - capture_offset_x, end_pos[1] - capture_offset_y
    max_w = capture_region[2] if len(capture_region) >= 3 else img_width
    max_h = capture_region[3] if len(capture_region) >= 4 else 0
    sx = max(0, min(sx, max_w - 1))
    sy = max(0, min(sy, max_h - 1))
    ex = max(0, min(ex, max_w - 1))
    ey = max(0, min(ey, max_h - 1))

    if sx == ex:
        ys = np.linspace(sy, ey, sample_points + 1, dtype=np.int32)
        xs = np.full_like(ys, sx)
    else:
        xs = np.linspace(sx, ex, sample_points + 1, dtype=np.int32)
        ys = np.full_like(xs, sy)

    valid = (xs >= 0) & (xs < img_width) & (ys >= 0)
    xs = xs[valid]
    ys = ys[valid]

    if isinstance(bmp_data, np.ndarray):
        arr = bmp_data
    else:
        arr = np.frombuffer(bmp_data, dtype=np.uint8)
    h = (len(arr) // 4) // img_width if img_width > 0 else 0
    valid = valid & (ys < h)
    xs = xs[valid]
    ys = ys[valid]
    if len(xs) == 0:
        return 0, "0"

    arr = arr[:h * img_width * 4].reshape(h, img_width, 4)
    pixels = arr[ys, xs, 2::-1]

    bar_colors = [c for c in bar_colors if isinstance(c, (list, tuple)) and len(c) >= 3]
    if not bar_colors:
        return 0, "0"

    pixels_arr = pixels.astype(np.int16)
    min_diff = np.full(len(pixels_arr), 999999, dtype=np.int32)
    for tr, tg, tb in bar_colors:
        diff = np.abs(pixels_arr[:, 0] - tr) + np.abs(pixels_arr[:, 1] - tg) + np.abs(pixels_arr[:, 2] - tb)
        min_diff = np.minimum(min_diff, diff)
    matched = min_diff <= tolerance * 3
    filled_count = int(np.count_nonzero(matched))

    color_matches = []
    for tr, tg, tb in bar_colors:
        diff = np.abs(pixels_arr[:, 0] - tr) + np.abs(pixels_arr[:, 1] - tg) + np.abs(pixels_arr[:, 2] - tb)
        color_matches.append(int(np.count_nonzero(diff <= tolerance * 3)))

    percentage = (filled_count / sample_points) * 100
    color_result = '+'.join(map(str, color_matches)) if color_matches else '0'
    return percentage, color_result


def _np_color_match_pixels(pixels, target_colors, tolerance):
    if not target_colors:
        return np.zeros(len(pixels), dtype=bool)
    if isinstance(target_colors, (list, tuple)) and len(target_colors) >= 3 and not isinstance(target_colors[0], (list, tuple)):
        target_colors = [target_colors]
    target_colors = [c for c in target_colors if isinstance(c, (list, tuple)) and len(c) >= 3]
    if not target_colors:
        return np.zeros(len(pixels), dtype=bool)
    pixels_arr = np.asarray(pixels, dtype=np.int16)
    min_diff = np.full(len(pixels), 999999, dtype=np.int32)
    for tr, tg, tb in target_colors:
        diff = np.abs(pixels_arr[:, 0] - tr) + np.abs(pixels_arr[:, 1] - tg) + np.abs(pixels_arr[:, 2] - tb)
        min_diff = np.minimum(min_diff, diff)
    return min_diff <= tolerance * 3


def check_positions_match(bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors=None):
    if not positions or not colors:
        return False, "0"
    if isinstance(bmp_data, np.ndarray):
        arr = bmp_data
    else:
        arr = np.frombuffer(bmp_data, dtype=np.uint8)
    h = (len(arr) // 4) // img_width if img_width > 0 else 0
    arr = arr[:h * img_width * 4].reshape(h, img_width, 4)
    valid_positions = []
    coords = []
    for pos in positions:
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            x = pos[0] - capture_region[0]
            y = pos[1] - capture_region[1]
            if 0 <= x < img_width and 0 <= y < h:
                valid_positions.append(True)
                coords.append((y, x))
            else:
                valid_positions.append(False)
        else:
            valid_positions.append(False)
    if not coords:
        return False, "0"
    ys, xs = zip(*coords)
    pixels = arr[ys, xs, 2::-1]
    matched = _np_color_match_pixels(pixels, colors, tolerance)
    if extra_colors is not None and extra_colors is not colors:
        matched_extra = _np_color_match_pixels(pixels, extra_colors, tolerance)
        matched = matched | matched_extra
    result_bits = []
    match_count = 0
    idx = 0
    for valid in valid_positions:
        if valid:
            bit = '1' if matched[idx] else '0'
            idx += 1
        else:
            bit = '0'
        result_bits.append(bit)
        if bit == '1':
            match_count += 1
    all_match = match_count == len(positions)
    return all_match, ''.join(result_bits)


def check_positions_count_match(bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold):
    if not positions or not colors:
        return False, "0", 0
    if isinstance(bmp_data, np.ndarray):
        arr = bmp_data
    else:
        arr = np.frombuffer(bmp_data, dtype=np.uint8)
    h = (len(arr) // 4) // img_width if img_width > 0 else 0
    arr = arr[:h * img_width * 4].reshape(h, img_width, 4)
    coords = []
    for pos in positions:
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            x = pos[0] - capture_region[0]
            y = pos[1] - capture_region[1]
            if 0 <= x < img_width and 0 <= y < h:
                coords.append((y, x))
    if not coords:
        return False, "0", 0
    ys, xs = zip(*coords)
    pixels = arr[ys, xs, 2::-1]
    matched = _np_color_match_pixels(pixels, colors, tolerance)
    match_count = int(np.count_nonzero(matched))
    ratio = match_count / len(positions)
    matched_result = ratio >= match_threshold
    return matched_result, str(match_count), match_count


def _bgra_to_array(bgra_data, width, height):
    if isinstance(bgra_data, np.ndarray):
        if bgra_data.shape == (height, width, 4):
            return bgra_data
        if bgra_data.size != height * width * 4:
            return np.zeros((height, width, 4), dtype=np.uint8)
        return bgra_data.reshape(height, width, 4).copy()
    arr = np.frombuffer(bgra_data, dtype=np.uint8)
    if arr.size != height * width * 4:
        return np.zeros((height, width, 4), dtype=np.uint8)
    return arr.reshape(height, width, 4).copy()


def _np_replace_color(arr, target_colors, tolerance, feather=0):
    if not target_colors:
        return arr
    r = arr[:, :, 2].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 0].astype(np.int16)
    min_diff = np.full(arr.shape[:2], 999999, dtype=np.int32)
    for tr, tg, tb in target_colors:
        diff = np.abs(r - tr) + np.abs(g - tg) + np.abs(b - tb)
        min_diff = np.minimum(min_diff, diff)
    threshold = tolerance * 3
    if feather > 0:
        is_target = min_diff <= threshold
        is_feather = (~is_target) & (min_diff <= threshold + feather * 3)
        diff_map = np.full(arr.shape[:2], 255, dtype=np.uint8)
        diff_map[is_target] = 0
        if np.any(is_feather):
            ratio = 1.0 - (min_diff[is_feather].astype(np.float64) - threshold) / (feather * 3)
            diff_map[is_feather] = ((1.0 - ratio) * 255).astype(np.uint8)
        arr[:, :, 0] = diff_map
        arr[:, :, 1] = diff_map
        arr[:, :, 2] = diff_map
    else:
        is_target = min_diff <= threshold
        arr[is_target, 0] = 0
        arr[is_target, 1] = 0
        arr[is_target, 2] = 0
        arr[~is_target, 0] = 255
        arr[~is_target, 1] = 255
        arr[~is_target, 2] = 255
    return arr


def _np_invert(arr):
    arr[:, :, 0] = 255 - arr[:, :, 0]
    arr[:, :, 1] = 255 - arr[:, :, 1]
    arr[:, :, 2] = 255 - arr[:, :, 2]
    return arr


def _np_contrast(arr, contrast):
    factor = (259 * (contrast + 255)) / (255 * (259 - contrast))
    for c in range(3):
        val = arr[:, :, c].astype(np.float64)
        val = factor * (val - 128) + 128
        arr[:, :, c] = np.clip(val, 0, 255).astype(np.uint8)
    return arr


def _np_channel(arr, channel):
    channel_map = {"r": 2, "g": 1, "b": 0}
    keep_idx = channel_map.get(channel.lower(), 2)
    val = arr[:, :, keep_idx].copy()
    arr[:, :, 0] = val
    arr[:, :, 1] = val
    arr[:, :, 2] = val
    return arr


def _np_dilate(arr, iterations=1):
    h, w = arr.shape[:2]
    mask = (arr[:, :, 0] < 128) | (arr[:, :, 1] < 128) | (arr[:, :, 2] < 128)
    full_iters = int(iterations)
    has_half = (iterations - full_iters) >= 0.5
    for _ in range(full_iters):
        padded = np.pad(mask, 1, mode='constant', constant_values=False)
        dilated = mask.copy()
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                dilated |= padded[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        mask = dilated
    if has_half:
        padded = np.pad(mask, 1, mode='constant', constant_values=False)
        dilated = mask.copy()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            dilated |= padded[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
        mask = dilated
    arr[mask, 0:3] = 0
    return arr


def _np_contour(arr):
    h, w = arr.shape[:2]
    is_dark = arr[:, :, 0] < 128
    padded = np.pad(is_dark, 1, mode='constant', constant_values=False)
    neighbors_dark = np.zeros((h, w), dtype=np.int32)
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dy == 0 and dx == 0:
                continue
            neighbors_dark += padded[1 + dy:1 + dy + h, 1 + dx:1 + dx + w].astype(np.int32)
    contour_mask = is_dark & (neighbors_dark < 8)
    contour_mask[0, :] = False
    contour_mask[-1, :] = False
    contour_mask[:, 0] = False
    contour_mask[:, -1] = False
    result = np.full((h, w, 4), 255, dtype=np.uint8)
    result[contour_mask, 0:3] = 0
    return result


def apply_filter_replace_color(bgra_data, width, height, target_colors, tolerance, feather=0):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_replace_color(arr, target_colors, tolerance, feather)
    return arr.tobytes()


def apply_filter_invert(bgra_data, width, height):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_invert(arr)
    return arr.tobytes()


def apply_filter_contrast(bgra_data, width, height, contrast):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_contrast(arr, contrast)
    return arr.tobytes()


def apply_filter_channel(bgra_data, width, height, channel):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_channel(arr, channel)
    return arr.tobytes()


def apply_filter_dilate(bgra_data, width, height, iterations=1):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_dilate(arr, iterations)
    return arr.tobytes()


def apply_filter_contour(bgra_data, width, height):
    arr = _bgra_to_array(bgra_data, width, height)
    arr = _np_contour(arr)
    return arr.tobytes()


FILTER_FUNCTIONS = {
    "replace_color": lambda arr, params: _np_replace_color(
        arr, params.get("parsed_colors", []), params.get("tolerance", 30), params.get("feather", 0)
    ),
    "invert": lambda arr, params: _np_invert(arr),
    "contrast": lambda arr, params: _np_contrast(arr, params.get("value", 50)),
    "channel": lambda arr, params: _np_channel(arr, params.get("channel", "r")),
    "dilate": lambda arr, params: _np_dilate(arr, params.get("iterations", 2) / 2),
    "contour": lambda arr, params: _np_contour(arr),
    "python": None,
}


def apply_filters_chain(bgra_data, width, height, filters, parse_color_func=None):
    arr = _bgra_to_array(bgra_data, width, height)
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
                    original_bytes = arr.tobytes()
                    local_vars = {
                        "data": bytearray(original_bytes),
                        "width": width, "height": height,
                        "np": np,
                        "np_data": arr,
                    }
                    exec(code, {"__builtins__": __builtins__, "np": np}, local_vars)
                    np_data_result = local_vars.get("np_data")
                    if np_data_result is not arr and isinstance(np_data_result, np.ndarray) and np_data_result.shape == (height, width, 4):
                        arr = np_data_result
                    else:
                        data_result = local_vars.get("data")
                        if isinstance(data_result, (bytes, bytearray)) and bytes(data_result) != original_bytes:
                            arr = np.frombuffer(data_result, dtype=np.uint8).reshape(height, width, 4).copy()
                except Exception as e:
                    print(f"[Image] Python滤镜执行失败: {e}")
            continue
        fn = FILTER_FUNCTIONS.get(f_type)
        if fn:
            arr = fn(arr, f)
    return arr.tobytes()


def apply_ocr_filter(bgra_data, width, height, target_colors, tolerance):
    return apply_filter_replace_color(bgra_data, width, height, target_colors, tolerance)


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
    arr = np.frombuffer(bgra_data, dtype=np.uint8)
    if arr.size != height * width * 4:
        return b''
    arr = arr.reshape(height, width, 4)
    rgba = arr[:, :, [2, 1, 0, 3]].copy()
    raw_rows = bytearray()
    for y in range(height):
        raw_rows.append(0)
        raw_rows.extend(rgba[y].tobytes())
    compressed = zlib.compress(bytes(raw_rows))
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
    arr = np.frombuffer(bgra_data, dtype=np.uint8).reshape(height, width, 4)
    flipped = arr[::-1]
    pad_bytes = b'\x00' * padding
    pixel_data = bytearray()
    for y in range(height):
        pixel_data.extend(flipped[y].tobytes())
        pixel_data.extend(pad_bytes)
    return file_header + dib_header + bytes(pixel_data)
