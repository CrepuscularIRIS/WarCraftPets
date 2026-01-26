from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(145)
class H_Prop145_AccuracyCtxSetA:
    """Set accuracy override context (variant A).

    This opcode updates ctx.acc_ctx.accuracy_override, which HitCheck
    prioritizes over per-effect Accuracy for the remainder of the current
    turn execution.
    """

    PROP_ID = 145

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        acc = args.get("accuracy", 1)
        try:
            acc = float(acc)
        except Exception:
            acc = 1.0

        setattr(ctx.acc_ctx, "accuracy_override", acc)
        ctx.log.effect_result(effect_row, actor, target, code="ACC_OVERRIDE", reason=str(acc))
        return EffectResult(executed=True, notes={"accuracy_override": acc})
