from dataclasses import dataclass, field
from typing import Any, List, Tuple

@dataclass
class EventBus:
    events: List[Tuple[Any, Any]] = field(default_factory=list)

    def emit(self, ev, payload=None):
        self.events.append((ev, payload))
