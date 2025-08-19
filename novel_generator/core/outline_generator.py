"""
大纲生成器
负责基于原始素材生成章节大纲
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from novel_generator.config.settings import Settings
from novel_generator.utils.api_client import ZhipuAIClient


class OutlineGenerator:
    """大纲生成器类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化大纲生成器
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.settings = Settings(config)
        self.logger = logging.getLogger(__name__)
        # 初始化AI API客户端
        self.api_client = ZhipuAIClient(config)
        
    def generate_outline(self, core_setting: Dict[str, Any], 
                        overall_outline: Dict[str, Any],
                        chapter_range: tuple = (1, 10)) -> Dict[str, Any]:
        """
        生成章节大纲
        
        Args:
            core_setting: 核心设定
            overall_outline: 整体大纲
            chapter_range: 章节范围
            
        Returns:
            Dict[str, Any]: 生成的章节大纲
        """
        try:
            self.logger.info(f"开始生成章节大纲，范围: {chapter_range}")
            
            # 构建提示词
            prompt = self._build_outline_prompt(core_setting, overall_outline, chapter_range)
            
            # 调用AI API
            response = self._call_ai_api(prompt)
            
            # 解析响应
            outline = self._parse_response(response)
            
            # 验证大纲
            self._validate_outline(outline)
            
            self.logger.info(f"章节大纲生成成功，共{len(outline)}章")
            return outline
            
        except Exception as e:
            self.logger.error(f"生成章节大纲失败: {e}")
            raise
    
    def _build_outline_prompt(self, core_setting: Dict[str, Any],
                            overall_outline: Dict[str, Any],
                            chapter_range: tuple) -> str:
        """构建大纲生成提示词"""
        
        prompt = f"""
请根据以下信息生成详细的章节大纲：

【核心设定】
世界观：{core_setting.get('世界观', '')}
核心冲突：{core_setting.get('核心冲突', '')}
主要人物：{self._format_characters(core_setting.get('人物小传', {}))}

【整体大纲】
# 动态构建所有幕的内容
{self._build_acts_text(overall_outline)}


关键转折点：{overall_outline.get('关键转折点', '')}

【生成要求】
请生成第{chapter_range[0]}-{chapter_range[1]}章的详细大纲，每章包含：
- 标题：简洁明了，体现本章核心内容
- 核心事件：本章必须发生的关键情节
- 场景：地点+环境描述
- 人物行动：主角/配角的核心动作
- 伏笔回收：本章需呼应的伏笔（如无则写"无"）
- 字数目标：1500字左右

【格式要求】
请严格按照YAML格式输出，每章一个条目，键名为"第X章"。
"""
        return prompt.strip()
    
    def _format_characters(self, characters: Dict[str, Any]) -> str:
        """格式化人物信息"""
        result = []
        for name, info in characters.items():
            if isinstance(info, dict):
                info_str = ", ".join([f"{k}: {v}" for k, v in info.items()])
                result.append(f"{name}({info_str})")
            else:
                result.append(f"{name}: {info}")
        return "; ".join(result)
    
    def _build_acts_text(self, overall_outline: Dict[str, Any]) -> str:
        """动态构建所有幕的内容文本"""
        acts_content = []
        act_number = 1
        
        # 中文数字映射
        chinese_numbers = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
        
        while True:
            # 尝试数字格式（第1幕、第2幕等）
            act_key_numeric = f"第{act_number}幕"
            act_content = overall_outline.get(act_key_numeric, '')
            
            # 如果数字格式没有找到，尝试中文格式（第一幕、第二幕等）
            if not act_content and act_number <= len(chinese_numbers):
                act_key_chinese = f"第{chinese_numbers[act_number-1]}幕"
                act_content = overall_outline.get(act_key_chinese, '')
            
            if act_content:
                # 使用找到的键名作为显示名称
                display_key = act_key_numeric if overall_outline.get(act_key_numeric) else act_key_chinese
                acts_content.append(f"{display_key}：{act_content}")
                act_number += 1
            else:
                break
        
        return '\n'.join(acts_content)
    
    def extract_total_chapters(self, overall_outline: Dict[str, Any]) -> int:
        """
        从整体大纲中提取总章节数量
        
        Args:
            overall_outline: 整体大纲
            
        Returns:
            int: 总章节数量
        """
        try:
            total_chapters = 0
            act_number = 1
            
            # 中文数字映射
            chinese_numbers = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
                              "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十"]
            
            while True:
                # 尝试数字格式（第1幕、第2幕等）
                act_key_numeric = f"第{act_number}幕"
                act_content = overall_outline.get(act_key_numeric, '')
                
                # 如果数字格式没有找到，尝试中文格式（第一幕、第二幕等）
                if not act_content and act_number <= len(chinese_numbers):
                    act_key_chinese = f"第{chinese_numbers[act_number-1]}幕"
                    act_content = overall_outline.get(act_key_chinese, '')
                
                if act_content:
                    # 从幕的内容中提取章节数量
                    # 支持多种格式："第1-15章"、"第 1-15 章"、"第1章到第15章"等
                    import re
                    
                    # 尝试匹配章节数量
                    chapter_patterns = [
                        r'第\s*(\d+)\s*-\s*(\d+)\s*章',  # 第1-15章
                        r'第\s*(\d+)\s*章\s*到\s*第\s*(\d+)\s*章',  # 第1章到第15章
                        r'(\d+)\s*-\s*(\d+)\s*章',  # 1-15章
                        r'第\s*(\d+)\s*章',  # 第1章（单章）
                    ]
                    
                    max_chapter_in_act = 0
                    for pattern in chapter_patterns:
                        matches = re.findall(pattern, act_content)
                        for match in matches:
                            if len(match) == 2:  # 范围格式
                                start_chapter = int(match[0])
                                end_chapter = int(match[1])
                                max_chapter_in_act = max(max_chapter_in_act, end_chapter)
                            else:  # 单章格式
                                chapter_num = int(match[0])
                                max_chapter_in_act = max(max_chapter_in_act, chapter_num)
                    
                    if max_chapter_in_act > 0:
                        total_chapters = max(total_chapters, max_chapter_in_act)
                    
                    act_number += 1
                else:
                    break
            
            # 如果没有找到章节数量，返回默认值
            if total_chapters == 0:
                self.logger.warning("无法从整体大纲中提取章节数量，使用默认值150")
                return 150
            
            self.logger.info(f"从整体大纲中提取到总章节数量: {total_chapters}")
            return total_chapters
            
        except Exception as e:
            self.logger.error(f"提取章节数量失败: {e}")
            return 150  # 返回默认值
    
    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API生成大纲"""
        try:
            self.logger.info("正在调用AI API生成章节大纲...")
            
            # 使用API客户端调用AI
            response = self.api_client.generate_outline(prompt)
            
            if not response:
                self.logger.warning("AI API返回空响应，使用模拟数据")
                return self._get_mock_response()
            
            self.logger.info("AI API调用成功")
            return response
            
        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            self.logger.info("使用模拟数据作为备用方案")
            return self._get_mock_response()
    
    def _get_mock_response(self) -> str:
        """获取模拟响应（用于测试）"""
        return """
第1章:
  标题: "开篇"
  核心事件: "主角登场，介绍背景和世界观"
  场景: "主角所在地点，如山村、书院等"
  人物行动: "主角的日常活动，展现性格特点"
  伏笔回收: ""
  字数目标: 1500

第2章:
  标题: "变故"
  核心事件: "发生重要事件，改变主角生活轨迹"
  场景: "事件发生地点，如家中、野外等"
  人物行动: "主角应对变故的行动"
  伏笔回收: ""
  字数目标: 1500
"""
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 清理响应内容，移除可能的markdown代码块标记
            cleaned_response = self._clean_markdown_response(response)
            
            # 尝试解析YAML
            outline = yaml.safe_load(cleaned_response)
            
            # 如果解析结果是字符串，尝试进一步解析
            if isinstance(outline, str):
                self.logger.warning("YAML解析返回字符串，尝试简单文本解析")
                return self._simple_parse(cleaned_response)
            
            return outline
        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            # 尝试简单的文本解析
            return self._simple_parse(cleaned_response)
    
    def _clean_markdown_response(self, response: str) -> str:
        """清理Markdown格式的响应"""
        # 移除markdown代码块标记
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 跳过代码块开始和结束标记
            if line.strip() in ['```yaml', '```', '```yml']:
                continue
            # 跳过空行（如果它们在代码块标记附近）
            elif line.strip() == '' and cleaned_lines and cleaned_lines[-1].strip() == '':
                continue
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _simple_parse(self, response: str) -> Dict[str, Any]:
        """简单的文本解析"""
        outline = {}
        lines = response.strip().split('\n')
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('第') and '章：' in line:
                current_chapter = line.split('：')[0]
                outline[current_chapter] = {}
            elif line.startswith('- ') and current_chapter:
                # 处理以 "- " 开头的行
                content = line[2:]  # 移除 "- "
                if '：' in content:
                    key, value = content.split('：', 1)
                    outline[current_chapter][key.strip()] = value.strip()
                elif ':' in content:
                    key, value = content.split(':', 1)
                    outline[current_chapter][key.strip()] = value.strip()
        
        return outline
    
    def _validate_outline(self, outline: Dict[str, Any]):
        """验证大纲格式"""
        required_fields = ['标题', '核心事件', '场景', '人物行动', '伏笔回收', '字数目标']
        
        for chapter, content in outline.items():
            if not isinstance(content, dict):
                raise ValueError(f"章节 {chapter} 内容格式错误")
            
            for field in required_fields:
                # 检查字段是否存在
                if field not in content:
                    # 检查字段变体
                    if field == '字数目标':
                        # 检查可能的变体
                        if '字数目标' in content:
                            content['字数目标'] = content.pop('字数目标')
                        elif '目标字数' in content:
                            content['字数目标'] = content.pop('目标字数')
                        elif '字数' in content:
                            content['字数目标'] = content.pop('字数')
                        else:
                            # 如果没有找到任何变体，设置默认值
                            content['字数目标'] = "1500字左右"
                    elif field == '伏笔回收':
                        # 伏笔回收可以是可选的，如果没有则设置为"无"
                        if '伏笔回收' not in content:
                            content['伏笔回收'] = "无"
                    else:
                        # 检查是否有相似的字段
                        similar_fields = [k for k in content.keys() if field in k or k in field]
                        if similar_fields:
                            # 使用相似字段
                            content[field] = content.pop(similar_fields[0])
                        else:
                            # 如果没有找到相似字段，设置默认值
                            if field == '标题':
                                content['标题'] = "未命名章节"
                            elif field == '核心事件':
                                content['核心事件'] = "待定"
                            elif field == '场景':
                                content['场景'] = "待定"
                            elif field == '人物行动':
                                content['人物行动'] = "待定"
    
    def save_outline(self, outline: Dict[str, Any], 
                    output_path: str, 
                    backup: bool = True) -> str:
        """
        保存大纲文件
        
        Args:
            outline: 大纲内容
            output_path: 输出路径
            backup: 是否备份
            
        Returns:
            str: 实际保存路径
        """
        try:
            output_file = Path(output_path)
            
            # 备份现有文件
            if backup and output_file.exists():
                backup_path = self._backup_file(output_file)
                self.logger.info(f"备份现有大纲文件: {backup_path}")
            
            # 保存新文件
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(outline, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"大纲文件保存成功: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"保存大纲文件失败: {e}")
            raise
    
    def _backup_file(self, file_path: Path) -> str:
        """备份文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = file_path.parent / "outline_history" / backup_name
        
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return str(backup_path)
    
    def load_outline(self, file_path: str) -> Dict[str, Any]:
        """
        加载大纲文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict[str, Any]: 大纲内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                outline = yaml.safe_load(f)
            
            self.logger.info(f"大纲文件加载成功: {file_path}")
            return outline
            
        except Exception as e:
            self.logger.error(f"加载大纲文件失败: {e}")
            raise
    
    def optimize_outline(self, outline: Dict[str, Any], 
                        core_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化大纲
        
        Args:
            outline: 原始大纲
            core_setting: 核心设定
            
        Returns:
            Dict[str, Any]: 优化后的大纲
        """
        try:
            self.logger.info("开始优化大纲...")
            
            # 检查人物一致性
            outline = self._check_character_consistency(outline, core_setting)
            
            # 检查伏笔连贯性
            outline = self._check_foreshadowing_consistency(outline)
            
            # 检查节奏合理性
            outline = self._check_pacing(outline)
            
            self.logger.info("大纲优化完成")
            return outline
            
        except Exception as e:
            self.logger.error(f"大纲优化失败: {e}")
            return outline
    
    def _check_character_consistency(self, outline: Dict[str, Any], 
                                   core_setting: Dict[str, Any]) -> Dict[str, Any]:
        """检查人物一致性"""
        characters = core_setting.get('人物小传', {})
        
        for chapter, content in outline.items():
            # 这里可以添加人物一致性检查逻辑
            pass
        
        return outline
    
    def _check_foreshadowing_consistency(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """检查伏笔连贯性"""
        # 收集所有伏笔回收
        foreshadowing = []
        
        for chapter, content in outline.items():
            foreshadowing.extend(content.get('伏笔回收', '').split(', '))
        
        # 检查伏笔是否合理
        # 这里可以添加具体的检查逻辑
        
        return outline
    
    def _check_pacing(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """检查节奏合理性"""
        # 检查章节节奏
        # 这里可以添加节奏检查逻辑
        
        return outline