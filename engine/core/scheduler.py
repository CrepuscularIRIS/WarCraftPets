from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

@dataclass
class ScheduledPacket:
    remaining_turns: int
    actor_id: int
    target_id: int
    effect_rows: List[Any]
    tag: str = "scheduled"

class Scheduler:
    def __init__(self):
        self._queue: List[ScheduledPacket] = []

    def schedule(self, *, delay_turns: int, actor_id: int, target_id: int, effect_rows: List[Any], tag: str = "scheduled") -> None:
        d = int(delay_turns)
        if d < 0:
            d = 0
        self._queue.append(ScheduledPacket(remaining_turns=d, actor_id=int(actor_id), target_id=int(target_id), effect_rows=list(effect_rows), tag=tag))

    def tick(self) -> List[ScheduledPacket]:
        ready: List[ScheduledPacket] = []
        for pkt in self._queue:
            pkt.remaining_turns -= 1
        still: List[ScheduledPacket] = []
        for pkt in self._queue:
            if pkt.remaining_turns <= 0:
                ready.append(pkt)
            else:
                still.append(pkt)
        self._queue = still
        return ready
