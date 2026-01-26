from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(25)
class H_Prop25_TrapAttempt:
    """
    Prop25 is used by Trap abilities (capture mechanics) in the pet battle data.

    Param schema (from pack):
      - BaseChanceToSucceed (u8_pct)
      - IncreasePerToss (i32)

    This engine focuses on battle simulation; capture is out-of-scope for win/lose
    resolution. We therefore implement Prop25 as an evolvable, non-destructive
    mechanic:
      - Track "trap tosses" in ctx.acc_ctx.trap_toss_count (battle-global).
      - Compute success chance = clamp(base + inc * toss_index, 0..100).
      - Roll against ctx.rng.rand_gate().
      - Expose the result via EffectResult.notes and ctx.acc_ctx.trap_last_*.

    No battle termination is performed here.
    """
    PROP_ID = 25

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        base = float(args.get("base_chance_to_succeed", 0))
        inc = float(args.get("increase_per_toss", 0))

        toss_index = int(getattr(ctx.acc_ctx, "trap_toss_count", 0))
        chance_pct = base + inc * toss_index
        if chance_pct < 0:
            chance_pct = 0.0
        if chance_pct > 100:
            chance_pct = 100.0

        roll = float(ctx.rng.rand_gate())
        success = roll < (chance_pct / 100.0)

        # persist on context for downstream debugging/telemetry
        try:
            ctx.acc_ctx.trap_toss_count = toss_index + 1
            ctx.acc_ctx.trap_last_chance_pct = float(chance_pct)
            ctx.acc_ctx.trap_last_roll = float(roll)
            ctx.acc_ctx.trap_last_success = bool(success)
        except Exception:
            pass

        # log if available
        if hasattr(ctx, "log") and hasattr(ctx.log, "info"):
            try:
                ctx.log.info(
                    effect_row,
                    code="TRAP_ATTEMPT",
                    detail={
                        "toss_index": toss_index,
                        "chance_pct": float(chance_pct),
                        "roll": float(roll),
                        "success": bool(success),
                    },
                )
            except Exception:
                pass

        return EffectResult(
            executed=True,
            notes={
                "trap": True,
                "toss_index": toss_index,
                "chance_pct": float(chance_pct),
                "roll": float(roll),
                "success": bool(success),
            },
        )
