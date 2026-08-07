# -*- coding: utf-8 -*-
"""China-ASEAN 11-country bilateral relations monthly index line chart - ENGLISH (dynamic month count)"""
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

# ---------- font (English-capable) ----------
CAND = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/STHeiti Medium.ttc",
]
CN = None
for p in CAND:
    if os.path.exists(p):
        try:
            fm.fontManager.addfont(p)
            CN = fm.FontProperties(fname=p)
            plt.rcParams["font.family"] = CN.get_name()
            print("font ->", p, "|", CN.get_name())
            break
        except Exception as e:
            print("skip", p, e)
plt.rcParams["axes.unicode_minus"] = False

def F(size, weight="normal"):
    fp = fm.FontProperties(fname=CN.get_file()) if CN else fm.FontProperties()
    fp.set_size(size); fp.set_weight(weight)
    return fp

# ---------- data (supports argv[1] for rolling dataset path) ----------
import sys
_JSON = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "data", "china_asean_scores_2026.json")
with open(_JSON, encoding="utf-8") as f:
    D = json.load(f)

_xm = D["meta"]["months"]
N = len(_xm)
_years = set(m[:4] for m in _xm)
if len(_years) == 1:
    XLAB = [m[5:].lstrip("0") for m in _xm]               # 2026-01 -> Jan
else:
    XLAB = [m[2:] for m in _xm]                           # cross-year -> 26-09
MONTHS = list(range(1, N + 1))
X0, X1 = 0.55, N + 0.62
LBLX = N + 0.16
_last = _xm[-1]

COLORS = {
    "Cambodia": "#C0392B", "Laos": "#E67E22", "Vietnam": "#B7950B", "Myanmar": "#1E8449",
    "Malaysia": "#17A589", "Indonesia": "#2471A3", "Brunei": "#7D3C98",
    "Singapore": "#D81B60", "Thailand": "#566573", "Timor-Leste": "#8D6E63", "Philippines": "#000000",
}
MARK = {
    "Cambodia": "o", "Laos": "s", "Vietnam": "^", "Myanmar": "D", "Malaysia": "v",
    "Indonesia": "P", "Brunei": "X", "Singapore": "*", "Thailand": "h", "Timor-Leste": "<", "Philippines": "o",
}

TIERS = [
    (-9, -6, "Confrontation", "#EFA9A9"), (-6, -3, "Tension", "#F7CFCB"),
    (-3, 0, "Discord", "#FBE6C8"), (0, 3, "Ordinary", "#EDF1F3"),
    (3, 6, "Good", "#DCEFE3"), (6, 9, "Friendly", "#C4E3CE"),
]

C = {c["name_en"]: c["scores"] for c in D["countries"]}
ORDER = sorted(C.keys(), key=lambda k: -C[k][-1])


def bands(ax, lo=-9, hi=9, label=True, x0=0.55, x1=None):
    x1 = X1 if x1 is None else x1
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
                ms=ms if n != "Singapore" else ms + 3, markerfacecolor="white",
                markeredgewidth=1.7, zorder=5,
                linestyle="--" if n == "Philippines" else "-")
    if labels:
        adj = spread([(C[n][-1], n) for n in names], gap or (yhi - ylo) * .052)
        for n in names:
            ax.text(LBLX, adj[n], f"{n} {C[n][-1]:+.1f}", color=COLORS[n],
                    fontproperties=F(11.5, "bold"), va="center", zorder=6)
    ax.set_xlim(X0, X1)
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


# ================= main figure (three panels) =================
fig = plt.figure(figsize=(15.2, 11.6), facecolor="white")
gs = gridspec.GridSpec(2, 2, height_ratios=[1.32, 1], width_ratios=[1.18, 1],
                       hspace=.30, wspace=.20,
                       left=.055, right=.845, top=.885, bottom=.075)

_cov = _xm[0] + " to " + _last
fig.text(.055, .955, "China-ASEAN Bilateral Relations Quantitative Index", fontproperties=F(26, "bold"), color="#1a1a1a")
fig.text(.055, .925, f"{_cov}  |  Monthly line chart  |  Scale -9 to +9",
         fontproperties=F(14), color="#666666")

# panel 1 overview
ax1 = fig.add_subplot(gs[0, :])
draw(ax1, ORDER, -9, 9, lw=2.0, ms=5.4, gap=.62)
ax1.set_title("① Overview: all 11 countries on one axis", fontproperties=F(15, "bold"), loc="left", pad=10, color="#222")
ax1.set_ylabel("Relationship Score", fontproperties=F(12.5))
ax1.axhline(0, color="#9e9e9e", lw=1.3, ls=":", zorder=2)
ax1.set_yticks(range(-9, 10, 3))

# panel 2 friendly zoom
FRIENDLY = [n for n in ORDER if n != "Philippines"]
ax2 = fig.add_subplot(gs[1, 0])
draw(ax2, FRIENDLY, 4.6, 9.0, lw=2.1, ms=5.6, gap=.29)
ax2.set_title("② Zoom: 10 'Amicable' countries (4.6 - 9.0)", fontproperties=F(14, "bold"), loc="left", pad=9, color="#222")
ax2.set_yticks([5, 6, 7, 8, 9])
ax2.annotate("To Lam state visit to China\nJoint statement", xy=(4, 8.3), xytext=(2.3, 8.72),
             fontproperties=F(9.6), color="#B7950B", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B7950B", lw=1.2))
ax2.annotate("Hun Sen visits China /\nXi Jinping meeting", xy=(6, 8.6), xytext=(4.5, 5.55),
             fontproperties=F(9.6), color="#C0392B", ha="center",
             arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.2))
ax2.annotate("Xi-Min Aung Hlaing talks\nChina-Myanmar community statement", xy=(6, 7.6), xytext=(6.55, 4.98),
             fontproperties=F(9.6), color="#1E8449", ha="center",
             arrowprops=dict(arrowstyle="->", color="#1E8449", lw=1.2))
ax2.annotate("Lee Hsien Loong visits China", xy=(5, 6.8), xytext=(3.1, 6.35),
             fontproperties=F(9.6), color="#D81B60", ha="center",
             arrowprops=dict(arrowstyle="->", color="#D81B60", lw=1.2))
ax2.annotate("PM Anutin visits China\nCommunity with Shared Future statement", xy=(7, 7.3), xytext=(6.25, 5.5),
             fontproperties=F(9.6), color="#566573", ha="center",
             arrowprops=dict(arrowstyle="->", color="#566573", lw=1.2))

# panel 3 philippines
ax3 = fig.add_subplot(gs[1, 1])
bands(ax3, -7.2, -3.0, label=True)
ax3.plot(MONTHS, C["Philippines"], color="#000000", marker="o", lw=3.0, ms=8,
         markerfacecolor="white", markeredgewidth=2.1, zorder=5)
for x, y in zip(MONTHS, C["Philippines"]):
    ax3.text(x, y + .17, f"{y:+.1f}", ha="center", fontproperties=F(9.6, "bold"), color="#000")
ax3.set_xlim(X0, X1); ax3.set_ylim(-7.2, -3.0)
ax3.set_xticks(MONTHS); ax3.set_xticklabels(XLAB, fontproperties=F(12))
ax3.set_yticks([-7, -6, -5, -4])
for t in ax3.get_yticklabels():
    t.set_fontproperties(F(11))
ax3.grid(axis="x", color="#fff", lw=.9, zorder=1)
for s in ("top", "right"):
    ax3.spines[s].set_visible(False)
ax3.spines["left"].set_color("#c8c8c8"); ax3.spines["bottom"].set_color("#c8c8c8")
ax3.set_title("③ Zoom: The Philippines (only negative-score country)", fontproperties=F(13.5, "bold"), loc="left", pad=9, color="#222")
ax3.annotate("US-Philippines 'Balikatan 2026'\nJapanese troops deployed for first time", xy=(4, -5.2), xytext=(2.4, -6.35),
             fontproperties=F(9.6), color="#7B1FA2", ha="center",
             arrowprops=dict(arrowstyle="->", color="#7B1FA2", lw=1.2))
ax3.annotate("Submits so-called 'Scarborough Shoal\nterritorial sea baseline' to UN", xy=(7, -5.5), xytext=(5.4, -3.72),
             fontproperties=F(9.6), color="#B71C1C", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.2))
ax3.annotate("Aug 1 four-track countermeasures\nfalls into 'Confrontation' tier", xy=(8, -6.4), xytext=(6.9, -6.95),
             fontproperties=F(9.8, "bold"), color="#B71C1C", ha="center",
             arrowprops=dict(arrowstyle="->", color="#B71C1C", lw=1.3))

# right-side legend: six tiers
lx, ly = .862, .70
fig.text(lx, ly + .175, "Six-Tier Scale", fontproperties=F(13, "bold"), color="#222")
rows = [("Friendly", "6 to 9", "#C4E3CE"), ("Good", "3 to 6", "#DCEFE3"), ("Ordinary", "0 to 3", "#EDF1F3"),
        ("Discord", "-3 to 0", "#FBE6C8"), ("Tension", "-6 to -3", "#F7CFCB"), ("Confrontation", "-9 to -6", "#EFA9A9")]
for i, (nm, rg, col) in enumerate(rows):
    yy = ly + .138 - i * .0275
    fig.patches.append(Rectangle((lx, yy - .008), .022, .019, transform=fig.transFigure,
                                 facecolor=col, edgecolor="#bbb", lw=.6))
    fig.text(lx + .028, yy, nm, fontproperties=F(11, "bold"), va="center", color="#333")
    fig.text(lx + .062, yy, rg, fontproperties=F(10), va="center", color="#777")
fig.text(lx, ly - .045, "Three macro-categories\nAmicable + / Non-aligned / Hostile -", fontproperties=F(10), color="#888", va="top")

fig.text(.055, .028,
         "Method: adapted from the Quantitative Measurement of China's Foreign Relations framework by Prof. Yan Xuetong's team at Tsinghua University. "
         "Taking the structural relationship level as baseline, each month's score is adjusted by the nature, level (head-of-state > minister > director-general > civil society) "
         "and domain of verifiable public diplomatic events, with decay toward baseline. Head-of-state visit +-0.5~0.9; ministerial mechanism +-0.2~0.5; "
         "landmark agreement signing +-0.3~0.6; military standoff / legal provocation -0.5~-1.2.",
         fontproperties=F(9.6), color="#8a8a8a")
fig.text(.055, .006,
         "Sources: China's Ministry of Foreign Affairs, China's Mission to ASEAN, Xinhua / People's Daily / gov.cn, China Media Group, and official releases and major media of each country. "
         "Scores are an academic research assessment based on public information, not official data.",
         fontproperties=F(9.6), color="#8a8a8a")

p1 = os.path.join(OUT, f"china-asean-relations-{_last}-en.jpg")
fig.savefig(p1, format="jpg", dpi=200, facecolor="white", pil_kwargs={"quality": 94})
print("saved", p1)
plt.close(fig)

# ================= simple version =================
fig2, ax = plt.subplots(figsize=(14.2, 8.4), facecolor="white")
fig2.subplots_adjust(left=.062, right=.845, top=.855, bottom=.135)
draw(ax, ORDER, -9, 9, lw=2.4, ms=6.2, gap=.60)
ax.axhline(0, color="#9e9e9e", lw=1.3, ls=":", zorder=2)
ax.set_yticks(range(-9, 10, 3))
ax.set_ylabel("Relationship Score", fontproperties=F(13))
fig2.text(.062, .945, f"China-ASEAN Bilateral Relations Quantitative Index ({_cov})",
          fontproperties=F(24, "bold"), color="#1a1a1a")
fig2.text(.062, .905, "Six-Tier Scale: Friendly 6~9 · Good 3~6 · Ordinary 0~3 · Discord -3~0 · Tension -6~-3 · Confrontation -9~-6",
          fontproperties=F(13), color="#666")
fig2.text(.062, .035,
          "Method: adapted from Prof. Yan Xuetong's team's Quantitative Measurement of China's Foreign Relations; weighted monthly scoring by nature / level / domain of public diplomatic events. "
          "Sources: MFA China, Mission to ASEAN, Xinhua, People's Daily, gov.cn, CMG, and each country's official releases. Scores are a research assessment, not official data.",
          fontproperties=F(10), color="#8a8a8a")
p2 = os.path.join(OUT, f"china-asean-relations-{_last}-en-simple.jpg")
fig2.savefig(p2, format="jpg", dpi=200, facecolor="white", pil_kwargs={"quality": 94})
print("saved", p2)
