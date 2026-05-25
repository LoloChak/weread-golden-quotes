# 微信读书每日金句生成器

从你的微信读书笔记中提取高质量金句，生成宣纸质感人文风格网页，每日随机展示 + 思考问题引导。

![预览图](https://img.shields.io/badge/字体-京华老宋体%20%7C%20LXGW文楷-brown)
![Python](https://img.shields.io/badge/Python-3.6+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 效果预览

生成的网页包含：

- 🎴 **宣纸底纹** — 多层 CSS 叠加的纤维质感
- 🖋️ **京华老宋体 + LXGW文楷** — 人文气质字体组合
- 💡 **每日金句** — 基于日期种子的确定性随机，每天不同
- 🤔 **思考问题** — 每条金句附带内容相关的思考引导
- ❤️ **收藏功能** — localStorage 持久化，支持导出 TXT
- 📱 **响应式** — 移动端适配

## 快速开始

### 前置条件

1. **微信读书 Agent Gateway API Key**（格式 `wrk-xxxxxxxx`）
   - 方式一：通过 [WorkBuddy](https://www.codebuddy.cn/) 安装微信读书 Skill，自动获取 API Key
   - 方式二：在微信读书网页版登录后，通过浏览器开发者工具抓取请求中的 Bearer Token

2. **Python 3.6+** 和 `requests` 库
   ```bash
   pip install requests
   ```

### 生成金句

```bash
# 1. 设置 API Key
export WEREAD_API_KEY="wrk-xxxxxxxx"

# 2. 克隆仓库
git clone https://github.com/LoloChak/weread-golden-quotes.git
cd weread-golden-quotes

# 3. 运行生成脚本
python scripts/fetch_quotes.py -o ./output

# 4. 打开生成的网页
open output/每日金句.html  # macOS
# 或 xdg-open output/每日金句.html  # Linux
```

## 命令参数

```
python scripts/fetch_quotes.py [选项]

选项：
  -o, --output     输出目录（默认 ./output）
  --max-books      最多处理多少本书（默认全部）
  --json           同时输出 JSON 格式数据
  --template       自定义 HTML 模板路径
  --no-html        不生成 HTML（只输出数据）
```

### 示例

```bash
# 快速测试：只处理前 20 本书
python scripts/fetch_quotes.py --max-books 20

# 同时输出 JSON（供二次开发）
python scripts/fetch_quotes.py --json

# 使用自定义模板
python scripts/fetch_quotes.py --template ./my_template.html
```

## 工作原理

```
微信读书 API
    │
    ├─ /user/notebooks     获取所有有笔记的书籍（自动翻页）
    │
    ├─ /book/bookmarklist  获取每本书的划线内容
    │
    └─ /review/list/mine   获取每本书的想法/点评
         │
         ▼
    质量筛选
    ├─ 长度过滤（15-150字）
    ├─ 洞察关键词匹配（22组）
    ├─ 内容清洗（排除标题/引用/纯标点）
    └─ 前缀去重
         │
         ▼
    分类 + 思考问题生成
    ├─ 10 大分类关键词映射
    └─ 49 条专属问题 + 5 条通用问题
         │
         ▼
    输出
    ├─ quotes_data.js   金句数据文件
    └─ 每日金句.html     宣纸质感网页
```

## 数据结构

每条金句的格式：

```json
{
  "t": "真正的自由不是想做什么就做什么，而是不想做什么就可以不做什么",
  "b": "1000个铁粉",
  "a": "某某某",
  "c": "个人成长",
  "y": "highlight",
  "q": "真正的自由在你的生活中意味着什么？"
}
```

| 字段 | 说明 |
|------|------|
| `t` | 金句文本 |
| `b` | 书名 |
| `a` | 作者 |
| `c` | 分类 |
| `y` | 类型：`highlight`（划线）或 `thought`（想法） |
| `q` | 思考问题 |

## 自定义

### 修改页面样式

复制 `assets/template.html` 并修改 CSS，然后通过 `--template` 指定：

```bash
python scripts/fetch_quotes.py --template ./my_style.html
```

模板关键约定：
- 必须包含 `<script src="quotes_data.js"></script>`
- 数据通过全局变量 `QUOTES` 访问
- 统计数字由 JS 动态计算

### 修改筛选规则

编辑 `scripts/fetch_quotes.py` 中的配置：

```python
# 金句长度范围
MIN_LEN = 15
MAX_LEN = 150

# 洞察关键词
INSIGHT_KEYWORDS = ["不是", "而是", "本质", ...]
```

## 项目结构

```
weread-golden-quotes/
├── SKILL.md                   # Skill 定义文件
├── README.md                  # 本文件
├── LICENSE                    # MIT 许可证
├── scripts/
│   └── fetch_quotes.py        # 数据抓取 + 金句生成脚本
└── assets/
    └── template.html          # HTML 模板（宣纸质感）
```

## 常见问题

### Q: API Key 在哪里获取？
本项目使用微信读书 Agent Gateway API（`i.weread.qq.com`），获取方式：

**方式一（推荐）：** 安装 [WorkBuddy](https://www.codebuddy.cn/)，通过内置的微信读书 Skill 自动获取 API Key。

**方式二：** 在微信读书网页版 (weread.qq.com) 登录后，打开浏览器开发者工具（F12），在 Network 面板中找到任意请求，复制请求头中的 `access_token` 值（格式为 `wrk-xxxxxxxx`）。

> ⚠️ API Key 属于个人隐私，请勿分享或提交到公开仓库。

### Q: 首次运行需要多久？
取决于你的笔记数量。100 本书大约 2-3 分钟，400+ 本书可能需要 10 分钟左右。

### Q: 生成的网页可以离线使用吗？
可以查看金句和收藏功能，但字体需要网络加载。如果需要完全离线，可以下载字体文件到本地并修改 HTML 中的引用。

### Q: 我的笔记很少，能生成金句吗？
可以。脚本会自动适配数据量，即使只有几本书也能生成。建议至少有 5 本以上有笔记的书。

### Q: 收藏的数据存在哪里？
使用浏览器的 localStorage 存储，数据保存在本地。清除浏览器数据会丢失收藏，建议定期使用导出功能。

## 致谢

- 字体：[京华老宋体](https://www.zeoseven.com/)、[LXGW WenKai](https://github.com/lxgw/LxgwWenKai)
- API：微信读书 Agent Gateway

## License

MIT License
