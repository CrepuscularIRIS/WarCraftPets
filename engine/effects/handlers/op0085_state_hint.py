from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(85)
class H_Prop85_StateHint:
    """State hint / UI tag.

    DB2 ParamLabel: State,,,,,

    This opcode does not directly modify combat state in v1. It is preserved
    as a diagnostic signal for downstream tooling (logs/RL).
    """

    PROP_ID = 85

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        state_id = int(args.get("state", 0) or 0)

        # Store on the shared action context so subsequent effects (if any) may consult it.
        try:
            setattr(ctx.acc_ctx, "state_hint", state_id)
        except Exception:
            pass

        # Log as a warning-level semantic signal (non-fatal).
        if hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
            ctx.log.warn(effect_row, code="STATE_HINT", detail={"state": int(state_id)})

        return EffectResult(executed=True, notes={"code": "STATE_HINT", "state": int(state_id)})
