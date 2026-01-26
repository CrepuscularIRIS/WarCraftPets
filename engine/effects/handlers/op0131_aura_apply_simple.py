from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(131)
class H_Prop131_AuraApplySimple:
    """Aura apply (simple) for opcode 131.

    The pack schema matches Prop52: ChainFailure,Accuracy,Duration.
    Runtime behavior is modeled identically to Prop52 in this engine.
    """

    PROP_ID = 131

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Delegate to the Prop52 implementation (keeps behavior aligned).
        from engine.effects.handlers.op0052_aura_apply_simple import H_Prop52_AuraApplySimple

        return H_Prop52_AuraApplySimple().apply(ctx, actor, target, effect_row, args)
