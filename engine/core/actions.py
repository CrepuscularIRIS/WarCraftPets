from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ActionKind(str, Enum):
    """Battle-level action kind.

    This layer is intentionally higher-level than EffectRow/Opcode handling.
    It is the interface boundary for RL policies / scripted agents.
    """

    USE_ABILITY = "USE_ABILITY"
    SWAP = "SWAP"
    PASS = "PASS"


@dataclass(frozen=True)
class BattleAction:
    kind: ActionKind

    # USE_ABILITY fields
    ability_id: int = 0
    slot_index: int = 0  # 1..3 for normal abilities; 0 allowed for "unknown" slot

    # SWAP fields
    swap_index: int = -1  # target pet index in team roster

    # Diagnostics / stable debug
    note: Optional[str] = None
