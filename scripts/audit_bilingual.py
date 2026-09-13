#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双语站点全面审查：articles.json + articles/*.md + *.html
输出：.workbuddy/audit/issues.json  + 控制台分类摘要
"""
import json, re, sys, os
from html.parser import HTMLParser
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.workbuddy' / 'audit'
OUT.mkdir(parents=True, exist_ok=True)

issues = []

def add(module, location, itype, current, suggestion, severity, note=''):
    issues.append(dict(module=module, location=location, type=itype,
                       current=(current or '')[:300], suggestion=suggestion,
                       severity=severity, note=note))

CJK_RE = re.compile(r'[\u4e00-\u9fff]')
# 仅中文专属标点（引号 “”‘’ 英文排版亦用，不算问题）
CN_PUNCT = '，。；：？！、（）《》【】～'
def cn_chars(s): return len(CJK_RE.findall(s))
def en_words(s): return len([w for w in re.split(r'\s+', (s or '').strip()) if w])

# ---------------- 1. articles.json ----------------
def check_articles_json():
    data = json.loads((ROOT/'data'/'articles.json').read_text(encoding='utf-8'))
    cat_map = {}
    for i, a in enumerate(data):
        slug = a.get('slug', f'#{i}'); loc = f'{slug}'
        en = a.get('en')
        if not en:
            add('articles.json', loc, '漏译(缺少 en 对象)', '-', '补齐 en 双语对象', '高'); continue
        for f in ('title','subtitle','summary','imageAlt','category','country'):
            if not (en.get(f) or '').strip():
                add('articles.json', loc, '漏译(en 字段为空)', f'en.{f} 为空', f'补 en.{f}', '高')
        zs, es = a.get('summary','') or '', en.get('summary','') or ''
        if cn_chars(zs) > 150:
            add('articles.json', loc, '体例(中文摘要超长)', f'{cn_chars(zs)} 字：{zs[:70]}', '≤150 字，精简核心论点', '中')
        if en_words(es) > 100:
            add('articles.json', loc, '体例(英文摘要超长)', f'{en_words(es)} 词：{es[:70]}', '≤100 词，精简', '中')
        if a.get('references') and en.get('references') and a['references'] != en['references']:
            add('articles.json', loc, '中英不同步(references·可能有意分源)', f'CN={a["references"]} EN={en["references"]}', '若非有意分源则统一；有意分源（中文源/英文源）可保留', '低')
        for f in ('title','subtitle','summary','imageAlt'):
            v = en.get(f) or ''
            hits = sorted(set(c for c in v if c in CN_PUNCT))
            if hits:
                add('articles.json', loc, '标点(英文段含中文标点)', f'en.{f} 含 {"".join(hits)}：{v[:60]}', '英文段改用半角标点', '中')
        for f in ('title','subtitle','summary'):
            v = a.get(f) or ''
            if re.search(r'[\u4e00-\u9fff][,;:?!](?=[\u4e00-\u9fff]|$)', v):
                add('articles.json', loc, '标点(中文段半角标点)', f'{f}：{v[:60]}', '中文语境改全角标点', '低')
        # category 中英映射
        c, ec = a.get('category'), en.get('category')
        if c and ec: cat_map.setdefault(c, Counter())[ec] += 1
        # image 与 imageCredit
        if not a.get('image'):
            add('articles.json', loc, '体例(缺题图)', 'image 为空', '按配图规范补 images/articles/{slug}.jpg', '中')
        if not a.get('imageCredit'):
            add('articles.json', loc, '体例(缺图源标注)', 'imageCredit 为空', '补 Pexels/Unsplash 来源', '低')
    return cat_map, data

# ---------------- 2. md 正文 ----------------
# 仅匹配“金额型”外币：中文段需数字/数量词紧邻货币名；英文段需符号+数字 或 数字+货币名
CN_CURRENCY = r'(美元|美金|新元|新台币|林吉特|泰铢|越南盾|印尼盾|比索|欧元|英镑|日元|日圆|港元|澳元|卢比|瑞尔|缅元|令吉|盾)'
CN_AMT = re.compile(r'([\d\.,]+\s*(?:万亿|亿|万|千)?|数[十百千万]|[一二三四五六七八九十百千]+)\s*' + CN_CURRENCY)
EN_AMT = re.compile(
    r'(?<![A-Za-z])(?:S\$|RM|฿|₫|Rp|₱|€|£|NT\$|A\$|C\$|HK\$|₩)\s?\d[\d,\.]*'
    r'|\b\d[\d,\.]*\s*(?:trillion|billion|million|thousand)?\s*(?:rupiah|baht|ringgit|dong|pesos?|euros?|yen|won)\b',
    re.I)
UNIT_CN = r'(平方公里|平方千米|公顷|英亩|平方英里|公里|千米|英里|米|万吨|吨|公斤|磅|海里)'

def cn_nums(s):
    out = []
    for m in re.finditer(r'([\d\.,]+)\s*(万亿|亿|万)', s):
        try: f = float(m.group(1).replace(',', ''))
        except ValueError: continue
        out.append(f * {'万': 1e4, '亿': 1e8, '万亿': 1e12}[m.group(2)])
    for m in re.finditer(r'([\d,]{5,})', s):
        try: out.append(float(m.group(1).replace(',', '')))
        except ValueError: pass
    return [x for x in out if x >= 1000 and not (1900 <= x <= 2100 and float(x).is_integer())]

def en_nums(s):
    out = []
    for m in re.finditer(r'([\d\.,]+)\s*(trillion|billion|million|thousand)', s, re.I):
        try: f = float(m.group(1).replace(',', ''))
        except ValueError: continue
        out.append(f * {'thousand': 1e3, 'million': 1e6, 'billion': 1e9, 'trillion': 1e12}[m.group(2).lower()])
    for m in re.finditer(r'([\d,]{5,})', s):
        try: out.append(float(m.group(1).replace(',', '')))
        except ValueError: pass
    return [x for x in out if x >= 1000 and not (1900 <= x <= 2100 and float(x).is_integer())]

def check_md():
    files = sorted((ROOT/'articles').glob('*.md'))
    stats = []
    for p in files:
        name = p.name
        try: txt = p.read_text(encoding='utf-8')
        except Exception as e:
            add('articles/*.md', name, '读取失败', str(e), '检查编码', '高'); continue
        parts = txt.split('===EN===')
        if len(parts) != 2:
            add('articles/*.md', name, '结构(===EN=== 分割异常)', f'分隔数={len(parts)-1}',
                '规范：中文版 → 空行 → ===EN=== → 空行 → 英文版', '高')
            continue
        zh, en = parts[0], parts[1]
        if '===EN===' not in txt: pass
        # 分隔符是否独占行
        for m in re.finditer(r'^.*===EN===.*$', txt, re.M):
            if m.group(0).strip() != '===EN===':
                add('articles/*.md', name, '结构(===EN=== 未独占行)', m.group(0).strip()[:60], '===EN=== 单独成行', '中')
                break
        zc, ew = cn_chars(zh), en_words(en)
        ratio = (zc/ew) if ew else 99
        stats.append((name, zc, ew, ratio))
        if ew and ratio < 1.2:
            add('articles/*.md', name, '中英不同步(字数比过低)', f'中文 {zc} 字 / 英文 {ew} 词 = {ratio:.2f}（规范 1.5–1.8，下限 1.2）',
                '英文过长或中文过短，补充中文或精简英文', '中')
        elif ew and ratio > 1.95:
            add('articles/*.md', name, '中英不同步(字数比过高)', f'中文 {zc} 字 / 英文 {ew} 词 = {ratio:.2f}',
                '中文偏多（可能摘要式压缩英文）或英文漏译', '中')
        # 小节数
        zsec = re.findall(r'^##\s+(.+)$', zh, re.M)
        esec = re.findall(r'^##\s+(.+)$', en, re.M)
        if len(zsec) != len(esec):
            add('articles/*.md', name, '中英不同步(小节数不等)',
                f'中文 {len(zsec)} 节 / 英文 {len(esec)} 节；CN={zsec[:4]} EN={esec[:4]}',
                '中英小节一一对应，补齐或合并', '高')
        # 延伸阅读 / Further reading
        zfr = '延伸阅读' in zh
        efr = re.search(r'Further reading', en, re.I)
        if zfr != bool(efr):
            add('articles/*.md', name, '体例(延伸阅读缺一方)',
                f'中文延伸阅读={zfr} / 英文 Further reading={bool(efr)}',
                '双语均需延伸阅读（中文 ## 延伸阅读 / 英文 ## Further reading）', '中')
        # 延伸阅读条数
        m = re.search(r'##\s*延伸阅读(.*?)(?=\n##|\*话题参考|\Z)', zh, re.S)
        if m:
            n = len(re.findall(r'^\s*[-*]?\s*\*\*', m.group(1), re.M)) or len(re.findall(r'^\s*[-*]\s+', m.group(1), re.M))
            if n > 3:
                add('articles/*.md', name, '体例(延伸阅读超 3 条)', f'{n} 条', '≤3 条', '低')
        m = re.search(r'##\s*Further reading(.*?)(?=\n##|\*Topic reference|\Z)', en, re.S)
        if m:
            n = len(re.findall(r'^\s*[-*]\s+', m.group(1), re.M))
            if n and n > 3:
                add('articles/*.md', name, '体例(Further reading 超 3 条)', f'{n} 条', '≤3 条', '低')
        # 话题参考
        if '话题参考' not in zh and 'mekong-drought-floods' not in name:
            add('articles/*.md', name, '体例(缺中文话题参考)', '未找到“话题参考”', '文末补 *话题参考：…*', '中')
        if not re.search(r'Topic reference', en) and 'mekong-drought-floods' not in name:
            add('articles/*.md', name, '体例(缺英文 Topic reference)', '未找到 Topic reference', '文末补 *Topic reference: …*', '中')
        # 正文禁用 ![...]
        for seg, tag in ((zh,'中文段'), (en,'英文段')):
            for mm in re.finditer(r'!\[[^\]]*\]\([^)]*\)', seg):
                add('articles/*.md', name, f'体例({tag}含 Markdown 图片语法)', mm.group(0)[:80],
                    '正文 md 不写 ![...]，题图走 a.image 元数据', '中')
        # 英文段中文标点
        hits = sorted(set(c for c in en if c in CN_PUNCT))
        if hits:
            add('articles/*.md', name, '标点(英文段含中文标点)', f'含 {"".join(hits)}（出现 {sum(en.count(c) for c in hits)} 次）',
                '英文段统一半角标点', '中')
        # 中文段半角标点（句末）
        bad = re.findall(r'[\u4e00-\u9fff][,;:?!](?=[\s\u4e00-\u9fff]|$)', zh)
        if len(bad) >= 3:
            add('articles/*.md', name, '标点(中文段半角标点)', f'疑似 {len(bad)} 处，如 …{zh[max(0,zh.find(bad[0])-15):zh.find(bad[0])+10]}…',
                '中文语境改全角，。；：？！', '低')
        # 数字/换算：中文段外币金额未加注人民币
        for mm in CN_AMT.finditer(zh):
            ctx = zh[max(0, mm.start()-70):mm.start()+90]
            if '人民币' in ctx or '（约' in ctx or '(约' in ctx or '折合' in ctx:
                continue
            add('articles/*.md', name, '数字/换算(中文段外币金额未加注人民币)',
                f'“{mm.group(0).strip()}” 上下文：…{ctx.strip()[:120]}…',
                '非人民币外币需括号加注人民币（发布当日中间价，用“约”）', '高')
            break
        # 英文段非美元外币未加注美元
        for mm in EN_AMT.finditer(en):
            if re.match(r'\s*US\$', mm.group(0)): continue
            ctx = en[max(0, mm.start()-70):mm.start()+90]
            if re.search(r'US\$|USD|about \$|~\$', ctx): continue
            add('articles/*.md', name, '数字/换算(英文段非美元外币未加注美元)',
                f'“{mm.group(0).strip()}” 上下文：…{ctx.strip()[:120]}…',
                '非美元外币需加注 ~US$…（发布当日中间价）', '高')
            break
        # 数字自洽（中英数值集合比对，提示性）
        cz, ce = cn_nums(zh), en_nums(en)
        if cz and ce and len(cz) <= 12 and len(ce) <= 12:
            def miss(a, b):
                return [x for x in a if not any(abs(x-y) <= max(1, abs(x)*0.02) for y in b)]
            m1, m2 = miss(cz, ce), miss(ce, cz)
            if len(m1) + len(m2) >= 2:
                add('articles/*.md', name, '数字/自洽(中英数值集合不匹配·待人工确认)',
                    f'中文 {[f"{x:g}" for x in cz[:6]]} vs 英文 {[f"{x:g}" for x in ce[:6]]}；中文独有 {[f"{x:g}" for x in m1[:4]]}，英文独有 {[f"{x:g}" for x in m2[:4]]}',
                    '核对是否为同一数据的中英表述（如 1.1万亿 = 1.1 trillion），或一方漏译/改数', '中')
        # 数字与量词空格一致性（中文段）
        with_sp = len(re.findall(r'\d\s+(?:万|亿|吨|元|人|个|年|月|日|%|公里|平方米|公顷)', zh))
        no_sp   = len(re.findall(r'\d(?:万|亿|吨|元|人|个|年|月|日|%|公里|平方米|公顷)', zh))
        stats[-1] = (name, zc, ew, ratio)
    return stats

# ---------------- 3. HTML 静态文案 ----------------
class _BilingualParser(HTMLParser):
    """逐标签检查 data-zh*/data-en* 配对，并找出未被双语属性托管的硬编码中文文本"""
    def __init__(self, fname):
        super().__init__(convert_charrefs=True)
        self.fname = fname
        self.stack = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        d = {k: (v or '') for k, v in attrs}
        self.stack.append((tag, d))
        if tag in ('script', 'style'):
            self.skip += 1
            return
        zs = {k for k in d if k.startswith('data-zh')}
        es = {k for k in d if k.startswith('data-en')}
        line = self.getpos()[0]
        if zs and not es:
            add(self.fname, f'行{line} <{tag}>', '漏译(有 data-zh 无 data-en)',
                f'zh 属性={ {k: d[k][:50] for k in sorted(zs)} }', '补对应 data-en* 属性', '高')
        elif es and not zs:
            add(self.fname, f'行{line} <{tag}>', '多译(有 data-en 无 data-zh)',
                f'en 属性={ {k: d[k][:50] for k in sorted(es)} }', '补对应 data-zh* 属性', '中')
        elif zs and es:
            zsuf = {k[len('data-zh'):] for k in zs}
            esuf = {k[len('data-en'):] for k in es}
            if zsuf != esuf:
                add(self.fname, f'行{line} <{tag}>', '中英不同步(属性变体不匹配)',
                    f'zh 后缀={sorted(zsuf)} en 后缀={sorted(esuf)}', '两侧属性变体一一对应', '中')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.stack.pop()

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip: return
        s = (data or '').strip()
        if not s or len(s) > 150 or not re.search(r'[\u4e00-\u9fff]', s): return
        managed = any(any(k.startswith('data-zh') or k.startswith('data-en') for k in d)
                      for _, d in self.stack)
        if not managed:
            add(self.fname, f'行{self.getpos()[0]} 文本“{s[:40]}”',
                '漏译(硬编码中文，英文版仍显示中文)', s[:110],
                '加 data-zh/data-en 双语属性，或确认该处仅中文语境', '中')


def check_html():
    files = ['index.html', 'about.html', 'article.html', 'hot.html', 'tags.html', 'dashboard.html']
    for f in files:
        p = ROOT / f
        if not p.exists(): continue
        txt = p.read_text(encoding='utf-8')
        _BilingualParser(f).feed(txt)

# ---------------- main ----------------
def main():
    cat_map, data = check_articles_json()
    stats = check_md()
    check_html()
    (OUT/'issues.json').write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding='utf-8')
    # 分类统计
    c = Counter((i['severity'], i['type']) for i in issues)
    print(f'总问题数: {len(issues)}')
    print('\n=== 按严重度 ===')
    for sev in ('高','中','低'):
        n = sum(1 for i in issues if i['severity']==sev)
        print(f'  {sev}: {n}')
    print('\n=== 按类型 ===')
    for (sev, t), n in sorted(c.items(), key=lambda x:(-{'高':3,'中':2,'低':1}[x[0][0]], -x[1])):
        print(f'  [{sev}] {t}: {n}')
    print('\n=== category 中英映射 ===')
    for k, v in cat_map.items():
        print(f'  {k} -> {dict(v)}')
    # 字数比分布
    rs = [r for _,_,_,r in stats if r < 90]
    if rs:
        rs.sort()
        print(f'\n=== 中英字数比分布 ({len(rs)} 篇) ===')
        print(f'  min={rs[0]:.2f}  p10={rs[len(rs)//10]:.2f}  中位={rs[len(rs)//2]:.2f}  p90={rs[len(rs)*9//10]:.2f}  max={rs[-1]:.2f}')
        print(f'  <1.2 的篇数: {sum(1 for r in rs if r<1.2)}   >1.95: {sum(1 for r in rs if r>1.95)}')
    print('\n=== 高严重度明细（前 40） ===')
    for i in [x for x in issues if x['severity']=='高'][:40]:
        print(f"  [{i['module']}] {i['location']}\n     {i['type']}: {i['current'][:150]}")

if __name__ == '__main__':
    main()
