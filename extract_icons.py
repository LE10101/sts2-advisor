"""
游戏图标提取脚本
从杀戮尖塔2游戏文件中提取卡牌/遗物/敌人图标
运行方式: python extract_icons.py --game-dir "D:\\LeStoreDownload\\steam\\steamapps\\common\\Slay the Spire 2"
"""
import os
import sys
import shutil
import argparse
from pathlib import Path


def find_icon_files(game_dir: str) -> dict:
    """扫描游戏目录，找到所有图标文件"""
    icons = {"cards": {}, "relics": {}, "enemies": {}, "ui": {}}

    game_path = Path(game_dir)
    if not game_path.exists():
        print(f"[错误] 游戏目录不存在: {game_dir}")
        return icons

    # 搜索所有图片文件
    image_exts = {".png", ".jpg", ".webp", ".svg"}
    all_images = []

    for root, dirs, files in os.walk(game_path):
        # 跳过一些大目录
        if "Steam" in root or "steamapps" in root and "common" not in root:
            continue
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in image_exts:
                all_images.append(os.path.join(root, f))

    print(f"找到 {len(all_images)} 个图片文件")

    # 分类
    for img_path in all_images:
        name = Path(img_path).stem.lower()
        parent = Path(img_path).parent.name.lower()

        if "card" in parent or "cards" in parent or "card" in name:
            icons["cards"][name] = img_path
        elif "relic" in parent or "relics" in parent or "relic" in name:
            icons["relics"][name] = img_path
        elif "enemy" in parent or "enemies" in parent or "monster" in parent:
            icons["enemies"][name] = img_path
        elif "ui" in parent or "icon" in parent:
            icons["ui"][name] = img_path

    return icons


def extract_icons(game_dir: str, output_dir: str):
    """提取图标到输出目录"""
    icons = find_icon_files(game_dir)

    # 创建输出目录
    out_path = Path(output_dir)
    for subdir in ["cards", "relics", "enemies", "ui"]:
        (out_path / subdir).mkdir(parents=True, exist_ok=True)

    # 复制文件
    total = 0
    for category, files in icons.items():
        for name, src in files.items():
            ext = Path(src).suffix
            dst = out_path / category / f"{name}{ext}"
            try:
                shutil.copy2(src, dst)
                total += 1
            except Exception as e:
                print(f"  复制失败 {name}: {e}")

    print(f"\n提取完成: {total} 个图标")
    print(f"输出目录: {output_dir}")
    print(f"  卡牌: {len(icons['cards'])}")
    print(f"  遗物: {len(icons['relics'])}")
    print(f"  敌人: {len(icons['enemies'])}")
    print(f"  UI: {len(icons['ui'])}")

    if total == 0:
        print("\n[提示] 未找到图标文件。杀戮尖塔2使用Godot引擎，资源打包在.pck文件中。")
        print("请使用Godot引擎的pck解包工具提取资源:")
        print("  1. 下载Godot 4.x: https://godotengine.org/")
        print("  2. 用Godot打开游戏目录或解包.pck文件")
        print("  3. 导出图标到 static/icons/ 目录")
        print("\n或者，STS2 AI Agent mod可能已暴露部分资源，检查mods目录。")

    return total


def create_icon_mapping(output_dir: str):
    """创建图标名称映射文件"""
    mapping = {
        "cards": {},
        "relics": {}
    }

    # 静默猎手卡牌名称映射（中文名 -> 可能的文件名）
    card_names = [
        "打击", "防御", "致命毒药", "毒性爆发", "咕嘟冒泡", "墨之刃", "袖里乾坤",
        "逃脱计划", "早有准备", "生存者", "侧步", "蜃景", "余像", "尖啸",
        "暴露", "啄击", "终结技", "猛扑", "扫腿", "中和", "触媒", "腐蚀波",
        "带毒刺击", "睡眠不佳", "进阶之灾", "笨拙", "回响斩击", "突然一拳",
        "潦草急救", "必备工具", "后空翻", "羽化", "腐蚀", "蛇咬", "磨蚀"
    ]

    for name in card_names:
        # 尝试多种文件名格式
        possible = [
            name.lower(),
            name.replace("+", "").lower(),
            name.replace(" ", "_").lower(),
        ]
        mapping["cards"][name] = possible

    # 遗物名称映射
    relic_names = [
        "风的女儿", "水银沙漏", "投斧", "船夹板", "金纸", "永冻冰晶",
        "钨合金棍", "蛇之戒指", "红面具", "节日拉炮", "巨大扭蛋", "空鸟笼"
    ]
    for name in relic_names:
        mapping["relics"][name] = [name.lower(), name.replace(" ", "_").lower()]

    mapping_path = Path(output_dir) / "icon_mapping.json"
    import json
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"图标映射文件已创建: {mapping_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="提取杀戮尖塔2游戏图标")
    parser.add_argument("--game-dir", default=r"D:\LeStoreDownload\steam\steamapps\common\Slay the Spire 2",
                        help="游戏安装目录")
    parser.add_argument("--output-dir", default="static/icons",
                        help="输出目录")
    args = parser.parse_args()

    print("=" * 50)
    print("STS2 游戏图标提取工具")
    print("=" * 50)
    print(f"游戏目录: {args.game_dir}")
    print(f"输出目录: {args.output_dir}")
    print("=" * 50)

    extract_icons(args.game_dir, args.output_dir)
    create_icon_mapping(args.output_dir)
