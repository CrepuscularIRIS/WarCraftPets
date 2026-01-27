#!/usr/bin/env python3
"""
WoW Pet Battle Simulator - 魔兽世界宠物对战模拟器

完整实现魔兽世界宠物对战系统，包括：
- 回合制战斗与速度先手判定
- 10种宠物类型与属性克制（强克+50%，弱克-33.3%）
- 10种种族被动技能
- 天气系统（月光、黑暗、沙尘暴等）
- Buff/Debuff/Aura系统
- DoT/HoT持续效果
- 多回合技能
- 技能冷却

Usage:
    python main.py                  # 运行演示战斗
    python main.py --help           # 显示帮助
    python main.py --help-rules     # 显示游戏规则
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

# Engine imports
from engine.core.team_manager import TeamManager
from engine.core.event_bus import EventBus
from engine.resolver.aura_manager import AuraManager
from engine.resolver.cooldown import CooldownManager
from engine.resolver.state_manager import StateManager
from engine.resolver.stats_resolver import StatsResolver
from engine.resolver.weather_manager import WeatherManager
from engine.resolver.racial_passives import RacialPassiveManager
from engine.pets.pet_instance import PetInstance
from engine.pets.progression import ProgressionDB
from engine.pets.pet_stats import PetStatsCalculator
from engine.constants.type_advantage import type_multiplier, STRONG_MULT, WEAK_MULT
from engine.constants.weather import (
    WEATHER_STATE_IDS, WEATHER_MOONLIGHT, WEATHER_DARKNESS,
    WEATHER_SANDSTORM, WEATHER_RAIN, WEATHER_LIGHTNING_STORM,
    get_weather_effect
)


# =============================================================================
# 常量定义
# =============================================================================

PET_TYPE_NAMES_ZH = {
    0: "人型", 1: "龙类", 2: "飞行", 3: "不死", 4: "小动物",
    5: "魔法", 6: "元素", 7: "野兽", 8: "水生", 9: "机械"
}

PET_TYPE_NAMES_EN = {
    0: "Humanoid", 1: "Dragonkin", 2: "Flying", 3: "Undead", 4: "Critter",
    5: "Magic", 6: "Elemental", 7: "Beast", 8: "Aquatic", 9: "Mechanical"
}

RACIAL_PASSIVE_DESC_ZH = {
    0: "人型：造成伤害后回复4%最大生命值",
    1: "龙类：将目标打到25%生命值以下后，下一轮伤害+50%",
    2: "飞行：生命值高于50%时速度+50%",
    3: "不死：死亡后复活1回合（无敌），然后正式死亡",
    4: "小动物：更快从控制效果中恢复",
    5: "魔法：单次受到的伤害不超过最大生命值的35%",
    6: "元素：忽略所有天气效果",
    7: "野兽：生命值低于50%时伤害+25%",
    8: "水生：受到的持续伤害减少50%",
    9: "机械：死亡后以20%生命值复活一次",
}

WEATHER_NAMES_ZH = {
    WEATHER_MOONLIGHT: "月光",
    WEATHER_DARKNESS: "黑暗",
    WEATHER_SANDSTORM: "沙尘暴",
    WEATHER_RAIN: "清洁之雨",
    WEATHER_LIGHTNING_STORM: "闪电风暴",
}

# 技能中文名称映射（常用技能）
ABILITY_NAMES_ZH = {
    429: "爪击", 535: "突袭", 492: "斜掠", 357: "尖啸",
    538: "吞食", 536: "潜行", 459: "啃咬", 334: "毒牙",
    385: "抽打", 381: "猛击", 382: "冲撞", 518: "致命俯冲",
    307: "水流喷射", 308: "治疗波", 309: "潮汐波",
    # 添加更多常用技能...
}


# =============================================================================
# 日志系统
# =============================================================================

class BattleLogger:
    """战斗日志记录器，同时输出到终端和文件"""

    def __init__(self, log_file: Optional[str] = None, verbose: bool = True):
        self.verbose = verbose
        self.log_file = log_file
        self.records: List[str] = []

        # 设置日志文件
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = f"battle_log_{timestamp}.txt"

        # 创建文件
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 魔兽世界宠物对战日志 ===\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"
        self.records.append(formatted)

        # 输出到终端
        if self.verbose:
            print(message)

        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(message + "\n")

    def separator(self, char: str = "-", length: int = 60):
        self.log(char * length)

    def header(self, text: str):
        self.separator("=")
        self.log(text)
        self.separator("=")

    def damage(self, attacker: str, target: str, damage: int, damage_type: str,
               type_mult: float, type_reason: str, is_crit: bool = False,
               is_periodic: bool = False, extra_info: str = ""):
        """记录伤害事件"""
        crit_str = " [暴击!]" if is_crit else ""
        periodic_str = " (持续)" if is_periodic else ""
        type_str = ""
        if type_reason == "STRONG":
            type_str = f" [克制x{type_mult:.2f}]"
        elif type_reason == "WEAK":
            type_str = f" [被克x{type_mult:.2f}]"

        msg = f"  💥 {attacker} -> {target}: {damage} {damage_type}伤害{type_str}{crit_str}{periodic_str}"
        if extra_info:
            msg += f" ({extra_info})"
        self.log(msg)

    def heal(self, source: str, target: str, heal_amount: int, heal_type: str = ""):
        """记录治疗事件"""
        self.log(f"  💚 {source} -> {target}: +{heal_amount} 治疗 {heal_type}")

    def dot_tick(self, target: str, damage: int, dot_name: str):
        """记录DoT跳伤"""
        self.log(f"  🔥 {target} 受到 {dot_name} 伤害: {damage}")

    def weather(self, weather_name: str, duration: int):
        """记录天气变化"""
        self.log(f"  🌤️ 天气变化: {weather_name} (持续{duration}回合)")

    def buff(self, target: str, buff_name: str, duration: int, is_debuff: bool = False):
        """记录Buff/Debuff"""
        icon = "⬇️" if is_debuff else "⬆️"
        self.log(f"  {icon} {target} 获得: {buff_name} ({duration}回合)")

    def pet_death(self, pet_name: str, revived: bool = False, passive_name: str = ""):
        """记录宠物死亡"""
        if revived:
            self.log(f"  💀 {pet_name} 被击败! -> 🔄 {passive_name}被动触发，复活!")
        else:
            self.log(f"  💀 {pet_name} 被击败!")

    def swap(self, team_name: str, old_pet: str, new_pet: str, forced: bool = False):
        """记录换宠"""
        swap_type = "强制换宠" if forced else "换宠"
        self.log(f"  🔄 {team_name} {swap_type}: {old_pet} -> {new_pet}")

    def round_start(self, round_no: int):
        """记录回合开始"""
        self.log(f"\n{'─' * 20} 第 {round_no} 回合 {'─' * 20}")

    def speed_info(self, pet0_name: str, speed0: int, pet1_name: str, speed1: int, first: str):
        """记录速度信息"""
        self.log(f"  ⚡ 速度: {pet0_name}={speed0} vs {pet1_name}={speed1} | 先手: {first}")


# =============================================================================
# 随机数生成器
# =============================================================================

@dataclass
class RandomRNG:
    """随机数生成器"""
    seed: Optional[int] = None
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        if self.seed is not None:
            self._rng = random.Random(self.seed)
        else:
            self._rng = random.Random()

    def rand_hit(self) -> float:
        return self._rng.random()

    def rand_gate(self) -> float:
        return self._rng.random()

    def rand_variance(self) -> float:
        return 0.95 + self._rng.random() * 0.1

    def rand_crit(self) -> float:
        return self._rng.random()


# =============================================================================
# 数据加载器
# =============================================================================

class DataLoader:
    """加载宠物和技能数据"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.pets_data: Dict[int, dict] = {}
        self.abilities_data: Dict[int, dict] = {}
        self.progression: dict = {}
        self.progression_db: Optional[ProgressionDB] = None
        self.pet_stats_calculator: Optional[PetStatsCalculator] = None

    def load_all(self):
        """加载所有数据"""
        self._load_pets()
        self._load_abilities()
        self._load_progression()
        self._init_pet_stats_calculator()

    def _load_pets(self):
        """加载宠物数据"""
        pets_file = self.base_path / "pets_template.jsonc"
        if pets_file.exists():
            with open(pets_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 移除注释
                content = re.sub(r'//.*', '', content)
                pets_list = json.loads(content)
                for pet in pets_list:
                    self.pets_data[pet['ID']] = pet

    def _load_abilities(self):
        """加载技能数据"""
        ability_file = self.base_path / "data" / "petbattle_ability_pack.v1.debug.jsonc"
        if ability_file.exists():
            with open(ability_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 移除注释
                content = re.sub(r'//.*', '', content)
                data = json.loads(content)
                for ability in data.get('abilities', []):
                    self.abilities_data[ability['ability_id']] = ability

    def _load_progression(self):
        """加载成长表"""
        prog_file = self.base_path / "pet_progression_tables.json"
        if prog_file.exists():
            with open(prog_file, 'r', encoding='utf-8') as f:
                self.progression = json.load(f)

    def _init_pet_stats_calculator(self):
        """初始化宠物属性计算器"""
        prog_file = self.base_path / "pet_progression_tables.json"
        if prog_file.exists():
            try:
                self.progression_db = ProgressionDB(prog_file)
                self.pet_stats_calculator = PetStatsCalculator(self.progression_db)
            except Exception as e:
                print(f"警告: 无法初始化PetStatsCalculator: {e}")

    def get_pet_name(self, pet_id: int) -> Tuple[str, str]:
        """获取宠物名称 (中文, 英文)"""
        pet = self.pets_data.get(pet_id, {})
        names = pet.get('Names', {})
        return names.get('zh', f'宠物{pet_id}'), names.get('en', f'Pet{pet_id}')

    def get_ability_name(self, ability_id: int) -> Tuple[str, str]:
        """获取技能名称 (中文, 英文)"""
        # 先从预定义映射查找
        zh_name = ABILITY_NAMES_ZH.get(ability_id)
        if zh_name:
            return zh_name, self.abilities_data.get(ability_id, {}).get('name', {}).get('en', f'Ability{ability_id}')

        # 从数据文件查找
        ability = self.abilities_data.get(ability_id, {})
        name = ability.get('name', {})
        zh = name.get('zh', '') or f'技能{ability_id}'
        en = name.get('en', '') or f'Ability{ability_id}'
        return zh, en

    def get_ability_panel_damage(self, ability_id: int, power: int) -> int:
        """获取技能面板伤害值

        使用公式: floor(base_points * (1 + power/20))
        """
        ability_info = self.abilities_data.get(ability_id, {})
        base_points = self._get_ability_points(ability_info)
        return int(math.floor(base_points * (1.0 + power / 20.0)))

    def _get_ability_points(self, ability_info: dict) -> int:
        """从技能数据中提取伤害点数"""
        cast = ability_info.get('cast', {})
        turns = cast.get('turns', [])
        if not turns:
            return 20  # 默认值

        for turn in turns:
            for effect in turn.get('effects', []):
                params = effect.get('params_raw', [])
                if params and len(params) > 0:
                    # 第一个参数通常是伤害点数
                    points = params[0]
                    if 10 <= points <= 100:  # 合理范围
                        return points

        return 20  # 默认值

    def calculate_stats(self, base_hp: float, base_power: float, base_speed: float,
                        level: int, rarity_id: int, breed_id: int) -> Tuple[int, int, int]:
        """计算宠物属性

        公式:
            stat = floor((base_stat + breed_add) * level * quality_mult) + 100 (仅HP)
        """
        quality_mult = self.progression.get('quality_multiplier', {}).get(str(rarity_id), 0.65)
        breed = self.progression.get('breed_stats', {}).get(str(breed_id), {})
        health_add = breed.get('health_add', 0.5)
        power_add = breed.get('power_add', 0.5)
        speed_add = breed.get('speed_add', 0.5)

        hp = int(math.floor((base_hp + health_add) * level * quality_mult)) + 100
        power = int(math.floor((base_power + power_add) * level * quality_mult))
        speed = int(math.floor((base_speed + speed_add) * level * quality_mult))

        return hp, power, speed


# =============================================================================
# 战斗上下文
# =============================================================================

class BattleContext:
    """战斗上下文，包含所有战斗状态"""

    def __init__(
        self,
        pets: Dict[int, PetInstance],
        teams: TeamManager,
        logger: BattleLogger,
        data_loader: DataLoader,
        seed: Optional[int] = None,
    ):
        self.pets = pets
        self.teams = teams
        self.logger = logger
        self.data = data_loader

        # RNG
        self.rng = RandomRNG(seed=seed)

        # 状态管理器
        self.states = StateManager()
        self.aura = AuraManager()
        self.cooldowns = CooldownManager()
        self.weather = WeatherManager()
        self.event_bus = EventBus()

        # 解析器
        self.stats = StatsResolver()

        # 种族被动
        self.racial = RacialPassiveManager()

        # 战斗状态
        self.btl = SimpleNamespace()
        self.btl.round_no = 0
        self.btl.current_weather = 0
        self.btl.weather_duration = 0

        # 配置
        self.crit_chance = 0.05
        self.crit_mult = 1.5

        # DoT追踪
        self.dots: Dict[int, List[dict]] = {}  # pet_id -> list of DoT effects

    def get_active_weather_name(self) -> str:
        """获取当前天气名称"""
        if self.btl.current_weather == 0:
            return "晴朗"
        return WEATHER_NAMES_ZH.get(self.btl.current_weather, f"天气{self.btl.current_weather}")


# =============================================================================
# 技能执行器
# =============================================================================

class AbilityExecutor:
    """技能执行器"""

    def __init__(self, ctx: BattleContext):
        self.ctx = ctx

    def execute_ability(self, actor: PetInstance, target: PetInstance,
                        ability_id: int, ability_name_zh: str) -> dict:
        """执行技能"""
        # 获取技能信息
        ability_info = self.ctx.data.abilities_data.get(ability_id, {})
        pet_type_enum = ability_info.get('pet_type_enum', actor.pet_type)

        # 获取技能伤害点数（从技能数据中提取）
        base_points = self._get_ability_points(ability_info)

        # 计算伤害
        power = self.ctx.stats.effective_power(self.ctx, actor.id)
        base_damage = int(math.floor(base_points * (1.0 + power / 20.0)))

        # 方差
        variance = self.ctx.rng.rand_variance()
        damage = int(base_damage * variance)

        # 类型克制
        mult, reason = type_multiplier(pet_type_enum, target.pet_type)
        damage = int(damage * mult)

        # 野兽被动：生命值低于50%时伤害+25%
        if actor.pet_type == 7:  # Beast
            if actor.hp * 2 < actor.max_hp:
                damage = int(damage * 1.25)

        # 龙类被动加成
        dragonkin_mult = self.ctx.racial.get_damage_multiplier(self.ctx, actor)
        if dragonkin_mult > 1.0:
            damage = int(damage * dragonkin_mult)

        # 魔法被动：伤害上限35%最大HP
        if target.pet_type == 5:  # Magic
            cap = int(target.max_hp * 0.35)
            if damage > cap:
                damage = cap

        # 暴击
        is_crit = False
        if self.ctx.rng.rand_crit() < self.ctx.crit_chance:
            is_crit = True
            damage = int(damage * self.ctx.crit_mult)

        # 不死无敌检查
        undead_immune = self.ctx.racial.is_undead_immortal(target)
        if undead_immune:
            damage = 0

        # 记录HP before
        hp_before = target.hp

        # 应用伤害
        actual_damage = target.take_damage(damage)

        # 通知种族被动
        self.ctx.racial.on_damage_dealt(
            self.ctx, actor, target, actual_damage,
            target_hp_before=hp_before,
            target_hp_after=target.hp
        )

        # 记录日志
        self.ctx.logger.damage(
            actor.name_zh, target.name_zh, actual_damage,
            PET_TYPE_NAMES_ZH.get(pet_type_enum, "物理"),
            mult, reason, is_crit
        )

        return {
            "ability_id": ability_id,
            "ability_name": ability_name_zh,
            "base_points": base_points,
            "base_damage": base_damage,
            "variance": variance,
            "type_mult": mult,
            "type_reason": reason,
            "is_crit": is_crit,
            "actual_damage": actual_damage,
            "target_hp": target.hp,
        }

    def _get_ability_points(self, ability_info: dict) -> int:
        """从技能数据中提取伤害点数"""
        cast = ability_info.get('cast', {})
        turns = cast.get('turns', [])
        if not turns:
            return 20  # 默认值

        for turn in turns:
            for effect in turn.get('effects', []):
                params = effect.get('params_raw', [])
                if params and len(params) > 0:
                    # 第一个参数通常是伤害点数
                    points = params[0]
                    if 10 <= points <= 100:  # 合理范围
                        return points

        return 20  # 默认值


# =============================================================================
# 战斗模拟器
# =============================================================================

def create_pet_from_data(data_loader: DataLoader, pet_id: int, instance_id: int,
                         level: int = 25, rarity_id: int = 4, breed_id: int = 3,
                         ability_choices: List[int] = None) -> PetInstance:
    """从数据创建宠物实例"""
    pet_data = data_loader.pets_data.get(pet_id, {})

    name_zh, name_en = data_loader.get_pet_name(pet_id)
    pet_type = pet_data.get('PetType', 0)

    # 使用PetStatsCalculator计算属性
    # 首先尝试使用新的计算器
    hp, power, speed = None, None, None
    if data_loader.pet_stats_calculator:
        try:
            pet_stats = data_loader.pet_stats_calculator.calculate(
                pet_id=pet_id,
                rarity_id=rarity_id,
                breed_id=breed_id,
                level=level
            )
            hp, power, speed = pet_stats.health, pet_stats.power, pet_stats.speed
        except KeyError:
            # 如果新计算器失败，使用旧的方法
            pass

    # 如果新计算器失败，回退到旧的计算方法
    if hp is None:
        base_stats = pet_data.get('BaseStats', {})
        base_hp = base_stats.get('HP', 8.0)
        base_power = base_stats.get('Power', 8.0)
        base_speed = base_stats.get('Speed', 8.0)
        hp, power, speed = data_loader.calculate_stats(
            base_hp, base_power, base_speed, level, rarity_id, breed_id
        )

    # 选择技能（每个槽位选第一个）
    ability_pool = pet_data.get('AbilityPool', {})
    abilities = {}
    ability_names = {}

    for slot_str, options in ability_pool.items():
        slot = int(slot_str)
        if options:
            # 如果指定了选择，使用指定的
            if ability_choices and slot < len(ability_choices):
                choice_idx = ability_choices[slot]
                if choice_idx < len(options):
                    ability_id = options[choice_idx]
                else:
                    ability_id = options[0]
            else:
                ability_id = options[0]

            abilities[slot + 1] = ability_id  # 槽位1-3
            zh_name, en_name = data_loader.get_ability_name(ability_id)
            ability_names[slot + 1] = {'zh': zh_name, 'en': en_name}

    pet = PetInstance(
        id=instance_id,
        pet_id=pet_id,
        rarity_id=rarity_id,
        breed_id=breed_id,
        level=level,
        pet_type=pet_type,
        name_en=name_en,
        name_zh=name_zh,
        base_max_hp=hp,
        base_power=power,
        base_speed=speed,
        max_hp=hp,
        hp=hp,
        power=power,
        speed=speed,
        abilities=abilities,
        ability_names=ability_names,
    )

    return pet


def run_battle(
    data_loader: DataLoader,
    team0_pet_ids: List[int],
    team1_pet_ids: List[int],
    level: int = 25,
    rarity_id: int = 4,
    seed: Optional[int] = None,
    max_rounds: int = 25,
    log_file: Optional[str] = None,
) -> int:
    """运行战斗

    所有宠物统一使用:
      - 等级: level (默认 25)
      - 品质: rarity_id (默认 4 = 精良蓝色)

    返回获胜队伍ID (0或1)，-1为平局
    """
    # 创建日志
    logger = BattleLogger(log_file=log_file, verbose=True)

    # 创建宠物
    pets: Dict[int, PetInstance] = {}
    team0_ids = []
    team1_ids = []

    for i, pet_id in enumerate(team0_pet_ids):
        instance_id = 100 + i
        # 使用该宠物可用的breed
        pet_data = data_loader.pets_data.get(pet_id, {})
        available_breeds = pet_data.get('AvailableBreeds', [3])
        breed_id = available_breeds[0] if available_breeds else 3

        pet = create_pet_from_data(data_loader, pet_id, instance_id, level, rarity_id, breed_id)
        pets[instance_id] = pet
        team0_ids.append(instance_id)

    for i, pet_id in enumerate(team1_pet_ids):
        instance_id = 200 + i
        pet_data = data_loader.pets_data.get(pet_id, {})
        available_breeds = pet_data.get('AvailableBreeds', [3])
        breed_id = available_breeds[0] if available_breeds else 3

        pet = create_pet_from_data(data_loader, pet_id, instance_id, level, rarity_id, breed_id)
        pets[instance_id] = pet
        team1_ids.append(instance_id)

    # 创建队伍
    teams = TeamManager()
    teams.register_team(0, team0_ids, active_index=0)
    teams.register_team(1, team1_ids, active_index=0)

    # 创建上下文
    ctx = BattleContext(pets=pets, teams=teams, logger=logger, data_loader=data_loader, seed=seed)
    executor = AbilityExecutor(ctx)

    # 打印战斗信息
    logger.header("魔兽世界宠物对战模拟器")
    logger.log(f"随机种子: {seed}")
    logger.log(f"等级: {level} | 品质: {'蓝色(精良)' if rarity_id == 4 else f'品质{rarity_id}'}")
    logger.log("")

    logger.log("队伍0:")
    for pid in team0_ids:
        pet = pets[pid]
        type_zh = PET_TYPE_NAMES_ZH.get(pet.pet_type, "未知")
        logger.log(f"  {pet.name_zh} [{type_zh}] HP:{pet.hp} 力量:{pet.power} 速度:{pet.speed}")

        # 显示技能和面板伤害
        for slot in sorted(pet.abilities.keys()):
            ability_id = pet.abilities[slot]
            ability_name = pet.ability_names.get(slot, {}).get('zh', '未知')
            panel_damage = data_loader.get_ability_panel_damage(ability_id, pet.power)
            logger.log(f"    技能{slot}: {ability_name} (面板伤害: {panel_damage})")

    logger.log("")
    logger.log("队伍1:")
    for pid in team1_ids:
        pet = pets[pid]
        type_zh = PET_TYPE_NAMES_ZH.get(pet.pet_type, "未知")
        logger.log(f"  {pet.name_zh} [{type_zh}] HP:{pet.hp} 力量:{pet.power} 速度:{pet.speed}")

        # 显示技能和面板伤害
        for slot in sorted(pet.abilities.keys()):
            ability_id = pet.abilities[slot]
            ability_name = pet.ability_names.get(slot, {}).get('zh', '未知')
            panel_damage = data_loader.get_ability_panel_damage(ability_id, pet.power)
            logger.log(f"    技能{slot}: {ability_name} (面板伤害: {panel_damage})")

    logger.separator()

    # 战斗循环
    all_pets = list(pets.values())

    for round_no in range(1, max_rounds + 1):
        ctx.btl.round_no = round_no
        ctx.racial.on_round_start(ctx, all_pets)

        logger.round_start(round_no)

        # 显示天气
        if ctx.btl.current_weather != 0:
            logger.log(f"  🌤️ 当前天气: {ctx.get_active_weather_name()} (剩余{ctx.btl.weather_duration}回合)")

        # 获取当前激活宠物
        pet0_id = teams.active_pet_id(0)
        pet1_id = teams.active_pet_id(1)
        pet0 = pets.get(pet0_id)
        pet1 = pets.get(pet1_id)

        if not pet0 or not pet1:
            break

        # 确定先后手
        speed0 = ctx.stats.effective_speed(ctx, pet0.id)
        speed1 = ctx.stats.effective_speed(ctx, pet1.id)

        if speed0 > speed1:
            order = [(0, pet0, pet1), (1, pet1, pet0)]
            first_name = pet0.name_zh
        elif speed1 > speed0:
            order = [(1, pet1, pet0), (0, pet0, pet1)]
            first_name = pet1.name_zh
        else:
            if ctx.rng.rand_gate() < 0.5:
                order = [(0, pet0, pet1), (1, pet1, pet0)]
                first_name = pet0.name_zh
            else:
                order = [(1, pet1, pet0), (0, pet0, pet1)]
                first_name = pet1.name_zh

        logger.speed_info(pet0.name_zh, speed0, pet1.name_zh, speed1, first_name)

        # 执行行动
        for team_id, actor, target in order:
            if not actor.alive:
                continue
            if not target.alive:
                # 寻找替补
                opp_team_id = 1 - team_id
                new_active = find_alive_pet(teams, pets, opp_team_id)
                if new_active:
                    target = pets[new_active]
                else:
                    continue

            # 使用第一个技能
            ability_slot = 1
            ability_id = actor.abilities.get(ability_slot, 0)
            if ability_id:
                ability_name_zh = actor.ability_names.get(ability_slot, {}).get('zh', '未知技能')
                logger.log(f"  {actor.name_zh} 使用 [{ability_name_zh}]:")

                result = executor.execute_ability(actor, target, ability_id, ability_name_zh)

                # 检查目标死亡
                if not target.alive:
                    revived = ctx.racial.on_pet_death(ctx, target)
                    passive_name = RACIAL_PASSIVE_DESC_ZH.get(target.pet_type, "").split("：")[0]
                    logger.pet_death(target.name_zh, revived, passive_name)

        # 显示回合结束状态
        logger.log(f"  ── 回合结束状态 ──")
        for tid in [0, 1]:
            active_id = teams.active_pet_id(tid)
            pet = pets.get(active_id)
            if pet:
                status = f"HP:{pet.hp}/{pet.max_hp}" if pet.alive else "已阵亡"
                logger.log(f"  队伍{tid}: {pet.name_zh} {status}")

        # 回合结束处理
        ctx.racial.on_round_end(ctx, all_pets)

        # 检查胜负
        winner = check_winner(teams, pets)
        if winner is not None:
            logger.log("")
            logger.header(f"战斗结束 - 队伍{winner}获胜!")
            logger.log(f"日志已保存到: {logger.log_file}")
            return winner

        # 确保激活宠物存活
        for tid in [0, 1]:
            if ensure_active_alive(teams, pets, tid, logger):
                pass

    logger.log("")
    logger.header("战斗结束 - 平局 (回合上限)")
    logger.log(f"日志已保存到: {logger.log_file}")
    return -1


def find_alive_pet(teams: TeamManager, pets: Dict[int, PetInstance], team_id: int) -> Optional[int]:
    """找到存活的宠物"""
    team = teams.teams[team_id]
    for pid in team.pet_ids:
        pet = pets.get(pid)
        if pet and pet.alive:
            return pid
    return None


def ensure_active_alive(teams: TeamManager, pets: Dict[int, PetInstance],
                        team_id: int, logger: BattleLogger) -> bool:
    """确保激活宠物存活"""
    team = teams.teams[team_id]
    active_id = teams.active_pet_id(team_id)
    active = pets.get(active_id)

    if active and active.alive:
        return False

    # 寻找替补
    old_name = active.name_zh if active else "未知"
    for idx, pid in enumerate(team.pet_ids):
        if pid == active_id:
            continue
        pet = pets.get(pid)
        if pet and pet.alive:
            team.active_index = idx
            logger.swap(f"队伍{team_id}", old_name, pet.name_zh, forced=True)
            return True

    return False


def check_winner(teams: TeamManager, pets: Dict[int, PetInstance]) -> Optional[int]:
    """检查胜负"""
    alive = {0: False, 1: False}

    for tid in [0, 1]:
        team = teams.teams[tid]
        for pid in team.pet_ids:
            pet = pets.get(pid)
            if pet and pet.alive:
                alive[tid] = True
                break

    if alive[0] and not alive[1]:
        return 0
    if alive[1] and not alive[0]:
        return 1
    return None


def print_help():
    """打印帮助信息"""
    print(__doc__)
    print("\n种族被动技能:")
    print("-" * 60)
    for pet_type, desc in RACIAL_PASSIVE_DESC_ZH.items():
        print(f"  {PET_TYPE_NAMES_ZH[pet_type]}: {desc.split('：')[1]}")

    print("\n属性克制关系:")
    print("-" * 60)
    print("  强克 (+50%伤害):")
    relations = [
        ("人型", "龙类"), ("龙类", "魔法"), ("飞行", "水生"),
        ("不死", "人型"), ("小动物", "不死"), ("魔法", "飞行"),
        ("元素", "机械"), ("野兽", "小动物"), ("水生", "元素"),
        ("机械", "野兽")
    ]
    for attacker, defender in relations:
        print(f"    {attacker} > {defender}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="魔兽世界宠物对战模拟器")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--rounds", type=int, default=25, help="最大回合数")
    parser.add_argument("--log", type=str, help="日志文件路径")
    parser.add_argument("--help-rules", action="store_true", help="显示游戏规则")
    args = parser.parse_args()

    if args.help_rules:
        print_help()
        return

    # 加载数据
    data_loader = DataLoader(".")
    data_loader.load_all()

    if not data_loader.pets_data:
        print("错误: 无法加载宠物数据")
        return

    # 选择对战宠物
    # 队伍0: 野兽队 (灰猫、黄猫、黑纹灰猫)
    team0_pets = [40, 41, 42]

    # 队伍1: 混合队 (虎皮猫、黑尾白猫、银纹虎猫)
    team1_pets = [43, 44, 45]

    # 运行战斗
    winner = run_battle(
        data_loader=data_loader,
        team0_pet_ids=team0_pets,
        team1_pet_ids=team1_pets,
        level=25,
        rarity_id=4,  # 蓝色品质
        seed=args.seed,
        max_rounds=args.rounds,
        log_file=args.log,
    )


if __name__ == "__main__":
    main()
