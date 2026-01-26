# Ensure handlers are imported so they can register themselves.
# This makes the opcode layer truly evolvable: drop-in new opXXXX_*.py -> auto-registered.
import engine.effects.handlers  # noqa: F401

from engine.effects.registry import get_handler
from engine.effects.param_parser import ParamParser
from engine.effects.semantic_registry import get_default_registry, normalize_args, validate_and_fill_args
from engine.effects.types import EffectResult


class EffectDispatcher:
    def __init__(self, semantic_registry=None):
        self._sem = semantic_registry or get_default_registry()

    def dispatch(self, ctx, actor, target, effect_row) -> EffectResult:
        sem = self._sem.get(effect_row.prop_id)
        h = get_handler(effect_row.prop_id)
        if h is None:
            # Distinguish: known opcode (semantics exists) vs unknown opcode
            reason = "NO_HANDLER_KNOWN" if sem is not None else "NO_HANDLER"
            ctx.log.unsupported(effect_row, reason=reason)
            return EffectResult(executed=False)

        # Semantics-aware validation (non-fatal, logs warnings)
        if sem is not None:
            mm = self._sem.label_mismatch(effect_row.prop_id, effect_row.param_label)
            if mm is not None and hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row, code="PARAM_LABEL_MISMATCH", detail=mm)

        args = ParamParser.parse(effect_row.param_label, effect_row.param_raw)
        if sem is not None:
            args, rep = validate_and_fill_args(args, sem.schema())
            if rep and hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row, code="ARG_SCHEMA", detail=rep)
            args = normalize_args(args, sem.schema())

        return h.apply(ctx, actor, target, effect_row, args)
