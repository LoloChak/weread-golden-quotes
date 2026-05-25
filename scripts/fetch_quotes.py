#!/usr/bin/env python3
"""
微信读书金句抓取器
从微信读书 Agent Gateway API 获取用户的所有划线与想法，
经过质量筛选后生成金句数据文件，供 HTML 页面使用。

依赖：pip install requests
"""

import json
import os
import sys
import time
import hashlib
import re
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ 缺少依赖：请先安装 requests")
    print("   pip install requests")
    sys.exit(1)

# ============================================================
# 配置
# ============================================================

GATEWAY = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.0"
API_KEY = os.environ.get("WEREAD_API_KEY", "")

# 质量筛选关键词（22 组洞察性关键词）
INSIGHT_KEYWORDS = [
    "不是", "而是", "本质", "真正", "关键", "核心", "根本",
    "唯一", "最重要", "秘诀", "真相", "底层", "逻辑", "规律",
    "原则", "误区", "陷阱", "反直觉", "洞察", "发现", "秘密",
    "定律",
]

# 金句长度范围
MIN_LEN = 15
MAX_LEN = 150

# 分类关键词映射
CATEGORY_MAP = {
    "文学": ["小说", "散文", "诗歌", "故事", "虚构", "文学"],
    "个人成长": ["成长", "习惯", "自律", "效率", "自我", "改变"],
    "艺术": ["书法", "绘画", "美学", "审美", "艺术", "设计"],
    "经济理财": ["投资", "理财", "经济", "商业", "财务", "金融"],
    "心理": ["心理", "情绪", "认知", "思维", "意识", "行为"],
    "教育学习": ["学习", "教育", "阅读", "写作", "知识", "方法"],
    "历史": ["历史", "朝代", "文明", "时代", "古代", "战争"],
    "哲学宗教": ["哲学", "存在", "意义", "生命", "宗教", "信仰"],
    "科学技术": ["科学", "技术", "数据", "算法", "物理", "数学"],
    "社会文化": ["社会", "文化", "制度", "组织", "群体", "城市"],
}

# 每组关键词对应的思考问题模板（2 套）
QUESTION_TEMPLATES = {
    "不是": ["这句话否定了什么常见认知？你认同吗？", "反过来想，什么才是真正的？"],
    "而是": ["你生活中有哪些'不是…而是…'的顿悟？", "这个转折背后的前提是什么？"],
    "本质": ["你能用自己的话重新定义这个本质吗？", "什么表象容易遮蔽这个本质？"],
    "真正": ["什么'看似如此实则不然'的经历印证了这句话？", "真正与表面的分界线在哪里？"],
    "关键": ["这个关键因素在你的领域如何体现？", "如果忽略这个关键会怎样？"],
    "核心": ["去掉这个核心会崩塌什么？", "核心与外围的边界如何判断？"],
    "根本": ["你见过哪些只治标不治本的案例？", "追到根本之后，发现什么？"],
    "唯一": ["这个'唯一'成立的前提条件是什么？", "有没有例外？例外说明了什么？"],
    "最重要": ["为什么它比其他都重要？", "最重要的东西为什么总被忽视？"],
    "秘诀": ["这个秘诀可以被复制吗？", "秘诀背后的原理是什么？"],
    "真相": ["什么让你对这真相视而不见？", "知道真相后你的行为会改变吗？"],
    "底层": ["你如何发现事物底层的运行逻辑？", "底层逻辑变更时，表层会如何重组？"],
    "逻辑": ["这个逻辑链条的薄弱环节在哪里？", "你能用一个类比来解释这个逻辑吗？"],
    "规律": ["你观察到生活中哪些隐含的规律？", "规律在什么条件下会失效？"],
    "原则": ["这条原则在极端情况下还成立吗？", "你有没有在关键时刻违背过类似原则？"],
    "误区": ["你曾陷入过这个误区吗？如何走出来的？", "误区之所以普遍，根源是什么？"],
    "陷阱": ["你见过的最隐蔽的陷阱是什么？", "如何建立预警机制来识别陷阱？"],
    "反直觉": ["为什么直觉在这里失效了？", "反直觉的认知能给你带来什么优势？"],
    "洞察": ["这个洞察改变了你对什么的看法？", "你是如何获得类似洞察的？"],
    "发现": ["这个发现对你有什么实际影响？", "还有什么等着你去发现？"],
    "秘密": ["知道这个秘密后，你的选择会不同吗？", "秘密为什么是秘密——是因为没人知道还是没人愿意相信？"],
    "定律": ["这个定律在你的领域如何应用？", "定律是描述性的还是规范性的？"],
}

# 默认思考问题
DEFAULT_QUESTIONS = [
    "这段话对你有什么启发？",
    "你能联想到什么经历或知识？",
    "如果把它写成一条行动准则，怎么写？",
    "它挑战了你什么固有认知？",
    "你会在什么场景下想起这句话？",
]


# ============================================================
# API 调用
# ============================================================

def api_call(payload: dict) -> dict:
    """调用微信读书 Agent Gateway API"""
    if not API_KEY:
        print("❌ 未设置 WEREAD_API_KEY 环境变量")
        print("   export WEREAD_API_KEY=wrk-xxxxxxxx")
        sys.exit(1)

    payload["skill_version"] = SKILL_VERSION
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(GATEWAY, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("errcode", 0) != 0:
            print(f"⚠️  API 错误: {data.get('errmsg', '未知错误')}")
            return {}

        # 版本升级检查
        if "upgrade_info" in data:
            print(f"⬆️  {data['upgrade_info'].get('message', '请升级')}")
        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return {}


def fetch_all_notebooks() -> list:
    """获取所有有笔记的书籍（自动翻页）"""
    print("📚 正在获取笔记本列表...")
    all_books = []
    last_sort = None
    page = 1

    while True:
        payload = {"api_name": "/user/notebooks", "count": 100}
        if last_sort is not None:
            payload["lastSort"] = last_sort

        data = api_call(payload)
        books = data.get("books", [])

        if not books:
            break

        all_books.extend(books)
        has_more = data.get("hasMore", 0)

        print(f"   第 {page} 页：{len(books)} 本，累计 {len(all_books)} 本")

        if has_more != 1:
            break

        last_sort = books[-1].get("sort")
        page += 1
        time.sleep(0.3)  # 请求间隔

    print(f"✅ 共获取 {len(all_books)} 本有笔记的书")
    return all_books


def fetch_bookmarks(book_id: str) -> list:
    """获取单本书的划线内容"""
    data = api_call({"api_name": "/book/bookmarklist", "bookId": book_id})
    return data.get("updated", [])


def fetch_reviews(book_id: str) -> list:
    """获取单本书的想法/点评"""
    all_reviews = []
    synckey = 0

    while True:
        payload = {
            "api_name": "/review/list/mine",
            "bookid": book_id,
            "count": 50,
            "synckey": synckey,
        }
        data = api_call(payload)
        reviews = data.get("reviews", [])

        if not reviews:
            break

        all_reviews.extend(reviews)
        has_more = data.get("hasMore", 0)
        if has_more != 1:
            break

        synckey = data.get("synckey", 0)
        time.sleep(0.2)

    return all_reviews


# ============================================================
# 质量筛选 & 分类
# ============================================================

def classify_text(text: str) -> str:
    """根据内容关键词分类"""
    for category, keywords in CATEGORY_MAP.items():
        if any(kw in text for kw in keywords):
            return category
    return ""


def generate_question(text: str) -> str:
    """根据内容关键词生成思考问题"""
    import random
    matched = []
    for keyword in INSIGHT_KEYWORDS:
        if keyword in text:
            matched.append(keyword)

    if matched:
        kw = random.choice(matched)
        templates = QUESTION_TEMPLATES.get(kw, DEFAULT_QUESTIONS)
        return random.choice(templates)

    return random.choice(DEFAULT_QUESTIONS)


def is_quality_quote(text: str) -> bool:
    """判断是否为高质量金句"""
    # 长度筛选
    if len(text) < MIN_LEN or len(text) > MAX_LEN:
        return False

    # 排除纯标点/数字
    stripped = re.sub(r'[\s\d，。！？、；：""''（）【】《》…—\-·.,!?;:\'"()\[\]{}]', '', text)
    if len(stripped) < 5:
        return False

    # 排除纯对话/引用标记
    if text.startswith(('——', '——', '—', '—')):
        return False

    # 排除纯标题/章节标记
    if re.match(r'^第[一二三四五六七八九十百千万\d]+[章节]', text):
        return False

    return True


def has_insight(text: str) -> bool:
    """判断是否包含洞察性关键词"""
    return any(kw in text for kw in INSIGHT_KEYWORDS)


def dedup_by_prefix(quotes: list, min_prefix_len: int = 20) -> list:
    """基于前缀去重（同一来源的相似金句只保留一条）"""
    seen_prefixes = {}
    result = []

    for q in quotes:
        prefix = q["t"][:min_prefix_len]
        source_key = f"{q['b']}_{prefix}"

        if source_key not in seen_prefixes:
            seen_prefixes[source_key] = True
            result.append(q)

    return result


# ============================================================
# 主流程
# ============================================================

def build_quotes(notebooks: list, max_books: int = None) -> list:
    """从笔记本列表构建金句数据"""
    all_quotes = []
    total = len(notebooks)
    processed = 0
    skipped = 0

    books_to_process = notebooks[:max_books] if max_books else notebooks

    for nb in books_to_process:
        book_info = nb.get("book", {})
        book_id = nb.get("bookId", "")
        title = book_info.get("title", "未知")
        author = book_info.get("author", "")
        note_count = nb.get("noteCount", 0)
        review_count = nb.get("reviewCount", 0)

        processed += 1

        # 跳过没有划线的书
        if note_count == 0 and review_count == 0:
            skipped += 1
            continue

        print(f"   [{processed}/{total}] 《{title}》 划线:{note_count} 想法:{review_count}")

        # 获取划线
        if note_count > 0:
            try:
                bookmarks = fetch_bookmarks(book_id)
                for bm in bookmarks:
                    mark_text = bm.get("markText", "").strip()
                    if mark_text and is_quality_quote(mark_text):
                        all_quotes.append({
                            "t": mark_text,
                            "b": title,
                            "a": author,
                            "c": classify_text(mark_text),
                            "y": "highlight",
                            "q": generate_question(mark_text),
                        })
                time.sleep(0.2)
            except Exception as e:
                print(f"      ⚠️ 划线获取失败: {e}")

        # 获取想法
        if review_count > 0:
            try:
                reviews = fetch_reviews(book_id)
                for rv in reviews:
                    review = rv.get("review", {})
                    content = review.get("content", "").strip()
                    # 想法内容通常是 HTML 格式，提取纯文本
                    content = re.sub(r'<[^>]+>', '', content).strip()
                    if content and is_quality_quote(content):
                        all_quotes.append({
                            "t": content,
                            "b": title,
                            "a": author,
                            "c": classify_text(content),
                            "y": "thought",
                            "q": generate_question(content),
                        })
                time.sleep(0.2)
            except Exception as e:
                print(f"      ⚠️ 想法获取失败: {e}")

    # 前缀去重
    before_dedup = len(all_quotes)
    all_quotes = dedup_by_prefix(all_quotes)
    after_dedup = len(all_quotes)

    if before_dedup != after_dedup:
        print(f"   前缀去重：{before_dedup} → {after_dedup}")

    return all_quotes


def save_quotes_js(quotes: list, output_path: str):
    """保存为 JavaScript 数据文件"""
    # 压缩格式：使用短键名减少体积
    json_str = json.dumps(quotes, ensure_ascii=False, separators=(',', ':'))

    js_content = f"// 微信读书金句数据 - 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    js_content += f"// 共 {len(quotes)} 条金句\n"
    js_content += f"const QUOTES={json_str};\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"📄 数据文件已保存：{output_path} ({size_mb:.1f} MB)")


def save_quotes_json(quotes: list, output_path: str):
    """保存为 JSON 文件（供调试或二次开发）"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)
    print(f"📄 JSON 数据已保存：{output_path}")


# ============================================================
# CLI 入口
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="微信读书金句抓取器 — 从你的阅读笔记中提取高质量金句",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 生成金句网页（默认）
  python fetch_quotes.py -o ./output

  # 只抓取前 50 本书的笔记
  python fetch_quotes.py --max-books 50

  # 同时输出 JSON 格式
  python fetch_quotes.py --json

  # 指定模板
  python fetch_quotes.py --template ./my_template.html
        """
    )
    parser.add_argument("-o", "--output", default="./output", help="输出目录（默认 ./output）")
    parser.add_argument("--max-books", type=int, default=None, help="最多处理多少本书（默认全部）")
    parser.add_argument("--json", action="store_true", help="同时输出 JSON 格式数据")
    parser.add_argument("--template", default=None, help="自定义 HTML 模板路径")
    parser.add_argument("--no-html", action="store_true", help="不生成 HTML 文件（只输出数据）")

    args = parser.parse_args()

    print("╔═══════════════════════════════════════╗")
    print("║   微信读书 · 每日金句生成器          ║")
    print("╚═══════════════════════════════════════╝")
    print()

    # 检查 API Key
    if not API_KEY:
        print("❌ 未设置 WEREAD_API_KEY 环境变量")
        print()
        print("获取方式：")
        print("  1. 打开微信读书 App")
        print("  2. 进入「我」→「设置」→「账户与安全」")
        print("  3. 找到「Agent API Key」并生成")
        print()
        print("配置方式：")
        print("  export WEREAD_API_KEY=wrk-xxxxxxxx")
        sys.exit(1)

    print(f"🔑 API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print()

    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 获取笔记本列表
    notebooks = fetch_all_notebooks()
    if not notebooks:
        print("❌ 未获取到任何笔记本数据")
        sys.exit(1)

    # 2. 构建金句数据
    print()
    print("🔍 正在提取金句...")
    quotes = build_quotes(notebooks, max_books=args.max_books)
    print()
    print(f"✅ 共提取 {len(quotes)} 条金句")

    if not quotes:
        print("❌ 未能提取到任何金句")
        sys.exit(1)

    # 统计
    highlights = sum(1 for q in quotes if q["y"] == "highlight")
    thoughts = sum(1 for q in quotes if q["y"] == "thought")
    books = len(set(q["b"] for q in quotes))
    print(f"   📝 划线金句：{highlights} 条")
    print(f"   💭 想法金句：{thoughts} 条")
    print(f"   📚 来自 {books} 本书")

    # 3. 保存数据文件
    print()
    data_js_path = str(output_dir / "quotes_data.js")
    save_quotes_js(quotes, data_js_path)

    if args.json:
        json_path = str(output_dir / "quotes_data.json")
        save_quotes_json(quotes, json_path)

    # 4. 生成 HTML
    if not args.no_html:
        print()
        template_path = args.template or str(Path(__file__).parent.parent / "assets" / "template.html")

        if not Path(template_path).exists():
            # 尝试使用内置模板
            builtin = Path(__file__).parent.parent / "assets" / "template.html"
            if builtin.exists():
                template_path = str(builtin)
            else:
                print(f"⚠️  模板文件不存在：{template_path}")
                print("   请确保 assets/template.html 文件存在")
                args.no_html = True

        if not args.no_html:
            html_path = str(output_dir / "每日金句.html")

            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 替换统计数字
            html_content = html_content.replace(
                "来自你的 422 本读书笔记",
                f"来自你的 {books} 本读书笔记"
            )

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"🌐 HTML 页面已生成：{html_path}")
            print()
            print("🎉 完成！打开 HTML 文件即可查看你的每日金句")
            print(f"   数据文件：{data_js_path}")
            print(f"   页面文件：{html_path}")


if __name__ == "__main__":
    main()
