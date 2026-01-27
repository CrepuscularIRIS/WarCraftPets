"""
Charge System - 充能管理系统

为WarCraftPets添加充能类技能支持:
- 充能回合计数
- 充能完成事件 (ON_CHARGE_READY)
- 充能状态管理
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class ChargeState(Enum):
    """充能状态"""
    CHARGING = "CHARGING"
    READY = "READY"
    USED = "USED"


@dataclass
class ChargeInstance:
    """充能实例"""
    skill_id: int
    pet_id: int
    total_charge_turns: int
    current_charge_turns: int
    state: ChargeState = ChargeState.CHARGING
    max_charges: int = 1  # 最大充能层数


class ChargeManager:
    """
    充能管理器

    职责:
    - 管理充能类技能的充能进度
    - 在充能完成时触发ON_CHARGE_READY事件
    - 支持多充能层数
    """

    def __init__(self):
        # pet_id -> skill_id -> ChargeInstance
        self._charges: Dict[int, Dict[int, ChargeInstance]] = {}

    def start_charging(
        self,
        pet_id: int,
        skill_id: int,
        charge_turns: int,
        max_charges: int = 1
    ) -> ChargeInstance:
        """开始充能"""
        if pet_id not in self._charges:
            self._charges[pet_id] = {}

        inst = ChargeInstance(
            skill_id=skill_id,
            pet_id=pet_id,
            total_charge_turns=charge_turns,
            current_charge_turns=0,
            state=ChargeState.CHARGING,
            max_charges=max_charges
        )
        self._charges[pet_id][skill_id] = inst
        return inst

    def tick(self, pet_id: int) -> List[ChargeInstance]:
        """
        回合结束时调用，推进充能进度
        返回充能完成的实例列表
        """
        completed: List[ChargeInstance] = []
        if pet_id not in self._charges:
            return completed

        for skill_id, inst in list(self._charges[pet_id].items()):
            if inst.state == ChargeState.CHARGING:
                inst.current_charge_turns += 1
                if inst.current_charge_turns >= inst.total_charge_turns:
                    inst.state = ChargeState.READY
                    completed.append(inst)

        return completed

    def use_charge(self, pet_id: int, skill_id: int) -> bool:
        """使用充能"""
        if pet_id not in self._charges:
            return False

        inst = self._charges[pet_id].get(skill_id)
        if inst and inst.state == ChargeState.READY:
            inst.state = ChargeState.USED
            return True
        return False

    def reset(self, pet_id: int, skill_id: int) -> bool:
        """重置充能（使用后重新充能）"""
        if pet_id not in self._charges:
            return False

        inst = self._charges[pet_id].get(skill_id)
        if inst:
            inst.current_charge_turns = 0
            inst.state = ChargeState.CHARGING
            return True
        return False

    def get_state(self, pet_id: int, skill_id: int) -> Optional[ChargeState]:
        """获取充能状态"""
        if pet_id not in self._charges:
            return None
        inst = self._charges[pet_id].get(skill_id)
        return inst.state if inst else None

    def get_progress(self, pet_id: int, skill_id: int) -> Optional[tuple]:
        """获取充能进度 (current, total)"""
        if pet_id not in self._charges:
            return None
        inst = self._charges[pet_id].get(skill_id)
        if inst:
            return (inst.current_charge_turns, inst.total_charge_turns)
        return None

    def is_ready(self, pet_id: int, skill_id: int) -> bool:
        """检查是否充能完成"""
        return self.get_state(pet_id, skill_id) == ChargeState.READY

    def remove(self, pet_id: int, skill_id: int) -> bool:
        """移除充能"""
        if pet_id in self._charges:
            if skill_id in self._charges[pet_id]:
                del self._charges[pet_id][skill_id]
                return True
        return False

    def clear_pet(self, pet_id: int) -> None:
        """清除宠物所有充能"""
        if pet_id in self._charges:
            self._charges[pet_id].clear()


# 测试代码
if __name__ == "__main__":
    cm = ChargeManager()

    print("=== Charge System Test ===\n")

    # 开始充能
    cm.start_charging(pet_id=1, skill_id=2001, charge_turns=3)
    print("开始充能技能2001 (需要3回合)")

    # 模拟回合
    for turn in range(1, 6):
        completed = cm.tick(1)
        progress = cm.get_progress(1, 2001)
        state = cm.get_state(1, 2001)
        print(f"回合 {turn}: 进度 {progress}, 状态 {state.value}")

        for inst in completed:
            print(f"  → 充能完成! ON_CHARGE_READY 事件 (skill={inst.skill_id})")

        if cm.is_ready(1, 2001):
            print(f"  → 充能就绪，可以使用!")

            # 使用充能
            if cm.use_charge(1, 2001):
                print(f"  → 充能已使用")

                # 重新充能
                if cm.reset(1, 2001):
                    print(f"  → 开始重新充能")
