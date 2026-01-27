from enum import Enum

class Event(str, Enum):
    TURN_START = "TURN_START"
    TURN_END = "TURN_END"
    ON_DAMAGE = "ON_DAMAGE"
    ON_HEAL = "ON_HEAL"
    ON_MISS = "ON_MISS"

# Backward/forward compatible alias
BattleEvent = Event
