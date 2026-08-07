# -*- coding: utf-8 -*-
"""中国—东盟11国双边关系月度量化评分折线图（2026年1-8月）"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle
import matplotlib.gridspec as gridspec

BASE = "/Users/xiechang/WorkBuddy/东南亚研究网站开发"
OUT = os.path.join(BASE, "images", "charts")
os.makedirs(OUT, exist_ok=True)

# ---------- 中文字体 ----------
CAND = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]
CN = None
for p in CAND:
    if os.path.exists(p):
        try:
            fm.fontManager.addfont(p)
            CN = fm.FontProperties(fname=p)
            name = CN.get_name()
            plt.rcParams["font.family"] = name
            print("font ->", p, "|", name)
            break
        except Exception as e:
            print("skip", p, e)
plt.rcParams["axes.unicode_minus"] = False

def F(size, weight="normal"):
    fp = fm.FontProperties(fname=CN.get_file()) if CN else fm.FontProperties()
    fp.set_size(size); fp.set_weight(weight)
    return fp

# ---------- 数据（支持 argv[1] 指定滚动数据集路径）----------
import sys
_JSON = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data", "china_asean_scores_2026.json")
with open(_JSON, encoding="utf-8") as f:
    D = json.load(f)

MONTHS = list(range(1, 9))
XLAB = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月*"]

COLORS = {
    "柬埔寨": "#C0392B", "老挝": "#E67E22", "越南": "#B7950B", "缅甸": "#1E8449",
    "马来西亚": "#17A589", "印度尼西亚": "#2471A3", "文莱": "#7D3C98",
    "新加坡": "#D81B60", "泰国": "#566573", "东帝汶": "#8D6E63", "菲律宾": "#000000",
}
MARK = {
    "柬埔寨": "o", "老挝": "s", "越南": "^", "缅甸": "D", "马来西亚": "v",
    "印度尼西亚": "P", "文莱": "X", "新加坡": "*", "泰国": "h", "东帝汶": "<", "菲律宾": "o",
}

TIERS = [
    (-9, -6, "对抗", "#EFA9A9"), (-6, -3, "紧张", "#F7CFCB"),
    (-3, 0, "不和", "#FBE6C8"), (0, 3, "普通", "#EDF1F3"),
    (3, 6, "良好", "#DCEFE3"), (6, 9, "友好", "#C4E3CE"),
]

C = {c["name"]: c["scores"] for c in D["countries"]}
ORDER = sorted(C.keys(), key=lambda k: -C[k][-1])


def bands(ax, lo=-9, hi=9, label=True, x0=0.55, x1=8.62):
    for a, b, nm, col in TIERS:
        if b <= lo or a >= hi:
            continue
        aa, bb = max(a, lo), min(b, hi)
        ax.add_patch(Rectangle((x0, aa), x1 - x0, bb - aa, facecolor=col,
                               alpha=.55, edgecolor="none", zorder=0))
        if label and (bb - aa) > 1.2:
            ax.text(x1 - .06, (aa + bb) / 2, nm, ha="right", va="center",
                    fontproperties=F(11), color="#5a5a5a", alpha=.95, zorder=1)
    for a, b, nm, col in TIERS:
        if lo < a < hi:
            ax.axhline(a, color="#ffffff", lw=1.1, zorder=1)


def spread(pairs, gap):
    """右侧标签防重叠：pairs=[(y, name)]，返回 {name: y_adj}"""
    ps = sorted(pairs, key=lambda t: t[0])
    ys = [p[0] for p in ps]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < gap:
            ys[i] = ys[i - 1] + gap
    return {ps[i][1]: ys[i] for i in range(len(ps))}


def draw(ax, names, ylo, yhi, lw=2.2, ms=6, labels=True, gap=None):
    bands(ax, ylo, yhi, label=labels)
    for n in names:
        y = C[n]
        ax.plot(MONTHS, y, color=COLORS[n], marker=MARK[n], lw=lw,
                ms=ms if n != "新加坡" else ms + 3, markerfacecolor="white",
                markeredgewidth=1.7, zorder=5,
                linestyle="--" if n == "菲律宾" else "-")
    if labels:
        adj = spread([(C[n][-1], n) for n in names], gap or (yhi - ylo) * .052)
        for n in names:
            ax.text(8.16, adj[n], f"{n} {C[n][-1]:+.1f}", color=COLORS[n],
                    fontproperties=F(11.5, "bold"), va="center", zorder=6)
    ax.set_xlim(.55, 8.62)
    ax.set_ylim(ylo, yhi)
    ax.set_xticks(MONTHS)
    ax.set_xticklabels(XLAB, fontproperties=F(12))
    for t in ax.get_yticklabels():
        t.set_fontproperties(F(11))
    ax.grid(axis="x", color="#ffffff", lw=.9, zorder=1)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#c8c8c8")
    ax.spines["bottom"].set_color("#c8c8c8")


# ================= 主图（三面板） =================
fig = plt.figure(figsize=(15.2, 11.6), facecolor="white")
gs = gridspec.GridSpec(2, 2, height_ratios=[1.32, 1], width_ratios=[1.18, 1],
                       hspace=.30, wspace=.20,
                       left=.055, right=.845, top=.885, bottom=.075)

fig.text(.055, .955, "中国—东盟11国双边关系量化评分", fontproperties=F(27, "bold"), color="#1a1a1a")
fig.text(.055, .925, "2026年1月—8月  月度折线图   （量表 -9 ~ +9，8月数据截至8月6日）",
         fontproperties=F(14), color="#666666")

# --- 面板1：全景 ---
ax1 = fig.add_subplot(gs[0, :])
draw(ax1, ORDER, -9, 9, lw=2.0, ms=5.4, gap=.62)
ax1.set_title("① 全景：11国同轴对比", fontproperties=F(15, "bold"), loc="left", pad=10, color="#222")
ax1.set_ylabel("关系分值", fontproperties=F(12.5))
ax1.axhline(0, color="#9e9e9e", lw=1.3, ls=":", zorder=2)
ax1.set_yticks(range(-9, 10, 3))

# --- 面板2：友善区放大 ---
FRIENDLY = [n for n in ORDER if n != "菲律宾"]
ax2 = fig.add_subplot(gs[1, 0])
draw(ax2, FRIENDLY, 4.6, 9.0, lw=2.1, ms=5.6, gap=.29)
ax2.set_title("② 放大：10个「友善」国家（4.6 ~ 9.0）", fontproperties=F(14, "bold"), loc="left", pad=9, color="#222")
ax2.set_yticks([5, 6, 7, 8, 9])
ax2.annotate("苏林国事访华\n发表联合声明", xy=(4, 8.3), xytext=(2.35, 8.72),
             fontproperties=F(9.6), color="#B7950B", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B7950B", lw=1.2))
ax2.annotate("洪森访华 / 习近平会见", xy=(6, 8.6), xytext=(4.6, 5.55),
             fontproperties=F(9.6), color="#C0392B", ha="center",
             arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.2))
ax2.annotate("习近平—敏昂莱会谈\n中缅命运共同体联合声明", xy=(6, 7.6), xytext=(6.55, 4.98),
             fontproperties=F(9.6), color="#1E8449", ha="center",
             arrowprops=dict(arrowstyle="->", color="#1E8449", lw=1.2))
ax2.annotate("李显龙访华", xy=(5, 6.8), xytext=(3.1, 6.35),
             fontproperties=F(9.6), color="#D81B60", ha="center",
             arrowprops=dict(arrowstyle="->", color="#D81B60", lw=1.2))
ax2.annotate("阿努廷总理访华\n命运共同体联合声明", xy=(7, 7.3), xytext=(6.3, 5.5),
             fontproperties=F(9.6), color="#566573", ha="center",
             arrowprops=dict(arrowstyle="->", color="#566573", lw=1.2))

# --- 面板3：菲律宾 ---
ax3 = fig.add_subplot(gs[1, 1])
bands(ax3, -7.2, -3.0, label=True, x1=8.62)
ax3.plot(MONTHS, C["菲律宾"], color="#000000", marker="o", lw=3.0, ms=8,
         markerfacecolor="white", markeredgewidth=2.1, zorder=5)
for x, y in zip(MONTHS, C["菲律宾"]):
    ax3.text(x, y + .17, f"{y:+.1f}", ha="center", fontproperties=F(9.6, "bold"), color="#000")
ax3.set_xlim(.55, 8.62); ax3.set_ylim(-7.2, -3.0)
ax3.set_xticks(MONTHS); ax3.set_xticklabels(XLAB, fontproperties=F(12))
ax3.set_yticks([-7, -6, -5, -4])
for t in ax3.get_yticklabels():
    t.set_fontproperties(F(11))
ax3.grid(axis="x", color="#fff", lw=.9, zorder=1)
for s in ("top", "right"):
    ax3.spines[s].set_visible(False)
ax3.spines["left"].set_color("#c8c8c8"); ax3.spines["bottom"].set_color("#c8c8c8")
ax3.set_title("③ 放大：菲律宾（唯一负分国）", fontproperties=F(14, "bold"), loc="left", pad=9, color="#222")
ax3.annotate("美菲「肩并肩-2026」军演\n日本部队首次进驻", xy=(4, -5.2), xytext=(2.5, -6.35),
             fontproperties=F(9.6), color="#7B1FA2", ha="center",
             arrowprops=dict(arrowstyle="->", color="#7B1FA2", lw=1.2))
ax3.annotate("向联合国提交\n所谓「黄岩岛领海基线」", xy=(7, -5.5), xytext=(5.6, -3.72),
             fontproperties=F(9.6), color="#B71C1C", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.2))
ax3.annotate("8·1 四线反制\n跌入「对抗」区间", xy=(8, -6.4), xytext=(7.0, -6.95),
             fontproperties=F(9.8, "bold"), color="#B71C1C", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.3))

# --- 右侧图例：六等级 ---
lx, ly = .862, .70
fig.text(lx, ly + .175, "六等级量表", fontproperties=F(13, "bold"), color="#222")
rows = [("友好", "6 ~ 9", "#C4E3CE"), ("良好", "3 ~ 6", "#DCEFE3"), ("普通", "0 ~ 3", "#EDF1F3"),
        ("不和", "-3 ~ 0", "#FBE6C8"), ("紧张", "-6 ~ -3", "#F7CFCB"), ("对抗", "-9 ~ -6", "#EFA9A9")]
cats = ["友善", "", "非敌非友", "", "敌对", ""]
for i, (nm, rg, col) in enumerate(rows):
    yy = ly + .138 - i * .0275
    fig.patches.append(Rectangle((lx, yy - .008), .022, .019, transform=fig.transFigure,
                                 facecolor=col, edgecolor="#bbb", lw=.6))
    fig.text(lx + .028, yy, nm, fontproperties=F(11, "bold"), va="center", color="#333")
    fig.text(lx + .062, yy, rg, fontproperties=F(10), va="center", color="#777")
fig.text(lx, ly - .045, "三大类别\n友善 ＋ / 非敌非友 / 敌对 -", fontproperties=F(10), color="#888", va="top")

fig.text(.055, .028,
         "方法：参照清华大学阎学通团队《中外关系定量衡量》体系。以结构性关系水平为基线，按当月公开外交事件的性质、层级（元首＞部长＞司局＞民间）与领域加权增减，"
         "并施加向基线回归的衰减。元首级互访 ±0.5~0.9，部长级机制性会议 ±0.2~0.5，重大协议签署 ±0.3~0.6，军事对峙／法理挑衅 -0.5~-1.2。",
         fontproperties=F(9.6), color="#8a8a8a")
fig.text(.055, .006,
         "资料来源：中国外交部、中国常驻东盟使团、新华社／人民日报／中国政府网、中央广播电视总台，及各国官方通稿与主流媒体。* 8月数据截至2026年8月6日。分值为基于公开信息的学术性研究判断，非官方数据。",
         fontproperties=F(9.6), color="#8a8a8a")

p1 = os.path.join(OUT, "china-asean-relations-2026.jpg")
fig.savefig(p1, format="jpg", dpi=200, facecolor="white", pil_kwargs={"quality": 94})
print("saved", p1)
plt.close(fig)

# ================= 简版：单张全景折线图 =================
fig2, ax = plt.subplots(figsize=(14.2, 8.4), facecolor="white")
fig2.subplots_adjust(left=.062, right=.845, top=.855, bottom=.135)
draw(ax, ORDER, -9, 9, lw=2.4, ms=6.2, gap=.60)
ax.axhline(0, color="#9e9e9e", lw=1.3, ls=":", zorder=2)
ax.set_yticks(range(-9, 10, 3))
ax.set_ylabel("关系分值", fontproperties=F(13))
fig2.text(.062, .945, "中国—东盟11国双边关系量化评分（2026年1—8月）",
          fontproperties=F(24, "bold"), color="#1a1a1a")
fig2.text(.062, .905, "六等级量表：友好6~9 · 良好3~6 · 普通0~3 · 不和-3~0 · 紧张-6~-3 · 对抗-9~-6　|　8月数据截至8月6日",
          fontproperties=F(13), color="#666")
fig2.text(.062, .035,
          "方法：参照阎学通团队《中外关系定量衡量》体系，按公开外交事件性质／层级／领域加权月度赋分。"
          "来源：中国外交部、常驻东盟使团、新华社、人民日报、中国政府网、总台及各国官方通稿。分值为研究判断，非官方数据。",
          fontproperties=F(10), color="#8a8a8a")
p2 = os.path.join(OUT, "china-asean-relations-2026-simple.jpg")
fig2.savefig(p2, format="jpg", dpi=200, facecolor="white", pil_kwargs={"quality": 94})
print("saved", p2)
