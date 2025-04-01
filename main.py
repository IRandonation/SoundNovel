from generators import WorldGenerator, PlotGenerator, ChapterGenerator
from models import NovelConfig
import json
from utils import load_config, select_from_list  # 添加导入


def main():
    # 初始化配置
    initial_prompt = input("请输入小说主题或初始想法: ")
    genre = select_from_list("选择类型", load_config()["novel"]["genres"])
    style = select_from_list("选择风格", load_config()["novel"]["styles"])
    
    # 生成世界设定
    print("生成世界观...")
    world = WorldGenerator.generate(f"{initial_prompt}\n类型: {genre}\n风格: {style}")
    
    # 生成主线剧情
    print("生成主线...")
    plot = PlotGenerator.generate(world)
    
    # 生成章节
    print("生成章节内容...")
    chapters = []
    for i in range(1, load_config()["novel"]["chapter_count"] + 1):
        print(f"生成第{i}章...")
        outline = generate_outline(i, world, plot)
        chapter = ChapterGenerator.generate(outline, chapters)
        chapters.append(chapter)
    
    # 输出结果
    save_novel(world, plot, chapters)

def select_from_list(prompt, options):
    print(f"{prompt}:")
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        choice = input("请选择(1-{}): ".format(len(options)))
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice)-1]

def generate_outline(ch_num, world, plot):
    # 简化的梗概生成逻辑
    return {
        "number": ch_num,
        "title": f"第{ch_num}章",
        "key_events": [plot.key_events[ch_num % len(plot.key_events)]]
    }

def save_novel(world, plot, chapters):
    novel = {
        "world": world.__dict__,
        "plot": plot.__dict__,
        "chapters": [ch.__dict__ for ch in chapters]
    }
    with open("novel_output.json", "w", encoding="utf-8") as f:
        json.dump(novel, f, ensure_ascii=False, indent=2)
    print("小说已生成到 novel_output.json")

if __name__ == "__main__":
    main()