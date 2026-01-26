from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(156)
class H_Prop156_StateGuardOrCCHint:
    """State guard / CC-resilient hint (opcode 156).

    This opcode is used in the exported ability pack in two recurring patterns:

    1) **State guard**: `State = 1 (Is_Dead)` placed before delayed damage or
       between multi-hit segments. The intention is to stop executing the
       remaining effects once the target is already dead.

    2) **CC resilient hint**: `State = 149 (resilient)` placed right before a
       crowd-control aura apply (Prop26/52/131). The aura apply handlers in this
       engine already support a *resilient duration reduction* via
       `ctx.acc_ctx.cc_resilient_state`.

    For maximum backward compatibility and minimal behavior change, this handler
    implements both behaviors:
      - If `State == 1` and target has that state (nonzero), return
        `STOP_ABILITY`.
      - Otherwise, record the state id as a CC resilient hint for the next aura
        apply effect.
    """

    PROP_ID = 156

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

        # 1) State guard for dead targets (Is_Dead = 1 in this pack).
        if sid == 1:
            is_dead = 0
            try:
                is_dead = int(ctx.states.get(int(getattr(target, "id", 0)), 1, 0))
            except Exception:
                is_dead = 0
            if is_dead != 0:
                ctx.log.effect_result(effect_row, actor, target, code="STOP", reason="TARGET_DEAD")
                return EffectResult(executed=False, flow_control="STOP_ABILITY", notes={"state": 1, "value": int(is_dead)})

        # 2) CC resilient duration-reduction hint (consumed by Prop26/52/131).
        setattr(ctx.acc_ctx, "cc_resilient_state", sid)
        setattr(ctx.acc_ctx, "cc_resilient_points", sp)
        ctx.log.effect_result(effect_row, actor, target, code="CC_HINT", reason=f"state={sid}")
        return EffectResult(executed=True, notes={"cc_resilient_state": sid, "cc_resilient_points": sp})
