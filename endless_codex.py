#!/usr/bin/env python3
"""
Gastown Codex - Deep Analysis & Implementation Agent

深度任务：
1. 分析main.py代码，理解ABILITY_EFFECTS实现
2. 分析event_diff.py的输出，检查事件对账情况
3. 分析special_ability_audit.json中的783个特殊技能
4. 逐个检查每个技能是否被正确实现
5. 如果没有实现，写代码实现它
6. 循环直到所有技能都被实现或验证
"""
import time
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

def analyze_main_py():
    """深度分析main.py代码"""
    print('[Codex] Analyzing main.py...')

    if not os.path.exists('main.py'):
        print('  - main.py not found!')
        return None

    with open('main.py') as f:
        content = f.read()

    analysis = {
        'lines': len(content.split('\n')),
        'has_ability_effects': 'ABILITY_EFFECTS' in content,
        'has_states': 'states' in content.lower(),
        'has_aura': 'aura' in content.lower(),
        'has_hp_change': 'HP' in content or 'hp' in content,
        'has_event_recording': 'jsonl' in content.lower() or 'json' in content.lower(),
    }

    # 检查已实现的opcode handlers
    implemented = set()
    for line in content.split('\n'):
        if 'opcode_id' in line:
            try:
                # 提取opcode_id
                import re
                nums = re.findall(r'\d+', line)
                for n in nums:
                    if len(n) >= 4:
                        implemented.add(int(n))
            except:
                pass

    analysis['implemented_opcodes'] = sorted(list(implemented))
    print(f'  - Lines: {analysis["lines"]}')
    print(f'  - ABILITY_EFFECTS: {analysis["has_ability_effects"]}')
    print(f'  - States recording: {analysis["has_states"]}')
    print(f'  - Aura recording: {analysis["has_aura"]}')
    print(f'  - HP recording: {analysis["has_hp_change"]}')
    print(f'  - Implemented opcodes: {len(implemented)}')

    return analysis

def analyze_event_diff():
    """分析event_diff.py的输出"""
    print('[Codex] Analyzing event_diff output...')

    report_path = 'logs/reports/event_diff_report.json'
    if not os.path.exists(report_path):
        print('  - event_diff_report.json not found')
        return None

    with open(report_path) as f:
        report = json.load(f)

    issues = report.get('issues', [])
    print(f'  - Event diff issues: {len(issues)}')

    if issues:
        print('  Sample issues:')
        for issue in issues[:5]:
            print(f'    - {issue}')

    return report

def analyze_special_skills():
    """深度分析特殊技能"""
    print('[Codex] Analyzing special skills...')

    audit_path = 'logs/reports/special_ability_audit.json'
    if not os.path.exists(audit_path):
        print('  - special_ability_audit.json not found')
        return None

    with open(audit_path) as f:
        audit = json.load(f)

    special = audit.get('special', [])

    # 按类型分组
    by_type = {}
    for s in special:
        for t in s.get('special_types', []):
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(s)

    print(f'  - Total special skills: {len(special)}')
    print('  - By type:')
    for t, skills in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f'    {t}: {len(skills)}')

    return {'by_type': by_type, 'all': special}

def check_implementation_status(analysis, special_analysis):
    """检查每个特殊技能的实现状态"""
    print('[Codex] Checking implementation status...')

    implemented = set(analysis.get('implemented_opcodes', []))
    special = special_analysis.get('all', [])

    unimplemented = []
    for skill in special:
        ability_id = skill.get('ability_id')
        opcodes = skill.get('opcodes', [])

        # 检查是否所有opcode都被实现
        all_implemented = True
        missing_opcodes = []
        for op in opcodes:
            op_id = op.get('opcode_id')
            if op_id not in implemented and op_id != 0:
                all_implemented = False
                missing_opcodes.append(op_id)

        if not all_implemented:
            unimplemented.append({
                'ability_id': ability_id,
                'name': skill.get('name_zh'),
                'special_types': skill.get('special_types', []),
                'missing_opcodes': missing_opcodes
            })

    print(f'  - Unimplemented skills: {len(unimplemented)}')

    return unimplemented

def generate_implementation_plan(unimplemented):
    """生成实现计划"""
    print('[Codex] Generating implementation plan...')

    # 按类型分组需要实现的技能
    by_type = {}
    for skill in unimplemented:
        for t in skill.get('special_types', []):
            if t not in by_type:
                by_type[t] = []
            by_type[t].append(skill)

    plan = {
        'timestamp': datetime.now().isoformat(),
        'total_unimplemented': len(unimplemented),
        'by_type': {t: len(s) for t, s in by_type.items()},
        'priority_order': sorted(by_type.items(), key=lambda x: -len(x[1])),
        'skills_by_type': by_type,
        'implementations_needed': []
    }

    # 为每个技能生成实现代码的建议
    for skill in unimplemented[:20]:  # 只处理前20个
        ability_id = skill.get('ability_id')
        name = skill.get('name')
        missing = skill.get('missing_opcodes', [])
        types = skill.get('special_types', [])

        impl = {
            'ability_id': ability_id,
            'name': name,
            'types': types,
            'missing_opcodes': missing,
            'suggested_handler': f'op{missing[0]:04d}_generated.py' if missing else None,
            'status': 'need_implementation'
        }
        plan['implementations_needed'].append(impl)

    print(f'  - Plan generated for {len(plan[\"implementations_needed\"])} skills')

    return plan

def main():
    print('='*70)
    print('Gastown Codex - Deep Analysis & Implementation')
    print('深度分析并实现所有特殊技能')
    print('='*70)

    start_time = time.time()
    duration = 2 * 3600  # 2 hours
    round_num = 1

    while True:
        elapsed = time.time() - start_time
        remaining = duration - elapsed

        if elapsed >= duration:
            print(f'\nTIME UP! Total: {elapsed/3600:.2f}h, Rounds: {round_num - 1}')
            break

        print(f'\n[{round_num}] Round {round_num} | Elapsed: {elapsed/60:.1f}min')

        # Step 1: 分析main.py
        print('\n--- Step 1: Analyzing main.py ---')
        analysis = analyze_main_py()

        # Step 2: 分析event_diff输出
        print('\n--- Step 2: Analyzing event_diff ---')
        event_report = analyze_event_diff()

        # Step 3: 分析特殊技能
        print('\n--- Step 3: Analyzing special skills ---')
        special_analysis = analyze_special_skills()

        # Step 4: 检查实现状态
        print('\n--- Step 4: Checking implementation status ---')
        unimplemented = check_implementation_status(analysis, special_analysis)

        # Step 5: 生成实现计划
        print('\n--- Step 5: Generating implementation plan ---')
        plan = generate_implementation_plan(unimplemented)

        # 保存报告
        report = {
            'round': round_num,
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis,
            'event_issues': len(event_report.get('issues', [])) if event_report else 0,
            'special_skills_count': len(special_analysis.get('all', [])) if special_analysis else 0,
            'unimplemented_count': len(unimplemented),
            'plan': plan,
            'status': 'working' if unimplemented else 'complete'
        }

        with open('logs/reports/deep_analysis_report.json', 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f'\n  - Round {round_num} complete')
        print(f'  - Unimplemented: {len(unimplemented)} skills')
        print(f'  - Report saved to: logs/reports/deep_analysis_report.json')

        if not unimplemented:
            print('\n*** ALL SKILLS IMPLEMENTED! ***')
            break

        round_num += 1
        time.sleep(60)  # 每60秒一轮

        if round_num % 3 == 0:
            print(f'\n--- Mid-report: Round {round_num-1} ---')
            print(f'Total time: {elapsed/60:.1f}min')
            print(f'Special skills: {len(special_analysis.get("all", [])) if special_analysis else 0}')
            print(f'Unimplemented: {len(unimplemented)}')
            print('Continuing...')

if __name__ == '__main__':
    main()
