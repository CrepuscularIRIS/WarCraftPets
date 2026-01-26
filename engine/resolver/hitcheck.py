from dataclasses import dataclass
from typing import Any, Tuple

from engine.constants.weather import get_weather_effect

@dataclass
class HitCheck:
    rng: Any
    stats: Any = None
    weather: Any = None

    # BattlePetState IDs (DB2) used for accuracy/evasion.
    #  - 41: Stat_Accuracy
    #  - 73: Stat_Dodge
    _STATE_STAT_ACCURACY: int = 41
    _STATE_STAT_DODGE: int = 73

    def compute(self, ctx: Any, actor: Any, target: Any, accuracy: Any, dont_miss: bool = False) -> Tuple[bool, str]:
        if dont_miss:
            return True, "DONT_MISS"

        # Accuracy override context (Prop145/139): when set, it overrides the
        # per-effect Accuracy parameter for the remainder of the current turn.
        override = None
        try:
            override = getattr(getattr(ctx, "acc_ctx", None), "accuracy_override", None)
        except Exception:
            override = None

        acc = float(override) if override is not None else (float(accuracy) if accuracy is not None else 1.0)
        # DB2 exports typically use 0..100; normalize to 0..1
        if acc > 1.0:
            acc = acc / 100.0
        # Apply accuracy modifiers.
        if self.stats is not None and ctx is not None:
            try:
                a_id = int(getattr(actor, "id", 0) or 0)
                t_id = int(getattr(target, "id", 0) or 0)
                acc += float(self.stats.sum_state(ctx, a_id, self._STATE_STAT_ACCURACY)) / 100.0
                acc -= float(self.stats.sum_state(ctx, t_id, self._STATE_STAT_DODGE)) / 100.0
            except Exception:
                pass

        # Apply weather hit chance additive.
        if self.weather is not None and ctx is not None:
            try:
                wid = int(getattr(self.weather, "current", lambda _ctx: 0)(ctx))
                we = get_weather_effect(wid)
                if we is not None and float(we.hit_chance_add) != 0.0:
                    # Elementals ignore negative weather effects.
                    actor_type = int(getattr(actor, "pet_type", -1) or -1)
                    if not (actor_type == 6 and float(we.hit_chance_add) < 0.0):
                        acc += float(we.hit_chance_add)
            except Exception:
                pass

        # Clamp
        if acc < 0.0:
            acc = 0.0
        if acc > 1.0:
            acc = 1.0

        r = self.rng.rand_hit()  # always consume for determinism
        if acc <= 0.0:
            return False, "MISS"
        hit = (r <= acc)
        return hit, ("HIT" if hit else "MISS")


