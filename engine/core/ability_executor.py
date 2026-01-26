from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from engine.core.executor import AbilityTurnExecutor, TurnExecResult
from engine.core.scheduler import Scheduler
from engine.core.tick_engine import TickEngine
from engine.core.events import Event

@dataclass
class AbilityUseResult:
    turn_result: TurnExecResult
    cooldown_set: int = 0

class AbilityExecutor:
    # Minimal cross-turn infrastructure:
    # - TURN_START: tick cooldowns; resolve scheduled packets; process TURN_START ticks.
    # - TURN_END: process TURN_END ticks (DOT/HOT + aura duration/expire).
    #
    # This is a framework for Prop22 (timer) / multi-turn abilities, not a full battle loop.

    def __init__(self):
        self.turn_executor = AbilityTurnExecutor()
        self.scheduler = Scheduler()
        self.tick_engine = TickEngine()
        self.turn_no = 0

    def _bind_scheduler(self, ctx: Any) -> None:
        # Make scheduler accessible to handlers (Prop22)
        ctx.scheduler = self.scheduler

    def on_turn_start(self, ctx: Any, pets: List[Any]) -> None:
        self.turn_no += 1
        self._bind_scheduler(ctx)

        # cooldown tick once per round
        # team control tick (ability lockouts)
        if hasattr(ctx, "teams") and ctx.teams is not None:
            ctx.teams.tick_down()
        if hasattr(ctx, "cooldowns"):
            ctx.cooldowns.tick_down()
            ctx.log.cooldown_tick()

        # resolve scheduled packets
        ready = self.scheduler.tick()
        for pkt in ready:
            actor = next((p for p in pets if p.id == pkt.actor_id), None)
            target = next((p for p in pets if p.id == pkt.target_id), None)
            if actor is None or target is None:
                continue
            self.turn_executor.execute_turn(ctx, actor, target, pkt.effect_rows)

        # event ticks at TURN_START (optional)
        self.tick_engine.process_event(ctx, pets, Event.TURN_START)

        # Sync effective stats (best-effort) after TURN_START packets/ticks.
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync"):
            try:
                stats.sync(ctx, pets)
            except Exception:
                pass

    def on_turn_end(self, ctx: Any, pets: List[Any]) -> None:
        self._bind_scheduler(ctx)
        self.tick_engine.process_event(ctx, pets, Event.TURN_END)

        # Sync effective stats after aura expiration.
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync"):
            try:
                stats.sync(ctx, pets)
            except Exception:
                pass

    def use_ability(self, ctx: Any, actor: Any, target: Any, effect_rows: List[Any], *, cooldown_turns: int = 0, slot_index: int | None = None) -> AbilityUseResult:
        self._bind_scheduler(ctx)
        # Turn-lock / stun gate (StateID=35 or aura meta state_ids includes 35)
        if hasattr(ctx, "teams") and ctx.teams is not None:
            if not ctx.teams.can_act(getattr(actor, "id", 0), ctx):
                if hasattr(ctx, "log"):
                    ctx.log.cannot_act(getattr(actor, "id", 0), reason="TURN_LOCK")
                from engine.core.executor import TurnExecResult
                return AbilityUseResult(turn_result=TurnExecResult(executed_count=0, stopped=True, stop_reason="CANNOT_ACT", last_effect_result=None), cooldown_set=0)
        # Apply pending lock-next-ability (Prop129) on ability usage
        if hasattr(ctx, "teams") and ctx.teams is not None:
            ability_id = effect_rows[0].ability_id if effect_rows else 0
            ctx.teams.on_pet_use_ability(getattr(actor, "id", 0), slot_index=slot_index, ability_id=ability_id)
        tr = self.turn_executor.execute_turn(ctx, actor, target, effect_rows)

        cd = int(cooldown_turns)
        if cd > 0 and hasattr(ctx, "cooldowns"):
            ability_id = effect_rows[0].ability_id if effect_rows else 0
            # Apply per-slot cooldown modifier (opcode 246). Modifier is added to the base cooldown
            # when the ability is used.
            if slot_index is not None and hasattr(ctx, "cooldown_mods") and ctx.cooldown_mods is not None:
                try:
                    mod = int(ctx.cooldown_mods.get((int(actor.id), int(slot_index)), 0))
                except Exception:
                    mod = 0
                cd = max(0, int(cd) + int(mod))

            ctx.cooldowns.set(actor.id, ability_id, cd)
            ctx.log.cooldown_set(actor.id, ability_id, cd)

        return AbilityUseResult(turn_result=tr, cooldown_set=cd)


    def use_ability_id(self, ctx: Any, actor: Any, target: Any, ability_id: int, *, slot_index: int | None = None) -> AbilityUseResult:
        """Execute an ability by ID using ScriptDB (ability pack) as the source of truth.

        Requirements:
          - ctx.scripts must be a ScriptDB (or compatible) that provides get_ability_cast_turns() and get_ability_cooldown().
          - Cast turns are executed in ascending order of their turn_order_index (already compiled into EffectRow.order_index).
          - STOP_ABILITY from any effect stops the remaining cast turns.
        """
        self._bind_scheduler(ctx)

        aid = int(ability_id)

        # Turn-lock / stun gate
        if hasattr(ctx, "teams") and ctx.teams is not None:
            if not ctx.teams.can_act(getattr(actor, "id", 0), ctx):
                if hasattr(ctx, "log"):
                    ctx.log.cannot_act(getattr(actor, "id", 0), reason="TURN_LOCK")
                return AbilityUseResult(
                    turn_result=TurnExecResult(executed_count=0, stopped=True, stop_reason="CANNOT_ACT", last_effect_result=None),
                    cooldown_set=0,
                )

        # Cooldown gate
        if hasattr(ctx, "cooldowns") and ctx.cooldowns is not None:
            rem = int(ctx.cooldowns.get(getattr(actor, "id", 0), aid))
            if rem > 0:
                if hasattr(ctx, "log"):
                    # Use existing logging channel; keep stable for tests.
                    ctx.log.cannot_act(getattr(actor, "id", 0), reason=f"COOLDOWN:{rem}")
                return AbilityUseResult(
                    turn_result=TurnExecResult(executed_count=0, stopped=True, stop_reason="COOLDOWN", last_effect_result=None),
                    cooldown_set=0,
                )

        # Apply pending lock-next-ability (Prop129) on ability usage
        if hasattr(ctx, "teams") and ctx.teams is not None:
            ctx.teams.on_pet_use_ability(getattr(actor, "id", 0), slot_index=slot_index, ability_id=aid)

        scripts = getattr(ctx, "scripts", None)
        if scripts is None or not hasattr(scripts, "get_ability_cast_turns"):
            if hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row=type("X", (), {"prop_id": -1})(), code="NO_SCRIPTS", detail={"ability_id": aid})
            return AbilityUseResult(
                turn_result=TurnExecResult(executed_count=0, stopped=True, stop_reason="NO_SCRIPT", last_effect_result=None),
                cooldown_set=0,
            )

        cast_turns = scripts.get_ability_cast_turns(aid)
        if not cast_turns:
            if hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row=type("X", (), {"prop_id": -1})(), code="NO_CAST", detail={"ability_id": aid})
            return AbilityUseResult(
                turn_result=TurnExecResult(executed_count=0, stopped=True, stop_reason="NO_CAST", last_effect_result=None),
                cooldown_set=0,
            )

        executed_total = 0
        stop_reason = None
        last_effect_result = None

        for rows in cast_turns:
            tr = self.turn_executor.execute_turn(ctx, actor, target, rows)
            executed_total += int(tr.executed_count)
            last_effect_result = tr.last_effect_result
            if tr.stopped and tr.stop_reason == "STOP_ABILITY":
                stop_reason = "STOP_ABILITY"
                break

        turn_result = TurnExecResult(
            executed_count=executed_total,
            stopped=stop_reason is not None,
            stop_reason=stop_reason,
            last_effect_result=last_effect_result,
        )

        cd = 0
        if hasattr(scripts, "get_ability_cooldown"):
            cd = int(scripts.get_ability_cooldown(aid) or 0)

        # Apply per-slot cooldown modifier (opcode 246).
        if cd > 0 and slot_index is not None and hasattr(ctx, "cooldown_mods") and ctx.cooldown_mods is not None:
            try:
                mod = int(ctx.cooldown_mods.get((int(getattr(actor, "id", 0)), int(slot_index)), 0))
            except Exception:
                mod = 0
            cd = max(0, int(cd) + int(mod))

        if cd > 0 and hasattr(ctx, "cooldowns") and ctx.cooldowns is not None:
            ctx.cooldowns.set(getattr(actor, "id", 0), aid, cd)
            if hasattr(ctx, "log"):
                ctx.log.cooldown_set(getattr(actor, "id", 0), aid, cd)

        return AbilityUseResult(turn_result=turn_result, cooldown_set=cd)

