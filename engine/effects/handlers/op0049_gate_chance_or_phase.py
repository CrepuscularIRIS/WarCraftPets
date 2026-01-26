from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(49)
class H_Prop49_GateChanceOrPhase:
    PROP_ID = 49

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: "Chance,unused,,,,"
        chance = args.get("chance", 0)
        passed, c_norm, roll = ctx.gatecheck.compute(chance)
        ctx.log.gate(effect_row, actor, target, c_norm, roll, passed)

        if not passed:
            # Same default as Prop158: stop remaining effects for this TURN.
            return EffectResult(executed=False, flow_control="STOP_TURN", notes={"gate_pass": False})

        return EffectResult(executed=True, flow_control="CONTINUE", notes={"gate_pass": True})
