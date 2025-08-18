"""
工作流程测试脚本
测试整个小说创作AI Agent的工作流程
"""

import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.project_manager import ProjectManager
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.core.sliding_window import ContextManager
from novel_generator.config.settings import Settings
from novel_generator.utils.logger import NovelLogger
from novel_generator.utils.file_handler import FileHandler
from novel_generator.utils.api_client import ZhipuAIClient


class WorkflowTester:
    """工作流程测试器"""
    
    def __init__(self, project_root: str = "."):
        """
        初始化测试器
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root).resolve()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """
        记录测试结果
        
        Args:
            test_name: 测试名称
            success: 是否成功
            message: 测试消息
        """
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'name': test_name,
            'success': success,
            'message': message
        })
    
    def test_project_structure(self) -> bool:
        """测试项目结构"""
        print("\n🔍 测试项目结构...")
        
        required_dirs = [
            "novel_generator",
            "novel_generator/core",
            "novel_generator/config",
            "novel_generator/utils",
            "novel_generator/templates",
            "01_source",
            "02_outline",
            "02_outline/outline_history",
            "03_draft",
            "03_draft/draft_history",
            "04_prompt",
            "05_script",
            "06_log",
            "06_log/ai_api_logs",
            "06_log/system_logs"
        ]
        
        required_files = [
            "01_source/core_setting.yaml",
            "01_source/overall_outline.yaml",
            "04_prompt/chapter_expand_prompt.yaml",
            "04_prompt/style_guide.yaml",
            "05_script/config.json",
            "05_script/main.py",
            "05_script/expand_chapters.py"
        ]
        
        # 检查目录
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                self.log_test("项目结构", False, f"缺少目录: {dir_path}")
                return False
        
        # 检查文件
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.log_test("项目结构", False, f"缺少文件: {file_path}")
                return False
        
        self.log_test("项目结构", True, "所有必要目录和文件都存在")
        return True
    
    def test_config_files(self) -> bool:
        """测试配置文件"""
        print("\n🔍 测试配置文件...")
        
        # 测试核心设定模板
        try:
            with open(self.project_root / "01_source" / "core_setting.yaml", 'r', encoding='utf-8') as f:
                core_setting = yaml.safe_load(f)
            
            required_fields = ['世界观', '核心冲突', '人物小传', '伏笔清单']
            missing_fields = [field for field in required_fields if field not in core_setting]
            
            if missing_fields:
                self.log_test("核心设定模板", False, f"缺少字段: {', '.join(missing_fields)}")
                return False
            
            self.log_test("核心设定模板", True, "核心设定模板格式正确")
            
        except Exception as e:
            self.log_test("核心设定模板", False, f"读取失败: {e}")
            return False
        
        # 测试整体大纲模板
        try:
            with open(self.project_root / "01_source" / "overall_outline.yaml", 'r', encoding='utf-8') as f:
                overall_outline = yaml.safe_load(f)
            
            required_fields = ['第一幕', '第二幕', '第三幕', '关键转折点']
            missing_fields = [field for field in required_fields if field not in overall_outline]
            
            if missing_fields:
                self.log_test("整体大纲模板", False, f"缺少字段: {', '.join(missing_fields)}")
                return False
            
            self.log_test("整体大纲模板", True, "整体大纲模板格式正确")
            
        except Exception as e:
            self.log_test("整体大纲模板", False, f"读取失败: {e}")
            return False
        
        # 测试配置文件
        try:
            with open(self.project_root / "05_script" / "config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            required_fields = ['api_key', 'api_base_url', 'models', 'paths']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                self.log_test("配置文件", False, f"缺少字段: {', '.join(missing_fields)}")
                return False
            
            self.log_test("配置文件", True, "配置文件格式正确")
            
        except Exception as e:
            self.log_test("配置文件", False, f"读取失败: {e}")
            return False
        
        return True
    
    def test_python_modules(self) -> bool:
        """测试Python模块"""
        print("\n🔍 测试Python模块...")
        
        # 测试导入
        try:
            from novel_generator.core.project_manager import ProjectManager
            from novel_generator.core.outline_generator import OutlineGenerator
            from novel_generator.core.chapter_expander import ChapterExpander
            from novel_generator.core.sliding_window import ContextManager
            from novel_generator.config.settings import Settings
            from novel_generator.utils.logger import NovelLogger
            from novel_generator.utils.file_handler import FileHandler
            from novel_generator.utils.api_client import ZhipuAIClient
            
            self.log_test("Python模块导入", True, "所有模块导入成功")
            return True
            
        except ImportError as e:
            self.log_test("Python模块导入", False, f"导入失败: {e}")
            return False
        except Exception as e:
            self.log_test("Python模块导入", False, f"未知错误: {e}")
            return False
    
    def test_project_manager(self) -> bool:
        """测试项目管理器"""
        print("\n🔍 测试项目管理器...")
        
        try:
            # 创建项目管理器
            manager = ProjectManager(str(self.project_root))
            
            # 测试加载配置
            config = manager.load_config()
            if not config:
                self.log_test("项目管理器", False, "加载配置失败")
                return False
            
            # 测试验证项目结构
            if not manager.validate_project_structure():
                self.log_test("项目管理器", False, "验证项目结构失败")
                return False
            
            self.log_test("项目管理器", True, "项目管理器功能正常")
            return True
            
        except Exception as e:
            self.log_test("项目管理器", False, f"测试失败: {e}")
            return False
    
    def test_settings(self) -> bool:
        """测试设置管理器"""
        print("\n🔍 测试设置管理器...")
        
        try:
            # 加载配置
            config_path = self.project_root / "05_script" / "config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 创建设置管理器
            settings = Settings(config)
            
            # 测试验证
            settings.validate()
            
            # 测试获取API模型
            model = settings.get_api_model('stage4')
            if not model:
                self.log_test("设置管理器", False, "获取API模型失败")
                return False
            
            self.log_test("设置管理器", True, "设置管理器功能正常")
            return True
            
        except Exception as e:
            self.log_test("设置管理器", False, f"测试失败: {e}")
            return False
    
    def test_file_handler(self) -> bool:
        """测试文件处理器"""
        print("\n🔍 测试文件处理器...")
        
        try:
            # 创建文件处理器
            file_handler = FileHandler(str(self.project_root))
            
            # 测试读取YAML文件
            core_setting = file_handler.read_yaml("01_source/core_setting.yaml")
            if not core_setting:
                self.log_test("文件处理器", False, "读取YAML文件失败")
                return False
            
            # 测试读取JSON文件
            config = file_handler.read_json("05_script/config.json")
            if not config:
                self.log_test("文件处理器", False, "读取JSON文件失败")
                return False
            
            # 测试写入文件
            test_data = {"test": "data", "timestamp": str(file_handler.get_file_modified_time("01_source/core_setting.yaml"))}
            test_file = file_handler.write_yaml("test_output.yaml", test_data)
            
            if not file_handler.file_exists("test_output.yaml"):
                self.log_test("文件处理器", False, "写入文件失败")
                return False
            
            # 清理测试文件
            file_handler.delete_file("test_output.yaml")
            
            self.log_test("文件处理器", True, "文件处理器功能正常")
            return True
            
        except Exception as e:
            self.log_test("文件处理器", False, f"测试失败: {e}")
            return False
    
    def test_logger(self) -> bool:
        """测试日志管理器"""
        print("\n🔍 测试日志管理器...")
        
        try:
            # 加载配置
            config_path = self.project_root / "05_script" / "config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 创建日志管理器
            logger = NovelLogger(config)
            
            # 测试记录操作
            logger.log_operation("测试操作", {"test": True})
            
            # 测试记录错误
            logger.log_error(Exception("测试错误"), "测试上下文")
            
            # 测试获取操作历史
            history = logger.get_operation_history()
            if not history:
                self.log_test("日志管理器", False, "获取操作历史失败")
                return False
            
            self.log_test("日志管理器", True, "日志管理器功能正常")
            return True
            
        except Exception as e:
            self.log_test("日志管理器", False, f"测试失败: {e}")
            return False
    
    def test_outline_generator(self) -> bool:
        """测试大纲生成器"""
        print("\n🔍 测试大纲生成器...")
        
        try:
            # 加载配置
            config_path = self.project_root / "05_script" / "config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载核心设定和整体大纲
            with open(self.project_root / "01_source" / "core_setting.yaml", 'r', encoding='utf-8') as f:
                core_setting = yaml.safe_load(f)
            
            with open(self.project_root / "01_source" / "overall_outline.yaml", 'r', encoding='utf-8') as f:
                overall_outline = yaml.safe_load(f)
            
            # 创建大纲生成器
            outline_generator = OutlineGenerator(config)
            
            # 测试构建提示词
            prompt = outline_generator._build_outline_prompt(core_setting, overall_outline, (1, 3))
            if not prompt:
                self.log_test("大纲生成器", False, "构建提示词失败")
                return False
            
            # 测试解析响应（使用模拟响应）
            mock_response = """
第1章:
  标题: "开篇"
  核心事件: "主角登场"
  场景: "山村"
  人物行动: "主角晨读"
  伏笔回收: ""
  字数目标: 1500
"""
            
            outline = outline_generator._parse_response(mock_response)
            if not outline:
                self.log_test("大纲生成器", False, "解析响应失败")
                return False
            
            self.log_test("大纲生成器", True, "大纲生成器功能正常")
            return True
            
        except Exception as e:
            self.log_test("大纲生成器", False, f"测试失败: {e}")
            return False
    
    def test_chapter_expander(self) -> bool:
        """测试章节扩写器"""
        print("\n🔍 测试章节扩写器...")
        
        try:
            # 加载配置
            config_path = self.project_root / "05_script" / "config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 创建章节扩写器
            expander = ChapterExpander(config)
            
            # 测试构建提示词
            chapter_outline = {
                "标题": "开篇",
                "核心事件": "主角登场",
                "场景": "山村",
                "人物行动": "主角晨读",
                "伏笔回收": "",
                "字数目标": 1500
            }
            
            prompt = expander._build_expand_prompt(
                chapter_num=1,
                chapter_outline=chapter_outline,
                previous_context="",
                style_guide={}
            )
            
            if not prompt:
                self.log_test("章节扩写器", False, "构建提示词失败")
                return False
            
            # 测试解析响应（使用模拟响应）
            mock_response = "清晨的阳光洒进小屋，主角开始新的一天..."
            
            content = expander._parse_and_optimize_response(mock_response, chapter_outline)
            if not content:
                self.log_test("章节扩写器", False, "解析响应失败")
                return False
            
            self.log_test("章节扩写器", True, "章节扩写器功能正常")
            return True
            
        except Exception as e:
            self.log_test("章节扩写器", False, f"测试失败: {e}")
            return False
    
    def test_sliding_window(self) -> bool:
        """测试滑动窗口"""
        print("\n🔍 测试滑动窗口...")
        
        try:
            # 加载配置
            config_path = self.project_root / "05_script" / "config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 创建滑动窗口
            from novel_generator.core.sliding_window import SlidingWindow
            sliding_window = SlidingWindow(config)
            
            # 测试构建上下文
            context = sliding_window.build_context(1, [], str(self.project_root / "03_draft"))
            
            # 测试优化上下文
            chapter_outline = {
                "标题": "开篇",
                "核心事件": "主角登场"
            }
            
            optimized_context = sliding_window.optimize_window(1, context, chapter_outline)
            
            if not optimized_context:
                self.log_test("滑动窗口", False, "优化上下文失败")
                return False
            
            self.log_test("滑动窗口", True, "滑动窗口功能正常")
            return True
            
        except Exception as e:
            self.log_test("滑动窗口", False, f"测试失败: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🚀 开始工作流程测试...")
        
        tests = [
            self.test_project_structure,
            self.test_config_files,
            self.test_python_modules,
            self.test_project_manager,
            self.test_settings,
            self.test_file_handler,
            self.test_logger,
            self.test_outline_generator,
            self.test_chapter_expander,
            self.test_sliding_window
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        # 输出测试结果摘要
        print(f"\n📊 测试结果摘要:")
        print(f"   通过: {passed}/{total}")
        print(f"   成功率: {passed/total*100:.1f}%")
        
        if passed == total:
            print("\n🎉 所有测试通过！工作流程正常。")
            return True
        else:
            print(f"\n⚠️  有 {total-passed} 个测试失败，请检查相关组件。")
            return False
    
    def generate_test_report(self) -> str:
        """生成测试报告"""
        report = "# 工作流程测试报告\n\n"
        report += f"测试时间: {str(self.project_root)}\n\n"
        
        for result in self.test_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            report += f"## {result['name']}\n"
            report += f"- 状态: {status}\n"
            report += f"- 详情: {result['message']}\n\n"
        
        return report


def main():
    """主函数"""
    print("🧪 小说创作AI Agent工作流程测试")
    print("=" * 50)
    
    # 创建测试器
    tester = WorkflowTester()
    
    # 运行所有测试
    success = tester.run_all_tests()
    
    # 生成测试报告
    report = tester.generate_test_report()
    
    # 保存测试报告
    report_path = tester.project_root / "test_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 测试报告已保存: {report_path}")
    
    # 返回测试结果
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())