from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(194)
class H_Prop194_TargetSelfIfPrevMiss:
    """Flow-control opcode: if the immediately previous effect MISSED, retarget next effect to self.

    Observed in DB2 exports (wow_export_merged.xlsx):
      - Ability 762 "Haymaker": on miss, apply a self-stun aura (next effect).
      - Ability 989 "Blingtron Gift Package": on miss, apply a follow-up heal (next effect).

    Semantics implemented here:
      - If previous effect executed successfully (i.e., hit/applied): stop remaining effects in this turn.
      - If previous effect did NOT execute (typically due to MISS): set a one-shot target override
        to the actor for the next effect, then continue.

    Preconditions:
      - AbilityTurnExecutor must populate ctx.acc_ctx.prev_effect_executed for this turn.
    """

    PROP_ID = 194

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        prev_ok = None
        try:
            prev_ok = getattr(ctx.acc_ctx, "prev_effect_executed", None)
        except Exception:
            prev_ok = None

        # If we have no signal (e.g., invoked first), do nothing.
        if prev_ok is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_PREV_EFFECT_SIGNAL")
            return EffectResult(executed=False, flow_control="CONTINUE")

        if bool(prev_ok):
            # Previous effect HIT/APPLIED -> skip the "on-miss" branch.
            ctx.log.effect_result(effect_row, actor, target, code="STOP", reason="PREV_EFFECT_EXECUTED")
            return EffectResult(executed=False, flow_control="STOP_TURN")

        # Previous effect did not execute (most commonly MISS) -> route next effect to self.
        try:
            ctx.acc_ctx.target_override_id = int(getattr(actor, "id", 0) or 0)
            ctx.acc_ctx.consume_target_override = True
        except Exception:
            pass

        ctx.log.effect_result(effect_row, actor, target, code="OVERRIDE", reason="PREV_EFFECT_NOT_EXECUTED")
        return EffectResult(executed=False, flow_control="CONTINUE")
