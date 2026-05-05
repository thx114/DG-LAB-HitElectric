"""
HitElectricLogic.py - 挨打就电 判断辅助库

提供模块化的判断逻辑，供主程序调用。
所有函数均为纯逻辑函数，通过参数传入配置，通过返回值传递结果。
"""


# ============================================================
# 受伤程度检测模块
# ============================================================

def calculate_damage_bonus(lost_hp, mid_value, max_bonus):
    """
    计算受伤程度检测的强度增幅

    阶段性公式:
    - 轻伤(r<10%): max_bonus * 0.2
    - 中伤(10%-50%): 线性过渡
    - 重伤(50%-100%): 二次曲线加速
    - 极限伤(r>=100%): max_bonus * 1.2
    """
    if mid_value <= 0 or lost_hp <= 0 or max_bonus <= 0:
        return 0

    r = min(lost_hp / mid_value, 1.0)

    if r < 0.1:
        return max_bonus * 0.2
    elif r < 0.5:
        t = (r - 0.1) / 0.4
        return max_bonus * (0.2 + t * 0.4)
    elif r < 1.0:
        t = (r - 0.5) / 0.5
        return max_bonus * (0.6 + t * t * 0.6)
    else:
        return max_bonus * 1.2


class DamageDetector:
    """
    受伤程度检测模块

    使用全局变量:
    - damage_bonus: 写入计算出的强度增幅
    - cached_config: 读取 damage_enabled, damage_mid_value, damage_max_bonus, damage_formula, damage_script
    """

    def __init__(self, config_getter):
        self._cfg = config_getter

    def apply(self, lost_hp, extra_hp=0):
        """计算受伤增幅并返回 damage_bonus 值"""
        if not self._cfg("damage_enabled", False):
            return 0
        total_lost = lost_hp + extra_hp
        if total_lost <= 0:
            return 0
        formula = self._cfg("damage_formula", "default")
        mid_value = self._cfg("damage_mid_value", 5000)
        max_bonus = self._cfg("damage_max_bonus", 10)
        if formula == "script":
            return self._run_script(total_lost, mid_value, max_bonus)
        return calculate_damage_bonus(total_lost, mid_value, max_bonus)

    def _run_script(self, lost_hp, mid_value, max_bonus):
        script = self._cfg("damage_script", "")
        if not script:
            return calculate_damage_bonus(lost_hp, mid_value, max_bonus)
        try:
            safe_builtins = {
                "max": max, "min": min, "abs": abs, "int": int,
                "float": float, "round": round, "len": len,
                "True": True, "False": False, "None": None,
            }
            local_vars = {
                "lost_hp": lost_hp,
                "mid_value": mid_value,
                "max_bonus": max_bonus,
                "result": 0,
            }
            exec(script, {"__builtins__": safe_builtins}, local_vars)
            result = local_vars.get("result", 0)
            return max(0, float(result))
        except Exception:
            return 0


# ============================================================
# Overlap 叠加模块
# ============================================================

class OverlapProcessor:
    """
    Overlap 叠加处理模块

    管理 overlap 累加、衰减、上限规则。
    支持5种自然回落模式: instant, linear, percent, ratio_accel, script
    """

    DECAY_MODES = ("instant", "linear", "percent", "ratio_accel", "script")

    def __init__(self, config_getter):
        self._cfg = config_getter
        self.accumulated = 0
        self.active_until = 0.0
        self.base_until = 0.0
        self._decay_script_fn = None
        self._initial_overlap_time = 0.0
        self._last_overlap_time = 0.0
        self._overlap_count = 0

    def reset_if_expired(self, now):
        """如果不在 overlap 时间内，根据回落模式处理累加值"""
        if now >= self.base_until:
            if not self._cfg("overlap_decay_enabled", False):
                self.accumulated = 0
                self._initial_overlap_time = 0.0
                self._last_overlap_time = 0.0
                self._overlap_count = 0
                return
            mode = self._cfg("overlap_decay_mode", "instant")
            if mode == "instant":
                self.accumulated = 0
                self._initial_overlap_time = 0.0
                self._last_overlap_time = 0.0
                self._overlap_count = 0
            elif mode in ("linear", "percent", "ratio_accel", "script"):
                pass
            else:
                self.accumulated = 0
                self._initial_overlap_time = 0.0
                self._last_overlap_time = 0.0
                self._overlap_count = 0

    def apply_decay(self, now):
        """在每帧调用，处理自然回落"""
        if not self._cfg("overlap_decay_enabled", False):
            return
        if self.accumulated <= 0:
            return
        if now < self.base_until:
            return

        mode = self._cfg("overlap_decay_mode", "instant")
        if mode == "instant":
            self.accumulated = 0
        elif mode == "linear":
            decay_val = self._cfg("overlap_decay_value", 1)
            self.accumulated = max(0, self.accumulated - decay_val)
        elif mode == "percent":
            decay_pct = self._cfg("overlap_decay_percent", 10)
            self.accumulated = max(0, self.accumulated * (1 - decay_pct / 100.0))
            if self.accumulated < 0.5:
                self.accumulated = 0
        elif mode == "ratio_accel":
            overlap_max = self._cfg("overlap_strength_max", 200)
            accel_factor = self._cfg("overlap_decay_ratio_accel", 0.5)
            if overlap_max > 0:
                ratio = self.accumulated / overlap_max
                decay_amount = max(0.1, ratio * accel_factor * overlap_max * 0.05)
                self.accumulated = max(0, self.accumulated - decay_amount)
            else:
                self.accumulated = 0
        elif mode == "script":
            self._run_decay_script()

    def _run_decay_script(self):
        script = self._cfg("overlap_decay_script", "")
        if not script:
            self.accumulated = 0
            return
        try:
            safe_builtins = {
                "max": max, "min": min, "abs": abs, "int": int,
                "float": float, "round": round, "len": len,
                "True": True, "False": False, "None": None,
            }
            local_vars = {
                "accumulated": self.accumulated,
                "strength_max": self._cfg("overlap_strength_max", 200),
                "strength_add": self._cfg("overlap_strength_add", 1),
                "initial_overlap_time": self._initial_overlap_time,
                "overlap_count": self._overlap_count,
                "last_overlap_time": self._last_overlap_time,
                "now": now,
            }
            exec(script, {"__builtins__": safe_builtins}, local_vars)
            result = local_vars.get("accumulated", 0)
            self.accumulated = max(0, float(result))
        except Exception as e:
            self.accumulated = 0

    def is_overlap(self, now):
        if self._cfg("overlap_decay_enabled", False):
            return self.accumulated > 0
        return now < self.base_until

    def compute(self, now, base_strength, damage_bonus):
        """
        计算 overlap 叠加

        Returns:
            (overlap_add, total_add, proximity, damage_bonus_after_weaken)
        """
        overlap_max = self._cfg("overlap_strength_max", 200)
        current_total = base_strength + self.accumulated + damage_bonus
        proximity = min(current_total / overlap_max, 1.0) if overlap_max > 0 else 0

        total_add = damage_bonus
        overlap_add = 0

        if self.is_overlap(now) and self._cfg("overlap_enabled", True):
            overlap_add_base = self._cfg("overlap_strength_add", 1)
            overlap_add = overlap_add_base * (1.0 - proximity)
            self.accumulated += overlap_add
            total_add += self.accumulated
            if self._initial_overlap_time == 0.0:
                self._initial_overlap_time = now
            self._last_overlap_time = now
            self._overlap_count += 1

        damage_bonus_out = damage_bonus
        if self._cfg("damage_enabled", False) and damage_bonus > 0:
            max_bonus = self._cfg("damage_max_bonus", 10)
            cap = max_bonus * 1.2
            if damage_bonus + self.accumulated > cap:
                excess = damage_bonus + self.accumulated - cap
                weaken_amount = min(damage_bonus, excess)
                damage_bonus_out = damage_bonus - weaken_amount * 0.75
                total_add = damage_bonus_out + self.accumulated

        return overlap_add, total_add, proximity, damage_bonus_out

    def update_timing(self, now, pulse_duration, proximity):
        """更新 overlap 时间"""
        duration_mult_base = self._cfg("overlap_duration_multiplier", 1.5)
        duration_mult = 1.0 + (duration_mult_base - 1.0) * (1.0 - proximity)
        self.base_until = now + pulse_duration
        self.active_until = now + pulse_duration * duration_mult

    def format_log(self, damage_bonus, overlap_add, total_add, strength_a, strength_b):
        """格式化强度增幅日志"""
        if total_add <= 0:
            return None
        parts = []
        if damage_bonus > 0:
            parts.append(f"dmg+{damage_bonus:.0f}")
        if self.accumulated > 0:
            parts.append(f"ovlp+{self.accumulated:.0f}")
        if parts:
            return f"bonus: {', '.join(parts)} | total+{total_add:.0f} | str A:{strength_a:.0f} B:{strength_b:.0f}"
        return None


# ============================================================
# 触发条件判断模块
# ============================================================

class TriggerConditions:
    """
    触发条件判断模块

    提供各种触发条件的链式判断，每个方法返回 (should_trigger, debug_msg)
    """

    def __init__(self, config_getter, debug_func):
        self._cfg = config_getter
        self._debug = debug_func

    def shield_blocks_health(self, current_shield):
        """盾存在时阻止血量电击"""
        if self._cfg("shield_blocks_health", True) and current_shield > 0:
            return True, f"盾存在时阻止血量电击 (盾={current_shield})"
        return False, ""

    def drop_threshold(self, bar_type, drop_amount, should_trigger):
        """掉落阈值检测"""
        if not should_trigger:
            return False, ""
        threshold = self._cfg(f"{bar_type}_drop_threshold", 0)
        if threshold > 0 and drop_amount < threshold:
            return False, f"{bar_type}减少{drop_amount:.0f}未达阈值{threshold}, 跳过电击"
        return True, ""

    def immune_check(self, multi_char_enabled, switch_immunity_frames,
                     healthbar_appear_immunity, switch_value_unchanged, pending_switch_index):
        """免疫检测"""
        if not multi_char_enabled:
            return False
        if switch_immunity_frames > 0 or healthbar_appear_immunity or switch_value_unchanged or pending_switch_index >= 0:
            return True
        return False


# ============================================================
# OCR 验证模块
# ============================================================

class OCRValidator:
    """OCR 数值验证模块，处理可疑变化"""

    SUSPECT_THRESHOLD = 2

    def __init__(self):
        self._suspect = {"health": False, "shield": False}
        self._suspected_value = {"health": None, "shield": None}
        self._suspect_count = {"health": 0, "shield": 0}

    def validate(self, value_type, new_value, old_value):
        """
        验证 OCR 数值是否可信

        Returns:
            (is_valid, final_value)
        """
        if old_value is None or new_value is None:
            return True, new_value
        if old_value <= 0:
            return True, new_value

        if not self._suspect[value_type]:
            return self._check_new_suspect(value_type, new_value, old_value)
        else:
            return self._check_existing_suspect(value_type, new_value, old_value)

    def _check_new_suspect(self, value_type, new_value, old_value):
        if new_value == 0:
            return True, new_value

        old_str = str(old_value)
        new_str = str(new_value)
        if len(new_str) < len(old_str) and old_str.endswith(new_str):
            self._set_suspect(value_type, new_value, 1)
            return False, old_value

        return True, new_value

    def _check_existing_suspect(self, value_type, new_value, old_value):
        if new_value == self._suspected_value[value_type]:
            self._suspect_count[value_type] += 1
            if self._suspect_count[value_type] >= self.SUSPECT_THRESHOLD:
                self._clear_suspect(value_type)
                return True, new_value
            return False, old_value
        else:
            self._clear_suspect(value_type)
            return True, new_value

    def _set_suspect(self, value_type, value, count):
        self._suspect[value_type] = True
        self._suspected_value[value_type] = value
        self._suspect_count[value_type] = count

    def _clear_suspect(self, value_type):
        self._suspect[value_type] = False
        self._suspected_value[value_type] = None
        self._suspect_count[value_type] = 0
