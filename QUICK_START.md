# Pet 子系统快速入门

## 5 秒快速开始

```bash
# 运行宠物对战
python main.py

# 或运行示例
python example_pet_stats.py

# 或运行测试
python -m pytest test_pet_stats.py -v
```

## 10 分钟指南

### 1. 运行默认战斗

```bash
python main.py
```

输出显示：
- 两支队伍，各 3 个宠物
- 所有宠物 **等级 25，品质 4**
- 宠物属性：Health、Power、Speed
- 每个技能的面板伤害值
- 完整的回合制战斗

### 2. 查看宠物属性

战斗开始前的宠物信息：

```
队伍0:
  灰猫 [野兽] HP:669 力量:140 速度:140
    技能1: 爪击 (面板伤害: 168)
    技能2: 斜掠 (面板伤害: 120)
    技能3: 吞食 (面板伤害: 120)
```

### 3. 查看战斗过程

每个回合显示：
- 速度比较和先手确定
- 技能使用和伤害计算
- 暴击判定和伤害类型
- 生命值更新

```
──────────────────── 第 1 回合 ────────────────────
  ⚡ 速度: 灰猫=140 vs 虎皮猫=131 | 先手: 灰猫
  灰猫 使用 [爪击]:
  💥 灰猫 -> 虎皮猫: 255 野兽伤害 [暴击!]
  虎皮猫 使用 [爪击]:
  💥 虎皮猫 -> 灰猫: 171 野兽伤害
  ── 回合结束状态 ──
  队伍0: 灰猫 HP:498/669
  队伍1: 虎皮猫 HP:418/673
```

### 4. 理解属性计算

#### Health (最大生命值)
```
公式: ((Base + Breed/10) * 5 * Level * Quality) + 100
例: ((10.5 + 0.5/10) * 5 * 25 * 0.65) + 100 = 775
```

#### Power (攻击力)
```
公式: (Base + Breed/10) * Level * Quality
例: (8.0 + 0.5/10) * 25 * 0.65 = 130
```

#### Speed (速度)
```
公式: (Base + Breed/10) * Level * Quality
例: (9.5 + 0.5/10) * 25 * 0.65 = 156
```

### 5. 理解技能伤害

#### 面板伤害 (Panel Damage)
```
公式: floor(base_points * (1 + power/20))
例: 爪击, base=10, power=140
    floor(10 * (1 + 140/20)) = floor(10 * 8) = 80
```

## 常用命令

### 基础命令
```bash
# 运行战斗并生成日志
python main.py

# 使用指定随机种子（重现结果）
python main.py --seed 12345

# 自定义最大回合数
python main.py --rounds 100

# 指定日志文件名
python main.py --log my_battle.txt

# 查看游戏规则
python main.py --help-rules
```

### 组合使用
```bash
# 使用种子和自定义回合数
python main.py --seed 42 --rounds 50 --log test_battle.txt

# 获取帮助
python main.py --help
```

## 查看结果

### 实时输出
战斗过程在终端实时显示，包括每回合的所有细节。

### 日志文件
自动生成 `battle_log_YYYYMMDD_HHMMSS.txt`

查看日志：
```bash
cat battle_log_20251228_213303.txt
```

## 运行示例

### 查看 7 个示例

```bash
python example_pet_stats.py
```

输出包括：
1. 基础属性计算
2. 技能伤害计算
3. 等级进度分析
4. 品质比较分析
5. 批量计算
6. 多技能伤害计算
7. 品种比较分析

## 运行测试

### 验证系统正确性

```bash
# 运行所有 20 个测试
python -m pytest test_pet_stats.py -v

# 快速运行（无输出）
python -m pytest test_pet_stats.py -q

# 运行特定测试
python -m pytest test_pet_stats.py::TestProgressionDB -v
```

预期输出：
```
============================== 20 passed in 0.03s ==============================
```

## 宠物队伍配置

### 队伍 0 (野兽队)
- 灰猫 (ID: 40) - 基础HP/Power/Speed
- 黄猫 (ID: 41) - 平衡型
- 黑纹灰猫 (ID: 42) - 高攻击

### 队伍 1 (混合队)
- 虎皮猫 (ID: 43) - 高攻击型
- 黑尾白猫 (ID: 44) - 平衡型
- 黑斑白猫 (ID: 45) - 基础型

所有宠物都是：
- **等级**: 25
- **品质**: 4 (精良蓝色)
- **类型**: 野兽

## 属性示例

### 灰猫 (ID: 40)

基础数据：
| 属性 | 值 |
|------|-----|
| Base HP | 8.0 |
| Base Power | 8.0 |
| Base Speed | 8.0 |
| Pet Type | 野兽 |

品种加成 (Breed 3)：
| 属性 | 加成 |
|------|------|
| Health Add | 0.5 |
| Power Add | 0.5 |
| Speed Add | 0.5 |

计算结果 (Level 25, Quality 4)：
| 属性 | 值 |
|------|-----|
| Health | 669 |
| Power | 140 |
| Speed | 140 |

技能伤害 (Power=140)：
| 技能 | Base | 伤害 |
|------|------|-----|
| 爪击 | 10 | 168 |
| 斜掠 | 8.5 | 120 |
| 吞食 | 8.5 | 120 |

## 关键概念

### 品质 (Rarity)
| 品质 | ID | 乘数 | 说明 |
|-----|----|----|------|
| 普通 | 1 | 0.50 | 最弱 |
| 普通 | 2 | 0.55 | - |
| 良好 | 3 | 0.60 | - |
| **精良** | **4** | **0.65** | **本系统使用** |
| 史诗 | 5 | 0.70 | - |
| 传奇 | 6 | 0.75 | 最强 |

### 等级 (Level)
- **支持范围**: 1-25
- **本系统使用**: 25 (最高等级)
- **属性随等级线性增长**

### 品种 (Breed)
- **支持范围**: 3-12（共10个品种）
- **作用**: 为属性提供加成
- **效果**: 加成值除以10后添加到基础值

## 常见问题

### Q: 如何更改宠物品质？
A: 目前固定为品质4。如需修改，编辑 `main.py` 中的 `run_battle()` 调用，修改 `rarity_id` 参数。

### Q: 如何添加更多回合？
A: 使用 `--rounds` 参数：
```bash
python main.py --rounds 100
```

### Q: 如何重现相同的战斗？
A: 使用相同的随机种子：
```bash
python main.py --seed 42
```

### Q: 技能伤害的计算方式是什么？
A: 使用公式：`floor(base_points * (1 + power/20))`
- base_points: 技能的基础伤害点数
- power: 宠物的攻击力属性

### Q: 日志文件在哪里？
A: 自动生成在当前目录，名称格式为 `battle_log_YYYYMMDD_HHMMSS.txt`

## 进阶使用

### 查看详细文档
- **API 文档**: 查看 `PET_SYSTEM_GUIDE.md`
- **快速参考**: 查看 `PET_QUICK_REFERENCE.md`
- **实现细节**: 查看 `PET_IMPLEMENTATION_SUMMARY.md`
- **集成说明**: 查看 `MAIN_PY_INTEGRATION.md`

### 查看代码
```bash
# 查看进度计算器
cat engine/pets/progression.py

# 查看统计数据模型
cat engine/pets/pet_stats.py

# 查看主程序集成
grep -n "PetStatsCalculator" main.py
```

### 自定义对战
编辑 `main.py` 的 `main()` 函数：
```python
# 选择对战宠物
team0_pets = [40, 41, 42]  # 修改这里
team1_pets = [43, 44, 45]  # 修改这里
```

## 总结

Pet 子系统提供：
- ✅ **标准化属性计算** - 所有宠物品质4、等级25
- ✅ **完整的宠物信息** - Health、Power、Speed、技能伤害
- ✅ **准确的伤害计算** - 基于官方公式
- ✅ **完整的战斗模拟** - 包括类型克制、暴击、被动技能等

现在您可以：
- 运行宠物对战
- 查看属性和伤害
- 分析战斗结果
- 理解计算方式

开始吧！🎮

```bash
python main.py
```
