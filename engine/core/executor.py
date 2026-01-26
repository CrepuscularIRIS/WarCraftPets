from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Any

from engine.effects.types import EffectResult


@dataclass
class TurnExecResult:
    executed_count: int
    stopped: bool
    stop_reason: Optional[str] = None  # "STOP_TURN" | "STOP_ABILITY"
    last_effect_result: Optional[EffectResult] = None


class AbilityTurnExecutor:
    # Executes a list of effect rows for a single turn (order_index ascending).
    #
    # Flow-control convention:
    #   - CONTINUE: proceed
    #   - STOP_TURN: stop executing remaining effects in THIS turn
    #   - STOP_ABILITY: stop executing remaining effects in THIS turn and signal caller
    #
    # This class intentionally does not know about cooldowns, multi-turn state machines, etc.

    def execute_turn(self, ctx: Any, actor: Any, target: Any, effect_rows: List[Any]) -> TurnExecResult:
        # Reset transient per-turn contexts at the start of each turn execution.
        if hasattr(ctx, "acc_ctx"):
            ctx.acc_ctx.dont_miss = False
            # Prop145/139 (accuracy override)
            setattr(ctx.acc_ctx, "accuracy_override", None)
            # Prop85 (state hint) / Prop177 (resilient hint)
            setattr(ctx.acc_ctx, "state_hint", None)
            setattr(ctx.acc_ctx, "cc_resilient_state", None)
            setattr(ctx.acc_ctx, "cc_resilient_points", 0)
            # Prop178 reporting hint
            setattr(ctx.acc_ctx, "cc_report_fails_as_immune", 0)
            # Prop159 multi-target cursor / target override (conservative)
            setattr(ctx.acc_ctx, "target_override_id", None)
            setattr(ctx.acc_ctx, "consume_target_override", False)
            setattr(ctx.acc_ctx, "mt_team_id", None)
            setattr(ctx.acc_ctx, "mt_targets", None)
            setattr(ctx.acc_ctx, "mt_index", 0)
            setattr(ctx.acc_ctx, "prev_prop_id", None)
            setattr(ctx.acc_ctx, "prev_effect_executed", None)
            setattr(ctx.acc_ctx, "prev_effect_flow_control", None)
            # Prop135 (bypass flag) - keep as hint for potential downstream effects
            setattr(ctx.acc_ctx, "bypass_pet_passives", 0)
        rows = sorted(effect_rows, key=lambda r: (getattr(r, "order_index", 0), getattr(r, "effect_id", 0)))
        executed = 0
        stop_reason: Optional[str] = None
        last: Optional[EffectResult] = None

        for row in rows:
            # Prop159 may set a one-shot target override for the next effect.
            eff_target = target
            used_override = False
            try:
                ov = getattr(ctx.acc_ctx, "target_override_id", None)
                if ov is not None:
                    maybe = getattr(ctx, "pets", {}).get(int(ov), None)
                    if maybe is not None:
                        eff_target = maybe
                        used_override = True
            except Exception:
                eff_target = target

            last = ctx.dispatcher.dispatch(ctx, actor, eff_target, row)

            # Record previous effect execution outcome (for control opcodes like Prop194).
            try:
                setattr(ctx.acc_ctx, "prev_effect_executed", bool(getattr(last, "executed", False)))
                setattr(ctx.acc_ctx, "prev_effect_flow_control", getattr(last, "flow_control", "CONTINUE"))
            except Exception:
                pass

            # Consume one-shot overrides to avoid leakage.
            try:
                if used_override and bool(getattr(ctx.acc_ctx, "consume_target_override", False)):
                    setattr(ctx.acc_ctx, "target_override_id", None)
                    setattr(ctx.acc_ctx, "consume_target_override", False)
            except Exception:
                pass

            # Record previous opcode for conservative control opcodes (e.g., Prop159).
            try:
                setattr(ctx.acc_ctx, "prev_prop_id", int(getattr(row, "prop_id", 0) or 0))
            except Exception:
                pass
            if last.executed:
                executed += 1

            fc = getattr(last, "flow_control", "CONTINUE") or "CONTINUE"
            if fc in ("STOP_TURN", "STOP_ABILITY"):
                stop_reason = fc
                break

        return TurnExecResult(
            executed_count=executed,
            stopped=stop_reason is not None,
            stop_reason=stop_reason,
            last_effect_result=last,
        )
