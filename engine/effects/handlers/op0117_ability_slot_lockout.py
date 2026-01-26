from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(117)
class H_Prop117_AbilitySlotLockout:
    PROP_ID = 117

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: Index,LockDuration,,,,
        idx = int(args.get("index", 0))
        dur = int(args.get("lock_duration", args.get("lockduration", 0)))
        if not hasattr(ctx, "teams") or ctx.teams is None:
            ctx.log.unsupported(effect_row, reason="TEAM_MANAGER_MISSING")
            return EffectResult(executed=False)
        ctx.teams.lock_slot(getattr(target, "id", 0), idx, dur)
        ctx.log.effect_result(effect_row, actor, target, code="SLOT_LOCK", reason=f"slot={idx},dur={dur}")
        return EffectResult(executed=True, notes={"slot": idx, "dur": dur})
