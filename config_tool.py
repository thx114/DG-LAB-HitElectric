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
import threading
import time
import dxcam
_dxcamInput = dxcam
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QGroupBox,
                             QScrollArea, QMessageBox, QFileDialog, QSplitter,
                             QTextEdit, QFrame, QGridLayout, QDialog, QCheckBox, QLayout,
                             QComboBox, QFormLayout, QSpinBox, QSizePolicy,
                             QPlainTextEdit, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRegularExpression, QEvent, QObject, QPoint
from PyQt6.QtGui import (QPixmap, QImage, QColor, QPalette, QPainter, QBrush, QPen,
                          QSyntaxHighlighter, QTextCharFormat, QFont, QKeySequence, QTextCursor)


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
from config import Config


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#569cd6"))
        keyword_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in ["for", "in", "if", "else", "elif", "while", "def", "class",
                    "return", "import", "from", "as", "not", "and", "or", "is",
                    "None", "True", "False", "pass", "break", "continue", "range",
                    "len", "int", "float", "str", "bytes", "bytearray", "list"]:
            self._rules.append((QRegularExpression(r"\b" + kw + r"\b"), keyword_fmt))

        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#dcdcaa"))
        for name in ["data", "width", "height"]:
            self._rules.append((QRegularExpression(r"\b" + name + r"\b"), builtin_fmt))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#b5cea8"))
        self._rules.append((QRegularExpression(r"\b[0-9]+\.?[0-9]*\b"), number_fmt))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#ce9178"))
        self._rules.append((QRegularExpression(r'".*?"'), string_fmt))
        self._rules.append((QRegularExpression(r"'.*?'"), string_fmt))

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6a9955"))
        self._rules.append((QRegularExpression(r"#[^\n]*"), comment_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


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


class GameScreenshotWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, pixmap, window_title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        screen = QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0
        pixmap.setDevicePixelRatio(dpr)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel()
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(label)

        logical_w = int(pixmap.width() / dpr)
        logical_h = int(pixmap.height() / dpr)
        self.setFixedSize(logical_w, logical_h)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


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
        elif isinstance(color, str):
            parsed = []
            for part in color.split('|'):
                part = part.strip()
                if not part:
                    continue
                if part.startswith('#'):
                    hex_color = part.lstrip('#')
                    r = int(hex_color[0:2], 16) if len(hex_color) >= 2 else 0
                    g = int(hex_color[2:4], 16) if len(hex_color) >= 4 else 0
                    b = int(hex_color[4:6], 16) if len(hex_color) >= 6 else 0
                    parsed.append(QColor(r, g, b))
                elif ',' in part:
                    try:
                        parts = [int(x.strip()) for x in part.split(',') if x.strip()]
                        if len(parts) >= 3:
                            parsed.append(QColor(parts[0], parts[1], parts[2]))
                    except ValueError:
                        pass
            self._colors = parsed
            if color and self.text() != color:
                self._is_setting_text = True
                super().setText(color)
                self._is_setting_text = False
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


_DG_FREQ_MAP = [
    10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
    30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
    50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72, 74, 76, 78,
    80, 85, 90, 95,
    100, 110, 120, 130, 140, 150, 160, 170, 180, 190,
    200, 233, 266, 300, 333, 366,
    400, 450, 500, 550,
    600, 700, 800, 900, 1000
]

_DG_SECTION_TIME_MAP = [
    0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6,
    1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3, 3.1, 3.2,
    3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8,
    4.9, 5, 5.2, 5.4, 5.6, 5.8, 6, 6.2, 6.4, 6.6, 6.8, 7, 7.2, 7.4, 7.6, 7.8,
    8, 8.5, 9, 9.5,
    10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
    20, 23.4, 26.6, 30, 33.4, 36.6,
    40, 45, 50, 55,
    60, 70, 80, 90,
    100, 120, 140, 160, 180,
    200, 250, 300
]


def _dg_period_to_v3_freq(period_ms):
    if period_ms <= 100:
        return max(10, min(240, int(round(period_ms))))
    elif period_ms <= 600:
        return max(10, min(240, int(round((period_ms - 100) / 5 + 100))))
    else:
        return max(10, min(240, int(round((period_ms - 600) / 10 + 200))))


def _v3_freq_to_period(v3_freq):
    if v3_freq <= 100:
        return float(v3_freq)
    elif v3_freq <= 200:
        return (v3_freq - 100) * 5 + 100
    else:
        return (v3_freq - 200) * 10 + 600


_OCR_TARGETS = {
    "health_bar": "血量",
    "shield_bar": "盾量",
}

_OCR_DEFAULT_OVERRIDES = {
    "ocr.language": "models/config_en.txt",
    "ocr.maxSideLen": 999999,
    "tbpu.parser": "none",
    "data.format": "text",
}


class OcrAdvancedDialog(QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("OCR进阶配置")
        self.setMinimumSize(600, 550)
        self._config = config
        self._current_target = None
        self._option_widgets = {}
        self._options_raw = {}
        self._memory_cache = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        target_layout = QHBoxLayout()
        target_label = QLabel("OCR目标:")
        self.target_combo = QComboBox()
        for key, name in _OCR_TARGETS.items():
            self.target_combo.addItem(name, key)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.target_combo)
        target_layout.addStretch()
        layout.addLayout(target_layout)

        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP:")
        ip_label.setFixedWidth(30)
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("例如: 127.0.0.1 (留空则使用默认本地接口)")
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_edit, stretch=1)
        layout.addLayout(ip_layout)

        port_info_layout = QHBoxLayout()
        port_info_label = QLabel("端口: 使用OCR端口配置中的端口")
        port_info_label.setStyleSheet("color: gray; font-size: 11px;")
        port_info_layout.addWidget(port_info_label)
        port_info_layout.addStretch()
        layout.addLayout(port_info_layout)

        fetch_layout = QHBoxLayout()
        self.fetch_btn = QPushButton("获取配置项")
        self.fetch_btn.clicked.connect(self._fetch_options)
        self.fetch_status = QLabel("")
        self.fetch_status.setStyleSheet("color: gray; font-size: 11px;")
        fetch_layout.addWidget(self.fetch_btn)
        fetch_layout.addWidget(self.fetch_status)
        fetch_layout.addStretch()
        layout.addLayout(fetch_layout)

        self.options_scroll = QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_container = QWidget()
        self.options_form_layout = QVBoxLayout(self.options_container)
        self.options_form_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.options_scroll.setWidget(self.options_container)
        layout.addWidget(self.options_scroll, stretch=1)

        hint_label = QLabel("提示: 留空IP则使用默认Umi-OCR本地接口; 点击\"获取配置项\"从服务端加载可配置选项")
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("完成")
        ok_btn.clicked.connect(self._save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self._load_memory_cache()
        self.target_combo.setCurrentIndex(0)
        self._current_target = self.target_combo.currentData()
        self._load_target(self._current_target)
        QTimer.singleShot(100, self._auto_fetch_options)

    def _load_memory_cache(self):
        for target_key in _OCR_TARGETS:
            if self._config:
                plugins = self._config.get("plugins", self._config)
                bar_config = plugins.get(target_key, {})
            else:
                bar_config = {}
            ip = bar_config.get("ocr_api_ip", "")
            raw = bar_config.get("ocr_api_data", "")
            saved_dict = {}
            if raw:
                try:
                    saved_dict = json.loads(raw) if isinstance(raw, str) else raw
                    if not isinstance(saved_dict, dict):
                        saved_dict = {}
                except (json.JSONDecodeError, TypeError):
                    saved_dict = {}
            self._memory_cache[target_key] = {
                "ip": ip,
                "data": saved_dict,
            }

    def _get_port(self):
        if not self._config:
            return 1395
        plugins = self._config.get("plugins", self._config)
        ocr_config = plugins.get("ocr", {})
        return ocr_config.get("port", 1395)

    def _get_ip(self):
        return self.ip_edit.text().strip()

    def _on_target_changed(self, index):
        self._flush_current_to_cache()
        target_key = self.target_combo.currentData()
        self._current_target = target_key
        self._load_target(target_key)
        self._auto_fetch_options()

    def _flush_current_to_cache(self):
        if self._current_target is None:
            return
        cache = self._memory_cache.setdefault(self._current_target, {"ip": "", "data": {}})
        cache["ip"] = self.ip_edit.text().strip()
        if self._option_widgets:
            cache["data"] = self._collect_options()

    def _load_target(self, target_key):
        cache = self._memory_cache.get(target_key, {"ip": "", "data": {}})
        self.ip_edit.setText(cache.get("ip", ""))
        self._clear_options()
        saved_dict = cache.get("data", {})
        if saved_dict:
            self._rebuild_options_from_saved(saved_dict)

    def _rebuild_options_from_saved(self, saved_dict):
        for key, value in saved_dict.items():
            row_layout = QHBoxLayout()
            label = QLabel(key + ":")
            label.setFixedWidth(180)
            label.setToolTip(key)
            row_layout.addWidget(label)
            if isinstance(value, bool):
                widget = QCheckBox()
                widget.setChecked(value)
                widget._option_key = key
                widget._option_type = "boolean"
                row_layout.addWidget(widget)
                self._option_widgets[key] = widget
            elif isinstance(value, (int, float)):
                widget = QLineEdit(str(value))
                widget._option_key = key
                widget._option_type = "number"
                widget._is_int = isinstance(value, int)
                row_layout.addWidget(widget, stretch=1)
                self._option_widgets[key] = widget
            else:
                widget = QLineEdit(str(value))
                widget._option_key = key
                widget._option_type = "text"
                row_layout.addWidget(widget, stretch=1)
                self._option_widgets[key] = widget
            row_layout.addStretch()
            self.options_form_layout.addLayout(row_layout)

    def _clear_options(self):
        self._option_widgets.clear()
        self._options_raw.clear()
        while self.options_form_layout.count():
            item = self.options_form_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

    def _fetch_options(self):
        self._do_fetch_options(overwrite=True)

    def _auto_fetch_options(self):
        self._do_fetch_options(overwrite=False)

    def _do_fetch_options(self, overwrite=True):
        ip = self._get_ip()
        port = self._get_port()
        if not ip:
            ip = "127.0.0.1"
        url = f"http://{ip}:{port}/api/ocr/get_options"
        self.fetch_status.setText("正在获取...")
        self.fetch_status.setStyleSheet("color: orange; font-size: 11px;")
        QApplication.processEvents()
        try:
            import requests
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                res = r.json()
                options = res if "code" not in res else res.get("data", res)
                if isinstance(options, dict):
                    if not overwrite and self._option_widgets and self._has_conflict(options):
                        reply = QMessageBox.question(
                            self, "OCR进阶配置",
                            "由于OCR API改变或版本更新，API配置产生变动，是否覆盖配置？",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                        )
                        if reply == QMessageBox.StandardButton.No:
                            self.fetch_status.setText("保持原配置")
                            self.fetch_status.setStyleSheet("color: gray; font-size: 11px;")
                            return
                        else:
                            cache = self._memory_cache.get(self._current_target, {"ip": "", "data": {}})
                            cache["data"] = {}
                    self._clear_options()
                    self._build_dynamic_options(options, force_defaults=not overwrite)
                    self.fetch_status.setText(f"获取成功 ({len(options)} 项)")
                    self.fetch_status.setStyleSheet("color: #4CAF50; font-size: 11px;")
                else:
                    self.fetch_status.setText("返回格式异常")
                    self.fetch_status.setStyleSheet("color: #F44336; font-size: 11px;")
            else:
                self.fetch_status.setText(f"HTTP {r.status_code}")
                self.fetch_status.setStyleSheet("color: #F44336; font-size: 11px;")
        except Exception as e:
            self.fetch_status.setText(f"连接失败: {e}")
            self.fetch_status.setStyleSheet("color: #F44336; font-size: 11px;")

    def _has_conflict(self, new_options):
        if not self._options_raw:
            return False
        old_keys = set(self._options_raw.keys())
        new_keys = set(k for k, v in new_options.items() if isinstance(v, dict))
        old_api_keys = old_keys & new_keys
        old_override_keys = old_keys - new_keys
        override_unexpected = [k for k in old_override_keys if k not in _OCR_DEFAULT_OVERRIDES]
        if override_unexpected:
            return True
        for key in old_api_keys:
            old_opt = self._options_raw.get(key, {})
            new_opt = new_options.get(key, {})
            if not isinstance(old_opt, dict) or not isinstance(new_opt, dict):
                continue
            if old_opt.get("type") != new_opt.get("type"):
                return True
            if old_opt.get("type") == "enum":
                old_items = str(old_opt.get("optionsList", []))
                new_items = str(new_opt.get("optionsList", []))
                if old_items != new_items:
                    return True
        return False

    def _build_dynamic_options(self, options, force_defaults=False):
        cache = self._memory_cache.get(self._current_target, {"ip": "", "data": {}})
        saved_data = cache.get("data", {})
        if force_defaults:
            saved_data = {}

        for key, opt in options.items():
            if not isinstance(opt, dict):
                continue
            self._options_raw[key] = opt
            opt_type = opt.get("type", "text")
            title = opt.get("title", key)
            tooltip = opt.get("toolTip", "")
            default_val = opt.get("default")

            if key in saved_data:
                current_val = saved_data[key]
            elif key in _OCR_DEFAULT_OVERRIDES:
                current_val = _OCR_DEFAULT_OVERRIDES[key]
                if key == "ocr.language" and opt_type == "enum":
                    options_list = opt.get("optionsList", [])
                    available_vals = set()
                    for item in options_list:
                        available_vals.add(item[0] if isinstance(item, list) and len(item) >= 2 else item)
                    if current_val not in available_vals:
                        for candidate in ["English", "models/config_en.txt"]:
                            if candidate in available_vals:
                                current_val = candidate
                                break
            else:
                current_val = default_val

            row_layout = QHBoxLayout()
            label = QLabel(title + ":")
            label.setFixedWidth(180)
            if tooltip:
                label.setToolTip(tooltip)
            row_layout.addWidget(label)

            if opt_type == "enum":
                widget = QComboBox()
                options_list = opt.get("optionsList", [])
                sel_idx = 0
                for i, item in enumerate(options_list):
                    val = item[0] if isinstance(item, list) and len(item) >= 2 else item
                    disp = item[1] if isinstance(item, list) and len(item) >= 2 else str(item)
                    widget.addItem(disp, val)
                    if val == current_val:
                        sel_idx = i
                widget.setCurrentIndex(sel_idx)
                widget._option_key = key
                widget._option_type = "enum"
                if tooltip:
                    widget.setToolTip(tooltip)
                row_layout.addWidget(widget, stretch=1)
                self._option_widgets[key] = widget
            elif opt_type == "boolean":
                widget = QCheckBox()
                widget.setChecked(bool(current_val))
                widget._option_key = key
                widget._option_type = "boolean"
                if tooltip:
                    widget.setToolTip(tooltip)
                row_layout.addWidget(widget)
                self._option_widgets[key] = widget
            elif opt_type == "number":
                widget = QLineEdit(str(current_val) if current_val is not None else "")
                widget._option_key = key
                widget._option_type = "number"
                widget._is_int = opt.get("isInt", False)
                if tooltip:
                    widget.setToolTip(tooltip)
                row_layout.addWidget(widget, stretch=1)
                self._option_widgets[key] = widget
            else:
                widget = QLineEdit(str(current_val) if current_val is not None else "")
                widget._option_key = key
                widget._option_type = "text"
                if tooltip:
                    widget.setToolTip(tooltip)
                row_layout.addWidget(widget, stretch=1)
                self._option_widgets[key] = widget

            row_layout.addStretch()
            self.options_form_layout.addLayout(row_layout)

    def _collect_options(self):
        result = {}
        for key, widget in self._option_widgets.items():
            opt_type = widget._option_type
            if opt_type == "enum":
                result[key] = widget.currentData()
            elif opt_type == "boolean":
                result[key] = widget.isChecked()
            elif opt_type == "number":
                text = widget.text().strip()
                if text:
                    try:
                        if getattr(widget, '_is_int', False):
                            result[key] = int(text)
                        else:
                            result[key] = float(text)
                    except ValueError:
                        result[key] = text
            else:
                result[key] = widget.text().strip()
        skip_keys = {"tbpu.ignoreArea"}
        cleaned = {}
        for k, v in result.items():
            if k in skip_keys:
                if v is None or v == "" or v == "[]" or v == []:
                    continue
            cleaned[k] = v
        return cleaned

    def _save_and_close(self):
        self._flush_current_to_cache()
        if self._config:
            plugins = self._config.get("plugins", self._config)
            for target_key, cache in self._memory_cache.items():
                if "plugins" in self._config:
                    bar_config = plugins.get(target_key, {})
                else:
                    bar_config = self._config.get(target_key, {})
                bar_config["ocr_api_ip"] = cache.get("ip", "")
                data_dict = cache.get("data", {})
                if data_dict:
                    bar_config["ocr_api_data"] = json.dumps(data_dict, ensure_ascii=False)
                else:
                    bar_config["ocr_api_data"] = ""
        self.accept()

    def get_config(self):
        return self._config


class ConfigTool(QMainWindow):
    _ocr_status_signal = pyqtSignal(bool)
    _game_status_signal = pyqtSignal(bool)

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
        self._fake_game_window = None
        self._active_capture_method = "gdi"
        self._visibility_deps = {}

        self._ocr_status_signal.connect(self._on_ocr_status_result)
        self._game_status_signal.connect(self._on_game_status_result)

        self.init_ui()
        self.load_config()
        self.setup_hotkeys()

    def init_ui(self):
        self.setWindowTitle("HitElectric 配置工具")
        self.setGeometry(100, 100, 630, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.config_layout = QVBoxLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=1)

        sampling_control_layout = QHBoxLayout()
        self.cancel_sampling_btn = QPushButton("取消采样 (ESC)")
        self.cancel_sampling_btn.clicked.connect(self.cancel_sampling)
        self.finish_sampling_btn = QPushButton("完成采样 (P)")
        self.finish_sampling_btn.clicked.connect(self.finish_sampling)
        sampling_control_layout.addWidget(self.cancel_sampling_btn)
        sampling_control_layout.addWidget(self.finish_sampling_btn)
        self.sampling_control_widget = QWidget()
        self.sampling_control_widget.setLayout(sampling_control_layout)
        self.sampling_control_widget.setVisible(False)
        main_layout.addWidget(self.sampling_control_widget)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_config)
        save_btn.setFixedWidth(50)
        reload_btn = QPushButton("重载")
        reload_btn.setToolTip("保存配置并通知主程序重载配置")
        reload_btn.clicked.connect(self.save_and_reload_config)
        reload_btn.setFixedWidth(50)
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self.import_preset_config)
        import_btn.setFixedWidth(50)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self.export_config)
        export_btn.setFixedWidth(50)
        screenshot_test_btn = QPushButton("截图测试")
        screenshot_test_btn.clicked.connect(self.screenshot_test)
        screenshot_test_btn.setFixedWidth(70)
        ocr_filter_btn = QPushButton("滤镜测试")
        ocr_filter_btn.clicked.connect(self.ocr_filter_preview)
        ocr_filter_btn.setFixedWidth(70)
        ocr_once_btn = QPushButton("OCR测试")
        ocr_once_btn.clicked.connect(self.ocr_once)
        ocr_once_btn.setFixedWidth(75)
        import_screenshot_btn = QPushButton("导入截图")
        import_screenshot_btn.clicked.connect(self.import_game_screenshot)
        import_screenshot_btn.setFixedWidth(75)
        full_screenshot_btn = QPushButton("截图游戏")
        full_screenshot_btn.clicked.connect(self.full_screenshot)
        full_screenshot_btn.setFixedWidth(70)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(reload_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(screenshot_test_btn)
        button_layout.addWidget(ocr_filter_btn)
        button_layout.addWidget(ocr_once_btn)
        button_layout.addWidget(import_screenshot_btn)
        button_layout.addWidget(full_screenshot_btn)
        self._top_btn = QPushButton("📌")
        self._top_btn.setCheckable(True)
        self._top_btn.setFixedWidth(40)
        self._top_btn.toggled.connect(lambda checked: self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked) or self.show())
        button_layout.addStretch()
        button_layout.addWidget(self._top_btn)
        main_layout.addLayout(button_layout)

        status_layout = QHBoxLayout()
        self.status_label = QLabel("状态: 就绪")
        status_layout.addWidget(self.status_label)
        main_layout.addLayout(status_layout)

    def create_config_group(self, title, config_key, enable_path=None, enable_label=None):
        group = QGroupBox()
        layout = QGridLayout(group)

        header_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(title_label)

        enable_checkbox = None
        if enable_path:
            if enable_label is None:
                enable_label = "启用"
            enable_checkbox = QCheckBox(enable_label)
            enable_checkbox.field_config_path = enable_path
            enable_checkbox.field_type = "boolean"
            value = self.get_config_value(enable_path)
            if value is not None:
                enable_checkbox.setChecked(bool(value))
            enable_checkbox.stateChanged.connect(lambda state, cb=enable_checkbox, g=group: self.on_group_enable_changed(cb, state, g))
            header_layout.addWidget(enable_checkbox)
            header_layout.addStretch()

        layout.addLayout(header_layout, 0, 0, 1, 5)

        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_widget, 1, 0, 1, 5)

        if enable_checkbox and not enable_checkbox.isChecked():
            content_widget.setVisible(False)

        content_widget._enable_checkbox = enable_checkbox

        return group, content_layout, config_key, content_widget

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
                         is_position=False, is_color=False, is_boolean=False, group_key=None, ocr_related=False,
                         max_width=None, paired=False, dropdown_options=None,
                         visible_when=None, depends_on=None):
        row_widget = QWidget()
        row_widget.field_config_path = config_path
        row_widget.ocr_related = ocr_related
        h_layout = QHBoxLayout(row_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4)

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
            if not paired:
                h_layout.addStretch()
            layout.addWidget(row_widget, row, 0, 1, 5)
            row_widget.checkbox = checkbox
            self._register_visibility(row_widget, visible_when, depends_on)
            return row_widget

        if field_type == "dropdown" and dropdown_options:
            combo = QComboBox()
            combo.field_config_path = config_path
            combo.field_type = "dropdown"
            combo.group_key = group_key
            combo.ocr_related = ocr_related
            combo._dropdown_value_map = {}
            current_value = self.get_config_value(config_path)
            select_index = 0
            for i, opt in enumerate(dropdown_options):
                if isinstance(opt, (list, tuple)) and len(opt) >= 2:
                    display_text, opt_value = opt[0], opt[1]
                else:
                    display_text = opt_value = str(opt)
                combo.addItem(display_text, opt_value)
                combo._dropdown_value_map[display_text] = opt_value
                if current_value is not None and str(opt_value).lower() == str(current_value).lower():
                    select_index = i
            combo.setCurrentIndex(select_index)
            combo.currentIndexChanged.connect(lambda idx, cb=combo: self.on_dropdown_changed(cb, idx))
            h_layout.addWidget(combo)
            if not paired:
                h_layout.addStretch()
            layout.addWidget(row_widget, row, 0, 1, 5)
            row_widget.combo = combo
            self._register_visibility(row_widget, visible_when, depends_on)
            return row_widget

        if is_position or is_color:
            btn = QPushButton("采样")
            btn.setCheckable(True)
            btn.setFixedWidth(50)
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
        line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if is_position:
            line_edit.setPlaceholderText("x, y")
        elif is_color:
            line_edit.setPlaceholderText("#RRGGBB")

        if max_width:
            line_edit.setMaximumWidth(max_width)
        elif field_type == "number":
            line_edit.setMaximumWidth(50)

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

        if not paired:
            if field_type == "number":
                h_layout.addWidget(line_edit, stretch=0)
                h_layout.addStretch()
            else:
                h_layout.addWidget(line_edit, stretch=1)
            layout.addWidget(row_widget, row, 0, 1, 5)
        else:
            h_layout.addWidget(line_edit, stretch=0)

        row_widget.line_edit = line_edit
        if is_position or is_color:
            row_widget.btn = btn

        self._register_visibility(row_widget, visible_when, depends_on)
        return row_widget

    def create_paired_row(self, layout, row, fields):
        paired_widget = QWidget()
        paired_layout = QHBoxLayout(paired_widget)
        paired_layout.setContentsMargins(0, 0, 0, 0)
        paired_layout.setSpacing(16)
        for field_info in fields:
            w = self.create_field_row(layout, row, **field_info, paired=True)
            paired_layout.addWidget(w)
        paired_layout.addStretch()
        layout.addWidget(paired_widget, row, 0, 1, 5)
        return paired_widget

    def _register_visibility(self, widget, visible_when, depends_on):
        if visible_when is None:
            return
        widget.visible_when = visible_when
        if depends_on is None:
            depends_on = []
        elif isinstance(depends_on, str):
            depends_on = [depends_on]
        widget._vis_depends_on = depends_on
        for dep_path in depends_on:
            if dep_path not in self._visibility_deps:
                self._visibility_deps[dep_path] = []
            self._visibility_deps[dep_path].append(widget)

    def _refresh_visibility_for(self, config_path):
        for widget in self._visibility_deps.get(config_path, []):
            try:
                if hasattr(widget, 'visible_when') and callable(widget.visible_when):
                    result = widget.visible_when()
                    widget.setVisible(bool(result))
            except RuntimeError:
                continue

    def _refresh_all_visibility(self):
        seen = set()
        for widgets in self._visibility_deps.values():
            for widget in widgets:
                wid = id(widget)
                if wid in seen:
                    continue
                seen.add(wid)
                try:
                    if hasattr(widget, 'visible_when') and callable(widget.visible_when):
                        result = widget.visible_when()
                        widget.setVisible(bool(result))
                except RuntimeError:
                    continue

    def on_group_enable_changed(self, checkbox, state, group):
        path = checkbox.field_config_path
        checked = state == Qt.CheckState.Checked.value
        self.set_config_value(path, checked)
        content_widget = group.layout().itemAtPosition(1, 0).widget()
        if content_widget:
            content_widget.setVisible(checked)

    def on_checkbox_changed(self, checkbox, state):
        path = checkbox.field_config_path
        checked = state == Qt.CheckState.Checked.value
        self.set_config_value(path, checked)
        self._refresh_visibility_for(path)

    def on_dropdown_changed(self, combo, index):
        path = combo.field_config_path
        value = combo.itemData(index)
        if value is not None:
            self.set_config_value(path, value)
        self._refresh_visibility_for(path)
        if path == "capture_method":
            self._update_capture_method(value)

    def _update_capture_method(self, method_value):
        if method_value == "dxgi":
            if not lib.is_dxgi_available():
                self.status_label.setText("状态: DXGI 不可用 (dxcam 未安装)，已回退到 GDI")
                self._active_capture_method = "gdi"
                if hasattr(self, 'capture_method_combo'):
                    for i in range(self.capture_method_combo.count()):
                        if self.capture_method_combo.itemData(i) == "gdi":
                            self.capture_method_combo.setCurrentIndex(i)
                            break
            else:
                self._active_capture_method = "dxgi"
                self.status_label.setText("状态: 截图方式已切换为 DXGI")
        elif method_value == "gdi":
            self._active_capture_method = "gdi"
            self.status_label.setText("状态: 截图方式已切换为 GDI")
        else:
            self._active_capture_method = "gdi"
            self.status_label.setText("状态: 截图方式已切换为 GDI")
        self._release_capture_resources()
        self._update_dxgi_status()

    def _update_dxgi_status(self):
        if hasattr(self, '_dxgi_status_label'):
            cfg = self.get_config_value("capture_method") or "gdi"
            dxgi_ok = lib.is_dxgi_available()
            if cfg == "gdi":
                self._dxgi_status_label.setText("● GDI")
                self._dxgi_status_label.setStyleSheet("color: #888; font-size: 11px;")
            elif cfg == "dxgi" and dxgi_ok:
                self._dxgi_status_label.setText("● DXGI")
                self._dxgi_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                self._dxgi_status_label.setText("● DXGI不可用 已回退GDI")
                self._dxgi_status_label.setStyleSheet("color: #FF9800; font-size: 11px;")

    def _release_capture_resources(self):
        if self._active_capture_method == "dxgi":
            try:
                lib.release_dxgi()
            except Exception:
                pass

    def _do_capture(self, region=None, hwnd=None):
        if self._active_capture_method == "dxgi":
            result = lib.capture_dxgi_fast(region, hwnd=hwnd)
            if result and result[0] is not None:
                return result
            result = lib.capture_screen_fast(region, hwnd=hwnd)
            return result
        return lib.capture_screen_fast(region, hwnd=hwnd)

    def on_ocr_toggled(self, state):
        """OCR启用/禁用时的显示/隐藏逻辑"""
        is_enabled = state == Qt.CheckState.Checked.value
        self.set_config_value("ocr.enabled", is_enabled)

        self._update_ocr_ui_visibility(is_enabled)

        if hasattr(self, '_ocr_test_timer'):
            if is_enabled:
                self._ocr_test_timer.start(500)
            else:
                self._ocr_test_timer.stop()
                if hasattr(self, 'ocr_status_label'):
                    self.ocr_status_label.setText("")
                    self.ocr_status_label.setStyleSheet("font-size: 11px;")

    def _save_config_to_file(self):
        config_path = os.path.join(_plugin_dir, 'config.json')
        try:
            def _clean_for_save(obj):
                if isinstance(obj, dict):
                    return {k: _clean_for_save(v) for k, v in obj.items() if not k.startswith('_')}
                elif isinstance(obj, list):
                    return [_clean_for_save(item) for item in obj]
                return obj
            save_data = {"config": _clean_for_save(self.config)}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ConfigTool] 保存配置失败: {e}")

    def _open_ocr_advanced_settings(self):
        dialog = OcrAdvancedDialog(self, config=self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.config = dialog.get_config()
            self._save_config_to_file()
            if hasattr(self, '_ocr_test_timer'):
                self._ocr_test_timer.start(500)

    def _update_ocr_ui_visibility(self, ocr_enabled):
        if not hasattr(self, 'group_widgets'):
            return

        plus_group = self.group_widgets.get('plus_group')
        if plus_group:
            plus_group.setVisible(not ocr_enabled)

        if hasattr(self, 'ocr_port_row'):
            self.ocr_port_row.setVisible(ocr_enabled)

        if hasattr(self, 'ocr_health_shield_detect_row'):
            self.ocr_health_shield_detect_row.setVisible(ocr_enabled)

        self._refresh_visibility_for('ocr.enabled')
    
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
        if keys[0] in ('plugins', 'waveform'):
            value = self.config
        else:
            value = self.config.get('plugins', {})
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def set_config_value(self, path, value):
        keys = path.split('.')
        if keys[0] in ('plugins', 'waveform'):
            config = self.config
        else:
            config = self.config.setdefault('plugins', {})
        for key in keys[:-1]:
            config = config.setdefault(key, {})
        config[keys[-1]] = value

    def on_field_changed(self, line_edit, text):
        path = line_edit.field_config_path
        field_type = getattr(line_edit, 'field_type', 'text')

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

        if path == "ocr.port" and hasattr(self, '_ocr_test_timer'):
            self._ocr_test_timer.start(500)
        elif path == "game.process_title" and hasattr(self, '_game_test_timer'):
            self._game_test_timer.start(500)

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

        from config import _migrate_legacy_filters, _ensure_defaults
        self.config = _migrate_legacy_filters(self.config)
        self.config = _ensure_defaults(self.config)

        self.build_config_ui()

        capture_method_config = self.get_config_value("capture_method") or "gdi"
        if capture_method_config == "dxgi":
            if lib.is_dxgi_available():
                self._active_capture_method = "dxgi"
            else:
                self._active_capture_method = "gdi"
        else:
            self._active_capture_method = "gdi"

        self._update_dxgi_status()

    def build_config_ui(self):
        while self.config_layout.count():
            item = self.config_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._visibility_deps.clear()

        from config import _migrate_legacy_filters
        self.config = _migrate_legacy_filters(self.config)

        cfg_from = self.config.get('cfgFrom', '')
        if cfg_from:
            self.setWindowTitle(f"HitElectric 配置工具 - {os.path.basename(cfg_from)}")
        else:
            self.setWindowTitle("HitElectric 配置工具")

        self.group_widgets = {}

        game_group, game_layout, _, _ = self.create_config_group("游戏配置", "game")
        self.game_status_label = QLabel("")
        self.game_status_label.setStyleSheet("font-size: 11px;")
        game_header_layout = game_group.layout().itemAtPosition(0, 0)
        if game_header_layout:
            game_header_layout.addWidget(self.game_status_label)
            game_header_layout.addStretch()
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

        # OCR端口配置（OCR专属）+ 进阶配置按钮
        self.ocr_port_row = self.create_field_row(game_layout, row, "OCR端口:", "ocr.port",
                                                   field_type="number", ocr_related=True)
        self.ocr_status_label = QLabel("")
        self.ocr_status_label.setStyleSheet("font-size: 11px;")
        self.ocr_status_label.ocr_related = True
        ocr_adv_btn = QPushButton("OCR进阶配置")
        ocr_adv_btn.setFixedWidth(120)
        ocr_adv_btn.clicked.connect(self._open_ocr_advanced_settings)
        ocr_adv_btn.ocr_related = True
        ocr_port_layout = self.ocr_port_row.layout()
        stretch_idx = -1
        for i in range(ocr_port_layout.count()):
            item = ocr_port_layout.itemAt(i)
            if item and item.spacerItem():
                stretch_idx = i
                break
        if stretch_idx >= 0:
            ocr_port_layout.takeAt(stretch_idx)
        ocr_port_layout.addWidget(self.ocr_status_label)
        ocr_port_layout.addWidget(ocr_adv_btn)
        ocr_port_layout.addStretch()
        row += 1

        self.ocr_health_shield_detect_row = self.create_field_row(game_layout, row, "OCR-盾量血量同时检测血条存在:", "ocr.health_shield_detect",
                                                                    field_type="boolean", is_boolean=True, ocr_related=True)
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

        toggle_row = QWidget()
        toggle_h = QHBoxLayout(toggle_row)
        toggle_h.setContentsMargins(0, 0, 0, 0)
        toggle_h.setSpacing(4)
        toggle_h.addWidget(QLabel("开关键:"))
        toggle_key_edit = QLineEdit(str(self.get_config_value("toggle_key") or "f9"))
        toggle_key_edit.setMaximumWidth(120)
        toggle_key_edit.setPlaceholderText("按键名 / 按键码(如0x72)")
        toggle_key_edit.field_config_path = "toggle_key"
        toggle_key_edit.textChanged.connect(lambda t, e=toggle_key_edit: self.on_field_changed(e, t))
        toggle_h.addWidget(toggle_key_edit)
        toggle_sample_btn = QPushButton("采样")
        toggle_sample_btn.setMaximumWidth(50)
        toggle_sample_btn.clicked.connect(lambda _, e=toggle_key_edit: self._sample_key(e))
        toggle_h.addWidget(toggle_sample_btn)
        toggle_h.addStretch()
        game_layout.addWidget(toggle_row, row, 0, 1, 5)
        row += 1

        setting_row = QWidget()
        setting_h = QHBoxLayout(setting_row)
        setting_h.setContentsMargins(0, 0, 0, 0)
        setting_h.setSpacing(4)
        setting_h.addWidget(QLabel("设置模式键:"))
        setting_key_edit = QLineEdit(str(self.get_config_value("setting_mode_key") or "f10"))
        setting_key_edit.setMaximumWidth(120)
        setting_key_edit.setPlaceholderText("按键名 / 按键码(如0x7B)")
        setting_key_edit.field_config_path = "setting_mode_key"
        setting_key_edit.textChanged.connect(lambda t, e=setting_key_edit: self.on_field_changed(e, t))
        setting_h.addWidget(setting_key_edit)
        setting_sample_btn = QPushButton("采样")
        setting_sample_btn.setMaximumWidth(50)
        setting_sample_btn.clicked.connect(lambda _, e=setting_key_edit: self._sample_key(e))
        setting_h.addWidget(setting_sample_btn)
        setting_h.addStretch()
        game_layout.addWidget(setting_row, row, 0, 1, 5)
        row += 1
        capture_method_row = QWidget()
        capture_method_h = QHBoxLayout(capture_method_row)
        capture_method_h.setContentsMargins(0, 0, 0, 0)
        capture_method_h.setSpacing(4)
        capture_method_label = QLabel("截图方式:")
        capture_method_h.addWidget(capture_method_label)
        current_method = self.get_config_value("capture_method") or "gdi"
        capture_method_combo = QComboBox()
        capture_method_combo.field_config_path = "capture_method"
        for opt in [("GDI+BitBlt", "gdi"), ("DXGI", "dxgi")]:
            capture_method_combo.addItem(opt[0], opt[1])
        for i in range(capture_method_combo.count()):
            if capture_method_combo.itemData(i) == current_method:
                capture_method_combo.setCurrentIndex(i)
                break
        capture_method_combo.currentIndexChanged.connect(lambda idx: self.on_dropdown_changed(capture_method_combo, idx))
        capture_method_h.addWidget(capture_method_combo)
        self.capture_method_combo = capture_method_combo
        self._dxgi_status_label = QLabel()
        self._dxgi_status_label.setStyleSheet("font-size: 11px;")
        capture_method_h.addWidget(self._dxgi_status_label)
        capture_method_h.addStretch()
        game_layout.addWidget(capture_method_row, row, 0, 1, 5)
        self._update_dxgi_status()
        row += 1

        self.config_layout.addWidget(game_group)

        plus_group, plus_layout, _, _ = self.create_config_group("+号检测配置", "plus_sign", enable_path="plus_sign.enabled")
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

        spectate_group, spectate_layout, _, _ = self.create_config_group("观战检测配置", "spectate", enable_path="spectate.enabled")
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

        health_group, health_layout, _, _ = self.create_config_group("血条配置", "health_bar", enable_path="health_bar.enabled")
        self.group_widgets['health_group'] = health_group
        self.health_bar_widgets = {}
        row = 0
        self.health_bar_widgets['ocr_top_left'] = self.create_field_row(health_layout, row, "OCR-数字左上角:", "health_bar.ocr_top_left",
                                                                        field_type="coordinate", is_position=True, group_key="health_bar", ocr_related=True,
                                                                        visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                        depends_on='ocr.enabled')
        row += 1
        self.health_bar_widgets['ocr_bottom_right'] = self.create_field_row(health_layout, row, "OCR-数字右下角:", "health_bar.ocr_bottom_right",
                                                                            field_type="coordinate", is_position=True, group_key="health_bar", ocr_related=True,
                                                                            visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                            depends_on='ocr.enabled')
        row += 1

        filter_row_widget = QWidget()
        filter_row_layout = QHBoxLayout(filter_row_widget)
        filter_row_layout.setContentsMargins(0, 0, 0, 0)
        filter_label = QLabel("自定义滤镜:")
        filter_label.ocr_related = True
        filter_row_layout.addWidget(filter_label)
        self.health_filter_btn = QPushButton("编辑滤镜")
        self.health_filter_btn.setFixedWidth(80)
        self.health_filter_btn.ocr_related = True
        self.health_filter_btn.config_key = "health_bar"
        self.health_filter_btn.clicked.connect(lambda: self.open_filter_editor("health_bar"))
        filter_row_layout.addWidget(self.health_filter_btn)
        self.health_filter_summary = QLabel("")
        self.health_filter_summary.setStyleSheet("color: #aaa; font-size: 11px;")
        self.health_filter_summary.ocr_related = True
        filter_row_layout.addWidget(self.health_filter_summary, stretch=1)
        health_layout.addWidget(filter_row_widget, row, 0, 1, 5)
        self.health_bar_widgets['ocr_filters'] = filter_row_widget
        self._register_visibility(filter_row_widget,
                                  visible_when=lambda: self.get_config_value('ocr.enabled'),
                                  depends_on='ocr.enabled')
        row += 1

        self.health_bar_widgets['ocr_end_trigger'] = self.create_field_row(health_layout, row, "血条框填满 但 血量数值下降 时不触发电击:", "health_bar.ocr_end_trigger",
                                                                            field_type="boolean", is_boolean=True,
                                                                            visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                            depends_on='ocr.enabled')
        row += 1
        self.health_bar_widgets['start'] = self.create_field_row(health_layout, row, "起始位置:", "health_bar.start",
                                                                  field_type="coordinate", is_position=True, group_key="health_bar",
                                                                  visible_when=lambda: not self.get_config_value('ocr.enabled'),
                                                                  depends_on='ocr.enabled')
        row += 1
        self.health_bar_widgets['end'] = self.create_field_row(health_layout, row, "结束位置:", "health_bar.end",
                                                                field_type="coordinate", is_position=True, group_key="health_bar",
                                                                visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('health_bar.ocr_end_trigger'),
                                                                depends_on=['ocr.enabled', 'health_bar.ocr_end_trigger'])
        row += 1
        self.health_bar_widgets['colors'] = self.create_field_row(health_layout, row, "血条颜色:", "health_bar.colors",
                                                                   field_type="colors", is_color=True, group_key="health_bar",
                                                                   visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('health_bar.ocr_end_trigger'),
                                                                   depends_on=['ocr.enabled', 'health_bar.ocr_end_trigger'])
        row += 1
        self.health_bar_widgets['tolerance'] = self.create_field_row(health_layout, row, "容差:", "health_bar.tolerance",
                                                                     field_type="number",
                                                                     visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('health_bar.ocr_end_trigger'),
                                                                     depends_on=['ocr.enabled', 'health_bar.ocr_end_trigger'])
        row += 1
        self.health_bar_widgets['sample_points'] = self.create_field_row(health_layout, row, "采样点数:", "health_bar.sample_points",
                                                                         field_type="number",
                                                                         visible_when=lambda: not self.get_config_value('ocr.enabled'),
                                                                         depends_on='ocr.enabled')
        row += 1
        self.health_bar_widgets['strength'] = self.create_field_row(health_layout, row, "强度A:", "health_bar.strength",
                                                                     field_type="number")
        row += 1
        self.health_bar_widgets['strength_b'] = self.create_field_row(health_layout, row, "强度B:", "health_bar.strength_b",
                                                                       field_type="number")
        row += 1
        self.health_bar_widgets['drop_threshold'] = self.create_field_row(health_layout, row, "血量减少阈值(0=禁用):", "health_bar.drop_threshold",
                                                                           field_type="number")
        row += 1
        self.config_layout.addWidget(health_group)

        shield_group, shield_layout, _, _ = self.create_config_group("盾条配置", "shield_bar", enable_path="shield_bar.enabled")
        self.group_widgets['shield_group'] = shield_group
        self.shield_bar_widgets = {}
        row = 0
        self.shield_bar_widgets['ocr_top_left'] = self.create_field_row(shield_layout, row, "OCR-数字左上角:", "shield_bar.ocr_top_left",
                                                                        field_type="coordinate", is_position=True, group_key="shield_bar", ocr_related=True,
                                                                        visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                        depends_on='ocr.enabled')
        row += 1
        self.shield_bar_widgets['ocr_bottom_right'] = self.create_field_row(shield_layout, row, "OCR-数字右下角:", "shield_bar.ocr_bottom_right",
                                                                            field_type="coordinate", is_position=True, group_key="shield_bar", ocr_related=True,
                                                                            visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                            depends_on='ocr.enabled')
        row += 1

        shield_filter_row = QWidget()
        shield_filter_layout = QHBoxLayout(shield_filter_row)
        shield_filter_layout.setContentsMargins(0, 0, 0, 0)
        shield_filter_label = QLabel("自定义滤镜:")
        shield_filter_label.ocr_related = True
        shield_filter_layout.addWidget(shield_filter_label)
        self.shield_filter_btn = QPushButton("编辑滤镜")
        self.shield_filter_btn.setFixedWidth(80)
        self.shield_filter_btn.ocr_related = True
        self.shield_filter_btn.config_key = "shield_bar"
        self.shield_filter_btn.clicked.connect(lambda: self.open_filter_editor("shield_bar"))
        shield_filter_layout.addWidget(self.shield_filter_btn)
        self.shield_filter_summary = QLabel("")
        self.shield_filter_summary.setStyleSheet("color: #aaa; font-size: 11px;")
        self.shield_filter_summary.ocr_related = True
        shield_filter_layout.addWidget(self.shield_filter_summary, stretch=1)
        shield_layout.addWidget(shield_filter_row, row, 0, 1, 5)
        self.shield_bar_widgets['ocr_filters'] = shield_filter_row
        self._register_visibility(shield_filter_row,
                                  visible_when=lambda: self.get_config_value('ocr.enabled'),
                                  depends_on='ocr.enabled')
        row += 1

        self.shield_bar_widgets['ocr_end_trigger'] = self.create_field_row(shield_layout, row, "盾条框填满 但 盾量数值下降 时不触发电击:", "shield_bar.ocr_end_trigger",
                                                                            field_type="boolean", is_boolean=True,
                                                                            visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                            depends_on='ocr.enabled')
        row += 1
        self.shield_bar_widgets['start'] = self.create_field_row(shield_layout, row, "起始位置:", "shield_bar.start",
                                                                  field_type="coordinate", is_position=True, group_key="shield_bar",
                                                                  visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('shield_bar.blocks_health'),
                                                                  depends_on=['ocr.enabled', 'shield_bar.blocks_health'])
        row += 1
        self.shield_bar_widgets['end'] = self.create_field_row(shield_layout, row, "结束位置:", "shield_bar.end",
                                                                field_type="coordinate", is_position=True, group_key="shield_bar",
                                                                visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('shield_bar.ocr_end_trigger'),
                                                                depends_on=['ocr.enabled', 'shield_bar.ocr_end_trigger'])
        row += 1
        self.shield_bar_widgets['colors'] = self.create_field_row(shield_layout, row, "盾条颜色:", "shield_bar.colors",
                                                                   field_type="colors", is_color=True, group_key="shield_bar",
                                                                   visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('shield_bar.ocr_end_trigger') or self.get_config_value('shield_bar.blocks_health'),
                                                                   depends_on=['ocr.enabled', 'shield_bar.ocr_end_trigger', 'shield_bar.blocks_health'])
        row += 1
        self.shield_bar_widgets['tolerance'] = self.create_field_row(shield_layout, row, "容差:", "shield_bar.tolerance",
                                                                     field_type="number",
                                                                     visible_when=lambda: not self.get_config_value('ocr.enabled') or self.get_config_value('shield_bar.ocr_end_trigger') or self.get_config_value('shield_bar.blocks_health'),
                                                                     depends_on=['ocr.enabled', 'shield_bar.ocr_end_trigger', 'shield_bar.blocks_health'])
        row += 1
        self.shield_bar_widgets['sample_points'] = self.create_field_row(shield_layout, row, "采样点数:", "shield_bar.sample_points",
                                                                         field_type="number",
                                                                         visible_when=lambda: not self.get_config_value('ocr.enabled'),
                                                                         depends_on='ocr.enabled')
        row += 1
        self.shield_bar_widgets['strength'] = self.create_field_row(shield_layout, row, "强度A:", "shield_bar.strength",
                                                                     field_type="number")
        row += 1
        self.shield_bar_widgets['strength_b'] = self.create_field_row(shield_layout, row, "强度B:", "shield_bar.strength_b",
                                                                       field_type="number")
        row += 1
        self.shield_bar_widgets['blocks_health'] = self.create_field_row(shield_layout, row, "盾存在时阻止扣血:", "shield_bar.blocks_health",
                                                                          field_type="boolean", is_boolean=True,
                                                                          visible_when=lambda: self.get_config_value('ocr.enabled'),
                                                                          depends_on='ocr.enabled')
        row += 1
        self.shield_bar_widgets['drop_threshold'] = self.create_field_row(shield_layout, row, "盾量减少阈值(0=禁用):", "shield_bar.drop_threshold",
                                                                           field_type="number")
        row += 1
        self.config_layout.addWidget(shield_group)

        overlap_group, overlap_layout, _, _ = self.create_config_group("重叠电击配置", "overlap", enable_path="overlap.enabled")
        row = 0
        self.create_field_row(overlap_layout, row, "强度增加:", "overlap.strength_add",
                              field_type="number")
        row += 1
        self.create_field_row(overlap_layout, row, "最大强度:", "overlap.strength_max",
                              field_type="number")
        row += 1
        self.create_field_row(overlap_layout, row, "时间叠加倍数:", "overlap.duration_multiplier",
                              field_type="number")
        row += 1
        self.create_field_row(overlap_layout, row, "自然回落:", "overlap.decay_enabled",
                              is_boolean=True)
        row += 1
        decay_mode_row = self.create_field_row(overlap_layout, row, "回落方式:", "overlap.decay_mode",
                              field_type="dropdown",
                              dropdown_options=[
                                  ("瞬间重置", "instant"),
                                  ("缓慢降低(数值)", "linear"),
                                  ("缓慢降低(百分比)", "percent"),
                                  ("比值加速", "ratio_accel"),
                                  ("自定义脚本", "script"),
                              ],
                              visible_when=lambda: self.get_config_value('overlap.decay_enabled'),
                              depends_on='overlap.decay_enabled')
        row += 1
        decay_value_row = self.create_field_row(overlap_layout, row, "每次降低数值:", "overlap.decay_value",
                              field_type="number",
                              visible_when=lambda: self.get_config_value('overlap.decay_enabled') and self.get_config_value('overlap.decay_mode') == 'linear',
                              depends_on=['overlap.decay_enabled', 'overlap.decay_mode'])
        row += 1
        decay_percent_row = self.create_field_row(overlap_layout, row, "每次降低百分比:", "overlap.decay_percent",
                              field_type="number",
                              visible_when=lambda: self.get_config_value('overlap.decay_enabled') and self.get_config_value('overlap.decay_mode') == 'percent',
                              depends_on=['overlap.decay_enabled', 'overlap.decay_mode'])
        row += 1
        decay_ratio_row = self.create_field_row(overlap_layout, row, "比值加速因子:", "overlap.decay_ratio_accel",
                              field_type="number",
                              visible_when=lambda: self.get_config_value('overlap.decay_enabled') and self.get_config_value('overlap.decay_mode') == 'ratio_accel',
                              depends_on=['overlap.decay_enabled', 'overlap.decay_mode'])
        row += 1

        decay_script_btn = QPushButton("修改回落脚本")
        decay_script_btn.clicked.connect(self._edit_decay_script)
        script_row = QWidget()
        script_h = QHBoxLayout(script_row)
        script_h.setContentsMargins(0, 0, 0, 0)
        script_label = QLabel("自定义回落脚本:")
        script_h.addWidget(script_label)
        script_h.addWidget(decay_script_btn)
        script_h.addStretch()
        overlap_layout.addWidget(script_row, row, 0, 1, 5)
        self._register_visibility(script_row,
                                  visible_when=lambda: self.get_config_value('overlap.decay_enabled') and self.get_config_value('overlap.decay_mode') == 'script',
                                  depends_on=['overlap.decay_enabled', 'overlap.decay_mode'])
        row += 1

        self.config_layout.addWidget(overlap_group)

        damage_group, damage_layout, _, _ = self.create_config_group("受伤程度检测", "damage_detect", enable_path="damage_detect.enabled")
        row = 0
        self.create_field_row(damage_layout, row, "血量中间数:", "damage_detect.mid_value",
                              field_type="number")
        row += 1
        self.create_field_row(damage_layout, row, "强度增幅上限:", "damage_detect.max_bonus",
                              field_type="number")
        row += 1
        self.create_field_row(damage_layout, row, "检测公式:", "damage_detect.formula",
                              field_type="dropdown",
                              dropdown_options=[
                                  ("默认公式", "default"),
                                  ("自定义Python代码", "script"),
                              ])
        row += 1
        damage_script_btn = QPushButton("修改检测脚本")
        damage_script_btn.clicked.connect(self._edit_damage_script)
        damage_script_row = QWidget()
        damage_script_h = QHBoxLayout(damage_script_row)
        damage_script_h.setContentsMargins(0, 0, 0, 0)
        damage_script_label = QLabel("自定义检测脚本:")
        damage_script_h.addWidget(damage_script_label)
        damage_script_h.addWidget(damage_script_btn)
        damage_script_h.addStretch()
        damage_layout.addWidget(damage_script_row, row, 0, 1, 5)
        self._register_visibility(damage_script_row,
                                  visible_when=lambda: self.get_config_value('damage_detect.enabled') and self.get_config_value('damage_detect.formula') == 'script',
                                  depends_on=['damage_detect.enabled', 'damage_detect.formula'])
        row += 1
        self.config_layout.addWidget(damage_group)

        multi_char_group, multi_char_layout, _, _ = self.create_config_group("多角色切换配置", "multi_character", enable_path="multi_character.enabled")
        row = 0
        self.create_field_row(multi_char_layout, row, "角色按键(逗号分隔):", "multi_character.character_keys",
                              field_type="text")
        row += 1
        self.create_field_row(multi_char_layout, row, "启用手柄支持:", "multi_character.gamepad_enabled",
                              field_type="boolean", is_boolean=True)
        row += 1
        self.create_field_row(multi_char_layout, row, "手柄按钮码(逗号分隔16进制):", "multi_character.gamepad_buttons",
                              field_type="text")
        row += 1
        self.create_field_row(multi_char_layout, row, "切换免疫帧数:", "multi_character.switch_immunity_frames",
                              field_type="number")
        row += 1
        self.create_field_row(multi_char_layout, row, "切换延迟帧数:", "multi_character.switch_delay_frames",
                              field_type="number")
        row += 1
        self.config_layout.addWidget(multi_char_group)

        waveform_group = QGroupBox("电击波形配置")
        waveform_layout = QVBoxLayout(waveform_group)

        class MiniWavePreview(QWidget):
            def __init__(self, pulse_data=None, parent=None):
                super().__init__(parent)
                self.setFixedHeight(30)
                self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self._steps = []
                if pulse_data and isinstance(pulse_data, list):
                    for line in pulse_data:
                        s = str(line).strip()
                        if len(s) >= 16:
                            try:
                                freq_val = int(s[:2], 16)
                                str_val = int(s[8:10], 16)
                                self._steps.append({"freq": freq_val, "strength": str_val})
                            except (ValueError, IndexError):
                                pass

            def update_data(self, pulse_data):
                self._steps.clear()
                if pulse_data and isinstance(pulse_data, list):
                    for line in pulse_data:
                        s = str(line).strip()
                        if len(s) >= 16:
                            try:
                                freq_val = int(s[:2], 16)
                                str_val = int(s[8:10], 16)
                                self._steps.append({"freq": freq_val, "strength": str_val})
                            except (ValueError, IndexError):
                                pass
                self.update()

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(20, 20, 25))
                w = self.width()
                h = self.height()
                if not self._steps:
                    painter.setPen(QPen(QColor(80, 80, 80)))
                    painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无波形")
                    painter.end()
                    return
                n = len(self._steps)
                total_w = w - 4
                step_w = total_w / n
                max_nl = 0
                line_counts = []
                for step in self._steps:
                    period_ms = _v3_freq_to_period(step["freq"])
                    nb = max(1, int(100.0 / period_ms))
                    nl = max(2, min(30, nb * 2))
                    line_counts.append(nl)
                    if nl > max_nl:
                        max_nl = nl
                global_gap = step_w / max_nl if max_nl > 0 else step_w
                lw = max(1, min(2, int(global_gap * 0.7)))
                for i, step in enumerate(self._steps):
                    nl = line_counts[i]
                    gap = step_w / nl
                    density_ratio = min(nl / 30.0, 1.0)
                    r = int(50 + 200 * density_ratio)
                    g = int(200 - 100 * density_ratio)
                    b = 80
                    painter.setPen(QPen(QColor(r, g, b, 200), lw))
                    line_h = (step["strength"] / 100.0) * (h - 4)
                    y_top = h - 2 - line_h
                    x_start = 2 + i * step_w
                    for j in range(nl):
                        lx = x_start + j * gap
                        painter.drawLine(int(lx), int(y_top), int(lx), h - 2)
                painter.end()

        wave_splitter = QSplitter(Qt.Orientation.Horizontal)

        health_wave_widget = QWidget()
        health_wave_layout = QVBoxLayout(health_wave_widget)
        health_wave_layout.setContentsMargins(0, 0, 0, 0)
        health_wave_label = QLabel("血量脉冲波形")
        health_wave_layout.addWidget(health_wave_label)
        health_pulse = self.get_config_value("waveform.health_pulse")
        self.health_wave_preview = MiniWavePreview(health_pulse)
        health_wave_layout.addWidget(self.health_wave_preview)
        self.health_wave_edit = QTextEdit()
        self.health_wave_edit.setMinimumHeight(260)
        if health_pulse and isinstance(health_pulse, list):
            self.health_wave_edit.setText("\n".join(str(s) for s in health_pulse))
        self.health_wave_edit.textChanged.connect(self._on_health_wave_changed)
        health_wave_layout.addWidget(self.health_wave_edit)
        health_wave_btn = QPushButton("编辑血量波形")
        health_wave_btn.clicked.connect(lambda: self._open_waveform_editor("health"))
        health_wave_layout.addWidget(health_wave_btn)
        wave_splitter.addWidget(health_wave_widget)

        shield_wave_widget = QWidget()
        shield_wave_layout = QVBoxLayout(shield_wave_widget)
        shield_wave_layout.setContentsMargins(0, 0, 0, 0)
        shield_wave_label = QLabel("盾量脉冲波形")
        shield_wave_layout.addWidget(shield_wave_label)
        shield_pulse = self.get_config_value("waveform.shield_pulse")
        self.shield_wave_preview = MiniWavePreview(shield_pulse)
        shield_wave_layout.addWidget(self.shield_wave_preview)
        self.shield_wave_edit = QTextEdit()
        self.shield_wave_edit.setMinimumHeight(260)
        if shield_pulse and isinstance(shield_pulse, list):
            self.shield_wave_edit.setText("\n".join(str(s) for s in shield_pulse))
        self.shield_wave_edit.textChanged.connect(self._on_shield_wave_changed)
        shield_wave_layout.addWidget(self.shield_wave_edit)
        shield_wave_btn = QPushButton("编辑盾量波形")
        shield_wave_btn.clicked.connect(lambda: self._open_waveform_editor("shield"))
        shield_wave_layout.addWidget(shield_wave_btn)
        wave_splitter.addWidget(shield_wave_widget)

        waveform_layout.addWidget(wave_splitter)

        self.config_layout.addWidget(waveform_group)

        ocr_enabled = self.get_config_value("ocr.enabled")
        if ocr_enabled is not None:
            self._update_ocr_ui_visibility(bool(ocr_enabled))

        self._refresh_all_visibility()

        self._update_dxgi_status()

        self.config_layout.addStretch()

        self._update_filter_summaries()
        self._start_status_timers()

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
                self.bmp_data, rx, ry, rw, rh, self.img_width = self._do_capture(hwnd=self.game_hwnd)
                self.capture_region = [rx, ry, rw, rh]
                self.status_label.setText(f"状态: 截图资源已准备就绪 ({rw}x{rh})")
            except Exception as e:
                self.status_label.setText(f"状态: 预热失败: {e}")

        self.cancel_sampling_btn.setEnabled(True)
        self.finish_sampling_btn.setEnabled(True)
        self.sampling_control_widget.setVisible(True)
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

        sample_result = lib.sample_color_at_cursor(hwnd=self.game_hwnd, capture_method=self._active_capture_method)
        pixel = sample_result['color']
        hex_color = sample_result['hex_color']

        has_color_sample = any('color' in getattr(btn, 'field_type', '') for btn in self.sampling_fields)

        debug_info = []
        for button in self.sampling_fields:
            field_type = getattr(button, 'field_type', '')
            is_multi = self.is_multi_value_field(field_type)

            widget = getattr(button, 'target_widget', None)
            if widget is None:
                path = getattr(button, 'field_config_path', '')
                widget = self._find_widget_by_config_path(self.config_layout, path)
            
            if widget is not None:
                try:
                    _ = widget.text()
                except RuntimeError:
                    self.sampling_fields.discard(button)
                    button.setChecked(False)
                    button.setStyleSheet("")
                    widget = None
            
            debug_msg = f"类型: {field_type} | 结果: {type(widget).__name__ if widget else 'None'}"
            debug_info.append(debug_msg)
            
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
        self.sampling_control_widget.setVisible(False)
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
        self.sampling_control_widget.setVisible(False)
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

        result = self._do_capture(self.capture_region, hwnd=self.game_hwnd)
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

    def ocr_filter_preview(self):
        try:
            rw, rh = self.capture_screenshot_for_test()
            img_width = self.img_width
            capture_region = self.capture_region

            ocr_top_left = lib.parse_coordinate(self.get_config_value("health_bar.ocr_top_left") or [0, 0])
            ocr_bottom_right = lib.parse_coordinate(self.get_config_value("health_bar.ocr_bottom_right") or [0, 0])
            ocr_filters = self.get_config_value("health_bar.ocr_filters") or []

            if not isinstance(ocr_top_left, list) or len(ocr_top_left) < 2:
                QMessageBox.warning(self, "错误", "请先配置血条OCR左上角坐标")
                return
            if not isinstance(ocr_bottom_right, list) or len(ocr_bottom_right) < 2:
                QMessageBox.warning(self, "错误", "请先配置血条OCR右下角坐标")
                return

            offset_x = capture_region[0] if len(capture_region) >= 1 else 0
            offset_y = capture_region[1] if len(capture_region) >= 2 else 0

            x1 = ocr_top_left[0] - offset_x
            y1 = ocr_top_left[1] - offset_y
            x2 = ocr_bottom_right[0] - offset_x
            y2 = ocr_bottom_right[1] - offset_y

            crop_w = x2 - x1
            crop_h = y2 - y1
            if crop_w <= 0 or crop_h <= 0:
                QMessageBox.warning(self, "错误", f"OCR裁剪区域无效: ({x1},{y1})-({x2},{y2})")
                return

            from PIL import Image
            import numpy as np
            import datetime

            bmp_data = bytes(self.bmp_data)

            buf_size = rw * rh * 4
            raw_data = bmp_data[:buf_size]
            arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((rh, rw, 4))
            rgb_arr = arr[:, :, 2::-1].copy()
            orig_img = Image.fromarray(rgb_arr, 'RGB')
            orig_cropped = orig_img.crop((x1, y1, x2, y2))

            filtered_bgra = None
            cropped_bytes = bytearray()
            for y in range(y1, y2):
                row_start = (y * img_width + x1) * 4
                row_end = row_start + crop_w * 4
                if row_end > len(bmp_data):
                    QMessageBox.warning(self, "错误", "裁剪区域超出截图范围")
                    return
                cropped_bytes.extend(bmp_data[row_start:row_end])
            cropped_bytes = bytes(cropped_bytes)

            if ocr_filters:
                filtered_bgra = lib.apply_filters_chain(cropped_bytes, crop_w, crop_h, ocr_filters, lib.parse_colors)

            screenshot_dir = os.path.join(_plugin_dir, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            orig_path = os.path.join(screenshot_dir, f"ocr_filter_original_{timestamp}.png")
            orig_cropped.save(orig_path, 'PNG')

            filtered_path = None
            if filtered_bgra:
                filtered_arr = np.frombuffer(bytes(filtered_bgra), dtype=np.uint8).reshape((crop_h, crop_w, 4))
                filtered_rgb = filtered_arr[:, :, 2::-1].copy()
                filtered_img = Image.fromarray(filtered_rgb, 'RGB')
                filtered_path = os.path.join(screenshot_dir, f"ocr_filter_filtered_{timestamp}.png")
                filtered_img.save(filtered_path, 'PNG')

            msg = f"原图已保存: {orig_path}"
            if filtered_path:
                msg += f"\n滤镜后已保存: {filtered_path}"
            else:
                msg += "\n未应用滤镜(未配置滤镜链)"

            self.status_label.setText(f"状态: OCR滤镜预览已保存")

            result_dialog = QDialog(self)
            result_dialog.setWindowTitle("OCR滤镜预览")
            result_dialog.setMinimumSize(600, 400)
            result_layout = QVBoxLayout(result_dialog)

            filters_desc = ", ".join(f.get("type", "?") for f in ocr_filters) if ocr_filters else "无"
            info_label = QLabel(f"OCR区域: ({ocr_top_left[0]},{ocr_top_left[1]}) - ({ocr_bottom_right[0]},{ocr_bottom_right[1]})  "
                                f"尺寸: {crop_w}x{crop_h}\n"
                                f"滤镜链: {filters_desc}")
            result_layout.addWidget(info_label)

            images_layout = QHBoxLayout()

            orig_label = QLabel("原图")
            orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            orig_pixmap = QPixmap(orig_path)
            if orig_pixmap.width() > 0:
                scaled = orig_pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                orig_label.setPixmap(scaled)
            images_layout.addWidget(orig_label)

            if filtered_path:
                filtered_label = QLabel("滤镜后")
                filtered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                filtered_pixmap = QPixmap(filtered_path)
                if filtered_pixmap.width() > 0:
                    scaled = filtered_pixmap.scaled(280, 280, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    filtered_label.setPixmap(scaled)
                images_layout.addWidget(filtered_label)

            result_layout.addLayout(images_layout)

            path_label = QLabel(msg)
            path_label.setWordWrap(True)
            result_layout.addWidget(path_label)

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(result_dialog.close)
            result_layout.addWidget(close_btn)

            result_dialog.exec()

        except ImportError:
            QMessageBox.warning(self, "错误", "此功能需要安装 PIL 和 numpy 库\n请运行: pip install pillow numpy")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"OCR滤镜预览失败: {e}")
            self.status_label.setText(f"状态: OCR滤镜预览出错 - {e}")

    def ocr_once(self):
        try:
            rw, rh = self.capture_screenshot_for_test()
            img_width = self.img_width
            capture_region = self.capture_region

            ocr_port = self.get_config_value("ocr.port") or 1395
            health_api_ip = self.get_config_value("health_bar.ocr_api_ip") or ""
            shield_api_ip = self.get_config_value("shield_bar.ocr_api_ip") or ""

            if not health_api_ip and not shield_api_ip:
                if not lib.check_ocr_server(ocr_port):
                    QMessageBox.warning(self, "错误", f"OCR服务端未运行 (端口: {ocr_port})\n请先启动 Umi-OCR 软件")
                    return

            offset_x = capture_region[0] if len(capture_region) >= 1 else 0
            offset_y = capture_region[1] if len(capture_region) >= 2 else 0

            results = []

            health_ocr_top_left = lib.parse_coordinate(self.get_config_value("health_bar.ocr_top_left") or [0, 0])
            health_ocr_bottom_right = lib.parse_coordinate(self.get_config_value("health_bar.ocr_bottom_right") or [0, 0])
            health_filters = self.get_config_value("health_bar.ocr_filters") or []
            health_api_data = self.get_config_value("health_bar.ocr_api_data") or ""

            if isinstance(health_ocr_top_left, list) and len(health_ocr_top_left) >= 2 and \
               isinstance(health_ocr_bottom_right, list) and len(health_ocr_bottom_right) >= 2:
                hx1 = health_ocr_top_left[0] - offset_x
                hy1 = health_ocr_top_left[1] - offset_y
                hx2 = health_ocr_bottom_right[0] - offset_x
                hy2 = health_ocr_bottom_right[1] - offset_y
                if hx2 > hx1 and hy2 > hy1:
                    health_number, health_ocr_time, _ = lib.ocr_recognize_number(
                        self.bmp_data, hx1, hy1, hx2, hy2, img_width,
                        port=ocr_port, log=lambda msg, lvl="INFO": None,
                        filters=health_filters if health_filters else None,
                        parse_color_func=lib.parse_colors,
                        api_ip=health_api_ip or None, api_data=health_api_data or None
                    )
                    results.append(f"血量OCR: {health_number if health_number is not None else '未识别'}  (耗时: {health_ocr_time*1000:.0f}ms)")
                else:
                    results.append("血量OCR: 区域无效")
            else:
                results.append("血量OCR: 未配置坐标")

            shield_ocr_top_left = lib.parse_coordinate(self.get_config_value("shield_bar.ocr_top_left") or [0, 0])
            shield_ocr_bottom_right = lib.parse_coordinate(self.get_config_value("shield_bar.ocr_bottom_right") or [0, 0])
            shield_filters = self.get_config_value("shield_bar.ocr_filters") or []
            shield_api_data = self.get_config_value("shield_bar.ocr_api_data") or ""

            if isinstance(shield_ocr_top_left, list) and len(shield_ocr_top_left) >= 2 and \
               isinstance(shield_ocr_bottom_right, list) and len(shield_ocr_bottom_right) >= 2:
                sx1 = shield_ocr_top_left[0] - offset_x
                sy1 = shield_ocr_top_left[1] - offset_y
                sx2 = shield_ocr_bottom_right[0] - offset_x
                sy2 = shield_ocr_bottom_right[1] - offset_y
                if sx2 > sx1 and sy2 > sy1:
                    shield_number, shield_ocr_time, _ = lib.ocr_recognize_number(
                        self.bmp_data, sx1, sy1, sx2, sy2, img_width,
                        port=ocr_port, log=lambda msg, lvl="INFO": None,
                        filters=shield_filters if shield_filters else None,
                        parse_color_func=lib.parse_colors,
                        api_ip=shield_api_ip or None, api_data=shield_api_data or None
                    )
                    results.append(f"盾量OCR: {shield_number if shield_number is not None else '未识别'}  (耗时: {shield_ocr_time*1000:.0f}ms)")
                else:
                    results.append("盾量OCR: 区域无效")
            else:
                results.append("盾量OCR: 未配置坐标")

            result_dialog = QDialog(self)
            result_dialog.setWindowTitle("OCR一次 结果")
            result_dialog.setMinimumWidth(400)
            result_layout = QVBoxLayout(result_dialog)

            result_text = QTextEdit()
            result_text.setReadOnly(True)
            result_text.setPlainText('\n'.join(results))
            result_layout.addWidget(result_text)

            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(result_dialog.close)
            result_layout.addWidget(close_btn)

            result_dialog.exec()
            self.status_label.setText(f"状态: OCR一次完成")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "错误", f"OCR一次失败: {e}")
            self.status_label.setText(f"状态: OCR一次出错 - {e}")

    FILTER_TYPE_NAMES = {
        "replace_color": "替换颜色",
        "invert": "反色",
        "contrast": "对比度",
        "channel": "单通道",
        "dilate": "膨胀",
        "contour": "轮廓",
        "python": "Python代码",
    }

    FILTER_TYPE_NAMES_REVERSE = {v: k for k, v in FILTER_TYPE_NAMES.items()}

    def open_filter_editor(self, bar_key):
        from PyQt6.QtWidgets import QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{'血量' if bar_key == 'health_bar' else '盾量'}滤镜编辑器")
        dialog.setMinimumSize(750, 650)
        dialog_layout = QVBoxLayout(dialog)

        filters = self.get_config_value(f"{bar_key}.ocr_filters") or []
        new_filters = [dict(f) for f in filters]

        add_row = QHBoxLayout()
        add_combo = QComboBox()
        chinese_names = list(self.FILTER_TYPE_NAMES.values())
        add_combo.addItems(chinese_names)
        add_btn = QPushButton("添加")
        add_row.addWidget(QLabel("添加滤镜:"))
        add_row.addWidget(add_combo, stretch=1)
        add_row.addWidget(add_btn)
        add_row.addStretch()
        dialog_layout.addLayout(add_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self._filters_list_layout = QVBoxLayout(scroll_content)
        self._filters_list_layout.setSpacing(4)
        self._filters_list_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(scroll_content)
        dialog_layout.addWidget(scroll, stretch=1)

        stage_row = QHBoxLayout()
        preview_btn = QPushButton("预览最终结果")
        stage_preview_btn = QPushButton("预览各阶段")
        stage_combo = QComboBox()
        stage_combo.addItem("全部阶段")
        stage_row.addWidget(preview_btn)
        stage_row.addWidget(stage_preview_btn)
        stage_row.addWidget(QLabel("查看阶段:"))
        stage_row.addWidget(stage_combo)
        ocr_toggle = QCheckBox("OCR识别")
        stage_row.addWidget(ocr_toggle)
        stage_row.addStretch()
        dialog_layout.addLayout(stage_row)

        preview_splitter = QSplitter(Qt.Orientation.Horizontal)
        orig_preview_label = QLabel()
        orig_preview_label.setMinimumHeight(80)
        orig_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orig_preview_label.setStyleSheet("border: 1px solid #555; background: #222;")
        filtered_preview_label = QLabel()
        filtered_preview_label.setMinimumHeight(80)
        filtered_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filtered_preview_label.setStyleSheet("border: 1px solid #555; background: #222;")
        preview_splitter.addWidget(orig_preview_label)
        preview_splitter.addWidget(filtered_preview_label)
        dialog_layout.addWidget(preview_splitter)

        ocr_result_label = QLabel("")
        ocr_result_label.setStyleSheet("color: #aaa; font-size: 11px; padding: 2px;")
        ocr_result_label.setVisible(False)
        dialog_layout.addWidget(ocr_result_label)

        _preview_timer = QTimer()
        _preview_timer.setInterval(100)
        _ocr_server_ok = [True]
        _ocr_fail_time = [0.0]

        def _auto_preview_tick():
            game_title = self.get_config_value("game.process_title") or ""
            if game_title:
                try:
                    if not self.game_hwnd:
                        self.game_hwnd = lib.get_game_window(process_title=game_title)
                    if self.game_hwnd:
                        bmp, rx, ry, rw, rh, iw = self._do_capture(hwnd=self.game_hwnd)
                        if bmp:
                            self.bmp_data = bmp
                            self.img_width = iw
                            self.capture_region = [rx, ry, rw, rh]
                except Exception:
                    pass
            cropped, w, h = _get_cropped_data()
            if cropped is None:
                return
            from ocr import create_png_from_bgra
            orig_png = create_png_from_bgra(cropped, w, h)
            if orig_png:
                qimg = QImage.fromData(bytes(orig_png))
                if not qimg.isNull():
                    orig_preview_label.setPixmap(QPixmap.fromImage(qimg).scaled(400, 120, Qt.AspectRatioMode.KeepAspectRatio))
            stage_idx = stage_combo.currentIndex() - 1
            from ocr import apply_filters_chain
            import image as img_mod
            if stage_idx < 0:
                result = apply_filters_chain(cropped, w, h, new_filters, img_mod.parse_colors)
            else:
                partial_filters = new_filters[:stage_idx + 1]
                result = apply_filters_chain(cropped, w, h, partial_filters, img_mod.parse_colors)
            result_png = create_png_from_bgra(result, w, h)
            if result_png:
                qimg = QImage.fromData(bytes(result_png))
                if not qimg.isNull():
                    filtered_preview_label.setPixmap(QPixmap.fromImage(qimg).scaled(400, 120, Qt.AspectRatioMode.KeepAspectRatio))
            if ocr_toggle.isChecked():
                import time
                now = time.monotonic()
                if not _ocr_server_ok[0] and (now - _ocr_fail_time[0]) < 4.0:
                    return
                try:
                    from ocr import create_png_from_bgra, check_ocr_server
                    import base64, requests, json as _json
                    ocr_port = self.get_config_value("ocr.port") or 1395
                    ocr_api_ip = (self.get_config_value("health_bar.ocr_api_ip") or "").strip()
                    if not ocr_api_ip or lib.check_ocr_server(ocr_port):
                        _ocr_server_ok[0] = True
                        png_for_ocr = create_png_from_bgra(result, w, h)
                        if png_for_ocr:
                            b64 = base64.b64encode(bytes(png_for_ocr)).decode('utf-8')
                            ocr_api_data = self.get_config_value("health_bar.ocr_api_data") or ""
                            options = {}
                            if ocr_api_data:
                                try:
                                    options = json.loads(ocr_api_data) if isinstance(ocr_api_data, str) else ocr_api_data
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            if not options:
                                options = {
                                    "data.format": "text",
                                    "ocr.language": "models/config_en.txt",
                                    "ocr.cls": False,
                                    "tbpu.parser": "none"
                                }
                            data = {"base64": b64, "options": options}
                            api_ip = ocr_api_ip if ocr_api_ip else "127.0.0.1"
                            r = requests.post(f"http://{api_ip}:{ocr_port}/api/ocr",
                                              data=_json.dumps(data),
                                              headers={"Content-Type": "application/json"},
                                              timeout=5)
                            if r.status_code == 200:
                                res = r.json()
                                from ocr import _extract_ocr_text
                                ocr_text = _extract_ocr_text(res)
                                if ocr_text:
                                    ocr_result_label.setText(f"OCR: {ocr_text}")
                                else:
                                    ocr_result_label.setText(f"OCR: 未识别")
                            else:
                                ocr_result_label.setText(f"OCR: HTTP {r.status_code}")
                        else:
                            ocr_result_label.setText("OCR: 图片生成失败")
                    else:
                        _ocr_server_ok[0] = False
                        _ocr_fail_time[0] = now
                        ocr_result_label.setText("OCR: 服务未启动")
                    ocr_result_label.setVisible(True)
                except Exception as e:
                    _ocr_server_ok[0] = False
                    _ocr_fail_time[0] = now
                    ocr_result_label.setText(f"OCR错误: {e}")
                    ocr_result_label.setVisible(True)
            else:
                _ocr_server_ok[0] = True
                ocr_result_label.setVisible(False)

        _preview_timer.timeout.connect(_auto_preview_tick)
        _preview_timer.start()

        def on_dialog_finished_cleanup():
            _preview_timer.stop()

        dialog.finished.connect(on_dialog_finished_cleanup)

        sampling_row = QHBoxLayout()
        filter_finish_sampling_btn = QPushButton("完成采样 (P)")
        filter_cancel_sampling_btn = QPushButton("取消采样 (ESC)")
        filter_sampling_status = QLabel("")
        sampling_row.addWidget(filter_sampling_status, stretch=1)
        sampling_row.addWidget(filter_finish_sampling_btn)
        sampling_row.addWidget(filter_cancel_sampling_btn)
        filter_sampling_widget = QWidget()
        filter_sampling_widget.setLayout(sampling_row)
        filter_sampling_widget.setVisible(False)
        dialog_layout.addWidget(filter_sampling_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        filter_bottom_layout = QHBoxLayout()
        filter_top_btn = QPushButton("📌置顶")
        filter_top_btn.setCheckable(True)
        filter_top_btn.setFixedWidth(60)
        filter_top_btn.toggled.connect(lambda checked: dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked) or dialog.show())
        filter_bottom_layout.addWidget(filter_top_btn)
        filter_bottom_layout.addStretch()
        filter_bottom_layout.addWidget(button_box)
        dialog_layout.addLayout(filter_bottom_layout)

        def rebuild_filters_ui():
            for btn in list(self.sampling_fields):
                btn.setChecked(False)
                btn.setStyleSheet("")
            self.sampling_fields.clear()

            while self._filters_list_layout.count():
                item = self._filters_list_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            stage_combo.clear()
            stage_combo.addItem("全部阶段")
            _filter_drag_idx = [-1]
            _filter_drag_target = [-1]
            _filter_rows = []
            for i, f in enumerate(new_filters):
                widget = _create_filter_item(i, f, _filter_drag_idx, _filter_drag_target, _filter_rows)
                self._filters_list_layout.addWidget(widget)
                stage_combo.addItem(f"{i}: {self._filter_display_text(f)}")
            self._filters_list_layout.addStretch()

        def _create_filter_item(index, f, _filter_drag_idx, _filter_drag_target, _filter_rows):
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.StyledPanel)
            frame.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 3px; }")
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(4, 4, 4, 4)
            frame_layout.setSpacing(2)

            header = QWidget()
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(4)

            handle_lbl = QLabel("☰")
            handle_lbl.setFixedWidth(22)
            handle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            handle_lbl.setCursor(Qt.CursorShape.OpenHandCursor)
            header_layout.addWidget(handle_lbl)

            toggle_btn = QPushButton("▶")
            toggle_btn.setFixedWidth(22)
            toggle_btn.setFlat(True)
            toggle_btn.setStyleSheet("QPushButton { font-size: 12px; }")
            header_layout.addWidget(toggle_btn)

            type_name = self.FILTER_TYPE_NAMES.get(f.get("type", ""), f.get("type", ""))
            summary = _get_filter_summary(f)
            type_label = QLabel(f"{type_name}  {summary}")
            type_label.setStyleSheet("font-weight: bold;")
            header_layout.addWidget(type_label, stretch=1)

            del_btn = QPushButton("×")
            del_btn.setFixedWidth(26)
            del_btn.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
            header_layout.addWidget(del_btn)

            frame_layout.addWidget(header)

            has_params = f.get("type", "") not in ("invert", "contour")

            content = QWidget()
            content_layout = QFormLayout(content)
            content_layout.setContentsMargins(4, 4, 4, 4)
            content_layout.setSpacing(4)
            _build_filter_content(content_layout, f, type_label)
            content.setVisible(False)

            if has_params:
                frame_layout.addWidget(content)

            if not has_params:
                toggle_btn.setVisible(False)

            def on_toggle():
                visible = content.isVisible()
                content.setVisible(not visible)
                toggle_btn.setText("▼" if not visible else "▶")

            toggle_btn.clicked.connect(on_toggle)

            def on_del():
                new_filters.pop(index)
                rebuild_filters_ui()

            del_btn.clicked.connect(on_del)

            row_info = {"widget": frame, "handle": handle_lbl}
            _filter_rows.append(row_info)

            def _make_handle_mouse_press(idx_i, h_lbl):
                def cb(event):
                    if event.button() == Qt.MouseButton.LeftButton:
                        _filter_drag_idx[0] = idx_i
                        _filter_drag_target[0] = idx_i
                        h_lbl.setCursor(Qt.CursorShape.ClosedHandCursor)
                return cb

            def _make_handle_mouse_release(idx_i, h_lbl):
                def cb(event):
                    if _filter_drag_idx[0] >= 0 and _filter_drag_target[0] >= 0:
                        src = _filter_drag_idx[0]
                        dst = _filter_drag_target[0]
                        if src != dst and 0 <= src < len(new_filters) and 0 <= dst < len(new_filters):
                            moved = new_filters.pop(src)
                            new_filters.insert(dst, moved)
                            rebuild_filters_ui()
                    _filter_drag_idx[0] = -1
                    _filter_drag_target[0] = -1
                    h_lbl.setCursor(Qt.CursorShape.OpenHandCursor)
                return cb

            def _make_handle_mouse_move(idx_i):
                def cb(event):
                    if _filter_drag_idx[0] == idx_i:
                        global_y = frame.mapToGlobal(event.position().toPoint()).y()
                        for j, sr2 in enumerate(_filter_rows):
                            w_y = sr2["widget"].mapToGlobal(QPoint(0, 0)).y()
                            w_h = sr2["widget"].height()
                            if w_y <= global_y <= w_y + w_h:
                                _filter_drag_target[0] = j
                                break
                return cb

            handle_lbl.mousePressEvent = _make_handle_mouse_press(index, handle_lbl)
            handle_lbl.mouseReleaseEvent = _make_handle_mouse_release(index, handle_lbl)
            handle_lbl.mouseMoveEvent = _make_handle_mouse_move(index)

            return frame

        def _get_filter_summary(f):
            f_type = f.get("type", "")
            if f_type == "replace_color":
                colors = f.get("colors", "")
                tol = f.get("tolerance", 30)
                feather = f.get("feather", 0)
                s = f"颜色={colors}, 容差={tol}"
                if feather > 0:
                    s += f", 羽化={feather}"
                return s
            elif f_type == "contrast":
                return f"值={f.get('value', 50)}"
            elif f_type == "channel":
                return f"通道={f.get('channel', 'r').upper()}"
            elif f_type == "dilate":
                return f"强度={f.get('iterations', 1)}"
            elif f_type == "python":
                code = f.get("code", "")
                first_line = code.split('\n')[0][:25] if code else ""
                return f"{first_line}..."
            return ""

        def _build_filter_content(layout, f, type_label_widget):
            f_type = f.get("type", "")
            if f_type == "replace_color":
                colors_edit = ColorLineEdit(f.get("colors", ""))
                colors_edit.setPlaceholderText("#RRGGBB, 多个用|分隔")
                colors_btn = QPushButton("采样")
                colors_btn.setCheckable(True)
                colors_btn.setFixedWidth(50)
                colors_btn.field_type = "colors"
                colors_btn.target_widget = colors_edit
                colors_row = QHBoxLayout()
                colors_row.addWidget(colors_btn)
                colors_row.addWidget(colors_edit, stretch=1)
                layout.addRow("颜色:", colors_row)
                tol_spin = QSpinBox()
                tol_spin.setRange(0, 255)
                tol_spin.setValue(f.get("tolerance", 30))
                layout.addRow("容差:", tol_spin)
                feather_spin = QSpinBox()
                feather_spin.setRange(0, 50)
                feather_spin.setValue(f.get("feather", 0))
                layout.addRow("羽化 (0=关闭):", feather_spin)

                def _update_colors(text):
                    f["colors"] = text
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                def _update_tol(v):
                    f["tolerance"] = v
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                def _update_feather(v):
                    f["feather"] = v
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                colors_edit.textChanged.connect(_update_colors)
                tol_spin.valueChanged.connect(_update_tol)
                feather_spin.valueChanged.connect(_update_feather)

                def _on_colors_btn_toggled(checked):
                    if checked:
                        if not self.sampling_mode:
                            self.start_sampling_mode()
                        self.sampling_fields.add(colors_btn)
                        colors_btn.setStyleSheet("background-color: red; color: white;")
                        filter_sampling_widget.setVisible(True)
                        filter_sampling_status.setText("采样模式 - 按 Enter 采样颜色")
                        self.sampling_control_widget.setVisible(False)
                    else:
                        self.sampling_fields.discard(colors_btn)
                        colors_btn.setStyleSheet("")
                        if not self.sampling_fields:
                            filter_sampling_widget.setVisible(False)
                            if self.sampling_mode:
                                self.finish_sampling()
                colors_btn.toggled.connect(_on_colors_btn_toggled)
                f["_colors_edit"] = colors_edit
                f["_colors_btn"] = colors_btn

            elif f_type == "contrast":
                contrast_spin = QSpinBox()
                contrast_spin.setRange(-100, 100)
                contrast_spin.setValue(f.get("value", 50))
                layout.addRow("对比度 (-100~100):", contrast_spin)
                def _update_contrast(v):
                    f["value"] = v
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                contrast_spin.valueChanged.connect(_update_contrast)

            elif f_type == "channel":
                channel_combo = QComboBox()
                channel_combo.addItems(["r", "g", "b"])
                channel_combo.setCurrentText(f.get("channel", "r"))
                layout.addRow("通道:", channel_combo)
                def _update_channel(text):
                    f["channel"] = text
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                channel_combo.currentTextChanged.connect(_update_channel)

            elif f_type == "dilate":
                iter_spin = QSpinBox()
                iter_spin.setRange(1, 20)
                iter_spin.setValue(f.get("iterations", 1))
                layout.addRow("强度(1=羽化,2=1次迭代):", iter_spin)
                def _update_iter(v):
                    f["iterations"] = v
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                iter_spin.valueChanged.connect(_update_iter)

            elif f_type == "python":
                hint_label = QLabel("可用变量: data(bytearray), width, height, np(numpy), np_data(ndarray h×w×4 BGRA)")
                hint_label.setStyleSheet("color: #888; font-size: 10px; padding: 2px;")
                layout.addRow(hint_label)
                code_edit = QPlainTextEdit()
                code_edit.setPlainText(f.get("code", ""))
                code_edit.setMinimumHeight(180)
                font = QFont("Consolas", 10)
                font.setStyleHint(QFont.StyleHint.Monospace)
                code_edit.setFont(font)
                code_edit.setStyleSheet("QPlainTextEdit { background-color: #1A1B1D; color: #d4d4d4; }")
                f["_highlighter"] = PythonSyntaxHighlighter(code_edit.document())
                layout.addRow(code_edit)
                def _update_code():
                    f["code"] = code_edit.toPlainText()
                    type_label_widget.setText(f"{self.FILTER_TYPE_NAMES.get(f_type, f_type)}  {_get_filter_summary(f)}")
                code_edit.textChanged.connect(_update_code)

        def on_add():
            chinese_name = add_combo.currentText()
            f_type = self.FILTER_TYPE_NAMES_REVERSE.get(chinese_name, chinese_name)
            f_obj = {"type": f_type}
            if f_type == "replace_color":
                f_obj["colors"] = ""
                f_obj["tolerance"] = 30
                f_obj["feather"] = 0
            elif f_type == "contrast":
                f_obj["value"] = 50
            elif f_type == "channel":
                f_obj["channel"] = "r"
            elif f_type == "dilate":
                f_obj["iterations"] = 1
            elif f_type == "python":
                f_obj["code"] = "# data: bytearray(BGRA), width, height\n# np_data: numpy.ndarray\n# 修改data后自动生效\nfor i in range(0, len(data)-2, 4):\n# passnp_data[:4] = [255, 0, 255, 255]\n# np_data[-4:] = [255, 0, 255, 255]"
            new_filters.append(f_obj)
            rebuild_filters_ui()

        add_btn.clicked.connect(on_add)

        def _get_cropped_data():
            if not self.bmp_data:
                return None, 0, 0
            ocr_tl = lib.parse_coordinate(self.get_config_value(f"{bar_key}.ocr_top_left") or [0, 0])
            ocr_br = lib.parse_coordinate(self.get_config_value(f"{bar_key}.ocr_bottom_right") or [0, 0])
            cap_region = self.capture_region
            x1 = ocr_tl[0] - cap_region[0]
            y1 = ocr_tl[1] - cap_region[1]
            x2 = ocr_br[0] - cap_region[0]
            y2 = ocr_br[1] - cap_region[1]
            w = x2 - x1
            h = y2 - y1
            if w <= 0 or h <= 0:
                return None, 0, 0
            cropped = bytearray()
            for yy in range(y1, y2):
                row_start = (yy * self.img_width + x1) * 4
                row_end = row_start + w * 4
                cropped.extend(self.bmp_data[row_start:row_end])
            return bytes(cropped), w, h

        def _show_preview(data, w, h):
            from ocr import create_png_from_bgra
            png_data = create_png_from_bgra(data, w, h)
            if png_data:
                qimg = QImage.fromData(bytes(png_data))
                if not qimg.isNull():
                    filtered_preview_label.setPixmap(QPixmap.fromImage(qimg).scaled(400, 120, Qt.AspectRatioMode.KeepAspectRatio))
                    return
            filtered_preview_label.setText("预览生成失败")

        def on_preview():
            cropped, w, h = _get_cropped_data()
            if cropped is None:
                filtered_preview_label.setText("请先截图或导入截图")
                return
            from ocr import apply_filters_chain
            import image as img_mod
            result = apply_filters_chain(cropped, w, h, new_filters, img_mod.parse_colors)
            _show_preview(result, w, h)

        def on_stage_preview():
            cropped, w, h = _get_cropped_data()
            if cropped is None:
                filtered_preview_label.setText("请先截图或导入截图")
                return
            from ocr import apply_filters_chain
            import image as img_mod
            stage_idx = stage_combo.currentIndex() - 1
            if stage_idx < 0:
                on_preview()
                return
            partial_filters = new_filters[:stage_idx + 1]
            result = apply_filters_chain(cropped, w, h, partial_filters, img_mod.parse_colors)
            _show_preview(result, w, h)

        preview_btn.clicked.connect(on_preview)
        stage_preview_btn.clicked.connect(on_stage_preview)

        def on_filter_finish_sampling():
            for button in list(self.sampling_fields):
                button.setChecked(False)
                button.setStyleSheet("")
            self.sampling_fields.clear()
            if self.sampling_mode:
                self.finish_sampling()

        def on_filter_cancel_sampling():
            for button in list(self.sampling_fields):
                button.setChecked(False)
                button.setStyleSheet("")
            self.sampling_fields.clear()
            if self.sampling_mode:
                self.cancel_sampling()

        filter_finish_sampling_btn.clicked.connect(on_filter_finish_sampling)
        filter_cancel_sampling_btn.clicked.connect(on_filter_cancel_sampling)

        rebuild_filters_ui()

        def on_accept():
            clean = []
            for f in new_filters:
                cf = {k: v for k, v in f.items() if not k.startswith('_')}
                clean.append(cf)
            self.set_config_value(f"{bar_key}.ocr_filters", clean)
            self._update_filter_summaries()
            dialog.close()

        button_box.accepted.connect(on_accept)
        button_box.rejected.connect(dialog.close)

        def on_dialog_finished():
            if self.sampling_mode:
                for button in list(self.sampling_fields):
                    button.setChecked(False)
                    button.setStyleSheet("")
                self.sampling_fields.clear()
                self.cancel_sampling()
            filter_sampling_widget.setVisible(False)

        dialog.finished.connect(on_dialog_finished)

        class _SamplingKeyFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress and self.active:
                    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        self.do_sample()
                        return True
                    elif event.key() == Qt.Key.Key_P:
                        self.do_finish()
                        return True
                    elif event.key() == Qt.Key.Key_Escape:
                        self.do_cancel()
                        return True
                return False

        _key_filter = _SamplingKeyFilter()
        _key_filter.active = False
        _key_filter.do_sample = self.perform_sampling
        _key_filter.do_finish = on_filter_finish_sampling
        _key_filter.do_cancel = on_filter_cancel_sampling

        _orig_start = self.start_sampling_mode
        _orig_finish = self.finish_sampling
        _orig_cancel = self.cancel_sampling

        def _patched_start():
            _orig_start()
            _key_filter.active = True
            self.sampling_control_widget.setVisible(False)

        def _patched_finish():
            _orig_finish()
            _key_filter.active = False
            filter_sampling_widget.setVisible(False)

        def _patched_cancel():
            _orig_cancel()
            _key_filter.active = False
            filter_sampling_widget.setVisible(False)

        self.start_sampling_mode = _patched_start
        self.finish_sampling = _patched_finish
        self.cancel_sampling = _patched_cancel

        QApplication.instance().installEventFilter(_key_filter)

        def _restore_on_close():
            QApplication.instance().removeEventFilter(_key_filter)
            self.start_sampling_mode = _orig_start
            self.finish_sampling = _orig_finish
            self.cancel_sampling = _orig_cancel
            clean = []
            for f in new_filters:
                cf = {k: v for k, v in f.items() if not k.startswith('_')}
                clean.append(cf)
            self.set_config_value(f"{bar_key}.ocr_filters", clean)
            self._update_filter_summaries()

        dialog.finished.connect(_restore_on_close)

        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.show()

    def _filter_display_text(self, f):
        f_type = f.get("type", "unknown")
        if f_type == "replace_color":
            feather = f.get('feather', 0)
            txt = f"替换颜色: colors={f.get('colors', '')}, tolerance={f.get('tolerance', 30)}"
            if feather > 0:
                txt += f", feather={feather}"
            return txt
        elif f_type == "invert":
            return "反色"
        elif f_type == "contrast":
            return f"对比度: {f.get('value', 50)}"
        elif f_type == "channel":
            return f"单通道: {f.get('channel', 'r').upper()}"
        elif f_type == "dilate":
            iters = f.get('iterations', 1)
            real = iters / 2
            return f"膨胀: 强度{iters}(≈{real:.1f}次迭代)"
        elif f_type == "contour":
            return "轮廓"
        elif f_type == "python":
            code = f.get("code", "")
            first_line = code.split('\n')[0][:30] if code else ""
            return f"Python代码: {first_line}..."
        return f_type

    def _update_filter_summaries(self):
        for bar_key, label_attr in [("health_bar", "health_filter_summary"), ("shield_bar", "shield_filter_summary")]:
            label = getattr(self, label_attr, None)
            if label is None:
                continue
            filters = self.get_config_value(f"{bar_key}.ocr_filters") or []
            if not filters:
                label.setText("(无滤镜)")
            else:
                names = []
                for f in filters:
                    cn = self.FILTER_TYPE_NAMES.get(f.get("type", ""), f.get("type", ""))
                    names.append(cn)
                label.setText(" → ".join(names))

    def _start_status_timers(self):
        if hasattr(self, '_ocr_test_timer'):
            self._ocr_test_timer.stop()
        if hasattr(self, '_game_test_timer'):
            self._game_test_timer.stop()
        self._ocr_connected = False
        self._game_connected = False
        self._ocr_test_timer = QTimer(self)
        self._ocr_test_timer.setSingleShot(True)
        self._ocr_test_timer.timeout.connect(self._test_ocr_connection)
        self._game_test_timer = QTimer(self)
        self._game_test_timer.setSingleShot(True)
        self._game_test_timer.timeout.connect(self._test_game_connection)
        self._ocr_test_timer.start(2000)
        self._game_test_timer.start(2000)

    def _test_ocr_connection(self):
        ocr_enabled = self.get_config_value("ocr.enabled")
        if not ocr_enabled:
            if hasattr(self, 'ocr_status_label'):
                self.ocr_status_label.setText("")
                self.ocr_status_label.setStyleSheet("font-size: 11px;")
            self._ocr_test_timer.start(10000)
            return
        health_api_ip = (self.get_config_value("health_bar.ocr_api_ip") or "").strip()
        shield_api_ip = (self.get_config_value("shield_bar.ocr_api_ip") or "").strip()
        port = self.get_config_value("ocr.port") or 1395
        def _do_test():
            try:
                if health_api_ip:
                    ok = lib.check_ocr_api(health_api_ip, port)
                elif shield_api_ip:
                    ok = lib.check_ocr_api(shield_api_ip, port)
                else:
                    ok = lib.check_ocr_server(port)
            except Exception:
                ok = False
            self._ocr_status_signal.emit(ok)
        threading.Thread(target=_do_test, daemon=True).start()

    def _on_ocr_status_result(self, ok):
        self._ocr_connected = ok
        if hasattr(self, 'ocr_status_label'):
            if ok:
                self.ocr_status_label.setText("● 已连接")
                self.ocr_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
                self._auto_init_ocr_advanced()
            else:
                self.ocr_status_label.setText("● 未连接")
                self.ocr_status_label.setStyleSheet("color: #F44336; font-size: 11px;")
        if ok:
            self._ocr_test_timer.start(30000)
        else:
            self._ocr_test_timer.start(10000)

    def _auto_init_ocr_advanced(self):
        needs_init = False
        for target_key in _OCR_TARGETS:
            api_data = self.get_config_value(f"{target_key}.ocr_api_data") or ""
            if not api_data:
                needs_init = True
                break
        if not needs_init:
            return
        if hasattr(self, 'ocr_status_label'):
            self.ocr_status_label.setText("初始化 OCR 进阶配置...")
            self.ocr_status_label.setStyleSheet("color: #FF9800; font-size: 11px;")
            QApplication.processEvents()
        port = self.get_config_value("ocr.port") or 1395
        try:
            import requests
            r = requests.get(f"http://127.0.0.1:{port}/api/ocr/get_options", timeout=3)
            if r.status_code == 200:
                res = r.json()
                options = res if "code" not in res else res.get("data", res)
                if isinstance(options, dict):
                    for target_key in _OCR_TARGETS:
                        api_data = self.get_config_value(f"{target_key}.ocr_api_data") or ""
                        if not api_data:
                            init_data = {}
                            for key, opt in options.items():
                                if not isinstance(opt, dict):
                                    continue
                                if key in _OCR_DEFAULT_OVERRIDES:
                                    init_data[key] = _OCR_DEFAULT_OVERRIDES[key]
                                else:
                                    default_val = opt.get("default")
                                    if default_val is not None:
                                        init_data[key] = default_val
                            skip_keys = {"tbpu.ignoreArea"}
                            cleaned = {}
                            for k, v in init_data.items():
                                if k in skip_keys:
                                    if v is None or v == "" or v == "[]" or v == []:
                                        continue
                                cleaned[k] = v
                            self.set_config_value(f"{target_key}.ocr_api_data", json.dumps(cleaned, ensure_ascii=False))
                    self._save_config_to_file()
        except Exception:
            pass
        QTimer.singleShot(2000, lambda: self._test_ocr_connection() if hasattr(self, '_test_ocr_connection') else None)

    def _test_game_connection(self):
        game_title = self.get_config_value("game.process_title") or ""
        def _do_test():
            try:
                if game_title:
                    hwnd = lib.get_game_window(process_title=game_title)
                    ok = hwnd is not None and hwnd != 0
                else:
                    ok = False
            except Exception:
                ok = False
            self._game_status_signal.emit(ok)
        threading.Thread(target=_do_test, daemon=True).start()

    def _on_game_status_result(self, ok):
        self._game_connected = ok
        if hasattr(self, 'game_status_label'):
            if ok:
                self.game_status_label.setText("● 已连接")
                self.game_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                self.game_status_label.setText("● 未连接")
                self.game_status_label.setStyleSheet("color: #F44336; font-size: 11px;")
        if ok:
            self._game_test_timer.start(20000)
        else:
            self._game_test_timer.start(5000)

    def _on_health_wave_changed(self):
        text = self.health_wave_edit.toPlainText()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        self.set_config_value("waveform.health_pulse", lines)
        if hasattr(self, 'health_wave_preview'):
            self.health_wave_preview.update_data(lines)

    def _on_shield_wave_changed(self):
        text = self.shield_wave_edit.toPlainText()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        self.set_config_value("waveform.shield_pulse", lines)
        if hasattr(self, 'shield_wave_preview'):
            self.shield_wave_preview.update_data(lines)

    def _parse_wave_step(self, line):
        try:
            line = line.strip()
            if len(line) < 16:
                return None
            freq_val = int(line[:2], 16)
            strength_val = int(line[8:10], 16)
            return {"freq": freq_val, "strength": strength_val, "raw": line}
        except (ValueError, IndexError):
            return None

    def _encode_wave_step(self, freq, strength):
        return f"{freq:02X}{freq:02X}{freq:02X}{freq:02X}{strength:02X}{strength:02X}{strength:02X}{strength:02X}"

    def _parse_dungeonlab(self, text):
        try:
            text = text.strip()
            if not text.startswith("Dungeonlab+pulse:"):
                return None
            body = text[len("Dungeonlab+pulse:"):]
            sections_raw = body.split("+section+")
            all_steps = []
            speed_rate = 1
            if sections_raw and "=" in sections_raw[0]:
                prefix, rest = sections_raw[0].split("=", 1)
                prefix_parts = prefix.split(",")
                if len(prefix_parts) >= 2:
                    try:
                        speed_rate = max(1, int(float(prefix_parts[1])))
                    except (ValueError, IndexError):
                        pass
                sections_raw[0] = rest
            for sec_idx, sec in enumerate(sections_raw):
                if "/" not in sec:
                    continue
                header, pulses_str = sec.split("/", 1)
                header_parts = header.split(",")
                if len(header_parts) < 5:
                    continue
                try:
                    min_freq_idx = int(float(header_parts[0]))
                    max_freq_idx = int(float(header_parts[1]))
                    duration_idx = int(float(header_parts[2]))
                    mode = int(float(header_parts[3]))
                    is_on = int(float(header_parts[4]))
                except (ValueError, IndexError):
                    continue
                if is_on == 0:
                    continue
                min_freq_idx = max(0, min(min_freq_idx, len(_DG_FREQ_MAP) - 1))
                max_freq_idx = max(0, min(max_freq_idx, len(_DG_FREQ_MAP) - 1))
                duration = _DG_SECTION_TIME_MAP[duration_idx] if 0 <= duration_idx < len(_DG_SECTION_TIME_MAP) else 1.0
                pulses = [p.strip() for p in pulses_str.split(",") if p.strip()]
                if not pulses:
                    continue
                pulses_duration_sec = len(pulses) * 0.1
                repeat_times = max(1, int(duration / pulses_duration_sec + 0.999))
                for j in range(repeat_times):
                    for idx, pt in enumerate(pulses):
                        if "-" in pt:
                            parts = pt.split("-")
                            strength_str = parts[0]
                        else:
                            strength_str = pt
                        try:
                            strength = float(strength_str)
                        except ValueError:
                            continue
                        strength_int = max(0, min(100, int(round(strength))))
                        if mode == 1:
                            freq_idx = min_freq_idx
                        elif mode == 2:
                            total = repeat_times * len(pulses)
                            current = j * len(pulses) + idx
                            freq_idx = min_freq_idx + int((max_freq_idx - min_freq_idx) * current / max(total - 1, 1))
                        elif mode == 3:
                            freq_idx = min_freq_idx + int((max_freq_idx - min_freq_idx) * idx / max(len(pulses) - 1, 1))
                        elif mode == 4:
                            freq_idx = min_freq_idx + int((max_freq_idx - min_freq_idx) * j / max(repeat_times - 1, 1))
                        else:
                            freq_idx = min_freq_idx
                        freq_idx = max(0, min(freq_idx, len(_DG_FREQ_MAP) - 1))
                        period_ms = _DG_FREQ_MAP[freq_idx]
                        v3_freq = _dg_period_to_v3_freq(period_ms)
                        all_steps.append({"freq": v3_freq, "strength": strength_int,
                                          "raw": self._encode_wave_step(v3_freq, strength_int)})
            return all_steps if all_steps else None
        except Exception:
            return None

    def _export_dungeonlab(self, steps):
        if not steps:
            return ""
        def v3_freq_to_index(v3_freq):
            period = _v3_freq_to_period(v3_freq)
            best_idx = 0
            best_diff = abs(_DG_FREQ_MAP[0] - period)
            for i, v in enumerate(_DG_FREQ_MAP):
                diff = abs(v - period)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
            return best_idx
        sections_data = []
        i = 0
        while i < len(steps):
            start_idx = i
            start_freq_idx = v3_freq_to_index(steps[i]["freq"])
            while i < len(steps) and v3_freq_to_index(steps[i]["freq"]) == start_freq_idx:
                i += 1
            group = steps[start_idx:i]
            freq_idx = start_freq_idx
            strengths = [s["strength"] for s in group]
            data_points = ",".join(f"{st:.2f}-0" for st in strengths)
            duration_idx = 0
            sections_data.append((freq_idx, freq_idx, duration_idx, 1, 1, data_points))
        if not sections_data:
            return ""
        parts = []
        for si, (min_f, max_f, dur, mode, is_on, data) in enumerate(sections_data):
            if si == 0:
                parts.append(f"0,1,8={min_f},{max_f},{dur},{mode},{is_on}/{data}")
            else:
                parts.append(f"{min_f},{max_f},{dur},{mode},{is_on}/{data}")
        return "Dungeonlab+pulse:" + "+section+".join(parts)

    def _open_waveform_editor(self, mode):
        from PyQt6.QtWidgets import QDialogButtonBox, QStyledItemDelegate, QStyleOptionComboBox
        from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont
        from PyQt6.QtCore import QRectF, QSize

        is_health = (mode == "health")
        title = "编辑血量波形" if is_health else "编辑盾量波形"
        wave_edit = self.health_wave_edit if is_health else self.shield_wave_edit
        wave_text = wave_edit.toPlainText()
        wave_lines = [l.strip() for l in wave_text.split('\n') if l.strip()]

        steps = []
        for line in wave_lines:
            parsed = self._parse_wave_step(line)
            if parsed:
                steps.append(parsed)
            else:
                steps.append({"freq": 10, "strength": 0, "raw": line})

        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(900, 650)
        main_layout = QVBoxLayout(dialog)

        class WaveformCanvas(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setMinimumHeight(220)
                self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self.selected = -1
                self._drag_mode = None
                self._drag_idx = -1
                self._drag_start_x = 0
                self._reorder_idx = -1
                self._reorder_target = -1
                self.setMouseTracking(True)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(25, 25, 30))
                w = self.width()
                h = self.height()
                ml, mr, mt, mb = 55, 20, 28, 42
                dw = w - ml - mr
                dh = h - mt - mb

                painter.setPen(QPen(QColor(180, 180, 180)))
                font = QFont()
                font.setPixelSize(12)
                painter.setFont(font)
                painter.drawText(5, 16, title)

                painter.setPen(QPen(QColor(80, 80, 80), 1))
                for pct in [0, 25, 50, 75, 100]:
                    y = mt + dh * (1 - pct / 100.0)
                    painter.drawLine(ml, int(y), w - mr, int(y))
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(5, int(y) + 4, f"{pct}")
                    painter.setPen(QPen(QColor(80, 80, 80), 1))

                painter.setPen(QPen(QColor(100, 100, 100), 1))
                painter.drawLine(ml, mt, ml, h - mb)
                painter.drawLine(ml, h - mb, w - mr, h - mb)

                if not steps:
                    painter.end()
                    return

                n = len(steps)
                gap = dw / n
                bar_w = min(gap * 0.5, 30)
                freq_marker_h = 4

                for i, step in enumerate(steps):
                    cx = ml + i * gap + gap / 2
                    bx = cx - bar_w / 2
                    strength_pct = step["strength"] / 100.0
                    bar_h = strength_pct * dh
                    freq = step["freq"]
                    freq_pct = (freq - 10) / 90.0
                    freq_y = h - mb - freq_pct * dh

                    period_ms = _v3_freq_to_period(freq)
                    num_bars = max(1, int(100.0 / period_ms))
                    density_ratio = min(num_bars * 2 / 40.0, 1.0)
                    r = int(50 + 200 * density_ratio)
                    g = int(200 - 100 * density_ratio)
                    b = int(50 + 50 * (1 - density_ratio))

                    if i == self.selected:
                        painter.setBrush(QBrush(QColor(100, 200, 255, 200)))
                        painter.setPen(QPen(QColor(100, 200, 255), 2))
                    else:
                        painter.setBrush(QBrush(QColor(r, g, b, 160)))
                        painter.setPen(QPen(QColor(r, g, b), 1))

                    painter.drawRect(QRectF(bx, h - mb - bar_h, bar_w, bar_h))

                    painter.setPen(QPen(QColor(255, 180, 50), 2))
                    painter.setBrush(QBrush(QColor(255, 180, 50)))
                    painter.drawRect(QRectF(bx - 1, freq_y - freq_marker_h / 2, bar_w + 2, freq_marker_h))

                    painter.setPen(QPen(QColor(200, 200, 200)))
                    font.setPixelSize(9)
                    painter.setFont(font)
                    painter.drawText(QRectF(cx - gap / 2, h - mb + 2, gap, 14),
                                     Qt.AlignmentFlag.AlignCenter, f"S{step['strength']}")
                    freq_font = QFont()
                    freq_font.setPixelSize(8)
                    painter.setFont(freq_font)
                    painter.setPen(QPen(QColor(255, 180, 50)))
                    painter.drawText(QRectF(cx - gap / 2, h - mb + 14, gap, 12),
                                     Qt.AlignmentFlag.AlignCenter, f"F{step['freq']}")

                    handle_font = QFont()
                    handle_font.setPixelSize(10)
                    painter.setFont(handle_font)
                    painter.setPen(QPen(QColor(120, 120, 120)))
                    painter.drawText(QRectF(cx - gap / 2, h - mb + 26, gap, 12),
                                     Qt.AlignmentFlag.AlignCenter, "☰")

                if self._reorder_idx >= 0 and self._reorder_target >= 0 and self._reorder_idx != self._reorder_target:
                    target_cx = ml + self._reorder_target * gap + gap / 2
                    painter.setPen(QPen(QColor(255, 100, 100), 2, Qt.PenStyle.DashLine))
                    painter.drawLine(int(target_cx), mt, int(target_cx), h - mb)

                painter.end()

            def _idx_at(self, x):
                ml = 55
                mr = 20
                dw = self.width() - ml - mr
                if not steps:
                    return -1
                gap = dw / len(steps)
                idx = int((x - ml) / gap)
                if 0 <= idx < len(steps):
                    return idx
                return -1

            def _hit_zone(self, x, y):
                ml, mr, mt, mb = 55, 20, 28, 42
                dh = self.height() - mt - mb
                idx = self._idx_at(x)
                if idx < 0:
                    return None, idx
                if y >= self.height() - mb:
                    return "reorder", idx
                step = steps[idx]
                freq_pct = (step["freq"] - 10) / 90.0
                freq_y = self.height() - mb - freq_pct * dh
                if abs(y - freq_y) < 10:
                    return "freq", idx
                return "strength", idx

            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    zone, idx = self._hit_zone(event.position().x(), event.position().y())
                    if idx >= 0:
                        self.selected = idx
                        self._drag_idx = idx
                        self._drag_start_x = event.position().x()
                        self._drag_mode = zone
                        if zone == "strength":
                            self._apply_strength_drag(event.position().y())
                        elif zone == "freq":
                            self._apply_freq_drag(event.position().y())
                        elif zone == "reorder":
                            self._reorder_idx = idx
                            self._reorder_target = idx
                        _update_visuals()
                        _on_select(idx)
                super().mousePressEvent(event)

            def mouseMoveEvent(self, event):
                if self._drag_mode == "strength" and self._drag_idx >= 0:
                    self._apply_strength_drag(event.position().y())
                    _update_visuals()
                elif self._drag_mode == "freq" and self._drag_idx >= 0:
                    self._apply_freq_drag(event.position().y())
                    _update_visuals()
                elif self._drag_mode == "reorder" and self._drag_idx >= 0:
                    target = self._idx_at(event.position().x())
                    if target >= 0:
                        self._reorder_target = target
                    _update_visuals()
                super().mouseMoveEvent(event)

            def mouseReleaseEvent(self, event):
                if self._drag_mode == "reorder" and self._reorder_idx >= 0 and self._reorder_target >= 0:
                    if self._reorder_idx != self._reorder_target:
                        moved = steps.pop(self._reorder_idx)
                        steps.insert(self._reorder_target, moved)
                        self.selected = self._reorder_target
                        _rebuild_step_rows()
                        _on_select(self._reorder_target)
                self._drag_mode = None
                self._drag_idx = -1
                self._reorder_idx = -1
                self._reorder_target = -1
                _update_visuals()
                super().mouseReleaseEvent(event)

            def _apply_strength_drag(self, y):
                mt = 28
                mb = 42
                dh = self.height() - mt - mb
                if dh <= 0:
                    return
                ratio = 1.0 - (y - mt) / dh
                new_strength = max(0, min(100, int(round(ratio * 100))))
                if 0 <= self._drag_idx < len(steps):
                    steps[self._drag_idx]["strength"] = new_strength
                    steps[self._drag_idx]["raw"] = _encode_step(
                        steps[self._drag_idx]["freq"], new_strength)
                    _sync_step_row(self._drag_idx)

            def _apply_freq_drag(self, y):
                mt = 28
                mb = 42
                dh = self.height() - mt - mb
                if dh <= 0:
                    return
                ratio = 1.0 - (y - mt) / dh
                new_freq = max(10, min(100, int(round(10 + ratio * 90))))
                if 0 <= self._drag_idx < len(steps):
                    steps[self._drag_idx]["freq"] = new_freq
                    steps[self._drag_idx]["raw"] = _encode_step(
                        new_freq, steps[self._drag_idx]["strength"])
                    _sync_step_row(self._drag_idx)

        canvas = WaveformCanvas()
        main_layout.addWidget(canvas)

        class FreqDensityWidget(QWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setFixedHeight(50)
                self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            def paintEvent(self, event):
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(20, 20, 25))
                w = self.width()
                h = self.height()
                if not steps:
                    painter.end()
                    return
                n = len(steps)
                total_w = w - 10
                step_w = total_w / n
                max_num_lines = 0
                step_line_counts = []
                for step in steps:
                    period_ms = _v3_freq_to_period(step["freq"])
                    num_bars = max(1, int(100.0 / period_ms))
                    nl = max(2, min(40, num_bars * 2))
                    step_line_counts.append(nl)
                    if nl > max_num_lines:
                        max_num_lines = nl
                global_gap = step_w / max_num_lines if max_num_lines > 0 else step_w
                line_width = max(1, min(2, int(global_gap * 0.7)))
                for i, step in enumerate(steps):
                    strength = step["strength"]
                    nl = step_line_counts[i]
                    density_ratio = min(nl / 40.0, 1.0)
                    x_start = 5 + i * step_w
                    gap = step_w / nl
                    line_h = (strength / 100.0) * (h - 6)
                    y_top = h - 3 - line_h
                    r = int(50 + 200 * density_ratio)
                    g = int(200 - 100 * density_ratio)
                    b = 80
                    painter.setPen(QPen(QColor(r, g, b, 220), line_width))
                    for j in range(nl):
                        lx = x_start + j * gap
                        painter.drawLine(int(lx), int(y_top), int(lx), h - 3)
                painter.end()

        freq_density = FreqDensityWidget()
        main_layout.addWidget(freq_density)

        def _update_visuals():
            canvas.update()
            freq_density.update()

        def _encode_step(freq, strength):
            return self._encode_wave_step(freq, strength)

        selected_info = QHBoxLayout()
        sel_label = QLabel("选中步骤: -")
        freq_spin = QSpinBox()
        freq_spin.setRange(10, 100)
        freq_spin.setPrefix("频率: ")
        str_spin = QSpinBox()
        str_spin.setRange(0, 100)
        str_spin.setPrefix("强度: ")
        selected_info.addWidget(sel_label)
        selected_info.addWidget(freq_spin)
        selected_info.addWidget(str_spin)
        selected_info.addStretch()
        main_layout.addLayout(selected_info)

        freq_spin.setEnabled(False)
        str_spin.setEnabled(False)

        def _on_freq_spin(v):
            idx = canvas.selected
            if 0 <= idx < len(steps):
                steps[idx]["freq"] = v
                steps[idx]["raw"] = _encode_step(v, steps[idx]["strength"])
                _sync_step_row(idx)
                _update_visuals()

        def _on_str_spin(v):
            idx = canvas.selected
            if 0 <= idx < len(steps):
                steps[idx]["strength"] = v
                steps[idx]["raw"] = _encode_step(steps[idx]["freq"], v)
                _sync_step_row(idx)
                _update_visuals()

        freq_spin.valueChanged.connect(_on_freq_spin)
        str_spin.valueChanged.connect(_on_str_spin)

        def _on_select(idx):
            if 0 <= idx < len(steps):
                sel_label.setText(f"选中步骤: {idx}")
                freq_spin.blockSignals(True)
                freq_spin.setValue(steps[idx]["freq"])
                freq_spin.blockSignals(False)
                freq_spin.setEnabled(True)
                str_spin.blockSignals(True)
                str_spin.setValue(steps[idx]["strength"])
                str_spin.blockSignals(False)
                str_spin.setEnabled(True)
                _scroll_to_step(idx)

        step_rows = []

        list_toggle_btn = QPushButton("▶ 步骤列表")
        list_toggle_btn.setFlat(True)
        list_toggle_btn.setStyleSheet("QPushButton { font-weight: bold; font-size: 12px; text-align: left; padding: 4px; }")
        main_layout.addWidget(list_toggle_btn)

        steps_container = QWidget()
        steps_container_layout = QVBoxLayout(steps_container)
        steps_container_layout.setContentsMargins(0, 0, 0, 0)
        steps_container_layout.setSpacing(0)
        steps_container.setVisible(False)

        steps_header = QWidget()
        steps_header_l = QHBoxLayout(steps_header)
        steps_header_l.setContentsMargins(2, 1, 2, 1)
        steps_header_l.setSpacing(4)
        for text, w in [("☰", 22), ("#", 28), ("频率", 90), ("强度", 90), ("HEX", 140), ("", 22)]:
            lbl = QLabel(text)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("color: #888; font-weight: bold; font-size: 10px;")
            steps_header_l.addWidget(lbl)
        steps_header_l.addStretch()
        steps_container_layout.addWidget(steps_header)

        steps_scroll = QScrollArea()
        steps_scroll.setWidgetResizable(True)
        steps_scroll.setMinimumHeight(180)
        steps_scroll_widget = QWidget()
        steps_inner = QVBoxLayout(steps_scroll_widget)
        steps_inner.setSpacing(2)
        steps_inner.setContentsMargins(0, 0, 0, 0)
        steps_scroll.setWidget(steps_scroll_widget)
        steps_container_layout.addWidget(steps_scroll)
        main_layout.addWidget(steps_container)

        def _toggle_list():
            vis = not steps_container.isVisible()
            steps_container.setVisible(vis)
            if vis:
                steps_container.setMaximumHeight(16777215)
            else:
                steps_container.setMaximumHeight(0)
            list_toggle_btn.setText("▼ 步骤列表" if vis else "▶ 步骤列表")

        list_toggle_btn.clicked.connect(_toggle_list)

        def _rebuild_step_rows():
            for sr in step_rows:
                sr["widget"].setParent(None)
                sr["widget"].deleteLater()
            step_rows.clear()

            _list_drag_idx = [-1]
            _list_drag_target = [-1]

            for i, step in enumerate(steps):
                row_w = QWidget()
                row_l = QHBoxLayout(row_w)
                row_l.setContentsMargins(2, 1, 2, 1)
                row_l.setSpacing(4)

                handle_lbl = QLabel("☰")
                handle_lbl.setFixedWidth(22)
                handle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                handle_lbl.setStyleSheet("color: #666; font-size: 11px;")
                handle_lbl.setCursor(Qt.CursorShape.OpenHandCursor)
                row_l.addWidget(handle_lbl)

                idx_lbl = QLabel(f"{i}")
                idx_lbl.setFixedWidth(28)
                idx_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                row_l.addWidget(idx_lbl)

                freq_s = QSpinBox()
                freq_s.setRange(10, 100)
                freq_s.setValue(step["freq"])
                freq_s.setFixedWidth(90)
                row_l.addWidget(freq_s)

                str_s = QSpinBox()
                str_s.setRange(0, 100)
                str_s.setValue(step["strength"])
                str_s.setFixedWidth(90)
                row_l.addWidget(str_s)

                raw_edit = QLineEdit(step["raw"])
                raw_edit.setFixedWidth(140)
                raw_edit.setStyleSheet("font-family: monospace; font-size: 11px;")
                row_l.addWidget(raw_edit)

                del_btn = QPushButton("×")
                del_btn.setFixedWidth(22)
                del_btn.setStyleSheet("color: red;")

                row_l.addStretch()
                steps_inner.addWidget(row_w)

                sr = {"widget": row_w, "freq_spin": freq_s, "str_spin": str_s, "raw_edit": raw_edit, "idx_lbl": idx_lbl, "handle": handle_lbl}

                def _make_freq_cb(idx_i):
                    def cb(v):
                        steps[idx_i]["freq"] = v
                        steps[idx_i]["raw"] = _encode_step(v, steps[idx_i]["strength"])
                        step_rows[idx_i]["raw_edit"].setText(steps[idx_i]["raw"])
                        if canvas.selected == idx_i:
                            freq_spin.blockSignals(True)
                            freq_spin.setValue(v)
                            freq_spin.blockSignals(False)
                        _update_visuals()
                    return cb

                def _make_str_cb(idx_i):
                    def cb(v):
                        steps[idx_i]["strength"] = v
                        steps[idx_i]["raw"] = _encode_step(steps[idx_i]["freq"], v)
                        step_rows[idx_i]["raw_edit"].setText(steps[idx_i]["raw"])
                        if canvas.selected == idx_i:
                            str_spin.blockSignals(True)
                            str_spin.setValue(v)
                            str_spin.blockSignals(False)
                        _update_visuals()
                    return cb

                def _make_raw_cb(idx_i):
                    def cb(text):
                        parsed = self._parse_wave_step(text)
                        if parsed:
                            steps[idx_i]["freq"] = parsed["freq"]
                            steps[idx_i]["strength"] = parsed["strength"]
                            steps[idx_i]["raw"] = text
                            step_rows[idx_i]["freq_spin"].blockSignals(True)
                            step_rows[idx_i]["freq_spin"].setValue(parsed["freq"])
                            step_rows[idx_i]["freq_spin"].blockSignals(False)
                            step_rows[idx_i]["str_spin"].blockSignals(True)
                            step_rows[idx_i]["str_spin"].setValue(parsed["strength"])
                            step_rows[idx_i]["str_spin"].blockSignals(False)
                            if canvas.selected == idx_i:
                                _on_select(idx_i)
                            _update_visuals()
                    return cb

                def _make_del_cb(idx_i):
                    def cb():
                        if len(steps) > 1:
                            steps.pop(idx_i)
                            if canvas.selected >= len(steps):
                                canvas.selected = len(steps) - 1
                            _rebuild_step_rows()
                            _update_visuals()
                    return cb

                freq_s.valueChanged.connect(_make_freq_cb(i))
                str_s.valueChanged.connect(_make_str_cb(i))
                raw_edit.textChanged.connect(_make_raw_cb(i))
                del_btn.clicked.connect(_make_del_cb(i))
                row_l.addWidget(del_btn)

                def _make_handle_mouse_press(idx_i, h_lbl):
                    def cb(event):
                        if event.button() == Qt.MouseButton.LeftButton:
                            _list_drag_idx[0] = idx_i
                            _list_drag_target[0] = idx_i
                            h_lbl.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return cb

                def _make_handle_mouse_release(idx_i, h_lbl):
                    def cb(event):
                        if _list_drag_idx[0] >= 0 and _list_drag_target[0] >= 0:
                            src = _list_drag_idx[0]
                            dst = _list_drag_target[0]
                            if src != dst and 0 <= src < len(steps) and 0 <= dst < len(steps):
                                moved = steps.pop(src)
                                steps.insert(dst, moved)
                                canvas.selected = dst
                                _rebuild_step_rows()
                                _update_visuals()
                        _list_drag_idx[0] = -1
                        _list_drag_target[0] = -1
                        h_lbl.setCursor(Qt.CursorShape.OpenHandCursor)
                    return cb

                def _make_handle_mouse_move(idx_i):
                    def cb(event):
                        if _list_drag_idx[0] == idx_i:
                            global_y = row_w.mapToGlobal(event.position().toPoint()).y()
                            for j, sr2 in enumerate(step_rows):
                                w_y = sr2["widget"].mapToGlobal(QPoint(0, 0)).y()
                                w_h = sr2["widget"].height()
                                if w_y <= global_y <= w_y + w_h:
                                    _list_drag_target[0] = j
                                    break
                    return cb

                handle_lbl.mousePressEvent = _make_handle_mouse_press(i, handle_lbl)
                handle_lbl.mouseReleaseEvent = _make_handle_mouse_release(i, handle_lbl)
                handle_lbl.mouseMoveEvent = _make_handle_mouse_move(i)

                step_rows.append(sr)

            steps_inner.addStretch()

        def _sync_step_row(idx):
            if 0 <= idx < len(step_rows):
                sr = step_rows[idx]
                sr["freq_spin"].blockSignals(True)
                sr["freq_spin"].setValue(steps[idx]["freq"])
                sr["freq_spin"].blockSignals(False)
                sr["str_spin"].blockSignals(True)
                sr["str_spin"].setValue(steps[idx]["strength"])
                sr["str_spin"].blockSignals(False)
                sr["raw_edit"].blockSignals(True)
                sr["raw_edit"].setText(steps[idx]["raw"])
                sr["raw_edit"].blockSignals(False)

        def _scroll_to_step(idx):
            if 0 <= idx < len(step_rows):
                steps_scroll.ensureWidgetVisible(step_rows[idx]["widget"])

        _rebuild_step_rows()

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加步骤")
        add_dup_btn = QPushButton("+ 复制最后一步")

        def on_add():
            steps.append({"freq": 10, "strength": 0, "raw": _encode_step(10, 0)})
            _rebuild_step_rows()
            _update_visuals()

        def on_add_dup():
            if steps:
                last = steps[-1]
                steps.append({"freq": last["freq"], "strength": last["strength"],
                              "raw": last["raw"]})
            else:
                steps.append({"freq": 10, "strength": 0, "raw": _encode_step(10, 0)})
            _rebuild_step_rows()
            _update_visuals()

        add_btn.clicked.connect(on_add)
        add_dup_btn.clicked.connect(on_add_dup)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(add_dup_btn)

        wave_presets = {
            "呼吸": [
                "0A0A0A0A00000000", "0A0A0A0A14141414", "0A0A0A0A28282828",
                "0A0A0A0A3C3C3C3C", "0A0A0A0A50505050", "0A0A0A0A64646464",
                "0A0A0A0A64646464", "0A0A0A0A64646464", "0A0A0A0A00000000",
                "0A0A0A0A00000000", "0A0A0A0A00000000", "0A0A0A0A00000000",
            ],
            "潮汐": [
                "0A0A0A0A00000000", "0B0B0B0B10101010", "0D0D0D0D21212121",
                "0E0E0E0E32323232", "1010101042424242", "1212121253535353",
                "1313131364646464", "151515155C5C5C5C", "1616161654545454",
                "181818184C4C4C4C", "1A1A1A1A44444444", "1A1A1A1A00000000",
                "1B1B1B1B10101010", "1D1D1D1D21212121", "1E1E1E1E32323232",
                "2020202042424242", "2222222253535353", "2323232364646464",
                "252525255C5C5C5C", "2626262654545454", "282828284C4C4C4C",
                "2A2A2A2A44444444", "0A0A0A0A00000000",
            ],
            "冲击": [
                "0A0A0A0A64646464", "1414141464646464", "0A0A0A0A64646464",
                "1414141464646464", "0A0A0A0A50505050", "0A0A0A0A3C3C3C3C",
                "0A0A0A0A28282828", "0A0A0A0A14141414", "0A0A0A0A0A0A0A0A",
            ],
            "渐强": [
                "0A0A0A0A0A0A0A0A", "0A0A0A0A14141414", "0A0A0A0A1E1E1E1E",
                "0A0A0A0A28282828", "0A0A0A0A32323232", "0A0A0A0A3C3C3C3C",
                "0A0A0A0A46464646", "0A0A0A0A50505050", "0A0A0A0A5A5A5A5A",
                "0A0A0A0A64646464",
            ],
        }

        class PresetDelegate(QStyledItemDelegate):
            def paint(self, painter, option, index):
                super().paint(painter, option, index)
                text = index.data()
                bar_start = option.rect.right() - 120
                bar_y = option.rect.y() + 2
                bar_h = option.rect.height() - 4
                preset_lines = wave_presets.get(text, [])
                if not preset_lines:
                    return
                n = len(preset_lines)
                total_w = 110
                step_w = total_w / n
                max_nl = 0
                line_counts = []
                for line in preset_lines:
                    freq_val = self._parse_freq(line)
                    period_ms = _v3_freq_to_period(freq_val) if freq_val else 100
                    nb = max(1, int(100.0 / period_ms))
                    nl = max(2, min(40, nb * 2))
                    line_counts.append(nl)
                    if nl > max_nl:
                        max_nl = nl
                global_gap = step_w / max_nl if max_nl > 0 else step_w
                lw = max(1, min(2, int(global_gap * 0.7)))
                pen = QPen(QColor(100, 180, 80, 200), lw)
                painter.setPen(pen)
                for i, line in enumerate(preset_lines):
                    strength_val = self._parse_strength(line)
                    nl = line_counts[i]
                    gap = step_w / nl
                    density_ratio = min(nl / 40.0, 1.0)
                    r = int(50 + 200 * density_ratio)
                    g = int(200 - 100 * density_ratio)
                    b = 80
                    painter.setPen(QPen(QColor(r, g, b, 200), lw))
                    line_h = (strength_val / 100.0) * bar_h if strength_val else 0
                    y_top = bar_y + bar_h - line_h
                    for j in range(nl):
                        lx = bar_start + i * step_w + j * gap
                        painter.drawLine(int(lx), int(y_top), int(lx), bar_y + bar_h)

            def _parse_freq(self, line):
                try:
                    return int(line[:2], 16)
                except Exception:
                    return None

            def _parse_strength(self, line):
                try:
                    return int(line[8:10], 16)
                except Exception:
                    return None

            def sizeHint(self, option, index):
                return QSize(option.rect.width(), 32)

        preset_label = QLabel("预设:")
        preset_combo = QComboBox()
        preset_combo.setItemDelegate(PresetDelegate())
        for name in wave_presets:
            preset_combo.addItem(name)
        preset_combo.setMinimumWidth(200)
        apply_preset_btn = QPushButton("应用预设")
        export_preset_btn = QPushButton("导出预设")
        import_preset_btn = QPushButton("导入预设")

        def on_apply_preset():
            name = preset_combo.currentText()
            if name in wave_presets:
                steps.clear()
                for ps in wave_presets[name]:
                    parsed = self._parse_wave_step(ps)
                    if parsed:
                        steps.append(parsed)
                canvas.selected = -1
                _rebuild_step_rows()
                _update_visuals()

        def on_export_preset():
            from PyQt6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(dialog, "导出预设", "预设名称:")
            if ok and name.strip():
                name = name.strip()
                wave_presets[name] = [s["raw"] for s in steps]
                if preset_combo.findText(name) < 0:
                    preset_combo.addItem(name)
                preset_combo.setCurrentText(name)

        def on_import_preset():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "导入预设文件", "",
                                                        "JSON 文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content.startswith("Dungeonlab+pulse:"):
                        parsed = self._parse_dungeonlab(content)
                        if parsed:
                            steps.clear()
                            steps.extend(parsed)
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法解析Dungeonlab波形格式")
                    elif content.startswith("{") or content.startswith("["):
                        data = json.loads(content)
                        pulse_list = None
                        if isinstance(data, dict):
                            for key in ["health_pulse", "shield_pulse", "pulse"]:
                                if key in data:
                                    pulse_list = data[key]
                                    break
                            if "name" in data and "steps" in data:
                                pulse_list = data["steps"]
                        elif isinstance(data, list):
                            pulse_list = data
                        if pulse_list and isinstance(pulse_list, list):
                            steps.clear()
                            for line in pulse_list:
                                parsed = self._parse_wave_step(str(line))
                                if parsed:
                                    steps.append(parsed)
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法识别的JSON波形格式")
                    else:
                        lines = [l.strip() for l in content.split('\n') if l.strip()]
                        steps.clear()
                        for line in lines:
                            parsed = self._parse_wave_step(line)
                            if parsed:
                                steps.append(parsed)
                        if steps:
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法解析波形文件")
                except Exception as e:
                    QMessageBox.warning(dialog, "错误", f"导入失败: {e}")

        apply_preset_btn.clicked.connect(on_apply_preset)
        export_preset_btn.clicked.connect(on_export_preset)
        import_preset_btn.clicked.connect(on_import_preset)
        btn_row.addWidget(preset_label)
        btn_row.addWidget(preset_combo)
        btn_row.addWidget(apply_preset_btn)
        btn_row.addWidget(export_preset_btn)
        btn_row.addWidget(import_preset_btn)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        io_row = QHBoxLayout()
        import_dl_btn = QPushButton("导入Dungeonlab波形")
        export_dl_btn = QPushButton("导出Dungeonlab波形")
        import_file_btn = QPushButton("从文件导入")

        def on_import_dl():
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getMultiLineText(dialog, "导入Dungeonlab波形",
                                                      "粘贴Dungeonlab波形文本:", "")
            if ok and text.strip():
                parsed = self._parse_dungeonlab(text.strip())
                if parsed:
                    steps.clear()
                    steps.extend(parsed)
                    canvas.selected = -1
                    _rebuild_step_rows()
                    _update_visuals()
                else:
                    QMessageBox.warning(dialog, "错误", "无法解析Dungeonlab波形格式")

        def on_export_dl():
            dl_text = self._export_dungeonlab(steps)
            from PyQt6.QtWidgets import QInputDialog
            QInputDialog.getMultiLineText(dialog, "导出Dungeonlab波形",
                                           "复制以下文本:", dl_text)

        def on_import_file():
            file_path, _ = QFileDialog.getOpenFileName(dialog, "选择波形文件", "",
                                                        "JSON 文件 (*.json);;文本文件 (*.txt);;所有文件 (*.*)")
            if file_path:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content.startswith("Dungeonlab+pulse:"):
                        parsed = self._parse_dungeonlab(content)
                        if parsed:
                            steps.clear()
                            steps.extend(parsed)
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法解析Dungeonlab波形格式")
                    elif content.startswith("{") or content.startswith("["):
                        data = json.loads(content)
                        pulse_list = None
                        if isinstance(data, dict):
                            for key in ["health_pulse", "shield_pulse", "pulse"]:
                                if key in data:
                                    pulse_list = data[key]
                                    break
                        elif isinstance(data, list):
                            pulse_list = data
                        if pulse_list and isinstance(pulse_list, list):
                            steps.clear()
                            for line in pulse_list:
                                parsed = self._parse_wave_step(str(line))
                                if parsed:
                                    steps.append(parsed)
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法识别的JSON波形格式")
                    else:
                        lines = [l.strip() for l in content.split('\n') if l.strip()]
                        steps.clear()
                        for line in lines:
                            parsed = self._parse_wave_step(line)
                            if parsed:
                                steps.append(parsed)
                        if steps:
                            canvas.selected = -1
                            _rebuild_step_rows()
                            _update_visuals()
                        else:
                            QMessageBox.warning(dialog, "错误", "无法解析波形文件")
                except Exception as e:
                    QMessageBox.warning(dialog, "错误", f"导入失败: {e}")

        import_dl_btn.clicked.connect(on_import_dl)
        export_dl_btn.clicked.connect(on_export_dl)
        import_file_btn.clicked.connect(on_import_file)
        io_row.addWidget(import_dl_btn)
        io_row.addWidget(export_dl_btn)
        io_row.addWidget(import_file_btn)
        io_row.addStretch()
        main_layout.addLayout(io_row)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        wave_bottom_layout = QHBoxLayout()
        wave_top_btn = QPushButton("📌置顶")
        wave_top_btn.setCheckable(True)
        wave_top_btn.setFixedWidth(60)
        wave_top_btn.toggled.connect(lambda checked: dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked) or dialog.show())
        wave_bottom_layout.addWidget(wave_top_btn)
        wave_bottom_layout.addStretch()
        wave_bottom_layout.addWidget(btn_box)
        main_layout.addLayout(wave_bottom_layout)

        def on_accept():
            raw_lines = [s["raw"] for s in steps]
            wave_edit.setText("\n".join(raw_lines))

        btn_box.accepted.connect(on_accept)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)

        dialog.exec()

    def save_config(self):
        config_path = os.path.join(_plugin_dir, 'config.json')
        try:
            def _clean_for_save(obj):
                if isinstance(obj, dict):
                    return {k: _clean_for_save(v) for k, v in obj.items() if not k.startswith('_')}
                elif isinstance(obj, list):
                    return [_clean_for_save(item) for item in obj]
                return obj
            save_data = {"config": _clean_for_save(self.config)}
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "成功", f"配置已保存到:\n{config_path}")
            return True
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
            return False

    def save_and_reload_config(self):
        """保存配置并触发主程序重载"""
        if not self.save_config():
            return

        trigger_file = os.path.join(_plugin_dir, ".reload_trigger")
        try:
            with open(trigger_file, 'w', encoding='utf-8') as f:
                f.write(str(time.time()))
            self.status_label.setText("状态: 配置已保存，已通知主程序重载")
            QMessageBox.information(self, "成功", "配置已保存并通知主程序重载\n主程序将在约1秒内应用新配置")
        except Exception as e:
            self.status_label.setText(f"状态: 配置已保存，但重载通知失败: {e}")
            QMessageBox.warning(self, "警告", f"配置已保存，但无法通知主程序重载:\n{e}")

    def _edit_decay_script(self):
        current_script = self.get_config_value("overlap.decay_script") or ""
        dialog = QDialog(self)
        dialog.setWindowTitle("自定义回落脚本")
        dialog.setMinimumSize(500, 350)
        layout = QVBoxLayout(dialog)

        hint_label = QLabel("可用变量: accumulated(当前累加值), strength_max(最大强度), strength_add(每次增加)\n"
                           "           initial_overlap_time(最初叠加时间), overlap_count(叠加次数)\n"
                           "           last_overlap_time(最后叠加时间), now(当前时间)\n"
                           "可用函数: max, min, abs, int, float, round\n"
                           "需设置 accumulated 为新值")
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint_label)

        code_edit = QPlainTextEdit()
        code_edit.setPlainText(current_script if current_script else "")
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        code_edit.setFont(font)
        code_edit.setStyleSheet("QPlainTextEdit { background-color: #1A1B1D; color: #d4d4d4; }")
        highlighter = PythonSyntaxHighlighter(code_edit.document())
        code_edit.highlighter = highlighter
        code_edit.moveCursor(QTextCursor.MoveOperation.Start)
        layout.addWidget(code_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_script = code_edit.toPlainText()
            self.set_config_value("overlap.decay_script", new_script)

    def _edit_damage_script(self):
        current_script = self.get_config_value("damage_detect.script") or ""
        dialog = QDialog(self)
        dialog.setWindowTitle("自定义受伤程度检测脚本")
        dialog.setMinimumSize(550, 400)
        layout = QVBoxLayout(dialog)

        hint_label = QLabel("可用变量: lost_hp(损失血量), mid_value(血量中间数), max_bonus(强度增幅上限)\n"
                           "可用函数: max, min, abs, int, float, round\n"
                           "需设置 result 为计算出的强度增幅值")
        hint_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(hint_label)

        default_script = (
            "# 默认受伤程度检测公式 (阶段性公式)\n"
            "# lost_hp: 损失血量, mid_value: 血量中间数, max_bonus: 强度增幅上限\n"
            "# 需设置 result 为计算出的强度增幅值\n"
            "\n"
            " if mid_value <= 0 or lost_hp <= 0 or max_bonus <= 0:\n"
            "     result = 0\n"
            " else:\n"
            "     r = min(lost_hp / mid_value, 1.0)\n"
            "     if r < 0.1:\n"
            "         result = max_bonus * 0.2\n"
            "     elif r < 0.5:\n"
            "         t = (r - 0.1) / 0.4\n"
            "         result = max_bonus * (0.2 + t * 0.4)\n"
            "     elif r < 1.0:\n"
            "         t = (r - 0.5) / 0.5\n"
            "         result = max_bonus * (0.6 + t * t * 0.6)\n"
            "     else:\n"
            "         result = max_bonus * 1.2\n"
        )

        code_edit = QPlainTextEdit()
        code_edit.setPlainText(current_script if current_script else default_script)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        code_edit.setFont(font)
        code_edit.setStyleSheet("QPlainTextEdit { background-color: #1A1B1D; color: #d4d4d4; }")
        highlighter = PythonSyntaxHighlighter(code_edit.document())
        code_edit.highlighter = highlighter
        code_edit.moveCursor(QTextCursor.MoveOperation.Start)
        layout.addWidget(code_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_script = code_edit.toPlainText()
            self.set_config_value("damage_detect.script", new_script)

    def _sample_key(self, line_edit):
        from keycodes import capture_next_key, vk_to_name
        self.status_label.setText("状态: 请按下要采样的按键 (5秒超时)...")
        QApplication.processEvents()
        vk, name = capture_next_key(timeout_sec=5)
        if name:
            line_edit.setText(name)
            self.status_label.setText(f"状态: 已采样按键: {name}")
        else:
            self.status_label.setText("状态: 采样超时")

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

                import copy
                from config import _deep_merge, _DEFAULTS

                def _deep_fill_for_import(target, defaults):
                    for key, default_val in defaults.items():
                        if key not in target:
                            target[key] = copy.deepcopy(default_val)
                        elif isinstance(default_val, dict) and isinstance(target.get(key), dict):
                            _deep_fill_for_import(target[key], default_val)

                removed_keys = []
                for section, defaults in _DEFAULTS.items():
                    if section not in plugins_preset:
                        continue
                    preset_section = plugins_preset[section]
                    if isinstance(preset_section, dict) and isinstance(defaults, dict):
                        for key in list(defaults.keys()):
                            if isinstance(defaults[key], dict):
                                for sub_key in defaults[key]:
                                    if sub_key not in preset_section.get(key, {}):
                                        removed_keys.append(f"{section}.{key}.{sub_key}")
                            elif key not in preset_section:
                                removed_keys.append(f"{section}.{key}")

                import_options = QMessageBox.question(
                    self, "导入选项",
                    "要导入全部配置还是仅导入采样点位置和颜色？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if import_options == QMessageBox.StandardButton.Yes:
                    import copy
                    preset_with_defaults = copy.deepcopy(plugins_preset)
                    
                    temp_config = {"plugins": preset_with_defaults}
                    from config import _ensure_defaults
                    temp_config = _ensure_defaults(temp_config)
                    preset_with_defaults = temp_config["plugins"]
                    
                    self.config['plugins'] = preset_with_defaults
                    self.config['cfgFrom'] = file_path
                    waveform_preset = preset_config.get('config', {}).get('waveform', {})
                    if waveform_preset:
                        self.config['waveform'] = waveform_preset
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

                if removed_keys:
                    removed_list = "\n".join(f"• {k}" for k in removed_keys[:15])
                    if len(removed_keys) > 15:
                        removed_list += f"\n... 及其他共 {len(removed_keys)} 项"
                    QMessageBox.information(
                        self, "导入提示",
                        f"以下配置项在预设配置中不存在，已自动填充默认值：\n\n{removed_list}"
                    )

                self.build_config_ui()
                QMessageBox.information(self, "成功", "预制配置已导入，界面已刷新")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def export_config(self):
        def _clean_for_save(obj):
            if isinstance(obj, dict):
                return {k: _clean_for_save(v) for k, v in obj.items() if not k.startswith('_')}
            elif isinstance(obj, list):
                return [_clean_for_save(item) for item in obj]
            return obj

        cfg_from = self.config.get('cfgFrom', '')

        if cfg_from and os.path.exists(cfg_from):
            options = ["导出为JSON", "覆盖原先导入的文件", "删除导入文件来源", "取消"]
            choice, ok = QInputDialog.getItem(
                self, "导出配置",
                f"检测到导入源配置文件:\n{cfg_from}\n\n请选择导出方式:",
                options,
                0,
                False
            )
            if not ok or choice == "取消":
                return

            if choice == "导出为JSON":
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "导出配置为JSON", "", "JSON 文件 (*.json)"
                )
                if file_path:
                    save_data = {"config": _clean_for_save(self._get_export_data())}
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=4)
                    QMessageBox.information(self, "成功", f"配置已导出到:\n{file_path}")

            elif choice == "覆盖原先导入的文件":
                try:
                    save_data = {"config": _clean_for_save(self._get_export_data())}
                    with open(cfg_from, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=4)
                    QMessageBox.information(self, "成功", f"配置已覆盖到原文件:\n{cfg_from}")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"覆盖失败: {e}")

            elif choice == "删除导入文件来源":
                self.config.pop('cfgFrom', None)
                self.build_config_ui()
                QMessageBox.information(self, "成功", "已删除导入文件来源标记")

        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出配置为JSON", "", "JSON 文件 (*.json)"
            )
            if file_path:
                save_data = {"config": _clean_for_save(self._get_export_data())}
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "成功", f"配置已导出到:\n{file_path}")

    def _get_export_data(self):
        import copy
        data = copy.deepcopy(self.config)
        data.pop('cfgFrom', None)
        return data

    def on_process_title_changed(self, text):
        self.set_config_value("game.process_title", text)

    def apply_game_title(self):
        self.game_hwnd = None
        self.bmp_data = None
        self.img_width = 0
        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
        self.status_label.setText(f"状态: 已切换游戏窗口为 '{game_title}'，请进行截图或采样")
        if hasattr(self, '_game_test_timer'):
            self._game_test_timer.start(500)

    def import_game_screenshot(self):
        game_title = self.get_config_value("game.process_title") or "卡拉彼丘"

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择游戏截图", "",
            "BMP 文件 (*.bmp);;图片文件 (*.bmp *.png *.jpg *.jpeg);;所有文件 (*.*)"
        )

        if not file_path:
            return

        if not file_path.lower().endswith('.bmp'):
            reply = QMessageBox.warning(
                self, "格式警告",
                "截图需求无损图片，若不是无损可能造成采样偏差，是否继续",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "错误", f"无法加载图片: {file_path}")
            return

        if self._fake_game_window is not None:
            self._fake_game_window.close()

        self._fake_game_window = GameScreenshotWindow(pixmap, game_title)
        self._fake_game_window.closed.connect(self._on_fake_window_closed)
        self._fake_game_window.show()

        fake_hwnd = int(self._fake_game_window.winId())
        self.game_hwnd = fake_hwnd
        self.bmp_data = None
        self.img_width = 0

        self.status_label.setText(
            f"状态: 已导入游戏截图 ({pixmap.width()}x{pixmap.height()})，窗口标题: {game_title}"
        )

    def _on_fake_window_closed(self):
        self.game_hwnd = None
        self.bmp_data = None
        self.img_width = 0
        self._fake_game_window = None
        self.status_label.setText("状态: 游戏截图窗口已关闭，已恢复默认游戏窗口")

    def full_screenshot(self):
        try:
            game_title = self.get_config_value("game.process_title") or "卡拉彼丘"
            if not self.game_hwnd:
                self.game_hwnd = lib.get_game_window(process_title=game_title)

            if not self.game_hwnd:
                raise Exception(f"未找到游戏窗口 '{game_title}'")

            result = self._do_capture(hwnd=self.game_hwnd)
            if not result or len(result) < 6:
                raise Exception("截图失败")

            bmp_data, rx, ry, rw, rh, img_width = result

            from PIL import Image
            import numpy as np
            import datetime

            buf_size = rw * rh * 4
            raw_data = bytes(bmp_data[:buf_size])
            arr = np.frombuffer(raw_data, dtype=np.uint8).reshape((rh, rw, 4))
            rgb_arr = arr[:, :, 2::-1].copy()
            qimage = QImage(rgb_arr.tobytes(), rw, rh, rw * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)

            screenshot_dir = os.path.join(_plugin_dir, "screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(screenshot_dir, f"full_screenshot_{rw}x{rh}_{timestamp}.bmp")

            bgra_data = bytes(bmp_data[:rw * rh * 4])
            bmp_file_data = lib.create_bmp_from_bgra(bgra_data, rw, rh)

            if bmp_file_data is None:
                raise Exception("BMP编码失败")

            with open(save_path, 'wb') as f:
                f.write(bmp_file_data)

            dialog = ScreenshotDialog(pixmap, self)
            dialog.setWindowTitle(f"完整截图 ({rw}x{rh}) 已保存")
            dialog.exec()
            self.status_label.setText(f"状态: 完整截图已保存 ({rw}x{rh}): {save_path}")

        except ImportError:
            QMessageBox.warning(self, "错误", "截图功能需要安装 PIL 和 numpy 库\n请运行: pip install pillow numpy")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"完整截图失败: {e}")
            self.status_label.setText(f"状态: 完整截图出错 - {e}")


def main():
    app = QApplication(sys.argv)
    window = ConfigTool()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
