from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(32)
class H_Prop32_PostDamageLifesteal:
    PROP_ID = 32

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: Points,Accuracy,ChainFailure
        points = int(args.get("points", 0))  # interpret as percent of last damage (100 => 100%)
        accuracy = args.get("accuracy", 1)
        cf = int(args.get("chain_failure", args.get("chainfailure", 0)))

        # Gate on last damage dealt > 0
        last = getattr(ctx.acc_ctx, "last_damage_dealt", 0)
        if int(last) <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NO_LAST_DAMAGE", reason="last_damage_dealt<=0")
            return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        # Hit check (most rows are 100% but keep it correct)
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        heal_amt = int(int(last) * (points / 100.0))
        if heal_amt <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="ZERO_HEAL", reason="computed<=0")
            return EffectResult(executed=False, flow_control="STOP_TURN" if cf else "CONTINUE")

        ctx.apply_heal(actor, heal_amt, trace={"op32_points_pct": points, "last_damage": int(last)})
        ctx.log.heal(effect_row, actor, actor, heal_amt, trace={"op32_points_pct": points, "last_damage": int(last)})
        return EffectResult(executed=True, notes={"heal": heal_amt, "points_pct": points})
