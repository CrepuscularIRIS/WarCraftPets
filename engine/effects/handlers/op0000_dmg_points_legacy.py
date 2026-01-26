from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(0)
class H_Prop0_DmgPointsLegacy:
    """Legacy / unlabeled damage opcode.

    In multiple exported packs, opcode_id=0 is used as a plain "damage points" opcode,
    but its param schema may be absent from the pack's opcode list.

    We therefore fall back to positional params_raw encoding via EffectRow.param_raw:
      - params[0] = Points
      - params[1] = Accuracy
      - params[2] = IsPeriodic (0/1)
    """

    PROP_ID = 0

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # No reliable labels; parse param_raw as positional.
        raw = str(getattr(effect_row, "param_raw", "") or "")
        parts = [p.strip() for p in raw.split(",") if p.strip() != ""]
        nums = []
        for p in parts:
            try:
                nums.append(int(p))
            except Exception:
                nums.append(0)
        while len(nums) < 6:
            nums.append(0)

        points = int(nums[0])
        accuracy = int(nums[1]) if len(nums) > 1 else 100
        is_periodic = bool(int(nums[2]) if len(nums) > 2 else 0)

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control="CONTINUE", notes={"miss_reason": reason})

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(points),
            is_periodic=bool(is_periodic),
            override_index=None,
        )
        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass
        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
