from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(139)
class H_Prop139_AccuracyCtxSetB:
    """Set accuracy override context (variant B).

    Semantically aligned with Prop145: the override is consumed by HitCheck
    and overrides subsequent effect Accuracy within the same executed turn.
    """

    PROP_ID = 139

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        acc = args.get("accuracy", 1)
        try:
            acc = float(acc)
        except Exception:
            acc = 1.0

        setattr(ctx.acc_ctx, "accuracy_override", acc)
        ctx.log.effect_result(effect_row, actor, target, code="ACC_OVERRIDE", reason=str(acc))
        return EffectResult(executed=True, notes={"accuracy_override": acc})
