# -*- coding: utf-8 -*-
r"""把 SMD 无源件的连接器**名字**改成 `1` / `2` ✓（只动 `name` ✗ 不动 id ✗✓）

★★ 用户 2026-10-11 ✓：「一起改成 1/2 吧」✓ —— 这批件的老写法是 `name="Pin 0"` / `name="Pin 1"` ✗，
   本库惯例（见 `D3` 那类件 ✓）是 **name = 脚号（1 基 ✓）**、而 **id 仍 0 基** ✓
   （`connector0` ↔ 第 1 脚 ✓）—— 记忆里那条「connector id 0 基但 name/svgId 用脚号」✓。

★ 为什么**只改 name** ✗（关键 ✓）：`id` 是**功能键** ✓ —— `.fzz` 里
   `<connect connectorId="connector0" …>` ✓、`.fzp` 的 `svgId`/`legId` ✗ 都按 id 找 ✗
   ⇒ 动 id 会把已有板子的连接**全部弄断** ✗✗。`name` 只影响**显示** ✓。

★ 改哪几处 ✓（都在 `.fzp` 里 ✓）：
   · `<connector id="connector0" name="…" …>` ⇒ `name="1"` ✓（`connector1` ⇒ `"2"` ✓）；
   · `<description>…</description>` 里同样口径 ✓（老写法写的是 `Pin0` / `Pin 1` ✓）；
   · ✗ 其它一律不碰 ✗（view / layers / buses / properties ✓）。

用法：
  py -3.13 -X utf8 tools\fix_conn_names.py            # 只报（dry ✓）
  py -3.13 -X utf8 tools\fix_conn_names.py --do       # 改 + 重打 .fzpz ✓
  py -3.13 -X utf8 tools\fix_conn_names.py --do svg\Resistor-0603 ...
退出码：0 = 全都已规范 ✓；1 = 还有 `Pin 0/Pin 1` 这种 ✗（`--do` 之后必为 0 ✓）。
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import breadboard_only_views as BOV                                 # noqa: E402

WANT = {"connector0": "1", "connector1": "2"}


def scan_dirs(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            fzps = [f for f in os.listdir(p) if f.startswith("part.") and f.endswith(".fzp")]
            if fzps:
                out.append((p, os.path.join(p, fzps[0])))
        else:
            out.append((os.path.dirname(p), p))
    return out


def fix_fzp(text):
    """⇒ (新文本, 改了几处 ✓)"""
    n = 0
    for cid, want in WANT.items():
        pat = re.compile(r'(<connector id="%s"\s+name=")([^"]*)(")' % re.escape(cid))

        def rep(m):
            nonlocal n
            if m.group(2) == want:
                return m.group(0)
            n += 1
            return m.group(1) + want + m.group(3)

        text = pat.sub(rep, text)
        # description 里那句也顺手对齐 ✓（老写法 `Pin0` / `Pin 1` ✓）
        m = re.search(r'(<connector id="%s".*?<description>)(.*?)(</description>)' % re.escape(cid),
                      text, re.S)
        if m and m.group(2).strip() != want:
            text = text[:m.start(2)] + want + text[m.end(2):]
            n += 1
    return text, n


def process(path, do=False):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    new, n = fix_fzp(text)
    if not n:
        return False, "name 已经规范 ✓"
    try:
        ET.fromstring(new)
    except ET.ParseError as exc:
        return False, "✗ 改完不是合法 XML（%s）⇒ **不写** ✗" % exc
    if re.search(r'<connector id="connector[01]"\s+name="Pin', new):
        return False, "✗ 改完还有 `Pin …` ✗ ⇒ **不写** ✗"
    if not do:
        return True, "（dry ✓）可改 %d 处 ✓ ⇒ name = 1/2 ✓（id 不动 ✓）" % n
    with open(path, "wb") as f:
        f.write(new.encode("utf-8"))
    return True, "✓ 改了 %d 处 ✓（只动 name/description ✗ id 未动 ✓）" % n


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--do", action="store_true", help="改 ＋ 重打 .fzpz ✓")
    a = ap.parse_args(argv)
    paths = a.paths or [d for d in (os.path.join(ROOT, "svg", n) for n in sorted(os.listdir(
        os.path.join(ROOT, "svg")))) if os.path.isdir(d)
        and re.search(r"(Resistor|Capacitor)", os.path.basename(d))]
    items = scan_dirs(paths)
    print("== fix_conn_names：SMD 无源件的连接器名 ⇒ `1`/`2` ✓"
          "（id 一律不动 ✗✓；判据 = 用户 2026-10-11 的「一起改成 1/2」✓）｜%d 件 ==" % len(items))
    changed = []
    for d, fzp in items:
        hit, why = process(fzp, do=a.do)
        if hit:
            print("   %-20s %s" % (os.path.basename(d), why))
            changed.append(d)
    if a.do and changed:
        for d in changed:
            BOV.pack(d)
        print("⇒ 改了 **%d** 件 ✓（并重打各自的 `.fzpz` ✓）" % len(changed))
    elif not a.do:
        print("⇒ 待改 **%d** 件 ✓（加 `--do` 才写 ✗）" % len(changed))
    rest = [os.path.basename(d) for d, fzp in items
            if re.search(r'<connector id="connector[01]"\s+name="Pin',
                         open(fzp, encoding="utf-8").read())]
    print("⇒ 复扫仍有 `Pin …` ✗：**%d** 件 %s" % (len(rest), "" if not rest else "✗"))
    return 1 if rest else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
