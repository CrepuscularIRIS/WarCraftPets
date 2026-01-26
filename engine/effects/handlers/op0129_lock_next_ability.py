from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(129)
class H_Prop129_LockNextAbility:
    PROP_ID = 129

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: LockDuration,,,,,
        dur = int(args.get("lock_duration", args.get("lockduration", 0)))
        if not hasattr(ctx, "teams") or ctx.teams is None:
            ctx.log.unsupported(effect_row, reason="TEAM_MANAGER_MISSING")
            return EffectResult(executed=False)
        ctx.teams.lock_next_ability(getattr(target, "id", 0), dur)
        ctx.log.effect_result(effect_row, actor, target, code="LOCK_NEXT", reason=f"dur={dur}")
        return EffectResult(executed=True, notes={"dur": dur})
