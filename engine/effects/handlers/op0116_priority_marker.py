from types import SimpleNamespace

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(116)
class H_Prop116_PriorityMarker:
    PROP_ID = 116

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: ",,,,,"
        # Semantics: marks current action as priority for initiative resolver.
        # Our skeleton stores it on ctx.btl for future battle orchestrator usage.
        if not hasattr(ctx, "btl") or ctx.btl is None:
            ctx.btl = SimpleNamespace()
        ctx.btl.priority_actor_id = int(getattr(actor, "id", 0))
        ctx.log.effect_result(effect_row, actor, target, code="PRIORITY_MARK", reason=None)
        return EffectResult(executed=True, notes={"priority_actor_id": ctx.btl.priority_actor_id})
