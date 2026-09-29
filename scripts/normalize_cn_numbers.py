# -*- coding: utf-8 -*-
r"""把中文段的统计性汉字数字改为阿拉伯数字。

适用：articles/*.md 的中文段（===EN=== 之前）与 articles.json 的中文字段。
用法：python scripts/normalize_cn_numbers.py [--apply]

设计要点（踩过的坑，改动前请读）：
1. 后行断言不能用 `(?<![\d\w])`——Python re 的 \w 在 Unicode 下**会匹配汉字**，
   会把「约八十名」「逾百万」这类前面是中文的数字全部静默漏掉。已改为 `(?<![A-Za-z0-9_])`。
2. 「万/亿」常作单位前缀（万吨 / 亿美元），所以不能让数值把「万」吞掉，
   否则「七千七百零一万吨」会变成「77010000吨」。分三遍并用占位符隔离。
3. 量级后置叙（如「六千万海外侨胞」）单独成 Pass C，保留「万/亿」尾巴。
4. 引号内的内容一律跳过——多为专名、活动名、口号（如「百千万」工程）。
5. 汉字小数（「一点四六亿元」）必须先整体处理，否则会被当成「四六」≈6 这种荒谬结果。
6. 个位数不转：「一群」「两国」「一并」属中文基础词汇，机械替换破坏语感。
"""
import re

CN   = {'零':0,'〇':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'两':2}
UNIT = {'十':10,'百':100,'千':1000}
BIG  = {'万':10**4,'亿':10**8}
NCH  = '零〇一二三四五六七八九十百千万亿两'
NUMONLY = '零〇一二三四五六七八九十百千两'    # 不含万/亿
DIGIT   = '一二三四五六七八九两'              # 纯数词，用于小数量级词的字首

def cn2int(s):
    total = num = 0
    for ch in s:
        if ch in CN: num = CN[ch]
        elif ch in UNIT:
            total += (num or 1) * UNIT[ch]; num = 0
        elif ch in BIG:
            cur = total + num
            total = (cur or 1) * BIG[ch]; num = 0
    return total + num

def year_str(s):
    return ''.join(str(CN[c]) for c in s if c in CN)

def dec_str(s):
    """汉字小数：三点一四 → 3.14；五点零 → 5"""
    if '点' in s:
        ip, fp = s.split('点', 1)
        ipd = str(cn2int(ip)) if ip else '0'
        fpd = ''.join(str(CN[c]) for c in fp if c in CN).rstrip('0')
        return f'{ipd}.{fpd}' if fpd else ipd
    return str(cn2int(s))

_NO_NUM_BEHIND = r'(?<![零〇一二三四五六七八九十百千万亿两])'
PROTECT = [
    r'第[' + NCH + r']+',                                    # 序数
    _NO_NUM_BEHIND + r'(?:十余|十来|十数|百余|千余|万余|亿余)',
    r'(?:数千|数千万|数十|数年|数月|数日|数十年|数百万|数十万|十几|几[十百千万亿]'
    r'|上百|上千|上万|成千|成百|数以[十百千万])',             # 泛指量词
    _NO_NUM_BEHIND + r'(?:两三年|两三天|两三个)',
    r'十[一二三四五六七八九][一二三四五六七八九]',            # 约数：十七八 / 十五六
    r'[一二三四五六七八九][二三四五六七八九](?=[百千万])',    # 约数：二三千 / 五六百万 / 七八千
                                                        # （限 [百千万] 以免误伤「三十六万亿」）
    r'(?:一带一路|三中全会|三通|两岸|双边|双十|二十四节令鼓|九三〇|九二共识|百日维新|九州|四海'
    r'|二十国集团|二十国|一国两制|三皇五帝)',
    r'(?:千方百计|九牛一毛|四面八方|五湖四海|七七八八|一来二去|三言两语|三头六臂'
    r'|九死一生|一目了然|一心一意|五花八门|七上八下|七零八落|三教九流)',
    r'(?:万般|万分|十分|十二分|万万|一律|一同|一体|一并|一流|一行|再三|一再|万幸|不一(?!_))',
]
PROT_RE = re.compile('(' + '|'.join(PROTECT) + ')')

QUOTED   = re.compile(r'[“"][^”"\n]{1,80}[”"]')                      # 引号内一律跳过
MIXED    = re.compile(r'[0-9][0-9,\.]*\s+(?=[' + NCH + r'])')         # 阿拉伯数字+空格+汉字数字
DECIMAL  = re.compile(r'(?<![\d.])([' + NUMONLY + r']{1,6})点([零〇一二三四五六七八九]{1,6})')
DATEMD   = re.compile(r'([一二三四五六七八九十]{1,2})月([一二三四五六七八九十]{1,3})日')
YEARCN   = re.compile(r'([零〇一二三四五六七八九]{4})年')
PCT      = re.compile(r'百分之([' + NCH + r'点]{1,12})')

_LB = r'(?<![A-Za-z0-9_])'
MAG   = (r'万亿|万吨|万人|万个|万家|万名|万次|万户|万美元|万部|万桶|万辆|万公顷|万千瓦|万立方米'
         r'|万美元|亿美元|亿元|亿立方米|亿千瓦时|亿人次|亿吨|亿个')
PLAIN = (r'美元|元|吨|米|公里|千米|平方|公顷|英亩|海里|公斤|磅|架|艘|辆|家|所|支|名|人|次|倍|座|条|项'
         r'|笔|起|例|国|省|市|县|州|岛|成|轮|批|期|岁|层|个百分点')

AMT_A = re.compile(_LB + r'([' + CN.keys().__iter__().__next__() + DIGIT[1:] + r'十百千][' + NUMONLY + r']+)(?=(?:余|多)?(?:' + MAG + r'))')
AMT_C = re.compile(_LB + r'([' + DIGIT + r'][' + NUMONLY + r']*)(万亿|亿|万)(?![零〇一二三四五六七八九十百千两])')
AMT_B = re.compile(_LB + r'([' + DIGIT + r'十百千][' + NCH + r']+)(?=(?:余|多)?(?:' + PLAIN + r'))')

def convert(text):
    """返回 (新文本, [(原串, 新串), ...])"""
    slots, changes = [], []

    def stash(m):
        slots.append(m.group(0)); return f'\x00{len(slots)-1}\x00'
    def hold(m):                       # 占位但保留原文
        slots.append(m.group(0)); return f'\x00{len(slots)-1}\x00'

    def rec(old, new):
        if old != new: changes.append((old, new))
        return new

    t = QUOTED.sub(hold, text)                      # ① 引号内跳过
    t = MIXED.sub(lambda m: m.group(0)[:-1] + '\x06', t)   # ② 混合写法跳过
    t = PROT_RE.sub(stash, t)                       # ③ 保护名单

    # ④ 先百分比/年份/日期，再小数——顺序反了会让「百分之零点五六」只转一半
    t  = PCT.sub(lambda m: rec(m.group(0), dec_str(m.group(1)) + '%'), t)
    t  = YEARCN.sub(lambda m: rec(m.group(0), year_str(m.group(1)) + '年'), t)
    t  = DATEMD.sub(lambda m: rec(m.group(0), f'{dec_str(m.group(1))}月{dec_str(m.group(2))}日'), t)
    t = DECIMAL.sub(lambda m: '\x01' + rec(m.group(0),
                    f'{cn2int(m.group(1))}.{"".join(str(CN[c]) for c in m.group(2) if c in CN).rstrip("0") or "0"}') + '\x02', t)

    def rep(m):
        v = cn2int(m.group(1))
        return rec(m.group(0), str(v)) if v else m.group(0)
    def rep_c(m):
        v = cn2int(m.group(1))
        return rec(m.group(0), str(v) + m.group(2)) if v else m.group(0)

    t = AMT_A.sub(lambda m: '\x01' + rep(m)  + '\x02', t)
    t = AMT_C.sub(lambda m: '\x01' + rep_c(m) + '\x02', t)
    t = AMT_B.sub(rep, t)

    t = t.replace('\x01', '').replace('\x02', '').replace('\x06', ' ')
    t = re.sub(r'\x00(\d+)\x00', lambda m: slots[int(m.group(1))], t)
    return t, changes


def main(root='.', apply=False):
    import pathlib as _P
    root = _P.Path(root)
    total = files = 0
    for p in sorted((root / 'articles').glob('*.md')):
        parts = p.read_text(encoding='utf-8').split('===EN===')
        if len(parts) < 2:
            continue
        new, ch = convert(parts[0])
        if not ch:
            continue
        total += len(ch); files += 1
        print(f'  {p.name}  ({len(ch)} 处)')
        for old, nw in ch:
            print(f'      “{old}” → “{nw}”')
        if apply:
            parts[0] = new
            p.write_text('===EN==='.join(parts), encoding='utf-8')
    print(f'\n{"已写回" if apply else "DRY-RUN"}：{total} 处 / {files} 篇')

if __name__ == '__main__':
    import sys
    main(apply=('--apply' in sys.argv))
