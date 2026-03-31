# ConfigManager 统一设计（Tasks 9-13）

## 目标

将 `Settings`、`GenerationConfigManager`、`SessionManager` 的配置读取入口统一为 `ConfigManager`，同时保持：

- 角色配置真相源：`05_script/generation_config.json`
- API Key 与运行态真相源：`05_script/session.json`
- CLI/GUI 现有业务逻辑与调用行为不变（通过兼容方法/属性过渡）

## 单一真相源约定

1. **roles（generator/reviewer/refiner）**：
   - 读取优先：`generation_config.json.roles`
   - 回填兜底：若缺失则使用默认角色配置
2. **API 配置 / provider / 运行进度 / 会话历史**：
   - 读取与保存：`session.json`
3. **generation 参数（batch/context/word_count/max_refine/pass_score）**：
   - 主读取：`generation_config.json.generation`
   - 兼容兜底：`session.json.generation_config`

## ConfigManager 责任边界

`novel_generator/config/config_manager.py` 提供统一类 `ConfigManager`：

### 核心方法

- `load() -> dict`
  - 加载并合并两份配置为内存态 unified config。
- `save() -> bool`
  - 将内存态拆分写回两份文件：
    - `generation_config.json`：roles / generation / providers / quality_check
    - `session.json`：api_config / generation_state / sessions / generation_config(兼容)
- `get_role_config(role_name) -> dict`
  - 返回 role 配置（兼容 `GenerationConfigManager.get_role_config`）。
- `get_api_key(provider) -> str`
  - provider in {`doubao`,`deepseek`}，返回对应 key。

### 向后兼容属性/方法

为最小改动迁移，提供与旧类同语义入口：

- `get_api_config()`（兼容 `SessionManager.get_api_config` 结果结构）
- `get_generation_config()`（兼容 `GenerationConfigManager`）
- `get_all_roles_config()`
- `set_role_config()` / `set_generation_config()`
- `set_api_config()`
- `state` 属性（映射 session state dataclass）
- `config` 属性（映射 generation config dict）

## 数据结构策略

内部维护两份缓存：

- `_generation_data: Dict[str, Any]`
- `_session_state: SessionState`

并提供统一视图 `_unified: Dict[str, Any]` 用于一次性读取与测试 roundtrip。

合并规则：

1. 先按默认模板生成两份基础结构；
2. 加载文件并 merge；
3. 将 `generation.roles` 同步为角色主视图；
4. 生成兼容 API 结构（含 `paths`、`novel_generation`、`system.api`）。

## 迁移脚本设计

新增 `scripts/migrate_config.py`：

- 输入：`--session`、`--generation`、`--project-root`、`--dry-run`
- 行为：
  1. 读取两份旧配置；
  2. 合并为 `ConfigManager` 可直接加载的标准结构；
  3. 冲突处理：若 roles 同时存在，以 `generation_config.json.roles` 为准；
  4. 输出预览（dry-run）或写回目标文件。
- 安全：默认不覆盖原文件，需显式 `--write` 才执行落盘。

## 导入替换策略

优先更新直接用旧管理器的命令模块：

- `cli/commands/outline.py`
- `cli/commands/expand.py`
- `cli/commands/continue_cmd.py`
- `cli/commands/review_cmd.py`
- `utils/common.py`

替换原则：

- 新代码优先 `from novel_generator.config.config_manager import ConfigManager`
- 保留旧模块类定义（不删除），作为兼容壳或可继续被测试调用。

## 测试设计

新增 `tests/config/test_config_manager.py`：

1. `test_load_creates_defaults_when_missing`
2. `test_get_role_config_prefers_generation_roles`
3. `test_get_api_key_from_session`
4. `test_roundtrip_load_save_load`
5. `test_missing_fields_merge_defaults`
6. `test_backward_compatible_get_api_config_shape`

## 风险与缓解

1. **旧 CLI 依赖 session.state 结构**
   - 缓解：`ConfigManager.state` 返回 `SessionState` 对象。
2. **不同文件字段命名差异**
   - 缓解：集中在 `ConfigManager` 内统一 mapping。
3. **迁移误覆盖用户配置**
   - 缓解：迁移脚本默认 dry-run，显式写入开关。

## 验证标准

- `tests/config/test_config_manager.py` 全通过
- 旧 tests (`test_settings/test_generation_config/test_session`) 不回归
- CLI 相关模块导入与基础调用不报错
