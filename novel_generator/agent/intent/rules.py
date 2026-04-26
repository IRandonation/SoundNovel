"""意图解析规则定义"""

import re
from typing import List, Tuple, Dict, Any

# 规则定义: (正则模式, 意图字典)
RULES: List[Tuple[str, Dict[str, Any]]] = [
    # 生成章节
    (r"^[生|写|创|扩]写?第?(\d+)章$", {"action": "generate", "target_type": "chapter"}),
    (r"^生成第?(\d+)章$", {"action": "generate", "target_type": "chapter"}),
    (r"^写第?(\d+)章$", {"action": "generate", "target_type": "chapter"}),
    (r"^扩写第?(\d+)章$", {"action": "expand", "target_type": "chapter"}),

    # 修改章节
    (r"^修改第?(\d+)章$", {"action": "modify", "target_type": "chapter"}),
    (r"^调整第?(\d+)章$", {"action": "modify", "target_type": "chapter"}),

    # 查询人物
    (r"^(.+?)[现|目]在[在|怎|状|情|何].*$", {"action": "query_character", "target_type": "character"}),
    (r"^查询(.+?)[的|状|信].*$", {"action": "query_character", "target_type": "character"}),
    (r"^(.+?)是谁$", {"action": "query_character", "target_type": "character"}),

    # 查询伏笔
    (r"^.*伏笔.*$", {"action": "query_foreshadowing", "target_type": "foreshadowing"}),
    (r"^埋了哪些伏笔.*$", {"action": "query_foreshadowing", "target_type": "foreshadowing"}),

    # 查询情感弧线
    (r"^.*情感.*$", {"action": "query_emotion", "target_type": "emotion"}),
    (r"^.*情绪.*$", {"action": "query_emotion", "target_type": "emotion"}),

    # 查看状态/进度
    (r"^状态$", {"action": "status", "target_type": "project"}),
    (r"^查看状态$", {"action": "status", "target_type": "project"}),
    (r"^进度$", {"action": "status", "target_type": "project"}),
    (r"^查看进度$", {"action": "status", "target_type": "project"}),
    (r"^项目状态$", {"action": "status", "target_type": "project"}),

    # 规划
    (r"^规划.*$", {"action": "plan", "target_type": "outline"}),
    (r"^大纲.*$", {"action": "plan", "target_type": "outline"}),

    # 帮助
    (r"^帮助$", {"action": "help", "target_type": "system"}),
    (r"^help$", {"action": "help", "target_type": "system"}),
    (r"^\\?$", {"action": "help", "target_type": "system"}),
    (r"^怎么用$", {"action": "help", "target_type": "system"}),

    # 退出
    (r"^退出$", {"action": "exit", "target_type": "system"}),
    (r"^exit$", {"action": "exit", "target_type": "system"}),
    (r"^quit$", {"action": "exit", "target_type": "system"}),
    (r"^再见$", {"action": "exit", "target_type": "system"}),
    (r"^拜拜$", {"action": "exit", "target_type": "system"}),
]


def compile_rules() -> List[Tuple[re.Pattern, Dict[str, Any]]]:
    """编译所有规则为正则表达式对象"""
    compiled = []
    for pattern, intent in RULES:
        try:
            compiled.append((re.compile(pattern, re.IGNORECASE), intent))
        except re.error:
            continue
    return compiled
