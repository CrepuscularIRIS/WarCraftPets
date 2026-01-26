from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(159)
class H_Prop159_MultiTargetAdvance:
    """Advance the implicit target cursor for subsequent effects.

    The exported DB2 packs often model "hit all pets in a team" as:
      - one effect applied to the current (active) target
      - followed by Prop159 to advance the target
      - repeated N times (typically 3)

    The pack schema is empty; this opcode is a control marker.

    Conservative policy (as agreed): only advance if the previous opcode in the
    same cast-turn was an aura apply (50/52/54). This prevents accidental target
    leakage in non-multi-target ability scripts.

    Implementation details:
      - We store a per-turn cursor in ctx.acc_ctx (mt_targets/mt_index).
      - We set ctx.acc_ctx.target_override_id for the *next* effect only.
        The executor consumes and clears the override after dispatch.
    """

    PROP_ID = 159

    _ALLOWED_PREV = {50, 52, 54}

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        prev = int(getattr(ctx.acc_ctx, "prev_prop_id", -1) or -1)
        if prev not in self._ALLOWED_PREV:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="PREV_NOT_AURA_APPLY")
            return EffectResult(executed=False, flow_control="CONTINUE")

        tm = getattr(ctx, "teams", None)
        if tm is None or not hasattr(tm, "team_of_pet"):
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_TEAM_MANAGER")
            return EffectResult(executed=False, flow_control="CONTINUE")

        try:
            team_id = tm.team_of_pet(int(getattr(target, "id", 0) or 0))
        except Exception:
            team_id = None
        if team_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="TEAM_UNKNOWN")
            return EffectResult(executed=False, flow_control="CONTINUE")

        team = tm.teams.get(int(team_id)) if hasattr(tm, "teams") else None
        if team is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="TEAM_MISSING")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Build or reuse cursor list.
        mt_team = getattr(ctx.acc_ctx, "mt_team_id", None)
        mt_targets = getattr(ctx.acc_ctx, "mt_targets", None)
        mt_index = int(getattr(ctx.acc_ctx, "mt_index", 0) or 0)

        if mt_team != int(team_id) or not isinstance(mt_targets, list) or not mt_targets:
            # Initialize from roster order, keeping only alive pets.
            roster = list(getattr(team, "pet_ids", []) or [])
            alive = []
            for pid in roster:
                p = getattr(ctx, "pets", {}).get(int(pid))
                if p is None:
                    continue
                if bool(getattr(p, "is_alive", True)) and int(getattr(p, "hp", 0) or 0) > 0:
                    alive.append(int(pid))
            if not alive:
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_ALIVE_TARGETS")
                return EffectResult(executed=False, flow_control="CONTINUE")

            anchor_id = int(getattr(target, "id", 0) or 0)
            try:
                mt_index = int(alive.index(anchor_id))
            except Exception:
                mt_index = 0
            mt_targets = alive
            setattr(ctx.acc_ctx, "mt_team_id", int(team_id))
            setattr(ctx.acc_ctx, "mt_targets", list(mt_targets))
            setattr(ctx.acc_ctx, "mt_index", int(mt_index))

        # Advance cursor.
        if len(mt_targets) > 1:
            mt_index = (int(mt_index) + 1) % int(len(mt_targets))
        else:
            mt_index = 0

        next_id = int(mt_targets[mt_index])
        setattr(ctx.acc_ctx, "mt_index", int(mt_index))

        # Override for next effect only.
        setattr(ctx.acc_ctx, "target_override_id", int(next_id))
        setattr(ctx.acc_ctx, "consume_target_override", True)
        ctx.log.effect_result(effect_row, actor, target, code="ADVANCE", reason=f"to:{next_id}")
        return EffectResult(executed=True, flow_control="CONTINUE", notes={"next_target_id": int(next_id)})
