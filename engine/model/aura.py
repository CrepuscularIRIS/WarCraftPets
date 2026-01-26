from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class AuraInstance:
    aura_id: int
    owner_pet_id: int
    caster_pet_id: int
    source_effect_id: int
    remaining_duration: int  # -1 => permanent
    tickdown_first_round: bool = False
    stacks: int = 1

    # Backward-compatible single payload (older usage)
    periodic_timing: str = "TURN_END"   # "TURN_START" | "TURN_END"
    periodic_effect_rows: Optional[List[Any]] = None

    # Preferred: multiple payloads per event
    periodic_payloads: Dict[str, List[Any]] = field(default_factory=dict)

    # Metadata for downstream systems (UI/RL/dispel)
    meta: Dict[str, Any] = field(default_factory=dict)
