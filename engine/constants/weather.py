"""Weather state IDs and a minimal effect registry.

DB2 `BattlePetState` contains a group of states named `Weather_*`.
In live WoW these are battlefield-wide effects ("weather"), typically set by an aura.

This engine treats weather as a *global* modifier (even if represented by per-pet auras
in the source data). We detect the active weather by scanning aura meta `state_binds`
for a `Weather_*` state id.

NOTE: Weather in WoW has many special cases (extra secondary effects, CC immunities, etc).
For v1 we implement only the most common numeric modifiers used by damage/heal/hit:
  - Moonlight: +10% Magic damage, +25% healing received
  - Darkness: -50% healing received, -10% hit chance
  - Cleansing Rain: +25% Aquatic damage
  - Lightning Storm: +25% Mechanical damage, +flat mechanical bonus damage
  - Sandstorm: -flat damage taken, -10% hit chance

Other weather-specific behaviors can be layered later via opcode semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


# Weather state IDs (from this repo's DB2 export: BattlePetState.lua_name == "Weather_*")
#
# IMPORTANT:
#   These IDs are export-dependent. In this engine skeleton, we align them to
#   `petbattle_ability_pack.v1.release.json` where the aura meta bindings use:
#     53 Weather_BurntEarth
#     54 Weather_ArcaneStorm
#     55 Weather_Moonlight
#     56 Weather_Darkness
#     57 Weather_Sandstorm
#     58 Weather_Blizzard
#     59 Weather_Mud
#     60 Weather_Rain
#     61 Weather_Sunlight
#     62 Weather_LightningStorm
#     316 Weather_Toxic_Gas
WEATHER_BURNT_EARTH = 53
WEATHER_ARCANE_STORM = 54
WEATHER_MOONLIGHT = 55
WEATHER_DARKNESS = 56
WEATHER_SANDSTORM = 57
WEATHER_BLIZZARD = 58
WEATHER_MUD = 59
WEATHER_RAIN = 60
WEATHER_SUNLIGHT = 61
WEATHER_LIGHTNING_STORM = 62
WEATHER_TOXIC_GAS = 316


WEATHER_STATE_IDS = {
    WEATHER_ARCANE_STORM,
    WEATHER_DARKNESS,
    WEATHER_MOONLIGHT,
    WEATHER_RAIN,
    WEATHER_SANDSTORM,
    WEATHER_LIGHTNING_STORM,
    WEATHER_SUNLIGHT,
    WEATHER_BLIZZARD,
    WEATHER_MUD,
    WEATHER_BURNT_EARTH,
    WEATHER_TOXIC_GAS,
}


@dataclass(frozen=True)
class WeatherEffect:
    # Multipliers are applied on top of state-based modifiers.
    damage_mult_by_attack_type: Dict[int, float]
    heal_taken_mult: float = 1.0
    hit_chance_add: float = 0.0  # additive on normalized 0..1 accuracy
    flat_damage_taken_add: int = 0  # additive flat applied late (negative reduces damage)


WEATHER_EFFECTS: Dict[int, WeatherEffect] = {
    WEATHER_MOONLIGHT: WeatherEffect(
        damage_mult_by_attack_type={5: 1.10},  # Magic abilities
        heal_taken_mult=1.25,
    ),
    WEATHER_DARKNESS: WeatherEffect(
        damage_mult_by_attack_type={},
        heal_taken_mult=0.50,
        hit_chance_add=-0.10,
    ),
    WEATHER_RAIN: WeatherEffect(
        damage_mult_by_attack_type={8: 1.25},  # Aquatic abilities
        heal_taken_mult=1.0,
    ),
    WEATHER_LIGHTNING_STORM: WeatherEffect(
        damage_mult_by_attack_type={9: 1.25},  # Mechanical abilities
        flat_damage_taken_add=39,
    ),
    WEATHER_SANDSTORM: WeatherEffect(
        damage_mult_by_attack_type={},
        hit_chance_add=-0.10,
        flat_damage_taken_add=-99,
    ),
}


def get_weather_effect(weather_state_id: int) -> Optional[WeatherEffect]:
    try:
        return WEATHER_EFFECTS.get(int(weather_state_id))
    except Exception:
        return None
