from __future__ import annotations

import math

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(27)
class H_Prop27_DmgRamping:
    """Ramping damage ("damage increases by X each time it hits").

    DB2 ParamLabel: Points,Accuracy,PointsIncreasePerUse,PointsMax,StateToTriggerMaxPoints,,

    Pragmatic v1 behavior:
      - Track a per-actor ramp counter (successful hits) and increase points linearly.
      - Clamp at PointsMax.
      - If StateToTriggerMaxPoints is provided (>0), use it as the state slot for the
        ramp counter; otherwise, use a derived synthetic state id per ability.

    Notes:
      - DB2's field name suggests "trigger max points"; empirically in exports the
        column is used as a stable state id for the ramping counter for some skills.
      - We intentionally keep this numeric-only; special resets (swap-out, miss resets,
        dispels) are not modeled in v1.
    """

    PROP_ID = 27

    # Synthetic state namespace (to avoid collisions with real BattlePetState IDs)
    _SYN_STATE_BASE = 900_000

    def _ramp_state_id(self, effect_row, args) -> int:
        # Prefer the explicit state id if present.
        sid = args.get("state_to_trigger_max_points")
        try:
            sid_i = int(sid or 0)
        except Exception:
            sid_i = 0
        if sid_i > 0:
            return int(sid_i)
        try:
            aid = int(getattr(effect_row, "ability_id", 0) or 0)
        except Exception:
            aid = 0
        return int(self._SYN_STATE_BASE + max(0, aid))

    def _clamp_points(self, base: int, inc: int, pmax: int, count: int) -> int:
        # Robust clamp for both positive and negative increments.
        points = int(base + inc * count)
        if pmax == 0:
            return int(points)
        if inc >= 0:
            return int(min(points, pmax))
        return int(max(points, pmax))

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

        base_points = int(args.get("points", 0) or 0)
        inc = int(args.get("points_increase_per_use", args.get("pointsincreaseperuse", 0)) or 0)
        pmax = int(args.get("points_max", args.get("pointsmax", 0)) or 0)

        ramp_sid = int(self._ramp_state_id(effect_row, args))
        actor_id = int(getattr(actor, "id", 0) or 0)

        sm = getattr(ctx, "states", None)
        count = 0
        if sm is not None:
            try:
                count = int(sm.get(actor_id, ramp_sid, 0) or 0)
            except Exception:
                count = 0

        # Compute points for this hit.
        points_used = self._clamp_points(base_points, inc, pmax, count)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(points_used),
            is_periodic=False,
            override_index=None,
        )
        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)
        # For post-damage effects (e.g., lifesteal)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass
        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)

        # Increment ramp counter after a successful hit.
        if sm is not None and inc != 0 and pmax != 0:
            try:
                # Number of increments needed to reach cap.
                max_steps = 0
                if inc > 0 and pmax > base_points:
                    max_steps = int(math.floor((pmax - base_points) / float(inc)))
                elif inc < 0 and pmax < base_points:
                    max_steps = int(math.floor((base_points - pmax) / float(-inc)))
                new_count = int(count + 1)
                if max_steps > 0:
                    new_count = int(min(new_count, max_steps))
                sm.set(actor_id, ramp_sid, int(new_count))
                # Reuse the existing state_set log primitive for observability.
                ctx.log.state_set(effect_row, actor, actor, ramp_sid, int(new_count))
            except Exception:
                pass

        return EffectResult(
            executed=True,
            spawned_damage_events=[dmg_event],
            notes={"ramp_state_id": int(ramp_sid), "ramp_count_before": int(count), "points_used": int(points_used)},
        )
