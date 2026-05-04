
import ctypes


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


def check_positions_match(bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors=None):
    if not positions or not colors:
        return False, "0"
    result_bits = []
    match_count = 0
    for pos in positions:
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            x = pos[0] - capture_region[0]
            y = pos[1] - capture_region[1]
            pixel = get_pixel_color(bmp_data, x, y, img_width)
            if color_match(pixel, colors, tolerance):
                match_count += 1
                result_bits.append('1')
            elif extra_colors and color_match(pixel, extra_colors, tolerance):
                match_count += 1
                result_bits.append('1')
            else:
                result_bits.append('0')
        else:
            result_bits.append('0')
    all_match = match_count == len(positions)
    return all_match, ''.join(result_bits)


def check_positions_count_match(bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold):
    if not positions or not colors:
        return False, "0", 0
    match_count = 0
    for pos in positions:
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            x = pos[0] - capture_region[0]
            y = pos[1] - capture_region[1]
            pixel = get_pixel_color(bmp_data, x, y, img_width)
            if color_match(pixel, colors, tolerance):
                match_count += 1
    if len(positions) == 0:
        return False, "0", 0
    ratio = match_count / len(positions)
    matched = ratio >= match_threshold
    return matched, str(match_count), match_count
