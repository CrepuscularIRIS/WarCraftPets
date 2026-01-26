from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(22)
class H_Prop22_TimerTrig:
    PROP_ID = 22

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Semantic (v1):
        #   points -> delay_turns
        delay = args.get("points", args.get("delay_turns", 0))
        try:
            delay = int(delay)
        except Exception:
            delay = 0
        if delay < 0:
            delay = 0

        payload = getattr(effect_row, "scheduled_effect_rows", None)
        if not payload:
            ctx.log.unsupported(effect_row, reason="TIMER_NO_PAYLOAD")
            return EffectResult(executed=False, flow_control="CONTINUE")

        sched = getattr(ctx, "scheduler", None)
        if sched is None:
            ctx.log.unsupported(effect_row, reason="NO_SCHEDULER")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Schedule payload
        sched.schedule(
            delay_turns=delay,
            actor_id=actor.id,
            target_id=target.id,
            effect_rows=payload,
            tag="timer_trig",
        )

        ctx.log.timer_schedule(effect_row, actor, target, delay, len(payload), "timer_trig")

        
        # Stop remaining effects in the same turn: payload should not execute immediately.
        return EffectResult(executed=True, flow_control="STOP_TURN", notes={"delay_turns": delay})
