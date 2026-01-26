from __future__ import annotations

from engine.core.events import Event
from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.model.heal import HealEvent


@register_handler(78)
class H_Prop78_HealScaleByStateApplyAura:
    """Apply aura and heal scaled by a state counter.

    DB2 ParamLabel: Points,State,MaxPoints,StateToMultiplyAgainst,,

    Observed use (merged export):
      - Ability 303 (Plant) applies aura 302 (Planted).
      - Aura 302 increments state 70 (Special_Plant) up to 10.
      - This opcode heals the owner for Points * stacks, where stacks is read
        from StateToMultiplyAgainst (usually the same state 70), clamped by
        MaxPoints when provided.

    Notes:
      - No Accuracy param in DB2 for this opcode (always hits).
      - Duration is taken from the aura's own semantics; we apply as permanent
        (-1) here, consistent with current engine pack behaviour.
    """

    PROP_ID = 78

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        points = int(args.get("points", 0) or 0)
        state_id = int(args.get("state", 0) or 0)
        max_points = int(args.get("maxpoints", args.get("max_points", 0)) or 0)
        mul_state = int(args.get("statetomultiplyagainst", args.get("state_to_multiply_against", 0)) or 0)

        # 1) Apply referenced aura (if any)
        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is not None and hasattr(ctx, "aura"):
            try:
                ar = ctx.aura.apply(
                    owner_pet_id=target.id,
                    caster_pet_id=actor.id,
                    aura_id=int(aura_id),
                    duration=-1,
                    tickdown_first_round=False,
                    source_effect_id=effect_row.effect_id,
                )
                if hasattr(ctx, "log"):
                    # duration=-1 permanent
                    if ar.refreshed and ar.aura is not None:
                        ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)
                    if ar.applied or ar.refreshed:
                        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), -1, False, ar.reason)
            except Exception:
                pass

        # 2) Compute multiplier from a state value
        mult = 1
        if mul_state and hasattr(ctx, "states"):
            try:
                mult = int(ctx.states.get(int(getattr(target, "id", 0)), int(mul_state), 0) or 0)
            except Exception:
                mult = 0
        if mult <= 0:
            mult = 1
        if max_points > 0 and mult > max_points:
            mult = max_points

        total_points = int(points * mult)

        # 3) Optional: also maintain the referenced state (some packs may rely on it)
        if state_id and hasattr(ctx, "states"):
            try:
                # Ensure state exists (no change) - do not override existing counters.
                _ = ctx.states.get(int(getattr(target, "id", 0)), int(state_id), 0)
            except Exception:
                pass

        # 4) Resolve and apply heal
        heal_event = HealEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(total_points),
            is_periodic=False,
        )
        resolved = ctx.heal_pipeline.resolve(ctx, heal_event)
        ctx.apply_heal(target, resolved.final_heal, trace=resolved.trace)
        if hasattr(ctx, "log"):
            ctx.log.heal(effect_row, actor, target, resolved.final_heal, trace=resolved.trace)
        if hasattr(ctx, "event_bus"):
            ctx.event_bus.emit(Event.ON_HEAL, payload=resolved)

        return EffectResult(
            executed=True,
            notes={
                "code": "HEAL_SCALE_BY_STATE",
                "points": int(points),
                "mult": int(mult),
                "total_points": int(total_points),
                "heal": int(resolved.final_heal),
            },
        )
