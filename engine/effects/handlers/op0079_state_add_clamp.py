from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(79)
class H_Prop79_StateAddClamp:
    """Add to a state and clamp between min/max.

    DB2 ParamLabel: State,StateChange,StateMin,StateMax,,
    """

    PROP_ID = 79

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        state_id = int(args.get("state", 0) or 0)
        delta = int(args.get("state_change", args.get("statechange", 0)) or 0)
        smin = int(args.get("state_min", args.get("statemin", 0)) or 0)
        smax = int(args.get("state_max", args.get("statemax", 0)) or 0)

        sm = getattr(ctx, "states", None)
        owner_id = int(getattr(target, "id", 0) or 0)
        old = 0
        if sm is not None:
            try:
                old = int(sm.get(owner_id, state_id, 0) or 0)
            except Exception:
                old = 0

        new = int(old + delta)
        # Clamp when a bound is provided. Note: bounds may legitimately be 0.
        if smin or smax:
            if smax and new > smax:
                new = int(smax)
            if smin and new < smin:
                new = int(smin)

        if sm is not None:
            try:
                sm.set(owner_id, state_id, int(new))
            except Exception:
                pass

        if hasattr(ctx, "log"):
            ctx.log.state_set(effect_row, actor, target, int(state_id), int(new))

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        return EffectResult(executed=True, notes={"code": "STATE_ADD_CLAMP", "state": int(state_id), "old": int(old), "new": int(new)})
