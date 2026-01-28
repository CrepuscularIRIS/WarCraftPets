from dataclasses import dataclass, field
from typing import Any, List, Tuple, Optional

@dataclass
class EventBus:
    events: List[Tuple[Any, Any]] = field(default_factory=list)
    logger: Optional[Any] = None

    def emit(self, ev, payload=None):
        self.events.append((ev, payload))
        if self.logger is not None:
            try:
                self.logger.log(ev, payload)
            except Exception:
                pass

    def set_logger(self, logger: Optional[Any]) -> None:
        self.logger = logger
