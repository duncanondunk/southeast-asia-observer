#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文段标点规范化（供写稿后处理复用）
  规则 A：半角引号 " " -> 全角 “ ”（仅中文段，逐行配对替换）
  规则 B：数字与中文之间的空格去除（站内规范：数字与中文之间不留空格）

用法：
  python scripts/normalize_cn_punct.py            # dry-run，只报告
  python scripts/normalize_cn_punct.py --apply    # 写回文件

保护（不处理）：
  1) ===EN=== 之后的英文段
  2) 话题参考行（*话题参考：… 原报道标题逐字保留）
  3) URL / 域名 / 邮箱
  4) 反引号代码 `…`
  5) HTML 标签 <…>
  6) 引号数为奇数的行（无法配对，跳过并报告）

踩坑记录（改前必读）：
  - 英文段含大量半角引号，必须按 ===EN=== 切分，否则全站英文被引号污染。
  - 话题参考里的中文标题带半角引号是引用原文，属逐字保留，不能转全角。
  - 数字空格规则需循环执行直到收敛：'2024 年 3 月' 一次替换只能吃掉一个空格。
"""
import glob, os, re, sys

APPLY = '--apply' in sys.argv

# ---- 保护用的占位 ----
URL_RE = re.compile(r'(?:https?://|www\.)[A-Za-z0-9._~:/?#@!$&\'()*+,;=%-]+')
MAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
CODE_RE = re.compile(r'`[^`\n]*`')
TAG_RE = re.compile(r'<[^<>\n]+>')

# ---- 规则 B：数字与中文之间空格 ----
DIG_SP = re.compile(r'(?<=[0-9]) (?=[一-鿿])|(?<=[一-鿿]) (?=[0-9])')

TOPIC_RE = re.compile(r'^\s*\*话题参考[:：]')


def mask(line):
    """把需保护片段替换为占位符，返回 (masked, 还原函数)"""
    store = []

    def _sub(pat):
        def f(m):
            store.append(m.group(0))
            return '\x00%d\x00' % (len(store) - 1)
        return pat.sub(f, line) if False else None

    def repl(m):
        store.append(m.group(0))
        return '\x00%d\x00' % (len(store) - 1)

    out = URL_RE.sub(repl, line)
    out = MAIL_RE.sub(repl, out)
    out = CODE_RE.sub(repl, out)
    out = TAG_RE.sub(repl, out)

    def unmask(s):
        for i, v in enumerate(store):
            s = s.replace('\x00%d\x00' % i, v)
        return s
    return out, unmask


def fix_quotes(line):
    """半角双引号按行配对转全角；奇数个则原样返回"""
    if '"' not in line:
        return line, 0
    if line.count('"') % 2 != 0:
        return line, 0
    out, flag = [], True
    for ch in line:
        if ch == '"':
            out.append('“' if flag else '”')
            flag = not flag
        else:
            out.append(ch)
    return ''.join(out), line.count('"')


def fix_digit_space(line):
    """数字与中文之间去空格，循环到收敛"""
    n = 0
    prev = None
    while prev != line:
        prev = line
        line, k = DIG_SP.subn('', line)
        n += k
    return line, n


def process(path):
    raw = open(path, encoding='utf-8').read()
    parts = raw.split('===EN===')
    zh = parts[0]
    rest = parts[1:] if len(parts) > 1 else []

    out_lines, q_total, d_total, odd_lines = [], 0, 0, []
    for i, line in enumerate(zh.split('\n'), 1):
        if TOPIC_RE.match(line):
            out_lines.append(line)
            continue
        m, unmask = mask(line)
        m, q = fix_quotes(m)
        if '"' in m and q == 0 and '"' in line:
            odd_lines.append(i)
        m, d = fix_digit_space(m)
        q_total += q
        d_total += d
        out_lines.append(unmask(m))

    new_zh = '\n'.join(out_lines)
    # 注意：分隔符两侧的换行已保留在 parts 里，重建时切勿再补 '\n'，
    # 否则每篇都会在 ===EN=== 前多出一个空行（曾在 2026-10-26 污染 289 篇）。
    if rest:
        new = new_zh + '===EN===' + '===EN==='.join(rest)
    else:
        new = new_zh
    return new, q_total, d_total, odd_lines


def main():
    files = sorted(glob.glob('articles/*.md'))
    tot_q = tot_d = 0
    touched, odd_report = [], []
    for p in files:
        new, q, d, odd = process(p)
        if q or d:
            touched.append((p, q, d))
            tot_q += q
            tot_d += d
            if odd:
                odd_report.append((p, odd))
            if APPLY:
                open(p, 'w', encoding='utf-8').write(new)
    print(f"{'APPLY' if APPLY else 'DRY-RUN'}：引号 {tot_q} 处 / 数字空格 {tot_d} 处 / 涉及 {len(touched)} 篇")
    if not APPLY:
        for p, q, d in sorted(touched, key=lambda x: -(x[1] + x[2]))[:15]:
            print(f"   {os.path.basename(p)}: 引号 {q} / 空格 {d}")
    if odd_report:
        print(f"\n含奇数引号（已跳过）{len(odd_report)} 篇，示例：")
        for p, odd in odd_report[:8]:
            print(f"   {os.path.basename(p)} 行 {odd[:6]}")


if __name__ == '__main__':
    main()
