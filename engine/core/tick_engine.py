from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from engine.core.events import Event
from engine.core.executor import AbilityTurnExecutor

@dataclass
class TickSummary:
    event: Event
    periodic_triggers: int
    expired_auras: int

class TickEngine:
    # Centralized event tick system.
    #
    # Responsibilities (v1):
    # - Periodic ticks (DOT/HOT) bound to aura instances:
    #     aura.periodic_payloads[event] (preferred), or legacy aura.periodic_effect_rows + aura.periodic_timing
    # - Aura duration decrement + expire on TURN_END by default (after periodic ticks)
    #
    # Determinism:
    # - TURN_END: (1) periodic ticks, (2) decrement duration, (3) expire at 0.

    def __init__(self):
        self.turn_executor = AbilityTurnExecutor()

    def process_event(self, ctx: Any, pets: List[Any], event: Event) -> TickSummary:
        periodic_triggers = 0
        expired_auras = 0

        if hasattr(ctx, "aura"):
            for owner in pets:
                for aura in ctx.aura.list_owner(owner.id).values():
                    # Preferred payloads mapping
                    rows = None
                    payloads = getattr(aura, "periodic_payloads", None)
                    if isinstance(payloads, dict):
                        rows = payloads.get(event.value)

                    # Legacy fallback
                    if not rows:
                        timing = getattr(aura, "periodic_timing", Event.TURN_END.value)
                        if str(timing) == event.value:
                            rows = getattr(aura, "periodic_effect_rows", None)

                    if not rows:
                        continue

                    actor = next((p for p in pets if p.id == aura.caster_pet_id), None)
                    if actor is None:
                        continue
                    self.turn_executor.execute_turn(ctx, actor, owner, rows)
                    periodic_triggers += 1

        if event == Event.TURN_END and hasattr(ctx, "aura"):
            for owner in pets:
                expired = ctx.aura.tick(owner.id)
                for ex in expired:
                    expired_auras += 1
                    if hasattr(ctx, "log"):
                        ctx.log.aura_expire(ex.owner_pet_id, ex.aura_id)

        # If a weather-providing aura expired, refresh cached weather.
        wm = getattr(ctx, "weather", None)
        if wm is not None and hasattr(wm, "clear_if_gone"):
            try:
                wm.clear_if_gone(ctx)
            except Exception:
                pass

        return TickSummary(event=event, periodic_triggers=periodic_triggers, expired_auras=expired_auras)
