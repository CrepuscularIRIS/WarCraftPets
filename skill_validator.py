"""
WarCraftPets Skill Logic Validator - 事件驱动验证器

功能:
1. 验证充能类技能跨回合释放
2. 验证AURA_APPLY/REFRESH/EXPIRE事件统计
3. 验证持续回合正确递减
4. 对比技能描述与实际行为
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json

# 导入核心系统
from engine.core.events import Event
from engine.resolver.aura_manager import AuraManager, AuraApplyResult, AuraExpire
from engine.resolver.state_manager import StateManager, StateChange


class EventType(Enum):
    """扩展事件类型"""
    ON_AURA_APPLY = "ON_AURA_APPLY"
    ON_AURA_REFRESH = "ON_AURA_REFRESH"
    ON_AURA_EXPIRE = "ON_AURA_EXPIRE"
    ON_STATE_SET = "ON_STATE_SET"
    ON_STATE_CLEAR = "ON_STATE_CLEAR"
    ON_CHARGE_READY = "ON_CHARGE_READY"


@dataclass
class EventRecord:
    """事件记录"""
    event_type: EventType
    pet_id: int
    aura_id: Optional[int] = None
    state_id: Optional[int] = None
    value: Optional[int] = None
    turn: int = 0
    timestamp: float = 0.0


@dataclass
class SkillExpectation:
    """技能预期"""
    skill_name: str
    skill_id: int
    expected_turns: int  # 预期持续回合
    expected_triggers: int  # 预期触发次数
    description: str  # 技能描述
    charge_turns: Optional[int] = None  # 充能回合数


@dataclass
class ValidationResult:
    """验证结果"""
    skill_name: str
    passed: bool
    expected_behavior: str
    actual_behavior: str
    discrepancies: List[str]
    event_log: List[EventRecord]


class EventValidator:
    """事件驱动验证器"""

    def __init__(self):
        self.aura_manager = AuraManager()
        self.state_manager = StateManager()
        self.event_log: List[EventRecord] = []
        self.turn_count = 0
        self._event_callbacks: Dict[EventType, List[Callable]] = {}

    def register_callback(self, event_type: EventType, callback: Callable):
        """注册事件回调"""
        if event_type not in self._event_callbacks:
            self._event_callbacks[event_type] = []
        self._event_callbacks[event_type].append(callback)

    def emit(self, event_type: EventType, pet_id: int, aura_id: Optional[int] = None,
             state_id: Optional[int] = None, value: Optional[int] = None):
        """发射事件并记录"""
        record = EventRecord(
            event_type=event_type,
            pet_id=pet_id,
            aura_id=aura_id,
            state_id=state_id,
            value=value,
            turn=self.turn_count
        )
        self.event_log.append(record)

        # 调用回调
        if event_type in self._event_callbacks:
            for cb in self._event_callbacks[event_type]:
                cb(record)

    def next_turn(self):
        """回合推进"""
        self.turn_count += 1

    def end_turn(self):
        """回合结束 - 处理aura递减"""
        expired = []
        # 获取所有pet_id
        pet_ids = list(self.aura_manager._auras.keys())
        for pet_id in pet_ids:
            expires = self.aura_manager.tick(pet_id)
            for ex in expires:
                self.emit(EventType.ON_AURA_EXPIRE, ex.owner_pet_id, ex.aura_id)
                expired.append(ex)
        return expired

    def apply_aura(self, caster_id: int, target_id: int, aura_id: int,
                   duration: int, tickdown_first: bool = True) -> AuraApplyResult:
        """应用aura并记录事件"""
        result = self.aura_manager.apply(
            owner_pet_id=target_id,
            caster_pet_id=caster_id,
            aura_id=aura_id,
            duration=duration,
            tickdown_first_round=tickdown_first,
            source_effect_id=0
        )

        if result.applied:
            self.emit(EventType.ON_AURA_APPLY, target_id, aura_id)
        elif result.refreshed:
            self.emit(EventType.ON_AURA_REFRESH, target_id, aura_id)

        return result

    def validate_skill_duration(self, expectation: SkillExpectation) -> ValidationResult:
        """验证技能持续回合"""
        # 重置状态
        self.aura_manager = AuraManager()
        self.event_log = []
        self.turn_count = 0

        # 应用aura
        self.apply_aura(
            caster_id=1,
            target_id=2,
            aura_id=expectation.skill_id,
            duration=expectation.expected_turns,
            tickdown_first=True
        )

        # 模拟回合
        actual_triggers = 0
        max_turns = 10 if expectation.expected_turns == -1 else expectation.expected_turns + 3

        for turn in range(1, max_turns):  # 有限回合数验证
            self.next_turn()
            # 记录TURN_START时的状态
            aura = self.aura_manager.get(2, expectation.skill_id)
            if aura:
                actual_triggers += 1
            self.end_turn()

        # 分析结果
        apply_events = [e for e in self.event_log if e.event_type == EventType.ON_AURA_APPLY]
        expire_events = [e for e in self.event_log if e.event_type == EventType.ON_AURA_EXPIRE]

        discrepancies = []

        # 检查持续回合
        if expectation.expected_turns == -1:
            # 永久aura应该一直存在
            if actual_triggers < 5:  # 至少活跃5回合
                discrepancies.append(
                    f"永久aura错误: 前10回合应该持续存在, 实际只有{actual_triggers}回合"
                )
            # 永久aura不应该有过期事件
            if expire_events:
                discrepancies.append("永久aura不应该触发过期事件")
        else:
            expected_active_turns = expectation.expected_turns
            if actual_triggers != expected_active_turns:
                discrepancies.append(
                    f"持续回合错误: 预期活跃{expected_active_turns}回合, 实际{actual_triggers}回合"
                )

            # 检查expire事件
            if not expire_events:
                discrepancies.append("Aura过期时没有触发ON_AURA_EXPIRE事件")

        return ValidationResult(
            skill_name=expectation.skill_name,
            passed=len(discrepancies) == 0,
            expected_behavior=f"持续{expectation.expected_turns}回合, 触发{actual_triggers}次",
            actual_behavior=f"活跃{actual_triggers}回合, expire事件{len(expire_events)}次",
            discrepancies=discrepancies,
            event_log=self.event_log.copy()
        )

    def validate_charge_skill(self, expectation: SkillExpectation) -> ValidationResult:
        """验证充能类技能"""
        # 重置状态
        self.aura_manager = AuraManager()
        self.event_log = []
        self.turn_count = 0

        discrepancies = []

        # 充能类技能逻辑: 需要充能回合后才能释放
        if expectation.charge_turns:
            for turn in range(1, expectation.charge_turns + 1):
                self.next_turn()
                self.end_turn()

            # 充能完成，应该可以释放
            charge_ready_events = [e for e in self.event_log
                                   if e.event_type == EventType.ON_CHARGE_READY]

            if not charge_ready_events:
                discrepancies.append(
                    f"充能技能问题: {expectation.charge_turns}回合充能后没有触发ON_CHARGE_READY事件"
                )

        return ValidationResult(
            skill_name=expectation.skill_name,
            passed=len(discrepancies) == 0,
            expected_behavior=expectation.description,
            actual_behavior=f"记录{len(self.event_log)}个事件",
            discrepancies=discrepancies,
            event_log=self.event_log.copy()
        )


def run_all_validations() -> Dict[str, Any]:
    """运行所有验证测试"""

    validator = EventValidator()
    results: List[ValidationResult] = []

    # 定义技能预期
    skill_expectations = [
        # 标准持续技能 (持续2回合, 2个TURN_START触发)
        SkillExpectation(
            skill_name="标准持续伤害",
            skill_id=1001,
            expected_turns=2,
            expected_triggers=2,
            description="持续2回合,每回合造成伤害",
            charge_turns=None
        ),
        # 长持续技能 (持续5回合)
        SkillExpectation(
            skill_name="强化光环",
            skill_id=1002,
            expected_turns=5,
            expected_triggers=5,
            description="持续5回合的增益效果",
            charge_turns=None
        ),
        # 充能技能 (3回合充能)
        SkillExpectation(
            skill_name="充能攻击",
            skill_id=2001,
            expected_turns=1,  # 释放只持续1回合
            expected_triggers=1,
            description="3回合充能后造成大量伤害",
            charge_turns=3
        ),
        # 无穷持续 (-1)
        SkillExpectation(
            skill_name="永久增益",
            skill_id=3001,
            expected_turns=-1,
            expected_triggers=999,  # 应该持续到战斗结束
            description="永久持续直到战斗结束",
            charge_turns=None
        ),
    ]

    # 运行验证
    for expectation in skill_expectations:
        if expectation.charge_turns:
            result = validator.validate_charge_skill(expectation)
        else:
            result = validator.validate_skill_duration(expectation)
        results.append(result)

    # 生成报告
    report = {
        "test_run_timestamp": "2026-01-27",
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": []
    }

    for result in results:
        report["results"].append({
            "skill_name": result.skill_name,
            "passed": result.passed,
            "expected": result.expected_behavior,
            "actual": result.actual_behavior,
            "discrepancies": result.discrepancies,
            "event_count": len(result.event_log),
            "events": [
                {
                    "type": e.event_type.value,
                    "turn": e.turn,
                    "pet_id": e.pet_id,
                    "aura_id": e.aura_id
                }
                for e in result.event_log
            ]
        })

    return report


def print_report(report: Dict[str, Any]):
    """打印验证报告"""
    print("\n" + "="*70)
    print("WARCRAFT PETS SKILL LOGIC VALIDATION REPORT")
    print("="*70)

    print(f"\n测试时间: {report['test_run_timestamp']}")
    print(f"总测试数: {report['total_tests']}")
    print(f"通过: {report['passed']} | 失败: {report['failed']}")

    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n{'='*50}")
        print(f"[{status}] {result['skill_name']}")
        print(f"预期: {result['expected']}")
        print(f"实际: {result['actual']}")
        print(f"事件数: {result['event_count']}")

        if result["discrepancies"]:
            print("问题:")
            for d in result["discrepancies"]:
                print(f"  - {d}")

        if result["events"]:
            print("事件日志:")
            for e in result["events"]:
                print(f"  T{e['turn']}: {e['type']} (pet={e['pet_id']}, aura={e['aura_id']})")

    print("\n" + "="*70)


if __name__ == "__main__":
    # 运行验证
    report = run_all_validations()

    # 打印报告
    print_report(report)

    # 保存JSON
    output_file = "/home/yarizakurahime/engine/wow_claude/logs/skill_validation_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n详细报告已保存到: {output_file}")
