# 挨打就电 v3.3 - 项目世界树

> 更新时间: 2026-05-04
> 主程序入口: [挨打就电v3.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py)
> 项目定位: 惩罚姬插件 - 游戏血条/盾条监控与电击触发系统

---

## 项目目录结构

```
挨打就电/
├── 挨打就电v3.py          # [主程序入口] 插件核心逻辑
├── capture.py              # [模块] 屏幕截图(GDI)
├── image.py                # [模块] 像素颜色/坐标解析/图像滤镜(numpy加速)
├── image.bak.py            # [备份] 旧版image.py(纯Python实现)
├── ocr.py                  # [模块] OCR识别(依赖image滤镜)
├── lib.py                  # [模块] 统一导出层(聚合capture/image/ocr + 手柄/窗口)
├── config.py               # [模块] 配置管理(Config类)
├── config_tool.py          # [工具] PyQt6配置GUI工具
├── config_tool.spec        # [构建] PyInstaller打包规格
├── test.py                 # [测试] OCR服务端测试脚本
├── config.json             # [配置] 当前运行配置
├── changelog.md            # [文档] 更新日志
├── README.md               # [文档] 项目说明
├── .gitignore              # [Git] 忽略规则
├── 点位图片.png             # [资源] 点位参考图
├── 预制采样配置-使用配置工具读取/  # [配置] 预设配置集
│   ├── 卡丘-1360x768.v3.2.json
│   ├── 卡丘-1920x1080.v3.2.json
│   ├── 卡丘-2560x1440.v3.2.json
│   ├── 卡丘-2560x1600.v3.2.json
│   ├── 异环-1920x1080.v3.1.json
│   ├── 异环-2560x1440.v3.1.json
│   ├── 异环-2560x1600.v3.1.json
│   ├── 鸣潮-1920x1080.v3.2.json
│   ├── 鸣潮-2560x1440.v3.2.json
│   └── 鸣潮-2560x1600.v3.2.json
├── screenshots/            # [输出] 调试截图目录(运行时生成)
└── dist/                   # [构建] 可执行文件输出
    └── config_tool.exe
```

---

## 模块详细分析

### 1. [挨打就电v3.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py) - 主程序入口

**插件元数据:**
- `name = "卡丘-挨打就电"` - from `"name = "` to `"卡丘-挨打就电"`
- `author = "F_thx"` - from `"author = "` to `"F_thx"`

**全局状态变量:**

| 变量 | 说明 | 位置 |
|------|------|------|
| `debug_mode` | 调试模式开关 | L11 |
| `base_dir` | 基础目录 | L23 |
| `PULSE_DATA` | 脉冲波形数据 | L24 |
| `stop_event` | 停止事件 | L25 |
| `msg_queue` | 消息队列(旧版) | L26 |
| `server` | V2服务器对象 | L27 |
| `logger` | 日志器 | L28 |
| `game_hwnd` | 游戏窗口句柄 | L30 |
| `is_monitoring` | 监控状态 | L31 |
| `cfg` | Config实例 | L33 |
| `main_loop` | 异步事件循环 | L34 |
| `overlay_hwnd` | 悬浮窗句柄 | L35 |
| `current_health` | 当前血量 | L37 |
| `current_shield` | 当前盾量 | L38 |
| `current_electric_strength` | 当前电击强度 | L39 |
| `is_spectating` | 是否观战 | L40 |
| `has_healthbar` | 是否有血条 | L41 |
| `multi_char_enabled` | 多角色模式 | L43 |
| `active_character` | 当前角色索引 | L44 |
| `target_character` | 目标角色索引 | L45 |
| `character_count` | 角色数量 | L46 |
| `character_states` | 角色状态字典 | L47 |
| `switch_immunity_frames` | 切换免疫帧 | L48 |
| `switch_value_unchanged` | 切换后数值未变化标志 | L55 |
| `strength_values` | 强度值字典(health_a/b, shield_a/b) | L82-L87 |
| `capture_method` | 截图方式标识 | L128 |
| `overlay_text` | 悬浮窗文本 | L75 |
| `overlay_visible` | 悬浮窗可见性 | L943 |
| `setting_mode` | 设置模式 | L78 |
| `setting_target` | 设置目标索引 | L79 |
| `electric_active_until` | 电击激活截止时间 | L92 |
| `electric_trigger_message` | 电击触发消息 | L93 |
| `electric_trigger_count` | 电击触发计数 | L94 |

**OCR怀疑机制变量:**

| 变量 | 说明 | 位置 |
|------|------|------|
| `ocr_health_suspect` | 血量OCR怀疑标志 | L67 |
| `ocr_shield_suspect` | 盾量OCR怀疑标志 | L68 |
| `ocr_suspected_health_value` | 怀疑的血量值 | L69 |
| `ocr_suspected_shield_value` | 怀疑的盾量值 | L70 |
| `ocr_health_suspect_count` | 血量怀疑计数 | L71 |
| `ocr_shield_suspect_count` | 盾量怀疑计数 | L72 |
| `OCR_SUSPECT_THRESHOLD` | 怀疑阈值(默认2) | L73 |

**虚拟键码常量:** L100-L126
- `VK_F6` ~ `VK_F10`, `VK_RETURN`, `VK_UP/DOWN/LEFT/RIGHT`, `VK_0` ~ `VK_9`
- `CHAR_KEY_MAP` - 字符到虚拟键码映射字典

**Win32 API对象:** L96-L98
- `user32`, `gdi32`, `kernel32`

**函数列表:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [cache_config](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L130-L133) | 无 | 无 | 缓存配置到全局变量 | L130-L133 |
| [get_pulse_duration](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L135-L145) | pulse_data | float(秒) | 计算脉冲持续时间 | L135-L145 |
| [get_health_pulse_data](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L147-L153) | 无 | list | 获取血量脉冲数据 | L147-L153 |
| [get_shield_pulse_data](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L155-L161) | 无 | list | 获取盾量脉冲数据 | L155-L161 |
| [log](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L163-L188) | msg_a, lvl | 无 | 日志输出(兼容V2/旧版) | L163-L188 |
| [debug](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L190-L192) | msg_a | 无 | 调试日志 | L190-L192 |
| [count_digit_changes](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L194-L221) | old_value, new_value | int | 计算位数变化数量 | L194-L221 |
| [is_suspect_change](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L223-L252) | old_value, new_value | bool | 检测是否可疑变化(截断/归零) | L223-L252 |
| [validate_ocr_value](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L254-L332) | value_type, new_value, old_value | (bool, value) | OCR数值可信度验证 | L254-L332 |
| [check_healthbar_exists](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L335-L388) | bmp_data, img_width | (bool, str) | 检测血条是否存在(点位+反向检测) | L335-L388 |
| [check_spectating](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L390-L407) | bmp_data, img_width | (bool, str) | 检测是否观战状态 | L390-L407 |
| [detect_bar_length](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L409-L411) | bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points | (float, str) | 检测条形长度百分比(委托lib) | L409-L411 |
| [check_health_and_shield](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L413-L456) | bmp_data, img_width | dict | 检测血量盾量变化(含盾阻止扣血) | L413-L456 |
| [check_healthbar_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L458-L499) | bmp_data, img_width | (bool, number, float, float) | OCR方式检测血条(传递api_url/api_data) | L458-L499 |
| [check_shield_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L501-L534) | bmp_data, img_width | (number, float, float) | OCR方式检测盾条(传递api_url/api_data) | L501-L534 |
| [check_bar_pixel_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L530-L551) | bmp_data, img_width, capture_region, bar_type, position_type | bool | 检查条形位置像素匹配 | L530-L551 |
| [_send_set_strength](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L553-L557) | channel, strength | 无 | 发送强度设置指令 | L553-L557 |
| [_send_pluses](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L559-L564) | pulse_data, channel, punish_time | 无 | 发送脉冲指令 | L559-L564 |
| [_clear_pluses](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L566-L570) | channel | 无 | 清除脉冲指令 | L566-L570 |
| [trigger_electric](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L572-L622) | strength_a, strength_b, pulse_type | coroutine | 触发电击(核心) | L572-L622 |
| [trigger_electric_health](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L624-L625) | strength_a, strength_b | coroutine | 触发血量电击 | L624-L625 |
| [trigger_electric_shield](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L627-L628) | strength_a, strength_b | coroutine | 触发盾量电击 | L627-L628 |
| [on_toggle_monitoring](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L630-L636) | 无 | 无 | 切换监控状态 | L630-L636 |
| [check_key_state](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L638-L639) | vk_code | bool | 检查按键状态 | L638-L639 |
| [request_switch_character](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L641-L664) | new_index | bool | 请求切换角色(延迟) | L641-L664 |
| [execute_switch_character](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L666-L697) | new_index | bool | 执行角色切换 | L666-L697 |
| [take_screenshot](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L699-L702) | prefix | path | 调用lib截图 | L699-L702 |
| [take_debug_screenshots](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L704-L810) | 无 | 无 | 产出调试截图和OCR输出(传递api_url/api_data) | L704-L810 |
| [key_monitor_loop](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L800-L940) | 无 | 无 | 按键监听循环(线程) | L800-L940 |
| [create_overlay_window](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L945-L1121) | 无 | 无 | 创建tkinter悬浮窗(线程) | L945-L1121 |
| [monitoring_loop](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L1125-L1393) | 无 | coroutine | 主监控循环(核心) | L1125-L1393 |
| [main](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L1395-L1519) | put_server, data, loggerr | coroutine | 插件入口函数 | L1395-L1519 |
| [stop](file:///d:/APPS/惩罚姬/plugins/挨打就电/挨打就电v3.py#L1521-L1526) | 无 | coroutine | 插件停止函数 | L1521-L1526 |

**create_overlay_window 内部函数:**
- `update_display()` (L982-L1017) - 悬浮窗定时刷新
- `update_label_text()` (L1019-L1110) - 更新悬浮窗标签文本

**monitoring_loop 关键逻辑:**
- OCR模式与像素模式双路径检测
- 盾量血量同时检测: `ocr_health_shield_detect` 配置项
- 盾阻止扣血: `shield_blocks_health` 配置项
- 切换后数值未变化免疫: `switch_value_unchanged`
- 血条出现免疫: `healthbar_appear_immunity`
- OCR性能瓶颈检测与警告

---

### 2. [capture.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py) - 屏幕截图模块

**常量:**
- `SRCCOPY = 0x00CC0020` (L5)

**ctypes结构体:**

| 类名 | 说明 | 位置 |
|------|------|------|
| [RECT](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L8-L10) | 矩形区域(left, top, right, bottom) | L8-L10 |
| [BITMAPINFOHEADER](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L13-L21) | 位图信息头 | L13-L21 |
| [BITMAPINFO](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L24-L25) | 位图信息(含颜色表) | L24-L25 |

**函数列表:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [capture_screen_fast](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L28-L103) | region=None, hwnd=None | (buf, rx, ry, rw, rh, img_width) | 快速截图(窗口/区域/全屏) | L28-L103 |
| [_capture_fullscreen](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L106-L132) | 无 | (buf, 0, 0, width, height, width) | 全屏截图(内部) | L106-L132 |
| [capture_screen_region](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L135-L182) | left, top, width, height | bytes | 指定区域截图(带异常处理) | L135-L182 |
| [save_screenshot_sync](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L185-L231) | bmp_data, width, height, filename | str(路径) | 同步保存截图(PNG/BMP) | L185-L231 |
| [take_screenshot](file:///d:/APPS/惩罚姬/plugins/挨打就电/capture.py#L234-L252) | prefix, log_func, hwnd | str(路径) | 截图并保存 | L234-L252 |

---

### 3. [image.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py) - 像素颜色/坐标解析/图像滤镜模块(numpy加速)

**依赖:** `struct`, `zlib`, `numpy`

**基础函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [get_pixel_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L6-L13) | bmp_data, x, y, img_width | (r, g, b) | 获取像素BGRA颜色 | L6-L13 |
| [parse_coordinate](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L16-L33) | coord | [int, int] | 解析单个坐标 | L16-L33 |
| [parse_coordinates](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L36-L57) | coords | list[[int,int]] | 解析坐标列表(支持\|分隔) | L36-L57 |
| [parse_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L60-L77) | color | (r, g, b) or None | 解析单个颜色(#hex/list) | L60-L77 |
| [parse_colors](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L80-L104) | colors | list[(r,g,b)] | 解析颜色列表(支持\|分隔) | L80-L104 |
| [color_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L107-L119) | pixel, target_colors, tolerance | bool | 颜色匹配检测 | L107-L119 |

**numpy加速检测函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [detect_bar_length](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L122-L183) | bmp_data, img_width, start_pos, end_pos, bar_colors, tolerance, sample_points, capture_region | (float, str) | 条形长度百分比检测(numpy加速) | L122-L183 |
| [_np_color_match_pixels](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L186-L199) | pixels, target_colors, tolerance | np.ndarray(bool) | numpy批量颜色匹配 | L186-L199 |
| [check_positions_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L202-L245) | bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors | (bool, str) | 检查位置颜色是否全部匹配(numpy加速) | L202-L245 |
| [check_positions_count_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L248-L272) | bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold | (bool, str, int) | 按比例检查位置颜色匹配(numpy加速) | L248-L272 |

**numpy图像处理内部函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [_bgra_to_array](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L275-L280) | bgra_data, width, height | np.ndarray | BGRA数据转numpy数组 | L275-L280 |
| [_np_replace_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L283-L313) | arr, target_colors, tolerance, feather | np.ndarray | 颜色替换(支持羽化) | L283-L313 |
| [_np_invert](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L316-L320) | arr | np.ndarray | 反色 | L316-L320 |
| [_np_contrast](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L323-L329) | arr, contrast | np.ndarray | 对比度调整 | L323-L329 |
| [_np_channel](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L332-L339) | arr, channel | np.ndarray | 通道提取 | L332-L339 |
| [_np_dilate](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L342-L361) | arr, iterations | np.ndarray | 膨胀(支持0.5迭代) | L342-L361 |
| [_np_contour](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L364-L381) | arr | np.ndarray | 轮廓提取 | L364-L381 |

**滤镜公开函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [apply_filter_replace_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L384-L387) | bgra_data, width, height, target_colors, tolerance, feather | bytes | 颜色替换滤镜 | L384-L387 |
| [apply_filter_invert](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L390-L393) | bgra_data, width, height | bytes | 反色滤镜 | L390-L393 |
| [apply_filter_contrast](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L396-L399) | bgra_data, width, height, contrast | bytes | 对比度滤镜 | L396-L399 |
| [apply_filter_channel](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L402-L405) | bgra_data, width, height, channel | bytes | 通道提取滤镜 | L402-L405 |
| [apply_filter_dilate](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L408-L411) | bgra_data, width, height, iterations | bytes | 膨胀滤镜 | L408-L411 |
| [apply_filter_contour](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L414-L417) | bgra_data, width, height | bytes | 轮廓提取滤镜 | L414-L417 |

**滤镜注册表:** `FILTER_FUNCTIONS` (L420-L430)
- `"replace_color"`, `"invert"`, `"contrast"`, `"channel"`, `"dilate"`, `"contour"`, `"python"`

**滤镜链与图像编码:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [apply_filters_chain](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L433-L466) | bgra_data, width, height, filters, parse_color_func | bytes | 滤镜链处理(按顺序应用,支持Python代码滤镜) | L433-L466 |
| [apply_ocr_filter](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L469-L470) | bgra_data, width, height, target_colors, tolerance | bytes | 旧版OCR滤镜(兼容) | L469-L470 |
| [create_png_from_bgra](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L473-L499) | bgra_data, width, height | bytes(PNG) | BGRA转PNG | L473-L499 |
| [create_bmp_from_bgra](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py#L502-L539) | bgra_data, width, height | bytes(BMP) | BGRA转BMP | L502-L539 |

---

### 4. [ocr.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py) - OCR识别模块

**依赖:** `requests`, `time`, `json`, `base64`, `re`, `image`(滤镜/编码函数)
**已移除依赖:** `yaml` (原用于OCR选项解析, 现由`_parse_options_data`用json替代)

**全局变量:**
- `_ocr_port = 1395` (L15)
- `_session_cache = {}` (L16) - requests.Session缓存

**函数列表:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [_get_session](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L19-L22) | key | requests.Session | 获取/缓存HTTP会话 | L19-L22 |
| [_print](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L25-L26) | msg, level | 无 | 内部打印 | L25-L26 |
| [_extract_ocr_text](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L29-L51) | res | str | 从OCR响应中提取文本(兼容多种API格式) | L29-L51 |
| [_parse_options_data](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L54-L64) | api_data | dict or None | 解析api_data(JSON字符串或dict)为选项字典 | L54-L64 |
| [get_ocr_server_url](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L67-L70) | port=None | str(URL) | 获取OCR服务端URL | L67-L70 |
| [set_ocr_port](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L73-L76) | port | 无 | 设置OCR端口 | L73-L76 |
| [check_ocr_server](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L79-L86) | port=None | bool | 检查本地OCR服务端是否运行 | L79-L86 |
| [check_ocr_api](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L89-L94) | ip, port | bool | 检查远程OCR API是否可用(按IP+端口) | L89-L94 |
| [extract_number](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L97-L107) | text | int or None | 从OCR文本提取数字 | L97-L107 |
| [crop_image_for_ocr](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L110-L164) | bmp_data, x1, y1, x2, y2, img_width, ... | (bytes or None, float) | 裁剪图像用于OCR(含滤镜预处理) | L110-L164 |
| [ocr_recognize_number](file:///d:/APPS/惩罚姬/plugins/挨打就电/ocr.py#L167-L233) | bmp_data, x1, y1, x2, y2, img_width, port, ..., api_ip=None, api_data=None | (number, elapsed, filter_time) | OCR识别数字(核心, 支持自定义api_ip+api_data选项) | L167-L233 |

**ocr_recognize_number 参数变更说明:**
- 新增 `api_ip` 参数: 自定义OCR服务IP地址, 非空时走自定义API路径(`http://{api_ip}:{port}/api/ocr`)
- 新增 `api_data` 参数: JSON选项字典(或JSON字符串), 经`_parse_options_data`解析后作为`options`字段发送
- `api_ip`非空时: 使用自定义API, 将`api_data`解析后的dict作为`options`传入请求体
- `api_ip`为空时: 走本地Umi-OCR默认接口, 使用硬编码的默认options

---

### 5. [lib.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py) - 统一导出层

**导入来源:**
- `capture` 模块: `capture_screen_fast`, `capture_screen_region`, `save_screenshot_sync`, `take_screenshot`, `BITMAPINFOHEADER`, `BITMAPINFO`, `RECT`
- `image` 模块: `get_pixel_color`, `parse_coordinate`, `parse_coordinates`, `parse_color`, `parse_colors`, `color_match`, `check_positions_match`, `check_positions_count_match`
- `ocr` 模块: `check_ocr_server`, `check_ocr_api`, `set_ocr_port`, `get_ocr_server_url`, `crop_image_for_ocr`, `ocr_recognize_number`, `extract_number`, `apply_ocr_filter`, `apply_filters_chain`, `create_png_from_bgra`, `create_bmp_from_bgra`

**常量:** L15-L30
- `SRCCOPY = 0x00CC0020`
- XInput按钮常量: `XINPUT_GAMEPAD_DPAD_UP/DOWN/LEFT/RIGHT`, `XINPUT_GAMEPAD_START/BACK`, `XINPUT_GAMEPAD_LEFT/RIGHT_THUMB/SHOULDER`, `XINPUT_GAMEPAD_A/B/X/Y`

**ctypes结构体:**

| 类名 | 说明 | 位置 |
|------|------|------|
| [XINPUT_GAMEPAD](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L33-L42) | 手柄状态结构体 | L33-L42 |
| [XINPUT_STATE](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L45-L49) | 手柄输入状态 | L45-L49 |

**全局变量:**
- `xinput_dll = None` (L52)

**函数列表:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [init_xinput](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L55-L68) | 无 | bool | 初始化XInput DLL(xinput1_4/xinput9_1_0) | L55-L68 |
| [read_xinput_buttons](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L71-L78) | user_index=0 | int(按钮位掩码) | 读取手柄按钮状态 | L71-L78 |
| [_print](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L81-L82) | msg, level | 无 | 内部打印 | L81-L82 |
| [find_window_by_keywords](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L85-L107) | keyword | list[hwnd] | 按标题关键字查找窗口(EnumWindows) | L85-L107 |
| [get_game_window](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L110-L125) | process_title, process_exeName | hwnd or None | 获取游戏窗口句柄(psutil+EnumWindows) | L110-L125 |
| [get_cursor_position](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L128-L131) | 无 | (x, y) | 获取鼠标位置 | L128-L131 |
| [get_client_offset](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L134-L139) | hwnd | (x, y) | 获取窗口客户区偏移 | L134-L139 |
| [sample_color_at_cursor](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L142-L190) | hwnd=None | dict(abs_x/y, rel_x/y, color, hex_color) | 采样光标处颜色 | L142-L190 |
| [get_plugin_dir](file:///d:/APPS/惩罚姬/plugins/挨打就电/lib.py#L193-L194) | 无 | str | 获取插件目录 | L193-L194 |

---

### 6. [config.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/config.py) - 配置管理模块

**依赖:** `json`, `os`, `sys`, `copy`, `image`(parse_coordinate, parse_coordinates, parse_colors)

**默认配置字典:** `_DEFAULTS` (L11-L120)
- `plugins` - 插件配置
  - `toggle_key` / `setting_mode_key` / `overlay_toggle_key` - 快捷键
  - `scan_interval` - 扫描间隔
  - `game` - 游戏进程/区域配置
  - `plus_sign` - 加号点位检测配置
  - `spectate` - 观战检测配置
  - `health_bar` - 血条配置(像素/OCR, 含ocr_filters, ocr_api_ip, ocr_api_data)
  - `shield_bar` - 盾条配置(像素/OCR, 含blocks_health, ocr_filters, ocr_api_ip, ocr_api_data)
  - `overlay` - 悬浮窗配置
  - `overlap` - 叠加电击配置
  - `ocr` - OCR服务配置(含health_shield_detect)
  - `multi_character` - 多角色配置
- `waveform` - 波形数据
  - `health_pulse` - 血量脉冲波形列表
  - `shield_pulse` - 盾量脉冲波形列表

**模块级函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [_deep_merge](file:///d:/APPS/惩罚姬/plugins/挨打就电/config.py#L119-L126) | base, override | dict | 深度合并字典 | L119-L126 |
| [_migrate_legacy_filters](file:///d:/APPS/惩罚姬/plugins/挨打就电/config.py#L129-L146) | data | dict | 迁移旧版OCR滤镜配置(颜色/容差->滤镜链) | L129-L146 |

**Config类:** [class Config](file:///d:/APPS/惩罚姬/plugins/挨打就电/config.py#L149-L294)

| 方法 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| `__init__` | 无 | 无 | 初始化(深拷贝默认值) | L150-L153 |
| `load` | config_path | 无 | 加载配置文件(含旧版迁移) | L155-L168 |
| `save` | config_path=None | bool | 保存配置文件 | L170-L180 |
| `_build_cache` | 无 | 无 | 构建扁平化缓存(解析坐标/颜色, 含ocr_api_ip/ocr_api_data) | L186-L255 |
| `get` | key, default=None | value | 从缓存获取值 | L248-L249 |
| `get_raw` | path, default=None | value | 按点分路径获取原始值 | L251-L259 |
| `set_raw` | path, value | 无 | 按路径设置值并重建缓存 | L261-L269 |
| `data` | (property) | dict | 原始数据 | L271-L273 |
| `plugins` | (property) | dict | 插件配置 | L275-L277 |
| `waveform` | (property) | dict | 波形配置 | L279-L281 |
| `get_capture_region` | 无 | [x, y, w, h] | 获取截图区域 | L283-L294 |

---

### 7. [config_tool.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py) - PyQt6配置GUI工具

**依赖:** `PyQt6`, `sys`, `os`, `json`, `ctypes`, `threading`, `lib`, `config`

**模块级函数:**

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [get_plugin_dir](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L23-L35) | 无 | str | 获取插件目录(支持PyInstaller) | L23-L35 |
| [_dg_period_to_v3_freq](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L287-L293) | period_ms | int | DG周期转V3频率 | L287-L293 |
| [_v3_freq_to_period](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L296-L302) | v3_freq | float | V3频率转DG周期 | L296-L302 |
| [main](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py) | 无 | 无 | 程序入口 | (文件末尾) |

**全局常量:**
- `_DG_FREQ_MAP` (L261-L270) - DG频率映射表
- `_DG_SECTION_TIME_MAP` (L272-L284) - DG段时间映射表
- `_OCR_TARGETS` (L305-L308) - OCR目标映射: health_bar->血量, shield_bar->盾量
- `_OCR_DEFAULT_OVERRIDES` (L310-L315) - OCR默认选项覆盖: ocr.language, ocr.maxSideLen, tbpu.parser, data.format

**类列表:**

| 类名 | 继承 | 说明 | 位置 |
|------|------|------|------|
| [PythonSyntaxHighlighter](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L46-L82) | QSyntaxHighlighter | Python语法高亮 | L46-L82 |
| [ScreenshotDialog](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L85-L97) | QDialog | 截图预览对话框 | L85-L97 |
| [GameScreenshotWindow](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L100-L131) | QWidget | 游戏截图窗口 | L100-L131 |
| [ColorLineEdit](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L134-L258) | QLineEdit | 带颜色预览的输入框(支持多颜色\|分隔) | L134-L258 |
| [OcrAdvancedDialog](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L318-L637) | QDialog | OCR进阶配置对话框(动态选项加载+多目标内存缓存) | L318-L637 |
| [ConfigTool](file:///d:/APPS/惩罚姬/plugins/挨打就电/config_tool.py#L640) | QMainWindow | 配置工具主窗口 | L640 |

**PythonSyntaxHighlighter 方法:**
- `__init__` (L47-L75) - 初始化高亮规则(关键字/内置/数字/字符串/注释)
- `highlightBlock` (L77-L81) - 高亮文本块

**ScreenshotDialog 方法:**
- `__init__` (L86-L97) - 初始化截图预览

**GameScreenshotWindow 方法:**
- `__init__` (L102-L127) - 初始化窗口
- `closeEvent` (L129-L131) - 关闭事件(发射closed信号)

**ColorLineEdit 方法:**
- `__init__` (L135-L143) - 初始化
- `setColor` (L145-L146) - 设置颜色
- `_parse_and_set_colors` (L148-L185) - 解析并设置颜色(#hex/list/str)
- `setText` (L187-L191) - 设置文本(带阻断标记)
- `_parse_colors_from_text_manually` (L193-L215) - 手动解析颜色
- `update_colors_from_text` (L217-L220) - 文本变化更新颜色
- `update_text_margins` (L222-L226) - 更新文本边距
- `paintEvent` (L228-L246) - 绘制颜色块
- `getColors` (L248-L249) - 获取颜色列表
- `restoreState` (L251-L258) - 恢复状态(取消采样时)

**OcrAdvancedDialog 类属性:**

| 属性 | 类型 | 说明 |
|------|------|------|
| `_config` | dict | 配置数据引用 |
| `_current_target` | str or None | 当前编辑的OCR目标(health_bar/shield_bar) |
| `_option_widgets` | dict | 选项键->Qt控件映射 |
| `_options_raw` | dict | 选项键->原始API返回数据映射 |
| `_memory_cache` | dict | 多目标内存缓存(target_key -> {ip, data}) |
| `target_combo` | QComboBox | 目标选择下拉框(血量/盾量) |
| `ip_edit` | QLineEdit | 自定义IP输入框 |
| `fetch_btn` | QPushButton | 获取配置项按钮 |
| `fetch_status` | QLabel | 获取状态标签 |
| `options_scroll` | QScrollArea | 选项滚动区域 |

**OcrAdvancedDialog 方法:**

| 方法 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| `__init__` | parent=None, config=None | 无 | 初始化(加载内存缓存) | L319-L328 |
| `_init_ui` | 无 | 无 | 构建UI(目标选择/IP输入/获取按钮/选项滚动区/提示) | L330-L394 |
| `_load_memory_cache` | 无 | 无 | 从config加载各目标的ocr_api_ip/ocr_api_data到内存缓存 | L396-L416 |
| `_get_port` | 无 | int | 获取当前OCR端口(从config.ocr.port) | L418-L423 |
| `_get_ip` | 无 | str | 获取当前IP输入 | L425-L426 |
| `_on_target_changed` | index | 无 | 目标切换时刷新缓存并加载新目标 | L428-L432 |
| `_flush_current_to_cache` | 无 | 无 | 将当前编辑状态写回内存缓存 | L434-L440 |
| `_load_target` | target_key | 无 | 从缓存加载目标配置到UI | L442-L448 |
| `_rebuild_options_from_saved` | saved_dict | 无 | 从已保存dict重建选项UI(无API元数据, 简化控件) | L450-L478 |
| `_clear_options` | 无 | 无 | 清空选项控件和布局 | L480-L491 |
| `_fetch_options` | 无 | 无 | 从OCR服务端`/api/ocr/get_options`动态获取配置项 | L493-L521 |
| `_build_dynamic_options` | options | 无 | 根据API返回的选项元数据动态构建UI(enum/boolean/number/text) | L523-L595 |
| `_collect_options` | 无 | dict | 从UI控件收集当前选项值 | L597-L617 |
| `_save_and_close` | 无 | 无 | 刷新缓存, 写回config中各目标的ocr_api_ip/ocr_api_data, 关闭对话框 | L619-L634 |
| `get_config` | 无 | dict | 返回更新后的config | L636-L637 |

**OcrAdvancedDialog 特性:**
- 多目标编辑: 血量/盾量切换时自动缓存/恢复, 切换不丢失编辑内容
- 动态选项加载: 调用`/api/ocr/get_options`获取OCR服务端支持的配置项, 自动生成对应UI控件
- 选项类型支持: enum(下拉框), boolean(复选框), number(数字输入), text(文本输入)
- 默认值覆盖: `_OCR_DEFAULT_OVERRIDES`中定义的键优先于API返回的default值
- IP自定义: 留空IP则使用默认本地Umi-OCR接口, 填写IP则走自定义API路径
- 保存时将选项dict序列化为JSON字符串存入`ocr_api_data`字段

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
| `_top_btn` | 主窗口置顶按钮(Checkable) |

**ConfigTool 状态标签:**

| 标签 | 位置 | 说明 |
|------|------|------|
| `health_filter_summary` | 血量滤镜编辑按钮右侧 | 当前滤镜链摘要 |
| `shield_filter_summary` | 盾量滤镜编辑按钮右侧 | 当前滤镜链摘要 |
| `ocr_status_label` | OCR端口配置右侧 | OCR连接状态(绿色/红色) |
| `game_status_label` | 游戏配置分组标题右侧 | 游戏窗口连接状态 |

**连接状态定时器:**

| 定时器 | 初始延迟 | 失败重试 | 成功重试 | 说明 |
|--------|----------|----------|----------|------|
| `_ocr_test_timer` | 2秒 | 10秒 | 30秒 | OCR服务连接测试 |
| `_game_test_timer` | 2秒 | 5秒 | 20秒 | 游戏窗口连接测试 |

**ConfigTool 类方法 (主窗口):**

| 方法 | 说明 |
|------|------|
| `__init__` | 初始化(连接信号槽) |
| `init_ui` | 构建UI(含底部置顶按钮) |
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
| `ocr_once` | 单次OCR测试(支持自定义api_ip/api_data, 修复3值解包) |
| `open_filter_editor` | 打开滤镜编辑器(非模态, 支持自定义IP的OCR识别) |
| `_filter_display_text` | 滤镜显示文本 |
| `_update_filter_summaries` | 更新滤镜列表摘要 |
| `_open_ocr_advanced_settings` | 打开OCR进阶配置对话框(OcrAdvancedDialog) |
| `_start_status_timers` | 启动OCR/游戏连接状态定时器 |
| `_test_ocr_connection` | 非阻塞OCR连接测试(子线程, 支持自定义IP的check_ocr_api) |
| `_test_game_connection` | 非阻塞游戏窗口连接测试(子线程) |
| `_on_ocr_status_result` | OCR连接结果处理 |
| `_on_game_status_result` | 游戏连接结果处理 |
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
| `FILTER_TYPE_NAMES` | 滤镜类型英中映射: replace_color->替换颜色, invert->反色, contrast->对比度, channel->单通道, dilate->膨胀, contour->轮廓, python->Python代码 |
| `FILTER_TYPE_NAMES_REVERSE` | 滤镜类型中英映射(反向) |

**open_filter_editor 内部关键结构:**

| 组件/函数 | 说明 |
|-----------|------|
| `rebuild_filters_ui()` | 重建滤镜列表UI |
| `_create_filter_item()` | 创建单个滤镜条目(含拖动手柄) |
| `_get_filter_summary()` | 获取滤镜摘要文本 |
| `_build_filter_content()` | 构建滤镜参数编辑区 |
| `_auto_preview_tick()` | 实时预览(100ms定时器) |
| `_get_cropped_data()` | 获取裁剪截图数据 |
| `_SamplingKeyFilter` | 滤镜编辑器采样按键过滤器 |
| `_preview_timer` | 预览定时器(100ms) |
| `_ocr_server_ok` / `_ocr_fail_time` | OCR服务状态追踪(失败后4秒冷却) |
| `filter_top_btn` | 滤镜编辑器置顶按钮(底部左侧, Checkable) |
| `on_accept()` | 确认回调(清理下划线前缀键后保存滤镜) |
| `_restore_on_close()` | 关闭回调(恢复采样方法，清理下划线前缀键后保存滤镜) |
| 拖动排序 | 手柄拖拽重排滤镜顺序 |

**滤镜编辑器特性:**
- 非模态对话框，可同时操作主窗口
- 实时截图捕获(100ms刷新)
- OCR识别开关：启用后自动识别滤镜结果，服务不可用时4秒冷却重试
- OCR识别支持自定义IP：使用`health_bar.ocr_api_ip`配置的IP地址进行OCR请求
- OCR识别使用正确配置路径：从`health_bar.ocr_api_data`读取选项数据
- 滤镜条目支持拖动手柄上下拖动排序
- 滤镜条目可展开/折叠编辑参数
- 支持颜色采样按钮(与主界面采样系统联动)
- Python代码滤镜带语法高亮
- 7种滤镜类型：替换颜色、反色、对比度、单通道、膨胀、轮廓、Python代码
- 置顶按钮(底部左侧)：可切换窗口置顶状态
- 滤镜保存时自动清理Qt控件引用

**save_config 清理机制:**
- `_clean_for_save(obj)` - 递归清理函数：字典中移除所有`_`开头的键，列表递归清理
- 保存时对整个config执行清理，确保Qt控件引用不会写入JSON

**import_preset_config 导入逻辑:**
- 全部导入：更新`plugins`配置 + 导入`waveform`波形数据(如有)
- 仅导入采样点：只导入位置和颜色相关字段
- 导入后自动重建UI并重启状态定时器

---

### 8. [test.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/test.py) - OCR服务端测试脚本

| 函数 | 输入 | 输出 | 说明 | 位置 |
|------|------|------|------|------|
| [test_ocr_options](file:///d:/APPS/惩罚姬/plugins/挨打就电/test.py#L5-L16) | port=1224 | 无 | 测试OCR服务端选项API | L5-L16 |

---

### 9. [image.bak.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py) - 旧版image.py备份(纯Python实现)

与当前 [image.py](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.py) 的区别：
- 无numpy依赖，所有像素操作为逐像素Python循环
- 无滤镜功能(无滤镜函数、无FILTER_FUNCTIONS、无图像编码)
- `check_positions_match` / `check_positions_count_match` 为纯Python实现
- 无 `detect_bar_length` 函数

**函数列表:**

| 函数 | 输入 | 输出 | 说明 |
|------|------|------|------|
| [get_pixel_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L1-L8) | bmp_data, x, y, img_width | (r, g, b) | 获取像素BGRA颜色 |
| [parse_coordinate](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L11-L28) | coord | [int, int] | 解析单个坐标 |
| [parse_coordinates](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L31-L51) | coords | list[[int,int]] | 解析坐标列表 |
| [parse_color](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L54-L71) | color | (r, g, b) or None | 解析单个颜色 |
| [parse_colors](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L74-L98) | colors | list[(r,g,b)] | 解析颜色列表 |
| [color_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L101-L113) | pixel, target_colors, tolerance | bool | 颜色匹配检测 |
| [check_positions_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L116-L137) | bmp_data, positions, colors, capture_region, img_width, tolerance, extra_colors | (bool, str) | 检查位置颜色全部匹配(纯Python) |
| [check_positions_count_match](file:///d:/APPS/惩罚姬/plugins/挨打就电/image.bak.py#L140-L155) | bmp_data, positions, colors, capture_region, img_width, tolerance, match_threshold | (bool, str, int) | 按比例检查位置颜色匹配(纯Python) |

---

## 配置文件结构

### [config.json](file:///d:/APPS/惩罚姬/plugins/挨打就电/config.json) - 当前运行配置

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
      "health_bar": { "enabled", "start", "end", "colors", "tolerance", "sample_points", "strength", "strength_b", "ocr_*", "ocr_filters", "ocr_api_ip", "ocr_api_data", "drop_threshold" },
      "shield_bar": { "enabled", "start", "end", "colors", "tolerance", "sample_points", "strength", "strength_b", "ocr_*", "ocr_filters", "ocr_api_ip", "ocr_api_data", "blocks_health" },
      "overlay": { "enabled" },
      "overlap": { "enabled", "strength_add", "strength_max" },
      "ocr": { "enabled", "port", "health_shield_detect" },
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

| 文件 | 游戏 | 分辨率 | 版本 |
|------|------|--------|------|
| 卡丘-1360x768.v3.2.json | 卡拉彼丘 | 1360x768 | v3.2 |
| 卡丘-1920x1080.v3.2.json | 卡拉彼丘 | 1920x1080 | v3.2 |
| 卡丘-2560x1440.v3.2.json | 卡拉彼丘 | 2560x1440 | v3.2 |
| 卡丘-2560x1600.v3.2.json | 卡拉彼丘 | 2560x1600 | v3.2 |
| 异环-1920x1080.v3.1.json | 异环 | 1920x1080 | v3.1 |
| 异环-2560x1440.v3.1.json | 异环 | 2560x1440 | v3.1 |
| 异环-2560x1600.v3.1.json | 异环 | 2560x1600 | v3.1 |
| 鸣潮-1920x1080.v3.2.json | 鸣潮 | 1920x1080 | v3.2 |
| 鸣潮-2560x1440.v3.2.json | 鸣潮 | 2560x1440 | v3.2 |
| 鸣潮-2560x1600.v3.2.json | 鸣潮 | 2560x1600 | v3.2 |

---

## 模块依赖关系

```
挨打就电v3.py (主程序)
├── lib.py (统一导出)
│   ├── capture.py (截图)
│   ├── image.py (像素/颜色/滤镜/numpy加速)
│   └── ocr.py (OCR识别, 依赖image滤镜)
└── config.py (配置管理, 依赖image解析函数)

config_tool.py (配置GUI)
├── lib.py (统一导出)
│   ├── capture.py
│   ├── image.py
│   └── ocr.py
└── config.py

test.py (测试)
└── requests (仅外部依赖)

image.bak.py (备份, 不参与运行)
```

---

## 核心数据流

```
游戏画面
  |
  v
capture_screen_fast() --- 截取屏幕区域 --- bmp_data
  |
  +-- [像素模式]
  |   +-- check_healthbar_exists() --- 点位匹配检测血条(含反向检测)
  |   +-- check_spectating() --- 点位匹配检测观战
  |   +-- check_health_and_shield() --- 采样点检测血盾百分比
  |       +-- detect_bar_length() --- 条形长度百分比(numpy加速)
  |
  +-- [OCR模式]
      +-- check_healthbar_ocr() --- OCR识别血量数值
      |   +-- ocr_health_shield_detect --- 盾量血量同时检测
      +-- check_shield_ocr() --- OCR识别盾量数值
      +-- validate_ocr_value() --- OCR数值可信度验证
          +-- is_suspect_change() --- 可疑变化检测(截断/归零)
  |
  v
血量/盾量下降?
  |
  +-- [盾阻止扣血] shield_blocks_health=True 且盾量>0 -> 不触发血量电击
  +-- [血量下降阈值] health_drop_threshold -> 低于阈值不触发
  +-- [切换免疫] switch_value_unchanged -> 跳过电击
  +-- [血条出现免疫] healthbar_appear_immunity -> 1帧免疫
  |
  v
trigger_electric() --- 触发电击
  +-- _send_set_strength() --- 设置强度
  +-- _send_pluses() --- 发送脉冲
  +-- _clear_pluses() --- 清除脉冲(叠加时)
  |
  v
惩罚姬主程序 --- 控制DG-Lab设备输出
```

---

## 滤镜处理数据流

```
截图数据 (bmp_data)
  |
  v
crop_image_for_ocr() --- 裁剪目标区域
  |
  v
apply_filters_chain() --- 按顺序应用滤镜(numpy加速)
  +-- apply_filter_replace_color() --- 颜色替换+羽化
  +-- apply_filter_invert() --- 反色
  +-- apply_filter_contrast() --- 对比度增强
  +-- apply_filter_channel() --- 通道提取
  +-- apply_filter_dilate() --- 膨胀
  +-- apply_filter_contour() --- 轮廓提取
  +-- python exec() --- 自定义Python代码
  |
  v
create_bmp_from_bgra() / create_png_from_bgra() --- 图像编码
  |
  v
ocr_recognize_number() --- 远程OCR服务识别
  +-- [自定义IP模式] api_ip非空 -> http://{api_ip}:{port}/api/ocr (options来自api_data)
  +-- [默认本地模式] api_ip为空 -> http://127.0.0.1:{port}/api/ocr (硬编码默认options)
  |
  v
extract_number() --- 提取数字结果
```

---

## 配置工具连接状态系统

```
_start_status_timers()
  |
  +-- _ocr_test_timer (2s首次)
  |   |
  |   v
  |   _test_ocr_connection() --- 子线程检测
  |   |   +-- [自定义IP] lib.check_ocr_api(health_api_ip/shield_api_ip, port)
  |   |   +-- [默认本地] lib.check_ocr_server(port)
  |   |   +-- _ocr_status_signal.emit(ok) --- 线程安全回传
  |   |
  |   v
  |   _on_ocr_status_result(ok)
  |   +-- ok=True -> ocr_status_label="已连接"(绿色) -> 30s后重测
  |   +-- ok=False -> ocr_status_label="未连接"(红色) -> 10s后重测
  |
  +-- _game_test_timer (2s首次)
      |
      v
      _test_game_connection() --- 子线程检测
      |   +-- lib.get_game_window(process_title)
      |   +-- _game_status_signal.emit(ok) --- 线程安全回传
      |
      v
      _on_game_status_result(ok)
      +-- ok=True -> game_status_label="已连接"(绿色) -> 20s后重测
      +-- ok=False -> game_status_label="未连接"(红色) -> 5s后重测

触发重测:
  +-- ocr.port变更 -> _ocr_test_timer.start(500ms)
  +-- game.process_title变更 -> _game_test_timer.start(500ms)
  +-- OCR启用 -> _ocr_test_timer.start(500ms)
  +-- OCR禁用 -> _ocr_test_timer.stop() + 清空标签
```

---

## 多角色系统状态机

```
[空闲] --按键/手柄--> [请求切换] request_switch_character()
  |                        |
  |                        v (延迟帧)
  |                   [执行切换] execute_switch_character()
  |                        |
  |                        v (免疫帧开始)
  |                   [免疫期] switch_immunity_frames > 0
  |                        |
  |                        v (数值变化确认)
  |                +--[确认切换]--> [空闲] (active_character = target_character)
  |                |
  |                +--[数值未变]--> [延长免疫] (最多2次)
  |                                  switch_value_unchanged = True
  |
  +--[血条出现]--> [出现免疫] healthbar_appear_immunity (1帧)
```

---

## 波形编辑器架构

```
配置工具主界面
  |
  +-- [血量波形编辑按钮] --> _open_waveform_editor("health")
  +-- [盾量波形编辑按钮] --> _open_waveform_editor("shield")
        |
        v
  波形编辑器对话框
  +-- WaveformCanvas --- 可交互波形画布(拖拽编辑频率/强度)
  +-- FreqDensityWidget --- 频率密度可视化(竖线密度)
  +-- 步骤列表 --- 可折叠, 拖动排序, 频率/强度/原始数据编辑
  +-- 预设下拉框 --- PresetDelegate渲染波形预览
  +-- Dungeonlab导入/导出 --- _parse_dungeonlab() / _export_dungeonlab()
  +-- 置顶按钮 --- 底部左侧, 可切换窗口置顶
  +-- 波形文本框 --- 直接编辑十六进制波形数据
```

---

## OCR进阶配置架构

```
配置工具主界面
  |
  +-- [OCR进阶配置按钮] (位于OCR端口行) --> _open_ocr_advanced_settings()
        |
        v
  OcrAdvancedDialog
  +-- 目标选择 (QComboBox: 血量/盾量)
  |   +-- _on_target_changed() --- 切换时_flush_current_to_cache() + _load_target()
  |
  +-- IP输入 (QLineEdit: 自定义IP, 留空用默认本地)
  |
  +-- [获取配置项] --> _fetch_options()
  |   +-- GET http://{ip}:{port}/api/ocr/get_options
  |   +-- 成功 -> _build_dynamic_options(options)
  |   |   +-- 逐项生成UI控件:
  |   |   |   +-- enum -> QComboBox (optionsList)
  |   |   |   +-- boolean -> QCheckBox
  |   |   |   +-- number -> QLineEdit (isInt判断int/float)
  |   |   |   +-- text -> QLineEdit
  |   |   +-- 值优先级: saved_data[key] > _OCR_DEFAULT_OVERRIDES[key] > API default
  |
  +-- 选项滚动区 (QScrollArea, 动态生成的选项控件)
  |
  +-- [完成] --> _save_and_close()
  |   +-- _flush_current_to_cache() --- 刷新当前编辑到缓存
  |   +-- 遍历_memory_cache, 写回config:
  |   |   +-- bar_config["ocr_api_ip"] = cache["ip"]
  |   |   +-- bar_config["ocr_api_data"] = json.dumps(cache["data"])
  |   +-- self.accept()
  |
  +-- [取消] --> self.reject() (丢弃所有更改)

内存缓存结构:
  _memory_cache = {
    "health_bar": {"ip": "127.0.0.1", "data": {"ocr.language": "...", ...}},
    "shield_bar": {"ip": "", "data": {}},
  }
```

---

## v3.1 -> v3.2 主要变更

| 变更项 | 说明 |
|--------|------|
| image.py 重构 | 从纯Python逐像素操作迁移到numpy加速，新增6种滤镜函数和滤镜链系统 |
| 滤镜系统 | 新增 `FILTER_FUNCTIONS` 注册表、`apply_filters_chain` 滤镜链、Python代码滤镜 |
| 图像编码 | `create_png_from_bgra` / `create_bmp_from_bgra` 从ocr.py迁移到image.py |
| OCR模块精简 | ocr.py 不再包含滤镜实现，改为从image.py导入 |
| detect_bar_length | 新增numpy加速的条形长度检测函数 |
| check_positions_match | 使用numpy批量颜色匹配替代逐像素循环 |
| image.bak.py | 旧版image.py保留为备份文件 |
| OCR怀疑机制 | 新增 `validate_ocr_value` / `is_suspect_change` / `count_digit_changes` |
| 血量下降阈值 | 新增 `health_drop_threshold` 配置项 |
| OCR性能检测 | monitoring_loop新增OCR性能瓶颈警告 |
| 触发计数显示 | 新增 `electric_trigger_count` 和感叹号叠加显示 |

---

## v3.2 -> v3.3 主要变更

| 变更项 | 说明 |
|--------|------|
| ocr.py: 新增`_extract_ocr_text` | 从OCR响应中提取文本, 兼容多种API返回格式(code=100/dict/list等) |
| ocr.py: 新增`_parse_options_data` | 解析api_data参数(JSON字符串或dict)为选项字典, 替代yaml依赖 |
| ocr.py: 新增`check_ocr_api` | 检查远程OCR API是否可用(按IP+端口), 用于自定义IP连接测试 |
| ocr.py: `ocr_recognize_number`新增`api_ip`/`api_data`参数 | 支持自定义OCR服务IP和选项数据, 非空api_ip时走自定义API路径 |
| ocr.py: 移除yaml依赖 | 原yaml解析改由`_parse_options_data`用json替代 |
| config.py: 新增`ocr_api_ip`/`ocr_api_data`字段 | health_bar和shield_bar默认配置及缓存中新增这两个字段 |
| config_tool.py: 新增`OcrAdvancedDialog`类 | OCR进阶配置对话框, 支持动态选项加载(`/api/ocr/get_options`)和多目标内存缓存 |
| config_tool.py: 新增`_OCR_TARGETS`/`_OCR_DEFAULT_OVERRIDES` | OCR目标映射和默认选项覆盖常量 |
| config_tool.py: "OCR进阶配置"按钮移至OCR端口行 | 与OCR端口配置在同一行显示, 便于访问 |
| config_tool.py: 修复`ocr_once`3值解包错误 | 原解包为2值, 现正确解包为3值(number, elapsed, filter_time) |
| config_tool.py: 修复滤镜编辑器OCR配置路径 | 原使用错误配置路径, 现使用`health_bar.ocr_api_ip`/`health_bar.ocr_api_data` |
| config_tool.py: 滤镜编辑器OCR支持自定义IP | 使用`ocr_api_ip`配置的自定义IP进行OCR识别, 支持非本地OCR服务 |
| config_tool.py: `_test_ocr_connection`支持自定义IP | 优先使用`health_bar.ocr_api_ip`/`shield_bar.ocr_api_ip`调用`check_ocr_api` |
| lib.py: 导出`check_ocr_api` | 从ocr模块新增导出`check_ocr_api`函数 |
