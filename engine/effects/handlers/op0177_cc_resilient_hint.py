from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(177)
class H_Prop177_CCResilientHint:
    """Prepare CC-resilient context for the next aura-apply effect.

    In the exported ability pack, Prop177 typically precedes Prop26/52 to
    indicate that the following crowd-control aura should be reduced by the
    target's current *Resilient* state (state_id=149 in common data).

    This handler records the state id in ctx.acc_ctx.cc_resilient_state.
    The actual duration adjustment is performed by Prop26/52 handlers.
    """

    PROP_ID = 177

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        sid = args.get("state", 0)
        sp = args.get("state_points", args.get("statepoints", 0))
        try:
            sid = int(sid)
        except Exception:
            sid = 0
        try:
            sp = int(sp)
        except Exception:
            sp = 0

        setattr(ctx.acc_ctx, "cc_resilient_state", sid)
        setattr(ctx.acc_ctx, "cc_resilient_points", sp)
        ctx.log.effect_result(effect_row, actor, target, code="CC_HINT", reason=f"state={sid}")
        return EffectResult(executed=True, notes={"cc_resilient_state": sid, "cc_resilient_points": sp})
