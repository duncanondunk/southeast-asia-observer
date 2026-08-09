# 中国—东盟双边关系月度指数 · 系列操作规范（SERIES_SPEC）

> 本文件是「为关系打分：中国—东盟双边关系月度指数」品牌系列的**唯一权威规范**。
> 月度自动化任务在每次运行时**必须首先读取本文件**，并严格遵照执行。
> 本系列已发布首篇（2026年1—8月综述，独立 HTML），本规范定义的**滚动月度系列从其下一个完整月份起**持续运行。

---

## 0. 品牌与定位

- **系列中文名**：为关系打分 · 中国—东盟双边关系月度指数
- **系列英文名**：Scoring the Bond · A Monthly Index of China–ASEAN Relations
- **归属**：网站「数据专题 / Data Features」板块（首页 `index.html` 中 `id="dataFeature"` 区）
- **性质**：学术性量化评估，非官方数据。方法论改编自清华大学阎学通团队《中外关系定量衡量》。
- **产出节奏**：每月一篇，评估**上个月**中国与东盟 11 国的双边关系。
- **作者**：谢畅 / Xie Chang（站点固定作者身份，见 about.html）

---

## 1. 评分方法论（必须严格照此执行）

### 1.1 六档量表（−9 至 +9）

| 大类 | 等级 | 分值范围 |
|------|------|----------|
| 敌对 | 对抗 | −9 至 −6 |
| 敌对 | 紧张 | −6 至 −3 |
| 非敌非友 | 不和 | −3 至 0 |
| 非敌非友 | 普通 | 0 至 +3 |
| 友善 | 良好 | +3 至 +6 |
| 友善 | 友好 | +6 至 +9 |

### 1.2 月度赋分规则

- **基线锚定**：当月分值 = 上月分值 + 当月公开事件调整；无显著事件月份分值**持平或小幅微调**（单月变动通常 ≤ ±0.3，实证均值≈0；不再执行 0.1~0.3/月的机械月度衰减——该规则已于 2026-08-07 依统计检验废止，见 `data/SCORING_VALIDATION.md`）。
- **三个赋权维度**：
  1. **性质**：正面事件加分，负面事件减分。
  2. **层级**：元首/政府首脑级互动 ±0.5~0.9 ＞ 部长级 ±0.2~0.5 ＞ 司局级 ±0.1~0.3。
  3. **领域**：政治互访、安全协议、重大经济签约影响最大（±0.3~0.6）；海上对峙、法律/法理挑衅扣分最狠（−0.5~−1.2）。
- **累加与封顶**：同月内多事件效应累加，**单月净变动上限 ±2.0**（超过则按 ±2.0 截断）。
- **结构性基线**：由国家间关系定位决定——命运共同体（如中柬、中老、中缅、中越、中马、中印尼、中泰）＞ 全面战略伙伴 ＞ 前瞻性伙伴（如中新）。基线通常落在 5.5~7.0 区间。
- **来源**：中华人民共和国外交部 mfa.gov.cn、中国常驻东盟使团、新华社/人民日报/中国政府网、中央广播电视总台、各国官方通稿与主流媒体（联合早报、Reuters、Manila Times 等）。
- **免责声明**：分值为基于公开信息的学术性研究判断，非官方数据。

### 1.3 滚动数据集

- **主文件**：`data/china_asean_scores_rolling.json`（已含 2026-01 至 2026-08 共 8 个月、11 国分值）。
- **结构**：`meta`（含 months 数组、method、sources、disclaimer）+ `countries`（每国含 name/name_en/scores[按月份顺序]/key_events/可选 tier 与说明）。
- **追加月份**：运行时读取该文件，获取最后一月（基准）与各国最新分值；计算新月份分值后，**追加到 `meta.months` 数组与每国 `scores` 列表末尾**，回写同一文件。
- **国家固定顺序**（与现有文件一致，勿改动）：柬埔寨、老挝、越南、缅甸、马来西亚、印度尼西亚、文莱、新加坡、泰国、东帝汶、菲律宾。

---

## 2. 图表生成

- **脚本**：`scripts/plot_china_asean.py`（中文图）、`scripts/plot_china_asean_en.py`（英文图）。
- **参数化**：两脚本均支持 `argv[1]` 指定 JSON 路径；运行月度系列时传入滚动数据集：
  ```
  python3 scripts/plot_china_asean.py data/china_asean_scores_rolling.json
  python3 scripts/plot_china_asean_en.py data/china_asean_scores_rolling.json
  ```
- **输出（按末月冻结，避免改写往期图表）**：脚本以 `meta.months[-1]` 为后缀生成固定文件名，例如数据集末月为 `2026-08` 时输出：
  - 中文：`images/charts/china-asean-relations-2026-08.jpg`（三面板主图）+ `-2026-08-simple.jpg`（简版）
  - 英文：`images/charts/china-asean-relations-2026-08-en.jpg` + `-2026-08-en-simple.jpg`
  - **每月追加新数据后重跑，得到该月专属快照；旧月文件保留不动，保证每篇已发文章图表自洽。**
  - ⓵ 全景（11 国同轴，六档色带背景，菲律宾黑色虚线独处负分区）
  - ⓶ 友善区放大（标关键事件：元首互访、命运共同体联合声明、2+2 机制等）
  - ⓷ 菲律宾单独面板（标注美菲军演、法理挑衅、中方反制等节点）
- **字体**：脚本已内置中文字体候选路径（Hiragino/STHeiti/Arial Unicode），无需额外安装；英文图用 Arial Unicode。
- **注意**：随月份增多，X 轴标签会自动从 `["1月",...]` 变为 `["2026-01",...]` 形式——脚本按 `meta.months` 长度自适应，无需手改。
- **环境**：使用托管 Python `/Users/xiechang/.workbuddy/binaries/python/envs/default/bin/python`（已装 matplotlib）。

---

## 3. 文章结构模板（中英文同义，章节一一对应）

### 中文结构（正文 ≥ 3000 字）

```
标题：为关系打分：中国—东盟双边关系月度指数（YYYY年M月）
导语 kicker：东南亚观察 · 数据专题
导语 standfirst：一句话点出本月核心发现（如"10国稳居友善区间，菲律宾继续探底"）
署名行：谢畅 · 东南亚观察 · YYYY年M月D日 · 约 N 分钟阅读

一、本月态势总览
  - 以数据开头（"改编自清华阎学通团队方法论的指数显示，截至M月……"）
  - 插入 Figure 1（折线图）
  - 三大特征，用"首先/第二/第三"分述（政治互信、经贸高位、局部震荡）
  - 可插入一张配图

二、国别评估
  - 分三个板块：中南半岛五国（引擎）/ 海上东盟四国（友好但受对冲封顶）/ 菲律宾（例外）
  - 每国一段：具体事件 + 分值变化 + 原因；用"第一件/第二件"或"值得注意的是"过渡
  - 插入配图

三、本月面临的新挑战 / 变量
  - 用"一是…/二是…"列负面变量（海上摩擦、第三方因素、国内政治、民意变化）
  - 菲律宾单独深挖
  - 插入配图

四、下月展望
  - 中央情景表（11 国下月预测分值 + 年末等级）
  - 菲律宾双向风险情景（下行/上行）
  - 插入配图

短评（约 300 字，观察者网风）
  - 冒号复合标题（如"一线两域：读懂中国—东盟的分野"）
  - 隐喻式评论，无第一人称，以"is not merely… but…"式收束（中文对应"不仅是……更是……"）

参考文献 / 数据来源
  - 列出 mfa.gov.cn、新华社等权威来源 + 本系列方法论出处

延伸阅读（≤3 条，中英必备，硬性上限 3 条）
  - 中文版在「参考文献」**之前**加一节 `<h2>延伸阅读</h2>`，列 2–3 条本篇核心概念，每条 `<p><strong>术语（英文）</strong>：一句话解释</p>`
  - 英文版在 `References` **之前**加一节 `<h2>Further reading</h2>`，与中文**逐条对等、同为 ≤3 条**（仅语言不同）
  - 示例概念：中国—东盟关系 / 六档双边关系评分（阎学通方法论）/ 命运共同体·"2+2"对话·"3+3"机制
```

### 英文结构（与中文逐段同义）

```
Title: Scoring the Bond: A Monthly Index of China–ASEAN Relations, [Month] [Year]
Kicker: Southeast Asia Watch · Data Features
Standfirst: one-line core finding
Byline: Xie Chang · Southeast Asia Watch · [date] · N min read

I. Monthly Overview
II. Country Assessments
III. Emerging Challenges
IV. Outlook
Short Commentary (~300 words, ECNS analytical register)
References

Further reading (≤3 items, bilingual, hard cap 3): add `<h2>Further reading</h2>` **before** `References`, paired item-by-item with the Chinese `延伸阅读` section (same ≤3 terms, language only differs).
```

**英文文风（ECNS 风）**：事实+数据驱动、短段落、中性语气、导语直陈核心发现、用 "according to the index" / "the data shows" 引出数据。
**中文文风（观察者网风 + 本站点声）**：短段落、口语化连接词（说白了、值得注意的是、背后有几件事）、用中文媒体常用外来词（outlier→例外、baseline→基本面）而非硬译；避免翻译腔。

---

## 4. 配图规范

- 每篇插入 **4 张** 主题配图（来自 Pexels，优先 pexels.com/zh-cn）。
- 放置位置：折线图后、国别评估段后、挑战段后、展望表后各一张。
- **每张必须标注**：`来源：Pexels（作者名, pexels.com/photo/ID）。访问时间：YYYY年M月D日。`
- 图片存 `images/articles/`，文件名用 pexels 原始 slug（如 `pexels-author-ID.jpg`）。
- 若指定图库不可直连，可用 LoremFlickr 的 Creative Commons Flickr 图源按关键词锁定替代，并明确标注为 CC 图源。

---

## 5. 表格规范

- **六档量表表**（首篇已用，沿用样式）：大类/等级/分值范围/特征；"大类"列左对齐（`.macro-cat` 类），其余居中。
- **月度分值表**：国家/当月/预测下月/…/年末等级。
- 表格 CSS 采用站点配色（赤陶红/暖金/深绿/米白），`.macro-cat{text-align:left}`，其余 `text-align:center`。

---

## 6. 发布流程（关键：先审后发）

> **⚠️ 严禁自动化任务自行 push 代码或部署站点。**

每次运行的完整流程：

1. 检索上个月中国与东盟 11 国重大外交事件（WebSearch/WebFetch + 必要时派子代理分国检索；**禁止虚构事件或日期**，无法确认的标注"存疑"）。
2. 按第 1 节方法论对 11 国逐国打分，追加到 `data/china_asean_scores_rolling.json`。
3. 运行绘图脚本生成中/英文折线图。
4. 撰写中、英文文章（中文 ≥ 3000 字，中英逐段同义），插入 4 张配图（含来源与访问时间）。
5. 生成两个独立 HTML 文件：
   - `articles/china-asean-relations-YYYY-MM-zh.html`
   - `articles/china-asean-relations-YYYY-MM-en.html`
   - 页眉回首页链接用 `../index.html`；CSS 沿用站点配色与现有两篇的样式。
6. **暂停，向用户展示草稿（文件路径 + 预览），并明确说明"待审核，尚未发布"。**
7. **等待用户在对话中明示"可以发布"后**，才执行：
   - 将两篇文章链接加入首页 `id="dataFeature"` 区（按语言分 `data-lang-card="zh"` / `"en"`，沿用现有语言自适应逻辑）；
   - `git add` 相关文件 → `git commit` → `git push origin main`（SSH，触发 Vercel 海外自动部署）；
   - `workbuddy_cloudstudio_deploy` 重部署国内镜像站（sandboxId 9504b8d136b54114b6755f4c12541449，链接不变）。
8. curl 验证首页、两篇文章、图表、配图均返回 200。

---

## 7. 文件与路径速查

| 用途 | 路径 |
|------|------|
| 滚动数据集 | `data/china_asean_scores_rolling.json` |
| 中文绘图脚本 | `scripts/plot_china_asean.py` |
| 英文绘图脚本 | `scripts/plot_china_asean_en.py` |
| 图表输出 | `images/charts/china-asean-relations-{末月}.jpg`（及 `-simple` / `-en` / `-en-simple` 变体；每月冻结） |
| 配图目录 | `images/articles/` |
| 文章输出 | `articles/china-asean-relations-YYYY-MM-{zh,en}.html` |
| 首页数据专题区 | `index.html` → `id="dataFeature"` |
| 托管 Python | `/Users/xiechang/.workbuddy/binaries/python/envs/default/bin/python` |

---

## 8. 质量检查清单（每次发布前自检）

- [ ] 11 国分值均落在 −9~+9，且经脚本按六档量表复核等级归属（勿凭印象手写等级）
- [ ] 单月净变动无超过 ±2.0 者；无事件月份持平或小幅微调（≤ ±0.3），无机械月度衰减
- [ ] 滚动数据集 months 与各国 scores 长度一致
- [ ] 中英文文章逐段同义；中文正文 ≥ 3000 字
- [ ] 4 张配图均标注来源 + 访问时间
- [ ] 六档量表表"大类"列左对齐、其余居中
- [ ] 未执行任何 push / deploy（除非用户已明示发布）
