from __future__ import annotations

import math


class SkillMath:
    """Shared math helpers for ability "panel" values.

    In WoW pet battles, many damage/heal effects use a base "points" value from
    the script tables and scale it by the caster's power.

    The engine's runtime pipeline implements additional modifiers (type advantage,
    weather, variance, critical strikes, etc.). For Pet management and UI/RL
    feature extraction, it is useful to have the deterministic base value.
    """

    @staticmethod
    def panel_value(points: int, power: int) -> int:
        """Compute the deterministic panel value.

        Formula:
            floor(points * (20 + power) / 20)
        """
        pts = float(int(points))
        p = float(int(power))
        return int(math.floor(pts * (20.0 + p) / 20.0))
