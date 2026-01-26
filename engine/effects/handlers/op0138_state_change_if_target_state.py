from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(138)
class H_Prop138_StateChangeIfTargetState:
    """Conditional caster-state change based on a target-state test.

    DB2 ParamLabel (from ability pack schema):
      State,StateChange,StateMin,StateMax,TargetTestState,TargetTestStateValue

    Interpreted behavior (observed in pack, e.g. Ability 120 "Howling Blast"):
      - Read the target's `TargetTestState`.
      - If it equals `TargetTestStateValue`, then modify the **caster's** `State`
        by `StateChange`.
      - Optionally clamp the resulting value into [StateMin, StateMax] when those
        bounds are provided (non-zero).
      - This opcode is marked can_miss in the pack; we therefore run a hitcheck
        with default accuracy=1.0, which still respects global accuracy overrides
        and consumes RNG deterministically.

    Notes:
      - This state is frequently used as an ephemeral gating flag for subsequent
        effects (e.g. Prop29 RequiredCasterState), and is then cleared by a
        trigger (e.g. Prop31 on Event 7).
    """

    PROP_ID = 138

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Default hitcheck (can_miss=True but schema has no explicit Accuracy field)
        try:
            hit, reason = ctx.hitcheck.compute(
                ctx, actor, target,
                accuracy=1,
                dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
            )
        except Exception:
            # If hitcheck is unavailable in a minimal harness, treat as hit.
            hit, reason = True, "HITCHECK_UNAVAILABLE"

        if not hit:
            try:
                ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            except Exception:
                pass
            return EffectResult(executed=False)

        state_id = int(args.get("state", 0) or 0)
        delta = int(args.get("statechange", args.get("state_change", 0)) or 0)
        vmin = int(args.get("statemin", args.get("state_min", 0)) or 0)
        vmax = int(args.get("statemax", args.get("state_max", 0)) or 0)
        test_state = int(args.get("targetteststate", args.get("target_test_state", 0)) or 0)
        test_value = int(args.get("targetteststatevalue", args.get("target_test_state_value", 0)) or 0)

        try:
            tgt_id = int(getattr(target, "id", 0))
            cur_test = int(ctx.states.get(tgt_id, test_state, 0))
        except Exception:
            cur_test = 0

        if cur_test != test_value:
            try:
                ctx.log.effect_result(
                    effect_row, actor, target,
                    code="COND_FALSE",
                    reason=f"target_state[{test_state}]={cur_test} != {test_value}",
                )
            except Exception:
                pass
            return EffectResult(executed=True, notes={
                "code": "COND_FALSE",
                "target_test_state": test_state,
                "target_test_value": test_value,
                "observed": cur_test,
            })

        # Apply the state change on caster (observed usage).
        try:
            actor_id = int(getattr(actor, "id", 0))
            cur = int(ctx.states.get(actor_id, state_id, 0))
        except Exception:
            actor_id = int(getattr(actor, "id", 0))
            cur = 0

        new = int(cur + delta)

        # Clamp only when bounds are provided (non-zero). If both are zero, treat as unbounded.
        if vmin != 0 or vmax != 0:
            lo = vmin
            hi = vmax
            # Defensive: if both provided but inverted, swap.
            if lo != 0 and hi != 0 and lo > hi:
                lo, hi = hi, lo
            if lo != 0 and new < lo:
                new = lo
            if hi != 0 and new > hi:
                new = hi

        try:
            ctx.states.set(actor_id, state_id, new)
        except Exception:
            pass

        try:
            ctx.log.effect_result(
                effect_row, actor, target,
                code="STATE_DELTA",
                reason=f"state[{state_id}] {cur}->{new} (delta={delta})",
            )
        except Exception:
            pass

        return EffectResult(executed=True, notes={
            "code": "STATE_DELTA",
            "state": state_id,
            "before": cur,
            "after": new,
            "delta": delta,
            "target_test_state": test_state,
            "target_test_value": test_value,
            "target_test_observed": cur_test,
        })
