"""Pet battle family type advantage table.

The project uses DB2-exported numeric IDs (0..9):
  0 humanoid
  1 dragonkin
  2 flying
  3 undead
  4 critter
  5 magic
  6 elemental
  7 beast
  8 aquatic
  9 mechanical

Damage multipliers:
  - strong: 1.5
  - weak: 2/3

This is stable WoW pet battle ruleset (MoP+).
"""

from __future__ import annotations

from typing import Dict, Tuple


STRONG_MULT: float = 1.5
WEAK_MULT: float = 2.0 / 3.0


# (attack_type -> target_type) mapping. If attack_type is strong against target_type => STRONG_MULT.
# Source of the mapping is the standard in-game family chart.
STRONG_AGAINST: Dict[int, int] = {
    0: 1,  # Humanoid > Dragonkin
    1: 5,  # Dragonkin > Magic
    2: 8,  # Flying > Aquatic
    3: 0,  # Undead > Humanoid
    4: 3,  # Critter > Undead
    5: 2,  # Magic > Flying
    6: 9,  # Elemental > Mechanical
    7: 4,  # Beast > Critter
    8: 6,  # Aquatic > Elemental
    9: 7,  # Mechanical > Beast
}


# If attack_type is weak against target_type => WEAK_MULT.
WEAK_AGAINST: Dict[int, int] = {
    0: 3,  # Humanoid < Undead
    1: 0,  # Dragonkin < Humanoid
    2: 1,  # Flying < Dragonkin
    3: 4,  # Undead < Critter
    4: 7,  # Critter < Beast
    5: 9,  # Magic < Mechanical
    6: 8,  # Elemental < Aquatic
    7: 9,  # Beast < Mechanical
    8: 2,  # Aquatic < Flying
    9: 6,  # Mechanical < Elemental
}


def type_multiplier(attack_type: int, target_type: int) -> Tuple[float, str]:
    """Return (multiplier, reason)."""
    try:
        a = int(attack_type)
        t = int(target_type)
    except Exception:
        return 1.0, "TYPE_UNKNOWN"

    if STRONG_AGAINST.get(a) == t:
        return STRONG_MULT, "STRONG"
    if WEAK_AGAINST.get(a) == t:
        return WEAK_MULT, "WEAK"
    return 1.0, "NEUTRAL"
