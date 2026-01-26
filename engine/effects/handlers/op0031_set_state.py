from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

STATE_DISPEL_ALL_AURAS = 141

@register_handler(31)
class H_Prop31_SetState:
    PROP_ID = 31

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel in DB2: "State,StateValue"
        state_id = int(args.get("state", 0))
        value = int(args.get("state_value", args.get("statevalue", 0)))

        # Store state on target for downstream systems (UI/RL/conditional effects)
        sm = getattr(ctx, "states", None)
        if sm is not None:
            sm.set(getattr(target, "id", 0), state_id, value)
        if hasattr(ctx, "log"):
            ctx.log.state_set(effect_row, actor, target, state_id, value)

        # Best-effort runtime stat sync (so pet.power/max_hp/... reflect new state).
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        # Special-case: dispel all auras when toggled ON.
        if state_id == STATE_DISPEL_ALL_AURAS and value == 1 and hasattr(ctx, "aura"):
            owner_id = int(getattr(target, "id", 0))
            current = ctx.aura.list_owner(owner_id)
            removed = 0
            for aura_id in list(current.keys()):
                ctx.aura.remove(owner_id, aura_id)
                removed += 1
                if hasattr(ctx, "log"):
                    ctx.log.aura_remove(owner_id, aura_id, reason="STATE141_DISPEL")
            if hasattr(ctx, "log"):
                ctx.log.dispel(effect_row, actor, target, removed, reason="STATE141_DISPEL")
            return EffectResult(executed=True, notes={"code": "STATE_DISPEL_ALL", "removed": removed})

        return EffectResult(executed=True, notes={"code": "STATE_SET", "state": state_id, "value": value})
