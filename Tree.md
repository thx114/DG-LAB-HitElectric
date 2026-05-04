# 挨打就电3.1 - 项目世界树

> 更新时间: 2026-05-04
> 主程序入口: [挨打就电3.1.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py)
> 项目定位: 惩罚姬插件 - 游戏血条/盾条监控与电击触发系统

---

## 项目目录结构

```
挨打就电3.1/
├── 挨打就电3.1.py          # [主程序入口] 插件核心逻辑
├── capture.py              # [模块] 屏幕截图(GDI)
├── image.py                # [模块] 像素颜色/坐标解析
├── ocr.py                  # [模块] OCR识别与图像滤镜
├── lib.py                  # [模块] 统一导出层(聚合capture/image/ocr)
├── config.py               # [模块] 配置管理(Config类)
├── config_tool.py          # [工具] PyQt6配置GUI工具
├── config_tool.spec        # [构建] PyInstaller打包规格
├── fix_update.py           # [脚本] config_tool.py修补脚本
├── test_wave.py            # [测试] 波形解析测试脚本
├── config.json             # [配置] 当前运行配置
├── changelog.md            # [文档] 更新日志
├── .gitignore              # [Git] 忽略规则
├── 点位图片.png             # [资源] 点位参考图
├── 预制采样配置-使用配置工具读取/  # [配置] 预设配置集
│   ├── 卡丘-1360x768.v3.1.json
│   ├── 卡丘-1920x1080.v3.1.json
│   ├── 卡丘-2560x1440.v3.1.json
│   ├── 卡丘-2560x1600.v3.1.json
│   ├── 异环-1920x1080.v3.1.json
│   ├── 异环-2560x1440.v3.1.json
│   ├── 异环-2560x1600.v3.1.json
│   ├── 鸣潮-1920x1080.v3.1.json
│   ├── 鸣潮-2560x1440.v3.1.json
│   └── 鸣潮-2560x1600.v3.1.json
├── screenshots/            # [输出] 调试截图目录
├── build/                  # [构建] PyInstaller构建输出
│   └── config_tool/
└── dist/                   # [构建] 可执行文件输出
    └── config_tool.exe
```

---

## 模块详细分析

### 1. [挨打就电3.1.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) - 主程序入口

**插件元数据:**
- `name = "卡丘-挨打就电"`
- `author = "F_thx"`

**全局状态变量:**

| 变量 | 说明 |
|------|------|
| `debug_mode` | 调试模式开关 |
| `base_dir` | 基础目录 |
| `PULSE_DATA` | 脉冲波形数据 |
| `stop_event` | 停止事件 |
| `msg_queue` | 消息队列(旧版) |
| `server` | V2服务器对象 |
| `logger` | 日志器 |
| `game_hwnd` | 游戏窗口句柄 |
| `is_monitoring` | 监控状态 |
| `cfg` | Config实例 |
| `main_loop` | 异步事件循环 |
| `overlay_hwnd` | 悬浮窗句柄 |
| `current_health` | 当前血量 |
| `current_shield` | 当前盾量 |
| `current_electric_strength` | 当前电击强度 |
| `is_spectating` | 是否观战 |
| `has_healthbar` | 是否有血条 |
| `multi_char_enabled` | 多角色模式 |
| `active_character` | 当前角色索引 |
| `target_character` | 目标角色索引 |
| `character_count` | 角色数量 |
| `character_states` | 角色状态字典 |
| `switch_immunity_frames` | 切换免疫帧 |
| `switch_value_unchanged` | 切换后数值未变化标志 |
| `strength_values` | 强度值字典(health_a/b, shield_a/b) |
| `capture_method` | 截图方式标识 |
| `overlay_text` | 悬浮窗文本 |
| `overlay_visible` | 悬浮窗可见性 |
| `setting_mode` | 设置模式 |
| `setting_target` | 设置目标索引 |
| `electric_active_until` | 电击激活截止时间 |
| `electric_trigger_message` | 电击触发消息 |
| `electric_trigger_count` | 电击触发计数 |

**OCR怀疑机制变量:**

| 变量 | 说明 |
|------|------|
| `ocr_health_suspect` | 血量OCR怀疑标志 |
| `ocr_shield_suspect` | 盾量OCR怀疑标志 |
| `ocr_suspected_health_value` | 怀疑的血量值 |
| `ocr_suspected_shield_value` | 怀疑的盾量值 |
| `ocr_health_suspect_count` | 血量怀疑计数 |
| `ocr_shield_suspect_count` | 盾量怀疑计数 |
| `OCR_SUSPECT_THRESHOLD` | 怀疑阈值(默认2) |

**虚拟键码常量:**
- `VK_F6` ~ `VK_F10`, `VK_RETURN`, `VK_UP/DOWN/LEFT/RIGHT`, `VK_0` ~ `VK_9`
- `CHAR_KEY_MAP` - 字符到虚拟键码映射字典

**Win32 API对象:**
- `user32`, `gdi32`, `kernel32`

**函数列表:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [cache_config](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | 无 | 缓存配置到全局变量 |
| [get_pulse_duration](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | pulse_data | float(秒) | 计算脉冲持续时间 |
| [get_health_pulse_data](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | list | 获取血量脉冲数据 |
| [get_shield_pulse_data](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | list | 获取盾量脉冲数据 |
| [log](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | msg_a, lvl | 无 | 日志输出(兼容V2/旧版) |
| [debug](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | msg_a | 无 | 调试日志 |
| [count_digit_changes](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | old_value, new_value | int | 计算位数变化数量 |
| [is_suspect_change](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | old_value, new_value | bool | 检测是否可疑变化(截断/归零) |
| [validate_ocr_value](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | value_type, new_value, old_value | (bool, value) | OCR数值可信度验证 |
| [check_healthbar_exists](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width | (bool, str) | 检测血条是否存在(点位+反向检测) |
| [check_spectating](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width | (bool, str) | 检测是否观战状态 |
| [detect_bar_length](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points | (float, str) | 检测条形长度百分比 |
| [check_health_and_shield](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width | dict | 检测血量盾量变化(含盾阻止扣血) |
| [check_healthbar_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width | (bool, number, float) | OCR方式检测血条 |
| [check_shield_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width | (number, float) | OCR方式检测盾条 |
| [check_bar_pixel_match](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | bmp_data, img_width, capture_region, bar_type, position_type | bool | 检查条形位置像素匹配 |
| [_send_set_strength](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | channel, strength | 无 | 发送强度设置指令 |
| [_send_pluses](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | pulse_data, channel, punish_time | 无 | 发送脉冲指令 |
| [_clear_pluses](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | channel | 无 | 清除脉冲指令 |
| [trigger_electric](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | strength_a, strength_b, pulse_type | coroutine | 触发电击(核心) |
| [trigger_electric_health](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | strength_a, strength_b | coroutine | 触发血量电击 |
| [trigger_electric_shield](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | strength_a, strength_b | coroutine | 触发盾量电击 |
| [on_toggle_monitoring](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | 无 | 切换监控状态 |
| [check_key_state](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | vk_code | bool | 检查按键状态 |
| [request_switch_character](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | new_index | bool | 请求切换角色(延迟) |
| [execute_switch_character](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | new_index | bool | 执行角色切换 |
| [take_screenshot](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | prefix | path | 调用lib截图 |
| [take_debug_screenshots](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | 无 | 产出调试截图和OCR输出 |
| [key_monitor_loop](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | 无 | 按键监听循环(线程) |
| [create_overlay_window](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | 无 | 创建tkinter悬浮窗(线程) |
| [monitoring_loop](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | coroutine | 主监控循环(核心) |
| [main](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | put_server, data, loggerr | coroutine | 插件入口函数 |
| [stop](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/挨打就电3.1.py) | 无 | coroutine | 插件停止函数 |

**create_overlay_window 内部函数:**
- `update_display()` - 悬浮窗定时刷新
- `update_label_text()` - 更新悬浮窗标签文本

**monitoring_loop 关键逻辑:**
- 盾量血量同时检测: `ocr_health_shield_detect` 配置项
- 盾阻止扣血: `shield_blocks_health` 配置项
- 切换后数值未变化免疫: `switch_value_unchanged`

---

### 2. [capture.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) - 屏幕截图模块

**常量:**
- `SRCCOPY = 0x00CC0020`

**ctypes结构体:**

| 类名 | 说明 |
|------|------|
| [RECT](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | 矩形区域(left, top, right, bottom) |
| [BITMAPINFOHEADER](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | 位图信息头 |
| [BITMAPINFO](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | 位图信息(含颜色表) |

**函数列表:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [capture_screen_fast](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | region=None, hwnd=None | (buf, rx, ry, rw, rh, img_width) | 快速截图(窗口/区域/全屏) |
| [_capture_fullscreen](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | 无 | (buf, 0, 0, width, height, width) | 全屏截图(内部) |
| [capture_screen_region](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | left, top, width, height | bytes | 指定区域截图 |
| [save_screenshot_sync](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | bmp_data, width, height, filename | str(路径) | 同步保存截图(PNG/BMP) |
| [take_screenshot](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/capture.py) | prefix, log_func, hwnd | str(路径) | 截图并保存 |

---

### 3. [image.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) - 像素颜色与坐标解析模块

**函数列表:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [get_pixel_color](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | bmp_data, x, y, img_width | (r, g, b) | 获取像素BGRA颜色 |
| [parse_coordinate](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | coord | [int, int] | 解析单个坐标 |
| [parse_coordinates](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | coords | list[[int,int]] | 解析坐标列表(支持\|分隔) |
| [parse_color](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | color | (r, g, b) or None | 解析单个颜色(#hex/list) |
| [parse_colors](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | colors | list[(r,g,b)] | 解析颜色列表(支持\|分隔) |
| [color_match](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | pixel, target_colors, tolerance | bool | 颜色匹配检测 |
| [check_positions_match](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors | (bool, str) | 检查位置颜色是否全部匹配 |
| [check_positions_count_match](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/image.py) | bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold | (bool, str, ...) | 按比例检查位置颜色匹配 |

---

### 4. [ocr.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) - OCR识别与图像滤镜模块

**全局变量:**
- `_ocr_port = 1395`

**滤镜函数:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [apply_filter_replace_color](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, target_colors, tolerance, feather | bytes | 颜色替换滤镜(支持羽化) |
| [apply_filter_invert](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height | bytes | 反色滤镜 |
| [apply_filter_contrast](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, contrast | bytes | 对比度滤镜 |
| [apply_filter_channel](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, channel | bytes | 通道提取滤镜 |
| [apply_filter_dilate](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, iterations | bytes | 膨胀滤镜 |
| [apply_filter_contour](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height | bytes | 轮廓提取滤镜 |

**滤镜注册表:**
- `FILTER_FUNCTIONS` - 滤镜类型名到函数的映射字典
  - `"replace_color"`, `"invert"`, `"contrast"`, `"channel"`, `"dilate"`, `"contour"`, `"python"`

**核心函数:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [_print](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | msg, level | 无 | 内部打印 |
| [get_ocr_server_url](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | port=None | str(URL) | 获取OCR服务端URL |
| [set_ocr_port](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | port | 无 | 设置OCR端口 |
| [check_ocr_server](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | port=None | bool | 检查OCR服务端是否运行 |
| [extract_number](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | text | int or None | 从OCR文本提取数字 |
| [apply_filters_chain](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, filters, parse_color_func | bytes | 滤镜链处理(按顺序应用) |
| [apply_ocr_filter](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height, target_colors, tolerance | bytes | 旧版OCR滤镜(兼容) |
| [crop_image_for_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bmp_data, x1, y1, x2, y2, img_width, ... | bytes or None | 裁剪图像用于OCR(含滤镜预处理) |
| [ocr_recognize_number](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bmp_data, x1, y1, x2, y2, img_width, port, ... | (number, elapsed) | OCR识别数字(核心) |
| [create_png_from_bgra](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height | bytes(PNG) | BGRA转PNG |
| [create_bmp_from_bgra](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/ocr.py) | bgra_data, width, height | bytes(BMP) | BGRA转BMP |

---

### 5. [lib.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) - 统一导出层

**导入来源:**
- `capture` 模块: `capture_screen_fast`, `capture_screen_region`, `save_screenshot_sync`, `take_screenshot`, `BITMAPINFOHEADER`, `BITMAPINFO`, `RECT`
- `image` 模块: `get_pixel_color`, `parse_coordinate`, `parse_coordinates`, `parse_color`, `parse_colors`, `color_match`, `check_positions_match`, `check_positions_count_match`
- `ocr` 模块: `check_ocr_server`, `set_ocr_port`, `get_ocr_server_url`, `crop_image_for_ocr`, `ocr_recognize_number`, `extract_number`, `apply_ocr_filter`, `apply_filters_chain`, `create_png_from_bgra`, `create_bmp_from_bgra`

**常量:**
- `SRCCOPY = 0x00CC0020`
- XInput按钮常量: `XINPUT_GAMEPAD_DPAD_UP/DOWN/LEFT/RIGHT`, `XINPUT_GAMEPAD_START/BACK`, `XINPUT_GAMEPAD_LEFT/RIGHT_THUMB/SHOULDER`, `XINPUT_GAMEPAD_A/B/X/Y`

**ctypes结构体:**

| 类名 | 说明 |
|------|------|
| [XINPUT_GAMEPAD](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | 手柄状态结构体 |
| [XINPUT_STATE](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | 手柄输入状态 |

**全局变量:**
- `xinput_dll = None`

**函数列表:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [init_xinput](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | 无 | bool | 初始化XInput DLL |
| [read_xinput_buttons](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | user_index=0 | int(按钮位掩码) | 读取手柄按钮状态 |
| [_print](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | msg, level | 无 | 内部打印 |
| [find_window_by_keywords](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | keyword | list[hwnd] | 按标题关键字查找窗口 |
| [get_game_window](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | process_title, process_exeName | hwnd or None | 获取游戏窗口句柄 |
| [get_cursor_position](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | 无 | (x, y) | 获取鼠标位置 |
| [get_client_offset](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | hwnd | (x, y) | 获取窗口客户区偏移 |
| [sample_color_at_cursor](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | hwnd=None | dict(abs_x/y, rel_x/y, color, hex_color) | 采样光标处颜色 |
| [get_plugin_dir](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/lib.py) | 无 | str | 获取插件目录 |

---

### 6. [config.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config.py) - 配置管理模块

**默认配置字典:** `_DEFAULTS`
- `plugins` - 插件配置
  - `toggle_key` / `setting_mode_key` / `overlay_toggle_key` - 快捷键
  - `scan_interval` - 扫描间隔
  - `game` - 游戏进程/区域配置
  - `plus_sign` - 加号点位检测配置
  - `spectate` - 观战检测配置
  - `health_bar` - 血条配置(像素/OCR)
  - `shield_bar` - 盾条配置(像素/OCR, 含 `blocks_health` 和 `ocr_health_shield_detect`)
  - `overlay` - 悬浮窗配置
  - `overlap` - 叠加电击配置
  - `ocr` - OCR服务配置
  - `multi_character` - 多角色配置
- `waveform` - 波形数据
  - `health_pulse` - 血量脉冲波形列表
  - `shield_pulse` - 盾量脉冲波形列表

**模块级函数:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [_deep_merge](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config.py) | base, override | dict | 深度合并字典 |
| [_migrate_legacy_filters](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config.py) | data | dict | 迁移旧版OCR滤镜配置(颜色/容差→滤镜链) |

**Config类:** [class Config](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config.py)

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `__init__` | 无 | 无 | 初始化(深拷贝默认值) |
| `load` | config_path | 无 | 加载配置文件(含旧版迁移) |
| `save` | config_path=None | bool | 保存配置文件 |
| `_build_cache` | 无 | 无 | 构建扁平化缓存 |
| `get` | key, default=None | value | 从缓存获取值 |
| `get_raw` | path, default=None | value | 按路径获取原始值 |
| `set_raw` | path, value | 无 | 按路径设置值并重建缓存 |
| `data` | (property) | dict | 原始数据 |
| `plugins` | (property) | dict | 插件配置 |
| `waveform` | (property) | dict | 波形配置 |
| `get_capture_region` | 无 | [x, y, w, h] | 获取截图区域 |

---

### 7. [config_tool.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) - PyQt6配置GUI工具

**模块级函数:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [get_plugin_dir](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | 无 | str | 获取插件目录(支持PyInstaller) |
| [_dg_period_to_v3_freq](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | period_ms | int | DG周期转V3频率 |
| [_v3_freq_to_period](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | v3_freq | float | V3频率转DG周期 |
| [main](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | 无 | 无 | 程序入口 |

**全局常量:**
- `_DG_FREQ_MAP` - DG频率映射表
- `_DG_SECTION_TIME_MAP` - DG段时间映射表

**类列表:**

| 类名 | 继承 | 说明 |
|------|------|------|
| [PythonSyntaxHighlighter](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | QSyntaxHighlighter | Python语法高亮 |
| [ScreenshotDialog](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | QDialog | 截图预览对话框 |
| [GameScreenshotWindow](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | QWidget | 游戏截图窗口 |
| [ColorLineEdit](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | QLineEdit | 带颜色预览的输入框(支持多颜色\|分隔) |
| [ConfigTool](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config_tool.py) | QMainWindow | 配置工具主窗口 |

**PythonSyntaxHighlighter 方法:**
- `__init__` - 初始化高亮规则
- `highlightBlock` - 高亮文本块

**ScreenshotDialog 方法:**
- `__init__` - 初始化截图预览

**GameScreenshotWindow 方法:**
- `__init__` - 初始化窗口
- `closeEvent` - 关闭事件

**ColorLineEdit 方法:**
- `__init__` - 初始化
- `setColor` - 设置颜色
- `_parse_and_set_colors` - 解析并设置颜色
- `setText` - 设置文本
- `_parse_colors_from_text_manually` - 手动解析颜色
- `update_colors_from_text` - 文本变化更新颜色
- `update_text_margins` - 更新文本边距
- `paintEvent` - 绘制颜色块
- `getColors` - 获取颜色列表
- `restoreState` - 恢复状态

**ConfigTool 类信号:**

| 信号 | 类型 | 说明 |
|------|------|------|
| `_ocr_status_signal` | pyqtSignal(bool) | OCR连接测试结果信号(线程安全回传) |
| `_game_status_signal` | pyqtSignal(bool) | 游戏窗口连接测试结果信号(线程安全回传) |

**ConfigTool 类属性:**

| 属性 | 说明 |
|------|------|
| `_ocr_connected` | OCR服务当前连接状态(bool) |
| `_game_connected` | 游戏窗口当前连接状态(bool) |
| `_ocr_test_timer` | OCR连接测试定时器(QTimer, SingleShot) |
| `_game_test_timer` | 游戏窗口连接测试定时器(QTimer, SingleShot) |
| `_top_btn` | 主窗口置顶按钮(📌置顶, Checkable) |

**ConfigTool 状态标签:**

| 标签 | 位置 | 说明 |
|------|------|------|
| `health_filter_summary` | 血量滤镜编辑按钮右侧 | 显示当前滤镜链摘要(如: 替换颜色 → 对比度)，无滤镜时显示"(无滤镜)" |
| `shield_filter_summary` | 盾量滤镜编辑按钮右侧 | 显示当前滤镜链摘要 |
| `ocr_status_label` | OCR端口配置右侧 | OCR连接状态(绿色●已连接/红色●未连接)，OCR禁用时为空 |
| `game_status_label` | 游戏配置分组标题右侧 | 游戏窗口连接状态(绿色●已连接/红色●未连接) |

**连接状态定时器:**

| 定时器 | 初始延迟 | 失败重试 | 成功重试 | 说明 |
|--------|----------|----------|----------|------|
| `_ocr_test_timer` | 2秒 | 10秒 | 30秒 | OCR服务连接测试(仅OCR启用时检测，禁用时10秒轮询) |
| `_game_test_timer` | 2秒 | 5秒 | 20秒 | 游戏窗口连接测试 |

**连接状态触发条件:**
- OCR端口变更(`ocr.port`) → 立即重置`_ocr_test_timer`(500ms)
- 游戏标题变更(`game.process_title`) → 立即重置`_game_test_timer`(500ms)
- OCR开关变更 → 启用时重启定时器(500ms)，禁用时停止并清空标签

**ConfigTool 类方法 (主窗口):**

| 方法 | 说明 |
|------|------|
| `__init__` | 初始化(连接信号槽) |
| `init_ui` | 构建UI(含底部📌置顶按钮) |
| `create_config_group` | 创建配置分组 |
| `is_multi_value_field` | 判断多值字段 |
| `format_config_value_for_display` | 格式化配置值显示 |
| `create_field_row` | 创建字段行 |
| `create_paired_row` | 创建配对行 |
| `on_group_enable_changed` | 分组启用变更 |
| `on_checkbox_changed` | 复选框变更 |
| `_toggle_end_position_visibility` | 切换结束位置可见性 |
| `on_ocr_toggled` | OCR开关切换(含状态定时器启停) |
| `_update_ocr_ui_visibility` | 更新OCR UI可见性 |
| `_toggle_bar_widgets_visibility` | 切换条形控件可见性 |
| `_get_widget_row` | 获取控件行 |
| `get_config_value` | 获取配置值 |
| `set_config_value` | 设置配置值 |
| `on_field_changed` | 字段变更处理(含OCR端口/游戏标题变更触发状态重测) |
| `load_config` | 加载配置 |
| `build_config_ui` | 构建配置UI(含状态标签、滤镜摘要) |
| `setup_hotkeys` | 设置热键 |
| `keyPressEvent` | 按键事件 |
| `toggle_sampling` | 切换采样模式 |
| `_backup_widget_state` | 备份控件状态 |
| `start_sampling_mode` | 启动采样模式 |
| `_find_widget_by_config_path` | 按路径查找控件 |
| `perform_sampling` | 执行采样 |
| `_restore_widget_state` | 恢复控件状态 |
| `cancel_sampling` | 取消采样 |
| `finish_sampling` | 完成采样 |
| `capture_screenshot_for_test` | 截图测试 |
| `screenshot_test` | 截图测试入口 |
| `ocr_filter_preview` | OCR滤镜预览 |
| `ocr_once` | 单次OCR测试 |
| `open_filter_editor` | 打开滤镜编辑器(非模态) |
| `_filter_display_text` | 滤镜显示文本 |
| `_update_filter_summaries` | 更新滤镜列表摘要(遍历health_bar/shield_bar，用FILTER_TYPE_NAMES生成→分隔的链文本) |
| `_start_status_timers` | 启动OCR/游戏连接状态定时器(初始化_ocr_test_timer和_game_test_timer，2秒后首次检测) |
| `_test_ocr_connection` | 非阻塞OCR连接测试(子线程调用lib.check_ocr_server，通过_ocr_status_signal回传结果) |
| `_test_game_connection` | 非阻塞游戏窗口连接测试(子线程调用lib.get_game_window，通过_game_status_signal回传结果) |
| `_on_ocr_status_result` | OCR连接结果处理(更新ocr_status_label颜色文本，成功30秒/失败10秒后重测) |
| `_on_game_status_result` | 游戏连接结果处理(更新game_status_label颜色文本，成功20秒/失败5秒后重测) |
| `_on_health_wave_changed` | 血量波形变更 |
| `_on_shield_wave_changed` | 盾量波形变更 |
| `_parse_wave_step` | 解析波形步骤 |
| `_encode_wave_step` | 编码波形步骤 |
| `_parse_dungeonlab` | 解析Dungeonlab格式 |
| `_export_dungeonlab` | 导出Dungeonlab格式 |
| `_open_waveform_editor` | 打开波形编辑器 |
| `save_config` | 保存配置(含_clean_for_save递归清理下划线前缀键) |
| `import_preset_config` | 导入预设配置(含波形数据导入) |
| `on_process_title_changed` | 进程标题变更 |
| `apply_game_title` | 应用游戏标题(重置_game_test_timer) |
| `import_game_screenshot` | 导入游戏截图 |
| `_on_fake_window_closed` | 假窗口关闭 |
| `full_screenshot` | 全窗口截图 |

**ConfigTool 内部类:**

| 内部类 | 说明 |
|--------|------|
| `MiniWavePreview(QWidget)` | 迷你波形预览(频率密度可视化) |
| `_SamplingKeyFilter(QObject)` | 采样按键过滤器(拦截Enter键) |
| `WaveformCanvas(QWidget)` | 波形画布(可交互编辑,拖拽频率/强度) |
| `FreqDensityWidget(QWidget)` | 频率密度控件(竖线密度可视化) |
| `PresetDelegate(QStyledItemDelegate)` | 预设列表委托(下拉框波形预览) |

**ConfigTool 滤镜类型常量:**

| 常量 | 说明 |
|------|------|
| `FILTER_TYPE_NAMES` | 滤镜类型英中映射: replace_color→替换颜色, invert→反色, contrast→对比度, channel→单通道, dilate→膨胀, contour→轮廓, python→Python代码 |
| `FILTER_TYPE_NAMES_REVERSE` | 滤镜类型中英映射(反向) |

**open_filter_editor 内部关键结构:**

| 组件/函数 | 说明 |
|-----------|------|
| `rebuild_filters_ui()` | 重建滤镜列表UI |
| `_create_filter_item()` | 创建单个滤镜条目(含☰拖动手柄) |
| `_get_filter_summary()` | 获取滤镜摘要文本 |
| `_build_filter_content()` | 构建滤镜参数编辑区 |
| `_auto_preview_tick()` | 实时预览(100ms定时器)，每次tick先通过lib.capture_screen_fast截取最新游戏画面，再裁剪+滤镜+OCR |
| `_get_cropped_data()` | 获取裁剪截图数据 |
| `_SamplingKeyFilter` | 滤镜编辑器采样按键过滤器 |
| `_preview_timer` | 预览定时器(100ms) |
| `_ocr_server_ok` / `_ocr_fail_time` | OCR服务状态追踪(失败后4秒冷却) |
| `filter_top_btn` | 滤镜编辑器📌置顶按钮(底部左侧, Checkable) |
| `on_accept()` | 确认回调(清理下划线前缀键后保存滤镜，更新滤镜摘要) |
| `_restore_on_close()` | 关闭回调(恢复采样方法，清理下划线前缀键后保存滤镜，更新滤镜摘要) |
| 拖动排序 | ☰手柄拖拽重排滤镜顺序 |

**滤镜编辑器特性:**
- 非模态对话框，可同时操作主窗口
- 实时截图捕获(100ms刷新)：每次tick通过lib.capture_screen_fast截取最新游戏画面，左侧原始图像，右侧滤镜后图像
- OCR识别开关：启用后自动识别滤镜结果，服务不可用时4秒冷却重试
- 滤镜条目支持☰拖动手柄上下拖动排序
- 滤镜条目可展开/折叠编辑参数
- 支持颜色采样按钮(与主界面采样系统联动)
- Python代码滤镜带语法高亮(#1A1B1D背景)
- 7种滤镜类型：替换颜色、反色、对比度、单通道、膨胀、轮廓、Python代码
- 📌置顶按钮(底部左侧)：可切换窗口置顶状态
- 滤镜保存时自动清理Qt控件引用：on_accept和_restore_on_close均会剥离以`_`开头的键(如_widget等Qt对象引用)，防止序列化失败

**save_config 清理机制:**
- `_clean_for_save(obj)` - 递归清理函数：字典中移除所有`_`开头的键，列表递归清理
- 保存时对整个config执行清理，确保Qt控件引用不会写入JSON

**import_preset_config 导入逻辑:**
- 全部导入：更新`plugins`配置 + 导入`waveform`波形数据(如有)
- 仅导入采样点：只导入位置和颜色相关字段
- 导入后自动重建UI并重启状态定时器

**波形编辑器特性:**
- 📌置顶按钮(底部左侧)：可切换窗口置顶状态

---

### 8. [fix_update.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/fix_update.py) - 修补脚本

一次性修补脚本，将 `config_tool.py` 中 `_open_waveform_editor` 方法内的 `canvas.update()` 替换为 `_update_visuals()`。

| 函数/逻辑 | 说明 |
|-----------|------|
| 主逻辑 | 读取文件，定位方法边界，执行替换 |

---

### 9. [test_wave.py](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/test_wave.py) - 波形解析测试

测试 `ConfigTool._parse_dungeonlab()` 方法的解析功能。

| 函数/逻辑 | 说明 |
|-----------|------|
| 主逻辑 | 测试呼吸/潮汐波形解析 |

---

## 配置文件结构

### [config.json](file:///d:/APPS/惩罚姬/plugins/挨打就电3.1/config.json) - 当前运行配置

```json
{
  "config": {
    "plugins": {
      "toggle_key": "f9",
      "setting_mode_key": "f10",
      "overlay_toggle_key": "f6",
      "scan_interval": 0.1,
      "game": { "process_exeName", "process_title", "region": { "top_left", "bottom_right" } },
      "plus_sign": { "enabled", "positions", "colors", "negative_positions", "negative_colors", "tolerance" },
      "spectate": { "enabled", "positions", "colors", "tolerance" },
      "health_bar": { "enabled", "start", "end", "colors", "tolerance", "sample_points", "strength", "strength_b", "ocr_*", "ocr_filters", "drop_threshold" },
      "shield_bar": { "enabled", "start", "end", "colors", "tolerance", "sample_points", "strength", "strength_b", "ocr_*", "ocr_filters", "blocks_health", "ocr_health_shield_detect" },
      "overlay": { "enabled" },
      "overlap": { "enabled", "strength_add", "strength_max" },
      "ocr": { "enabled", "port" },
      "multi_character": { "enabled", "character_keys", "gamepad_enabled", "gamepad_buttons", "switch_immunity_frames", "switch_delay_frames" }
    },
    "waveform": {
      "health_pulse": ["1414141464646464", ...],
      "shield_pulse": ["0A0A0A0A50505050", ...]
    }
  }
}
```

### 预制采样配置

位于 `预制采样配置-使用配置工具读取/` 目录，结构与 `config.json` 相同，按游戏名+分辨率命名：

| 文件 | 游戏 | 分辨率 |
|------|------|--------|
| 卡丘-1360x768.v3.1.json | 卡拉彼丘 | 1360x768 |
| 卡丘-1920x1080.v3.1.json | 卡拉彼丘 | 1920x1080 |
| 卡丘-2560x1440.v3.1.json | 卡拉彼丘 | 2560x1440 |
| 卡丘-2560x1600.v3.1.json | 卡拉彼丘 | 2560x1600 |
| 异环-1920x1080.v3.1.json | 异环 | 1920x1080 |
| 异环-2560x1440.v3.1.json | 异环 | 2560x1440 |
| 异环-2560x1600.v3.1.json | 异环 | 2560x1600 |
| 鸣潮-1920x1080.v3.1.json | 鸣潮 | 1920x1080 |
| 鸣潮-2560x1440.v3.1.json | 鸣潮 | 2560x1440 |
| 鸣潮-2560x1600.v3.1.json | 鸣潮 | 2560x1600 |

---

## 模块依赖关系

```
挨打就电3.1.py (主程序)
├── lib.py (统一导出)
│   ├── capture.py (截图)
│   ├── image.py (像素/颜色)
│   └── ocr.py (OCR/滤镜)
└── config.py (配置管理)

config_tool.py (配置GUI)
├── lib.py (统一导出)
│   ├── capture.py
│   ├── image.py
│   └── ocr.py
└── config.py

test_wave.py (测试)
└── config_tool.py (仅引用ConfigTool._parse_dungeonlab)

fix_update.py (修补脚本)
└── config_tool.py (文件修补)
```

---

## 核心数据流

```
游戏画面
  │
  ▼
capture_screen_fast() ─── 截取屏幕区域 ─── bmp_data
  │
  ├── [像素模式]
  │   ├── check_healthbar_exists() ─── 点位匹配检测血条
  │   ├── check_spectating() ─── 点位匹配检测观战
  │   └── check_health_and_shield() ─── 采样点检测血盾百分比
  │       └── detect_bar_length() ─── 条形长度百分比
  │
  └── [OCR模式]
      ├── check_healthbar_ocr() ─── OCR识别血量数值
      │   └── ocr_health_shield_detect ─── 盾量血量同时检测
      ├── check_shield_ocr() ─── OCR识别盾量数值
      └── validate_ocr_value() ─── OCR数值可信度验证
          └── is_suspect_change() ─── 可疑变化检测
  │
  ▼
血量/盾量下降?
  │
  ├── [盾阻止扣血] shield_blocks_health=True 且盾量>0 → 不触发血量电击
  │
  ├── [切换免疫] switch_value_unchanged → 跳过电击
  │
  ▼
trigger_electric() ─── 触发电击
  ├── _send_set_strength() ─── 设置强度
  ├── _send_pluses() ─── 发送脉冲
  └── _clear_pluses() ─── 清除脉冲(叠加时)
  │
  ▼
惩罚姬主程序 ─── 控制DG-Lab设备输出
```

---

## 滤镜编辑器数据流

```
截图数据 (bmp_data)
  │
  ▼
crop_image_for_ocr() ─── 裁剪目标区域
  │
  ▼
apply_filters_chain() ─── 按顺序应用滤镜
  ├── apply_filter_replace_color() ─── 颜色替换+羽化
  ├── apply_filter_invert() ─── 反色
  ├── apply_filter_contrast() ─── 对比度增强
  ├── apply_filter_channel() ─── 通道提取
  ├── apply_filter_dilate() ─── 膨胀
  ├── apply_filter_contour() ─── 轮廓提取
  └── python exec() ─── 自定义Python代码
  │
  ▼
ocr_recognize_number() ─── 远程OCR服务识别
  │
  ▼
extract_number() ─── 提取数字结果
```

---

## 配置工具连接状态系统

```
_start_status_timers()
  │
  ├── _ocr_test_timer (2s首次)
  │   │
  │   ▼
  │   _test_ocr_connection() ─── 子线程检测
  │   │   ├── lib.check_ocr_server(port)
  │   │   └── _ocr_status_signal.emit(ok) ─── 线程安全回传
  │   │
  │   ▼
  │   _on_ocr_status_result(ok)
  │   ├── ok=True → ocr_status_label="● 已连接"(绿色) → 30s后重测
  │   └── ok=False → ocr_status_label="● 未连接"(红色) → 10s后重测
  │
  └── _game_test_timer (2s首次)
      │
      ▼
      _test_game_connection() ─── 子线程检测
      │   ├── lib.get_game_window(process_title)
      │   └── _game_status_signal.emit(ok) ─── 线程安全回传
      │
      ▼
      _on_game_status_result(ok)
      ├── ok=True → game_status_label="● 已连接"(绿色) → 20s后重测
      └── ok=False → game_status_label="● 未连接"(红色) → 5s后重测

触发重测:
  ├── ocr.port变更 → _ocr_test_timer.start(500ms)
  ├── game.process_title变更 → _game_test_timer.start(500ms)
  ├── OCR启用 → _ocr_test_timer.start(500ms)
  └── OCR禁用 → _ocr_test_timer.stop() + 清空标签
```

---

## 多角色系统状态机

```
[空闲] ──按键/手柄──▶ [请求切换] request_switch_character()
  │                      │
  │                      ▼ (延迟帧)
  │                 [执行切换] execute_switch_character()
  │                      │
  │                      ▼ (免疫帧开始)
  │                 [免疫期] switch_immunity_frames > 0
  │                      │
  │                      ▼ (数值变化确认)
  │              ┌──[确认切换]──▶ [空闲] (active_character = target_character)
  │              │
  │              ├──[数值未变]──▶ [延长免疫] (最多3次)
  │              │                switch_value_unchanged = True
  │              │
  │              └──[延长耗尽]──▶ [回退免疫] revert_immunity_frames
  │                                    │
  │                                    ▼
  │                               [空闲] (保持原角色)
  │
  └──[血条出现]──▶ [出现免疫] healthbar_appear_immunity (1帧)
```

---

## 波形编辑器架构

```
配置工具主界面
  │
  ├── [血量波形编辑按钮] ──▶ _open_waveform_editor("health")
  └── [盾量波形编辑按钮] ──▶ _open_waveform_editor("shield")
        │
        ▼
  波形编辑器对话框
  ├── WaveformCanvas ─── 可交互波形画布(拖拽编辑频率/强度)
  ├── FreqDensityWidget ─── 频率密度可视化(竖线密度)
  ├── 步骤列表 ─── 可折叠, ☰拖动排序, 频率/强度/原始数据编辑
  ├── 预设下拉框 ─── PresetDelegate渲染波形预览
  ├── Dungeonlab导入/导出 ─── _parse_dungeonlab() / _export_dungeonlab()
  ├── 📌置顶按钮 ─── 底部左侧, 可切换窗口置顶
  └── 波形文本框 ─── 直接编辑十六进制波形数据
```
