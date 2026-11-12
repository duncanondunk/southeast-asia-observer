#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配图唯一性门禁（防止文章配图重复 / 高度相似）

背景 / 根因
----------
自动化写稿的配图规则依赖图库搜索页取直链，而这些通道已被反爬或网络不可达。
取图失败时旧规则只说「退而求其次选一张东南亚城市或自然风光的横版图」，
既没有唯一性约束，也没有发布前校验，于是每天退化到同一个固定 Unsplash ID，
另存为各篇自己的路径 —— 路径全不同、字节全相同，形成大量「隐形重复」。

本脚本提供两道防线：
  1) --check  纯本地扫描，发布前门禁。发现精确重复或高度相似即退出码 1，
              自动化应在 git commit 之前调用，失败则换图或终止发布。
  2) --fix    对重复/相似的文章重新分配全局唯一图片（Pexels CDN 直链），
              保留 image 路径不变，只覆盖文件并更新 imageCredit。

判定口径
--------
  精确重复：文件 md5 相同（同一张图另存为不同文件名）
  高度相似：dHash 感知哈希汉明距离 <= SIM_THRESHOLD（同图不同压缩/裁剪/尺寸）

用法
----
  python scripts/ensure_unique_images.py --check     # 门禁，不联网，退出码 1 表示不通过
  python scripts/ensure_unique_images.py --fix                 # 修复（需外网，images.pexels.com）
  python scripts/ensure_unique_images.py --fix --limit 15      # 分批修，幂等可重复跑
  python scripts/ensure_unique_images.py --check --json        # 机器可读输出

注意
----
  - --fix 的外网下载必须在允许直连外网的环境执行（沙箱内 curl 会返回 0 字节）。
  - 串行下载：曾有 8 线程并发导致 ID 竞态复用的事故，这里刻意不用并发。
  - 分配新图时同时校验 md5 未出现、且与所有现存图的 dHash 距离均超过阈值，
    避免「新图碰巧撞上仓库里已有的图」。
  - 图源历史：picsum.photos 于 2026-11-13 实测已不可达（HTTP 000），
    改用 images.pexels.com CDN 数字 ID 直链（实测连续 ID 命中率 100%）。
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES_JSON = os.path.join(ROOT, 'data', 'articles.json')
IMAGE_DIR = os.path.join(ROOT, 'images', 'articles')
SIM_THRESHOLD = 6          # dHash 汉明距离阈值，<= 视为高度相似
PEXELS_URL = ('https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg'
              '?auto=compress&cs=tinysrgb&w=1600&h=1067&fit=crop')
PEXELS_START = 32327749    # 起点，+1 后落入实测 100% 命中的连续 ID 段
MAX_TRY = 120              # 单篇最多尝试的 ID 数

CREDIT_TPL = 'Pexels (pexels.com/photos/{pid})'


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, '/')


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def dhash(path, size=8):
    """差值感知哈希：对同图不同压缩/尺寸鲁棒"""
    if Image is None:
        return None
    try:
        im = Image.open(path).convert('L').resize((size + 1, size), Image.LANCZOS)
        px = list(im.tobytes())   # L 模式每像素 1 字节，避免已弃用的 getdata()
        bits = []
        for r in range(size):
            for c in range(size):
                bits.append(1 if px[r * (size + 1) + c] > px[r * (size + 1) + c + 1] else 0)
        return int(''.join(map(str, bits)), 2)
    except Exception:
        return None


def hamming(a, b):
    return bin(a ^ b).count('1') if a is not None and b is not None else 999


def load_articles():
    with open(ARTICLES_JSON, encoding='utf-8') as f:
        return json.load(f)


def collect():
    """返回 (entries, missing)
    entries: [{slug, path, abs, md5, dhash, category}]
    """
    entries, missing = [], []
    for a in load_articles():
        img = a.get('image')
        if not img:
            continue
        ab = img if os.path.isabs(img) else os.path.join(ROOT, img)
        if not os.path.exists(ab):
            missing.append((a.get('slug'), img))
            continue
        entries.append({
            'slug': a.get('slug'),
            'path': img,
            'abs': ab,
            'md5': md5(ab),
            'dhash': dhash(ab),
            'category': a.get('category', ''),
        })
    return entries, missing


def all_image_files():
    """所有磁盘图片（含未被 articles.json 引用的），用于分配新图时避免撞车"""
    out = []
    for fn in os.listdir(IMAGE_DIR):
        if fn.lower().endswith('.jpg'):
            out.append(os.path.join(IMAGE_DIR, fn))
    return sorted(out)


def scan():
    entries, missing = collect()
    exact = {}
    for e in entries:
        exact.setdefault(e['md5'], []).append(e)
    exact_dups = {k: v for k, v in exact.items() if len(v) > 1}

    # 相似检测：只在 md5 不同的配对之间比较 dHash（O(n^2)，n≈360 可接受）
    similar = []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if a['md5'] == b['md5']:
                continue
            if hamming(a['dhash'], b['dhash']) <= SIM_THRESHOLD:
                similar.append((a, b, hamming(a['dhash'], b['dhash'])))
    return entries, missing, exact_dups, similar


def report(entries, missing, exact_dups, similar, as_json=False):
    if as_json:
        print(json.dumps({
            'articles_with_image': len(entries),
            'missing_files': [{'slug': s, 'path': p} for s, p in missing],
            'exact_groups': [
                {'count': len(v), 'slugs': [x['slug'] for x in v],
                 'categories': sorted({x['category'] for x in v})}
                for v in exact_dups.values()],
            'similar_pairs': [
                {'a': a['slug'], 'b': b['slug'], 'distance': d}
                for a, b, d in similar],
        }, ensure_ascii=False, indent=2))
        return

    print(f"配图唯一性检查：{len(entries)} 篇有图")
    print(f"  文件缺失            : {len(missing)}")
    print(f"  精确重复组(md5)     : {len(exact_dups)}  涉及 {sum(len(v) for v in exact_dups.values())} 篇")
    print(f"  高度相似对(dHash<= {SIM_THRESHOLD}) : {len(similar)}")

    bycat = {}
    for k, v in exact_dups.items():
        for x in v:
            bycat[x['category']] = bycat.get(x['category'], 0) + 1
    if bycat:
        print("  精确重复按板块:", dict(sorted(bycat.items(), key=lambda x: -x[1])))

    for k, v in sorted(exact_dups.items(), key=lambda x: -len(x[1]))[:12]:
        cats = sorted({x['category'] for x in v})
        print(f"    {len(v)} 篇 | {v[0]['path']} | 板块 {cats}")
        print(f"        {[x['slug'] for x in v][:6]}{' ...' if len(v) > 6 else ''}")
    for s, p in missing[:5]:
        print(f"    [缺失] {s} -> {p}")
    for a, b, d in similar[:8]:
        print(f"    [相似 d={d}] {a['slug']}  <->  {b['slug']}")


def used_pexels_ids():
    """收集仓库里已用过的 Pexels photo ID，避免重复分配"""
    import re
    ids = set()
    txt = open(ARTICLES_JSON, encoding='utf-8').read()
    for pat in (r'pexels-photo-(\d+)', r'pexels\.com/photos/(\d+)', r'pexels-[a-z-]+-(\d+)\.jpg'):
        ids.update(int(x) for x in re.findall(pat, txt))
    return ids


def fetch_unique(dest, taken_md5, taken_dhash, used_ids, start_id):
    """串行挑一个全局唯一的 Pexels 图写入 dest，返回 pid 或 None"""
    tried = 0
    pid = start_id
    while tried < MAX_TRY:
        pid += 1
        tried += 1
        if pid in used_ids:
            continue
        url = PEXELS_URL.format(pid=pid)
        try:
            r = subprocess.run(
                ['curl', '-sL', '--max-time', '10', '-o', dest + '.tmp', '-w', '%{http_code}', url],
                capture_output=True, text=True, timeout=14)
        except subprocess.TimeoutExpired:
            continue
        if r.returncode != 0 or r.stdout.strip() != '200':
            continue
        tmp = dest + '.tmp'
        if not os.path.exists(tmp) or os.path.getsize(tmp) < 8000:
            continue
        try:
            if Image is not None:
                with Image.open(tmp) as im:
                    if im.format != 'JPEG' or im.width <= im.height:
                        continue
        except Exception:
            continue
        h = md5(tmp)
        dh = dhash(tmp)
        if h in taken_md5:
            continue
        if any(hamming(dh, x) <= SIM_THRESHOLD for x in taken_dhash):
            continue
        os.replace(tmp, dest)
        used_ids.add(pid)
        taken_md5.add(h)
        taken_dhash.append(dh)
        return pid
    return None


def update_credit(slug, pid):
    """只改该篇文章的 imageCredit 行，避免整文件重写产生巨大 diff"""
    lines = open(ARTICLES_JSON, encoding='utf-8').read().split('\n')
    key = '"slug": "%s"' % slug
    start = None
    for i, l in enumerate(lines):
        if key in l:
            start = i
            break
    if start is None:
        return False
    import re
    for i in range(start, min(start + 60, len(lines))):
        if lines[i].lstrip().startswith('"imageCredit"'):
            lines[i] = re.sub(r'("imageCredit"\s*:\s*").*?("\s*,?\s*)$',
                              lambda m: m.group(1) + CREDIT_TPL.format(pid=pid) + m.group(2),
                              lines[i])
            open(ARTICLES_JSON, 'w', encoding='utf-8').write('\n'.join(lines))
            return True
    return False


def clusters(entries, exact_dups, similar):
    """连通分量聚类：md5 相同或 dHash 相近的文章归入同一簇，每簇只保留第 1 篇。

    不能只按「两两配对修后者」处理 —— 同一张图被多次重压缩时会被拆成多个
    md5 组，两两配对会在簇里留下多篇。并查集保证每簇恰好保留一篇。
    """
    n = len(entries)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    idx = {e['slug']: i for i, e in enumerate(entries)}
    for v in exact_dups.values():
        for x in v[1:]:
            union(idx[v[0]['slug']], idx[x['slug']])
    for a, b, d in similar:
        union(idx[a['slug']], idx[b['slug']])

    groups = {}
    for i, e in enumerate(entries):
        groups.setdefault(find(i), []).append(e)
    return [g for g in groups.values() if len(g) > 1]


def fix(limit=None):
    entries, missing, exact_dups, similar = scan()
    groups = clusters(entries, exact_dups, similar)
    targets = [e for g in groups for e in g[1:]]   # 保留每簇第一篇
    total = len(targets)
    if limit:
        targets = targets[:limit]
    print(f"重复/相似簇 {len(groups)} 个，待修复 {total} 篇"
          f"（本次处理 {len(targets)} 篇，最大簇 {max((len(g) for g in groups), default=0)} 篇）")

    # 全局已占用集合（含孤儿文件与所有文章图）
    files = all_image_files()
    taken_md5 = {md5(f) for f in files}
    taken_dhash = [d for d in (dhash(f) for f in files) if d is not None]
    used_ids = used_pexels_ids()
    start = PEXELS_START

    ok, fail = 0, []
    for idx, e in enumerate(targets, 1):
        pid = fetch_unique(e['abs'], taken_md5, taken_dhash, used_ids, start)
        start = pid or start
        if pid is None:
            fail.append(e['slug'])
            print(f"  [{idx}/{len(targets)}] FAIL {e['slug']}")
            continue
        update_credit(e['slug'], pid)
        ok += 1
        if idx % 10 == 0 or idx == len(targets):
            print(f"  [{idx}/{len(targets)}] ok={ok} fail={len(fail)}")

    print(f"\n本次完成：成功 {ok} 篇，失败 {len(fail)} 篇")
    if fail:
        print("  失败 slug:", fail)
    # 复验（分批时仍有剩余属正常，最终用 --check 做门禁判定）
    e2, m2, d2, s2 = scan()
    print(f"复验：精确重复组 {len(d2)} | 相似对 {len(s2)} | 缺失 {len(m2)}")
    return 1 if fail else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--fix', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--limit', type=int, default=None,
                    help='每批最多处理篇数；fix 幂等，可分多次跑完')
    args = ap.parse_args()
    if args.fix:
        return fix(args.limit)
    entries, missing, exact_dups, similar = scan()
    report(entries, missing, exact_dups, similar, args.json)
    bad = bool(missing or exact_dups or similar)
    if args.check and bad:
        print("\n门禁未通过：存在缺失 / 精确重复 / 高度相似配图")
        return 1
    if args.check:
        print("\n门禁通过：所有配图唯一且无高度相似")
    return 0


if __name__ == '__main__':
    sys.exit(main())
