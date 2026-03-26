---
name: standard-agent-process
description: 将“某个过程/提示词/格式规范”整理为标准的 Agent Skill 目录结构（SKILL.md + references + scripts + assets）。当用户要求“把流程整理成 skill”“补齐职责/触发/步骤/输出标准”“把确认过的格式要求放进 references”“把可自动化步骤写进 scripts”“把模板放进 assets”时使用。
---

# Standard Agent Process Skill

## 职责（What）

- 将一个已存在的“流程/Prompt/规范要求”**归档为标准 Skill 结构**：
  - `SKILL.md`：职责、触发场景、执行步骤、输出标准
  - `references/`：已确认的格式要求与内容标准（以原文为准）
  - `scripts/`：可自动化的整理/导入/校验步骤
  - `assets/`：可复用模板（输出模板、检查清单模板等）

## 触发场景（When）

出现以下任一需求时触发：

- 用户要求“创建/整理/标准化一个 Agent Skill”
- 用户强调要包含 `skill.md / references / scripts / assets(templates)` 完整结构
- 用户要求“把我们确认过的格式要求/内容标准都放到 references”
- 用户要求“可自动化步骤写入 scripts”“模板放入 assets 复用”

## 输入要求（Input）

- **必须输入**：
  - 流程文档/Prompt 原文（文件路径或粘贴文本）
  - 已确认的格式要求与内容标准（原文）
- **可选输入**：
  - `skill_name`（若未给出：默认使用 `standard-agent-process`）
  - 目标存放位置（项目内推荐：`skills/<skill_name>/`；若另有约定按约定）

## 执行步骤（How）

### 1) 选择存放位置与命名

- 采用 `name`：小写 + 连字符，≤ 64 字符
- 默认路径：`skills/<skill_name>/`

### 2) 创建目录结构

在目标目录下创建：

- `SKILL.md`
- `references/`
- `scripts/`
- `assets/templates/`

### 3) 编写 `SKILL.md`

`SKILL.md` 必须包含并清晰分段：

- 职责（What）
- 触发场景（When）
- 输入要求（Input）
- 执行步骤（How）
- 输出标准（Output Contract）
- 失败/回退规则（例如：缺少“已确认标准原文”时只生成占位区块并标记 TODO）

### 4) 归档 references（以原文为准）

将“确认过”的内容按主题落盘，推荐拆分为：

- `references/PROMPTS.md`：流程 Prompt 原文/版本说明
- `references/FORMAT_REQUIREMENTS.md`：格式（标题层级、段落结构、命名、引用规范等）
- `references/CONTENT_STANDARDS.md`：内容标准（必须包含/禁止包含/质量门槛/验收项等）

要求：

- **不擅自改写标准**；如需要结构化，只做“目录化/分段/加标题”，保留原文。

### 5) 可自动化步骤写入 scripts

将能自动完成的动作脚本化，例如：

- 从一个源文档导入到 `references/` 的单一来源文件（保留原文）
- 生成 `assets/templates/` 的初始模板
- 进行最基本校验（例如：`SKILL.md` 是否含 frontmatter；references 文件是否存在）

### 6) 放入可复用模板（assets）

将可重复使用的产物模板放入：

- `assets/templates/prompt_template.md`
- `assets/templates/output_template.md`
- `assets/templates/checklist_template.md`

模板要求：

- 可直接复制使用
- 明确“需由用户/文档填充”的占位符

## 输出标准（Output Contract）

交付物必须满足：

- 存在完整目录结构：`SKILL.md`、`references/`、`scripts/`、`assets/templates/`
- `SKILL.md`：
  - 含 YAML frontmatter：`name`、`description`
  - `description` 使用第三人称，包含 WHAT + WHEN + 触发关键词
  - 清晰、可执行、可验收
- `references/`：
  - 收录“已确认标准”的原文或原文片段
  - 若缺少原文：必须显式标注“待补充”，不得编造
- `scripts/`：
  - 提供可运行脚本与说明文档
  - 脚本输出路径固定且可预测

## 限制与回退规则

- 当“确认过的格式要求/内容标准”原文不可用时：
  - 仅生成结构与占位区块
  - 在 `references/` 与模板中明确标注 TODO
  - 不得虚构任何团队标准内容

## 关联资源（One-level deep）

- `references/PROMPTS.md`
- `references/FORMAT_REQUIREMENTS.md`
- `references/CONTENT_STANDARDS.md`
- `scripts/README.md`
