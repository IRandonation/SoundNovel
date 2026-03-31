# 项目结构优化方案

## TL;DR

> **Quick Summary**: 对 SoundNovel 项目进行结构性重构，包括配置合并、GUI 模块化、删除智谱 AI 相关代码、工程化补齐，提升可维护性而不改变业务逻辑。
>
> **Deliverables**:
> - 统一的 ConfigManager（合并 Settings/SessionManager/GenerationConfigManager）
> - 模块化的 GUI 结构（gui/tabs/）
> - 删除智谱 AI (glm/zhipu) 相关代码和依赖
> - pytest/ruff/mypy 工程化配置
> - 核心模块基础测试
> - 清理的 __pycache__ 目录
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Wave 1 → Wave 2 → Wave 3/4 (parallel) → Final Verification

---

## Context

### Original Request
Oracle 分析报告指出项目存在 6 个可优化点，用户选择一次全做（排除模型常量提取，改为删除智谱 AI 相关代码）。

### Interview Summary
**Key Discussions**:
- **执行范围**: 配置合并、GUI拆分、删除智谱AI、工程化补齐、__pycache__清理
- **测试策略**: 补齐 pytest + 核心模块测试（TDD where applicable）
- **GUI 拆分**: 按功能模块拆分（gui/tabs/）
- **配置合并**: 激进合并 → 统一 ConfigManager
- **删除智谱 AI**: 删除 glm/zhipu 相关代码、依赖、文档

**Research Findings**:
- AIRoleConfig/AIRolesConfig 在 3 个文件重复定义
- gui_app.py 约 1143 行
- 无测试框架、无 lint/typecheck
- Role configs 存储在两处（session.json 和 generation_config.json）
- 智谱 AI 相关内容分布在 4 个文件（pyproject.toml, README.md, docs/AGENTS.md, multi_model_client.py）

### Metis Review
**Identified Gaps** (addressed):
- **配置合并单一真相源**: 应用默认值 → generation_config.json 为角色配置真相源，session.json 为 API keys/运行状态
- **向后兼容迁移**: 生成迁移脚本处理现有用户配置
- **GUI tabs 独立性**: 保持单页 tabs 结构（不使用 Streamlit 多页面），session_state 跨模块访问需文档化
- **测试覆盖率目标**: 目标 30%（核心配置模块）

---

## Work Objectives

### Core Objective
重构项目结构，提升可维护性，保持业务逻辑不变。

### Concrete Deliverables
- `novel_generator/config/ai_roles.py` — 统一的 AIRoleConfig 定义（删除其他重复）
- `novel_generator/config/config_manager.py` — 统一 ConfigManager
- `novel_generator/gui/tabs/` — 模块化的 GUI tabs
- `tests/` — pytest 测试目录 + 核心模块测试
- `pyproject.toml` — pytest/ruff/mypy 配置，删除 zhipuai 依赖
- 迁移脚本 `scripts/migrate_config.py`
- 删除智谱 AI 相关代码和文档

### Definition of Done
- [ ] 所有 CLI 命令功能不变（init/status/outline/expand/continue/settings）
- [ ] GUI 5 tabs 功能不变
- [ ] 现有配置文件可读（向后兼容）
- [ ] pytest 测试通过
- [ ] ruff/mypy 检查通过
- [ ] 智谱 AI 相关代码和依赖已删除

### Must Have
- 统一的 ConfigManager
- pytest/ruff/mypy 配置
- 核心配置模块测试（load/save/roundtrip）
- __pycache__ 清理
- 删除智谱 AI 相关代码

### Must NOT Have (Guardrails)
- **业务逻辑改动**: ChapterExpander/OutlineGenerator/Reviewer/Refiner 逻辑不变
- **新功能**: 无新 CLI 命令、无新 GUI tabs、无新配置选项
- **破坏性 API 改变**: 保持现有 CLI 命令签名
- **JSON schema 无迁移**: 配置文件格式改变必须提供迁移脚本
- **AI slop patterns**: 不添加过度注释、过度抽象、过度文档

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: YES (TDD for config classes, tests-after for other modules)
- **Framework**: pytest
- **Coverage Target**: 30% (core config modules)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright (playwright skill) — Navigate Streamlit GUI, interact with tabs, assert DOM, screenshot
- **CLI**: Use Bash — Run CLI commands, validate output, check exit code
- **Config/API**: Use Bash (curl/Python REPL) — Load/save/roundtrip config, assert values
- **Library/Module**: Use Bash (pytest) — Run tests, check coverage

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — Safety Net):
├── Task 1: pytest infrastructure setup [quick]
├── Task 2: ruff/mypy configuration [quick]
├── Task 3: Config class tests (TDD baseline) [quick]
└── Task 4: Pre-refactor verification (CLI/GUI smoke test) [quick]

Wave 2 (After Wave 1 — Config Cleanup + Delete Zhipu AI):
├── Task 5: AIRoleConfig deduplication [quick]
├── Task 6: Delete zhipuai dependency from pyproject.toml [quick]
├── Task 7: Delete zhipu/glm references from docs [quick]
└── Task 8: Delete zhipu references from code comments [quick]

Wave 3 (After Wave 2 — Config Merge, Parallel with Wave 4):
├── Task 9: ConfigManager design [deep]
├── Task 10: ConfigManager implementation [deep]
├── Task 11: Migration script [unspecified-high]
├── Task 12: Update all config imports [unspecified-high]
└── Task 13: Config roundtrip test [quick]

Wave 4 (After Wave 2 — Parallel with Wave 3):
├── Task 14: GUI tabs extraction [visual-engineering]
├── Task 15: GUI utils module [quick]
├── Task 16: GUI app refactor (thin coordinator) [quick]
├── Task 17: Session state documentation [writing]
└── Task 18: GUI module tests [quick]

Wave FINAL (After Waves 3 & 4 — Cleanup + Verification):
├── Task 19: __pycache__ cleanup [quick]
├── Task 20: Final CLI verification [quick]
├── Task 21: Final GUI verification [unspecified-high]
├── Task 22: Test coverage check [quick]
├── Task 23: Lint/typecheck verification [quick]
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: W1 → W2 → W3/W4 → FINAL → user okay
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 5 (Wave 3 & 4)
```

### Dependency Matrix

- **1-4**: — — 5-8, 9-13, 14-18, 1
- **5-8**: 3 — 9-13, 14-18, 1
- **9-13**: 5 — 19-23, F1-F4, 2
- **14-18**: 5 — 19-23, F1-F4, 2
- **19-23, F1-F4**: 9-13, 14-18 — user okay

### Agent Dispatch Summary

- **W1**: **4** — T1-T4 → `quick`
- **W2**: **4** — T5 → `quick`, T6-T8 → `quick`
- **W3**: **5** — T9-T10 → `deep`, T11-T12 → `unspecified-high`, T13 → `quick`
- **W4**: **5** — T14 → `visual-engineering`, T15-T16 → `quick`, T17 → `writing`, T18 → `quick`
- **FINAL**: **9** — T19-T20, T22-T23 → `quick`, T21 → `unspecified-high`, F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

### Wave 1: Safety Net (Start Immediately)

- [x] 1. **pytest Infrastructure Setup**

  **What to do**:
  - Add pytest to dev dependencies: `uv add --dev pytest pytest-cov`
  - Create `tests/` directory structure: `tests/__init__.py`, `tests/conftest.py`
  - Add pytest config to `pyproject.toml`: testpaths, coverage settings
  - Verify: `uv run pytest --collect-only` succeeds

  **Must NOT do**:
  - Do NOT add test files for all modules yet
  - Do NOT configure coverage thresholds (just enable reporting)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file config changes, standard pytest setup
  - **Skills**: []
    - No specialized skills needed for basic pytest setup

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Task 3, Task 22
  - **Blocked By**: None

  **References**:
  - `pyproject.toml:1-50` - Current dependency configuration, add pytest alongside existing deps
  - Standard pytest config pattern: `testpaths = ["tests"]`, `addopts = "-v --cov=novel_generator"`

  **Acceptance Criteria**:
  - [ ] pytest in dev dependencies: `uv pip list | grep pytest` shows pytest
  - [ ] tests/ directory exists with __init__.py and conftest.py
  - [ ] pytest config in pyproject.toml
  - [ ] `uv run pytest --collect-only` exits with 0

  **QA Scenarios**:
  ```
  Scenario: pytest infrastructure works
    Tool: Bash
    Preconditions: pyproject.toml exists
    Steps:
      1. Run: uv run pytest --collect-only
      2. Check exit code
    Expected Result: Exit code 0, no collection errors
    Failure Indicators: "module not found", "config error"
    Evidence: .sisyphus/evidence/task-1-pytest-setup.log

  Scenario: pytest-cov available
    Tool: Bash
    Steps:
      1. Run: uv run pytest --cov=novel_generator --cov-report=term --collect-only
    Expected Result: Coverage plugin loaded, no errors
    Evidence: .sisyphus/evidence/task-1-cov-setup.log
  ```

  **Commit**: YES
  - Message: `test: add pytest infrastructure`
  - Files: pyproject.toml, tests/__init__.py, tests/conftest.py

- [x] 2. **ruff/mypy Configuration**

  **What to do**:
  - Add ruff and mypy to dev dependencies: `uv add --dev ruff mypy`
  - Create `pyproject.toml` config sections for ruff (lint rules, exclude patterns) and mypy (strictness level)
  - Verify: `uv run ruff check . --statistics` and `uv run mypy novel_generator` succeed

  **Must NOT do**:
  - Do NOT enable overly strict rules that fail on existing code
  - Do NOT fix existing lint errors (just establish baseline config)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard linting config setup
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 23
  - **Blocked By**: None

  **References**:
  - `pyproject.toml:1-50` - Add config alongside pytest
  - Standard ruff config: select = ["E", "F", "W"], exclude = ["__pycache__"]
  - Standard mypy config: python_version = "3.10", warn_return_any = true

  **Acceptance Criteria**:
  - [ ] ruff/mypy in dev dependencies
  - [ ] ruff config in pyproject.toml
  - [ ] mypy config in pyproject.toml
  - [ ] `uv run ruff check . --statistics` exits with 0
  - [ ] `uv run mypy novel_generator` exits with 0 or shows errors (baseline)

  **QA Scenarios**:
  ```
  Scenario: ruff runs successfully
    Tool: Bash
    Steps:
      1. Run: uv run ruff check . --statistics
    Expected Result: Exit code 0, shows statistics
    Evidence: .sisyphus/evidence/task-2-ruff.log

  Scenario: mypy runs successfully
    Tool: Bash
    Steps:
      1. Run: uv run mypy novel_generator --no-error-summary
    Expected Result: Exit code 0 or lists type issues (baseline established)
    Evidence: .sisyphus/evidence/task-2-mypy.log
  ```

  **Commit**: YES
  - Message: `chore: add ruff and mypy configuration`
  - Files: pyproject.toml

- [x] 3. **Config Class Tests (TDD Baseline)**

  **What to do**:
  - Create `tests/config/` directory: `tests/config/__init__.py`, `tests/config/test_settings.py`, `tests/config/test_generation_config.py`, `tests/config/test_session.py`
  - Write tests for existing config classes: load/save/roundtrip, default values, validation
  - Focus on Settings, GenerationConfigManager, SessionManager
  - Run tests: `uv run pytest tests/config/ -v` should pass (existing code should work)

  **Must NOT do**:
  - Do NOT test refactored code (test CURRENT code first)
  - Do NOT add tests for business logic modules yet

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Test file creation, straightforward assertions
  - **Skills**: []
    - No specialized skills needed for basic test writing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 13, Task 18
  - **Blocked By**: Task 1 (pytest infrastructure)

  **References**:
  - `novel_generator/config/settings.py:Settings` - Class to test load/save
  - `novel_generator/config/generation_config.py:GenerationConfigManager` - Class to test
  - `novel_generator/config/session.py:SessionManager` - Class to test
  - `tests/conftest.py` - Use for fixtures (sample config files)

  **Acceptance Criteria**:
  - [ ] tests/config/ directory exists with test files
  - [ ] Tests for Settings load/save/roundtrip
  - [ ] Tests for GenerationConfigManager
  - [ ] Tests for SessionManager
  - [ ] `uv run pytest tests/config/ -v` passes

  **QA Scenarios**:
  ```
  Scenario: config tests pass
    Tool: Bash
    Preconditions: pytest infrastructure ready (Task 1)
    Steps:
      1. Run: uv run pytest tests/config/ -v
    Expected Result: All tests pass, coverage reported
    Failure Indicators: "FAILED", "ERROR"
    Evidence: .sisyphus/evidence/task-3-config-tests.log

  Scenario: roundtrip test validates config integrity
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/config/test_settings.py::test_settings_roundtrip -v
    Expected Result: Test passes, config load→save→load produces identical state
    Evidence: .sisyphus/evidence/task-3-roundtrip.log
  ```

  **Commit**: YES
  - Message: `test: add config class tests (TDD baseline)`
  - Files: tests/config/__init__.py, tests/config/test_settings.py, tests/config/test_generation_config.py, tests/config/test_session.py
  - Pre-commit: `uv run pytest tests/config/ -v`

- [x] 4. **Pre-refactor Verification (CLI/GUI Smoke Test)**

  **What to do**:
  - Run all CLI commands and document expected outputs: init, status, settings --show-file
  - Launch GUI headless and verify 5 tabs render
  - Capture baseline behavior for comparison after refactoring
  - Document in `.sisyphus/evidence/baseline/`

  **Must NOT do**:
  - Do NOT execute business commands (outline, expand) — focus on config/UI commands
  - Do NOT modify any code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification execution, documentation
  - **Skills**: []
    - No specialized skills needed for smoke tests

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 20, Task 21, F3
  - **Blocked By**: None

  **References**:
  - `soundnovel.py:cli` - Entry point for CLI commands
  - `novel_generator/gui/app.py` or `gui_app.py` - GUI entry point
  - README.md:CLI Commands - Expected command signatures

  **Acceptance Criteria**:
  - [ ] CLI init works: `uv run python soundnovel.py cli init` succeeds
  - [ ] CLI status works: `uv run python soundnovel.py cli status` succeeds
  - [ ] CLI settings works: `uv run python soundnovel.py cli settings --show-file` succeeds
  - [ ] GUI launches: headless Streamlit runs, tabs visible
  - [ ] Baseline captured in .sisyphus/evidence/baseline/

  **QA Scenarios**:
  ```
  Scenario: CLI commands work
    Tool: Bash
    Steps:
      1. Run: uv run python soundnovel.py cli init
      2. Run: uv run python soundnovel.py cli status
      3. Run: uv run python soundnovel.py cli settings --show-file
    Expected Result: All commands exit with 0, expected output format
    Evidence: .sisyphus/evidence/task-4-cli-baseline.log

  Scenario: GUI launches headless
    Tool: Bash
    Steps:
      1. Start: uv run streamlit run gui_app.py --server.headless true &
      2. Wait: sleep 5
      3. Check: curl -s http://localhost:8501 | grep -E "(Tab|配置|生成|大纲|扩写|评审)"
    Expected Result: HTML contains tab-related content
    Evidence: .sisyphus/evidence/task-4-gui-baseline.log
  ```

  **Commit**: NO
  - Just evidence capture, no code changes

### Wave 2: Config Cleanup + Delete Zhipu AI (After Wave 1)

- [x] 5. **AIRoleConfig Deduplication**

  **What to do**:
  - Consolidate AIRoleConfig/AIRolesConfig definitions to single location: `novel_generator/config/ai_roles.py`
  - **Naming decision**: Use `AIRoleConfig` as canonical class name (matches existing duplicates)
  - Rename `RoleConfig` in `novel_generator/core/ai_roles.py` to `AIRoleConfig` if needed
  - Delete duplicate definitions from settings.py (AIRoleConfig) and session.py (AIRoleState)
  - Update imports in affected files: settings.py, session.py, other consumers
  - Verify: `uv run pytest tests/config/ -v` still passes

  **Must NOT do**:
  - Do NOT change AIRoleConfig structure/fields (preserve all existing fields)
  - Do NOT delete files that have other important code
  - Do NOT use inconsistent naming (standardize on `AIRoleConfig`)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Code relocation, import updates, naming standardization
  - **Skills**: [`git-master`]
    - `git-master`: Use lsp_find_references to find all usages before renaming/moving

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8)
  - **Blocks**: Task 9, Task 10
  - **Blocked By**: Task 3 (config tests should pass before refactoring)

  **References**:
  - `novel_generator/config/settings.py:15-113` - Duplicate `AIRoleConfig` class to remove
  - `novel_generator/config/session.py:70-160` - Duplicate `AIRoleState` class to remove (rename to match AIRoleConfig or delete)
  - `novel_generator/core/ai_roles.py:44-142` - Current `RoleConfig` class, rename to `AIRoleConfig`
  - Use `lsp_find_references` on `AIRoleConfig` and `RoleConfig` to find all usages

  **Acceptance Criteria**:
  - [ ] Single `AIRoleConfig` definition in `novel_generator/config/ai_roles.py` (moved from core/)
  - [ ] Class named consistently as `AIRoleConfig` (not `RoleConfig`)
  - [ ] No duplicate definitions in settings.py, session.py
  - [ ] All imports updated to use `AIRoleConfig`
  - [ ] `uv run pytest tests/config/ -v` passes

  **QA Scenarios**:
  ```
  Scenario: only one AIRoleConfig definition exists
    Tool: Bash
    Steps:
      1. Run: grep -r "class AIRoleConfig" novel_generator/ --include="*.py" | wc -l
    Expected Result: Output is "1"
    Failure Indicators: Output > 1 (duplicates still exist)
    Evidence: .sisyphus/evidence/task-5-single-definition.log

  Scenario: RoleConfig renamed to AIRoleConfig
    Tool: Bash
    Steps:
      1. Run: grep -r "class RoleConfig" novel_generator/ --include="*.py" | wc -l
    Expected Result: Output is "0" (RoleConfig renamed)
    Failure Indicators: Output > 0 (old name still exists)
    Evidence: .sisyphus/evidence/task-5-renamed.log

  Scenario: config tests pass after dedup
    Tool: Bash
    Preconditions: Task 3 completed
    Steps:
      1. Run: uv run pytest tests/config/ -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-5-tests-pass.log
  ```

  **Commit**: YES
  - Message: `refactor: consolidate AIRoleConfig to config/ai_roles.py with standard naming`
  - Files: novel_generator/config/ai_roles.py (new location), novel_generator/config/settings.py, novel_generator/config/session.py, novel_generator/core/ai_roles.py (delete or update), affected imports
  - Pre-commit: `uv run pytest tests/config/ -v`

- [x] 6. **Delete zhipuai Dependency**

  **What to do**:
  - Remove `zhipuai>=2.1.5.20250801` from `pyproject.toml` dependencies
  - Run `uv sync` to update lock file
  - Verify: `uv pip list | grep zhipu` returns nothing

  **Must NOT do**:
  - Do NOT remove other dependencies
  - Do NOT change version constraints of other packages

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-line config change
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7, 8)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `pyproject.toml:20` - `zhipuai>=2.1.5.20250801` line to remove
  - `uv sync` command to update dependencies

  **Acceptance Criteria**:
  - [ ] zhipuai removed from pyproject.toml
  - [ ] `uv sync` runs successfully
  - [ ] `uv pip list | grep zhipu` returns empty

  **QA Scenarios**:
  ```
  Scenario: zhipuai removed from dependencies
    Tool: Bash
    Steps:
      1. Run: grep "zhipuai" pyproject.toml
    Expected Result: Exit code 1 (no match found)
    Evidence: .sisyphus/evidence/task-6-no-zhipuai.log

  Scenario: uv sync succeeds
    Tool: Bash
    Steps:
      1. Run: uv sync
    Expected Result: Exit code 0, dependencies synced
    Evidence: .sisyphus/evidence/task-6-uv-sync.log
  ```

  **Commit**: YES
  - Message: `chore: remove zhipuai dependency`
  - Files: pyproject.toml, uv.lock

- [x] 7. **Delete Zhipu/GLM References from Docs**

  **What to do**:
  - Update `README.md`: change "智谱、豆包、DeepSeek" to "豆包、DeepSeek"
  - Update `docs/AGENTS.md`: remove zhipu/glm example configurations and references
  - Update `docs/ARCHITECTURE.md` if contains zhipu references
  - Verify: `grep -ri "zhipu\|glm\|智谱" docs/ README.md` returns empty

  **Must NOT do**:
  - Do NOT change other documentation content
  - Do NOT break existing formatting

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Documentation updates
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 8)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `README.md:10` - "智谱、豆包、DeepSeek" to change
  - `docs/AGENTS.md:7,383,385` - Zhipu references to remove
  - grep pattern: `grep -ri "zhipu\|glm\|智谱" docs/ README.md`

  **Acceptance Criteria**:
  - [ ] README.md updated (no zhipu/智谱 references)
  - [ ] docs/AGENTS.md updated (no zhipu/glm examples)
  - [ ] grep check returns empty

  **QA Scenarios**:
  ```
  Scenario: no zhipu/glm references in docs
    Tool: Bash
    Steps:
      1. Run: grep -ri "zhipu\|glm\|智谱" docs/ README.md
    Expected Result: Exit code 1 (no match found)
    Evidence: .sisyphus/evidence/task-7-docs-clean.log
  ```

  **Commit**: YES
  - Message: `docs: remove zhipu/glm references`
  - Files: README.md, docs/AGENTS.md, docs/ARCHITECTURE.md

- [x] 8. **Delete Zhipu References from Code**

  **What to do**:
  - Update `novel_generator/utils/multi_model_client.py`: remove "智谱AI" from docstring/comment
  - Search for any other zhipu/glm references in code: `grep -ri "zhipu\|glm\|智谱" novel_generator/`
  - Remove any found references
  - Verify: grep returns empty

  **Must NOT do**:
  - Do NOT change business logic
  - Do NOT remove actual model provider code (only references to zhipu that don't exist)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Comment/docstring cleanup
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `novel_generator/utils/multi_model_client.py:2-4` - Docstring mentions "智谱AI"
  - grep pattern: `grep -ri "zhipu\|glm\|智谱" novel_generator/ --include="*.py"`

  **Acceptance Criteria**:
  - [ ] multi_model_client.py docstring updated
  - [ ] No zhipu/glm references in code files
  - [ ] Code still works

  **QA Scenarios**:
  ```
  Scenario: no zhipu/glm references in code
    Tool: Bash
    Steps:
      1. Run: grep -ri "zhipu\|glm\|智谱" novel_generator/ --include="*.py"
    Expected Result: Exit code 1 (no match found)
    Evidence: .sisyphus/evidence/task-8-code-clean.log

  Scenario: code still works after cleanup
    Tool: Bash
    Steps:
      1. Run: uv run python -c "from novel_generator.utils.multi_model_client import MultiModelClient; print('OK')"
    Expected Result: Prints 'OK', no ImportError
    Evidence: .sisyphus/evidence/task-8-code-works.log
  ```

  **Commit**: YES
  - Message: `chore: remove zhipu references from code`
  - Files: novel_generator/utils/multi_model_client.py, other affected files

### Wave 3: Config Merge (High Risk, Parallel with Wave 4)

- [x] 9. **ConfigManager Design**

  **What to do**:
  - Design unified ConfigManager interface in `novel_generator/config/config_manager.py`
  - Define responsibilities: single source of truth for role configs (generation_config.json), API keys in session.json
  - Document migration strategy from Settings/GenerationConfigManager/SessionManager
  - Create design doc in `.sisyphus/drafts/config-manager-design.md`

  **Must NOT do**:
  - Do NOT implement yet (design first)
  - Do NOT change existing config file schemas without migration plan

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Architecture decision with long-term impact, requires careful planning
  - **Skills**: []
    - No specialized skills needed for design phase

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 11, 12, 13)
  - **Blocks**: Task 10, Task 12
  - **Blocked By**: Task 5 (AIRoleConfig consolidated)

  **References**:
  - `novel_generator/config/settings.py:Settings` - Current Settings implementation to merge
  - `novel_generator/config/generation_config.py:GenerationConfigManager` - Current GenConfig to merge
  - `novel_generator/config/session.py:SessionManager` - Current SessionManager to merge
  - Metis recommendation: generation_config.json for roles, session.json for API keys

  **Acceptance Criteria**:
  - [ ] Design doc created: `.sisyphus/drafts/config-manager-design.md`
  - [ ] ConfigManager interface defined (load/save/roundtrip methods)
  - [ ] Migration strategy documented
  - [ ] Single source of truth specified

  **QA Scenarios**:
  ```
  Scenario: design doc exists and is complete
    Tool: Bash
    Steps:
      1. Read: .sisyphus/drafts/config-manager-design.md
      2. Check: grep -E "interface|migration|single source" .sisyphus/drafts/config-manager-design.md
    Expected Result: All sections present
    Evidence: .sisyphus/evidence/task-9-design-complete.log
  ```

  **Commit**: NO
  - Design phase, no production code yet

- [x] 10. **ConfigManager Implementation**

  **What to do**:
  - Implement ConfigManager in `novel_generator/config/config_manager.py`
  - Consolidate: load generation_config.json for roles, session.json for API keys
  - Provide backward-compatible access methods: get_role_config(), get_api_key()
  - Implement save methods with proper JSON serialization
  - Verify: `uv run pytest tests/config/test_config_manager.py -v` passes (write test first)

  **Must NOT do**:
  - Do NOT break existing CLI commands
  - Do NOT change business logic

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex implementation merging three config sources
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 11, 12, 13)
  - **Blocks**: Task 12, Task 13
  - **Blocked By**: Task 9 (design), Task 5 (AIRoleConfig consolidated)

  **References**:
  - `.sisyphus/drafts/config-manager-design.md` - Design to implement
  - `novel_generator/config/ai_roles.py` - AIRoleConfig to use
  - `05_script/generation_config.json` - JSON structure for roles
  - `05_script/session.json` - JSON structure for API keys

  **Acceptance Criteria**:
  - [ ] ConfigManager class implemented
  - [ ] load/save methods work
  - [ ] Backward-compatible access methods
  - [ ] Tests pass

  **QA Scenarios**:
  ```
  Scenario: ConfigManager loads existing configs
    Tool: Bash
    Steps:
      1. Run: uv run python -c "from novel_generator.config.config_manager import ConfigManager; cm = ConfigManager(); cm.load(); print(cm.get_role_config('generator').model)"
    Expected Result: Prints model name from generation_config.json
    Evidence: .sisyphus/evidence/task-10-cm-load.log

  Scenario: ConfigManager roundtrip works
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/config/test_config_manager.py::test_roundtrip -v
    Expected Result: Test passes
    Evidence: .sisyphus/evidence/task-10-cm-roundtrip.log
  ```

  **Commit**: YES
  - Message: `refactor: implement unified ConfigManager`
  - Files: novel_generator/config/config_manager.py, tests/config/test_config_manager.py
  - Pre-commit: `uv run pytest tests/config/test_config_manager.py -v`

- [x] 11. **Migration Script**

  **What to do**:
  - Create `scripts/migrate_config.py` for existing user configs
  - Handle: session.json + generation_config.json → new unified format
  - Provide conflict resolution (generation_config.json roles take precedence)
  - Add validation and error handling
  - Verify: script runs on sample configs, produces valid output

  **Must NOT do**:
  - Do NOT modify user's actual config files (script should be optional/runnable separately)
  - Do NOT auto-run migration without user consent

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Migration logic requires careful handling of edge cases
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 12, 13)
  - **Blocks**: None (optional tool)
  - **Blocked By**: Task 9 (design)

  **References**:
  - `05_script/session.json` - Sample session config for testing migration
  - `05_script/generation_config.json` - Sample generation config for testing migration
  - `.sisyphus/drafts/config-manager-design.md` - Migration strategy

  **Acceptance Criteria**:
  - [ ] Migration script created: `scripts/migrate_config.py`
  - [ ] Handles both config files
  - [ ] Conflict resolution documented
  - [ ] Validation included
  - [ ] Tested on sample configs

  **QA Scenarios**:
  ```
  Scenario: migration script runs successfully
    Tool: Bash
    Preconditions: Sample config files exist
    Steps:
      1. Run: uv run python scripts/migrate_config.py --dry-run --session 05_script/session.json --generation 05_script/generation_config.json
    Expected Result: Script exits 0, shows migration preview
    Evidence: .sisyphus/evidence/task-11-migration-dry.log

  Scenario: migration produces valid output
    Tool: Bash
    Steps:
      1. Run migration on test configs
      2. Validate output JSON loads correctly
    Expected Result: Output JSON valid, ConfigManager can load it
    Evidence: .sisyphus/evidence/task-11-migration-valid.log
  ```

  **Commit**: YES
  - Message: `feat: add config migration script`
  - Files: scripts/migrate_config.py

- [x] 12. **Update All Config Imports**

  **What to do**:
  - Find all usages of Settings, GenerationConfigManager, SessionManager using lsp_find_references
  - Update imports to use ConfigManager where appropriate
  - Maintain backward-compatible aliases in old files if needed
  - Verify: CLI commands still work, tests pass

  **Must NOT do**:
  - Do NOT delete old config files (keep for backward compatibility or transition period)
  - Do NOT break CLI commands

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Many files affected, need careful import updates
  - **Skills**: [`git-master`]
    - `git-master`: Use lsp_find_references to find all usages before updating

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11, 13)
  - **Blocks**: Wave 5
  - **Blocked By**: Task 10 (ConfigManager implemented), Task 6 (AIRoleConfig consolidated)

  **References**:
  - Use `lsp_find_references` on Settings, GenerationConfigManager, SessionManager
  - `novel_generator/cli/commands/settings_cmd.py` - CLI settings command to update
  - `novel_generator/gui/gui_app.py` or gui_app.py - GUI to update
  - `novel_generator/core/chapter_expander.py` - Core logic using configs

  **Acceptance Criteria**:
  - [ ] All imports updated to ConfigManager where appropriate
  - [ ] CLI commands work: `uv run python soundnovel.py cli settings`
  - [ ] Tests pass: `uv run pytest tests/ -v`

  **QA Scenarios**:
  ```
  Scenario: CLI settings command works with ConfigManager
    Tool: Bash
    Steps:
      1. Run: uv run python soundnovel.py cli settings --show-file
    Expected Result: Command succeeds, shows config file path
    Evidence: .sisyphus/evidence/task-12-cli-settings.log

  Scenario: all tests pass after import updates
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/ -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-12-tests-pass.log
  ```

  **Commit**: YES
  - Message: `refactor: update imports to use ConfigManager`
  - Files: All affected files (CLI, GUI, core modules)
  - Pre-commit: `uv run pytest tests/ -v`

- [x] 13. **Config Roundtrip Test**

  **What to do**:
  - Write comprehensive roundtrip test for ConfigManager in `tests/config/test_config_manager.py`
  - Test: load → modify → save → load produces identical state
  - Test edge cases: missing fields, conflict resolution, backward compatibility
  - Verify: test passes

  **Must NOT do**:
  - Do NOT modify ConfigManager (test should pass if implementation correct)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Test writing
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 9, 10, 11, 12)
  - **Blocks**: Wave 5
  - **Blocked By**: Task 10 (ConfigManager implemented)

  **References**:
  - `novel_generator/config/config_manager.py` - ConfigManager to test
  - `tests/config/test_settings.py` - Existing test patterns to follow

  **Acceptance Criteria**:
  - [ ] Roundtrip test written
  - [ ] Edge cases tested
  - [ ] Test passes

  **QA Scenarios**:
  ```
  Scenario: roundtrip test passes
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/config/test_config_manager.py::test_roundtrip -v
    Expected Result: Test passes
    Evidence: .sisyphus/evidence/task-13-roundtrip.log
  ```

  **Commit**: YES
  - Message: `test: add ConfigManager roundtrip tests`
  - Files: tests/config/test_config_manager.py

---

### Wave 4: GUI Modularization (Parallel with Wave 3)

- [x] 14. **GUI Tabs Extraction**

  **What to do**:
  - **IMPORTANT**: Keep `gui_app.py` at project root (do NOT move it)
  - Create `novel_generator/gui/tabs/` directory structure for extracted tab modules
  - Extract each tab from gui_app.py to separate module under `novel_generator/gui/tabs/`:
    - `tabs/__init__.py`
    - `tabs/config_tab.py` - Configuration tab
    - `tabs/generation_tab.py` - Generation control tab
    - `tabs/outline_tab.py` - Outline management tab
    - `tabs/expand_tab.py` - Chapter expansion tab
    - `tabs/review_tab.py` - Review/refine tab
  - Each tab module should have a `render()` function
  - Verify: imports work from root `gui_app.py`, no circular dependencies

  **Must NOT do**:
  - Do NOT move `gui_app.py` from root (keep at `D:\Project\SoundNovel\gui_app.py`)
  - Do NOT change tab behavior (just relocate code)
  - Do NOT create new tabs
  - Do NOT break session_state access

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI component extraction, Streamlit-specific patterns
  - **Skills**: []
    - No specialized skills needed for Streamlit tab extraction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 15, 16, 17, 18)
  - **Blocks**: Task 16
  - **Blocked By**: Task 3 (config tests should pass before GUI refactor)

  **References**:
  - `gui_app.py` (root level) - Source file to split (1143 lines), **DO NOT MOVE**
  - Existing render functions pattern: `render_*_tab()` functions in gui_app.py
  - Streamlit session_state keys: documented in README or gui_app.py comments
  - Import pattern: `from novel_generator.gui.tabs.config_tab import render`

  **Acceptance Criteria**:
  - [ ] `novel_generator/gui/tabs/__init__.py` exists
  - [ ] 5 tab modules created: config_tab.py, generation_tab.py, outline_tab.py, expand_tab.py, review_tab.py
  - [ ] Each tab has `render()` function
  - [ ] `gui_app.py` still at root, imports tabs from `novel_generator.gui.tabs`
  - [ ] No circular imports

  **QA Scenarios**:
  ```
  Scenario: tab modules import correctly from gui_app.py
    Tool: Bash
    Steps:
      1. Run: uv run python -c "from novel_generator.gui.tabs.config_tab import render; print('OK')"
    Expected Result: Prints 'OK', no ImportError
    Evidence: .sisyphus/evidence/task-14-tab-import.log

  Scenario: all 5 tabs extracted
    Tool: Bash
    Steps:
      1. Run: ls novel_generator/gui/tabs/*.py | wc -l
    Expected Result: Output is "6" (5 tabs + __init__.py)
    Evidence: .sisyphus/evidence/task-14-tab-count.log

  Scenario: gui_app.py still at root
    Tool: Bash
    Steps:
      1. Run: test -f gui_app.py && echo "PASS: gui_app.py at root"
    Expected Result: Prints 'PASS', file exists at root
    Evidence: .sisyphus/evidence/task-14-gui-root.log
  ```

  **Commit**: YES
  - Message: `refactor: extract GUI tabs to novel_generator/gui/tabs/`
  - Files: novel_generator/gui/__init__.py, novel_generator/gui/tabs/__init__.py, tabs/config_tab.py, tabs/generation_tab.py, tabs/outline_tab.py, tabs/expand_tab.py, tabs/review_tab.py

- [x] 15. **GUI Utils Module**

  **What to do**:
  - Create `novel_generator/gui/utils/__init__.py`
  - Extract common helpers from gui_app.py:
    - Session state initialization
    - Config loading/saving helpers
    - Common UI components (buttons, inputs)
  - Document session_state keys in `utils/session_keys.py`
  - Verify: utils can be imported from tabs

  **Must NOT do**:
  - Do NOT over-abstract (keep minimal, practical)
  - Do NOT add new utilities

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Utility extraction, straightforward
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 14, 16, 17, 18)
  - **Blocks**: Task 16
  - **Blocked By**: Task 14 (tabs extracted)

  **References**:
  - `gui_app.py` - Source for common helpers
  - Streamlit session_state patterns

  **Acceptance Criteria**:
  - [ ] `novel_generator/gui/utils/__init__.py` exists
  - [ ] Common helpers extracted
  - [ ] Session state keys documented
  - [ ] Utils importable from tabs

  **QA Scenarios**:
  ```
  Scenario: utils module exists and imports work
    Tool: Bash
    Steps:
      1. Run: uv run python -c "from novel_generator.gui.utils import init_session_state; print('OK')"
    Expected Result: Prints 'OK', no ImportError
    Evidence: .sisyphus/evidence/task-15-utils-import.log
  ```

  **Commit**: YES
  - Message: `refactor: extract GUI utils`
  - Files: novel_generator/gui/utils/__init__.py, utils/session_keys.py

- [x] 16. **GUI App Refactor (Thin Coordinator)**

  **What to do**:
  - Refactor `gui_app.py` (at root) to thin coordinator: import tabs from `novel_generator.gui.tabs`, render tabs in sequence
  - Remove inline tab code (now in tab modules under `novel_generator/gui/tabs/`)
  - Keep main layout: title, sidebar, tab navigation
  - Verify: GUI launches from root `gui_app.py`, all tabs render correctly
  - Line count should drop significantly (<200 lines in gui_app.py)

  **Must NOT do**:
  - Do NOT move `gui_app.py` from root (keep at `D:\Project\SoundNovel\gui_app.py`)
  - Do NOT change GUI appearance or behavior
  - Do NOT break session_state

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Code relocation, reduce file size
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 14, 15, 17, 18)
  - **Blocks**: Task 21
  - **Blocked By**: Task 14, Task 15

  **References**:
  - `gui_app.py` (root) - File to refactor, stays at root
  - `novel_generator/gui/tabs/*.py` - Imported tab modules
  - `novel_generator/gui/utils/*.py` - Imported utils
  - Original gui_app.py layout structure preserved

  **Acceptance Criteria**:
  - [ ] `gui_app.py` refactored to thin coordinator at root
  - [ ] Tabs imported from `novel_generator.gui.tabs` and rendered
  - [ ] Line count in `gui_app.py` <200
  - [ ] GUI launches successfully from `gui_app.py`

  **QA Scenarios**:
  ```
  Scenario: GUI launches after refactor from root
    Tool: Bash
    Steps:
      1. Start: uv run streamlit run gui_app.py --server.headless true &
      2. Wait: sleep 5
      3. Check: curl -s http://localhost:8501 | grep "小说创作助手"
    Expected Result: HTML contains app title
    Evidence: .sisyphus/evidence/task-16-gui-launch.log

  Scenario: line count reduced in gui_app.py
    Tool: Bash
    Steps:
      1. Run: wc -l gui_app.py
    Expected Result: Line count <200
    Evidence: .sisyphus/evidence/task-16-line-count.log
  ```

  **Commit**: YES
  - Message: `refactor: modularize gui_app.py into thin coordinator`
  - Files: gui_app.py (at root)
  - Pre-commit: GUI smoke test from root

- [x] 17. **Session State Documentation**

  **What to do**:
  - Create `novel_generator/gui/utils/session_keys.py` documenting all session_state keys
  - Document: key name, purpose, type, which tabs use it
  - Update tabs to use documented keys
  - Verify: documentation complete

  **Must NOT do**:
  - Do NOT change session_state key names (preserve existing)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation task
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 14, 15, 16, 18)
  - **Blocks**: None
  - **Blocked By**: Task 14 (tabs extracted)

  **References**:
  - `gui_app.py` - Existing session_state keys
  - `novel_generator/gui/tabs/*.py` - Tabs using session_state

  **Acceptance Criteria**:
  - [ ] session_keys.py created
  - [ ] All keys documented
  - [ ] Tabs use documented keys

  **QA Scenarios**:
  ```
  Scenario: session keys documented
    Tool: Bash
    Steps:
      1. Run: grep -E "^#|^KEY_" novel_generator/gui/utils/session_keys.py | wc -l
    Expected Result: Count >10 (documented keys)
    Evidence: .sisyphus/evidence/task-17-keys-doc.log
  ```

  **Commit**: YES
  - Message: `docs: document GUI session_state keys`
  - Files: novel_generator/gui/utils/session_keys.py

- [x] 18. **GUI Module Tests**

  **What to do**:
  - Create `tests/gui/` directory: `tests/gui/__init__.py`, `tests/gui/test_tabs.py`
  - Write basic tests for tab imports, utils imports
  - Note: Streamlit GUI is hard to test, focus on module structure tests
  - Verify: `uv run pytest tests/gui/ -v` passes

  **Must NOT do**:
  - Do NOT try to test Streamlit rendering (too complex)
  - Do NOT over-test GUI logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Basic module tests
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 14, 15, 16, 17)
  - **Blocks**: Wave 5
  - **Blocked By**: Task 14, Task 15

  **References**:
  - `novel_generator/gui/tabs/*.py` - Modules to test for import
  - `novel_generator/gui/utils/*.py` - Utils to test

  **Acceptance Criteria**:
  - [ ] tests/gui/ directory exists
  - [ ] Basic import tests written
  - [ ] Tests pass

  **QA Scenarios**:
  ```
  Scenario: GUI tests pass
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/gui/ -v
    Expected Result: Tests pass
    Evidence: .sisyphus/evidence/task-18-gui-tests.log
  ```

  **Commit**: YES
  - Message: `test: add GUI module structure tests`
  - Files: tests/gui/__init__.py, tests/gui/test_tabs.py

---

## Final Verification Wave (MANDATORY)

- [ ] F1. **Plan Compliance Audit** — `oracle`
- [ ] F2. **Code Quality Review** — `unspecified-high`
- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if UI)
### Wave 5: Cleanup & Final Verification

- [x] 19. **__pycache__ Cleanup**

  **What to do**:
  - Run `git clean -fdX` to remove tracked __pycache__ directories (7 directories)
  - Update `.gitignore` to enforce __pycache__ exclusion
  - Verify: `git status` shows no __pycache__ directories

  **Must NOT do**:
  - Do NOT remove user data files
  - Do NOT remove .gitignore entries

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple cleanup
  - **Skills**: [`git-master`]
    - `git-master`: Safe git clean operation

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 20, 21, 22, 23)
  - **Blocks**: F1-F4
  - **Blocked By**: Wave 3, Wave 4

  **References**:
  - `.gitignore` - Should already have __pycache__ entry, verify
  - git clean command: `git clean -fdX` (remove ignored files)

  **Acceptance Criteria**:
  - [ ] __pycache__ directories removed
  - [ ] .gitignore updated if needed
  - [ ] `git status` clean

  **QA Scenarios**:
  ```
  Scenario: __pycache__ removed
    Tool: Bash
    Steps:
      1. Run: find . -type d -name "__pycache__" | wc -l
    Expected Result: Output is "0"
    Evidence: .sisyphus/evidence/task-19-pycache-clean.log
  ```

  **Commit**: YES
  - Message: `chore: clean __pycache__ directories`
  - Files: .gitignore (if updated)

- [x] 20. **Final CLI Verification**

  **What to do**:
  - Run all CLI commands: init, status, settings, outline, expand (if sample data available)
  - Verify outputs match baseline from Task 4
  - Document in evidence
  - Confirm no regression

  **Must NOT do**:
  - Do NOT modify code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification execution
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 19, 21, 22, 23)
  - **Blocks**: F3
  - **Blocked By**: Wave 3 (config merge), Wave 4 (GUI refactor)

  **References**:
  - `.sisyphus/evidence/baseline/task-4-cli-baseline.log` - Baseline from Task 4
  - CLI commands from README.md

  **Acceptance Criteria**:
  - [ ] CLI init works
  - [ ] CLI status works
  - [ ] CLI settings works
  - [ ] Outputs match baseline

  **QA Scenarios**:
  ```
  Scenario: CLI commands all work
    Tool: Bash
    Steps:
      1. Run: uv run python soundnovel.py cli init
      2. Run: uv run python soundnovel.py cli status
      3. Run: uv run python soundnovel.py cli settings --show-file
    Expected Result: All commands exit 0
    Evidence: .sisyphus/evidence/task-20-cli-final.log
  ```

  **Commit**: NO
  - Verification only

- [x] 21. **Final GUI Verification**

  **What to do**:
  - Launch GUI headless from root `gui_app.py`
  - Verify all 5 tabs render
  - Take screenshots of each tab
  - Compare with baseline from Task 4
  - Confirm no regression

  **Must NOT do**:
  - Do NOT modify code

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Comprehensive GUI verification
  - **Skills**: [`playwright`]
    - `playwright`: Browser automation for GUI screenshots

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 19, 20, 22, 23)
  - **Blocks**: F3
  - **Blocked By**: Wave 4 (GUI modularization)

  **References**:
  - `gui_app.py` (root) - GUI entry point, stays at root
  - `.sisyphus/evidence/baseline/task-4-gui-baseline.log` - Baseline from Task 4

  **Acceptance Criteria**:
  - [ ] GUI launches from `gui_app.py`
  - [ ] All 5 tabs visible
  - [ ] Screenshots captured
  - [ ] No regression

  **QA Scenarios**:
  ```
  Scenario: GUI all tabs visible from root
    Tool: Bash
    Steps:
      1. Start: uv run streamlit run gui_app.py --server.headless true &
      2. Wait: sleep 5
      3. Check: curl -s http://localhost:8501 | grep -E "(配置|生成|大纲|扩写|评审)"
    Expected Result: All tab names present in HTML
    Evidence: .sisyphus/evidence/task-21-gui-final.log
  ```

  **Commit**: NO
  - Verification only

- [x] 22. **Test Coverage Check**

  **What to do**:
  - Run pytest with coverage: `uv run pytest tests/ --cov=novel_generator --cov-report=term`
  - Verify coverage ≥30% (target for config modules)
  - Document coverage report in evidence

  **Must NOT do**:
  - Do NOT modify code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Coverage reporting
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 19, 20, 21, 23)
  - **Blocks**: F2
  - **Blocked By**: Wave 3, Wave 4

  **References**:
  - pytest-cov configuration from Task 1

  **Acceptance Criteria**:
  - [ ] Coverage report generated
  - [ ] Coverage ≥30%
  - [ ] Evidence captured

  **QA Scenarios**:
  ```
  Scenario: coverage meets target
    Tool: Bash
    Steps:
      1. Run: uv run pytest tests/ --cov=novel_generator --cov-report=term
      2. Parse: grep "TOTAL" coverage report
    Expected Result: Coverage percentage ≥30%
    Evidence: .sisyphus/evidence/task-22-coverage.log
  ```

  **Commit**: NO
  - Verification only

- [x] 23. **Lint/Typecheck Verification**

  **What to do**:
  - Run ruff: `uv run ruff check novel_generator/`
  - Run mypy: `uv run mypy novel_generator/`
  - Verify both pass (or baseline maintained)
  - Document in evidence

  **Must NOT do**:
  - Do NOT modify code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Lint verification
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5 (with Tasks 19, 20, 21, 22)
  - **Blocks**: F2
  - **Blocked By**: Wave 3, Wave 4

  **References**:
  - ruff/mypy config from Task 2

  **Acceptance Criteria**:
  - [ ] ruff passes
  - [ ] mypy passes (or baseline errors documented)
  - [ ] Evidence captured

  **QA Scenarios**:
  ```
  Scenario: ruff passes
    Tool: Bash
    Steps:
      1. Run: uv run ruff check novel_generator/
    Expected Result: Exit code 0, no violations
    Evidence: .sisyphus/evidence/task-23-ruff.log

  Scenario: mypy passes
    Tool: Bash
    Steps:
      1. Run: uv run mypy novel_generator/
    Expected Result: Exit code 0, or documented baseline errors
    Evidence: .sisyphus/evidence/task-23-mypy.log
  ```

  **Commit**: NO
  - Verification only

---

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  
  **What to do**:
  - Read the plan end-to-end
  - For each "Must Have": verify implementation exists (read file, curl endpoint, run command)
  - For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found
  - Check evidence files exist in .sisyphus/evidence/
  - Compare deliverables against plan

  **Output**: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F2, F3, F4)
  - **Blocks**: user okay
  - **Blocked By**: Wave 5

  **QA Scenarios**:
  ```
  Scenario: plan compliance verified
    Tool: oracle agent
    Steps:
      1. Oracle reads plan, checks each Must Have/Must NOT Have
    Expected Result: VERDICT: APPROVE
    Evidence: .sisyphus/evidence/F1-compliance.log
  ```

  **Commit**: NO

- [ ] F2. **Code Quality Review** — `unspecified-high`

  **What to do**:
  - Run `tsc --noEmit` (or mypy) + ruff + pytest
  - Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports
  - Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp)
  - Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F3, F4)
  - **Blocks**: user okay
  - **Blocked By**: Wave 5

  **QA Scenarios**:
  ```
  Scenario: code quality verified
    Tool: unspecified-high agent
    Steps:
      1. Run mypy, ruff, pytest
      2. Review changed files
    Expected Result: VERDICT: APPROVE
    Evidence: .sisyphus/evidence/F2-quality.log
  ```

  **Commit**: NO

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if UI)

  **What to do**:
  - Start from clean state
  - Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence
  - Test cross-task integration (features working together, not isolation)
  - Test edge cases: empty state, invalid input, rapid actions
  - Save to `.sisyphus/evidence/final-qa/`

  **Output**: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F2, F4)
  - **Blocks**: user okay
  - **Blocked By**: Wave 5

  **QA Scenarios**:
  ```
  Scenario: manual QA complete
    Tool: unspecified-high agent + playwright
    Steps:
      1. Execute all QA scenarios from tasks 1-23
      2. Test integration
      3. Test edge cases
    Expected Result: VERDICT: APPROVE
    Evidence: .sisyphus/evidence/F3-manual-qa/
  ```

  **Commit**: NO

- [ ] F4. **Scope Fidelity Check** — `deep`

  **What to do**:
  - For each task: read "What to do", read actual diff (git log/diff)
  - Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep)
  - Check "Must NOT do" compliance
  - Detect cross-task contamination: Task N touching Task M's files
  - Flag unaccounted changes

  **Output**: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Final Wave (with F1, F2, F3)
  - **Blocks**: user okay
  - **Blocked By**: Wave 5

  **QA Scenarios**:
  ```
  Scenario: scope fidelity verified
    Tool: deep agent
    Steps:
      1. Compare each task spec vs actual diff
      2. Check Must NOT do compliance
      3. Detect contamination
    Expected Result: VERDICT: APPROVE
    Evidence: .sisyphus/evidence/F4-fidelity.log
  ```

  **Commit**: NO

---

## Commit Strategy

Atomic commits per logical change, verified independently:

1. `test: add pytest infrastructure` — pyproject.toml, tests/__init__.py, tests/conftest.py
2. `chore: add ruff and mypy configuration` — pyproject.toml
3. `test: add config class tests (TDD baseline)` — tests/config/*
4. `refactor: consolidate AIRoleConfig to config/ai_roles.py` — settings.py, session.py, ai_roles.py
5. `chore: remove zhipuai dependency` — pyproject.toml, uv.lock
6. `docs: remove zhipu/glm references` — README.md, docs/AGENTS.md
7. `chore: remove zhipu references from code` — multi_model_client.py
8. `test: add ConfigManager roundtrip tests` — tests/config/test_config_manager.py
9. `refactor: implement unified ConfigManager` — config/config_manager.py
10. `feat: add config migration script` — scripts/migrate_config.py
11. `refactor: update imports to use ConfigManager` — CLI, GUI, core modules
12. `refactor: extract GUI tabs to gui/tabs/` — gui/tabs/*
13. `refactor: extract GUI utils` — gui/utils/*
14. `docs: document GUI session_state keys` — gui/utils/session_keys.py
15. `refactor: modularize GUI into thin coordinator` — gui/app.py
16. `test: add GUI module structure tests` — tests/gui/*
17. `chore: clean __pycache__ directories` — .gitignore (if updated)

Each commit: pre-commit test run, independent revert capability.

---

## Success Criteria

### Verification Commands
```bash
# CLI verification
uv run python soundnovel.py cli init && echo "PASS: init works"
uv run python soundnovel.py cli status && echo "PASS: status works"
uv run python soundnovel.py cli settings --show-file && echo "PASS: settings works"

# GUI verification (from root gui_app.py)
uv run streamlit run gui_app.py --server.headless true &
sleep 5
curl -s http://localhost:8501 | grep "小说创作助手" && echo "PASS: GUI launches"

# Test verification
uv run pytest tests/ -v && echo "PASS: tests pass"
uv run pytest tests/ --cov=novel_generator --cov-report=term && echo "PASS: coverage report"

# Lint verification
uv run ruff check novel_generator/ && echo "PASS: ruff passes"
uv run mypy novel_generator/ && echo "PASS: mypy passes"

# Zhipu AI removal verification
grep -ri "zhipu\|glm\|智谱" novel_generator/ docs/ README.md --include="*.py" --include="*.md" && echo "FAIL: zhipu references found" || echo "PASS: zhipu removed"
grep "zhipuai" pyproject.toml && echo "FAIL: zhipuai dependency found" || echo "PASS: zhipuai removed"

# Config dedup verification
grep -r "class AIRoleConfig" novel_generator/ --include="*.py" | wc -l | grep "^1$" && echo "PASS: single AIRoleConfig definition"
grep -r "class RoleConfig" novel_generator/ --include="*.py" | wc -l | grep "^0$" && echo "PASS: RoleConfig renamed to AIRoleConfig"

# GUI modularization verification (gui_app.py at root)
wc -l gui_app.py | awk '{if ($1 < 200) print "PASS: GUI thin coordinator"}'
test -f gui_app.py && echo "PASS: gui_app.py at root"

# __pycache__ verification
find . -type d -name "__pycache__" | wc -l | grep "^0$" && echo "PASS: __pycache__ cleaned"
```

### Final Checklist
- [ ] All "Must Have" present (ConfigManager, pytest, tests, GUI tabs, __pycache__ cleaned, zhipu removed)
- [ ] All "Must NOT Have" absent (business logic unchanged, no new features, no breaking API changes)
- [ ] All tests pass
- [ ] CLI commands work
- [ ] GUI tabs work
- [ ] Coverage ≥30%
- [ ] ruff/mypy pass
- [ ] Zhipu AI removed (code, docs, dependency)
- [ ] Single AIRoleConfig
- [ ] GUI line count <200
- [ ] User explicit okay received