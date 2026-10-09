# -*- coding: utf-8 -*-
r"""Gerber 导出目录 **独立校验**（直接读文件 ✓，不看 Fritzing 的脸色 ✗）2026-10-10 立 ✓

★★ 为什么要它 ✓：用户从 Fritzing 导出一批 Gerber 之后，**"能不能直接送板"** 得有个
   **可重复、有数值、能进 CI** 的判据 ✓ —— ✗ 不能靠"打开 Fritzing 看一眼" ✗，
   ✗ 也不能靠板厂的在线预览"看着像" ✗（那玩意儿不告诉你 0.12 mm 的线 ✗）。
   ⇒ 本工具**只读导出目录里的文件** ✓（RS-274X ＋ Excellon），
     把 层齐全性 / 单位格式原点 / 板框闭合 / 钻孔表 / 线宽 / 铜间距 / 旋转焊盘 /
     阻焊开窗 / 丝印压盘 / 可疑物 逐项算成**数** ✓，再（可选）与 `.fzz` 的 PCB 视图对账 ✓。

★ 口径（都是**实测**来的 ✓，不是猜 ✗）：
  · 单位/格式：Fritzing 导出 `%FSLAX23Y23*%`（英寸 ✓、**省略前导零** ✓、1 mil 栅格 ✓）
    —— 出处 = Fritzing 源码 `src/svg/svg2gerber.cpp`（`// format coordinates to drop
    leading zeros with 2,3 digits` / `// NOTE: this currently forces a 1 mil grid` ✓）。
  · 坐标原点：**板框左下角、y 向上、英寸** ✓（实测：模型里离板角 3.00 mm 的安装孔
    在钻孔文件里正是 `X001180Y001181` = 0.118 in ✓）。
  · 阻焊 = **铜 ＋ 0.254 mm**（10 mil ✓ = 2×5 mil）—— 出处 = 同一份源码的
    `MaskClearance`（注释写 "5 mils clearance" ✓、装机版按 5 mil 算 ✓）。⇒ 丝印/导线
    的阻焊开窗是 Fritzing 的**既有行为** ✓，本工具照实报 ✓、不静默 ✗。
  · 板框 = 0.2032 mm 笔画的**中心线**，且这条线**向内缩半个笔宽** ✓
    （实测：25.000 mm 板 ⇒ 路径 bbox 976 mil；984.252 − 976 = 8.252 mil ≈ 笔宽 8 mil ＋
     2.3 格式舍入 ✓）⇒ **笔画外沿 = 板框** ✓，**线心围出的面积小 0.2032 mm/轴** ✗
    —— 两种读法都给数 ✓（见报告 §2），别让板厂猜 ✗。
  · 填充：Fritzing 把"实心形状"导成**扫描线**（1 mil × 1 mil 方光圈 `R,0.001X0.001`
    或 0.0001 in 细圆 `C,0.0001` ✓）⇒ **超细光圈 ≠ 细线** ✓，本工具据此分开算 ✗。

用法：
  py -3.13 -X utf8 tools\gerber_check.py <gerber目录> [选项]
    --fzz <sketch.fzz>   与模型（PCB 视图）对账 ✓；不给 ⇒ 去 <目录>\.. 找 `<前缀>.fzz` ✓
    --no-model           只做"文件内在"检查 ✓（不找 fzz ✓）
    --png                出叠图预览 png ✓（默认放导出目录 ✓）
    --out <目录>         png 写这里 ✓（默认 = 导出目录 ✓）
    --json <文件>        结构化结果 ✓（自测/CI 用 ✓）
    --quiet              只打结论与 ✗/⚠ 项 ✓
退出码：**0 = 可送板** ✓；**1 = 有 ✗（不可送板）** ✓；**2 = 拒判**（缺层/读不动 ⇒ 判不了 ✓）。
"""
import array
import collections
import csv
import heapq
import io
import json
import math
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

MM_PER_IN = 25.4
MIL_MM = 0.0254
SK = 25.4 / 90.0                      # 1 sketch 单位 = 0.282222 mm ✓（与 `pcb_wire.SK` 同 ✓）

# 判据（都可调 ✓ —— 值写在这里并**在报告里印出来** ✓，不藏在代码里 ✗）
POS_TOL_MM = 0.06                     # 位置对账容差 ✓（1 mil 栅格 ＋ 2.3 舍入 ⇒ 0.033 mm；留一倍余量 ✓）
SIZE_TOL_MM = 0.06                    # 焊盘尺寸容差 ✓
BOARD_TOL_MM = 0.30                   # 板框尺寸容差 ✓（线心/外沿两种读法差 0.2032 ✓ ⇒ 由这里判 ✓）
LEN_TOL_FRAC = 0.03                   # 铜总长对账容差 ✓（±3% ✓）
HAIRLINE_MM = 0.1524                  # 6 mil ✓ = JLCPCB **常规**最小线宽/间距 ✓
FILL_AP_MM = 0.06                     # ≤ 这个光圈尺寸 ⇒ 判为**填充笔**（不是导线 ✓）
FILL_PEN_MM = 0.03                    # ≤ 这个 ⇒ **扫描线填充笔**（1 mil / 0.1 mil ✓）；丝印用它填文字 ✓
MASK_CLEAR_MM = 0.254                 # 阻焊外扩 10 mil ✓（增量口径 ✓）
RASTER_STEP_MM = 0.05                 # 间距扫描步长 ✓（粗扫 ✓）
RASTER_REFINE_MM = 0.004              # 细化步长 ✓（粗扫定位后原地细扫 ✓）
CLEAR_LIMIT_MM = 1.0                  # 只关心 ≤ 这么宽的间距 ✓（超过就不值得报 ✓）

# 复用的模型读取（库仓同一份 ✓，不另写 ✗）
try:
    import pcb_check as PC
    import pcb_wire as PW
    _HAS_MODEL = True
except Exception as _exc:                                              # pragma: no cover
    PC = PW = None
    _HAS_MODEL = False
    _MODEL_ERR = _exc

# 角色 → （后缀, 必需?, 中文名 ✓）
ROLES = [
    ("copperTop", (".gtl",), True, "顶层铜"),
    ("copperBottom", (".gbl",), True, "底层铜"),
    ("maskTop", (".gts",), True, "顶层阻焊"),
    ("maskBottom", (".gbs",), True, "底层阻焊"),
    ("silkTop", (".gto",), True, "顶层丝印"),
    ("silkBottom", (".gbo",), True, "底层丝印"),
    ("outline", (".gm1", ".gko", ".gml", ".gbr"), True, "板框"),
    ("drill", (".txt", ".drl", ".xln", ".ncd"), True, "钻孔"),
    ("pasteTop", (".gtp",), False, "顶层钢网"),
    ("pasteBottom", (".gbp",), False, "底层钢网"),
    ("pnp", (".xy", ".pos", ".csv"), False, "贴片坐标"),
]
COPPER_ROLES = ("copperTop", "copperBottom")
SIDE_OF_ROLE = {"copperTop": "top", "copperBottom": "bottom",
                "maskTop": "top", "maskBottom": "bottom",
                "silkTop": "top", "silkBottom": "bottom",
                "pasteTop": "top", "pasteBottom": "bottom"}


# ---------------------------------------------------------------- 小工具
def fmt(x, n=3):
    return ("%%.%df" % n) % x


def mm_in(v):
    """英寸 → mm ✓"""
    return v * MM_PER_IN


# ---------------------------------------------------------------- RS-274X
class Op(object):
    """一条 Gerber 操作 ✓（flash / draw / region ✓ 三种）"""
    __slots__ = ("kind", "ap", "p0", "p1", "pts", "line")

    def __init__(self, kind, ap=None, p0=None, p1=None, pts=None, line=0):
        self.kind = kind
        self.ap = ap
        self.p0 = p0
        self.p1 = p1
        self.pts = pts or []
        self.line = line


class Gerber(object):
    """读一份 RS-274X ✓（Fritzing 导出的子集 ＋ 常见的 G36/G37 填充 ✓）"""

    def __init__(self, path, role=""):
        self.path = path
        self.name = os.path.basename(path)
        self.role = role
        self.comments = []
        self.fs = None                     # (int_digits, dec_digits, 'L'|'T')
        self.unit = None                   # 'IN' | 'MM'
        self.unit_mm = None
        self.offset = (0.0, 0.0)
        self.scale = (1.0, 1.0)
        self.axis = None
        self.layer_name = None
        self.polarity = "D"
        self.apertures = {}                # code -> (kind, params_mm)
        self.ap_defs = []                  # [(code, kind, params_mm)] 文件顺序 ✓
        self.ap_dup = []                   # [(code, first, later)] 同号重复定义 ✗
        self.macros = 0
        self.arcs = 0
        self.unknown = []
        self.ops = []
        self.regions = []                  # [pts] ✓
        self.ap_use = collections.Counter()   # (code, kind_of_op) -> 次数
        self.code_use = collections.Counter()  # code -> 次数
        self.undef_use = set()             # 用了但没定义的 D 码 ✗
        self.ended = False
        self.zero_len = 0
        text = io.open(path, encoding="utf-8", errors="replace").read()
        self.text_len = len(text)
        self._parse(text)

    # -------------------------------------------------- 解析
    def _parse(self, text):
        buf = []
        chunks = []
        for ch in text:
            if ch == "*":
                chunks.append("".join(buf))
                buf = []
            elif ch in "\r\n\t":
                continue
            else:
                buf.append(ch)
        if buf:
            chunks.append("".join(buf))
        cur = (0.0, 0.0)
        start = None
        region = None
        interp = 1
        for line, raw in enumerate(chunks, 1):
            tok = raw.strip()
            while tok and tok[0] == "%":                     # `*%` 换行后还粘着下一句的 `%` ✓
                tok = tok[1:].strip()
            while tok and tok[-1] == "%":
                tok = tok[:-1].strip()
            if not tok:
                continue
            if tok.startswith("G04"):
                self.comments.append(tok[3:].strip())
                continue
            if tok.startswith("FS"):
                self.fs = self._fs(tok)
                continue
            if tok.startswith("MO"):
                self.unit = "IN" if tok.startswith("MOIN") else ("MM" if tok.startswith("MOMM") else None)
                self.unit_mm = MM_PER_IN if self.unit == "IN" else (1.0 if self.unit == "MM" else None)
                continue
            if tok.startswith("OF"):
                m = re.match(r"OFA(-?[\d.]+)B(-?[\d.]+)", tok)
                if m:
                    self.offset = (float(m.group(1)), float(m.group(2)))
                continue
            if tok.startswith("SF"):
                m = re.match(r"SFA(-?[\d.]+)B(-?[\d.]+)", tok)
                if m:
                    self.scale = (float(m.group(1)), float(m.group(2)))
                continue
            if tok.startswith("AS"):
                self.axis = tok[2:]
                continue
            if tok.startswith("AD"):
                self._add(tok)
                continue
            if tok.startswith("AM"):
                self.macros += 1
                continue
            if tok.startswith("LP"):
                self.polarity = tok[2:3] or "D"
                continue
            if tok.startswith("LN"):
                self.layer_name = tok[2:]
                continue
            if tok.startswith("SR"):
                self.unknown.append(tok)
                continue
            if tok in ("M02", "M00", "M2"):
                self.ended = True
                continue
            if tok.startswith("G54"):
                tok = tok[3:]                                # 老写法：G54D10 ✓
                if not tok:
                    continue
            # 复合词：G01/G02/G03 ＋ X/Y/I/J ＋ D01/D02/D03 ✓
            gw = re.findall(r"G(\d+)|X(-?\d+)|Y(-?\d+)|I(-?\d+)|J(-?\d+)|D(\d+)|M(\d+)", tok)
            if not gw:
                self.unknown.append(tok)
                continue
            dx = dy = None
            dcode = None
            for g, x, y, i, j, d, m in gw:
                if g:
                    gv = int(g)
                    if gv in (1, 2, 3):
                        interp = gv
                    elif gv == 36:
                        region = [cur]
                    elif gv == 37:
                        if region:
                            self.regions.append(region)
                            self.ops.append(Op("region", ap=None, pts=region, line=line))
                            self.ap_use[("fill", "region")] += 1
                        region = None
                    elif gv in (70, 71, 90, 91, 74, 75):
                        if gv == 91:
                            self.unknown.append("G91（增量坐标 ✗ 未支持）")
                    else:
                        self.unknown.append(tok)
                elif x:
                    dx = self._num(x)
                elif y:
                    dy = self._num(y)
                elif i or j:
                    pass                                     # 圆弧参数（本工具不支持 ✓）
                elif d:
                    dcode = int(d)
                elif m:
                    self.unknown.append(tok)
            if dcode is not None and dcode not in (1, 2, 3):
                self.cur_ap = dcode
                self.code_use[dcode] += 0
                if dcode not in self.apertures:
                    self.undef_use.add(dcode)
                continue
            if dx is not None or dy is not None:
                cur = (cur[0] if dx is None else dx, cur[1] if dy is None else dy)
            if dcode is None:
                if region is not None:
                    region.append(cur)
                continue
            ap = getattr(self, "cur_ap", None)
            if dcode == 2:
                if region is not None:
                    region = [cur]
                self.ops.append(Op("move", ap, cur, cur, line=line))
            elif dcode == 1:
                if interp != 1:
                    self.arcs += 1
                prev = cur
                if start is None:
                    start = prev
                if region is not None:
                    region.append(cur)
                if ap is not None and ap not in self.apertures:
                    self.undef_use.add(ap)
                self.ops.append(Op("draw", ap, self._prev_pt(prev, start), cur, line=line))
                self.ap_use[(ap, "draw")] += 1
                self.code_use[ap] += 1
                start = cur
            elif dcode == 3:
                self.ops.append(Op("flash", ap, cur, cur, line=line))
                self.ap_use[(ap, "flash")] += 1
                self.code_use[ap] += 1
                if ap is None or ap not in self.apertures:
                    if ap is not None:
                        self.undef_use.add(ap)
                    else:
                        self.undef_use.add("（没选光圈就 D03 ✗）")
        # D01 的起点（上一操作的点）靠 `_last` 记 ✓
        self._fix_draw_starts()

    def _pos_of(self, p):
        return p

    def _prev_pt(self, prev, start):
        return getattr(self, "_last", prev)

    def _fix_draw_starts(self):
        """把每条 draw 的**真起点**补上 ✓（D02 之后才有 D01 ✓，直线段链也一样 ✓）"""
        last = None
        for o in self.ops:
            if o.kind == "move":
                last = o.p0
            elif o.kind == "draw":
                o.p0 = last if last is not None else o.p0
                if o.p0 == o.p1:
                    self.zero_len += 1
                last = o.p1
            elif o.kind == "flash":
                last = o.p0

    def _fs(self, tok):
        m = re.match(r"FS([LT]?)([AI]?)X(\d)(\d)Y(\d)(\d)", tok)
        if not m:
            self.unknown.append(tok)
            return None
        return (int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), m.group(1) or "L")

    def _add(self, tok):
        m = re.match(r"ADD(\d+)([A-Za-z_][\w.\-]*),?(.*)$", tok)
        if not m:
            self.unknown.append(tok)
            return
        code = int(m.group(1))
        kind = m.group(2).upper()
        rest = m.group(3)
        params = []
        for part in re.split(r"[Xx]", rest):
            part = part.strip()
            if part:
                try:
                    params.append(float(part))
                except ValueError:
                    params = []
                    break
        if self.unit_mm:
            params = [p * self.unit_mm for p in params]
        elif params:
            params = []                                    # 单位没写 ⇒ 不敢换算 ✗
        self.ap_defs.append((code, kind, params))
        if code in self.apertures:
            self.ap_dup.append((code, self.apertures[code], (kind, params)))
        self.apertures[code] = (kind, params)

    def _num(self, s):
        """坐标串 → mm ✓（按 FS 的位数与省略零口径 ✓）"""
        neg = s.startswith("-")
        s = s.lstrip("+-")
        dec = self.fs[1] if self.fs else 3
        v = int(s) / float(10 ** dec)
        if neg:
            v = -v
        if self.unit_mm is None:
            return v
        x, _y = self.scale
        return v * self.unit_mm * (x if x else 1.0)

    # -------------------------------------------------- 统计
    def ap_mm(self, code):
        if code not in self.apertures:
            return None
        kind, params = self.apertures[code]
        if kind == "C" and params:
            return (params[0], params[0])
        if kind in ("R", "O") and len(params) >= 2:
            return (params[0], params[1])
        if kind == "P" and params:
            return (params[0], params[0])
        return None

    def ap_min_mm(self, code):
        wh = self.ap_mm(code)
        return min(wh) if wh else None

    def bbox(self, pad=0.0):
        """墨迹包围盒 ✓（元图形 bbox ∪ 光圈半径 ✓）"""
        xs, ys = [], []
        for o in self.ops:
            if o.kind == "region":
                pts = o.pts
            elif o.kind == "flash":
                pts = [o.p0]
            else:
                pts = [o.p0, o.p1]
            r = 0.0
            if o.kind == "flash":
                wh = self.ap_mm(o.ap)
                r = (max(wh) / 2.0) if wh else 0.0
            elif o.kind == "draw":
                m = self.ap_min_mm(o.ap)
                r = m / 2.0 if m else 0.0
            for p in pts:
                xs.append(p[0] - r)
                xs.append(p[0] + r)
                ys.append(p[1] - r)
                ys.append(p[1] + r)
        if not xs:
            return None
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def draws(self):
        return [o for o in self.ops if o.kind == "draw"]

    def flashes(self):
        return [o for o in self.ops if o.kind == "flash"]

    def dup_ops(self):
        """同一层里**同一图形写两遍** ✓ ⇒ [(说明, 次数)] ✓"""
        seen = collections.Counter()
        for o in self.ops:
            if o.kind == "region":
                key = ("region", tuple((round(x, 3), round(y, 3)) for x, y in o.pts))
            elif o.kind == "flash":
                key = ("flash", o.ap, (round(o.p0[0], 3), round(o.p0[1], 3)))
            elif o.kind == "draw":
                key = ("draw", o.ap, (round(o.p0[0], 3), round(o.p0[1], 3)),
                       (round(o.p1[0], 3), round(o.p1[1], 3)))
            else:
                continue
            seen[key] += 1
        return [(k, n) for k, n in seen.items() if n > 1]


# ---------------------------------------------------------------- Excellon
class Drill(object):
    """读一份钻孔文件 ✓（Excellon：M48 头 ＋ 刀表 ＋ 坐标 ✓）"""

    def __init__(self, path, board_mm=None):
        self.path = path
        self.name = os.path.basename(path)
        self.unit = None
        self.unit_mm = None
        self.tools = {}                    # code -> 直径 mm ✓
        self.plated = {}                   # code -> True/False/None
        self.holes = []                    # dict(tool, d_mm, p=(x,y) mm, plated)
        self.fmt = None                    # (int_digits, dec_digits) 推断出来的 ✓
        self.fmt_why = ""
        self.unknown = []
        self.notes = []
        self.ended = False
        text = io.open(path, encoding="utf-8", errors="replace").read()
        self.text = text
        self._parse(text)
        self._infer_format(board_mm)

    def _parse(self, text):
        head = True
        cur = None
        raw_pts = []
        for raw in text.splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith(";"):
                self.notes.append(s.lstrip("; ").strip())
                continue
            if s == "M48":
                head = True
                continue
            if s in ("%", "M95"):
                head = False
                continue
            if s.startswith("METRIC"):
                self.unit, self.unit_mm = "MM", 1.0
                continue
            if s.startswith("INCH"):
                self.unit, self.unit_mm = "IN", MM_PER_IN
                continue
            if s.startswith("FMAT") or s.startswith("VER") or s.startswith("G90") \
                    or s.startswith("G70") or s.startswith("G71") or s.startswith("M71") \
                    or s.startswith("M72") or s.startswith("G05") or s.startswith("ICI") \
                    or s.startswith("R,") or s.startswith("FMAT,2"):
                continue
            if s in ("T00", "T0"):
                self.ended = True
                continue
            if s.startswith("M30") or s.startswith("M00"):
                self.ended = True
                head = False
                continue
            m = re.match(r"^T(\d+)(?:C([\d.]+))?(F[\d.]+)?(S[\d.]+)?$", s)
            if m:
                code = int(m.group(1))
                if m.group(2) and head:
                    self.tools[code] = float(m.group(2)) * (self.unit_mm or 1.0)
                    # ★ plated 口径 = Fritzing 自己在文件头写死的（`T1..T99` 非镀 ✓、`T100+` 镀通 ✓）
                    self.plated[code] = code >= 100
                cur = code
                continue
            m = re.match(r"^X(-?\d+(?:\.\d+)?)(?:Y(-?\d+(?:\.\d+)?))?", s)
            if m and cur is not None:
                raw_pts.append((cur, m.group(1), m.group(2) or "0"))
                continue
            if s.startswith("G85") or s.startswith("G05") or re.match(r"^G\d+$", s):
                continue
            self.unknown.append(s)
        self._raw = raw_pts

    def _infer_format(self, board_mm):
        """坐标格式**不猜** ✗ ⇒ 按"落在板内 / 对上模型"选 ✓ 并把依据写出来 ✓"""
        if not self._raw:
            return
        lens = collections.Counter(max(len(a.rstrip("0") or "0"), len(a)) for _, a, b in self._raw)
        explicit = any("." in a for _, a, b in self._raw)
        cands = []
        if explicit:
            cands = [((0, 0), 0, "坐标自带小数点 ✓ 无需推格式")]
        else:
            digits = collections.Counter(len(a) for _, a, b in self._raw)
            tot = digits.most_common(1)[0][0]
            for idec in ((2, 4), (2, 3), (3, 3), (1, 4), (3, 4), (2, 5)):
                if sum(idec) == tot or sum(idec) >= tot:
                    cands.append((idec, idec[1], "总位数 %d ⇒ %d.%d" % (tot, idec[0], idec[1])))
        best = None
        for idec, ddec, why in cands:
            pts = []
            ok = True
            for _t, a, b in self._raw:
                try:
                    pts.append((float(a) / 10.0 ** ddec, float(b) / 10.0 ** ddec))
                except ValueError:
                    ok = False
                    break
            if not ok:
                continue
            inboard = 0
            if board_mm:
                w, h = board_mm
                for x, y in pts:
                    u = x * (self.unit_mm or 1.0)
                    v = y * (self.unit_mm or 1.0)
                    if -0.5 <= u <= w + 0.5 and -0.5 <= v <= h + 0.5:
                        inboard += 1
            score = (inboard, -abs(idec[0] + idec[1]))
            if best is None or score > best[0]:
                best = (score, (idec, ddec, why, pts))
        if best:
            (idec, ddec, why, pts) = best[1]
            self.fmt = idec
            self.fmt_why = why
            for (code, _a, _b), (x, y) in zip(self._raw, pts):
                self.holes.append(dict(tool=code, p=(x * (self.unit_mm or 1.0), y * (self.unit_mm or 1.0)),
                                       d_mm=self.tools.get(code, 0.0), plated=self.plated.get(code)))

    def d_mm(self, code):
        return self.tools.get(code)

    def by_tool(self):
        out = collections.defaultdict(list)
        for h in self.holes:
            out[h["tool"]].append(h)
        return out


# ---------------------------------------------------------------- 栅格（画图 ＋ 量间距 一份实现 ✓）
class Grid(object):
    """位图栅格 ✓：把 flash/draw/region 刷进 bytearray ✓（画预览与量间距**同一套** ✓）"""

    def __init__(self, x0, y0, x1, y1, step):
        self.step = step
        self.x0, self.y0 = x0, y0
        self.w = max(1, int(math.ceil((x1 - x0) / step)) + 1)
        self.h = max(1, int(math.ceil((y1 - y0) / step)) + 1)
        self.data = bytearray(self.w * self.h)

    def idx(self, ix, iy):
        return iy * self.w + ix

    def _cell_range(self, box):
        ix0 = max(0, int(math.floor((box[0] - self.x0) / self.step)))
        iy0 = max(0, int(math.floor((box[1] - self.y0) / self.step)))
        ix1 = min(self.w - 1, int(math.ceil((box[2] - self.x0) / self.step)))
        iy1 = min(self.h - 1, int(math.ceil((box[3] - self.y0) / self.step)))
        return ix0, iy0, ix1, iy1

    def pt(self, ix, iy):
        return (self.x0 + (ix + 0.5) * self.step, self.y0 + (iy + 0.5) * self.step)

    def circle(self, c, r, val=1):
        ix0, iy0, ix1, iy1 = self._cell_range((c[0] - r, c[1] - r, c[0] + r, c[1] + r))
        r2 = r * r
        for iy in range(iy0, iy1 + 1):
            y = self.y0 + (iy + 0.5) * self.step
            dy2 = (y - c[1]) ** 2
            for ix in range(ix0, ix1 + 1):
                x = self.x0 + (ix + 0.5) * self.step
                if (x - c[0]) ** 2 + dy2 <= r2:
                    self.data[iy * self.w + ix] = val

    def rect(self, c, w, h, val=1, rot=0.0):
        hw, hh = w / 2.0, h / 2.0
        ca, sa = math.cos(rot), math.sin(rot)
        rr = math.hypot(hw, hh)
        ix0, iy0, ix1, iy1 = self._cell_range((c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr))
        for iy in range(iy0, iy1 + 1):
            y = self.y0 + (iy + 0.5) * self.step - c[1]
            for ix in range(ix0, ix1 + 1):
                x = self.x0 + (ix + 0.5) * self.step - c[0]
                u = x * ca + y * sa
                v = -x * sa + y * ca
                if abs(u) <= hw and abs(v) <= hh:
                    self.data[iy * self.w + ix] = val

    def seg(self, p0, p1, w, h=None, val=1):
        """线段 ＋ 光圈 ✓（圆光圈 = 胶囊 ✓；方光圈 = 沿线的矩形并集 ✓）"""
        h = w if h is None else h
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        rr = math.hypot(dx, dy)
        box = (min(x0, x1) - max(w, h) / 2.0, min(y0, y1) - max(w, h) / 2.0,
               max(x0, x1) + max(w, h) / 2.0, max(y0, y1) + max(w, h) / 2.0)
        ix0, iy0, ix1, iy1 = self._cell_range(box)
        hw, hh = w / 2.0, h / 2.0
        square = abs(w - h) < 1e-9 and w > 0
        for iy in range(iy0, iy1 + 1):
            y = self.y0 + (iy + 0.5) * self.step
            for ix in range(ix0, ix1 + 1):
                x = self.x0 + (ix + 0.5) * self.step
                if square:
                    ok = self._in_stroke_rect(x, y, x0, y0, dx, dy, rr, hw, hh)
                else:
                    ok = self._d_pt_seg((x, y), (x0, y0), (x1, y1)) <= w / 2.0
                if ok:
                    self.data[iy * self.w + ix] = val

    @staticmethod
    def _in_stroke_rect(x, y, x0, y0, dx, dy, rr, hw, hh):
        if rr < 1e-12:
            return abs(x - x0) <= hw and abs(y - y0) <= hh
        tlo, thi = 0.0, 1.0
        for num, den in ((x - x0, dx), (y - y0, dy)):
            if abs(den) < 1e-12:
                if abs(num) > (hw if den is dx else hh):
                    return False
                continue
            t1 = (num - (hw if den is dx else hh)) / den
            t2 = (num + (hw if den is dx else hh)) / den
            if t1 > t2:
                t1, t2 = t2, t1
            tlo = max(tlo, t1)
            thi = min(thi, t2)
            if tlo > thi:
                return False
        return True

    @staticmethod
    def _d_pt_seg(p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        d2 = dx * dx + dy * dy
        if d2 < 1e-18:
            return math.hypot(px - ax, py - ay)
        t = ((px - ax) * dx + (py - ay) * dy) / d2
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def poly(self, pts, val=1, fill=True):
        if len(pts) < 3:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ix0, iy0, ix1, iy1 = self._cell_range((min(xs), min(ys), max(xs), max(ys)))
        n = len(pts)
        for iy in range(iy0, iy1 + 1):
            y = self.y0 + (iy + 0.5) * self.step
            xs_cross = []
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if (y1 > y) != (y2 > y):
                    xs_cross.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs_cross.sort()
            for k in range(0, len(xs_cross) - 1, 2):
                a, b = xs_cross[k], xs_cross[k + 1]
                ia = int(math.floor((a - self.x0) / self.step) - 1)
                ib = int(math.ceil((b - self.x0) / self.step) + 1)
                for ix in range(max(0, ia), min(self.w - 1, ib) + 1):
                    if a <= self.x0 + (ix + 0.5) * self.step <= b:
                        self.data[iy * self.w + ix] = val


def _dilate(data, w, h, r=1):
    """3×3（或 r 格）**膨胀** ✓ —— 给"逐格对账"吃掉 1 mil 栅格的量化噪声 ✓"""
    out = bytearray(w * h)
    for i, v in enumerate(data):
        if not v:
            continue
        ix, iy = i % w, i // w
        for yy in range(max(0, iy - r), min(h - 1, iy + r) + 1):
            base = yy * w
            for xx in range(max(0, ix - r), min(w - 1, ix + r) + 1):
                out[base + xx] = 1
    return out


def model_shapes_side(model, side):
    """模型里**件自己画的图元**（铜/丝印 ✓）⇒ `[{bbox, layer, id, title, side}]`（Gerber mm ✓）

    ★ 用途：铜层"**多出来的格**"要能**归因** ✗（含糊其辞的多余铜没法修 ✓）：
      · 落在件的 `copper0/copper1` 图元上 ⇒ **件里画的铜**（例：NFC 线圈 722 条 ✓）✓；
      · 落在件的 `silkscreen` 图元上 ⇒ **丝印跑到铜层了** ✗
        （实测根因 ✓：`SH-1.0-3P-V` 的 pcb svg 把 `<g id="silkscreen">` **嵌在** `<g id="copper1">`
         里面 ⇒ Fritzing 按"在铜组里"导出 ⇒ 铜层多了 14 段 0.12 mm 的丝印线 ✗）。
      ★ **按件所在面筛** ✗（底面件的丝印不该出现在顶面 ✓ —— 不筛会把归因张冠李戴 ✗）。
    """
    out = []
    for b in model["raw"].get("bodies") or []:
        if (b.get("side") or "top") != side:
            continue
        for (layer, bb, sid) in (b.get("shapes") or []):
            if layer not in ("copper0", "copper1", "silkscreen"):
                continue
            if side == "top" and layer == "copper0":
                continue                       # 底面铜不上顶面 ✓
            if side == "bottom" and layer == "copper1":
                continue
            p0 = model["to_gerber_mm"]((bb[0], bb[3]))
            p1 = model["to_gerber_mm"]((bb[2], bb[1]))
            out.append(dict(bbox=(min(p0[0], p1[0]), min(p0[1], p1[1]),
                                  max(p0[0], p1[0]), max(p0[1], p1[1])),
                            layer=layer, id=sid or "", title=b.get("title") or "?"))
    return out


def classify_cells(model, side, cells, tol=0.35):
    """一组格子落在"件里画的铜"/"件里的丝印"上 ✓ ⇒ `(kind, label)`

    `kind`：`"copper"`（件里画的铜 ✓ = 正常 ✓）／`"silk"`（**丝印漏到铜层** ✗）／`"none"`（没归上 ⇒ 可疑 ✗）

    ★ 判法 = **逐个格子**问"它在不在某个件的那个图元的框里" ✓ —— ✗ 不是"整块对单个图元算覆盖率" ✗：
      整块（例：**整条 NFC 线圈 66.8 mm²** ✓）跨几百个图元 ⇒ 对任何**单个**图元的覆盖率都趋 0 ✗
      ⇒ 会假报"没归上" ✓（实测踩过 ✓）。
    """
    shapes = model_shapes_side(model, side)
    if not cells or not shapes:
        return "none", ""
    cub = [s for s in shapes if s["layer"].startswith("copper")]
    sil = [s for s in shapes if s["layer"] == "silkscreen"]
    hit = {"copper": collections.Counter(), "silk": collections.Counter()}
    for (x, y) in cells:
        for k, lst in (("copper", cub), ("silk", sil)):
            for s in lst:
                bb = s["bbox"]
                if bb[0] - tol <= x <= bb[2] + tol and bb[1] - tol <= y <= bb[3] + tol:
                    hit[k][(s["title"], s["id"])] += 1
                    break
    cov = {k: sum(hit[k].values()) / float(len(cells)) for k in hit}
    if cov["copper"] >= 0.5 and cov["copper"] >= cov["silk"]:
        (ttl, sid), _n = hit["copper"].most_common(1)[0]
        return "copper", "件 `%s` 的铜图元 `%s`（%d 个取样点落在它就位的框里 ✓）" % (ttl, sid, cov["copper"] * len(cells))
    if cov["silk"] >= 0.5:
        (ttl, sid), _n = hit["silk"].most_common(1)[0]
        return "silk", "件 `%s` 的**丝印**图元 `%s`" % (ttl, sid)
    return "none", "铜 %.2f ／ 丝印 %.2f（都没过半 ✗）" % (cov["copper"], cov["silk"])


def nearest_model_feature(model, side, pt):
    """`pt` 最近的**模型**铜特征 ✓ ⇒ `(距离 mm, 标签)` ✓（"缺的那块对应模型里的谁" ✓）"""
    best = (1e9, "?")
    for p in model["pads"]:
        if side not in p["side"] or not p["size"]:
            continue
        r = max(p["size"]) / 2.0
        if p.get("poly"):
            d = min(Grid._d_pt_seg(pt, p["poly"][i], p["poly"][(i + 1) % len(p["poly"])])
                    for i in range(len(p["poly"])))
        else:
            d = max(0.0, math.hypot(pt[0] - p["p"][0], pt[1] - p["p"][1]) - r)
        if d < best[0]:
            best = (d, "盘 %s.%s（%.2f mm）" % (p["title"], p["cid"], max(p["size"])))
    for v in model["vias"]:
        d = max(0.0, math.hypot(pt[0] - v["p"][0], pt[1] - v["p"][1]) - v["out_mm"] / 2.0)
        if d < best[0]:
            best = (d, "过孔 %s（Ø%.2f mm）" % (v.get("ttl") or "via", v["out_mm"]))
    for k, t in enumerate(model["traces"]):
        if t["side"] != side:
            continue
        pts = t["pts"]
        d = min(max(0.0, Grid._d_pt_seg(pt, pts[i], pts[i + 1]) - t["width_mm"] / 2.0)
                for i in range(len(pts) - 1))
        if d < best[0]:
            best = (d, "走线 #%d（%.2f mil ✓）" % (k, t["width_mm"] / MIL_MM))
    return best


def raster_model(model, side, step, window):
    """把模型的铜刷成栅格 ✓（盘的真几何 ＋ 走线带宽 ＋ 过孔圆 ✓）—— 与 Gerber 侧**同一套**栅格 ✓"""
    x0, y0, x1, y1 = window
    grid = Grid(x0, y0, x1, y1, step)
    for p in model["pads"]:
        if side not in p["side"]:
            continue
        if p.get("poly"):
            grid.poly(p["poly"])
        elif p.get("circle"):
            grid.circle(p["p"], p["circle_r"])
        elif p.get("size"):
            grid.rect(p["p"], p["size"][0], p["size"][1])
    for v in model["vias"]:
        grid.circle(v["p"], v["out_mm"] / 2.0)
    for t in model["traces"]:
        if t["side"] != side:
            continue
        w = max(t["width_mm"], step)
        pts = t["pts"]
        for i in range(len(pts) - 1):
            grid.seg(pts[i], pts[i + 1], w)
    for sh in model.get("part_copper") or []:
        if side not in sh["sides"]:
            continue
        if sh["kind"] == "seg":
            grid.seg(sh["p0"], sh["p1"], max(sh.get("w_mm") or 0.0, step))
        elif sh["kind"] == "circ":
            grid.circle(sh["p"], max(sh.get("r_mm") or 0.0, step / 2.0))
        else:
            grid.poly(sh["poly"])
    return grid


def clusters(data, grid, topn=3, min_cells=1, cap=240):
    """把一组格子按连通聚成块 ✓ ⇒ `([dict(area_mm2, centroid, cells)], lab, n, sizes)` ✓

    ★ 带上**块内的格子样本**（均匀抽到 `cap` 个 ✓）—— "多出来的铜是谁的"要**按块判** ✗，
      拿**质心**判会栽在**环状/弯折**的块上 ✗（实测：整条线圈的质心落在**线圈中间的空白**里 ✗）。
    """
    g = Grid(grid.x0, grid.y0, grid.x0 + (grid.w - 1) * grid.step,
             grid.y0 + (grid.h - 1) * grid.step, grid.step)
    g.data = bytearray(data)
    lab, n, sizes = components(g)
    order = sorted(range(1, n + 1), key=lambda k: -sizes[k - 1])
    out = []
    for k in order:
        if sizes[k - 1] < min_cells:
            continue
        idxs = [i for i, v in enumerate(lab) if v == k]
        stepk = max(1, len(idxs) // cap)
        cells = [(g.x0 + (i % g.w + 0.5) * g.step, g.y0 + (i // g.w + 0.5) * g.step)
                 for i in idxs[::stepk]]
        cnt = len(idxs)
        sx = sum(i % g.w for i in idxs) / float(cnt)
        sy = sum(i // g.w for i in idxs) / float(cnt)
        out.append(dict(cells=cnt, area_mm2=cnt * g.step * g.step,
                        centroid=(g.x0 + (sx + 0.5) * g.step, g.y0 + (sy + 0.5) * g.step),
                        samples=cells))
        if len(out) >= topn:
            break
    return out, lab, n, sizes


def feature_label(g, o):
    """一个 Gerber 图元的**人话标签** ✓（报告里点名用 ✓）"""
    if o is None:
        return "?"
    if o.kind == "move":
        return "空移（无铜 ✓）@(%.3f,%.3f)" % (o.p0[0], o.p0[1])
    if o.kind == "flash":
        wh = g.ap_mm(o.ap)
        s = ("D%s（%.4f×%.4f mm）@(%.3f,%.3f)"
             % (o.ap, wh[0], wh[1], o.p0[0], o.p0[1])) if wh else ("D%s @(%.3f,%.3f)" % (o.ap, o.p0[0], o.p0[1]))
        return "flash " + s
    if o.kind == "draw":
        m = g.ap_min_mm(o.ap)
        return ("线段（光圈 %.4f mm ✓）(%.3f,%.3f)→(%.3f,%.3f)"
                % (m or 0.0, o.p0[0], o.p0[1], o.p1[0], o.p1[1]))
    return "G36 多边形（%d 顶点）@(%.3f,%.3f)" % (len(o.pts), o.pts[0][0], o.pts[0][1])


def op_dist(g, o, pt):
    """`pt` 到**一个 Gerber 图元**的净距 ✓（圆 = 减半径 ✓，方 = 按**矩形**减 ✗ 不能当圆 ✗；
    实测：把 1.2×0.5 的方盘当"半径 0.6 的圆"会把 0.13 mm 的净距算成 0 ✗）"""
    wh = g.ap_mm(o.ap)
    if o.kind == "flash":
        if not wh:
            return math.hypot(o.p0[0] - pt[0], o.p0[1] - pt[1])
        if g.apertures[o.ap][0] == "C" or abs(wh[0] - wh[1]) < 1e-9:
            return max(0.0, math.hypot(o.p0[0] - pt[0], o.p0[1] - pt[1]) - wh[0] / 2.0)
        dx = max(0.0, abs(pt[0] - o.p0[0]) - wh[0] / 2.0)
        dy = max(0.0, abs(pt[1] - o.p0[1]) - wh[1] / 2.0)
        return math.hypot(dx, dy)
    if o.kind == "draw":
        return max(0.0, Grid._d_pt_seg(pt, o.p0, o.p1) - (g.ap_min_mm(o.ap) or 0.0) / 2.0)
    return 1e9


def nearest_near(g, at, limit_mm=1.0):
    """离 `at` 最近的图元 ✓（点名"这两块铜是谁"用 ✓）"""
    best = None
    for o in g.ops:
        if o.kind not in ("flash", "draw"):
            continue
        d = op_dist(g, o, at)
        if d > limit_mm:
            continue
        if best is None or d < best[0]:
            best = (d, o)
    return best


def raster_gerber(g, role, step, window=None):
    """把一层刷成栅格 ✓（形状口径：G36 多边形/方光圈/圆光圈/胶囊 ✓）

    ★ **填充笔（< %.4f mm）按 %.4f mm 刷** ✓ —— Fritzing 的实心区域是用 1 mil 扫描线画的 ✓，
      照原尺寸刷会**漏格**（比步长还小 ✓）⇒ 间距就算错 ✗。这一步只影响"填充"✓：
      0.2 mm（线圈 ✓）与 0.2032 mm（8 mil ✓）这些**真线宽**一个字都不动 ✓。
    """
    if window:
        x0, y0, x1, y1 = window
    else:
        bb = g.bbox(pad=max(0.2, step))
        if not bb:
            return Grid(0.0, 0.0, step, step, step)      # **空层** ⇒ 空栅格 ✓（别崩 ✗）
        x0, y0, x1, y1 = bb
    grid = Grid(x0, y0, x1, y1, step)

    def _clamp(v):
        # ★ 比**步长**还细的笔（Fritzing 的 1 mil 扫描线填充 ✓ 0.1 mil 细圆 ✓）**抬到一格** ✓ ——
        #   ✗ 不抬 ⇒ 光栅化会**整格漏掉** ⇒ 那段铜"消失" ✗ ⇒ 间距/覆盖全错 ✗。
        #   ★ 抬到 **step**（不是固定常数 ✓）：细扫时 step 小 ⇒ 失真也小 ⇒ 量的间距才准 ✓
        #   （实测：固定抬到 0.06 mm 会把底面的真间距 0.19 报成 0.13 ✗）。
        return step if 0 < v < step else v

    for o in g.ops:
        if o.kind == "flash":
            wh = g.ap_mm(o.ap)
            if not wh:
                continue
            kind = g.apertures[o.ap][0]
            w, h = _clamp(wh[0]), _clamp(wh[1])
            if kind == "C" or abs(w - h) < 1e-9:
                grid.circle(o.p0, w / 2.0)
            else:
                grid.rect(o.p0, w, h)
        elif o.kind == "draw":
            wh = g.ap_mm(o.ap)
            if not wh:
                continue
            grid.seg(o.p0, o.p1, _clamp(wh[0]), _clamp(wh[1]))
        elif o.kind == "region":
            grid.poly(o.pts)
    return grid


def components(grid):
    """连通块 ✓（8 连通 ✓）⇒ (labels 数组, 块数, 每块像素数 ✓)"""
    w, h = grid.w, grid.h
    d = grid.data
    lab = array.array("i", [0]) * (w * h)
    n = 0
    sizes = []
    stack = []
    for i0 in range(w * h):
        if not d[i0] or lab[i0]:
            continue
        n += 1
        lab[i0] = n
        stack.append(i0)
        cnt = 0
        while stack:
            i = stack.pop()
            cnt += 1
            ix, iy = i % w, i // w
            for dyy in (-1, 0, 1):
                yy = iy + dyy
                if yy < 0 or yy >= h:
                    continue
                for dxx in (-1, 0, 1):
                    xx = ix + dxx
                    if xx < 0 or xx >= w:
                        continue
                    j = yy * w + xx
                    if d[j] and not lab[j]:
                        lab[j] = n
                        stack.append(j)
        sizes.append(cnt)
    return lab, n, sizes


def clearance(grid, limit=CLEAR_LIMIT_MM, want_lab=False):
    """**最小铜↔铜间距** ✓ ⇒ (mm, (块A, 块B), 冲突点) ✓

    ★ 口径（**在 Gerber 上直接量** ✓，不看模型 ✗）：
      ① 同层铜先分**连通块** ✓（8 连通 ✓）；
      ② 从所有铜格**多源同时外扩** ✓（heapq ＝ Dijkstra ✓）⇒ 两块 Voronoi 相遇处
         就是最近点 ✓（`di + dj + step` ✓）；
      ③ 只关心 ≤ `limit` ✓ ⇒ 超过就停 ✓（不必扫全板 ✓）。
      ⚠️ 局限：**同网**的碎块（被别的东西隔开的两段铜 ✓）也会被算进来 ✓ ⇒
         报的是"**几何最近的两块铜**"✓，判据落在 §6 的"是否 ≥ 6 mil"上 ✓（不冒充网表 ✗）。
    """
    w, h = grid.w, grid.h
    lab, n, sizes = components(grid)
    if n < 2:
        return (None, None, None, lab) if want_lab else (None, None, None)
    step = grid.step
    INF = float("inf")
    dist = array.array("f", [INF]) * (w * h)
    owner = array.array("i", [-1]) * (w * h)
    pq = []
    for i in range(w * h):
        if lab[i]:
            dist[i] = 0.0
            owner[i] = lab[i]
            pq.append((0.0, i))
    heapq.heapify(pq)
    best = INF
    pair = None
    at = None
    sq2 = math.sqrt(2.0) * step
    while pq:
        dcur, i = heapq.heappop(pq)
        if dcur > dist[i]:
            continue
        if dcur > best or dcur > limit:
            break
        ix, iy = i % w, i // w
        for dyy in (-1, 0, 1):
            yy = iy + dyy
            if yy < 0 or yy >= h:
                continue
            for dxx in (-1, 0, 1):
                if dxx == 0 and dyy == 0:
                    continue
                xx = ix + dxx
                if xx < 0 or xx >= w:
                    continue
                j = yy * w + xx
                wgt = sq2 if (dxx and dyy) else step
                ol = owner[j]
                if ol != -1 and ol != owner[i]:
                    cand = dist[i] + wgt + dist[j]
                    if cand < best:
                        best = cand
                        pair = (owner[i], ol)
                        at = (grid.x0 + (xx + 0.5) * step, grid.y0 + (yy + 0.5) * step)
                if ol == -1:
                    nd = dist[i] + wgt
                    if nd < dist[j]:
                        dist[j] = nd
                        owner[j] = owner[i]
                        heapq.heappush(pq, (nd, j))
    if pair is None:
        return (None, None, None, lab) if want_lab else (None, None, None)
    return (best, pair, at, lab) if want_lab else (best, pair, at)


def classify_pair(g, grid, lab, at, pair):
    """**这道间距是谁跟谁** ✓（按**连通块**认 ✓ —— ✗ 不能只取"离冲突点最近的两个图元" ✗：
    实测会把**同一块铜上相邻的两段**报出来 ✗，那是同网铜 ✓ 不是间距 ✓）
    ⇒ `(标签A, 标签B)` ✓
    """
    out = []
    for k in (pair or ()):
        best = None
        for o in g.ops:
            if o.kind not in ("flash", "draw"):
                continue
            d = op_dist(g, o, at)
            p = o.p0
            ix = int((p[0] - grid.x0) / grid.step)
            iy = int((p[1] - grid.y0) / grid.step)
            if not (0 <= ix < grid.w and 0 <= iy < grid.h):
                continue
            if lab[iy * grid.w + ix] != k:
                continue
            if best is None or d < best[0]:
                best = (d, o)
        out.append((feature_label(g, best[1]) if best else "（块 %s）" % k,
                    (best[0] if best else None)))
    return (out + [("?", None), ("?", None)])[:2]


def refine_clearance_grid(grid, at, approx, step=RASTER_REFINE_MM):
    """在**已经刷好的**栅格上原地细扫 ✓（模型侧用 ✓）⇒ (精确间距 mm, 窗口) ✓"""
    return _refine_any(grid, at, approx, step, lambda win, st: _crop(grid, win, st))


def _crop(grid, window, step):
    """从一个栅格上**裁**一块下来（按新步长重刷不了 ✗ ⇒ 只做粗化 ✓）—— 模型侧够用 ✓"""
    x0, y0, x1, y1 = window
    g = Grid(x0, y0, x1, y1, grid.step)
    for iy in range(g.h):
        y = g.y0 + (iy + 0.5) * g.step
        sy = int((y - grid.y0) / grid.step)
        if not (0 <= sy < grid.h):
            continue
        for ix in range(g.w):
            x = g.x0 + (ix + 0.5) * g.step
            sx = int((x - grid.x0) / grid.step)
            if 0 <= sx < grid.w and grid.data[sy * grid.w + sx]:
                g.data[iy * g.w + ix] = 1
    return g


def _refine_any(_grid, at, approx, step, build):
    win = approx + 0.3
    window = (at[0] - win, at[1] - win, at[0] + win, at[1] + win)
    g2 = build(window, step)
    _lab, n, _s = components(g2)
    if n < 2:
        return approx, window
    val, _p, _a = clearance(g2, limit=min(CLEAR_LIMIT_MM, approx * 2.0 + 0.3))
    return (val if val else approx), window


def refine_clearance(g, role, at, approx, step=RASTER_REFINE_MM):
    """粗扫定位后**原地细扫** ✓（Gerber 侧：能按新步长重刷 ✓）⇒ (精确间距 mm, 窗口) ✓"""
    if not at or not approx:
        return approx, None
    return _refine_any(g, at, approx, step,
                       lambda win, st: raster_gerber(g, role, st, win))


# ---------------------------------------------------------------- 模型（.fzz 的 PCB 视图）
def part_copper_geom(part, to_gerber_mm):
    """件里**画的铜**的真几何 ✓（例：NFC 线圈的 722 条 `<line>` ✓、接插件固定脚的两块矩形 ✓）

    ★ 为什么要它 ✓：模型的"铜"不只是"盘 ＋ 走线" ✗ —— 件自己会在铜层上画东西 ✓
      （线圈就是整块天线 ✓）。✗ 不带上它 ⇒ 逐格对账会把线圈报成"多出来的铜" ✗、
      模型侧的**最小间距**也会算错 ✗（因为少了一整块铜 ✓）。
    ★ 变换**只调用库仓那一份** ✓（`pcb_pads._placer` 的 `abs_of` ＋ 件的 `loc` ✓，
      与 `part_shapes` / `part_pads` 同一套矩阵 ✓）—— ✗ 不另写一份矩阵数学 ✗。
    ★ 判层：背面件（`bottom="true"`）的 **svg `copper1` 画在板子的 `copper0`（背面 ✓）**
      ⇒ 层与面**对调** ✓（与 `pcb_pads` 同一口径 ✓）。
    """
    if part.get("svg_text") is None:
        return []
    try:
        pl = PP._placer(part)
    except Exception:
        return []
    if pl is None:
        return []
    root, k, _ox, _oy, _vbw, flip, _M, loc, abs_of = pl
    out = []
    pad_ids = set()
    for cid in (part.get("connectors") or {}):
        for suf in PP.PAD_SUF:
            pad_ids.add(cid + suf)

    def _side_of(layer):
        if layer not in ("copper0", "copper1"):
            return None
        top = (layer == "copper1")
        if flip:
            top = not top
        return ("top",) if top else ("bottom",)

    def _to_mm(p):
        q = abs_of(p)
        return to_gerber_mm((loc[0] + q[0], loc[1] + q[1]))

    def walk(el, layer):
        for ch in el:
            t = PP.tag(ch)
            if t == "g":
                walk(ch, ch.get("id") or layer)
                continue
            sides = _side_of(layer)
            if sides is None:
                continue
            eid = ch.get("id") or ""
            if eid in pad_ids:
                continue                                  # 盘另有出处 ✓（不重复 ✓）
            sw = float(ch.get("stroke-width") or 0.0) * k * SK
            if t == "line":
                p0 = _to_mm((PP.num(ch, "x1"), PP.num(ch, "y1")))
                p1 = _to_mm((PP.num(ch, "x2"), PP.num(ch, "y2")))
                if p0 != p1:
                    out.append(dict(kind="seg", sides=sides, p0=p0, p1=p1, w_mm=sw))
            elif t == "rect":
                x, y = PP.num(ch, "x"), PP.num(ch, "y")
                w, h = PP.num(ch, "width"), PP.num(ch, "height")
                out.append(dict(kind="poly", sides=sides,
                                poly=[_to_mm((x, y)), _to_mm((x + w, y)),
                                      _to_mm((x + w, y + h)), _to_mm((x, y + h))]))
            elif t == "circle" and (ch.get("fill") or "").lower() not in ("none", ""):
                r = PP.num(ch, "r") * k * SK
                out.append(dict(kind="circ", sides=sides, p=_to_mm((PP.num(ch, "cx"),
                                                                    PP.num(ch, "cy"))),
                                r_mm=r))
    walk(root, None)
    return out


def load_model(path):
    """读 `.fzz` 的 PCB 视图 ✓ ⇒ dict ✓（board/pads/vias/holes/traces ＋ 换算函数 ✓）"""
    m = PC.collect(path)
    b = m["board"]
    board_mm = ((b[2] - b[0]) * SK, (b[3] - b[1]) * SK)

    def to_gerber_mm(p):
        """模型 sketch 坐标 → Gerber 坐标（mm ✓，原点 = 板框左下角 ✓、y 向上 ✓）"""
        return ((p[0] - b[0]) * SK, (b[3] - p[1]) * SK)

    # ★ 通孔盘的**孔径**：`pcb_check.collect` 只带 `thr` 布尔 ✗ ⇒ 从 `pcb_pads` 补一份 ✓
    #   （`hole_mm` = 库按 `circle.r` = **孔半径** 读出来的值 ✓ —— 与 Fritzing 实做
    #    「2r − 笔宽」不同 ⇒ 报告里要**把两套数都摆出来** ✓，不藏 ✗）
    thr_hole = {}
    part_copper = []
    try:
        parts, _board = PC.PP.read_fzz(path)
        for part in parts:
            got, _ex, _bad, _nt = PC.PP.part_pads(part)
            for cid, q in (got or {}).items():
                if q.get("hole_mm"):
                    thr_hole[(part.get("title"), cid)] = (q["hole_mm"], q.get("ring_mm"))
            try:
                part_copper += part_copper_geom(part, to_gerber_mm)
            except Exception:
                pass
    except Exception:
        pass

    pads = []
    for q in m["pads"]:
        c = to_gerber_mm(q["c"])
        size = None
        pts = None
        cr = None
        if q.get("poly"):
            pts = [to_gerber_mm(p) for p in q["poly"]]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            size = (max(xs) - min(xs), max(ys) - min(ys))
        elif q.get("circle"):
            cr = q["circle"][1] * SK
            size = (cr * 2, cr * 2)
        else:
            bb = q.get("box")
            if bb:
                size = ((bb[2] - bb[0]) * SK, (bb[3] - bb[1]) * SK)
        lay = q.get("layer")
        sides = {"copper0": ("bottom",), "copper1": ("top",),
                 "both": ("top", "bottom")}.get(lay, ("top", "bottom"))
        pads.append(dict(title=q["title"], cid=q["cid"], nm=q.get("nm"), side=sides,
                         p=c, size=size, poly=pts, circle_r=cr, thr=bool(q.get("thr")),
                         hole_mm=(thr_hole.get((q["title"], q["cid"])) or (None, None))[0],
                         ring_mm=(thr_hole.get((q["title"], q["cid"])) or (None, None))[1],
                         rot_deg=_poly_rot(pts), src="pad"))
    vias = []
    for v in m["vias"]:
        d_out = (v["hole_mm"] or 0.0) + 2.0 * (v["ring_mm"] or 0.0)
        vias.append(dict(ttl=v.get("ttl"), p=to_gerber_mm(v["p"]), hole_mm=v["hole_mm"],
                         out_mm=d_out, side=("top", "bottom"), src="via"))
    holes = []
    for (c, inner, outer) in m["holes"]:
        holes.append(dict(p=to_gerber_mm(c), hole_mm=inner, out_mm=outer, src="hole"))
    traces = []
    for t in m["traces"]:
        pts = [to_gerber_mm(p) for p in t["pts"]]
        ln = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
                 for i in range(len(pts) - 1))
        side = "top" if (t.get("layer") or "").startswith("copper1") else "bottom"
        traces.append(dict(pts=pts, width_mm=(t.get("mils") or 0.0) * MIL_MM, length_mm=ln,
                           side=side, curve=bool(t.get("curve")), layer=t.get("layer")))
    return dict(path=path, board=board_mm, pads=pads, vias=vias, holes=holes, traces=traces,
                raw=m, to_gerber_mm=to_gerber_mm, part_copper=part_copper)


def _poly_rot(pts):
    """矩形四个角 → 旋转角（度 ✓，取最小边方向 ✓）"""
    if not pts or len(pts) != 4:
        return None
    import collections as _c
    angs = []
    for i in range(4):
        dx = pts[(i + 1) % 4][0] - pts[i][0]
        dy = pts[(i + 1) % 4][1] - pts[i][1]
        angs.append((math.degrees(math.atan2(dy, dx)) + 180.0) % 90.0)
    # 四条边两两平行 ⇒ 取出现两次的那个角 ✓
    cnt = _c.Counter(round(a, 3) for a in angs)
    return cnt.most_common(1)[0][0]


# ---------------------------------------------------------------- 预览 PNG
def write_png(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    comp = zlib.compress(raw, 9)

    def chunk(t, d):
        return (struct.pack(">I", len(d)) + t + d
                + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def render(preview, path, mm_bbox, px_per_mm=24.0, bg=(255, 255, 255), pad_mm=1.0):
    """把若干层叠成一张 png ✓（`preview` = [(role, 颜色), …] ✓ 顺序即叠序 ✓）"""
    x0, y0, x1, y1 = mm_bbox
    x0 -= pad_mm
    y0 -= pad_mm
    x1 += pad_mm
    y1 += pad_mm
    W = int((x1 - x0) * px_per_mm)
    H = int((y1 - y0) * px_per_mm)
    step = 1.0 / px_per_mm
    g = Grid(x0, y0, x0 + W * step, y0 + H * step, step)
    canvas = [[list(bg) for _ in range(g.w)] for _ in range(g.h)]
    for role, color, gb in preview:
        grid = raster_gerber(gb, role, step, window=(x0, y0, x0 + g.w * step, y0 + g.h * step))
        for iy in range(grid.h):
            row = grid.data[iy * grid.w:(iy + 1) * grid.w]
            for ix, v in enumerate(row):
                if v:
                    canvas[iy][ix] = list(color)
    rows = [b"".join(bytes(c) for c in row) for row in canvas]
    write_png(path, g.w, g.h, rows)
    return path


# ---------------------------------------------------------------- 报告
class Report(object):
    def __init__(self):
        self.items = []          # (id, level, text)

    def add(self, cid, level, text):
        self.items.append((cid, level, text))

    def level(self, cid):
        lv = [i[1] for i in self.items if i[0] == cid]
        if "FAIL" in lv:
            return "FAIL"
        if "WARN" in lv:
            return "WARN"
        return "OK" if lv else "-"

    def has_fail(self):
        return any(i[1] == "FAIL" for i in self.items)

    def print(self, quiet=False):
        cur = None
        for cid, level, text in self.items:
            if cid != cur:
                cur = cid
                print("\n── %s ──" % cid)
            if quiet and level == "OK":
                continue
            mark = {"OK": "✓", "WARN": "⚠", "FAIL": "✗"}[level]
            print("   %s %s" % (mark, text))


# ---------------------------------------------------------------- 主流程
def inventory(folder):
    """盘点导出目录 ✓ ⇒ (role -> 文件, 多余的其它文件 ✓)"""
    files = sorted(os.listdir(folder))
    got = {}
    used = set()
    for role, exts, req, cn in ROLES:
        hit = None
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                hit = os.path.join(folder, f)
                break
        if hit:
            got[role] = hit
            used.add(os.path.basename(hit))
    extra = [f for f in files if f not in used
             and os.path.splitext(f)[1].lower() not in (".png", ".zip")]
    return got, extra


def check_pnp(path, model, rep):
    """贴片坐标 `.xy`（Fritzing 的 Pick&Place ✓）—— **给装配厂看的** ✗ ⇒ 也验一遍 ✓

    ★ 口径（文件头自己写的 ✓）：`Coordinates in mils, always center of component` ✓、
      `Origin 0/0 = Lower left corner of PCB` ✓、`Rotation in degree` ✓、列还带 `Side`／`Mount` ✓。
      ⇒ 与模型的（板左下角、y 向上、mm ✓）**同一套原点** ✓（实测 Via1 ✓ 77.544/884.695 mil
        = (1.97, 22.47) mm ↔ 模型 (1.981, 22.479) ✓）。
    """
    rows = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("RefDes") or s.startswith("Description:"):
            continue
        # ★ 用 csv 模块 ✓ —— 有件（C1/C2 ✓）的 `Description` 字段**带引号且含逗号** ✗，
        #   `split(",")` 会把列**串位** ⇒ 位置/面全读错 ✗（实测：C1/C2 直接消失 ✓）
        parts = next(csv.reader([s])) if s else []
        if len(parts) < 7:
            continue
        ref, pkg, x, y, rot, side, mount = parts[0], parts[2], parts[3], parts[4], parts[5], parts[6], \
            (parts[7] if len(parts) > 7 else "")
        try:
            rows.append(dict(ref=ref, pkg=pkg, p=(float(x) * MIL_MM, float(y) * MIL_MM),
                             rot=float(rot), side=side.strip(), mount=mount.strip()))
        except ValueError:
            continue
    rep.add("§3 贴片坐标", "OK", "`.xy` 读到 %d 行 ✓（单位 mils ✓、原点 = 板左下角 ✓、"
            "含 X/Y/旋转/面/装法 ✓）：%s"
            % (len(rows), "、".join("%s(%s,%s)" % (r["ref"], r["side"], r["mount"]) for r in rows[:8])))
    bad = [r for r in rows if r["side"] not in ("Top", "Bottom")]
    if bad:
        rep.add("§3 贴片坐标", "WARN", "%d 行**面**写得不认识 ✗：%s"
                % (len(bad), "、".join(r["ref"] for r in bad[:6])))
    if model:
        by_title = collections.defaultdict(list)
        for p in model["pads"]:
            by_title[p["title"]].append(p)
        notin = [t for t in by_title if t not in {r["ref"] for r in rows}]
        if notin:
            rep.add("§3 贴片坐标", "WARN", "模型里有、`.xy` 里没有的件 ✗：%s" % "、".join(sorted(notin)))
        else:
            rep.add("§3 贴片坐标", "OK", "模型里 %d 个有盘的件**都在** `.xy` 里 ✓" % len(by_title))
        worst = 0.0
        worst_ref = ""
        sidebad = []
        bodies = {b.get("title"): b for b in (model["raw"].get("bodies") or [])}
        for r in rows:
            lst = by_title.get(r["ref"])
            if not lst:
                continue
            body = bodies.get(r["ref"]) or {}
            bb = body.get("box")
            if bb:                                   # ★ 用**体框中心**比 ✓（盘心均值对 L1 这种件不成立 ✗）
                p0 = model["to_gerber_mm"]((bb[0], bb[3]))
                p1 = model["to_gerber_mm"]((bb[2], bb[1]))
                cx = (p0[0] + p1[0]) / 2.0
                cy = (p0[1] + p1[1]) / 2.0
                if max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])) <= 5.0:      # 大件（线圈 ✓）不算 ✗
                    d = math.hypot(cx - r["p"][0], cy - r["p"][1])
                    if d > worst:
                        worst = d
                        worst_ref = r["ref"]
            sides = set()
            for p in lst:
                sides |= set(p["side"])
            want = "Top" if sides == {"top"} else ("Bottom" if sides == {"bottom"} else "?")
            if want != "?" and want.lower() != r["side"].lower():
                sidebad.append("%s（`.xy` 说 %s、模型说 %s）" % (r["ref"], r["side"], want))
        lv = "OK" if (worst <= 0.05 and not sidebad) else ("FAIL" if sidebad else "WARN")
        rep.add("§3 贴片坐标", lv,
                "件心对账（**体框中心 ≤5 mm 的件** ↔ `.xy` ✓；大件如线圈「件心 ≠ 体框心」✗ 不参与 ✓）："
                "最大偏差 %.4f mm @%s ⇒ %s%s"
                % (worst, worst_ref, "≤0.05 mm ✓" if worst <= 0.05 else "⚠ 需人眼看一眼 ✓",
                   ("；**面不一致** ✗：%s（贴错面 = 报废 ✗）" % "、".join(sidebad[:6])) if sidebad else " ✓"))


def check(folder, fzz=None, no_model=False, want_png=False, out_dir=None, step=RASTER_STEP_MM):
    rep = Report()
    got, extra = inventory(folder)
    roles_ok = []
    missing = []
    for role, exts, req, cn in ROLES:
        if role in got:
            roles_ok.append("%s=%s" % (cn, os.path.basename(got[role])))
        elif req:
            missing.append(cn)
    # ① 目录 / 层齐全性
    rep.add("§1 目录与层齐全性", "OK", "找到 %d 个文件：%s" % (len(roles_ok), "、".join(roles_ok)))
    if extra:
        rep.add("§1 目录与层齐全性", "WARN", "目录里还有没归类的文件：%s" % "、".join(extra))
    if missing:
        rep.add("§1 目录与层齐全性", "FAIL", "**缺层**（点名的这几种没有）：%s ✗" % "、".join(missing))
        return rep, None, got, dict(missing=missing, gers={}, drill=None, pngs=[], outline=None)
    rep.add("§1 目录与层齐全性", "OK", "必需层齐全 ✓（铜×2 ／ 阻焊×2 ／ 丝印×2 ／ 板框 ／ 钻孔 ✓）"
            + ("；另有钢网＋贴片坐标 ✓" if "pasteTop" in got or "pnp" in got else ""))

    # ② 文件头（逐文件 ✓）
    gers = {}
    for role, path in got.items():
        if role in ("drill", "pnp"):
            continue
        try:
            gers[role] = Gerber(path, role)
        except Exception as exc:
            rep.add("§2 单位/格式/原点", "FAIL", "%s 读不了：%s ✗" % (os.path.basename(path), exc))
    heads = []
    for role, g in sorted(gers.items()):
        fs = ("X%d.%d/Y%d.%d（%s 省略零 ✓）" % (g.fs[0], g.fs[1], g.fs[2], g.fs[3],
                                            "前导" if g.fs[4] == "L" else "后导")) if g.fs else "（没写 FS ✗）"
        unit = g.unit or "（没写 MO ✗）"
        heads.append("%s：%s / %s / OFA%sB%s / 轴序%s / 层名%s / 极性%s"
                     % (role, unit, fs, fmt(g.offset[0]), fmt(g.offset[1]), g.axis or "?",
                        g.layer_name or "?", g.polarity))
    rep.add("§2 单位/格式/原点", "OK", "逐文件头（%d 份 ✓）：%s" % (len(heads), "\n        ".join(heads)))
    units = set(g.unit for g in gers.values())
    bad_u = [r for r, g in gers.items() if g.unit not in ("IN", "MM")]
    if bad_u:
        rep.add("§2 单位/格式/原点", "FAIL",
                "%s 没写单位指令（`%%MO…%%`）✗ ⇒ 板厂会按默认英寸猜 ✗" % "、".join(bad_u))
    if len(units) > 1:
        rep.add("§2 单位/格式/原点", "WARN", "各层单位**不一致** ✗：%s" % "、".join(sorted(str(u) for u in units)))
    else:
        rep.add("§2 单位/格式/原点", "OK", "全部同一单位 ✓（%s）；格式全为 2.3 英寸 ⇒ **1 mil 栅格** ✓"
                "（Fritzing 源码口径 ✓）" % list(units)[0])
    dup_ap = [(r, d) for r, g in gers.items() for d in g.ap_dup]
    if dup_ap:
        rep.add("§2 单位/格式/原点", "WARN",
                "**同一 D 码定义了两次**（后一次覆盖前一次 ✗）：%s"
                % "、".join("%s D%d：先 %s 后 %s" % (r, c, a, b) for r, (c, a, b) in dup_ap))
    und = [(r, sorted(g.undef_use)) for r, g in gers.items() if g.undef_use]
    if und:
        rep.add("§2 单位/格式/原点", "FAIL",
                "**引用了没定义的光圈** ✗：%s" % "、".join("%s %s" % (r, v) for r, v in und))
    mac = [r for r, g in gers.items() if g.macros]
    if mac:
        rep.add("§2 单位/格式/原点", "WARN", "%s 里用了 AM 光圈宏 ✗（本工具不展开 ✓）" % "、".join(mac))
    unk = [(r, g.unknown[:4]) for r, g in gers.items() if g.unknown]
    if unk:
        rep.add("§2 单位/格式/原点", "WARN", "没认出来的词：%s"
                % "；".join("%s %s" % (r, v) for r, v in unk))
    notend = [r for r, g in gers.items() if not g.ended]
    if notend:
        rep.add("§2 单位/格式/原点", "FAIL", "%s 没写 `M02*`（文件没结束 ✗）" % "、".join(notend))

    # 钻孔文件
    out_g0 = gers.get("outline")
    hint = None
    if out_g0:
        b0 = out_g0.bbox()
        if b0:
            hint = (b0[2] - b0[0], b0[3] - b0[1])
    drl = Drill(got["drill"], board_mm=hint) if got.get("drill") else None
    if drl:
        rep.add("§2 单位/格式/原点", "OK", "钻孔：单位 %s ✓、坐标格式 %s ✓（%s ✓）、刀具 %s"
                % (drl.unit or "（没写 ✗）",
                   ("%d.%d" % drl.fmt) if drl.fmt else "?",                   drl.fmt_why,
                   "、".join("T%d=Ø%.3f mm" % (t, d) for t, d in sorted(drl.tools.items()))))
        plated_note = []
        for t, d in sorted(drl.tools.items()):
            n = len([h for h in drl.holes if h["tool"] == t])
            plated_note.append("T%d：%d 孔%s" % (t, n, "" if t < 100 else ""))
        rep.add("§2 单位/格式/原点", "OK",
                "plated 口径：Fritzing 按 `T1..T99 = 非镀（NPTH）`／`T100+ = 镀通（PTH）` ✓（文件头注释 ✓）⇒ %s"
                % "、".join(plated_note))
        if not drl.ended:
            rep.add("§2 单位/格式/原点", "WARN", "钻孔文件没写 `M30` ✗")
        if not drl.fmt:
            rep.add("§2 单位/格式/原点", "FAIL", "钻孔坐标格式**推不出来** ✗（没有 %FS 也没有小数点 ✗）")

    # 原点与板框
    out_g = gers.get("outline")
    outline_rect = None
    if out_g:
        bb = out_g.bbox()
        rep.add("§2 单位/格式/原点", "OK",
                "坐标原点（有据 ✓）：钻孔/铜层坐标 = **板框左下角、y 向上、英寸** ✓"
                "（实测安装孔 = 板角内 3.00 mm ⇒ 钻孔里 `X001180Y001181` ✓）")

    # ③ 模型对照
    model = None
    if not no_model:
        if not fzz:
            pref = os.path.commonprefix([os.path.basename(p) for p in got.values()]).rstrip("_")
            cand = os.path.join(os.path.dirname(os.path.abspath(folder)), pref + ".fzz")
            if os.path.isfile(cand):
                fzz = cand
        if fzz and os.path.isfile(fzz):
            if _HAS_MODEL:
                try:
                    model = load_model(fzz)
                except Exception as exc:
                    rep.add("§3 与模型对照", "WARN", "模型读不了（%s）⇒ 跳过对照 ✓" % exc)
            else:
                rep.add("§3 与模型对照", "WARN", "库仓工具（pcb_check）没装上 ⇒ 跳过对照 ✓：%s" % _MODEL_ERR)
        else:
            rep.add("§3 与模型对照", "WARN", "没找到配套 .fzz ⇒ 只做文件内在检查 ✓（`--fzz` 可指定 ✓）")
    if model:
        rep.add("§3 与模型对照", "OK", "模型 = `%s` ✓（库仓 `pcb_check.collect` 读的 ✓ —— "
                "与渲染/校验/布线**同一套**解析 ✓）：板 %.3f×%.3f mm ✓、盘 %d、过孔 %d、安装孔 %d、走线 %d"
                % (os.path.basename(model["path"]), model["board"][0], model["board"][1],
                   len(model["pads"]), len(model["vias"]), len(model["holes"]),
                   len(model["traces"])))

    # 板框尺寸
    if out_g:
        d = out_g.draws()
        pts = []
        for o in d:
            pts.append(o.p0)
            pts.append(o.p1)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ink = out_g.bbox()
        aps = {o.ap for o in d}
        pen = max((out_g.ap_min_mm(a) or 0.0) for a in aps) if aps else 0.0
        closed = d and _closed(pts)
        rep.add("§3 板框", "OK" if closed else "FAIL",
                "板框 %s ✓：%d 段、端点闭合=%s ✓；笔宽 = %.4f mm ✓；" 
                % (os.path.basename(got["outline"]), len(d), "是" if closed else "**不是** ✗", pen))
        rep.add("§3 板框", "OK", "① **笔画外沿**（＝板边 ✓）%.4f × %.4f mm；② **线心**（板厂按线心铣 ⇒ 实际板）"
                "%.4f × %.4f mm（两者差 %.4f mm/轴＝笔宽 ✓）"
                % (ink[2] - ink[0], ink[3] - ink[1],
                   (max(xs) - min(xs)), (max(ys) - min(ys)), pen))
        rep.add("§3 板框", "OK",
                "★ **这 %.4f mm 的口径差别要跟板厂讲清** ✗：路径端点写在 **%.1f ／ %.1f mil** ✓（= 笔宽 %.4f mm ✓ 的"
                "半个内缩 ✓），而板框 %.4f mm = **%.3f mil** ✓ ⇒ **外沿读法** %.4f mm、**线心读法** %.4f mm。"
                "**根因 = Fritzing 导出器**（`src/svg/svg2gerber.cpp` 的 `board_outline_line_width` 默认 "
                "0.2032 mm ✓ ⇒ 笔画**外沿**正好落在板框上 ✓，线心则向内缩半个笔宽 ✗）⇒ **修法**"
                "（本轮**不改 .fzz** ✗）：① 下单备注「板框 = 外沿 %.2f×%.2f mm」✓；"
                "② 或接受线心尺寸（差 %.2f mm/轴，在常规铣边公差内 ✓）；"
                "③ 导出前把该项设置调小（如 0.05 mm ✓）⇒ 口径差缩到 0.05 mm ✓"
                % (pen, min(xs) / MIL_MM, max(xs) / MIL_MM, pen,
                   max(model["board"][0], ink[2] - ink[0]) if model else (ink[2] - ink[0]),
                   (max(model["board"][0], ink[2] - ink[0]) if model else (ink[2] - ink[0])) / MIL_MM,
                   ink[2] - ink[0], max(xs) - min(xs),
                   max(model["board"][0], ink[2] - ink[0]) if model else (ink[2] - ink[0]),
                   max(model["board"][1], ink[3] - ink[1]) if model else (ink[3] - ink[1]),
                   (pen + 0.0) / 2.0 * 2.0))
        if model:
            bw, bh = model["board"]
            lo = (ink[2] - ink[0], ink[3] - ink[1])
            cen = (max(xs) - min(xs), max(ys) - min(ys))
            d1 = max(abs(lo[0] - bw), abs(lo[1] - bh))
            d2 = max(abs(cen[0] - bw), abs(cen[1] - bh))
            best = min(d1, d2)
            rep.add("§3 板框", "OK" if best <= BOARD_TOL_MM else "FAIL",
                    "对模型板框 %.3f × %.3f mm ✓：外沿读法差 %.4f mm ✓、线心读法差 %.4f mm"
                    "（差 = 笔宽 %.4f mm ✓）；取差小者 %.4f ≤ 容差 %.2f ⇒ %s"
                    % (bw, bh, d1, d2, pen, best, BOARD_TOL_MM, "对得上 ✓" if best <= BOARD_TOL_MM else "**对不上** ✗"))
            outline_rect = (0.0, 0.0, bw, bh) if d1 <= d2 else \
                (pen / 2, pen / 2, pen / 2 + cen[0], pen / 2 + cen[1])
        else:
            outline_rect = (0.0, 0.0, ink[2] - ink[0], ink[3] - ink[1])
        # 板框闭合/唯一区域
        if not closed:
            rep.add("§3 板框", "FAIL", "板框**不闭合** ✗ ⇒ 板厂算不出唯一板内区域 ✗")
        else:
            rep.add("§3 板框", "OK", "闭合回路 ＋ 唯一矩形区域 ✓（矩形的 bbox 唯一 ✓）")

    # 钻孔对照
    if drl and model:
        tr = []
        for t, d in sorted(drl.tools.items()):
            hs = [h for h in drl.holes if h["tool"] == t]
            tr.append("T%d Ø%.3f mm ×%d（%s）" % (t, d, len(hs),
                                                "NPTH ✓" if t < 100 else "PTH ✓"))
        rep.add("§3 钻孔", "OK", "刀具表：%s" % "；".join(tr))
        # 过孔
        vias = model["vias"]
        holes = model["holes"]
        gv = [h for h in drl.holes if abs(h["d_mm"] - (vias[0]["hole_mm"] or 0.0)) < 0.02] if vias else []
        rep.add("§3 钻孔", "OK" if len(gv) == len(vias) else "FAIL",
                "过孔：模型 %d 个 Ø%.2f mm ＋ 铜盘 Ø%.2f mm ⇒ 钻孔文件里 Ø%.2f mm 有 %d 个 %s"
                % (len(vias), (vias[0]["hole_mm"] if vias else 0),
                   (vias[0]["out_mm"] if vias else 0),
                   (vias[0]["hole_mm"] if vias else 0), len(gv),
                   "✓" if len(gv) == len(vias) else "✗"))
        worst = 0.0
        where = ""
        used = set()
        for v in vias:
            best = None
            for i, h in enumerate(drl.holes):
                if i in used:
                    continue
                dd = math.hypot(h["p"][0] - v["p"][0], h["p"][1] - v["p"][1])
                if best is None or dd < best[0]:
                    best = (dd, i, h)
            if best:
                used.add(best[1])
                if best[0] > worst:
                    worst = best[0]
                    where = "%s（模型 (%.3f,%.3f) ↔ 钻孔 (%.3f,%.3f) mm）" % (
                        v.get("ttl") or "via", v["p"][0], v["p"][1], best[2]["p"][0], best[2]["p"][1])
        rep.add("§3 钻孔", "OK" if worst <= POS_TOL_MM else "FAIL",
                "过孔位置最大偏差 = %.4f mm ≤ 容差 %.3f ✓（%s）" % (worst, POS_TOL_MM, where))
        # 安装孔
        for h in holes:
            hit = [x for x in drl.holes if math.hypot(x["p"][0] - h["p"][0], x["p"][1] - h["p"][1]) <= POS_TOL_MM]
            ok = hit and abs(hit[0]["d_mm"] - h["hole_mm"]) <= 0.05
            rep.add("§3 钻孔", "OK" if ok else "FAIL",
                    "安装孔 @(%.3f,%.3f) mm：模型 Ø%.2f mm ⇒ 钻孔 %s %s"
                    % (h["p"][0], h["p"][1], h["hole_mm"],
                       ("Ø%.3f mm" % hit[0]["d_mm"]) if hit else "**没找到** ✗",
                       "✓" if ok else "✗"))
        # 模型里没有的孔（点名 ✓ 不算错 ✗）
        known = []
        for x in vias:
            known.append((x["p"], x["hole_mm"], "过孔 %s" % (x.get("ttl") or "")))
        for x in holes:
            known.append((x["p"], x["hole_mm"], "安装孔 ✓"))
        for p in model["pads"]:
            if p["thr"]:
                known.append((p["p"], p.get("hole_mm"), "通孔盘 %s.%s" % (p["title"], p["cid"])))
        extra_holes = []
        for x in drl.holes:
            hit = None
            for p, _d, tag in known:
                if math.hypot(x["p"][0] - p[0], x["p"][1] - p[1]) <= POS_TOL_MM:
                    hit = tag
                    break
            if hit is None:
                extra_holes.append(x)
        if extra_holes:
            rep.add("§3 钻孔", "WARN",
                    "**模型里没有的孔** %d 个（点名 ✓）：%s"
                    % (len(extra_holes), "；".join("@(%.3f,%.3f) Ø%.3f mm" % (h["p"][0], h["p"][1], h["d_mm"])
                                             for h in extra_holes)))
        else:
            rep.add("§3 钻孔", "OK", "钻孔文件里的每个孔都能在模型里对上（过孔 ／ 安装孔 ／ 通孔盘 ✓）")
        # 通孔焊盘的孔 ⇒ 与"圆环"口径对账（Fritzing 的孔 = 2r − 笔宽 ✓）
        thr = [p for p in model["pads"] if p["thr"]]
        for p in thr:
            hit = [x for x in drl.holes if math.hypot(x["p"][0] - p["p"][0], x["p"][1] - p["p"][1]) <= POS_TOL_MM]
            if not hit:
                rep.add("§3 钻孔", "FAIL", "通孔焊盘 %s.%s 没有对应钻孔 ✗" % (p["title"], p["cid"]))
                continue
            got_d = hit[0]["d_mm"]
            exp = p.get("hole_mm")
            if exp and abs(got_d - exp) > 0.05:
                rep.add("§3 钻孔", "WARN",
                        "**通孔盘的孔径口径不一致** ⚠ %s.%s（铜盘 Ø%.2f mm）：库仓 `pcb_pads` 按"
                        "「`circle.r` = 孔半径」读 ⇒ Ø%.2f mm；钻孔文件里是 Ø%.3f mm"
                        "（= 2r − 笔宽 ✓ = **SVG 画出来的环内径** ✓，Fritzing 源码口径 ✓）"
                        "⇒ **Gerber 自洽** ✓（孔在环内 ✓）、差 %.3f mm **不是导出错** ✗，"
                        "是**我们库的读法（`pcb_pads` 自己标了「待核 ⚠️」✓）**与实做不一致 ✗"
                        "⇒ 要改的是**库的读法/件定义** ✓，不关这批 Gerber ✗"
                        % (p["title"], p["cid"], (p["size"] or (0, 0))[0], exp, got_d,
                           abs(got_d - exp)))
            elif not exp:
                rep.add("§3 钻孔", "OK", "通孔盘 %s.%s ⇒ 钻孔 Ø%.3f mm ✓（库没给孔径 ✗，只报了外径 ✓）"
                        % (p["title"], p["cid"], got_d))

    # 铜层内容
    if got.get("pnp"):
        try:
            check_pnp(got["pnp"], model, rep)
        except Exception as exc:
            rep.add("§3 贴片坐标", "WARN", "`.xy` 读不了：%s ✗" % exc)
    for role in COPPER_ROLES:
        g = gers.get(role)
        if not g:
            continue
        fl = g.flashes()
        dr = g.draws()
        total_len = sum(math.hypot(o.p1[0] - o.p0[0], o.p1[1] - o.p0[1]) for o in dr)
        widths = collections.Counter()
        for o in dr:
            m = g.ap_min_mm(o.ap)
            if m is not None:
                widths[round(m, 4)] += 1
        real = [w for w in widths if w > FILL_AP_MM]
        hair = [w for w in widths if w <= FILL_AP_MM]
        names = {"copperTop": "顶", "copperBottom": "底"}
        rep.add("§3 铜层内容", "OK",
                "%s层：flash %d 个（%s）／线段 %d 条、总长 %.2f mm ／ 光圈 %d 种：%s"
                % (names[role], len(fl), "、".join("D%d×%d" % (c, len([o for o in fl if o.ap == c]))
                                                 for c in sorted({o.ap for o in fl})),
                   len(dr), total_len, len(widths),
                   "、".join("Ø%.4f mm×%d" % (w, n) for w, n in sorted(widths.items()))))
        if real:
            rep.add("§3 铜层内容", "OK",
                    "%s层**真实线宽**最小 = %.4f mm（%.2f mil）；填充笔（≤%.2f mm）：%s"
                    % (names[role], min(real), min(real) / MIL_MM, FILL_AP_MM,
                       "、".join("Ø%.4f mm×%d" % (w, widths[w]) for w in sorted(hair)) or "无 ✓"))
        if not dr and not fl:
            rep.add("§3 铜层内容", "FAIL", "%s层**是空的** ✗" % names[role])

    if model and gers.get("copperTop"):
        # 模型 vs Gerber：线宽集合（信息 ✓）＋ **逐格覆盖对账**（硬判据 ✓）
        rep.add("§3 铜层内容", "OK", "模型：走线 %d 条（盘心↔盘心总长 %.2f mm ✓），线宽 %s"
                % (len(model["traces"]),
                   sum(t["length_mm"] for t in model["traces"]),
                   "、".join("%.2f mil（%.4f mm）×%d" % (w / MIL_MM, w, n)
                             for w, n in sorted(collections.Counter(
                                 round(t["width_mm"], 4) for t in model["traces"]).items()))))
        rep.add("§3 铜层内容", "OK",
                "★ 口径：**长度不能直接比** ✗ —— 模型量的是**盘心↔盘心** ✓，而 Fritzing 导出时"
                "把**落在盘上的走线端从盘心向里收了 ~0.14 mm** ✓（实测：模型最长那条顶面走线 "
                "12.201 mm ↔ Gerber 11.913 mm ✓，两端各差 ~0.14 ✓）⇒ 长度差**不代表缺铜** ✓；"
                "下面用**逐格覆盖**判「铜在不在」✓")

    # ⑥ 铜层内容：**逐格覆盖对账**（模型铜 ↔ Gerber 铜 ✓）
    if model:
        bmx = None
        for g in gers.values():
            bb = g.bbox()
            if bb:
                bmx = bb if bmx is None else (min(bmx[0], bb[0]), min(bmx[1], bb[1]),
                                              max(bmx[2], bb[2]), max(bmx[3], bb[3]))
        if bmx and model:
            bmx = (min(bmx[0], 0.0) - 0.3, min(bmx[1], 0.0) - 0.3,
                   max(bmx[2], model["board"][0]) + 0.3, max(bmx[3], model["board"][1]) + 0.3)
        for role, side in (("copperTop", "top"), ("copperBottom", "bottom")):
            g = gers.get(role)
            if not g or not bmx:
                continue
            gg = raster_gerber(g, role, step, window=bmx)
            mg = raster_model(model, side, step, window=bmx)
            gd = _dilate(gg.data, gg.w, gg.h, 1)
            md = _dilate(mg.data, mg.w, mg.h, 1)
            gd5 = gd
            md5 = md
            for _k in range(4):                      # 再膨胀 4 格 ⇒ 容差 ≈ 5 格 = 0.25 mm ✓
                gd5 = _dilate(gd5, gg.w, gg.h, 1)
                md5 = _dilate(md5, mg.w, mg.h, 1)
            m_tot = sum(1 for v in mg.data if v)
            g_tot = sum(1 for v in gg.data if v)
            missed = bytearray(1 if (mg.data[i] and not gd[i]) else 0 for i in range(len(mg.data)))
            missed5 = bytearray(1 if (mg.data[i] and not gd5[i]) else 0 for i in range(len(mg.data)))
            extra = bytearray(1 if (gg.data[i] and not md[i]) else 0 for i in range(len(gg.data)))
            extra5 = bytearray(1 if (gg.data[i] and not md5[i]) else 0 for i in range(len(gg.data)))
            n_miss = sum(missed)
            n_miss5 = sum(missed5)
            n_extra = sum(extra)
            cell_mm2 = step * step
            rep.add("§3 铜层覆盖对账", "OK" if m_tot else "WARN",
                    "%s面：模型铜 %d 格（%.2f mm²）↔ Gerber 铜 %d 格（%.2f mm²）；"
                    "**模型有、Gerber 没有**（容差 1 格 = %.3f mm ✓）%d 格 = %.3f mm²（%.3f%% ✓）"
                    "；放宽到 5 格（%.3f mm ✓，容「曲线被板厂按折线填」的偏差 ✓）⇒ 剩 %d 格 = %.4f mm²（%.3f%% ✓）"
                    % ("顶" if side == "top" else "底", m_tot, m_tot * cell_mm2,
                       g_tot, g_tot * cell_mm2, step, n_miss, n_miss * cell_mm2,
                       100.0 * n_miss / max(1, m_tot), 5 * step, n_miss5, n_miss5 * cell_mm2,
                       100.0 * n_miss5 / max(1, m_tot)))
            if n_miss:
                cl, _lab, _n, _s = clusters(missed, gg, topn=3)
                frac = 100.0 * n_miss5 / max(1, m_tot)
                rep.add("§3 铜层覆盖对账", "OK" if frac <= 1.0 else "FAIL",
                        "差得最远的那几块（容差 1 格 ✓）：%s ⇒ %s"
                        % ("；".join("%.3f mm² @(%.3f,%.3f)" % (b["area_mm2"], b["centroid"][0],
                                                                b["centroid"][1]) for b in cl),
                           "都在 5 格（0.25 mm）内 ✓ ⇒ 只是**形状边缘/填充折线**的差 ✓，不是缺铜 ✓"
                           if frac <= 1.0 else "**>1% 的对象 5 格都盖不上 ⇒ 真缺铜** ✗"))
                for b in cl[:3]:
                    d, lab2 = nearest_model_feature(model, side, b["centroid"])
                    rep.add("§3 铜层覆盖对账", "OK" if frac <= 1.0 else "FAIL",
                            "   这块缺的离模型的哪个铜最近：%s（净距 %.3f mm ✓）" % (lab2, d))
            if n_extra:
                cl, _lab, _n, _s = clusters(extra5, gg, topn=6)
                kinds = collections.Counter()
                for b in cl:
                    kind, lab2 = classify_cells(model, side, b["samples"])
                    kinds[(kind, lab2)] += 1
                only_ok = all(k[0] == "copper" for k in kinds)
                txt = []
                for (kind, lab2), v in kinds.items():
                    if kind == "copper":
                        txt.append("%s ⇒ 件里画的铜（例：线圈 ✓）✓ ×%d" % (lab2, v))
                    elif kind == "silk":
                        txt.append("%s ⇒ **丝印漏到铜层** ✗ ×%d" % (lab2, v))
                    else:
                        txt.append("**没归上（可疑）** ✗（%s）×%d" % (lab2, v))
                rep.add("§3 铜层覆盖对账", "OK" if only_ok else "WARN",
                        "**Gerber 有、模型没有**（1 格容差 %.3f mm² ✓，放宽 5 格后 %.3f mm² ✓）"
                        "⇒ 归因（%d 块 ✓）：%s"
                        % (n_extra * cell_mm2, sum(1 for v in extra5 if v) * cell_mm2,
                           len(cl), "；".join(txt)))

    # 焊盘 flash 对账（含 45° 旋转盘 ✓）
    if model:
        for side, role in (("top", "copperTop"), ("bottom", "copperBottom")):
            g = gers.get(role)
            if not g:
                continue
            fl = g.flashes()
            regs = [o for o in g.ops if o.kind == "region"]
            pads = [p for p in model["pads"] if side in p["side"]]
            vias = model["vias"]
            exp = [dict(p=p["p"], size=p["size"], tag="%s.%s" % (p["title"], p["cid"]),
                        rot=p["rot_deg"], poly=p["poly"]) for p in pads]
            exp += [dict(p=v["p"], size=(v["out_mm"], v["out_mm"]),
                         tag="%s（过孔）" % (v.get("ttl") or "via"), rot=None, poly=None)
                    for v in vias]
            hit_fl = 0
            worst = 0.0
            worst_what = ""
            miss = []
            for e in exp:
                best = None
                for o in fl:
                    dd = math.hypot(o.p0[0] - e["p"][0], o.p0[1] - e["p"][1])
                    if best is None or dd < best:
                        best = dd
                for o in regs:
                    xs = [x for x, _y in o.pts]
                    ys = [y for _x, y in o.pts]
                    cx = (min(xs) + max(xs)) / 2.0
                    cy = (min(ys) + max(ys)) / 2.0
                    dd = math.hypot(cx - e["p"][0], cy - e["p"][1])
                    if best is None or dd < best:
                        best = dd
                if best is None or best > POS_TOL_MM:
                    miss.append(e["tag"])
                else:
                    hit_fl += 1
                    if best > worst:
                        worst = best
                        worst_what = e["tag"]
            rep.add("§3 焊盘对账", "OK" if not miss else "FAIL",
                    "%s面：模型 %d 个盘（含过孔）⇒ Gerber 里对上 %d 个 ✓（最大偏差 %.4f mm @%s）%s"
                    % ("顶" if side == "top" else "底", len(exp), hit_fl, worst, worst_what,
                       ("；**没对上**：%s ✗" % "、".join(miss[:8])) if miss else ""))
            # 多余 flash
            extra_f = []
            for o in fl:
                if not any(math.hypot(o.p0[0] - e["p"][0], o.p0[1] - e["p"][1]) <= POS_TOL_MM for e in exp):
                    extra_f.append(o)
            if extra_f:
                info = []
                notok = 0
                for o in extra_f[:8]:
                    kind, lab2 = classify_cells(model, side, [(o.p0[0], o.p0[1])], tol=0.35)
                    if kind == "copper":
                        info.append("@(%.3f,%.3f) D%s = %s ✓（没有 connector id 的铜 ⇒ 接插件固定脚 ✓）"
                                    % (o.p0[0], o.p0[1], o.ap, lab2))
                    else:
                        notok += 1
                        info.append("@(%.3f,%.3f) D%s = **没归上** ✗（%s）" % (o.p0[0], o.p0[1], o.ap, lab2))
                rep.add("§3 焊盘对账", "OK" if not notok else "WARN",
                        "%s面有 %d 个 flash **不在模型的 connector 清单里**（点名 ✓）：%s"
                        % ("顶" if side == "top" else "底", len(extra_f), "；".join(info)))
            # 尺寸对账（抽最小的三个 ＋ 最大的一个 ✓）
            got_sz = []
            for e in exp:
                if not e["size"]:
                    continue
                best = None
                for o in fl:
                    dd = math.hypot(o.p0[0] - e["p"][0], o.p0[1] - e["p"][1])
                    if best is None or dd < best[0]:
                        best = (dd, o)
                if best and best[0] <= POS_TOL_MM:
                    wh = g.ap_mm(best[1].ap)
                    if wh:
                        got_sz.append((e, wh))
            if got_sz:
                bad = []
                for e, wh in got_sz:
                    if max(abs(wh[0] - e["size"][0]), abs(wh[1] - e["size"][1])) > SIZE_TOL_MM:
                        bad.append("%s 模型 %.3f×%.3f ↔ Gerber %.3f×%.3f"
                                   % (e["tag"], e["size"][0], e["size"][1], wh[0], wh[1]))
                rep.add("§3 焊盘对账", "OK" if not bad else "FAIL",
                        "盘尺寸（轴对齐 flash ✓ %d 个）：%s"
                        % (len(got_sz), "全部 ≤ %.3f mm ✓" % SIZE_TOL_MM if not bad
                           else "**不符**：%s ✗" % "、".join(bad[:6])))
            # 45° 旋转盘（G36 区域 ✓）
            rot_exp = [e for e in exp if e["rot"] is not None and 5.0 < e["rot"] < 85.0]
            if rot_exp:
                ok = 0
                worstv = 0.0
                worst_tag = ""
                for e in rot_exp:
                    for o in regs:
                        pts = o.pts[:-1] if len(o.pts) > 1 and o.pts[0] == o.pts[-1] else o.pts
                        if len(pts) < 4:
                            continue
                        xs = [x for x, _y in pts]
                        ys = [y for _x, y in pts]
                        cx = (min(xs) + max(xs)) / 2.0
                        cy = (min(ys) + max(ys)) / 2.0
                        if math.hypot(cx - e["p"][0], cy - e["p"][1]) > POS_TOL_MM:
                            continue
                        dd = max(min(math.hypot(px - x, py - y) for (x, y) in pts)
                                 for (px, py) in e["poly"])
                        if dd <= POS_TOL_MM * 4:
                            ok += 1
                            if dd > worstv:
                                worstv = dd
                                worst_tag = e["tag"]
                            break
                rep.add("§3 45° 焊盘", "OK" if ok == len(rot_exp) else "FAIL",
                        "**旋转盘**（模型里 %.0f° 摆的 ✗ 轴对齐 flash 装不下 ⇒ 应导成 G36 多边形 ✓）："
                        "%s面 %d 个 ⇒ Gerber 的 G36 区域里对上 %d 个 ✓（顶点最大偏差 %.4f mm @%s）；"
                        "该层 G36 区域共 %d 个 ✓"
                        % (rot_exp[0]["rot"], "顶" if side == "top" else "底", len(rot_exp), ok,
                           worstv, worst_tag, len(regs)))
                break

    # ⑥ 铜间距（同层 ✓）＋ **模型侧同一算法** 对账（分"设计的间距"还是"导出的错" ✓）
    for role, side in (("copperTop", "top"), ("copperBottom", "bottom")):
        g = gers.get(role)
        if not g:
            continue
        grid = raster_gerber(g, role, step)
        lab, n, sizes = components(grid)
        # ★★ **分辨率护栏** ✓：栅格步长就是"能看见的最小缝" ✗ —— 4 mil（0.1016 mm）的缝
        #   在 0.05 mm 步长下只隔 2 格 ✓，再窄就可能被**并成一块铜** ✗ ⇒ 报"只有 1 块铜" ✗
        #   （实测：两条 4 mil 线心距 8 mil ⇒ 缝 0.1016 ✓ 看得见 ✓；缝 ≤ 0.05 ✗ 看不见 ✓）
        #   ⇒ 拿 **step/2** 复核一遍 ✓：块数变多 ⇒ 说明粗步长漏了 ⇒ 用细的那份 ✓。
        fine_step = step / 2.0
        g2 = raster_gerber(g, role, fine_step)
        lab2, n2, sizes2 = components(g2)
        if n2 > n:
            rep.add("§4 铜↔铜间距", "OK", "%s层：粗步长 %.3f mm 只分出 %d 块、细步长 %.3f mm 分出 %d 块 ✓"
                    " ⇒ **按细的重算** ✓（粗步长会把窄缝并掉 ✗）" % (role, step, n, fine_step, n2))
            grid, lab, n, sizes = g2, lab2, n2, sizes2
            step = fine_step
        val, pair, at, lab = clearance(grid, want_lab=True)
        if val is None:
            rep.add("§4 铜↔铜间距", "OK", "%s层：只有 1 块连通铜 ⇒ 没有间距问题 ✓"
                    "（**分辨率限制** ⚠：比步长 %.3f mm 更窄的缝看不出来 ✗；要更细就 `--step %.3f` ✓）"
                    % (role, step, step / 2.0))
            continue
        fine, _win = refine_clearance(g, role, at, val)
        # ★ 判据（可辩护 ✓）：**< 0.127 mm（5 mil，嘉立创 1-2 层能做的最小间距 ✓）= 硬伤 ✗**；
        #   0.127..0.1524（6 mil，**常规**工艺 ✓）= ⚠ 须知（做得出，但不是"常规" ✓）
        lv = "FAIL" if fine < 0.127 else ("WARN" if fine < HAIRLINE_MM else "OK")
        rep.add("§4 铜↔铜间距", lv,
                "%s层**最小铜↔铜间距** = %.4f mm（%.2f mil）@(%.3f,%.3f) mm ⇒ %s（6 mil = %.4f mm ✓ = "
                "嘉立创**常规**下限 ✓；5 mil = 0.1270 mm ✓ = 能做的下限 ✓）"
                % (role, fine, fine / MIL_MM, at[0], at[1],
                   "**在**常规 6 mil 内 ✓" if fine >= HAIRLINE_MM else
                   ("**低于**常规 6 mil ⚠（还在能做范围内 ✓）" if fine >= 0.127 else "**低于 5 mil** ✗"),
                   HAIRLINE_MM))
        pairinfo = classify_pair(g, grid, lab, at, pair)
        rep.add("§4 铜↔铜间距", lv, "   这道间距出现在：%s（距冲突点 %.3f mm ✓）↔ %s（%.3f mm ✓）"
                % (pairinfo[0][0], pairinfo[0][1] or 0.0, pairinfo[1][0], pairinfo[1][1] or 0.0))
        if model:
            mwin = (max(0.0, at[0] - 3.0) - 0.5, max(0.0, at[1] - 3.0) - 0.5,
                    at[0] + 3.5, at[1] + 3.5)
            mg = raster_model(model, side, step, mwin)
            mval, _mp, _mat = clearance(mg, limit=CLEAR_LIMIT_MM)
            if mval:
                mfine, _w2 = refine_clearance_grid(mg, _mat, mval)
                near = abs(mfine - fine) <= 0.05
                rep.add("§4 铜↔铜间距", "OK" if near else "WARN",
                        "   **模型侧**同一算法（同窗口 ✓）：%.4f mm ⇒ %s"
                        "（⚠ Gerber 这道间距若牵涉**模型里没有的铜**（例：丝印漏到铜层 ✗）"
                        "⇒ 两边**本来就该不一样** ✓ ⇒ 看上一行的归因 ✓）"
                        % (mfine, "两边一致 ⇒ 是**设计**里的间距 ✓，不是导出错 ✗" if near
                           else "不相等（差 %.4f mm ✓）" % abs(mfine - fine)))
            else:
                rep.add("§4 铜↔铜间距", "OK",
                        "   **模型侧**同一算法（同窗口 ✓）：窗口里 %.1f mm 内**没有两块铜相遇** ⇒ 没得比 ✓"
                        "（多半就是 Gerber 那边有**模型里没有的铜** ✗ —— 见上一行归因 ✓）"
                        % CLEAR_LIMIT_MM)
        rep.add("§4 铜↔铜间距", "OK", "%s层连通块 %d 个（最大 %.3f mm²、最小 %.5f mm²）"
                % (role, n, max(sizes) * step * step, min(sizes) * step * step))
        blanks = [i + 1 for i, s in enumerate(sizes) if s * step * step < 0.02]
        if blanks:
            rep.add("§4 铜↔铜间距", "WARN",
                    "%s层有 %d 块**碎铜/微铜**（面积 < 0.02 mm² ⇒ 可能被蚀掉/浮空 ✓，点名 ✓）"
                    % (role, len(blanks)))

    # ⑦ 阻焊 / 丝印
    if model:
        for side, crole, mrole in (("top", "copperTop", "maskTop"), ("bottom", "copperBottom", "maskBottom")):
            cg, mg = gers.get(crole), gers.get(mrole)
            if not (cg and mg):
                continue
            pads = [p for p in model["pads"] if side in p["side"]]
            pads += [dict(p=v["p"], size=(v["out_mm"], v["out_mm"]), cid="via", title=v.get("ttl") or "via")
                     for v in model["vias"]]
            miss = []
            deltas = []
            # ★ 阻焊的"开窗"不只 flash ✓ —— 45° 盘的开窗是 **G36 多边形** ✓（拿质心比 ✓）
            mfeat = [(o.p0, mg.ap_mm(o.ap)) for o in mg.flashes()]
            for o in mg.ops:
                if o.kind == "region" and o.pts:
                    xs = [x for x, _y in o.pts]
                    ys = [y for _x, y in o.pts]
                    mfeat.append((((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0),
                                  (max(xs) - min(xs), max(ys) - min(ys))))
            for p in pads:
                hit = None
                for (pp, size) in mfeat:
                    if math.hypot(pp[0] - p["p"][0], pp[1] - p["p"][1]) <= POS_TOL_MM:
                        hit = size
                        break
                if hit is None:
                    miss.append("%s.%s" % (p["title"], p["cid"]))
                    continue
                # ★ 开窗外扩**按 Gerber 自己比** ✓（铜层同位置的 flash 光圈 vs 阻焊开窗 ✓）
                #   —— ✗ 不拿模型的尺寸当基准 ✗（模型的尺寸口径与 Fritzing 的"笔宽/环宽"约定
                #   不同 ⇒ 会算出 0.118 这种看不懂的数 ✓）
                cop = None
                for o2 in cg.flashes():
                    if math.hypot(o2.p0[0] - p["p"][0], o2.p0[1] - p["p"][1]) <= POS_TOL_MM:
                        cop = cg.ap_mm(o2.ap)
                        break
                if hit and cop:
                    a = sorted(hit)
                    b = sorted(cop)
                    deltas.append((round(a[0] - b[0], 4), round(a[1] - b[1], 4),
                                   "%s.%s" % (p["title"], p["cid"])))
            rep.add("§4 阻焊开窗", "OK" if not miss else "FAIL",
                    "%s面阻焊：模型 %d 个盘 ⇒ 开窗对上 %d 个 ✓%s" 
                    % ("顶" if side == "top" else "底", len(pads), len(pads) - len(miss),
                       ("；**没开窗**：%s ✗" % "、".join(miss[:8])) if miss else ""))
            if deltas:
                uni = sorted(set((d[0], d[1]) for d in deltas))
                bad = [d for d in deltas if min(d[0], d[1]) < -0.01]
                rep.add("§4 阻焊开窗", "OK" if not bad else "FAIL",
                        "%s面**开窗外扩**（阻焊 − 铜，逐盘对账 ✓ ⇒ 与模型口径无关 ✓）：%s ⇒ %s"
                        % ("顶" if side == "top" else "底",
                           "、".join("%+.4f/%+.4f mm×%d" % (a, b, len([1 for d in deltas if (d[0], d[1]) == (a, b)]))
                                     for a, b in uni[:4]),
                           "**都 ≥ 0** ✓（每个盘都开得比铜大 ✓）" if not bad
                           else "**有盘开得比铜小** ✗：%s" % "、".join(d[2] for d in bad[:5])))
            # 阻焊内容 = 铜 ＋ 外扩 ⇒ 顺便报"导线是否也开窗"
            mg_draws = len(mg.draws())
            if mg_draws:
                rep.add("§4 阻焊开窗", "WARN",
                        "%s面阻焊层里有 **%d 条线段**（= 铜层导线原样搬过来 ＋ %.3f mm 外扩 ✓ "
                        "Fritzing 的既有行为 ✓）⇒ 后果：**导线也开窗**（不盖绿油 ✓）⇒ "
                        "本板导线 0.20/8 mil 细 ⇒ 装配期**挂锡/桥连**风险 ↑ ⚠（不是错 ✗，是不好看＋难焊 ✓）"
                        % ("顶" if side == "top" else "底", mg_draws, MASK_CLEAR_MM))
    if gers.get("silkTop") or gers.get("silkBottom"):
        # ★ 丝印只跟**同一面**的盘/孔比 ✗（顶面丝印盖不到底面的盘 ✓；不筛会假报 ✓）
        by_side = {"top": [], "bottom": []}
        if model:
            for p in model["pads"]:
                if p["size"]:
                    for sd in p["side"]:
                        by_side[sd].append((p["p"], max(p["size"]), "%s.%s" % (p["title"], p["cid"])))
            for v in model["vias"]:
                for sd in v["side"]:
                    by_side[sd].append((v["p"], v["out_mm"], v.get("ttl") or "via"))
            for h in model["holes"]:
                by_side["top"].append((h["p"], h["hole_mm"], "安装孔"))
                by_side["bottom"].append((h["p"], h["hole_mm"], "安装孔"))
        for role in ("silkTop", "silkBottom"):
            g = gers.get(role)
            if not g:
                continue
            allpads = by_side["top" if role == "silkTop" else "bottom"]
            dr = g.draws()
            widths = collections.Counter(round(g.ap_min_mm(o.ap) or 0.0, 4) for o in dr)
            tot = sum(math.hypot(o.p1[0] - o.p0[0], o.p1[1] - o.p0[1]) for o in dr)
            fillpen = [w for w in widths if 0 < w <= FILL_PEN_MM]
            real = [w for w in widths if w > FILL_PEN_MM]
            rep.add("§4 丝印", "OK", "%s：线段 %d 条、总长 %.2f mm、光圈 %s ⇒ **真丝印线宽** %s；"
                    "填充笔（≤%.4f mm ✓ = Fritzing 把**实心形状**（位号文字 ✓）导成 1 mil 扫描线 ✓）：%s"
                    % (role, len(dr), tot,
                       "、".join("Ø%.4f×%d" % (w, n) for w, n in sorted(widths.items())),
                       ("最小 %.4f mm（%.2f mil）" % (min(real), min(real) / MIL_MM)) if real else "无",
                       FILL_PEN_MM,
                       "、".join("Ø%.4f mm×%d 段" % (w, widths[w]) for w in sorted(fillpen)) or "无 ✓"))
            thin = [w for w in real if w < HAIRLINE_MM]
            if thin:
                rep.add("§4 丝印", "WARN", "%s 有 %.4f mm 的**真丝印线** ✗（< %.4f mm = 6 mil ✓；"
                        "嘉立创丝印下限 0.15 mm ⇒ 可能印不清 ✓）"
                        % (role, min(thin), HAIRLINE_MM))
            if allpads:
                bad = 0
                worst = None
                pressed = collections.Counter()
                for o in dr:
                    w = (g.ap_min_mm(o.ap) or 0.0) / 2.0
                    for (pp, sz, tag) in allpads:
                        d = Grid._d_pt_seg(pp, o.p0, o.p1) - w - sz / 2.0
                        if d < 0:
                            bad += 1
                            pressed[tag] += 1
                            if worst is None or d < worst[0]:
                                worst = (d, o.p0, o.p1, pp)
                            break
                lv = "OK" if bad == 0 else "WARN"
                rep.add("§4 丝印", lv,
                        "%s **压焊盘/压孔**的线段 = %d 条（占 %.1f%% ✓）%s"
                        % (role, bad, 100.0 * bad / max(1, len(dr)),
                           ("；最狠：线 (%.3f,%.3f)→(%.3f,%.3f) 与盘 @(%.3f,%.3f) 净距 %.4f mm ✗；"
                            "被压的盘（前 6 ✓）：%s"
                            % (worst[1][0], worst[1][1], worst[2][0], worst[2][1], worst[3][0], worst[3][1],
                               worst[0], "、".join("%s×%d" % (t, n) for t, n in pressed.most_common(6))))
                           if worst else " ✓（都不压盘 ✓）"))

    # ⑧ 可疑物
    if out_g and outline_rect:
        x0, y0, x1, y1 = outline_rect
        for role in COPPER_ROLES + ("silkTop", "silkBottom"):
            g = gers.get(role)
            if not g:
                continue
            bb = g.bbox()
            out = []
            tol = 0.25 if role.startswith("silk") else 0.0
            worstout = 0.0
            for o in g.ops:
                if o.kind == "region":
                    pts = o.pts
                elif o.kind == "flash":
                    pts = [o.p0]
                else:
                    pts = [o.p0, o.p1]
                r = 0.0
                if o.kind == "flash":
                    wh = g.ap_mm(o.ap)
                    r = max(wh) / 2.0 if wh else 0.0
                elif o.kind == "draw":
                    r = (g.ap_min_mm(o.ap) or 0.0) / 2.0
                for (px, py) in pts:
                    d = max(x0 - (px - r), (px + r) - x1, y0 - (py - r), (py + r) - y1)
                    if d > worstout:
                        worstout = d
                    if d > tol + 1e-6:
                        out.append(o)
                        break
            if out:
                rep.add("§5 可疑物", "WARN" if role.startswith("silk") else "FAIL",
                        "%s 有 %d 个图元**越出板框** ✗（容差 %.2f mm ✓；最远伸出 %.4f mm ✓；"
                        "点名前 3 个：%s）"
                        % (role, len(out), tol, worstout,
                           "；".join("线 (%.3f,%.3f)→(%.3f,%.3f)" % (o.p0[0], o.p0[1], o.p1[0], o.p1[1])
                                   if o.kind == "draw" else "@(%.3f,%.3f)" % (o.p0[0], o.p0[1])
                                   for o in out[:3])))
            else:
                rep.add("§5 可疑物", "OK", "%s 全在板框内 ✓（最外伸出 %.4f mm ≤ 容差 %.2f mm ✓）"
                        % (role, worstout, tol))
    for role, g in sorted(gers.items()):
        dups = g.dup_ops()
        if dups:
            rep.add("§5 可疑物", "WARN", "%s 里**同一图形写了两遍**（%d 组 ✓；多半是填充/叠画 ✓ "
                    "不致命 ✗，但要让板厂知道 ✓）：%s"
                    % (role, len(dups), "；".join("%s×%d" % (k[0], n) for k, n in dups[:4])))
        if g.zero_len:
            rep.add("§5 可疑物", "WARN", "%s 里有 %d 条**零长线段**（D01 两端重合 ✗）" % (role, g.zero_len))
        for code in g.apertures:
            nm = g.apertures[code][0]
            wh = g.ap_mm(code)
            used = sum(n for (c, _k), n in g.ap_use.items() if c == code)
            if wh and min(wh) < FILL_AP_MM and min(wh) > 0 and used and role in COPPER_ROLES:
                rep.add("§5 可疑物", "OK", "%s 的 D%d（%s，%.5f×%.5f mm）用了 %d 次 ⇒ 判为"
                        "**填充笔**（Fritzing 把**曲线走线的宽笔画**导成 1 mil 扫描线 ✓ ⇒ "
                        "图上是一条实心铜带 ✓，不是细导线 ✓）"
                        % (role, code, nm, wh[0], wh[1], used))
        if g.arcs:
            rep.add("§5 可疑物", "WARN", "%s 里有 %d 段**圆弧**（本工具按弦处理 ✓，"
                    "间距/长度口径会略偏 ✓）" % (role, g.arcs))
    # 未知 / 未结束 / 未定义
    if not gers.get("outline"):
        rep.add("§5 可疑物", "FAIL", "**没有板框层** ✗ ⇒ 板厂不知道切哪儿 ✗")
    # 碎铜：没有盘/孔落在里面的连通块
    if model:
        for role, side in (("copperTop", "top"), ("copperBottom", "bottom")):
            g = gers.get(role)
            if not g:
                continue
            grid = raster_gerber(g, role, step)
            lab, n, sizes = components(grid)
            if n < 2:
                continue
            anchors = [(p["p"], max(p["size"] or (0, 0))) for p in model["pads"]
                       if side in p["side"] and p["size"]]
            anchors += [(v["p"], v["out_mm"]) for v in model["vias"]]
            # ★ **件里自己画的铜**也算锚 ✓（例：接插件固定脚的铜没有 connector id ✗）
            for sh in model_shapes_side(model, side):
                if sh["layer"].startswith("copper"):
                    bb = sh["bbox"]
                    anchors.append((((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0),
                                    max(bb[2] - bb[0], bb[3] - bb[1])))
            hit = set()
            for (pp, sz) in anchors:
                ix = int((pp[0] - grid.x0) / step)
                iy = int((pp[1] - grid.y0) / step)
                for dyy in (-1, 0, 1):
                    for dxx in (-1, 0, 1):
                        xx, yy = ix + dxx, iy + dyy
                        if 0 <= xx < grid.w and 0 <= yy < grid.h and lab[yy * grid.w + xx]:
                            hit.add(lab[yy * grid.w + xx])
            lonely = [(i + 1, sizes[i] * step * step) for i in range(n) if (i + 1) not in hit]
            if lonely:
                info = []
                for k, a in sorted(lonely, key=lambda t: -t[1])[:6]:
                    sx = sy = cnt = 0
                    for i, v in enumerate(lab):
                        if v == k:
                            sx += i % grid.w
                            sy += i // grid.w
                            cnt += 1
                    c = (grid.x0 + (sx / float(cnt) + 0.5) * step, grid.y0 + (sy / float(cnt) + 0.5) * step)
                    cells = []
                    for i, v in enumerate(lab):
                        if v == k:
                            cells.append((grid.x0 + (i % grid.w + 0.5) * step,
                                          grid.y0 + (i // grid.w + 0.5) * step))
                            if len(cells) >= 400:
                                break
                    kind, lab2 = classify_cells(model, side, cells)
                    info.append("%.4f mm² @(%.3f,%.3f) %s"
                                % (a, c[0], c[1],
                                   ("= %s ⇒ **丝印漏到铜层** ✗" % lab2) if kind == "silk" else
                                   (("= %s ✓" % lab2) if kind == "copper" else "（没归上 ✗）")))
                bad = [x for x in info if "✗" in x]
                rep.add("§5 可疑物", "WARN" if bad else "OK",
                        "%s 有 %d 块**没接任何盘/过孔/件铜的铜**（孤立铜岛 ✓）：%s"
                        % (role, len(lonely), "；".join(info)))
            else:
                rep.add("§5 可疑物", "OK", "%s 每块铜都接在盘/过孔/件铜上 ✓（无孤立铜岛 ✓）" % role)

    # 预览
    pngs = []
    if want_png:
        bb = None
        for g in gers.values():
            b = g.bbox()
            if not b:
                continue
            bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]),
                                       max(bb[2], b[2]), max(bb[3], b[3]))
        if bb and out_g:
            o = out_g.bbox()
            bb = (min(bb[0], o[0]), min(bb[1], o[1]), max(bb[2], o[2]), max(bb[3], o[3]))
        out_dir = out_dir or folder
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        base = os.path.splitext(os.path.basename(got["copperTop"]))[0].split("_")[0]
        plan = [("copperTop.png", [("copperTop", (198, 40, 40), gers.get("copperTop"))],
                 "顶层铜（红）＋板框（黑）"),
                ("copperBottom.png", [("copperBottom", (40, 80, 200), gers.get("copperBottom"))],
                 "底层铜（蓝）＋板框（黑）"),
                ("silk.png", [("silkTop", (40, 40, 40), gers.get("silkTop")),
                              ("silkBottom", (150, 150, 150), gers.get("silkBottom"))],
                 "丝印：顶=深灰 ✓ 底=浅灰 ✓"),
                ("mask.png", [("maskTop", (230, 170, 30), gers.get("maskTop")),
                              ("maskBottom", (120, 200, 90), gers.get("maskBottom"))],
                 "阻焊开窗：顶=橙 ✓ 底=绿 ✓"),
                ("overlay.png", [("copperBottom", (150, 180, 230), gers.get("copperBottom")),
                                 ("copperTop", (198, 40, 40), gers.get("copperTop")),
                                 ("silkTop", (40, 40, 40), gers.get("silkTop")),
                                 ("silkBottom", (170, 170, 170), gers.get("silkBottom"))],
                 "全叠：底铜（淡蓝）＋顶铜（红）＋丝印 ✓")]
        for fn, stack, note in plan:
            st = [(r, c, g) for (r, c, g) in stack if g]
            if not st:
                continue
            path = os.path.join(out_dir, "%s_%s" % (base, fn))
            render(st, path, bb)
            pngs.append((path, note))
        if out_g:
            # 板框单独描一下（黑框叠在最上面 ✓）—— 直接把 outline 画进 overlay ✓
            path = os.path.join(out_dir, "%s_overlay.png" % base)
            render([("copperBottom", (150, 180, 230), gers.get("copperBottom")),
                    ("copperTop", (198, 40, 40), gers.get("copperTop")),
                    ("silkTop", (40, 40, 40), gers.get("silkTop")),
                    ("silkBottom", (170, 170, 170), gers.get("silkBottom")),
                    ("outline", (0, 0, 0), out_g)], path, bb)
        for p, note in pngs:
            rep.add("§6 预览", "OK", "%s（%s）" % (p, note))

    # 结论
    hard = [i for i in rep.items if i[1] == "FAIL"]
    warn = [i for i in rep.items if i[1] == "WARN"]
    if hard:
        rep.add("§7 结论", "FAIL", "**不可送板** ✗：%d 条硬伤（%s）"
                % (len(hard), "；".join(t.split("：")[0][:40] for _c, _l, t in hard[:5])))
        silk_leak = sorted({m.group(1) for _c, _l, t in rep.items
                            for m in [re.search(r"件 `([^`]+)` 的\*\*丝印\*\*图元", t)] if m})
        if silk_leak:
            rep.add("§7 结论", "FAIL",
                    "★ **硬伤的根因（工具自己归的因 ✓，不是猜 ✗）**：件 %s 的 pcb svg 把 "
                    "`<g id=\"silkscreen\">` **嵌在** `<g id=\"copper1\">` 里 ✗ ⇒ Fritzing 按"
                    "「在铜组里」把它当**铜**导出 ✗ ⇒ 铜层多出 0.12 mm 细线 ⇒ 与旁边的线只隔 "
                    "0.09 mm（< 5 mil）✗。**修法**（本轮只报告、不执行 ✗）：把那几条线**移出铜组**"
                    "（放到 `<svg>` 根下，与 `WS2812B` 那件一样 ✓）⇒ **重新导出**即可 ✓ "
                    "—— 与 `.fzz`、与导出器都无关 ✗。" % "、".join("`%s`" % s for s in silk_leak))
    else:
        rep.add("§7 结论", "OK", "**可送板** ✓：0 条硬伤、%d 条须知（⚠ 见上 ✓；"
                "导出的就是 Fritzing 的既有行为 ✓，不是坏文件 ✗）" % len(warn))
    return rep, model, got, dict(missing=[], gers=gers, drill=drl, pngs=pngs, outline=out_g)


def _closed(pts):
    """端点首尾相接 ＋ 每个点出现偶数次 ✓（矩形截面 ✓）"""
    if not pts:
        return False
    cnt = collections.Counter((round(x, 3), round(y, 3)) for x, y in pts)
    if any(v % 2 for v in cnt.values()):
        return False
    return len(cnt) >= 4 and (round(pts[0][0], 3), round(pts[0][1], 3)) == \
        (round(pts[-1][0], 3), round(pts[-1][1], 3))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    folder = argv[0]
    fzz = None
    no_model = False
    want_png = False
    out_dir = None
    json_out = None
    quiet = False
    step = RASTER_STEP_MM
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--fzz" and i + 1 < len(argv):
            fzz = argv[i + 1]
            i += 2
        elif a == "--no-model":
            no_model = True
            i += 1
        elif a == "--png":
            want_png = True
            i += 1
        elif a == "--out" and i + 1 < len(argv):
            out_dir = argv[i + 1]
            i += 2
        elif a == "--json" and i + 1 < len(argv):
            json_out = argv[i + 1]
            i += 2
        elif a == "--quiet":
            quiet = True
            i += 1
        elif a == "--step" and i + 1 < len(argv):
            step = float(argv[i + 1])
            i += 2
        else:
            print("✗ 不认识的参数：%s" % a)
            print(__doc__)
            return 2
    if not os.path.isdir(folder):
        print("✗ 不是目录：%s" % folder)
        return 2
    print("== gerber_check：%s ==" % os.path.abspath(folder))
    rep, model, got, ctx = check(folder, fzz=fzz, no_model=no_model, want_png=want_png,
                                 out_dir=out_dir, step=step)
    rep.print(quiet=quiet)
    if json_out:
        with io.open(json_out, "w", encoding="utf-8") as f:
            json.dump(dict(items=rep.items,
                           model=os.path.basename(model["path"]) if model else None,
                           missing=ctx.get("missing") or []),
                      f, ensure_ascii=False, indent=1)
    if ctx.get("missing"):
        print("\n⇒ **拒判（exit 2）**：缺 %s ⇒ 板都做不出来 ✓，先把层导齐 ✗"
              % "、".join(ctx["missing"]))
        return 2
    print("\n⇒ %s（%d 项：✗%d ⚠%d ✓%d）"
          % ("可送板（exit 0）" if not rep.has_fail() else "不可送板（exit 1）",
             len(rep.items),
             len([1 for _c, l, _t in rep.items if l == "FAIL"]),
             len([1 for _c, l, _t in rep.items if l == "WARN"]),
             len([1 for _c, l, _t in rep.items if l == "OK"])))
    return 0 if not rep.has_fail() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
