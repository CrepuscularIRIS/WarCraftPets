#!/usr/bin/env python3
"""
Event Diff - 事件对账脚本

检查日志中事件的完整性和一致性：
1. 伤害事件 vs HP变化
2. 治疗事件 vs HP变化
3. AURa应用/移除 vs 状态变化
4. State设置 vs 状态变化
5. Event完整性检查
"""
import json
import os
from datetime import datetime
from collections import defaultdict

def analyze_events():
    """分析所有事件日志"""
    print("="*70)
    print("Event Diff - 事件对账分析")
    print("="*70)

    # 收集所有事件
    all_events = []
    events_dir = 'logs/events'
    if os.path.exists(events_dir):
        for f in os.listdir(events_dir):
            if f.endswith('.jsonl'):
                with open(os.path.join(events_dir, f)) as file:
                    for line in file:
                        if line.strip():
                            try:
                                event = json.loads(line)
                                event['_source_file'] = f
                                all_events.append(event)
                            except:
                                pass

    print(f"\\n总共收集事件: {len(all_events)}")

    # 按类型分组
    by_type = defaultdict(list)
    for e in all_events:
        etype = e.get('type', e.get('event_type', 'unknown'))
        by_type[etype].append(e)

    print("\\n事件类型分布:")
    for etype, events in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {etype}: {len(events)}")

    # 伤害对账
    print("\\n" + "="*70)
    print("伤害对账 (Damage Reconciliation)")
    print("="*70)

    damage_events = by_type.get('damage', by_type.get('DAMAGE', []))
    hp_changes = by_type.get('hp_change', by_type.get('HP_CHANGE', []))
    ability_effects = by_type.get('ability_effect', by_type.get('ABILITY_EFFECT', []))

    print(f"伤害事件: {len(damage_events)}")
    print(f"HP变化事件: {len(hp_changes)}")
    print(f"ABILITY_EFFECT事件: {len(ability_effects)}")

    issues = []

    # 检查ABILITY_EFFECT中的HP变化是否一致
    hp_effect_mismatches = 0
    for ae in ability_effects:
        actor_hp = ae.get('actor', {}).get('hp_change', 0)
        target_hp = ae.get('target', {}).get('hp_change', 0)

        # 检查伤害是否记录在target上
        if target_hp < 0:
            # 应该有一个对应的damage事件
            found = False
            for de in damage_events:
                if (de.get('target_id') == ae.get('target', {}).get('id') and
                    abs(de.get('damage', 0)) == abs(target_hp)):
                    found = True
                    break
            if not found:
                hp_effect_mismatches += 1
                if hp_effect_mismatches <= 5:
                    issues.append({
                        'type': 'DAMAGE_MISSING',
                        'ability_id': ae.get('ability_id'),
                        'target_hp_change': target_hp,
                        'description': 'ABILITY_EFFECT中有伤害但没有对应damage事件'
                    })

    print(f"\\nHP变化不匹配: {hp_effect_mismatches}")

    # 治疗对账
    print("\\n" + "="*70)
    print("治疗对账 (Heal Reconciliation)")
    print("="*70)

    heal_events = by_type.get('heal', by_type.get('HEAL', []))
    print(f"治疗事件: {len(heal_events)}")

    heal_mismatches = 0
    for ae in ability_effects:
        actor_hp = ae.get('actor', {}).get('hp_change', 0)
        target_hp = ae.get('target', {}).get('hp_change', 0)

        if target_hp > 0:
            found = False
            for he in heal_events:
                if (he.get('target_id') == ae.get('target', {}).get('id') and
                    he.get('heal', 0) == target_hp):
                    found = True
                    break
            if not found:
                heal_mismatches += 1
                if heal_mismatches <= 5:
                    issues.append({
                        'type': 'HEAL_MISSING',
                        'ability_id': ae.get('ability_id'),
                        'target_hp_change': target_hp,
                        'description': 'ABILITY_EFFECT中有治疗但没有对应heal事件'
                    })

    print(f"治疗不匹配: {heal_mismatches}")

    # AURa对账
    print("\\n" + "="*70)
    print("Aura对账 (Aura Reconciliation)")
    print("="*70)

    aura_apply = by_type.get('aura_apply', by_type.get('AURA_APPLY', []))
    aura_remove = by_type.get('aura_remove', by_type.get('AURA_REMOVE', []))
    aura_refresh = by_type.get('aura_refresh', by_type.get('AURA_REFRESH', []))

    print(f"Aura应用: {len(aura_apply)}")
    print(f"Aura移除: {len(aura_remove)}")
    print(f"Aura刷新: {len(aura_refresh)}")

    # 检查Aura应用和移除是否平衡
    aura_issues = 0
    for apply_event in aura_apply:
        aura_id = apply_event.get('aura_id')
        owner_id = apply_event.get('owner_id')

        # 应该有对应的移除或刷新
        found = False
        for refresh in aura_refresh:
            if (refresh.get('aura_id') == aura_id and
                refresh.get('owner_id') == owner_id):
                found = True
                break

        if not found:
            # 检查是否有后续移除
            for remove in aura_remove:
                if (remove.get('aura_id') == aura_id and
                    remove.get('owner_id') == owner_id):
                    found = True
                    break

            if not found and aura_issues <= 3:
                aura_issues += 1
                issues.append({
                    'type': 'AURA_UNBALANCED',
                    'aura_id': aura_id,
                    'owner_id': owner_id,
                    'description': 'Aura应用后没有对应的移除或刷新事件'
                })

    print(f"不平衡Aura: {aura_issues}")

    # State对账
    print("\\n" + "="*70)
    print("State对账 (State Reconciliation)")
    print("="*70)

    state_set = by_type.get('state_set', by_type.get('STATE_SET', []))
    state_change = by_type.get('state_change', by_type.get('STATE_CHANGE', []))

    print(f"State设置: {len(state_set)}")
    print(f"State变化: {len(state_change)}")

    # 检查状态是否一致
    state_issues = 0
    for ss in state_set:
        state_id = ss.get('state_id')
        value = ss.get('value')
        target_id = ss.get('target_id')

        found = False
        for sc in state_change:
            if (sc.get('state_id') == state_id and
                sc.get('target_id') == target_id):
                found = True
                break

        if not found and state_issues <= 3:
            state_issues += 1
            issues.append({
                'type': 'STATE_MISSING',
                'state_id': state_id,
                'target_id': target_id,
                'description': 'State设置后没有对应的state_change事件'
            })

    print(f"状态不匹配: {state_issues}")

    # 生成报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'summary': {
            'total_events': len(all_events),
            'damage_events': len(damage_events),
            'heal_events': len(heal_events),
            'aura_apply': len(aura_apply),
            'aura_remove': len(aura_remove),
            'state_set': len(state_set),
        },
        'issues': {
            'hp_effect_mismatches': hp_effect_mismatches,
            'heal_mismatches': heal_mismatches,
            'aura_issues': aura_issues,
            'state_issues': state_issues,
            'details': issues[:20]
        },
        'status': 'PASS' if sum([hp_effect_mismatches, heal_mismatches, aura_issues, state_issues]) == 0 else 'NEEDS_ATTENTION'
    }

    # 保存报告
    os.makedirs('logs/reports', exist_ok=True)
    with open('logs/reports/event_diff_report.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\\n" + "="*70)
    print("对账结果")
    print("="*70)
    print(f"状态: {report['status']}")
    print(f"HP变化不匹配: {hp_effect_mismatches}")
    print(f"治疗不匹配: {heal_mismatches}")
    print(f"Aura不匹配: {aura_issues}")
    print(f"State不匹配: {state_issues}")
    print(f"\\n详细报告: logs/reports/event_diff_report.json")

    if issues:
        print("\\n前5个问题:")
        for i, issue in enumerate(issues[:5], 1):
            print(f"  {i}. {issue['type']}: {issue['description']}")
            if 'ability_id' in issue:
                print(f"     ability_id: {issue.get('ability_id')}")

    return report

if __name__ == '__main__':
    analyze_events()
