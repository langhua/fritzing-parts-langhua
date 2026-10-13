# -*- coding: utf-8 -*-
r"""G6 **单位口径闸门** ✓ —— 同一个物理量**只许一处定义** ✗，且各处的值必须**相等** ✓

★ 起因（2026-10-13 用户定 ✓）：「既然**总犯这个错误**，是不是写入规则？」
  错的事：**`px` 多长**，同一个量在库仓里曾经**同时有三个值** ✗✗：
    · `part_box.canvas_mm`：`25.4/72` ✓（1/72 in ✓，2026-09-27 从 `25.4/96` ✗ 改过来 ✓，
      注释里还写着「**同一件事只能有一份口径**」✗ —— 可另一半没跟着改 ✗）；
    · `sch_box.UMM`：`25.4/90` ✗（= 把 px 当 sketch 单位 ⇒ 有 viewBox 的件算出 `k=1.0` ✗）；
    · 更早的 `render_bb`：`25.4/96` ✗。
  后果（实测 ✓）：原理图里**每个 px 声明件**的脚位都比 Fritzing 认的**近 20%** ✗
  ⇒ 用户报「`Wire90000077` 没接到 `D1.A`、`Wire90000071` 没接到 `D1.C`，而 Fritzing 却报了连接」✗
  ⇒ **数据与实际脱节** ✓；而我自己那套判据（与写线器共用同一份坐标）报 `(A)/(B)=0` ✗ = **自证** ✗✗。

★ 本闸门守三条（都指向"第二个值" ✗）：
  ① **两个实现的值必须相等** ✓：`sch_box.UMM["px"]` 必须 == `part_box` 算出来的 px ✓（pt 同理 ✓）
     —— 这条**当年就能抓住这次 bug** ✓（90 vs 72 ✗）；
  ② 全仓 `tools/*.py` 里，**任何** `"px": 25.4/N` 定义式，`N` 必须是 **72** ✓（96/90 一律 FAIL ✗）；
  ③ 全仓不许再出现 `25.4 / 96` ✓（那是 96dpi 的老错值 ✗）。

★ 用法：`py -3.13 tools/check_units.py`（rc 0 = 过 ✓ / 1 = 不合格 ✗ / 2 = 环境缺依赖 ⇒ 跳过 ✓）
"""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
FAILS, WARNS = [], []


def _fail(msg):
    FAILS.append(msg)


# ── ① 两个实现的值必须相等 ✓（用**公开函数**问，不读它们的私有表 ✗）─────────────
sys.path.insert(0, str(HERE))
try:
    import part_box as PB
    import sch_box as SB
except Exception as ex:                                  # noqa: BLE001
    print("SKIP G6 单位口径：库仓工具 import 不了（%s）" % ex)
    sys.exit(2)

try:
    _pb_px = PB.canvas_mm({"width": "1px", "height": "1px"})[0]
    _pb_pt = PB.canvas_mm({"width": "1pt", "height": "1pt"})[0]
    _sb_px = SB.UMM["px"]
    _sb_pt = SB.UMM["pt"]
    print("① part_box：1px = %.6f mm ｜ sch_box：UMM['px'] = %.6f mm" % (_pb_px, _sb_px))
    if abs(_pb_px - _sb_px) > 1e-9:
        _fail("① `px` 两处**不相等** ✗：`part_box` = %.6f mm、`sch_box` = %.6f mm"
              "（同一件事两份口径 ✗ —— 2026-10-13 那个 bug 就是这个 ✓）" % (_pb_px, _sb_px))
    if abs(_pb_pt - _sb_pt) > 1e-9:
        _fail("① `pt` 两处**不相等** ✗：`part_box` = %.6f、`sch_box` = %.6f" % (_pb_pt, _sb_pt))
    if abs(_sb_px * 72.0 / 25.4 - 1.0) > 1e-9:
        _fail("① `px` **不等于 1/72 英寸** ✗（当前 1px = %.6f mm ⇒ 分母 %.1f ✗）"
              % (_sb_px, 25.4 / _sb_px))
except Exception as ex:                                  # noqa: BLE001
    _fail("① 问不到两个实现的值 ✗（%s）—— 口径**无法核对** ✓ 要报出，不许静默 ✗" % ex)

# ── ② 全仓 `"px": 25.4/N` 的 N 必须是 72 ✓ ────────────────────────────────────
_pat_def = re.compile(r'[\'"]px[\'"]\s*:\s*25\.4\s*/\s*([0-9.]+)')
_hits = []
for f in sorted(HERE.glob("*.py")):
    for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for m in _pat_def.finditer(ln):
            _hits.append((f.name, i, m.group(1), ln.strip()))
            if abs(float(m.group(1)) - 72.0) > 1e-9:
                _fail("② %s:%d 把 `px` 定义成 `25.4/%s` ✗（必须是 **72** ✓ = 1/72 英寸 ✓）：%s"
                      % (f.name, i, m.group(1), ln.strip()[:90]))
print("② 全仓 `\"px\": 25.4/N` 定义式：%d 处 ⇒ %s"
      % (len(_hits), "、".join("%s(N=%s)" % (h[0], h[2]) for h in _hits) or "一处都没有 ✗"))

# ── ③ 全仓不许再出现 `25.4 / 96` ✓（96dpi 老错值 ✗）──
#   ★ 只查**代码** ✓，不查注释/说明里的历史提法 ✗（本仓惯例：注释会写“由 xxx 改成 yyy”✗
#     ⇒ 不过滤就会**误报** ✗ —— 实测 ✓：首版把 `part_box.py` / `sch_box.py` 里那两行
#     历史注释都报成错了 ✗）。口径：去掉 `#` 之后若还含中文字符 ⇒ 当**说明文字** ✓（记 WARN ✓）。
_CJK = re.compile(r"[\u4e00-\u9fff]")
_pat96 = re.compile(r"25\.4\s*/\s*96")
for f in sorted(HERE.glob("*.py")):
    for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not _pat96.search(ln) or "check_units" in f.name:
            continue
        _code = ln.split("#", 1)[0]
        if not _code.strip() or _CJK.search(_code):      # 纯注释行 / 说明文字 ⇒ 记 WARN 不算错 ✓
            WARNS.append("③ %s:%d 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：%s"
                         % (f.name, i, ln.strip()[:80]))
            continue
        _fail("③ %s:%d 又出现 `25.4 / 96` ✗（= 按 96dpi 算 px ✗，2026-09-27 已否掉 ✓）：%s"
              % (f.name, i, ln.strip()[:90]))

print("\n=== G6 单位口径：%s ===" % ("**不合格** ✗ %d 条" % len(FAILS) if FAILS else "**合格** ✓"))
for _f in FAILS:
    print("   ✗ " + _f)
for _w in WARNS:
    print("   ⚠ " + _w)
sys.exit(1 if FAILS else 0)
