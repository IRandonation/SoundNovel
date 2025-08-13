"""
小说生成系统
实现4个阶段的文本处理流程：
1. 长文本API模型 → 整篇剧情摘要和伏笔 (>150字)
2. 基于剧情摘要和伏笔构建章节大纲 (100字/章)
3. 每章大纲 → 1k扩写
4. 1k → 2k扩写
"""

import os
import yaml
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/novel_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NovelGenerator:
    """小说生成器主类"""
    
    def __init__(self, config_file: str = "config.json", prompts_file: str = "prompts.yaml"):
        """
        初始化小说生成器
        
        Args:
            config_file: 配置文件路径
            prompts_file: prompts文件路径
        """
        self.config = self._load_config(config_file)
        self.prompts = self._load_prompts(prompts_file)
        self.api_client = self._init_api_client()
        
        # 创建必要的目录
        os.makedirs("output", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        os.makedirs("failed", exist_ok=True)
        
        # 初始化人物名称映射表
        self.character_mapping = {}  # 原名 -> 新名
        self.reverse_mapping = {}    # 新名 -> 原名
        self.mapped_characters = set()  # 已处理的人物集合
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件 {config_file} 不存在，使用默认配置")
            return {
                "api_key": "",
                "api_base_url": "",
                "model": "glm-4.5-air",
                "max_tokens": 2000,
                "temperature": 0.7
            }
    
    def _load_prompts(self, prompts_file: str) -> Dict[str, Any]:
        """加载prompts配置文件"""
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Prompts文件 {prompts_file} 不存在")
            raise
    
    def _init_api_client(self):
        """初始化API客户端"""
        try:
            # 尝试使用不同的API客户端库
            api_key = self.config.get("api_key", "")
            api_base_url = self.config.get("api_base_url", "")
            
            if not api_key:
                logger.error("API密钥未配置")
                raise ValueError("API密钥未配置")
            
            # 方法1: 尝试使用 openai 库
            try:
                import openai
                client = openai.OpenAI(
                    api_key=api_key,
                    base_url=api_base_url
                )
                logger.info("使用 OpenAI 客户端")
                return client
            except ImportError:
                pass
            
            # 方法2: 尝试使用 zai-sdk
            try:
                from zai import AsyncClient
                client = AsyncClient(
                    api_key=api_key,
                    base_url=api_base_url
                )
                logger.info("使用 ZAI 客户端")
                return client
            except ImportError:
                pass
            
            # 方法3: 尝试使用 httpx 直接请求
            try:
                import httpx
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                client = httpx.Client(base_url=api_base_url, headers=headers)
                logger.info("使用 HTTPX 客户端")
                return client
            except ImportError:
                pass
            
            logger.error("无法找到可用的HTTP客户端库，请安装 openai、zai-sdk 或 httpx")
            raise ImportError("无法找到可用的HTTP客户端库")
            
        except Exception as e:
            logger.error(f"初始化API客户端失败: {e}")
            raise
    
    def _get_model_for_stage(self, stage_name: str) -> str:
        """根据阶段获取对应的模型"""
        models = self.config.get("models", {})
        
        # 根据阶段类型选择模型
        if stage_name in ["stage1_summary"]:
            return models.get("summary_model", "glm-4-long")
        elif stage_name in ["stage2_chapter_outline"]:
            return models.get("outline_model", models.get("summary_model", "glm-4-long"))
        elif stage_name in ["stage3_chapter_expansion", "stage4_final_expansion"]:
            return models.get("expansion_model", "glm-4.5-air")
        else:
            # 默认模型
            return models.get("default_model", "glm-4.5-air")
    
    def _format_prompt(self, stage_name: str, **kwargs) -> str:
        """格式化prompt"""
        if stage_name not in self.prompts:
            raise ValueError(f"未找到阶段 {stage_name} 的配置")
        
        prompt_template = self.prompts[stage_name]["prompt_template"]
        
        # 如果启用了版权规避，添加相关信息
        if self.config.get("copyright_bypass", False) and "copyright_bypass_info" in prompt_template:
            copyright_info = self._generate_copyright_bypass_info()
            kwargs["copyright_bypass_info"] = copyright_info
        
        # 如果启用了版权规避，添加人物替换指导
        if self.config.get("copyright_bypass", False) and "character_replacement_guidance" in prompt_template:
            character_guidance = self._get_character_replacement_guidance()
            kwargs["character_replacement_guidance"] = character_guidance
        
        return prompt_template.format(**kwargs)
    
    def _generate_copyright_bypass_info(self) -> str:
        """生成版权规避信息"""
        copyright_config = self.prompts.get("copyright_bypass", {})
        world_options = copyright_config.get("world_options", ["现代都市背景"])
        world_descriptions = copyright_config.get("world_descriptions", {})
        
        # 从配置文件中读取用户选择的世界观风格
        selected_world = self.config.get("world_style", world_options[0])  # 默认选择第一个选项
        
        # 验证选择的世界观是否在可用选项中
        if selected_world not in world_options:
            logger.warning(f"选择的世界观风格 '{selected_world}' 不在可用选项中，使用默认选项")
            selected_world = world_options[0]
        
        # 获取世界观的具体描述
        world_description = ""
        # 根据选择的世界观获取对应的描述
        if selected_world == "玄幻修真世界" and "fantasy_cultivation" in world_descriptions:
            world_description = world_descriptions ["fantasy_cultivation"]
        elif selected_world == "都市异能世界" and "urban_superpower" in world_descriptions:
            world_description = world_descriptions ["urban_superpower"]
        elif selected_world == "末世求生世界" and "apocalyptic_survival" in world_descriptions:
            world_description = world_descriptions ["apocalyptic_survival"]
        elif selected_world == "系统流穿书世界" and "system_transmigration" in world_descriptions:
            world_description = world_descriptions ["system_transmigration"]
        elif selected_world == "星际修仙世界" and "interstellar_cultivation" in world_descriptions:
            world_description = world_descriptions ["interstellar_cultivation"]
        elif selected_world == "武侠江湖世界" and "martial_arts_world" in world_descriptions:
            world_description = world_descriptions ["martial_arts_world"]
        elif selected_world == "无限流副本世界" and "infinite_dungeon" in world_descriptions:
            world_description = world_descriptions ["infinite_dungeon"]
        elif selected_world == "田园休闲世界" and "pastoral_leisure" in world_descriptions:
            world_description = world_descriptions ["pastoral_leisure"]
        elif selected_world == "仙侠神话世界" and "xianxia_myth" in world_descriptions:
            world_description = world_descriptions ["xianxia_myth"]
        elif selected_world == "奇幻魔法世界" and "fantasy_magic" in world_descriptions:
            world_description = world_descriptions ["fantasy_magic"]

        
        return f"""
    注意：请将故事背景改写为"{selected_world}"设定，保持原有的情节逻辑和人物关系，但使用新的背景设定和人物名称。
    
    世界观详细描述：
    {world_description}
    
    要求：
    1. 将古代背景元素转换为{selected_world}的对应元素
    2. 为所有主要人物创建新的名称和身份，保持人物性格特征不变
    3. 调整环境描写、服饰、道具等细节以适应新的背景
    4. 确保改写后的内容自然流畅，逻辑一致
    """
    
    def _get_character_replacement_guidance(self) -> str:
        """获取人物替换指导"""
        copyright_config = self.prompts.get("copyright_bypass", {})
        examples = copyright_config.get("name_mapping_examples", "")
        
        if examples:
            return f"""
    人物名称替换指导：请参考以下示例进行人物名称和身份的替换：
    {examples}
    注意：保持人物的性格特征、关系和核心行为不变，只改变名称和外在身份。
    """
        else:
            return "请在叙述中使用新的人物名称和身份设定，避免使用原文中的人物名称。"
    
    def _save_output(self, stage_name: str, content: str, filename: str = None):
        """保存输出结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{stage_name}_{timestamp}.txt"
        
        output_path = os.path.join("output", filename)
        
        # 使用标准化输出格式
        try:
            output_format = self.prompts["output_format"]["format"]
            stage_config = self.prompts.get(stage_name, {})
            stage_name_display = stage_config.get("name", stage_name)
            
            formatted_output = output_format.format(
                stage_name=stage_name_display,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                content=content
            )
        except KeyError as e:
            logger.error(f"输出格式配置错误，缺少键: {e}")
            # 使用简单的格式作为备选
            formatted_output = f"【{stage_name}】\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}\n\n------------------------"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            logger.info(f"输出已保存到: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"保存输出失败: {e}")
            raise
    
    def _call_api(self, prompt: str, stage_name: str = None) -> str:
        """调用API生成内容"""
        try:
            # 根据阶段获取对应的模型
            model = self._get_model_for_stage(stage_name) if stage_name else self.config.get("model", "gpt-3.5-turbo")
            logger.info(f"调用API - 模型: {model}, 阶段: {stage_name}")
            
            # 检查客户端类型并调用相应的方法
            if hasattr(self.api_client, 'chat'):
                # OpenAI 客户端
                logger.info("使用OpenAI客户端调用API")
                response = self.api_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.config.get("max_tokens", 2000),
                    temperature=self.config.get("temperature", 0.7)
                )
                content = response.choices[0].message.content
                logger.info(f"OpenAI API调用成功，响应长度: {len(content)}")
                return content
            elif hasattr(self.api_client, 'chat completions'):
                # ZAI 客户端
                logger.info("使用ZAI客户端调用API")
                response = self.api_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.config.get("max_tokens", 2000),
                    temperature=self.config.get("temperature", 0.7)
                )
                content = response.choices[0].message.content
                logger.info(f"ZAI API调用成功，响应长度: {len(content)}")
                return content
            elif hasattr(self.api_client, 'post'):
                # HTTPX 客户端
                logger.info("使用HTTPX客户端调用API")
                import json
                response = self.api_client.post(
                    "/chat/completions",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": self.config.get("max_tokens", 2000),
                        "temperature": self.config.get("temperature", 0.7)
                    }
                )
                response_data = response.json()
                content = response_data["choices"][0]["message"]["content"]
                logger.info(f"HTTPX API调用成功，响应长度: {len(content)}")
                return content
            else:
                raise ValueError("不支持的API客户端类型")
                
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            logger.error(f"调用参数 - 模型: {model}, 阶段: {stage_name}")
            raise
    
    def stage1_generate_summary(self, input_text: str) -> Dict[str, str]:
        """
        阶段1: 长文本API模型 → 整篇剧情摘要和伏笔 (>150字)
        
        Args:
            input_text: 输入的长文本
            
        Returns:
            包含剧情摘要和伏笔分析的字典
        """
        logger.info("开始阶段1: 生成剧情摘要和伏笔")
        
        prompt = self._format_prompt(
            "stage1_summary",
            input_text=input_text
        )
        
        response = self._call_api(prompt, "stage1_summary")
        
        # 记录API响应内容（前500字符）
        logger.info(f"API响应内容（前500字符）: {response[:500]}...")
        
        # 解析响应，提取剧情摘要和伏笔分析
        summary_start = response.find("【剧情摘要】")
        foreshadowing_start = response.find("【伏笔分析】")
        
        logger.info(f"解析结果 - 剧情摘要位置: {summary_start}, 伏笔分析位置: {foreshadowing_start}")
        
        if summary_start == -1 or foreshadowing_start == -1:
            logger.error(f"API响应格式不正确。响应内容: {response}")
            # 尝试其他可能的格式
            if "剧情摘要" in response and "伏笔分析" in response:
                logger.info("尝试使用无括号的格式...")
                summary_start = response.find("剧情摘要")
                foreshadowing_start = response.find("伏笔分析")
                if summary_start != -1 and foreshadowing_start != -1:
                    summary = response[summary_start + 4:foreshadowing_start].strip()
                    foreshadowing = response[foreshadowing_start + 4:].strip()
                else:
                    raise ValueError("API响应格式不正确，无法找到剧情摘要和伏笔分析标记")
            else:
                raise ValueError("API响应格式不正确，无法找到剧情摘要和伏笔分析标记")
        else:
            summary = response[summary_start + 6:foreshadowing_start].strip()
            foreshadowing = response[foreshadowing_start + 6:].strip()
        
        logger.info(f"解析成功 - 剧情摘要长度: {len(summary)}, 伏笔分析长度: {len(foreshadowing)}")
        
        # 保存结果
        self._save_output("stage1", response, "stage1_summary.txt")
        
        return {
            "summary": summary,
            "foreshadowing": foreshadowing
        }
    
    def stage2_generate_chapter_outlines(self, summary: str, foreshadowing: str) -> List[str]:
        """
        阶段2: 基于剧情摘要和伏笔构建章节大纲 (100字/章)
        
        Args:
            summary: 剧情摘要
            foreshadowing: 伏笔分析
            
        Returns:
            章节大纲列表
        """
        logger.info("开始阶段2: 生成章节大纲")
        
        prompt = self._format_prompt(
            "stage2_chapter_outline",
            summary=summary,
            foreshadowing=foreshadowing
        )
        
        response = self._call_api(prompt, "stage2_chapter_outline")
        
        # 解析响应，提取章节大纲
        outlines = []
        lines = response.split('\n')
        current_outline = ""
        
        for line in lines:
            if line.startswith("第") and "章：" in line:
                if current_outline:
                    outlines.append(current_outline.strip())
                current_outline = line + "\n"
            else:
                current_outline += line + "\n"
        
        if current_outline:
            outlines.append(current_outline.strip())
        
        # 保存结果
        self._save_output("stage2", response, "stage2_chapter_outlines.txt")
        
        return outlines
    
    def stage3_expand_chapter(self, chapter_outline: str) -> str:
        """
        阶段3: 每章大纲 → 1k扩写
        
        Args:
            chapter_outline: 章节大纲
            
        Returns:
            扩写后的章节内容
        """
        logger.info("开始阶段3: 章节扩写到1k字")
        
        prompt = self._format_prompt(
            "stage3_chapter_expansion",
            chapter_outline=chapter_outline
        )
        
        response = self._call_api(prompt, "stage3_chapter_expansion")
        
        # 保存结果
        self._save_output("stage3", response, "stage3_expanded_chapter.txt")
        
        return response
    
    def stage4_final_expansion(self, chapter_content: str) -> str:
        """
        阶段4: 1k → 2k扩写（深度优化和润色）
        
        Args:
            chapter_content: 章节内容
            
        Returns:
            最终扩写后的章节内容
        """
        logger.info("开始阶段4: 最终扩写到2k字")
        
        prompt = self._format_prompt(
            "stage4_final_expansion",
            chapter_content=chapter_content
        )
        
        response = self._call_api(prompt, "stage4_final_expansion")
        logger.info(f"stage4扩写响应长度: {len(response)}")
        
        # 检查响应是否为空或过短
        if len(response.strip()) < 100:
            logger.warning("stage4响应内容过短，可能存在问题")
            # 使用原始内容作为备选
            response = chapter_content
            logger.info("使用原始内容作为stage4的备选方案")
        
        # 保存结果
        self._save_output("stage4", response, "stage4_final_chapter.txt")
        
        return response
    
    def process_novel(self, input_file: str, output_dir: str = "output") -> Dict[str, Any]:
        """
        完整处理小说文本
        
        Args:
            input_file: 输入文本文件路径
            output_dir: 输出目录
            
        Returns:
            处理结果字典
        """
        logger.info(f"开始处理小说文件: {input_file}")
        
        # 读取输入文件
        try:
            # 首先尝试UTF-8编码
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    input_text = f.read()
            except UnicodeDecodeError:
                # 如果UTF-8失败，尝试检测编码
                import chardet
            
                logger.warning(f"UTF-8解码失败，尝试检测文件编码...")
                
                # 读取文件内容并检测编码
                with open(input_file, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']
                    confidence = result['confidence']
                
                logger.info(f"检测到编码: {encoding} (置信度: {confidence:.2f})")
                
                if confidence > 0.7:  # 置信度阈值
                    with open(input_file, 'r', encoding=encoding) as f:
                        input_text = f.read()
                    logger.info(f"成功使用 {encoding} 编码读取文件")
                else:
                    # 如果置信度太低，尝试常见编码
                    encodings_to_try = ['gbk', 'gb2312', 'big5', 'latin1']
                    for enc in encodings_to_try:
                        try:
                            with open(input_file, 'r', encoding=enc) as f:
                                input_text = f.read()
                            logger.info(f"成功使用 {enc} 编码读取文件")
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise UnicodeDecodeError(f"无法确定文件编码，尝试的编码: UTF-8, {encoding}, {', '.join(encodings_to_try)}")
                        
        except Exception as e:
            logger.error(f"读取输入文件失败: {e}")
            raise
        
        # 阶段1: 生成剧情摘要和伏笔
        try:
            stage1_result = self.stage1_generate_summary(input_text)
            logger.info("阶段1处理成功")
        except Exception as e:
            logger.error(f"阶段1处理失败: {e}")
            logger.error(f"阶段1错误类型: {type(e).__name__}")
            raise
        
        # 阶段2: 生成章节大纲
        try:
            chapter_outlines = self.stage2_generate_chapter_outlines(
                stage1_result["summary"],
                stage1_result["foreshadowing"]
            )
            logger.info("阶段2处理成功")
        except Exception as e:
            logger.error(f"阶段2处理失败: {e}")
            logger.error(f"阶段2错误类型: {type(e).__name__}")
            raise
        
        # 处理每个章节
        processed_chapters = []
        for i, outline in enumerate(chapter_outlines):
            logger.info(f"处理第 {i+1} 章")
            
            try:
                # 阶段3: 扩写到1k字
                stage3_result = self.stage3_expand_chapter(outline)
                
                # 阶段4: 最终扩写到2k字
                stage4_result = self.stage4_final_expansion(stage3_result)
                
                processed_chapters.append({
                    "chapter_number": i + 1,
                    "outline": outline,
                    "stage3_content": stage3_result,
                    "stage4_content": stage4_result
                })
                
            except Exception as e:
                logger.error(f"处理第 {i+1} 章失败: {e}")
                # 保存失败的章节
                with open(f"failed/chapter_{i+1}_failed.txt", 'w', encoding='utf-8') as f:
                    f.write(outline)
                continue
        
        # 保存完整结果
        final_result = {
            "input_file": input_file,
            "stage1": stage1_result,
            "chapter_outlines": chapter_outlines,
            "processed_chapters": processed_chapters,
            "total_chapters": len(processed_chapters),
            "processing_time": datetime.now().isoformat()
        }
        
        # 保存JSON格式的完整结果
        result_file = os.path.join(output_dir, "novel_processing_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"小说处理完成，结果已保存到: {result_file}")
        return final_result


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="小说生成系统")
    parser.add_argument("input_file", help="输入文本文件路径")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--output", default="output", help="输出目录")
    
    args = parser.parse_args()
    
    try:
        generator = NovelGenerator(config_file=args.config)
        result = generator.process_novel(args.input_file, args.output)
        
        print(f"处理完成！共处理了 {result['total_chapters']} 章")
        print(f"结果已保存到: {args.output}")
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        print(f"处理失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())