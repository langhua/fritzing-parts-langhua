# -*- coding: utf-8 -*-
r"""`gerber_check.py` 自测 ✓（2026-10-10 立 ✓）—— 正例 ＋ **人为破坏的反例** ✓

★ 约定（仓规 ✓，见 `tools/tests/run_all.py` ✓）：零第三方依赖 ✓、自带 `exit 0/1` ✓、
  命名 `*_selftest.py` ✗（不叫 `test_*.py` ✗ —— pytest 会收集它、被 `SystemExit` 打崩 ✓）。

★ 为什么要有它 ✓：`gerber_check` 是"**送板前最后一道闸门**" ✓ —— ✗ 一个"永远报绿"的检查比没有检查更坏 ✗
  （它会让用户把**缺铜/短路**的板直接下单 ✗）。⇒ 每种硬伤**都要有一条反例**：
  ① 缺层（点名的 8 种必需层 ✓）；② 板框不闭合 ✗；③ 引用了没定义的光圈 ✗；
  ④ 铜↔铜间距 < 5 mil ✗；⑤ 铜层是空的 ✗；⑥ 钻孔里没有过孔（模型对不上）✗。

★ 夹具**自己造** ✓（不是抄用户的板 ✓）：10 × 10 mm 的小板 ✓ —— 造法照 Fritzing 自己的头
  （`%FSLAX23Y23*%` ＋ `%MOIN*%` ＋ `%LNZ` ✓，1 mil 栅格 ✓），坐标 = **板左下角、y 向上、英寸** ✓。
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "gerber_check.py")

HDR = ("G04 MADE WITH FRITZING*\nG04 WWW.FRITZING.ORG*\nG04 DOUBLE SIDED*\nG04 HOLES PLATED*\n"
       "G04 CONTOUR ON CENTER OF CONTOUR VECTOR*\n%ASAXBY*%\n%FSLAX23Y23*%\n%MOIN*%\n"
       "%OFA0B0*%\n%SFA1.0B1.0*%\n")
TAIL = "M02*\n"


def ger(aps, body, layer):
    """一份小 Gerber ✓（`aps` = [(码, 定义)] ✓、`body` = 正文行 ✓）"""
    s = HDR
    for code, dfn in aps:
        s += "%%ADD%d%s*%%\n" % (code, dfn)
    s += "%%LN%s*%%\nG90*\nG70*\n" % layer
    return s + body + TAIL


def flash(x, y, d):
    return "G54D%d*\nX%dY%dD03*\n" % (d, x, y)


def seg(x0, y0, x1, y1, d):
    return "G54D%d*\nX%dY%dD02*\nX%dY%dD01*\nD02*\n" % (d, x0, y0, x1, y1)


def outline(w=394, h=394, close=True, pen=8):
    b = ("G54D10*\nG54D11*\n" + "X4Y%dD02*\n" % (h - 4) +
         "X%dY%dD01*\n" % (w - 4, h - 4) + "X%dY4D01*\n" % (w - 4) +
         "X4Y4D01*\n")
    b += "X4Y%dD01*\n" % (h - 4) if close else "X40Y40D01*\n"
    return ger([(10, "R,3.940000X3.940000"), (11, "C,0.008000"), (10, "C,0.008")],
               b + "D02*\nG04 End of contour*\n", "CONTOUR")


def drill(holes=((100, 12, 12),), tools=((1, 0.0866), (100, 0.0118))):
    """钻孔 ✓（Excellon ✓；`T1..T99` = 非镀 ✓、`T100+` = 镀通 ✓ —— Fritzing 的口径 ✓）"""
    s = "; NON-PLATED HOLES START AT T1\n; THROUGH (PLATED) HOLES START AT T100\nM48\nINCH\n"
    for t, d in tools:
        s += "T%dC%.6f\n" % (t, d)
    s += "%\n"
    for t, x, y in holes:
        s += "T%d\nX%06dY%06d\n" % (t, x, y)
    return s + "T00\nM30\n"


def write_fixture(d, **opt):
    """造一套"正常"的 10×10 mm 双层板 ✓（`opt` 用来**破坏**它 ✓）⇒ 目录 ✓"""
    os.makedirs(d, exist_ok=True)
    w = opt.get("outline_w", 394)
    files = {
        "t_copperTop.gtl": ger([(10, "C,0.024000"), (11, "C,0.008000")],
                               flash(120, 120, 10) + seg(120, 120, 300, 120, 11)
                               + seg(300, 120, 300, 300, 11), "COPPER1"),
        "t_copperBottom.gbl": ger([(10, "C,0.024000"), (11, "C,0.008000")],
                                  flash(300, 300, 10)
                                  + seg(300, 300, 120, 300, 11), "COPPER0"),
        "t_maskTop.gts": ger([(10, "C,0.034000")], flash(120, 120, 10), "MASK1"),
        "t_maskBottom.gbs": ger([(10, "C,0.034000")], flash(300, 300, 10), "MASK0"),
        "t_silkTop.gto": ger([(10, "C,0.008661")], seg(60, 60, 340, 60, 10), "SILK1"),
        "t_silkBottom.gbo": ger([(10, "C,0.008661")], seg(60, 340, 340, 340, 10), "SILK0"),
        "t_contour.gm1": outline(w=w, close=opt.get("close", True)),
        "t_drill.txt": drill(),
    }
    for fn, txt in files.items():
        io.open(os.path.join(d, fn), "w", encoding="utf-8", newline="\n").write(txt)
    if opt.get("del_maskTop"):
        os.remove(os.path.join(d, "t_maskTop.gts"))
    if opt.get("empty_top"):
        io.open(os.path.join(d, "t_copperTop.gtl"), "w", encoding="utf-8",
                newline="\n").write(ger([(10, "C,0.024000")], "", "COPPER1"))
    if opt.get("undef_ap"):
        io.open(os.path.join(d, "t_copperTop.gtl"), "w", encoding="utf-8",
                newline="\n").write(ger([(10, "C,0.024000")], flash(120, 120, 99), "COPPER1"))
    if opt.get("tight"):
        # 4 mil 线心距 8 mil ⇒ **缝 0.1016 mm**（4 mil ✓ < 5 mil ⇒ 必 ✗）
        # ★ 盘/支线要**离远点** ✗ —— 贴在一起会把两根线**并成一块铜** ✗（实测踩过 ✓）
        io.open(os.path.join(d, "t_copperTop.gtl"), "w", encoding="utf-8", newline="\n").write(
            ger([(10, "C,0.024000"), (11, "C,0.004000")],
                flash(120, 120, 10) + seg(120, 120, 120, 180, 11)
                + seg(120, 280, 300, 280, 11) + seg(120, 288, 300, 288, 11), "COPPER1"))
    if opt.get("outside"):
        io.open(os.path.join(d, "t_copperTop.gtl"), "w", encoding="utf-8", newline="\n").write(
            ger([(10, "C,0.024000"), (11, "C,0.008000")],
                flash(120, 120, 10) + seg(120, 120, 520, 120, 11), "COPPER1"))
        io.open(os.path.join(d, "t_drill.txt"), "w", encoding="utf-8", newline="\n").write(
            drill(holes=((1, 12, 12),), tools=((1, 0.0866), (100, 0.0118))))
    return d

def run(folder, *args):
    cmd = [sys.executable, "-X", "utf8", TOOL, folder] + list(args)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, p.stdout.decode("utf-8", "replace")


CASES = [
    # (名字, 破坏项, 期望退出码, 期望报告里出现的字 ✓)
    ("正例：正常的 10×10 双面板 ✓", {}, 0, "可送板"),
    ("反例①：删掉顶层阻焊 ⇒ **缺层** ✗", {"del_maskTop": True}, 2, "缺层"),
    ("反例②：板框不闭合 ✗", {"close": False}, 1, "不闭合"),
    ("反例③：引用了没定义的光圈 ✗", {"undef_ap": True}, 1, "没定义的光圈"),
    ("反例④：两条 4 mil 线的心距 8 mil（缝 4 mil < 5 mil）✗", {"tight": True}, 1, "低于 5 mil"),
    ("反例⑤：顶层铜是空的 ✗", {"empty_top": True}, 1, "是空的"),
    ("反例⑥：铜线跑到板框外 ✗", {"outside": True}, 1, "越出板框"),
]


def main():
    tmp = tempfile.mkdtemp(prefix="gerber_check_selftest_", dir=HERE)
    bad = []
    try:
        for i, (name, opt, want_rc, want_txt) in enumerate(CASES):
            folder = os.path.join(tmp, "case%02d" % i)
            write_fixture(folder, **opt)
            rc, out = run(folder, "--no-model")
            ok = (rc == want_rc) and (want_txt in out)
            print("── %s ⇒ exit %d（期望 %d）%s" % (name, rc, want_rc, "✓" if ok else "✗"))
            if not ok:
                bad.append(name)
                print("   期望报告里出现：%s" % want_txt)
                for ln in out.splitlines():
                    if "✗" in ln or "⚠" in ln:
                        print("   | " + ln.strip()[:160])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n⇒ %s（%d 例 ✓）" % ("✓ 全过" if not bad else "✗ **不过 %d 例**：%s"
                              % (len(bad), "、".join(bad)), len(CASES)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
