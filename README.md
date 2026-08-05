# 东南亚观察 · Southeast Asia Watch

一个独立运营的东南亚区域观察博客，聚焦地缘政治、经济产业、气候变化与社会文化。

## 技术栈

- **纯静态站点**：HTML + CSS + 原生 JavaScript，无构建步骤
- **Markdown 渲染**：[marked](https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js) + [DOMPurify](https://cdn.jsdelivr.net/npm/dompurify@3.0.11/dist/purify.min.js)（CDN 引入，安全清洗）
- **数据驱动**：`data/articles.json` 存文章元数据，`articles/*.md` 存正文，前端 `fetch` 加载

## 目录结构

```
东南亚研究网站开发/
├── index.html          # 首页（精选轮播 + 分类分区 + 热门榜）
├── article.html        # 文章详情页（Markdown 渲染 + 目录 + 上下篇）
├── tags.html           # 标签页（标签云 + 按标签筛选）
├── about.html          # 关于页面
├── css/style.css       # 全站样式
├── js/app.js           # 核心逻辑
├── data/
│   └── articles.json   # 文章元数据
└── articles/           # Markdown 正文
    ├── vietnam-manufacturing-supply-chain.md
    ├── indonesia-nickel-export-ban.md
    ├── mekong-drought-floods.md
    ├── singapore-small-state-diplomacy.md
    └── philippines-south-china-sea-pivot.md
```

## 本地运行

由于使用 `fetch` 加载 JSON 与 Markdown，需通过 HTTP 服务器访问（不能用 `file://` 直接打开）：

```bash
cd 东南亚研究网站开发
python3 -m http.server 8000
# 浏览器访问 http://localhost:8000
```

## 添加新文章

1. 在 `articles/` 下新建一个 `.md` 文件（文件名即 slug，建议英文短横线）
2. 在 `data/articles.json` 数组里追加一条元数据：

```json
{
  "slug": "my-new-post",
  "title": "文章标题",
  "subtitle": "副标题",
  "category": "地缘政治",
  "tags": ["地缘政治", "国家观察"],
  "country": "越南",
  "date": "2026-08-01",
  "readingTime": 8,
  "featured": false,
  "summary": "一句话摘要，用于列表展示。"
}
```

> 若不写 `"file"` 字段，正文默认从 `articles/{slug}.md` 加载。

## 设计说明

- **视觉参考**：cryopolitics.com 的杂志式分区布局（精选轮播 + 分类纵向堆叠 + 分享按钮前置）
- **配色**：东南亚暖色——赤陶红 `#a8401f`、暖金 `#c98a2b`、热带深绿 `#1d5b4e`，米白底 `#faf7f2`
- **字体**：标题用衬线体（Noto Serif SC），正文用无衬线（Noto Sans SC）
- **响应式**：900px / 640px 两档断点，移动端导航折叠

## 部署

纯静态，可直接部署到任意静态托管：

- **CloudStudio 沙箱**：用云部署能力一键发布
- **Vercel / Netlify / Cloudflare Pages**：直接连接目录，无需构建命令
- **GitHub Pages**：推到仓库开启 Pages 即可
- **自有服务器**：把整个目录丢到 nginx 静态目录

## 已实现功能

- [x] 文章列表（首页最新 + 分类分区 + 热门榜）
- [x] 文章详情（Markdown 渲染、自动目录、标签、上下篇导航）
- [x] 标签分类（标签云 + 按标签筛选 + URL 参数同步）
- [x] 关于页面
- [x] 精选轮播（自动播放、悬停暂停、左右切换、圆点导航）
- [x] 分享按钮（X / Facebook / 邮件 / 复制链接）
- [x] 订阅表单（前端校验）
- [x] 移动端响应式 + 导航折叠
- [x] SEO（meta 描述、Open Graph、结构化数据）
- [x] 无障碍（语义化标签、焦点样式、aria 标签）
