from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class EffectResult:
    executed: bool
    flow_control: str = "CONTINUE"
    spawned_events: List[Any] = field(default_factory=list)
    spawned_damage_events: List[Any] = field(default_factory=list)
    aura_ops: List[Any] = field(default_factory=list)
    state_ops: List[Any] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)
