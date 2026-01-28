from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

@register_handler(223)
class H_Prop223_Unknown:
    PROP_ID = 223

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        """
        Unknown effect (opcode 223)
        Used by ability_id: [1344]
        
        TODO: 需要分析真实游戏行为来确定具体效果
        """
        # 命中检查
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        # 记录unknown effect
        ctx.log.effect_result(effect_row, actor, target, code="UNKNOWN", reason="opcode_223")
        
        return EffectResult(executed=True, notes={"opcode": 223, "type": "unknown"})
