"""
overlay.py - 悬浮窗模块

特性:
- 固定宽度列布局，变长文本不影响旁边x位置
- 中文标签
- tkinter 无边框置顶透明窗口
- 白色文字 + 右下阴影描边
- 尝试加载 HarmonyOS Sans 字体
"""

import tkinter as tk
import threading
import time
import os


_OVERLAY_FONT_FAMILY = "Microsoft YaHei"
try:
    _font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HarmonyOS_Sans_SC_Regular.ttf")
    if os.path.exists(_font_path):
        import tkinter.font as tkfont
        tkfont.addfont(_font_path)
        _OVERLAY_FONT_FAMILY = "HarmonyOS Sans SC"
except Exception:
    pass

_SHADOW_COLOR = "#333333"


class OverlayWindow:
    def __init__(self, gs_ref, get_monitoring_attrs, get_overlap_processor):
        self.gs = gs_ref
        self._get_attrs = get_monitoring_attrs
        self._get_overlap = get_overlap_processor
        self.root = None
        self.visible = True
        self._bottom_canvas = None
        self._trigger_message = ""
        self._trigger_show_until = 0

    def create(self, toggle_event, setting_event, stop_event, on_log=None):
        self._toggle_event = toggle_event
        self._setting_event = setting_event
        self._stop_event = stop_event
        self._log = on_log or print

        self.root = tk.Tk()
        self.root.title("HitElectric")
        self.root.geometry("+10+10")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black')
        self.root.configure(bg='black')

        main_frame = tk.Frame(self.root, bg='black')
        main_frame.pack(fill=tk.X, anchor='w')

        self._top_canvas = tk.Canvas(main_frame, width=1100, height=22, bg='black', highlightthickness=0)
        self._top_canvas.pack(fill=tk.X, anchor='w')

        self._bottom_canvas = tk.Canvas(main_frame, width=1100, height=28, bg='black', highlightthickness=0)
        self._bottom_canvas.pack(fill=tk.X, anchor='w')

        self._top_layout = [
            ("method", 0),
            ("healthbar", 50),
            ("spectating", 110),
            ("health", 170),
            ("shield", 240),
            ("delay", 310),
            ("strength", 650),
            ("overlap", 850),
            ("debug", 920),
        ]

        self.gs.overlay_hwnd = self.root
        self._log("悬浮窗已创建")

        self._refresh()

        self._update_loop()
        try:
            self.root.mainloop()
        except Exception as e:
            self._log(f"悬浮窗主循环出错: {e}")
        finally:
            self.gs.overlay_hwnd = None

    def _update_loop(self):
        try:
            if self._stop_event.is_set():
                try:
                    self.root.destroy()
                except Exception:
                    pass
                return

            try:
                if self._toggle_event.is_set():
                    self._toggle_event.clear()
                    self.visible = not self.visible
                    try:
                        if self.visible:
                            self.root.deiconify()
                        else:
                            self.root.withdraw()
                    except Exception:
                        pass

                if self.gs.overlay_update_event.is_set():
                    self.gs.overlay_update_event.clear()
                    self._refresh()

                if self._setting_event.is_set():
                    self._setting_event.clear()
                    self._refresh()
            except Exception:
                pass

            self.root.after(80, self._update_loop)
        except Exception:
            try:
                self.root.after(80, self._update_loop)
            except Exception:
                pass

    def _draw_text_outline(self, canvas, x, y, text, fill="white", outline=_SHADOW_COLOR, font=None):
        if not text:
            return
        if font is None:
            font = (_OVERLAY_FONT_FAMILY, 10, 'bold')
        for dx in range(1, 3):
            for dy in range(1, 3):
                canvas.create_text(x + dx, y + dy, text=text, fill=outline, font=font, anchor='w')
        canvas.create_text(x, y, text=text, fill=fill, font=font, anchor='w')

    def _refresh(self):
        try:
            gs = self.gs
            attrs = self._get_attrs()
            overlap = self._get_overlap()

            method = gs.capture_method
            hp_bar = "y" if gs.has_healthbar else "n"
            spc = "y" if gs.is_spectating else "n"
            health_val = f"{gs.current_health:.0f}"
            shield_val = f"{gs.current_shield:.0f}"

            capture_ms = attrs.get('last_capture_time', 0)
            ocr_ms = attrs.get('ocr_total_time', 0) * 1000
            filter_ms = attrs.get('filter_total_time', 0) * 1000
            delay_parts = [f"{capture_ms:.1f}ms"]
            if filter_ms > 0:
                delay_parts.append(f"+{filter_ms:.1f}ms(滤镜)")
            if ocr_ms > 0:
                delay_parts.append(f"+{ocr_ms:.0f}ms(ocr)")
            delay_str = "Delay:" + " ".join(delay_parts)

            if gs.electric_trigger_message:
                self._trigger_message = gs.electric_trigger_message
                self._trigger_show_until = time.time() + 3.0
                gs.electric_trigger_message = ""

            trigger_text = ""
            if self._trigger_message and time.time() < self._trigger_show_until:
                trigger_text = f"⚡{self._trigger_message}"
            else:
                self._trigger_message = ""

            targets = ["health_a", "health_b", "shield_a", "shield_b"]
            parts = []
            for i, t in enumerate(targets):
                v = gs.strength_values[t]
                if gs.setting_mode and i == gs.setting_target:
                    parts.append(f">{v}<")
                else:
                    parts.append(f"{v}")
            strength_str = f"A:{parts[0]} B:{parts[1]} | S:{parts[2]} {parts[3]}"
            if gs.setting_mode:
                strength_str += " ⚙"

            plus_result = attrs.get('plus_result', '')
            spectate_result = attrs.get('spectate_result', '')
            health_color = attrs.get('health_color_result', '0')
            shield_color = attrs.get('shield_color_result', '0')
            debug_str = f"{plus_result},{spectate_result},{health_color},{shield_color}"

            col_map_top = {
                "method": f"[{method}]",
                "healthbar": f"血条:{hp_bar}",
                "spectating": f"观战:{spc}",
                "health": f"血:{health_val}",
                "shield": f"盾:{shield_val}",
                "delay": delay_str,
                "strength": strength_str,
                "overlap": f"ovlp:{overlap.accumulated:.1f}",
                "debug": debug_str,
            }

            self._top_canvas.delete("all")
            top_font = (_OVERLAY_FONT_FAMILY, 8, 'bold')

            for col_key, x_pos in self._top_layout:
                text = col_map_top.get(col_key, "")
                self._draw_text_outline(self._top_canvas, x_pos, 10, text, font=top_font)

            self._bottom_canvas.delete("all")
            font = (_OVERLAY_FONT_FAMILY, 10, 'bold')
            self._draw_text_outline(self._bottom_canvas, 0, 12, trigger_text, font=font)

            install_status = getattr(gs, 'install_status', '')
            install_status_until = getattr(gs, 'install_status_until', 0)
            if install_status and time.time() < install_status_until:
                self._draw_text_outline(self._bottom_canvas, 0, 12, install_status, fill="#FFD700", font=font)

        except Exception as e:
            try:
                self._log(f"悬浮窗刷新错误: {e}")
            except Exception:
                pass

    def destroy(self):
        try:
            self.root.destroy()
        except Exception:
            pass
