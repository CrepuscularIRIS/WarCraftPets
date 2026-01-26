from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(122)
class H_Prop122_CloneActivateOrSpawn:
    """Clone: activate/spawn.

    Observed in the pack for abilities like:
      - Split (451)
      - Magical Clone (467)
      - Wrath of Tarecgosa (813)
      - Hatch (1770)

    Pack metadata marks this opcode as `can_miss`, but `param_schema` is empty.
    Empirically, rows carry `params_raw` where slot2 is often 100 (hit chance).
    Some rows have slot2=0; in those cases the game behavior is still a success,
    therefore we treat 0 as "default 100%".

    Minimal engine behavior:
      - Perform an accuracy check (best-effort).
      - If hit: mark clone as active on the caster using DB2 clone states.
      - The engine currently does not materialize a separate spawned pet entity;
        downstream logic can key off Clone_* states and the clone aura (often 720)
        applied by the subsequent Prop26.
    """

    _STATE_CLONE_ACTIVE = 100
    _STATE_CLONE_LAST_ABILITY_ID = 107
    _STATE_CLONE_LAST_ABILITY_TURN = 108
    _STATE_CLONE_CLONE_ABILITY_ID = 117

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # No reliable param_label -> parse raw slots directly.
        raw = str(getattr(effect_row, "param_raw", "") or "")
        toks = [(t.strip() or "0") for t in raw.split(",")]
        while len(toks) < 6:
            toks.append("0")
        try:
            p1 = int(toks[0])
        except Exception:
            p1 = 0
        try:
            p2 = int(toks[1])
        except Exception:
            p2 = 0

        chain_failure = p1
        # Treat 0 as default 100% (see notes).
        accuracy = (p2 if p2 != 0 else 100)

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False))
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="CLONE_ACTIVATE", reason=reason)
            return EffectResult(
                executed=True,
                flow_control=("STOP_ABILITY" if int(chain_failure or 0) != 0 else "CONTINUE"),
                notes={"hit": False, "reason": reason, "chain_failure": int(chain_failure or 0)},
            )

        # Apply states to the caster (owner).
        try:
            pid = int(getattr(actor, "id", 0) or 0)
            ctx.states.set(pid, self._STATE_CLONE_ACTIVE, 1)
            ctx.states.set(pid, self._STATE_CLONE_LAST_ABILITY_ID, int(effect_row.ability_id or 0))
            ctx.states.set(pid, self._STATE_CLONE_LAST_ABILITY_TURN, int(effect_row.turn_id or 0))
            ctx.states.set(pid, self._STATE_CLONE_CLONE_ABILITY_ID, int(effect_row.ability_id or 0))
        except Exception:
            # Fail closed: keep battle running.
            pass

        ctx.log.effect_result(effect_row, actor, target, code="CLONE_ACTIVATE", reason="HIT")
        return EffectResult(
            executed=True,
            notes={"hit": True, "chain_failure": int(chain_failure or 0)},
        )
