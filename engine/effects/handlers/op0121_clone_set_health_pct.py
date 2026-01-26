from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(121)
class H_Prop121_CloneSetHealthPct:
    """Clone: set clone health/max health from a percentage.

    Pack schema: HealthPercentage

    Notes:
      - The engine skeleton does not fully model spawned "clone" pets as
        separate actors. However, DB2 exposes a set of clone-related states
        (Clone_Health, Clone_MaxHealth, etc.). This opcode is therefore
        implemented as a state write so that downstream logic (or future
        extensions) can build on it deterministically.
      - Observed usage in this pack: Split / Magical Clone / Hatch variants.
    """

    PROP_ID = 121

    # BattlePetState IDs from pack (see data/petbattle_ability_pack...):
    _STATE_CLONE_HEALTH = 105
    _STATE_CLONE_MAX_HEALTH = 106

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Param is a percentage of the actor's max health.
        pct = int(args.get("health_percentage", 0) or 0)
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

        max_hp = int(getattr(actor, "max_hp", 0) or 0)
        # If actor doesn't expose max_hp (edge-case in tests), fall back to hp.
        if max_hp <= 0:
            max_hp = int(getattr(actor, "hp", 0) or 0)

        clone_max = int(max_hp * pct / 100)
        if clone_max < 0:
            clone_max = 0

        # Store on actor: the clone is conceptually "owned" by the caster.
        try:
            pid = int(getattr(actor, "id", 0) or 0)
            ctx.states.set(pid, self._STATE_CLONE_MAX_HEALTH, clone_max)
            ctx.states.set(pid, self._STATE_CLONE_HEALTH, clone_max)
        except Exception:
            # Fail closed: keep battle running.
            pass

        ctx.log.effect_result(effect_row, actor, target, code="CLONE_HP_PCT", reason=str(pct))
        return EffectResult(executed=True, notes={"health_percentage": pct, "clone_max_health": clone_max})
