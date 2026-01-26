from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(111)
class H_Prop111_SetHpPct:
    """Set target current HP to a percentage of MaxHP (revive compatible).

    Observed uses in the exported pack:
      - Failsafe / GM Revive: set target HP to 20%/100% and revive.
      - Damned: set HP to a small percentage.
    """

    PROP_ID = 111

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        pct = args.get("percentage", 0)
        try:
            pct = float(pct)
        except Exception:
            pct = 0.0

        # Resolve MaxHP.
        max_hp = int(getattr(target, "max_hp", 0) or 0)
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "snapshot_for_pet"):
            try:
                snap = stats.snapshot_for_pet(ctx, target)
                max_hp = int(getattr(snap, "max_hp", max_hp) or max_hp)
            except Exception:
                pass
        if max_hp <= 0:
            # Fallback: keep current hp as max, avoiding division-by-zero.
            max_hp = int(getattr(target, "hp", 0) or 0)

        new_hp = int(max_hp * (pct / 100.0))
        if pct > 0 and new_hp < 1:
            new_hp = 1
        if new_hp > max_hp:
            new_hp = max_hp
        if new_hp < 0:
            new_hp = 0

        target.hp = int(new_hp)
        target.alive = (target.hp > 0)

        # Keep derived stats consistent if the resolver supports syncing.
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        ctx.log.effect_result(effect_row, actor, target, code="SET_HP_PCT", reason=f"{pct}")
        return EffectResult(executed=True, notes={"pct": pct, "new_hp": int(new_hp), "max_hp": int(max_hp)})
