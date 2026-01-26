from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(107)
class H_Prop107_ForceSwapRandom:
    PROP_ID = 107

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: Accuracy
        accuracy = args.get("accuracy", 1)

        if not hasattr(ctx, "teams") or ctx.teams is None:
            ctx.log.unsupported(effect_row, reason="TEAM_MANAGER_MISSING")
            return EffectResult(executed=False)

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        ok, why, new_pid = ctx.teams.force_swap_random(getattr(target, "id", 0), ctx, ignore_swap_out_lock=True)
        if not ok:
            ctx.log.effect_result(effect_row, actor, target, code="FORCE_SWAP_FAIL", reason=why)
            return EffectResult(executed=False)

        # Log as a generic effect_result to avoid expanding log schema.
        ctx.log.effect_result(effect_row, actor, target, code="FORCE_SWAP_OK", reason=f"new_active={new_pid}")
        return EffectResult(executed=True, notes={"new_active_pet_id": int(new_pid)})
