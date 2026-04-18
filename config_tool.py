#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HitElectric 配置工具
用于配置和采样游戏点位颜色
"""
import sys
import os
import json
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QMessageBox, QFileDialog, QSplitter,
                             QTextEdit, QFrame, QGridLayout, QDialog, QCheckBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QPalette, QPainter, QBrush


def get_plugin_dir():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        if base_dir.endswith('dist') or os.path.basename(base_dir) == 'dist':
            base_dir = os.path.dirname(base_dir)
        plugin_dir = os.path.join(base_dir, '..', 'plugins', '挨打就电v2.2.4')
        if os.path.exists(plugin_dir):
            return os.path.abspath(plugin_dir)
        if os.path.exists(os.path.join(base_dir, 'config.json')):
            return base_dir
        return base_dir
    else:
        return os.path.dirname(os.path.abspath(__file__))


_plugin_dir = get_plugin_dir()
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

import lib


class ScreenshotDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("截图预览")
        self.setModal(True)
        layout = QVBoxLayout(self)
        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


class ColorLineEdit(QLineEdit):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self._colors = []
        self._block_size = 16
        self._block_spacing = 2
        self._left_padding = 6
        self._is_setting_text = False
        self.setColor(color)
        self.textChanged.connect(self.update_colors_from_text)

    def setColor(self, color):
        self._parse_and_set_colors(color)

    def _parse_and_set_colors(self, color):
        if color is None:
            self._colors = []
        elif isinstance(color, list):
            if len(color) > 0 and isinstance(color[0], list) and len(color[0]) >= 3:
                self._colors = [QColor(c[0], c[1], c[2]) for c in color if isinstance(c, list) and len(c) >= 3]
            elif len(color) >= 3:
                self._colors = [QColor(color[0], color[1], color[2])]
            else:
                self._colors = []
        elif isinstance(color, str) and color.startswith('#'):
            hex_color = color.lstrip('#')
            r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 0
            g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 0
            b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 0
            self._colors = [QColor(r, g, b)]
        else:
            self._colors = []
        self.update()
        self.update_text_margins()

    def setText(self, text):
        self._is_setting_text = True
        super().setText(text)
        self._is_setting_text = False
        self._parse_colors_from_text_manually(text)

    def _parse_colors_from_text_manually(self, text):
        try:
            colors = text.split('|')
            parsed_colors = []
            for color_str in colors:
                color_str = color_str.strip()
                if not color_str:
                    continue
                if color_str.startswith('#'):
                    hex_color = color_str.lstrip('#')
                    r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 0
                    g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 0
                    b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 0
                    parsed_colors.append(QColor(r, g, b))
                elif ',' in color_str:
                    parts = [int(x.strip()) for x in color_str.split(',') if x.strip()]
                    if len(parts) >= 3:
                        parsed_colors.append(QColor(parts[0], parts[1], parts[2]))
            self._colors = parsed_colors
        except Exception:
            self._colors = []
        self.update()
        self.update_text_margins()

    def update_colors_from_text(self, text):
        if self._is_setting_text:
            return
        self._parse_colors_from_text_manually(text)

    def update_text_margins(self):
        total_width = self._left_padding
        if self._colors:
            total_width += len(self._colors) * self._block_size + (len(self._colors) - 1) * self._block_spacing + 4
        self.setTextMargins(total_width, 0, 0, 0)

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self._colors:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        x = self._left_padding + 2
        y = (self.height() - self._block_size) // 2

        for i, qcolor in enumerate(self._colors):
            painter.setBrush(QBrush(qcolor))
            painter.setPen(QColor(80, 80, 80))
            painter.drawRoundedRect(x, y, self._block_size, self._block_size, 3, 3)
            x += self._block_size + self._block_spacing

        painter.end()

    def getColors(self):
        return self._colors

    def restoreState(self, text, colors):
        """用于取消采样时恢复完整状态"""
        self._is_setting_text = True
        super().setText(text)
        self._is_setting_text = False
        self._colors = colors if colors else []
        self.update()
        self.update_text_margins()


class ConfigTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = {}
        self.game_hwnd = None
        self.sampling_mode = False
        self.sampling_fields = set()
        self.sampling_backup = {}
        self.capture_region = [0, 0, 1500, 200]
        self.bmp_data = None
        self.img_width = 0

        self.init_ui()
        self.load_config()
        self.setup_hotkeys()

    def init_ui(self):
        self.setWindowTitle("HitElectric 配置工具")
        self.setGeometry(100, 100, 900, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.config_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        import_btn = QPushButton("导入预制配置")
        import_btn.clicked.connect(self.import_preset_config)
        screenshot_test_btn = QPushButton("截图测试")
        screenshot_test_btn.clicked.connect(self.screenshot_test)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(screenshot_test_btn)
        main_layout.addLayout(button_layout)

        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态: 就绪")
        status_layout.addWidget(QLabel("状态:"))
        status_layout.addWidget(self.status_label, stretch=1)
        main_layout.addLayout(status_layout)

        sampling_control_layout = QHBoxLayout()
        self.cancel_sampling_btn = QPushButton("取消采样 (ESC)")
        self.cancel_sampling_btn.clicked.connect(self.cancel_sampling)
        self.cancel_sampling_btn.setEnabled(False)
        self.finish_sampling_btn = QPushButton("完成采样 (P)")
        self.finish_sampling_btn.clicked.connect(self.finish_sampling)
        self.finish_sampling_btn.setEnabled(False)
        sampling_control_layout.addWidget(self.cancel_sampling_btn)
        sampling_control_layout.addWidget(self.finish_sampling_btn)
        main_layout.addLayout(sampling_control_layout)

    def create_config_group(self, title, config_key):
        group = QGroupBox(title)
        layout = QGridLayout(group)
        return group, layout, config_key

    def is_multi_value_field(self, field_type):
        return field_type in ['positions', 'colors']

    def format_config_value_for_display(self, value, field_type, is_color=False, config_path=""):
        if value is None:
            return ""

        if isinstance(value, bool):
            return ""

        # negative_positions 保持字符串格式直接返回
        if 'negative_positions' in config_path:
            return str(value) if value else ""

        # 颜色字段：统一处理为 #RRGGBB | #RRGGBB 格式
        if is_color or 'color' in field_type:
            if isinstance(value, str):
                # 已经是字符串格式（如 #FFFFFF|#FFFFFF），直接返回
                return value.replace('|', ' | ')
            elif isinstance(value, list):
                # 兼容旧格式：数组转换为 #RRGGBB 格式
                parts = []
                for item in value:
                    if isinstance(item, list) and len(item) >= 3:
                        parts.append(f"#{item[0]:02X}{item[1]:02X}{item[2]:02X}")
                    elif isinstance(item, int):
                        parts.append(str(item))
                    else:
                        parts.append(str(item))
                return ' | '.join(parts)
            else:
                return str(value)

        if isinstance(value, list):
            if 'position' in field_type or field_type == 'coordinate':
                if len(value) >= 2 and not isinstance(value[0], list):
                    return f"{value[0]}, {value[1]}"
                else:
                    parts = []
                    for item in value:
                        if isinstance(item, list) and len(item) >= 2:
                            parts.append(f"{item[0]}, {item[1]}")
                        else:
                            parts.append(str(item))
                    return ' | '.join(parts)
            else:
                return ', '.join(map(str, value))

        return str(value)

    def create_field_row(self, layout, row, label_text, config_path, field_type="text",
                         is_position=False, is_color=False, is_boolean=False, group_key=None, ocr_related=False):
        row_widget = QWidget()
        row_widget.field_config_path = config_path
        row_widget.ocr_related = ocr_related
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.field_config_path = config_path + "_label"
        label.field_type = "label"
        label.group_key = group_key
        label.ocr_related = ocr_related
        h_layout.addWidget(label)

        if is_boolean:
            checkbox = QCheckBox()
            checkbox.field_config_path = config_path
            checkbox.field_type = field_type
            checkbox.group_key = group_key
            value = self.get_config_value(config_path)
            if value is not None:
                checkbox.setChecked(bool(value))
            checkbox.stateChanged.connect(lambda state, cb=checkbox: self.on_checkbox_changed(cb, state))
            h_layout.addWidget(checkbox)
            h_layout.addStretch()
            layout.addWidget(row_widget, row, 0, 1, 5)
            row_widget.checkbox = checkbox
            return row_widget

        if is_position or is_color:
            btn = QPushButton("采样")
            btn.setCheckable(True)
            btn.setFixedWidth(60)
            btn.field_config_path = config_path
            btn.field_type = field_type
            btn.group_key = group_key
            btn.ocr_related = ocr_related
            btn.toggled.connect(lambda checked, b=btn: self.toggle_sampling(b, checked))
            h_layout.addWidget(btn)

        if is_color:
            line_edit = ColorLineEdit()
        else:
            line_edit = QLineEdit()

        line_edit.field_config_path = config_path
        line_edit.field_type = field_type
        line_edit.group_key = group_key
        line_edit.ocr_related = ocr_related
        if is_position:
            line_edit.setPlaceholderText("x, y 或 多个用 | 分隔")
        elif is_color:
            line_edit.setPlaceholderText("#RRGGBB 或 多个用 | 分隔")

        value = self.get_config_value(config_path)
        display_text = self.format_config_value_for_display(value, field_type, is_color, config_path)
        if is_color:
            line_edit.setColor(value)
            if display_text:
                line_edit.setText(display_text)
        elif display_text:
            line_edit.setText(display_text)

        text_changed_callback = lambda text, le=line_edit: self.on_field_changed(le, text)
        line_edit.textChanged.connect(text_changed_callback)
        h_layout.addWidget(line_edit, stretch=1)
        layout.addWidget(row_widget, row, 0, 1, 5)

        row_widget.line_edit = line_edit
        if is_position or is_color:
            row_widget.btn = btn

        return row_widget

    def on_checkbox_changed(self, checkbox, state):
        path = checkbox.field_config_path
        self.set_config_value(path, state == Qt.CheckState.Checked.value)
        
        # 如果是ocr_end_trigger改变，更新结束点位置的可见性
        if path.endswith('ocr_end_trigger'):
            ocr_enabled = self.get_config_value('ocr.enabled')
            if ocr_enabled:
                if 'health_bar' in path:
                    self._toggle_end_position_visibility(self.health_bar_widgets, state == Qt.CheckState.Checked.value)
                elif 'shield_bar' in path:
                    self._toggle_end_position_visibility(self.shield_bar_widgets, state == Qt.CheckState.Checked.value)
    
    def _toggle_end_position_visibility(self, widgets_dict, end_trigger_enabled):
        """切换结束点位置的可见性"""
        if 'end' in widgets_dict:
            widgets_dict['end'].setVisible(end_trigger_enabled)

    def on_ocr_toggled(self, state):
        """OCR启用/禁用时的显示/隐藏逻辑"""
        is_enabled = state == Qt.CheckState.Checked.value
        self.set_config_value("ocr.enabled", is_enabled)

        self._update_ocr_ui_visibility(is_enabled)

    def _update_ocr_ui_visibility(self, ocr_enabled):
        """根据OCR启用状态更新UI可见性 - 使用已保存的widget引用"""
        if not hasattr(self, 'group_widgets'):
            return

        plus_group = self.group_widgets.get('plus_group')
        if plus_group:
            plus_group.setVisible(not ocr_enabled)

        self._toggle_bar_widgets_visibility(self.health_bar_widgets, ocr_enabled)
        self._toggle_bar_widgets_visibility(self.shield_bar_widgets, ocr_enabled)

        # 控制OCR端口配置的可见性
        if hasattr(self, 'ocr_port_row'):
            self.ocr_port_row.setVisible(ocr_enabled)

    def _toggle_bar_widgets_visibility(self, widgets_dict, ocr_enabled):
        """切换血条/盾条配置的可见性

        OCR启用时：
          - 显示: ocr_top_left, ocr_bottom_right, ocr_number_color, ocr_number_tolerance (OCR专属字段)
          - 显示: ocr_end_trigger (结束点触发配置)
          - 根据ocr_end_trigger值显示/隐藏: end (结束点位置)
          - 显示: start, colors, tolerance (传统字段，OCR模式下用于检测起始/结束点)
          - 隐藏: sample_points (采样点数，OCR模式下不需要)
        OCR禁用时相反
        """
        # OCR专属字段
        ocr_fields = {'ocr_top_left', 'ocr_bottom_right', 'ocr_number_color', 'ocr_number_tolerance'}
        # 传统字段（OCR模式下也显示，用于检测起始/结束点）
        traditional_fields = {'start', 'colors', 'tolerance'}
        # OCR模式下隐藏的传统字段
        ocr_hidden_fields = {'sample_points'}
        # 结束点相关字段
        end_trigger_field = 'ocr_end_trigger'
        end_position_field = 'end'

        # 获取ocr_end_trigger的当前值（从checkbox获取）
        ocr_end_trigger_enabled = True
        if end_trigger_field in widgets_dict:
            row_widget = widgets_dict[end_trigger_field]
            if hasattr(row_widget, 'checkbox'):
                ocr_end_trigger_enabled = row_widget.checkbox.isChecked()

        for key, widget in widgets_dict.items():
            if key in ocr_fields:
                # OCR专属字段：OCR启用时显示
                widget.setVisible(ocr_enabled)
            elif key in traditional_fields:
                # 传统字段：始终显示（OCR模式下用于检测起始/结束点）
                widget.setVisible(True)
            elif key in ocr_hidden_fields:
                # OCR模式下隐藏的传统字段
                widget.setVisible(not ocr_enabled)
            elif key == end_trigger_field:
                # ocr_end_trigger配置：OCR启用时显示
                widget.setVisible(ocr_enabled)
            elif key == end_position_field:
                # 结束点位置：OCR启用且ocr_end_trigger为True时显示，或OCR禁用时显示
                if ocr_enabled:
                    widget.setVisible(ocr_end_trigger_enabled)
                else:
                    widget.setVisible(True)
    
    def _get_widget_row(self, layout, widget):
        """获取控件在布局中的行号"""
        if isinstance(layout, QGridLayout):
            for row in range(layout.rowCount()):
                for col in range(layout.columnCount()):
                    item = layout.itemAtPosition(row, col)
                    if item and item.widget() == widget:
                        return row
        return -1

    def get_config_value(self, path):
        keys = path.split('.')
        value = self.config.get('plugins', {})
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def set_config_value(self, path, value):
        keys = path.split('.')
        config = self.config.setdefault('plugins', {})
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        config[keys[-1]] = value

    def on_field_changed(self, line_edit, text):
        path = line_edit.field_config_path
        field_type = line_edit.field_type

        try:
            if 'position' in field_type or field_type == 'coordinate':
                # negative_positions 保持字符串格式，不转换为数组
                if 'negative_positions' in path:
                    self.set_config_value(path, text)
                elif '|' in text:
                    items = [item.strip() for item in text.split('|') if item.strip()]
                    result = []
                    for item in items:
                        if ',' in item:
                            parts = [int(x.strip()) for x in item.split(',') if x.strip()]
                            if len(parts) >= 2:
                                result.append(parts[:2])
                    self.set_config_value(path, result if result else items)
                elif ',' in text:
                    parts = [int(x.strip()) for x in text.split(',') if x.strip()]
                    self.set_config_value(path, parts)
            elif 'color' in field_type:
                # 统一保存为 #FFFFFF | #FFFFFF 格式字符串
                if '|' in text:
                    # 多颜色：统一格式为 #RRGGBB|#RRGGBB
                    items = [item.strip() for item in text.split('|') if item.strip()]
                    normalized_items = []
                    for item in items:
                        if item.startswith('#'):
                            # 已经是 #RRGGBB 格式，保持原样
                            normalized_items.append(item.upper())
                        elif ',' in item:
                            # R,G,B 格式，转换为 #RRGGBB
                            parts = [int(x.strip()) for x in item.split(',') if x.strip()]
                            if len(parts) >= 3:
                                normalized_items.append(f"#{parts[0]:02X}{parts[1]:02X}{parts[2]:02X}")
                    self.set_config_value(path, '|'.join(normalized_items) if normalized_items else text)
                elif text.startswith('#'):
                    # 单颜色 #RRGGBB 格式，保持原样
                    self.set_config_value(path, text.upper())
                elif ',' in text:
                    # R,G,B 格式，转换为 #RRGGBB
                    parts = [int(x.strip()) for x in text.split(',') if x.strip()]
                    if len(parts) >= 3:
                        self.set_config_value(path, f"#{parts[0]:02X}{parts[1]:02X}{parts[2]:02X}")
                    else:
                        self.set_config_value(path, text)
            else:
                if text.isdigit():
                    self.set_config_value(path, int(text))
                else:
                    try:
                        num = float(text)
                        self.set_config_value(path, num)
                    except ValueError:
                        self.set_config_value(path, text)
        except Exception as e:
            pass

    def load_config(self):
        config_path = os.path.join(_plugin_dir, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                if isinstance(raw_data, dict) and 'config' in raw_data:
                    self.config = raw_data['config']
                elif isinstance(raw_data, dict) and 'plugins' in raw_data:
                    self.config = raw_data
                else:
                    self.config = {'plugins': raw_data if isinstance(raw_data, dict) else {}}
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法加载配置文件: {e}\n路径: {config_path}")
            self.config = {'plugins': {}}

        self.build_config_ui()

    def build_config_ui(self):
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.group_widgets = {}

        game_group, game_layout, _ = self.create_config_group("游戏配置", "game")
        row = 0

        title_layout = QHBoxLayout()
        title_label = QLabel("游戏窗口标题:")
        title_layout.addWidget(title_label)

        process_title_edit = QLineEdit()
        process_title_edit.field_config_path = "game.process_title"
        process_title_edit.field_type = "text"
        process_title_edit.group_key = "game"
        value = self.get_config_value("game.process_title")
        if value is not None:
            process_title_edit.setText(str(value))
        process_title_edit.textChanged.connect(lambda text: self.on_field_changed(process_title_edit, text))
        title_layout.addWidget(process_title_edit, stretch=1)

        apply_btn = QPushButton("应用并重启采样")
        apply_btn.clicked.connect(self.apply_game_title)
        apply_btn.setFixedWidth(140)
        title_layout.addWidget(apply_btn)

        game_layout.addLayout(title_layout, row, 0, 1, 5)
        row += 1

        # 启用OCR放在游戏标题下方
        ocr_row = self.create_field_row(game_layout, row, "启用OCR (需要安装并启动Umi-OCR软件):", "ocr.enabled",
                                             field_type="boolean", is_boolean=True)
        ocr_row.checkbox.stateChanged.connect(self.on_ocr_toggled)
        row += 1

        # OCR端口配置（OCR专属）
        self.ocr_port_row = self.create_field_row(game_layout, row, "OCR端口:", "ocr.port",
                                                   field_type="number", ocr_related=True)
        row += 1

        self.create_field_row(game_layout, row, "区域左上角:", "game.region.top_left",
                              field_type="coordinate", is_position=True, group_key="game.region")
        row += 1
        self.create_field_row(game_layout, row, "区域右下角:", "game.region.bottom_right",
                              field_type="coordinate", is_position=True, group_key="game.region")
        row += 1
        self.create_field_row(game_layout, row, "扫描间隔:", "scan_interval",
                              field_type="number")
        row += 1

        self.config_layout.addWidget(game_group)

        plus_group, plus_layout, _ = self.create_config_group("+号检测配置", "plus_sign")
        self.group_widgets['plus_group'] = plus_group
        row = 0
        self.create_field_row(plus_layout, row, "+号位置:", "plus_sign.positions",
                              field_type="positions", is_position=True, group_key="plus_sign")
        row += 1
        self.create_field_row(plus_layout, row, "+号颜色:", "plus_sign.colors",
                              field_type="colors", is_color=True, group_key="plus_sign")
        row += 1
        self.create_field_row(plus_layout, row, "反向位置:", "plus_sign.negative_positions",
                              field_type="positions", is_position=True, group_key="plus_sign")
        row += 1
        self.create_field_row(plus_layout, row, "反向颜色:", "plus_sign.negative_colors",
                              field_type="colors", is_color=True, group_key="plus_sign")
        row += 1
        self.create_field_row(plus_layout, row, "容差:", "plus_sign.tolerance",
                              field_type="number")
        row += 1
        self.config_layout.addWidget(plus_group)

        spectate_group, spectate_layout, _ = self.create_config_group("观战检测配置", "spectate")
        self.group_widgets['spectate_group'] = spectate_group
        row = 0
        self.create_field_row(spectate_layout, row, "观战位置:", "spectate.positions",
                              field_type="positions", is_position=True, group_key="spectate")
        row += 1
        self.create_field_row(spectate_layout, row, "观战颜色:", "spectate.colors",
                              field_type="colors", is_color=True, group_key="spectate")
        row += 1
        self.create_field_row(spectate_layout, row, "容差:", "spectate.tolerance",
                              field_type="number")
        row += 1
        self.config_layout.addWidget(spectate_group)

        health_group, health_layout, _ = self.create_config_group("血条配置", "health_bar")
        self.group_widgets['health_group'] = health_group
        self.health_bar_widgets = {}
        row = 0
        self.health_bar_widgets['enabled'] = self.create_field_row(health_layout, row, "启用血条:", "health_bar.enabled",
                                                                    field_type="boolean", is_boolean=True)
        row += 1
        # --- OCR配置区域 ---
        self.health_bar_widgets['ocr_top_left'] = self.create_field_row(health_layout, row, "OCR-数字左上角:", "health_bar.ocr_top_left",
                                                                        field_type="coordinate", is_position=True, group_key="health_bar", ocr_related=True)
        row += 1
        self.health_bar_widgets['ocr_bottom_right'] = self.create_field_row(health_layout, row, "OCR-数字右下角:", "health_bar.ocr_bottom_right",
                                                                            field_type="coordinate", is_position=True, group_key="health_bar", ocr_related=True)
        row += 1
        self.health_bar_widgets['ocr_number_color'] = self.create_field_row(health_layout, row, "OCR-血量颜色:", "health_bar.ocr_number_color",
                                                                             field_type="colors", is_color=True, group_key="health_bar", ocr_related=True)
        row += 1
        self.health_bar_widgets['ocr_number_tolerance'] = self.create_field_row(health_layout, row, "OCR-血量容差:", "health_bar.ocr_number_tolerance",
                                                                                 field_type="number", ocr_related=True)
        row += 1
        self.health_bar_widgets['ocr_end_trigger'] = self.create_field_row(health_layout, row, "血条框填满 但 血量数值下降 时不触发电击:", "health_bar.ocr_end_trigger",
                                                                            field_type="boolean", is_boolean=True)
        row += 1
        # --- 传统配置区域（用于起始/结束点检测） ---
        self.health_bar_widgets['start'] = self.create_field_row(health_layout, row, "起始位置:", "health_bar.start",
                                                                  field_type="coordinate", is_position=True, group_key="health_bar")
        row += 1
        self.health_bar_widgets['end'] = self.create_field_row(health_layout, row, "结束位置:", "health_bar.end",
                                                                field_type="coordinate", is_position=True, group_key="health_bar")
        row += 1
        self.health_bar_widgets['colors'] = self.create_field_row(health_layout, row, "血条颜色:", "health_bar.colors",
                                                                   field_type="colors", is_color=True, group_key="health_bar")
        row += 1
        self.health_bar_widgets['tolerance'] = self.create_field_row(health_layout, row, "容差:", "health_bar.tolerance",
                                                                     field_type="number")
        row += 1
        self.health_bar_widgets['sample_points'] = self.create_field_row(health_layout, row, "采样点数:", "health_bar.sample_points",
                                                                         field_type="number")
        row += 1
        # --- 电击强度配置 ---
        self.health_bar_widgets['strength'] = self.create_field_row(health_layout, row, "强度A:", "health_bar.strength",
                                                                     field_type="number")
        row += 1
        self.health_bar_widgets['strength_b'] = self.create_field_row(health_layout, row, "强度B:", "health_bar.strength_b",
                                                                       field_type="number")
        row += 1
        self.config_layout.addWidget(health_group)

        shield_group, shield_layout, _ = self.create_config_group("盾条配置", "shield_bar")
        self.group_widgets['shield_group'] = shield_group
        self.shield_bar_widgets = {}
        row = 0
        self.shield_bar_widgets['enabled'] = self.create_field_row(shield_layout, row, "启用盾条:", "shield_bar.enabled",
                                                                    field_type="boolean", is_boolean=True)
        row += 1
        # --- OCR配置区域 ---
        self.shield_bar_widgets['ocr_top_left'] = self.create_field_row(shield_layout, row, "OCR-数字左上角:", "shield_bar.ocr_top_left",
                                                                        field_type="coordinate", is_position=True, group_key="shield_bar", ocr_related=True)
        row += 1
        self.shield_bar_widgets['ocr_bottom_right'] = self.create_field_row(shield_layout, row, "OCR-数字右下角:", "shield_bar.ocr_bottom_right",
                                                                            field_type="coordinate", is_position=True, group_key="shield_bar", ocr_related=True)
        row += 1
        self.shield_bar_widgets['ocr_number_color'] = self.create_field_row(shield_layout, row, "OCR-盾量颜色:", "shield_bar.ocr_number_color",
                                                                             field_type="colors", is_color=True, group_key="shield_bar", ocr_related=True)
        row += 1
        self.shield_bar_widgets['ocr_number_tolerance'] = self.create_field_row(shield_layout, row, "OCR-盾量容差:", "shield_bar.ocr_number_tolerance",
                                                                                 field_type="number", ocr_related=True)
        row += 1
        self.shield_bar_widgets['ocr_end_trigger'] = self.create_field_row(shield_layout, row, "盾条框填满 但 盾量数值下降 时不触发电击:", "shield_bar.ocr_end_trigger",
                                                                            field_type="boolean", is_boolean=True)
        row += 1
        # --- 传统配置区域（用于起始/结束点检测） ---
        self.shield_bar_widgets['start'] = self.create_field_row(shield_layout, row, "起始位置:", "shield_bar.start",
                                                                  field_type="coordinate", is_position=True, group_key="shield_bar")
        row += 1
        self.shield_bar_widgets['end'] = self.create_field_row(shield_layout, row, "结束位置:", "shield_bar.end",
                                                                field_type="coordinate", is_position=True, group_key="shield_bar")
        row += 1
        self.shield_bar_widgets['colors'] = self.create_field_row(shield_layout, row, "盾条颜色:", "shield_bar.colors",
                                                                   field_type="colors", is_color=True, group_key="shield_bar")
        row += 1
        self.shield_bar_widgets['tolerance'] = self.create_field_row(shield_layout, row, "容差:", "shield_bar.tolerance",
                                                                     field_type="number")
        row += 1
        self.shield_bar_widgets['sample_points'] = self.create_field_row(shield_layout, row, "采样点数:", "shield_bar.sample_points",
                                                                         field_type="number")
        row += 1
        # --- 电击强度配置 ---
        self.shield_bar_widgets['strength'] = self.create_field_row(shield_layout, row, "强度A:", "shield_bar.strength",
                                                                     field_type="number")
        row += 1
        self.shield_bar_widgets['strength_b'] = self.create_field_row(shield_layout, row, "强度B:", "shield_bar.strength_b",
                                                                       field_type="number")
        row += 1
        # 新增配置：盾存在时不扣血
        self.shield_bar_widgets['blocks_health'] = self.create_field_row(shield_layout, row, "盾存在时阻止扣血:", "shield_bar.blocks_health",
                                                                          field_type="boolean", is_boolean=True)
        row += 1
        self.config_layout.addWidget(shield_group)

        overlap_group, overlap_layout, _ = self.create_config_group("重叠电击配置", "overlap")
        row = 0
        self.create_field_row(overlap_layout, row, "强度增加:", "overlap.strength_add",
                              field_type="number")
        row += 1
        self.create_field_row(overlap_layout, row, "最大强度:", "overlap.strength_max",
                              field_type="number")
        row += 1
        self.config_layout.addWidget(overlap_group)

        overlay_group, overlay_layout, _ = self.create_config_group("悬浮窗配置", "overlay")
        row = 0
        self.create_field_row(overlay_layout, row, "启用悬浮窗:", "overlay.enabled",
                              field_type="boolean", is_boolean=True)
        row += 1
        self.config_layout.addWidget(overlay_group)

        ocr_enabled = self.get_config_value("ocr.enabled")
        if ocr_enabled is not None:
            self._update_ocr_ui_visibility(bool(ocr_enabled))

        self.config_layout.addStretch()

    def setup_hotkeys(self):
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if self.sampling_mode:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.perform_sampling()
            elif event.key() == Qt.Key.Key_P:
                self.finish_sampling()
            elif event.key() == Qt.Key.Key_Escape:
                self.cancel_sampling()
        super().keyPressEvent(event)

    def toggle_sampling(self, button, checked):
        if checked:
            if not self.sampling_mode:
                self.start_sampling_mode()
            self.sampling_fields.add(button)
            button.setStyleSheet("background-color: red; color: white;")
            self.status_label.setText(f"状态: 采样模式 - 已选择 {len(self.sampling_fields)} 个字段 (按 Enter 采样)")
        else:
            self.sampling_fields.discard(button)
            button.setStyleSheet("")
            if not self.sampling_fields:
                self.status_label.setText("状态: 采样模式 - 未选择字段 (点击字段旁的按钮选择)")
            else:
                self.status_label.setText(f"状态: 采样模式 - 已选择 {len(self.sampling_fields)} 个字段 (按 Enter 采样)")

    def _backup_widget_state(self, layout):
        """递归备份布局中所有可配置控件的状态"""
        if not layout:
            return

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue

            # 如果是子布局，递归处理
            if item.layout():
                self._backup_widget_state(item.layout())
                continue

            widget = item.widget()
            if not widget:
                continue

            # 备份有 field_config_path 属性的控件（只备份输入框和复选框，跳过按钮）
            if hasattr(widget, 'field_config_path'):
                path = widget.field_config_path
                if isinstance(widget, ColorLineEdit):
                    self.sampling_backup[path] = {
                        'text': widget.text(),
                        'colors': widget.getColors()
                    }
                elif isinstance(widget, QLineEdit):
                    self.sampling_backup[path] = {
                        'text': widget.text(),
                        'colors': None
                    }
                elif isinstance(widget, QCheckBox):
                    self.sampling_backup[path] = {
                        'checked': widget.isChecked()
                    }
                # QPushButton 不备份，但它可能有内部布局需要处理
                # 继续执行下面的内部布局检查，而不是直接 continue

            # 如果控件有内部布局（如 QGroupBox），也递归处理
            inner_layout = widget.layout()
            if inner_layout:
                self._backup_widget_state(inner_layout)

    def start_sampling_mode(self):
        self.sampling_mode = True
        self.sampling_backup = {}

        # 递归备份所有配置控件的状态
        self._backup_widget_state(self.config_layout)

        # 预加载游戏窗口句柄和截图资源（避免首次采样卡顿）
        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
        if not self.game_hwnd:
            self.status_label.setText("状态: 正在初始化游戏窗口...")
            QApplication.processEvents()
            self.game_hwnd = lib.get_game_window(process_title=game_title)
        
        if self.game_hwnd and (not self.bmp_data or self.img_width == 0):
            self.status_label.setText("状态: 正在预热截图资源...")
            QApplication.processEvents()
            try:
                self.bmp_data, rx, ry, rw, rh, self.img_width = lib.capture_screen_fast(hwnd=self.game_hwnd)
                self.capture_region = [rx, ry, rw, rh]
                self.status_label.setText(f"状态: 截图资源已准备就绪 ({rw}x{rh})")
            except Exception as e:
                self.status_label.setText(f"状态: 预热失败: {e}")

        self.cancel_sampling_btn.setEnabled(True)
        self.finish_sampling_btn.setEnabled(True)
        if '预热' not in self.status_label.text():
            self.status_label.setText("状态: 采样模式已启动 - 点击字段旁的按钮选择要采样的字段")

    def _find_widget_by_config_path(self, layout, config_path, prefer_input=True):
        """递归查找指定配置路径的控件
        
        Args:
            layout: 要搜索的布局
            config_path: 配置路径
            prefer_input: 是否优先返回输入框（QLineEdit/ColorLineEdit）而不是按钮
        """
        if not layout:
            return None

        # 第一轮：优先查找输入框
        if prefer_input:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if not item:
                    continue

                # 先检查是否是布局项，递归处理
                sub_layout = item.layout()
                if sub_layout:
                    result = self._find_widget_by_config_path(sub_layout, config_path, prefer_input=True)
                    if result and isinstance(result, (QLineEdit, ColorLineEdit)):
                        return result

                # 再检查是否是控件
                widget = item.widget()
                if widget:
                    # 检查控件本身是否符合条件且是输入框
                    if (hasattr(widget, 'field_config_path') and 
                        widget.field_config_path == config_path and
                        isinstance(widget, (QLineEdit, ColorLineEdit))):
                        return widget
                    
                    # 如果控件有内部布局（如 QGroupBox），也递归处理
                    inner_layout = widget.layout()
                    if inner_layout:
                        result = self._find_widget_by_config_path(inner_layout, config_path, prefer_input=True)
                        if result and isinstance(result, (QLineEdit, ColorLineEdit)):
                            return result

        # 第二轮：查找任何匹配的控件（包括按钮）
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue

            sub_layout = item.layout()
            if sub_layout:
                result = self._find_widget_by_config_path(sub_layout, config_path, prefer_input=False)
                if result:
                    return result

            widget = item.widget()
            if widget:
                if hasattr(widget, 'field_config_path') and widget.field_config_path == config_path:
                    return widget
                
                inner_layout = widget.layout()
                if inner_layout:
                    result = self._find_widget_by_config_path(inner_layout, config_path, prefer_input=False)
                    if result:
                        return result

        return None

    def perform_sampling(self):
        if not self.sampling_mode or not self.sampling_fields:
            return

        abs_x, abs_y = lib.get_cursor_position()

        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
        if not self.game_hwnd:
            self.game_hwnd = lib.get_game_window(process_title=game_title)

        client_offset_x, client_offset_y = 0, 0
        if self.game_hwnd:
            client_offset_x, client_offset_y = lib.get_client_offset(self.game_hwnd)

        rel_x = abs_x - client_offset_x
        rel_y = abs_y - client_offset_y

        sample_result = lib.sample_color_at_cursor(hwnd=self.game_hwnd)
        pixel = sample_result['color']
        hex_color = sample_result['hex_color']

        has_color_sample = any('color' in btn.field_type for btn in self.sampling_fields)

        debug_info = []
        for button in self.sampling_fields:
            path = button.field_config_path
            field_type = button.field_type
            is_multi = self.is_multi_value_field(field_type)

            # 使用递归方法查找控件
            widget = self._find_widget_by_config_path(self.config_layout, path)
            
            debug_msg = f"查找: {path} | 类型: {field_type} | 结果: {type(widget).__name__ if widget else 'None'}"
            debug_info.append(debug_msg)
            print(f"[DEBUG] {debug_msg}")
            
            if widget and isinstance(widget, (QLineEdit, ColorLineEdit)):
                current_text = widget.text().strip()

                if 'position' in field_type or field_type in ['coordinate', 'positions']:
                    new_value = f"{rel_x}, {rel_y}"
                    if is_multi and current_text:
                        widget.setText(f"{current_text} | {new_value}")
                    else:
                        widget.setText(new_value)
                elif 'color' in field_type:
                    if is_multi and current_text:
                        widget.setText(f"{current_text} | {hex_color}")
                    else:
                        widget.setText(hex_color)
                
                print(f"[DEBUG] 已设置文本: {widget.text()}")
            else:
                print(f"[DEBUG] 未找到有效控件或类型不匹配: path={path}, widget={widget}")

        print(f"[DEBUG] 采样完成 - 查找结果: {' | '.join(debug_info)}")

        if has_color_sample:
            self.status_label.setText(f"状态: 已采样 ({rel_x}, {rel_y}) 颜色:{hex_color} - 按 Enter 继续采样，P 完成")
        else:
            self.status_label.setText(f"状态: 已采样 ({rel_x}, {rel_y}) - 按 Enter 继续采样，P 完成")

    def _restore_widget_state(self, layout, path, backup_data):
        """递归恢复布局中指定控件的状态"""
        if not layout:
            return False

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue

            # 如果是子布局，递归处理
            if item.layout():
                if self._restore_widget_state(item.layout(), path, backup_data):
                    return True
                continue

            widget = item.widget()
            if not widget:
                continue

            # 检查控件本身是否是目标控件（优先匹配输入框）
            if hasattr(widget, 'field_config_path') and widget.field_config_path == path:
                # 确保是输入框类型才恢复（避免找到按钮）
                if isinstance(widget, ColorLineEdit) and 'text' in backup_data:
                    widget.blockSignals(True)
                    widget.restoreState(backup_data['text'], backup_data.get('colors'))
                    widget.blockSignals(False)
                    return True
                elif isinstance(widget, QLineEdit) and 'text' in backup_data:
                    widget.blockSignals(True)
                    widget.setText(backup_data['text'])
                    widget.blockSignals(False)
                    return True
                elif isinstance(widget, QCheckBox) and 'checked' in backup_data:
                    widget.blockSignals(True)
                    widget.setChecked(backup_data['checked'])
                    widget.blockSignals(False)
                    return True
                # 如果不是输入框/复选框（如按钮），不返回，继续检查内部布局

            # 如果控件有内部布局（如 QGroupBox），也递归处理
            inner_layout = widget.layout()
            if inner_layout:
                if self._restore_widget_state(inner_layout, path, backup_data):
                    return True

        return False

    def cancel_sampling(self):
        # 递归恢复所有备份的状态
        for path, backup_data in self.sampling_backup.items():
            self._restore_widget_state(self.config_layout, path, backup_data)

        for button in list(self.sampling_fields):
            button.setChecked(False)
            button.setStyleSheet("")

        self.sampling_fields.clear()
        self.sampling_mode = False
        self.sampling_backup = {}
        self.cancel_sampling_btn.setEnabled(False)
        self.finish_sampling_btn.setEnabled(False)
        self.status_label.setText("状态: 采样已取消，已恢复原始值")

    def finish_sampling(self):
        for button in list(self.sampling_fields):
            button.setChecked(False)
            button.setStyleSheet("")

        self.sampling_fields.clear()
        self.sampling_mode = False
        self.sampling_backup = {}
        self.cancel_sampling_btn.setEnabled(False)
        self.finish_sampling_btn.setEnabled(False)
        self.status_label.setText("状态: 采样完成")

    def capture_screenshot_for_test(self):
        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
        self.game_hwnd = lib.get_game_window(process_title=game_title)

        if not self.game_hwnd:
            raise Exception(f"未找到游戏窗口 '{game_title}'")

        region_config = self.config.get('plugins', {}).get('game', {}).get('region', {})
        top_left = lib.parse_coordinate(region_config.get('top_left', [0, 1300]))
        bottom_right = lib.parse_coordinate(region_config.get('bottom_right', [1500, 1500]))

        if isinstance(top_left, list) and len(top_left) >= 2 and isinstance(bottom_right, list) and len(bottom_right) >= 2:
            x = max(0, top_left[0])
            y = max(0, top_left[1])
            width = max(10, bottom_right[0] - top_left[0])
            height = max(10, bottom_right[1] - top_left[1])
            self.capture_region = [int(x), int(y), int(width), int(height)]

        result = lib.capture_screen_fast(self.capture_region, hwnd=self.game_hwnd)
        if result and len(result) >= 6:
            self.bmp_data, rx, ry, rw, rh, img_width = result
            self.img_width = img_width
            return rw, rh
        raise Exception("截图失败")

    def screenshot_test(self):
        try:
            rw, rh = self.capture_screenshot_for_test()

            from PIL import Image
            import numpy as np
            buf_size = rw * rh * 4
            raw_data = bytes(self.bmp_data[:buf_size])
            arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((rh, rw, 4))
            rgb_arr = arr[:, :, 2::-1].copy()
            qimage = QImage(rgb_arr.tobytes(), rw, rh, rw * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)

            dialog = ScreenshotDialog(pixmap, self)
            dialog.exec()
            self.status_label.setText(f"状态: 截图测试成功 ({rw}x{rh})")
        except ImportError:
            QMessageBox.warning(self, "错误", "截图功能需要安装 PIL 和 numpy 库\n请运行: pip install pillow numpy")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"截图失败: {e}")
            self.status_label.setText(f"状态: 截图出错 - {e}")

    def save_config(self):
        config_path = os.path.join(_plugin_dir, 'config.json')
        try:
            save_data = {"config": self.config}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "成功", f"配置已保存到:\n{config_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")

    def import_preset_config(self):
        preset_dir = os.path.join(_plugin_dir, '预制采样配置-使用配置工具读取')

        if not os.path.exists(preset_dir):
            QMessageBox.warning(self, "错误", f"预制配置文件夹不存在:\n{preset_dir}")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择预制配置文件", preset_dir, "JSON 文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    preset_config = json.load(f)

                plugins_preset = preset_config.get('config', {}).get('plugins', {})
                import_options = QMessageBox.question(
                    self, "导入选项",
                    "要导入全部配置还是仅导入采样点位置和颜色？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if import_options == QMessageBox.StandardButton.Yes:
                    self.config['plugins'].update(plugins_preset)
                else:
                    position_keys = [
                        'plus_sign.positions', 'plus_sign.negative_positions',
                        'spectate.positions',
                        'health_bar.start', 'health_bar.end',
                        'shield_bar.start', 'shield_bar.end'
                    ]
                    color_keys = [
                        'plus_sign.colors', 'plus_sign.negative_colors',
                        'spectate.colors',
                        'health_bar.colors', 'shield_bar.colors'
                    ]

                    for key in position_keys + color_keys:
                        keys = key.split('.')
                        value = plugins_preset
                        for k in keys:
                            if isinstance(value, dict):
                                value = value.get(k)
                            else:
                                value = None
                                break
                        if value is not None:
                            self.set_config_value(key, value)

                self.build_config_ui()
                QMessageBox.information(self, "成功", "预制配置已导入，界面已刷新")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def on_process_title_changed(self, text):
        self.set_config_value("game.process_title", text)

    def apply_game_title(self):
        self.game_hwnd = None
        self.bmp_data = None
        self.img_width = 0
        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
        self.status_label.setText(f"状态: 已切换游戏窗口为 '{game_title}'，请进行截图或采样")


def main():
    app = QApplication(sys.argv)
    window = ConfigTool()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
