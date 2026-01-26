from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event


@register_handler(53)
class H_Prop53_HealPctMaxHP:
    """Heal for a percentage of target max HP.

    Pack schema: Percentage,Accuracy

    Conservative modeling:
      - Healing amount = floor(effective_max_hp * Percentage / 100)
      - Does not scale with Power (unlike points-based heals).
    """

    PROP_ID = 53

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 100),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"miss_reason": reason})

        pct = args.get("percentage", 0)
        try:
            pct = int(pct)
        except Exception:
            pct = 0
        if pct <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="PCT<=0")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Prefer effective max HP if StatsResolver is available.
        max_hp = int(getattr(target, "max_hp", 0) or 0)
        stats = getattr(ctx, "stats", None)
        if stats is not None:
            try:
                if hasattr(stats, "snapshot_for_pet"):
                    eff = stats.snapshot_for_pet(ctx, target)
                    max_hp = int(getattr(eff, "max_hp", max_hp) or max_hp)
                elif hasattr(stats, "effective_max_hp"):
                    # Fallback path (requires ctx.pets mapping)
                    max_hp = int(stats.effective_max_hp(ctx, int(getattr(target, "id", 0) or 0)))
            except Exception:
                max_hp = int(getattr(target, "max_hp", 0) or 0)

        heal_amt = int((max_hp * pct) // 100)
        if heal_amt <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="HEAL<=0")
            return EffectResult(executed=False, flow_control="CONTINUE")

        ctx.apply_heal(target, heal_amt, trace={"pct": int(pct), "base_max_hp": int(max_hp)})
        ctx.log.heal(effect_row, actor, target, heal_amt, trace={"pct": int(pct), "base_max_hp": int(max_hp)})
        ctx.event_bus.emit(Event.ON_HEAL, payload={"amount": int(heal_amt), "pct": int(pct)})
        return EffectResult(executed=True)
