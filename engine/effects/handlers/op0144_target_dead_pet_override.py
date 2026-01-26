from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(144)
class H_Prop144_TargetDeadPetOverride:
    """Select a dead pet ("corpse") as the target for subsequent effects in the same turn.

    DB2 ParamLabel: ,,,,,

    Observed use (pack): Ability 665 "Consume Corpse" (Prop144 -> Prop61 -> Prop31).

    Conservative behavior:
      - Find the first dead pet on the *opposing* team (relative to the actor).
      - Prefer a dead pet that has state 120 > 0 (if state tracking exists).
      - Store it into ctx.acc_ctx.target_override_id (without consuming it) so subsequent
        effect rows use that target via AbilityTurnExecutor.
      - If no suitable dead pet exists, this opcode is a NOOP.

    This is a targeting utility opcode rather than a direct gameplay effect.
    """

    PROP_ID = 144

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
        teams = getattr(ctx, "teams", None)
        pets = getattr(ctx, "pets", None)
        if teams is None or pets is None:
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_TEAMS")
            return EffectResult(executed=False, flow_control="CONTINUE")

        actor_id = int(getattr(actor, "id", 0) or 0)
        actor_team = teams.team_of_pet(actor_id)
        if actor_team is None:
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_TEAM")
            return EffectResult(executed=False, flow_control="CONTINUE")
        enemy_team = 1 - int(actor_team)

        enemy = teams.teams.get(int(enemy_team))
        if enemy is None:
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_ENEMY")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Prefer a dead pet with state 120 (commonly used as "corpse available" marker).
        candidates = []
        for pid in list(getattr(enemy, "pet_ids", []) or []):
            pid = int(pid)
            p = pets.get(pid)
            if p is None:
                continue
            alive = bool(getattr(p, "alive", True)) and int(getattr(p, "hp", 1) or 0) > 0
            if alive:
                continue
            candidates.append(pid)

        if not candidates:
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_CORPSE")
            return EffectResult(executed=False, flow_control="CONTINUE")

        chosen = None
        for pid in candidates:
            if self._sum_state(ctx, pid, 120) > 0:
                chosen = pid
                break
        if chosen is None:
            chosen = int(candidates[0])

        try:
            setattr(ctx.acc_ctx, "target_override_id", int(chosen))
            # Keep override active for subsequent effects (do not consume).
            setattr(ctx.acc_ctx, "consume_target_override", False)
        except Exception:
            pass

        if hasattr(ctx, "log"):
            ctx.log.effect_result(effect_row, actor, target, code="TARGET_OVERRIDE", reason=f"CORPSE:{chosen}")
        return EffectResult(executed=True, flow_control="CONTINUE", notes={"target_override_id": int(chosen)})
