from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(136)
class H_Prop136_DontMiss:
    PROP_ID = 136

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # ParamLabel: DontMiss
        v = int(args.get("dont_miss", args.get("dontmiss", 0)))
        ctx.acc_ctx.dont_miss = (v != 0)
        return EffectResult(executed=True, notes={"code": "DONT_MISS", "dont_miss": bool(ctx.acc_ctx.dont_miss)})
