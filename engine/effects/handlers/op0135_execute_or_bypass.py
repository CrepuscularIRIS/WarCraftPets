from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.resolver.damage_pipeline import ResolvedDamage


@register_handler(135)
class H_Prop135_ExecuteOrBypass:
    """Execute / lethal effect with immunity checks.

    Pack schema: Accuracy,CasterImmuneState,TargetImmuneState,enableReverse,BypassPetPassives

    Agreed modeling: implement as a lethal "execute". If the target is immune and
    enableReverse=1, redirect the effect to the caster (unless the caster is immune).

    BypassPetPassives:
      - If 1: bypass passive damage caps (e.g., Magic family cap) and kill outright.
      - If 0: apply a conservative passive cap for Magic pets (max 35% of max HP)
        and apply ignore-threshold clamps if the StatsResolver provides them.
    """

    PROP_ID = 135

    def _sum_state(self, ctx, pet_id: int, state_id: int) -> int:
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sum_state"):
            try:
                return int(stats.sum_state(ctx, int(pet_id), int(state_id)))
            except Exception:
                pass
        st = getattr(ctx, "states", None)
        if st is not None:
            try:
                return int(st.get(int(pet_id), int(state_id), 0) or 0)
            except Exception:
                return 0
        return 0

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

        caster_immune_state = int(args.get("caster_immune_state", 0) or 0)
        target_immune_state = int(args.get("target_immune_state", 0) or 0)
        enable_reverse = bool(int(args.get("enable_reverse", 0) or 0))
        bypass = bool(int(args.get("bypass_pet_passives", 0) or 0))

        actual_target = target

        # Target immunity gate.
        if target_immune_state > 0:
            tid = int(getattr(target, "id", 0) or 0)
            if self._sum_state(ctx, tid, int(target_immune_state)) > 0:
                if enable_reverse:
                    # Redirect to caster unless caster is immune.
                    aid = int(getattr(actor, "id", 0) or 0)
                    if caster_immune_state > 0 and self._sum_state(ctx, aid, int(caster_immune_state)) > 0:
                        ctx.log.effect_result(effect_row, actor, target, code="IMMUNE", reason="TARGET_IMMUNE_AND_CASTER_IMMUNE")
                        return EffectResult(executed=False, flow_control="CONTINUE")
                    actual_target = actor
                else:
                    ctx.log.effect_result(effect_row, actor, target, code="IMMUNE", reason="TARGET_IMMUNE")
                    return EffectResult(executed=False, flow_control="CONTINUE")

        # Caster immunity when self-targeted (reverse case).
        if actual_target is actor and caster_immune_state > 0:
            aid = int(getattr(actor, "id", 0) or 0)
            if self._sum_state(ctx, aid, int(caster_immune_state)) > 0:
                ctx.log.effect_result(effect_row, actor, actual_target, code="IMMUNE", reason="CASTER_IMMUNE")
                return EffectResult(executed=False, flow_control="CONTINUE")

        # Lethal damage amount (kill intent).
        hp = int(getattr(actual_target, "hp", 0) or 0)
        if hp <= 0:
            ctx.log.effect_result(effect_row, actor, actual_target, code="NOOP", reason="TARGET_DEAD")
            return EffectResult(executed=False, flow_control="CONTINUE")

        dmg = int(hp)

        # Passive cap example: Magic family takes at most 35% of max HP from one hit.
        # Apply only when bypass is disabled.
        if not bypass:
            try:
                if int(getattr(actual_target, "pet_type", -1) or -1) == 5:
                    max_hp = int(getattr(actual_target, "max_hp", 0) or 0)
                    cap = int(max_hp * 0.35)
                    if cap > 0:
                        dmg = min(int(dmg), int(cap))
            except Exception:
                pass

            stats = getattr(ctx, "stats", None)
            if stats is not None and hasattr(stats, "apply_damage_thresholds"):
                try:
                    dmg = int(stats.apply_damage_thresholds(ctx, int(getattr(actual_target, "id", 0) or 0), int(dmg)))
                except Exception:
                    dmg = int(dmg)

        if dmg <= 0:
            ctx.log.effect_result(effect_row, actor, actual_target, code="NOOP", reason="DMG<=0")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Apply lethal (or capped) damage.
        ctx.apply_damage(actual_target, int(dmg), trace={"execute": True, "bypass": bool(bypass)})
        try:
            ctx.acc_ctx.last_damage_dealt = int(dmg)
            ctx.acc_ctx.last_damage_target_id = int(getattr(actual_target, "id", 0))
        except Exception:
            pass

        resolved = ResolvedDamage(final_damage=int(dmg), trace={"execute": True, "bypass": bool(bypass)})
        ctx.log.damage(effect_row, actor, actual_target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        return EffectResult(executed=True)
