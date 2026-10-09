# -*- coding: utf-8 -*-
r"""PCB 读回校验器（通用 ✓）2026-09-30 立

把 sketch 的 **pcbView** 读成**几何** ⇒ 查六件事 ✓
（PCB 上是**物理**连接 ✗ —— 两根线之间必须有铜，不是"同名即连通" ✓，见 AGENTS §5b 第 5 条 ✓）：

① **悬空端点**：走线端点既没落在焊盘上 ✓、也没挨上别的走线 ⇒ 废线/断线 ✗
② **板外**：走线端点 / 过孔落在**板框外** ⇒ ✗（就是 8 月那次"挪完件冒出远处垃圾走线"的病 ✓）
③ **过孔**：过孔至少要挨到**某一层**的铜 ⇒ 否则是块孤立铜 ✗
④ **同层交叉 / 重叠**：两条走线在**同一层**相交或重叠 ⇒ 物理上就是**短接** ✗
   （★ 不同层交叉 = 正常 ✓）
⑤ **连通性 == 网表** ✓（期望来自项目数据 `EXPECT` ✓）：几何接触 ⇒ 并查集 ⇒ 逐网比 ✓
   ★ **短接会自动在 ⑤ 现形** ✓（两个网被粘成一片 ⇒ 对不上 ✓）
   ★ 判据是**几何**（端点重合 / 端点落在焊盘或别条线上 / 过孔贯通两层 ✓）——
     与 Fritzing 记的 `<connects>` **无关** ✓ ⇒ 这份校验**不共用**生成器的世界模型 ✓（不许自证 ✓）
⑥ ★★ **过孔铜盘不许压到焊盘** ✓（2026-10-01 补 ✗）
   —— ③ 只查"**孔心**落没落在**盘框**里" ✗ ⇒ “孔心在盘外、但**环叠在盘上**”
   这类**全部漏掉** ✗✗（2026-10-01 v47 实测：18 个过孔里 **7 个**的铜盘压到邻盘，
   其中 **6 处是别的网** ⇒ 实物短路 ✗；用户拿图一眼就看出来了 ✗ —— 这条就是那次教训
   补上的机器守 ✓，`pcb_route` 里的 `novia` 只禁了盘内 ✓ 不够 ✗）。
   铜盘外半径 = `(孔直 + 环宽)/2 + 环宽/2` ✓（口径见 `fritzing-sketch-format-notes.md` 的 F17 ✓）。
⑩ ★★ **声明 vs 几何** ✓（2026-10-02 补 ✗）—— 把 Fritzing 写下的 `<connect>`（它认为
   “这里接上了” ✓）与**真铜是否重叠** ✗ 对照一遍；声明接了但铜没碰上 ⇒ 造出来是**断的** ✗。
   ★ 起因：用户手加的过孔被 ①③ 报成“孤立/悬空”✗，而他在 Fritzing 里**点线节点是通的** ✓
     —— 文件里确实写了 `<connect … modelIndex="…"/>` ✓ ⇒ 两套判据必须互相对照 ✓。
   ★ 反过来（铜重叠但没声明 ✓）只是 Fritzing 没记 ✓ ⇒ 制造上没事 ✓ ⇒ **不报** ✗。

⚠️ **通孔盘（THT）口径**：`pcb_pads` 报的层 = svg 里画的那层 ✓；但**带孔**的盘物理上**贯通两层** ✓
   ⇒ 这里按"贯通两层"算 ✓，并把"只画了一层"**另行提示** ✓（不静默 ✗；口径待拿 Fritzing 源码核 ✓）。

用法：
  py -3.13 tools\pcb_check.py <sketch.fzz> [--nets=<含 EXPECT 的项目数据.py>]
退出码：0 = 全过 ✓；1 = 有问题 ✗（每条问题都点名 ✓，不静默 ✓）
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_box as PB                                            # noqa: E402
import pcb_pads as PP                                            # noqa: E402
import pcb_wire as PW                                            # noqa: E402
import projdata                                                  # noqa: E402

TOL = 0.5                    # sketch 单位 ✓（≈ 0.14 mm）：端点重合 / 落在焊盘上的容差 ✓（Fritzing 写 6 位有效数字 ✓）
IND = "  "


# ── 几何小工具（一份实现 ✓）────────────────────────────────────────────────
def d_pt_seg(p, a, b):
    """点到**线段**的距离 ✓"""
    vx, vy = b[0] - a[0], b[1] - a[1]
    wx, wy = p[0] - a[0], p[1] - a[1]
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / L2))
    return ((wx - t * vx) ** 2 + (wy - t * vy) ** 2) ** 0.5


def on_seg(p, a, b, tol=TOL):
    return d_pt_seg(p, a, b) <= tol


def in_rect(p, r, tol=TOL):
    return r[0] - tol <= p[0] <= r[2] + tol and r[1] - tol <= p[1] <= r[3] + tol


def d_pt_rect(p, r):
    """点到**矩形**的距离 ✓（在框内 ⇒ 0 ✓；单位同输入 ✓）"""
    dx = max(r[0] - p[0], 0.0, p[0] - r[2])
    dy = max(r[1] - p[1], 0.0, p[1] - r[3])
    return (dx * dx + dy * dy) ** 0.5


def seg_rect(a, b, r, tol=TOL):
    """线段与矩形是否相交 ✓（端点在内 / 穿过 / 贴着都算 ✓）"""
    if in_rect(a, r, tol) or in_rect(b, r, tol):
        return True
    r2 = (r[0] - tol, r[1] - tol, r[2] + tol, r[3] + tol)
    edges = [((r2[0], r2[1]), (r2[2], r2[1])), ((r2[2], r2[1]), (r2[2], r2[3])),
             ((r2[2], r2[3]), (r2[0], r2[3])), ((r2[0], r2[3]), (r2[0], r2[1]))]
    return any(seg_seg(a, b, c, d) for c, d in edges)


def _cr(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def seg_seg(a, b, c, d):
    """两线段是否相交 ✓（含端点相接与共线重叠 ✓）"""
    d1, d2 = _cr(c, d, a), _cr(c, d, b)
    d3, d4 = _cr(a, b, c), _cr(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return (abs(d1) < 1e-9 and on_seg(a, c, d)) or (abs(d2) < 1e-9 and on_seg(b, c, d)) \
        or (abs(d3) < 1e-9 and on_seg(c, a, b)) or (abs(d4) < 1e-9 and on_seg(d, a, b))


# ── 走线的**真实几何**（一份实现 ✓ —— ★★ 2026-10-08 立 ✗）──────────────────────
#   ★ 起因 ✓：弧的真形状在 `<bezier>` 里 ✓，✗ 拿两端点的**弦**当"线在哪" ⇒ 下面全部判据
#     （间距 / 交叉 / 压盘 / 压孔 / 端点在不在别条线上 ✓）在弧上**都是错的** ✗ ——
#     实测 v59 那条 `24 mil` 电源弧**偏离弦最多 ≈2.5 mm** ✗（比线宽大一个数量级 ✓）。
#   ⇒ ✗ 谁也别再直接读 `t["a"]`/`t["b"]` 算"线身" ✗：一律走这几条 ✓（直线走**快路** ✓，
#     与老口径逐字相同 ⇒ 没弧的板子报数与以前**一模一样** ✓）。
#   ★ "是不是弧"看 `t["curve"]` ✓（✗ 别看 `pts` ✗ —— 直线也有 pts，只是 2 个点 ✓）。
def segs_of(t):
    """走线 ⇒ **段表** `[(a, b), …]` ✓（直线 1 段 ✓、弧 = 采样后的 n 段 ✓）—— 唯一入口 ✓"""
    if not t.get("curve"):
        return [(t["a"], t["b"])]
    p = t.get("pts") or [t["a"], t["b"]]
    return list(zip(p, p[1:]))


def d_pt_trace(p, t):
    """点到走线**真实几何**的距离 ✓（弧按折线采样 ✓；单位同输入 ✓）"""
    if not t.get("curve"):
        return d_pt_seg(p, t["a"], t["b"])
    return min(d_pt_seg(p, a, b) for a, b in segs_of(t))


def trace_near_pt(t, p, tol=TOL):
    """走线**线身**是否挨着这点 ✓（含弧 ✓）"""
    if not t.get("curve"):
        return on_seg(p, t["a"], t["b"], tol)
    return d_pt_trace(p, t) <= tol


def trace_rect_hit(t, r, tol=TOL):
    """走线（含弧 ✓）与矩形是否相交 ✓"""
    if not t.get("curve"):
        return seg_rect(t["a"], t["b"], r, tol)
    return any(seg_rect(a, b, r, tol) for a, b in segs_of(t))


def trace_trace_hit(ti, tj, tol=TOL):
    """两条走线**真的碰上**吗 ✓（含弧 ✓）"""
    if not (ti.get("curve") or tj.get("curve")):
        return seg_seg(ti["a"], ti["b"], tj["a"], tj["b"])
    for a, b in segs_of(ti):
        for c, d in segs_of(tj):
            if seg_seg(a, b, c, d):
                return True
    return False


# ★★ 过孔**安全距离**规则 ✓（2026-10-01 用户定 ✓，原话：「我想先实现通孔不能在元件内，
#   并与有安全距离的规则，比如 Via10 在 J1 焊盘上打孔了」✓）
#   围栏（FAIL ✗）两条 —— 都按**过孔铜盘**（Ø = 孔 + 2×环 ✓，本仓 = 0.6 ⇒ 半径 0.30 ✓）算：
#     ⑥a 铜盘压到**任何**焊盘（**含同一张网** ✗✗）⇒ 旧口径把同网的 via-in-pad 当"合法"✗
#         —— 用户点名否掉 ✗（J1 是 1.0 mm 间距的座子，孔打在它盘上 = 打穿了元件 ✗）；
#     ⑦  铜盘与**任何焊盘**的净距 < `VIA_SAFE_MM` ✗；
#         或者碰到**元件画出来的铜**（`copper0/1` ✓ 逐图元 ✓ 含线宽 ✓）✗
#         （= "有安全距离 + 通孔不能在元件内" ✓；净距 = 铜盘边 → 焊盘/铜图形边 ✓）
#         ★ 丝印（`silkscreen`/`outline`）**不算** ✗ —— 孔上盖丝印是印刷问题 ✓，
#           不是"打在元件上"✗（实测把它算进来会多出 13 条噪音 ✗）。
#     ⑧  **同一面**的两个件的**图元不许相交** ✗（异面叠着是**正常**的 ✓）
#         ★ 这边**要**看丝印 ✓ —— 件的丝印轮廓就是它的**本体** ✓（C1×U1 就是这么抓到的 ✓）。
#   ★ 值 = **0.25 mm**（我定的 ✓，可调 ✓）：工艺能力表里 1 oz 铜**最小线间距 0.127 mm**（嘉立创 ✓），
#     0.25 = 给装配/蚀刻留一档余量 ✓；✗ 别跟布线器的 `VIA_PAD_KEEPOUT_MM=0.45`（布局用的**预警**区 ✓）
#     混为一谈 ✗ —— 一个是"量出来合不合法" ✓（本文件 ✓），一个是"布的时候躲多远" ✓（`pcb_route` ✓），
#     **两份实现** ✓（故意的 ✓：互不背书 ⇒ 不会一起错 ✗）。
# ★★ 「**该缩宽**」的判据 ✓（2026-10-01 立 ✓，单一定义 ✓ —— 布线器与生成器都读它 ✓）：
#   = 这个盘到**同一个件**最近另一个盘的**边缘间隙** < `NECK_TRIGGER_MM` ✓。
#   由来（实测 ✓）：电线在盘旁边走，要占 `线宽/2` ✓、两侧还要净距 `CLEAR` ✓
#     ⇒ 间隙放不下 ⇒ **必须缩宽**（进盘前变细 ✓，业界常规做法 ✓）。
#   ★ 值 = `TRACE_MM + 2×CLEAR_MM` = 0.3048 + 0.30 = **0.6048 mm** ✓
#     （= 信号线满宽 + 两侧净距 ✓，放不下就得细 ✓）。
#   ★ 为什么不用 `VIA_INPAD_PITCH_MM`（细间距）当缩宽判据 ✗：那个是**过孔合法性**的口径 ✓，
#     而且只按**中心距**≤ 0.65 ✓ ⇒ `R1`（0402 ✓ 0.9 间距）与 `J1`（1.0 ✓）都不算 ✓
#     ⇒ 它们旁边的粗线仍按 0.455 挡 ✗ ⇒ 实测起点被围成 **72 / 312 / 288 格的小口袋** ✗
#       （`RC` / `COIL_A` / `COIL_B` 就是死在这里 ✓）。
#   ★ 实测本板命中（按**间隙**算 ✓）：`U1` QFN 0.200 ✓、`D3` 0.200 ✓、`R1`/`C1` 0402 ≈ 0.4 ✓、
#     `J1`/`J2` ≈ 0.4 ✓、`LED2` ≈ 0.4 ✓ ⇒ 都命中 ✓；`C2` 0603 ≈ 1.5 ✗、`L1` 线圈 7.4 ✗ ⇒ 不缩 ✓。
NECK_TRIGGER_MM = 0.6048

# ★★ 安装孔的**净距规则** ✓（2026-10-01 用户定 ✓，原话：
#   「安装孔附近是不能布线的，更不能穿体」✓）——
#   走线 / 过孔 到**孔内壁**的净距必须 ≥ `HOLE_CLEAR_MM` ✓；穿过（净距 < 0 ✓）**必定** FAIL ✗。
#   ★ 值 0.25 与 `VIA_SAFE_MM` / `PART_GAP_MM` 同值 ✓（好记 ✓、一行可调 ✓）。
#   ★ 起因（实测 ✓，不是推测 ✗）：安装孔件是核心 `HoleModuleID` ✓、`hole size="2.2mm,0.0mm"`
#     ⇒ **没有铜** ✓ ⇒ 以前**谁都看不见它** ✗（渲染器要画孔才解析过它 ✗）
#     ⇒ `v50H.fzz` 里有 **4 根走线直接穿过安装孔** ✗（实测距内壁 −1.100 / −0.900 / −0.800 / −0.300 mm ✓，
#     其中 −1.100 = 正**穿孔心** ✓）。
#   ★ 与布线器的口径关系 ✓：那边把孔按**方框**挡（`pcb_route.HOLE_CLEAR_MM` ✓，多挡四个角 ✓ = 更严 ✓）；
#     这里是**圆**的精确判据 ✓ —— 两边**各自实现** ✓（互不背书 ✓）。
HOLE_CLEAR_MM = 0.25


def rect_gap_mm(a, b):
    """两个**盘框**的**边缘间隙**（mm ✓；相交 ⇒ 0 ✓）—— 缩宽判据的**唯一实现** ✓"""
    dx = max(a[0] - b[2], 0.0, b[0] - a[2])
    dy = max(a[1] - b[3], 0.0, b[1] - a[3])
    return (dx * dx + dy * dy) ** 0.5 * 25.4 / 90.0


HOLE_GAP_MM = 0.25          # 孔 ↔ 孔（**孔壁到孔壁** ✓）—— 2026-10-05 用户定 ✗（新规则 ✓）
VIA_SAFE_MM = 0.25
# ★★ EPAD（裸露焊盘）上的**同网 via-in-pad 是允许的** ✓（2026-10-01 用户定 ✓）：
#   用户原话：「是在 EPAD 上开通孔接 GND 吗？这个必须允许」✓
#   —— QFN 的中央散热盘要接地，业界常规就是在 EPAD 上打一簇过孔接到背面地 ✓；
#      ✗ 旧口径把它也当违规 ✗（实测：`U1.connector20` 就是 EPAD ✓，被 ⑥ 报成“压在盘上” ✗）
#      ⇒ 等于禁止了正确做法 ✗。
#   ★ 例外**只限 EPAD** ✓（不扩大到其它焊盘 ✗）：接插件（`J1`/`J2`）、电阻、电容的盘上
#     **仍然禁止打孔** ✗ —— 那才是用户点名的 `Via10` 打在 `J1.connector2` 上那种（机械/装配 ✗）。
#   ★ 判 EPAD 的**依据**（不猜 ✗）：该焊盘的**连接器名**里含 `EPAD`/`EP`/`exposed` ✓
#     （本仓实例：`CH32V003F4U6` 的 `connector20 name="EPAD"` ✓、`RT6150` 的 `EP` ✓、
#      `TX-AH` 的 `EPAD1/2` ✓ —— 都命中 ✓）。
EPAD_EXEMPT = True
# ★★ 「**细间距焊盘**上的同网 via-in-pad」也允许 ✓（2026-10-01 用户选 (ii) ✓：
#   原话「2 吧，我看看啥样」✓），**但接插件 / 电阻 / 电容仍然禁止** ✗。
#   ★ 判据 = **物理量**（不猜 ✗、也不列白名单 ✗）：该焊盘到**同一个件**最近焊盘的中心距
#     ≤ `VIA_INPAD_PITCH_MM = 0.65 mm` ✓ —— 这正是“出口被夹死”的那种脚 ✓。
#     实测本仓：`U1` QFN20 = **0.40** ✓（命中 ✓）、`D3` SOT-363 = 0.65 ✓（命中 ✓）、
#     `LED2` = 0.85 ✗、`J1`/`J2` = **1.00** ✗、`R1`/`C1`（0402）= **0.90** ✗、
#     `C2` �©0603 = 2.07 ✗、`L1` 线圈 = 7.40 ✗ ⇒ **用户禁的那三类全部落在外面** ✓。
#   ★ 工艺提醒（要认账 ✓）：via-in-pad 会**吸锡**✗ ⇒ 制板时要选 **孔塞 / 盖油（tented & filled ✓）**，
#     否则贴片时锡会渗进孔里 ✓（嘉立创、PCBWay 都提供 ✓，可能略加价 ✓）。
VIA_INPAD_PITCH_MM = 0.65
# ★★ 元件之间（**同一层** ✓）要留的**安全间隔** ✓（2026-10-01 用户定 ✓：
#   「规则里还要元件之间保持安全间隔距离」✓）—— 比"不相交"严一档 ✓：
#   两件的图元最近距离必须 ≥ 本值 ✓（相交 ⇒ 负值 ⇒ 必定违规 ✓）。
#   ★ 取 0.25 mm（与 `VIA_SAFE_MM` 同值 ✓，好记 ✓；工艺上贴片件间距通常 ≥ 0.2 ✓）⇒ 一行可调 ✓。
PART_GAP_MM = 0.25
#   ★★ ⑦b / ⑧ 为什么必须**逐图元**判 ✗（2026-10-01 实测 ✓）：
#     ✗ 用"件的**占位框**（墨迹 bbox ✓）"会**大批假报** ✓：`NFC_Coil_20mm_6T_0p2_1`（L1）
#       的框是 **21.6×22.05 mm**（整块线圈 ✓），而板只有 **25×25 mm** ✓ ⇒ 15/16 个过孔
#       全被报成"在元件内" ✗；而 `LED2` 本来就坐在线圈**中间的空地**上 ✓（天线绕着电路 ✓
#       这是标准做法 ✓）⇒ 两件"同面相交"也是假报 ✗。
#     ✓ 改成逐图元（线圈 = `copper1` 里几百条螺旋 `<line>` ✓、按 `stroke-width/2` 外扩 ✓）：
#       过孔只要不碰那些线 ✓、LED2 只要不压到线 ✓ ⇒ 真违规才报 ✓。


class UF(object):
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


# ── 读模型 ─────────────────────────────────────────────────────────────────
def d_pt_pad(p, q):
    """点到**焊盘真铜**的距离 ✓（内部单位 ✓；落在铜里 ⇒ 0 ✓）

    ★★ 2026-10-05 立 ✗（**量出来的** ✓）：⑥/⑦ 原来按 `q["box"]`（**轴对齐方框** ✓）算 ✗ ——
      而**通孔盘的铜是圆的** ✗（`circle` ✓）⇒ 方框的**四角**在铜外 ✗ ⇒ 从角上量出来的
      "净距"**比真值小** ✗ ⇒ **假报** ✓。
      实测 ✓：`过孔 @(42.80,19.40)` 对 `L1.connector0`（心 (43.731,20.522)、铜半径 0.800 ✓）——
      按圆量 **0.358 mm** ✓（合规 ✓），按方框角量 **0.047 mm** ✗（假报"离得太近" ✗）。
    """
    if q.get("circle"):
        (cx, cy), r = q["circle"]
        return max(0.0, math.hypot(p[0] - cx, p[1] - cy) - r)
    if q.get("poly"):
        # ★★ 2026-10-09 修 ✗（**实测** ✓）：45° 摆的矩形盘（U1 的 QFN ✓）**方框**会胀大 ✗ ——
        #   0.2×0.6 的盘转 45° 后方框 ±0.283 mm ✗，而相邻脚中心只隔 0.400 mm ⇒ 两只脚的
        #   方框**互叠 0.166 mm** ✗ ⇒ "端点在 A 脚中心"同时被判"在 B 脚盘里" ✗ ⇒
        #   union 把同一端点并给两只相邻脚 ✗ ⇒ ⑤ 假报"粘上了别的脚" ✓
        #   （实测 `{PD2,PD3}`、`{PC0,PC1}` ✓）。⇒ 有 `poly`（旋转后的真多边形 ✓）就按它算 ✓。
        pl = q["poly"]
        n = len(pl)
        inside = False
        for i in range(n):
            a, b = pl[i], pl[(i + 1) % n]
            if (a[1] > p[1]) != (b[1] > p[1]):
                xi = a[0] + (p[1] - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                if p[0] < xi:
                    inside = not inside
        if inside:
            return 0.0
        best = None
        for i in range(n):
            a, b = pl[i], pl[(i + 1) % n]
            vx, vy = b[0] - a[0], b[1] - a[1]
            L2 = vx * vx + vy * vy
            t = 0.0 if L2 <= 1e-18 else max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
            d = math.hypot(a[0] + t * vx - p[0], a[1] + t * vy - p[1])
            best = d if best is None else min(best, d)
        return best
    b = q["box"]
    dx = max(b[0] - p[0], 0.0, p[0] - b[2])
    dy = max(b[1] - p[1], 0.0, p[1] - b[3])
    return math.hypot(dx, dy)


def is_epad(nm):
    """这个焊盘是不是**裸露焊盘** ✓（判据写在 `EPAD_EXEMPT` 的注释里 ✓）—— 不猜 ✗"""
    s = str(nm or "").lower()
    return ("epad" in s) or ("exposed" in s) or (s.strip() in ("ep", "ep0"))


def collect(path):
    """把一份 sketch 的 PCB 读成几何模型 ✓"""
    parts, board = PP.read_fzz(path)
    pads, warns, bodies = [], [], []
    for p in parts:
        mid = p.get("moduleId") or ""
        # ★ 板框自己 / 面包板件 **不是 PCB 上的元件** ✗（`pcb_pads` 的 main 也是这么分的 ✓）：
        #   面包板件在 pcbView 里挂着 830 个孔脚 ✗ ⇒ 不跳掉就报 830 条假“缺焊盘” ✗
        if mid == PP.BOARD_MID or mid.startswith("Breadboard") or mid.startswith("Via"):
            continue
        if p.get("fzp") is None:
            warns.append("%s: %s" % (p.get("title"), p.get("why")))
            continue
        # ★★ 元件**占位框**（本体墨迹 bbox ✓）—— ⑦「过孔安全距离」要用 ✓
        #   （2026-10-01 用户定 ✓：「通孔不能在元件内，并与有安全距离」✓）
        # ★ 元件**占位框**（本体墨迹 bbox ✓）+ **逐图元**（铜/丝印 ✓）+ **所在面** ✓
        #   （2026-10-01 用户定 ✓：「通孔不能在元件内，并与有安全距离」✓ + 「同面不许重叠」✓）
        #   ★ 逐图元那份（`shapes` ✓）是关键 ✓：外框会把 NFC 线圈的**中间空地**也算成实体 ✗
        #     ⇒ 实测 1 个假报 ✓（`LED2` 坐在线圈中间，天经地义 ✓）。
        bb = PP.part_body(p)
        bot = ((p.get("pv") or {}).get("bottom") or "").lower() == "true"
        bodies.append(dict(title=p.get("title"), box=bb, shapes=PP.part_shapes(p),
                           side="bottom" if bot else "top"))
        got, _ex, bad, _nt = PP.part_pads(p)
        warns += ["%s: %s" % (p["title"], b) for b in (bad or [])][:6]
        if not got:
            continue
        for cid, q in got.items():
            if q["hole_mm"] and q["layer"] != "both":
                warns.append("%s.%s 带孔（Ø%.2f）却只画在 `%s` 一层 ⇒ 按**贯通两层**算 ✓（口径待核 ⚠️）"
                             % (p["title"], cid, q["hole_mm"], q["layer"]))
            pads.append(dict(title=p["title"], cid=cid, nm=q["nm"], c=q["abs"], box=q["absbox"],
                             # ★ 焊盘**真几何**（旋转后的真矩形 ✓ / 通孔的真圆 ✓）——
                             #   2026-10-02 补 ✓：`box` 是**轴对齐**包围盒 ✗，45° 摆的件会被
                             #   胀大 ✗ ⇒ 「线端落没落在盘上」必须用 `poly`/`circle` ✓
                             #   （真几何由 `pcb_pads.py` 算一次 ✓，这里只取用 ✓）
                             poly=q.get("poly"), circle=q.get("circle"),
                             layer=q["layer"], thr=bool(q["hole_mm"]),
                             # ★ 是不是**裸露焊盘（EPAD）** ✓ —— ⑦/⑥ 的例外要靠它 ✓
                             epad=is_epad(q["nm"]),
                             mi=p.get("mi") or ""))
    # ★★ “细间距焊盘”标记 ✓（2026-10-01 用户选 (ii) ✓，判据见 `VIA_INPAD_PITCH_MM` ✓）：
    #   = 该盘中心到**同一个件**最近另一个盘中心的距离 ≤ 阈值 ✓
    #     （接插件/电阻/电容的间距都比它大 ⇒ 自动落在外面 ✓，不靠白名单 ✗）
    by_title = {}
    for q in pads:
        by_title.setdefault(q["title"], []).append(q)
    for lst in by_title.values():
        for q in lst:
            best = None
            gap = None
            for z in lst:
                if z is q:
                    continue
                d = ((z["c"][0] - q["c"][0]) ** 2 + (z["c"][1] - q["c"][1]) ** 2) ** 0.5 \
                    * 25.4 / 90.0
                best = d if best is None else min(best, d)
                gg = rect_gap_mm(q["box"], z["box"])
                gap = gg if gap is None else min(gap, gg)
            q["fine"] = bool(best is not None and best <= VIA_INPAD_PITCH_MM)
            # ★★ 「**该缩宽**」= 边缘间隙放不下满宽线 + 两侧净距 ✓（判据见 `NECK_TRIGGER_MM` ✓，
            #   2026-10-01 立 ✓ —— 与 `fine` 是**两件事** ✗：`fine` 管“过孔能不能落盘上” ✓，
            #   `tight` 管“线到这里要不要变细” ✓）
            q["gap_mm"] = gap
            q["tight"] = bool(gap is not None and gap < NECK_TRIGGER_MM)
    text, name = PW.read(path)
    traces, vias = [], []
    for _ind, b in PW.blocks(text):
        mr = re.search(r'moduleIdRef="([^"]+)"', b)
        mid = mr.group(1) if mr else ""
        if mid.startswith("Via"):
            m = re.search(r'<pcbView\b[^>]*?\blayer="([\w]+)"[^>]*>\s*<geometry ([^>]*)/>', b)
            if m:
                a = dict(re.findall(r'([\w]+)="([^"]*)"', m.group(2)))
                # ★★ 过孔尺寸 = 件属性 `hole size` ✓，口径 **`<孔直径>,<环宽>`** ✓
                #   （2026-10-01 用 **Fritzing 自己的导出**定死 ✓：它给每个过孔画两个同心环
                #    `fill=none r=0.637795 stroke-width=0.425197` ✓ ⇒ 中心线 0.225 mm、
                #    环宽 0.15 mm ⇒ **内径 0.30 / 外径 0.60 mm** ✓，正对 `0.3mm,0.15mm` ✓。
                #    ✗ 别按"环直径"读 ✗ —— 那是内径 + 半环宽，会算错一半 ✓）
                sz = re.search(r'name="hole size"\s+value="([^"]+)"', b)
                mmv = [float(x) for x in re.findall(r"([\d.]+)\s*mm", sz.group(1))] if sz else []
                ttl = re.search(r"<title>([^<]*)</title>", b)
                # ★ ⑩ 要按 `modelIndex` 反查“这条线上声明接的是谁” ✓（2026-10-02 ✓）
                mi = re.search(r'modelIndex="(\d+)"', b)
                # ★★ 过孔的 `<geometry>` 是 **svg 画布原点** ✗ —— 真铜心要加**画图偏移** ✓
                #   （2026-10-01 定案 ✓，见 `part_box.draw_off_units` 的出处 ✓）
                #   ✗ 旧版直接把 geometry 当铜心 ⇒ 所有过孔差 0.8644 mm ✗ ⇒ “压别的焊盘”测不出来 ✗
                # ★★★ 2026-10-02 修 ✗：偏移 = **铜半径 + 画布留白** ✓ ⇒ **必须把本颗的尺寸传进去** ✗
                #   （✗ 旧版对**所有**过孔都用默认常数的 0.86444 ✗ ⇒ 用户那颗 `0.4mm,0.3mm`
                #    （外径 1.00）的过孔被算偏 0.2 mm/轴（0.283 mm 斜）✗ ⇒ 报成
                #    “孤立过孔 ＋ 两个悬空端点” ✗，而用户拿 Fritzing 点一下**明明是通的** ✗
                #    —— 2026-10-02 用户当场指出 ✓。三个实测点见 `part_box.ring_off_mm` ✓）
                off = PB.draw_off_units("via", (mmv[0], mmv[1] if len(mmv) > 1 else None)
                                        if mmv else None)
                geo = (float(a.get("x", 0)), float(a.get("y", 0)))
                vias.append(dict(layer=m.group(1),
                                 p=(geo[0] + off, geo[1] + off),      # 真铜心 ✓
                                 geo=geo,                            # 原始 geometry ✓（写文件时用 ✓）
                                 off=off,
                                 inst=mi.group(1) if mi else None,   # ⑩ 反查用 ✓
                                 # ★ 标题（`Via1`… ✓）也带出来 ⇒ 渲染器能写**稳定 id** ✓
                                 #   （2026-10-01 用户按 "circleNNNN" 对不上账 ✓ —— 那名字是查看器给的 ✗）
                                 ttl=ttl.group(1) if ttl else None,
                                 hole_mm=mmv[0] if mmv else None,
                                 ring_mm=mmv[1] if len(mmv) > 1 else None))
            continue
        if not mid.startswith("Wire"):          # ★ 板框/面包板/零件的 block **不是走线** ✗
            continue
        t = PW.parse_trace(b)
        if t is None:
            continue
        e = PW.abs_ends(t["geo"])
        mi = re.search(r'modelIndex="(\d+)"', b)
        traces.append(dict(layer=t["layer"][:-5] if t["layer"].endswith("trace") else t["layer"],
                           a=e[0], b=e[1],
                           # ★★ **真实形状** ✓（2026-10-08 ✓）：直线 = 2 点 ✓、带 `<bezier>` = 采样的
                           #   弧 ✓（`pcb_wire.trace_pts()` = 唯一定义 ✓）。★ 下面**所有**几何判据
                           #   都走 `segs_of()` / `d_pt_trace()` 读它 ✗ —— `a`/`b` 只剩"两端点"
                           #   这一个用途（端点落盘 / 声明 / 板外 ✓），✗ 不许再拿它当"整条线在哪" ✗。
                           pts=PW.trace_pts(t),
                           #   ★ "这条线是不是**弧**" 要单独有个记号 ✗ —— `pts` **人人都有** ✓
                           #     （直线就是 2 个点 ✓）⇒ ✗ 别拿 `pts` 当"有弧"的判据 ✗
                           #     （`pcb_metrics` 第一版就这么写错了 ✓ ⇒ 报成"168 条弯曲" ✗）。
                           curve=bool(t.get("bezier")),
                           # ★★ 曲线走线的**绝对控制点** ✓（`<bezier><cp0/><cp1/>` ⇒ 三次贝塞尔 ✓）
                           #   ✗ 只带端点 ⇒ 渲染器把弯曲的电源线画成**直弦** ✗ ——
                           #   2026-10-08 用户对图指出 ✓：v59 的 5V/GND `24 mil` 粗线在 Fritzing 里
                           #   是弧线 ✓、导出里也是 `<path d="M…C…">` ✓（实测 5/15 根 24mil 带 `bezier` ✓）
                           #   ⇒ 模型里**必须**带着它 ✓，渲染器才画得出同一条弧 ✓。
                           bez=PW.ctrl_pts(t["geo"], t.get("bezier")),
                           # ★ 线宽跟着走 ✓（`<wireExtras mils>` ✓）⇒ 渲染器照实物画 ✓
                           #   ✗ 旧版没有它 ⇒ 预览把每根线画成死值 ✗（v47 实宽 0.3048 mm ✓）。
                           mils=t.get("mils"),
                           # ★ ⑩ 要用：自己的 `modelIndex` ✓ ＋ 两端**声明的**连接 ✓
                           #   （`{端: [(connectorId, modelIndex, layer), …]}` ✓）
                           inst=mi.group(1) if mi else None,
                           ends=t.get("ends") or {}))
    return dict(pads=pads, traces=traces, vias=vias, board=PW.board_rect(text),
                bodies=bodies, holes=PP.holes(text), text=text, name=name,
                warns=warns, parts=parts)


def pad_layers(q):
    """这个焊盘**物理上**在哪几层 ✓（THT ⇒ 两层 ✓）"""
    return ("copper0", "copper1") if q["thr"] else (q["layer"],)


# ── 五查 ───────────────────────────────────────────────────────────────────
def check(model, expect=None):
    pads, traces, vias = model["pads"], model["traces"], model["vias"]
    probs, notes = [], []
    uf = UF()

    def end(i, k):
        return ("end", i, k)

    # ★★ `net_of` / `_nets_of` ✓（2026-10-01 提到最前 ✓，**各只留一份** ✗）：
    #   `net_of` = 焊盘 → 网名 ✓（从 `expect` 来 ✓）；`_nets_of(root)` = 该连通块牵了哪几张网 ✓。
    #   ★ 必须在 ①/⑤ 建边（会拿它判「短路桥」✓）与 ④ 之前就位 ✗。
    net_of = {}
    if expect:
        for _n2, _lst2 in expect.items():
            for _s2 in _lst2:
                if isinstance(_s2, str) and "." in _s2:
                    net_of[_s2] = _n2

    def _nets_of(root):
        """这个连通块里牵到几张网 ✓（顺着并查集看块里的焊盘 ✓）"""
        out = set()
        for q in pads:
            if uf.find(("pad", q["title"], q["cid"])) == root:
                nm = net_of.get("%s.%s" % (q["title"], q["cid"]))
                if nm is not None:
                    out.add(nm)
        return out

    def endpt(t, k):
        return t["a"] if k == 0 else t["b"]

    # ① 悬空端点 ＋ ⑤ 建边（端点↔焊盘 ✓、端点↔别条线 ✓、★端点↔过孔 ✓）
    for i, t in enumerate(traces):
        # ★★ 2026-10-01 补 ✗：**一根线的两个端点必须先并起来** ✓
        #   ✗ 原来从来没有这条边 ✗ ⇒ 如果一根线是"中间过路"的（一端接上游 ✓、另一端接下游 ✓），
        #     它的两端在图上**各属一块铜** ✗ ⇒ ⑤ 会把整张网报成"没连通" ✗✗
        #     （实测 v47：9 张网**全部**误报 ✗，而几何上铜是连着的 ✓）。
        #   ★ 病根：**线身不是节点** ✗ ⇒ 过路就断 ✓；补这一条即可（线两端的铜本来就一体 ✓）。
        uf.union(end(i, 0), end(i, 1))
        for k in (0, 1):
            e = endpt(t, k)
            hit = False
            for q in pads:
                # ★★ 2026-10-09 修 ✗：45° 摆的件，`box` 是**胀大的轴对齐包围盒** ✗
                #    ⇒ 「线端落没落在盘上」改判**真铜**（`poly`/`circle` ✓）
                if t["layer"] in pad_layers(q) and d_pt_pad(e, q) <= 0:
                    # ★★ 「线端落在盘框里」也要**按网筛** ✗✓（2026-10-01 ✓）：
                    #   同网的盘 ⇒ 正常接入 ✓；**别的网**的盘 ⇒ **短路桥** ✗（报出来 ✓）。
                    ttl2 = (q["title"], q["cid"])
                    qn = net_of.get("%s.%s" % ttl2)
                    if qn is not None:
                        ra2 = uf.find(end(i, k))
                        na2 = _nets_of(ra2)
                        if na2 and qn not in na2:
                            probs.append("④ 走线 #%d（网 %s）的%s端落在**别的网**的盘 `%s.%s`"
                                         "（网 %s）里 ⇒ **短路桥** ✗"
                                         % (i, "、".join(sorted(na2)), ("起" if k == 0 else "终"),
                                            ttl2[0], ttl2[1], qn))
                    uf.union(end(i, k), ("pad", ttl2[0], ttl2[1]))
                    hit = True
            for j, u in enumerate(traces):
                if j == i or u["layer"] != t["layer"]:
                    continue
                # ★ 2026-10-08 改 ✓：`on_seg(e, u.a, u.b)` ⇒ `trace_near_pt(u, e)` ✓
                #   （判据从"端点落在**弦**上"变成"端点挨着**真几何**" ✓ —— 弧才不会漏 ✓）
                # ★★ 2026-10-09 修 ✗（**实测** ✓）：这里原用 `tol=TOL`（带容差 ✗）
                #   —— QFN 相邻脚在 45° 下**本来就只隔 0.200 mm** ✓ ⇒ 邻脚的线端被判成
                #   "挨着"邻脚 ⇒ union-find 把两张网**并成一群** ✗ ⇒ ⑤ 假报"粘上了别的脚" ✗
                #   （实测：`{PD2,PD3}`、`{PC0,PC1}` 各被并成一群 ✓）。端到端**真重合**才算接上 ✓。
                #   ⇒ 取 **0.10 mm**（= 0.354 文件单位 ✓）：网格吸附噪声（实测 ≤0.05 mm ✓）吃得下 ✓，
                #     而 0.200 mm 的邻脚间距**不再误并** ✓（实测两处假报的距离都在 0.2–0.3 mm ✓）。
                if trace_near_pt(u, e, 0.3543):
                    uf.union(end(i, k), end(j, 0))
                    hit = True
            # ★★ 2026-10-08 补 ✗：**弧的线身**也要能"接上东西" ✓ ——
            #   ✗ 上面只查**两个端点** ✗：弧弯过去**身子**贴着焊盘/过孔/别的线的情形，
            #     在直线年代不可能（线身 = 端点之间的一条直段 ✓），弧一来就真会发生了 ✗
            #     ⇒ 不补就会把"几何上明明贴着铜"的弧报成**悬空** ✗（假报 ✓）。
            #   ★ 只对**带弧的**走线查中间采样点 ✓（直线的线身判据不动 ✗ —— 那会改变
            #     已交付板子的报数 ✓，而"直线中段压盘"另有 ④b 专门管 ✓）。
            if k == 1 and t.get("curve"):
                for mid in t["pts"][1:-1]:
                    for q in pads:
                        if t["layer"] in pad_layers(q) and d_pt_pad(mid, q) <= 0:
                            uf.union(end(i, k), ("pad", q["title"], q["cid"]))
                            hit = True
                    for j, u in enumerate(traces):
                        if j == i or u["layer"] != t["layer"]:
                            continue
                        if trace_near_pt(u, mid):
                            uf.union(end(i, k), end(j, 0))
                            hit = True
                    for vi, v in enumerate(vias):
                        if (abs(v["p"][0] - mid[0]) <= TOL
                                and abs(v["p"][1] - mid[1]) <= TOL):
                            uf.union(end(i, k), ("via", vi))
                            hit = True
            # ★★ 2026-09-30 补 ✗：端点落在**过孔**上也算接上了 ✓ ——
            #   ✗ 旧版只查"焊盘 + 同层线" ✗ ⇒ **换层的两根线各报一个悬空端点** ✗
            #     （两层当然不同层 ✗）⇒ 实测把 15 个过孔报成 **30 条悬空** ✗
            #     —— 而用户早就说过：「有时候需要添加过孔，来跨层连接」✓。
            #   ★ 过孔**两层都连通** ✓ ⇒ 不挑端点所在层 ✓。
            for vi, v in enumerate(vias):
                if (abs(v["p"][0] - e[0]) <= TOL and abs(v["p"][1] - e[1]) <= TOL):
                    uf.union(end(i, k), ("via", vi))
                    hit = True
            if not hit:
                probs.append("① 悬空端点：走线 #%d（%s 层，(%.2f,%.2f)→(%.2f,%.2f) mm）的 %s 端"
                             "既不在焊盘上、也不挨着别的线 ✗"
                             % (i, t["layer"], t["a"][0] * PW.SK, t["a"][1] * PW.SK,
                                t["b"][0] * PW.SK, t["b"][1] * PW.SK, ("起" if k == 0 else "终")))

    # ④ 同层交叉 / 重叠 ⇒ 短接 ✗（并进连通图 ✓ 让它也在 ⑤ 现形 ✓）
    #   ★★ 2026-10-01 修 ✗：**必须按网筛** ✗ —— 实测 6 对里大部分是**同一张网**的铜互碰 ✓
    #     （`GND`×`GND` ✓、`C1.connector1`×`C1.connector1` ✓、`LED2.connector1`×… ✓）
    #     ⇒ 那是**合法**的 ✓（同一张网本来就是一块铜 ✓，尤其是 GND 的汇流 ✓），不是短路 ✗。
    #   ⇒ 判据改成：这一碰**是否把两张不同的网并到一起** ✓（拿 `net_of` 查到 ≥2 张网才报 ✓）。
    #   ★ `net_of` 必须在**这之前**建好 ✗（它早先只在 ⑥ 里定义 ⇒ 这里引用会 `UnboundLocalError` ✓）
    #   ★ `net_of` / `_nets_of` 已在上面定义过一份 ✓ ⇒ 这里**不再重复定义** ✗（单一实现 ✓）
    for i in range(len(traces)):
        for j in range(i + 1, len(traces)):
            ti, tj = traces[i], traces[j]
            if ti["layer"] != tj["layer"]:
                continue
            # ★ 2026-10-08 改 ✓：弦 → **真几何** ✓（`trace_trace_hit` 逐段比 ✓，
            #   两条都是直线时走快路 ⇒ 与老口径逐字相同 ✓）
            if not trace_trace_hit(ti, tj):
                continue
            share = any(abs(endpt(ti, k)[0] - endpt(tj, m)[0]) <= TOL
                        and abs(endpt(ti, k)[1] - endpt(tj, m)[1]) <= TOL
                        for k in (0, 1) for m in (0, 1))
            # ★★ 只在「这一碰**真的把两张不同的网并到一起**」时才是**短路桥** ✗✓
            #   （2026-10-01 ✓）：先看这一碰**之前**两边各牵了哪些网 ✓ ——
            #   · 两边已含同一张网 ✓ ⇒ 只是同网自己碰自己 ✓ ⇒ 合法 ✓、**不报** ✗；
            #   · 一边 A、一边 B（不同网 ✓）⇒ **就是它把两张网接通了** ✗ ⇒ 报 ✓
            #     （一个网对只会在**第一次**被接通时报一次 ✓ ⇒ 4 处伏报自然收敛成真桥 ✓）。
            ra, rb = uf.find(end(i, 0)), uf.find(end(j, 0))
            na, nb = _nets_of(ra), _nets_of(rb)
            uf.union(end(i, 0), end(j, 0))
            if share or not na or not nb or (na & nb):
                continue
            # ★ 直线才分"重叠 / 交叉"✓（那个判据看的是**弦**✗）⇒ 有弧就只说"相交" ✓
            if ti.get("curve") or tj.get("curve"):
                kind = "相交（含弧 ✓）"
            else:
                kind = "重叠" if abs(_cr(ti["a"], ti["b"], tj["a"])) < 1e-6 else "交叉"
            probs.append("④ 同层%s ⇒ **短路桥**：走线 #%d（网 %s）与 #%d（网 %s）在 %s 层"
                         "把两张网接通了 ✗"
                         % (kind, i, "、".join(sorted(na)), j, "、".join(sorted(nb)),
                            ti["layer"]))

    # ④b ★★ 2026-10-05 补 ✗：「**线身**压到**别的网**的盘」✓ —— ④ 只管**线↔线** ✗、
    #   ① 只管**线端**落在盘里 ✗ ⇒ 「**中段过盘**」是个**盲区** ✗。
    #   实测（就是它漏报的 ✓）：`v65` 里 `BR+` 的一根线**贴着** `L1.connector0`（COIL_A ✓）
    #   的**环**走 ⇒ 铜叠进 **1.6 µm** ✗（真有铜 ✓ = 短路 ✗），而 ④/① 两边都没报 ✗。
    #   根因（量出来的 ✓）：布线器的障碍表当时把通孔盘按**孔**算 ✗（少挡 0.25 mm/边 ✗，
    #   已在 `pcb_pads.absbox` 修 ✓）——**但闸门不能指望上游做对** ✗，所以这里补一层 ✓。
    for i, t in enumerate(traces):
        hw = (t.get("mils") or 12.0) * 0.0254 / 2.0 / PW.SK
        na = _nets_of(uf.find(end(i, 0)))
        if not na:
            continue
        for q in pads:
            if t["layer"] not in pad_layers(q):
                continue
            qn = net_of.get("%s.%s" % (q["title"], q["cid"]))
            if qn is None or qn in na:
                continue
            if q.get("circle"):
                (cx, cy), r = q["circle"]
                # ★ 2026-10-08 改 ✓：弦 → **真几何** ✓（`d_pt_trace` 逐段比 ✓）
                d = d_pt_trace((cx, cy), t)
                if d <= r + hw + 1e-9:
                    ov = (r + hw - d) * PW.SK
                else:
                    continue
            else:
                # ★★ 2026-10-09 修 ✗（**实测出来的假报** ✓）：`q["box"]` 是**轴对齐包围盒** ✗
                #   —— 45° 摆的件（`U1` 的 EPAD = 菱形 ✓）它的**方框角点**离真铜 0.9 mm ✗，
                #   却把 `90015438`(LED 末段) / `90015465`(DATA_IN) 报成"压住 EPAD 短路" ✗。
                #   ⇒ 有 `poly`（旋转后的真多边形 ✓）就**逐边**量走线 ✓（与上面 circle 同源 ✓）
                pl = q.get("poly")
                if not pl:
                    if not trace_rect_hit(t, q["box"], hw):
                        continue
                    ov = -1.0
                else:
                    def _d2s(a, b, c):
                        """点 c 到线段 ab 的距离（**文件单位** ✓）"""
                        vx, vy = b[0] - a[0], b[1] - a[1]
                        L2 = vx * vx + vy * vy
                        tt = 0.0 if L2 <= 1e-18 else max(0.0, min(1.0, ((c[0] - a[0]) * vx + (c[1] - a[1]) * vy) / L2))
                        return ((a[0] + tt * vx - c[0]) ** 2 + (a[1] + tt * vy - c[1]) ** 2) ** 0.5

                    def _d2seg(a, b, c, d):
                        """线段 ab ↔ 线段 cd 的最小距离（取 4 个端点-线段距离的最小 ✓）"""
                        return min(_d2s(a, b, c), _d2s(a, b, d), _d2s(c, d, a), _d2s(c, d, b))

                    n = len(t["pts"])
                    d = min(_d2seg(t["pts"][k], t["pts"][k + 1], pl[m], pl[(m + 1) % len(pl)])
                            for k in range(n - 1) for m in range(len(pl)))
                    if d > hw + 1e-9:
                        continue
                    ov = max(0.0, (hw - d) * PW.SK)
            probs.append("④b 线**中段**压到**别的网**的盘 ⇒ **短路桥** ✗：走线 #%d（`%s`，网 %s）在 %s 层"
                         "压住 `%s.%s`（网 %s）%s"
                         % (i, t.get("inst"), "、".join(sorted(na)), t["layer"], q["title"], q["cid"], qn,
                            "" if ov < 0 else "，叠 **%.4f mm** ✓" % ov))

    # ③ 过孔挨铜 ＋ 贯通两层 ✓
    # ★★ 2026-10-05 修 ✗✓（**量出来的** ✓，不是猜 ✗）：判据从「**孔心**落在盘框/线段上」
    #   改成「**铜真的碰上**」✓ —— ✗ 旧口径只说"孔心在不在铜上" ✗：
    #   实测（用户手改件 ✓）`Via6` 的**铜与 `Via8` 叠了 0.200 mm** ✓、
    #   与三根走线各叠 0.011 / 0.069 / 0.011 mm ✓ ⇒ **明明连着** ✓，
    #   而孔心既不在任何盘框里、也不在任何线中心线上 ✗ ⇒ 旧口径报「**孤立过孔**」✗
    #   ⇒ **假报** ✓（同一个坑在 2026-10-02 已经在 ① 上撞过一次 ✓）。
    #   ⇒ 现在：盘按**真铜**（`d_pt_pad` ✓）、线按**半宽**（`mils` ✓）、孔按铜盘半径 ✓。
    for i, v in enumerate(vias):
        hd, rg = v.get("hole_mm"), v.get("ring_mm")
        rv = ((hd or 0.3) / 2.0 + (rg or 0.15)) / PW.SK      # 本孔铜盘半径 ✓（单位 ✓）
        touch = []
        for j, t in enumerate(traces):
            hw = (t.get("mils") or 12.0) * 0.0254 / 2.0 / PW.SK
            # ★ 2026-10-08 改 ✓：弦 → **真几何** ✓（弧弯过去贴着过孔也要算 ✓）
            if d_pt_trace(v["p"], t) <= rv + hw + 1e-9:
                uf.union(("via", i), end(j, 0))
                touch.append(t["layer"])
        for q in pads:
            if d_pt_pad(v["p"], q) <= rv + 1e-9:
                uf.union(("via", i), ("pad", q["title"], q["cid"]))
                touch.append("pad")
        for j, w in enumerate(vias):
            if j == i:
                continue
            hd2, rg2 = w.get("hole_mm"), w.get("ring_mm")
            rw = ((hd2 or 0.3) / 2.0 + (rg2 or 0.15)) / PW.SK
            if math.hypot(v["p"][0] - w["p"][0], v["p"][1] - w["p"][1]) \
                    <= rv + rw + 1e-9:
                uf.union(("via", i), ("via", j))
                touch.append("via")
        if not touch:
            probs.append("③ 孤立过孔：过孔 #%d 在 (%.2f,%.2f) mm 没挨到任何铜 ✗"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK))
        else:
            notes.append("过孔 #%d @(%.2f,%.2f) mm 挨到 %s ✓"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK, "/".join(sorted(set(touch)))))

    # ⑩ ★★ **声明 vs 几何** ✓（2026-10-02 补 ✗，见文件头 ⑩ ✓）
    #   ★ 为什么需要 ✗：**声明**（`<connect>` ✓）与**铜重叠**（几何 ✓）是**两套判据** ✗ ——
    #     2026-10-02 实测：用户手加的过孔，①③ 报“孤立/悬空”✗，而 Fritzing 里
    #     **点线节点显示是通的** ✓（文件里也确实写着 `<connect … modelIndex="…"/>` ✓）——
    #     两边不一致时不能只信一边 ✗ ⇒ 这里把它们**摆在一起对** ✓。
    #   ★ 铜判据（物理 ✓）：`净距 = 端点到目标铜的距离 − 本线半宽 − 目标半宽` ⇒ > 0 = **没碰上** ✗
    #     · 过孔半宽 = **铜盘外半径** = 孔直/2 + 环宽 ✓；· 焊盘 ⇒ 用它的**盘框** ✓；
    #     · 线↔线 ⇒ 两个半宽相加 ✓。
    #   ★ 容差 5 µm ✓（Fritzing 的数字是 6 位有效数字 ✓ ⇒ 不该有可见误差 ✓）
    DECL_TOL_MM = 0.005

    def _hw(t):
        # 线宽不明 ⇒ 按 Fritzing 核心默认 12 mil 算 ✓（偏保守 ✓ —— 报出来的自己再核 ✓）
        return (t.get("mils") or 12.0) * 0.0254 / 2.0

    by_inst = {}
    for i, v in enumerate(vias):
        if v.get("inst"):
            by_inst[v["inst"]] = ("via", i)
    for i, t in enumerate(traces):
        if t.get("inst"):
            by_inst[t["inst"]] = ("wire", i)
    pad_by = {}
    for q in pads:
        pad_by[(q["mi"], q["cid"])] = q
    seen10 = 0
    for i, t in enumerate(traces):
        for k in (0, 1):
            for cid, midx, _lay in (t.get("ends") or {}).get(k, []):
                seen10 += 1
                e = endpt(t, k)
                tg = by_inst.get(midx)
                who, gap = None, None
                if tg and tg[0] == "via":
                    v = vias[tg[1]]
                    r = (v.get("hole_mm") or 0.3) / 2.0 + (v.get("ring_mm") or 0.15)
                    gap = math.hypot(e[0] - v["p"][0], e[1] - v["p"][1]) * PW.SK - r - _hw(t)
                    who = "过孔 #%d" % tg[1]
                elif tg and tg[0] == "wire":
                    u = traces[tg[1]]
                    # ★ 2026-10-08 改 ✓：弦 → **真几何** ✓
                    gap = d_pt_trace(e, u) * PW.SK - _hw(t) - _hw(u)
                    who = "走线 #%d" % tg[1]
                else:
                    q = pad_by.get((midx, cid))
                    if q is not None:
                        gap = d_pt_pad(e, q) * PW.SK - _hw(t)
                        who = "焊盘 %s.%s" % (q["title"], q["cid"])
                if gap is not None and gap > DECL_TOL_MM:
                    probs.append("⑩ 声明未兼现：走线 #%d 的%s端在 `<connect>` 里声明接在 %s 上 ✓，"
                                 "但几何上铜还差 **%.3f mm** ✗ ⇒ 造出来是**断的** ✗"
                                 % (i, ("起" if k == 0 else "终"), who, gap))
    if seen10:
        notes.append("⑩ 逐条核对 Fritzing 的 `<connect>` 声明 %d 条 ✓"
                     "（**声明接上 ≠ 铜真碰上** ✗）；不合格 %d 条 ✓"
                     % (seen10, sum(1 for p in probs if p.startswith("⑩"))))

    # ⑫ ★★ **悬空声明** ✓（2026-10-06 加 ✓，起因 = `docs/pr-candidates.md` 的 **P1** ✓）
    #   ✗ ⑩ 的洞：它只遍历**走线**上声明的连接 ✗（`for i, t in enumerate(traces)` ✓）
    #     ⇒ **线根本不存在时它无从可查** ✗ —— 而幽灵正是这种形态 ✓：
    #     实测 `pixel-pcb-v70.fzz` 里 `RC` 三只脚**一条线都没有** ✗，
    #     可 Fritzing 状态栏**照样显示「布线完成」** ✓（它顺着文件里的 `<connect>` 走 ✓）。
    #   ✓ 这一条**不看几何** ✗，只问一句 ✓：
    #     文件里**每一条** `<connect … modelIndex="…"/>` 指的对象**还在不在** ✓？
    #     不在 ⇒ 那条声明是**幽灵** ✗ —— 人眼看不见 ✗、可 Fritzing 看得见 ✓ ⇒ 它会当成已连通 ✓。
    #   ★ 与 ⑩ 分工 ✓：⑩ = “声明的**几何**兼不兼现” ✓；⑫ = “声明指的**东西**还存不存在” ✓。
    _t12 = model.get("text") or ""
    _have12 = set()
    for _q12 in pads:
        if _q12.get("mi"):
            _have12.add(_q12["mi"])
    for _t in traces:
        if _t.get("inst"):
            _have12.add(_t["inst"])
    for _v in vias:
        if _v.get("inst"):
            _have12.add(_v["inst"])
    for _m12 in re.finditer(r'<instance\b[^>]*\bmodelIndex="(\d+)"', _t12):
        _have12.add(_m12.group(1))
    _dang12 = {}
    for _m12 in re.finditer(r'<connect\b[^>]*\bmodelIndex="(\d+)"', _t12):
        if _m12.group(1) not in _have12:
            _dang12[_m12.group(1)] = _dang12.get(_m12.group(1), 0) + 1
    if _dang12:
        probs.append("⑫ **悬空声明** ✗：%d 条 `<connect>` 指向的对象**文件里不存在** ✗"
                     "（例：modelIndex=%s ✓）⇒ Fritzing 会顺着它**当成已连通** ✓，"
                     "而**铜并不在** ✗ ⇒ 它会显示「布线完成」✓ —— 这样的文件**不能出厂** ✗"
                     % (sum(_dang12.values()), "、".join(list(_dang12)[:4])))
    else:
        notes.append("⑫ 悬空声明 **0 条** ✓（每一条 `<connect>` 指的对象都在文件里 ✓）")

    # ⑪ ★★ **孔 ↔ 孔** 的间距 ✓（2026-10-05 用户定 ✗，**新规则** ✓）：
    #   探伤（实测 ✓，用户手改件）：`Via6`@(45.18,20.52) 与 `Via8`@(45.18,20.92) 孔心距
    #     **0.40 mm** ✓ ⇒ 两颗 Ø0.30 的孔，**孔壁只差 0.10 mm** ✗ ⇒ 钻头/断刀风险 ✓。
    #   判据 ✓：**孔壁到孔壁**（mm ✓）必须 ≥ `HOLE_GAP_MM` ✓；
    #   比的是**每颗孔自己的直径** ✓（`hole size` 头一段 ✓）；
    #   ★ 安装孔（核心孔件 ✓）也算孔 ✓ —— 它没有铜 ✗，所以只有这条管得着它 ✓。
    hl = []
    for (c, dia, _cup) in (model.get("holes") or ()):
        hl.append(("安装孔Ø%.1f" % dia, c, dia))
    for i, v in enumerate(vias):
        hl.append(("过孔 %s" % (v.get("ttl") or "#%d" % i), v["p"], v.get("hole_mm")))
    for i in range(len(hl)):
        for j in range(i + 1, len(hl)):
            n1, p1, d1 = hl[i]
            n2, p2, d2 = hl[j]
            if not d1 or not d2:
                probs.append("⑪ %s 或 %s 没写孔径 ⇒ 孔距查不了 ✗（别静默 ✗）" % (n1, n2))
                continue
            g = (math.hypot(p1[0] - p2[0], p1[1] - p2[1])) * PW.SK - (d1 + d2) / 2.0
            if g < HOLE_GAP_MM:
                probs.append("⑪ 孔壁间距不够：%s @(%.2f,%.2f) 与 %s @(%.2f,%.2f) 只差 **%.3f mm** ✗"
                             "（需要 ≥ %.2f mm ✓；孔径 %.2f / %.2f mm ✓）"
                             % (n1, p1[0] * PW.SK, p1[1] * PW.SK, n2, p2[0] * PW.SK, p2[1] * PW.SK,
                                g, HOLE_GAP_MM, d1, d2))

    # ⑥ ★★ 过孔**铜盘**压焊盘 ✓（2026-10-01 补 ✗，见文件头 ⑥ ✓）
    #   ✗ ③ 只问"孔心在不在盘框里" ✗ ⇒ 孔心在盘外、**环压在盘上**的情形它看不见 ✗✗
    #   ★ 判据（2026-10-01 晚定 ✗，与生成器的闸门**各自实现** ✓）：
    #     · 压到**两张不同网**的盘 ⇒ **确定短路** ✗✗ ⇒ FAIL ✓
    #     · 压到**空脚**（网表里没有的脚 ✓）⇒ FAIL ✗（会把空脚拖进这张网 ✗，PC0 那次教训 ✓）
    #     · 压到**同一张网**的一个/几个盘 ⇒ **via-in-pad** ✓ 合法 ✓ ⇒ 只**提示** ✓
    #       （万一它其实属于别的网 ⇒ ⑤ 的连通性会把两张网粘在一起 ⇒ 报"粘上了别的脚" ✓
    #         —— 所以这条放宽**不会**漏掉真短路 ✓）
    for i, v in enumerate(vias):
        hd, rg = v.get("hole_mm"), v.get("ring_mm")
        if hd is None or rg is None:
            notes.append("过孔 #%d 没写 `hole size` ⇒ ⑥ 铜盘压盘检查**跳过** ✗（别静默 ✗）" % i)
            continue
        r_edge = ((hd + rg) / 2.0 + rg / 2.0) / PW.SK        # mm → 内部单位 ✓
        hit = []
        for q in pads:
            # ★★ 2026-10-05 修 ✗：一律用**真铜**（圆盘按圆 ✓）—— 旧版按 `box` ✗ ⇒
            #   通孔盘的**方框四角**落在铜外 ✗ ⇒ 假报“压到盘”/“离得太近” ✓（见 `d_pt_pad` ✓）。
            d = d_pt_pad(v["p"], q)
            if d < r_edge:
                key = "%s.%s" % (q["title"], q["cid"])
                hit.append((key, net_of.get(key), (r_edge - d) * PW.SK,
                            bool(q.get("epad") or q.get("fine"))))
        nets = {n for _k, n, _o, _e in hit}
        if not hit:
            continue
        # ★★ EPAD 例外 ✓（2026-10-01 用户定 ✓，见 `EPAD_EXEMPT` 的注释 ✓）：
        #   压到的**全部**是同网的焊盘、且它们**都是 EPAD** ⇒ via-in-pad ✓ 合法 ✓（EPAD 接地）
        #   ⇒ 报**提示** ✓ 不判违规 ✓；其余（异网 / 空脚 / 同网但非 EPAD）照旧 ✗。
        if None not in nets and len(nets) == 1 and all(h[3] for h in hit):
            notes.append("过孔 #%d 压在**同网**的 %s 上 ⇒ via-in-pad ✓ 合法 ✓"
                         "（EPAD 接地 / 细间距片子的扇出就是这么接的 ✓）"
                         % (i, ", ".join("%s 叠 %.3f mm" % (k, o) for k, _n, o, _e in hit)))
            continue
        if None in nets:
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 压到**空脚**的盘 %s ✗"
                         "（会把空脚拖进某张网 ✗）"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join(k for k, n, _o, _e in hit if n is None)))
        elif len(nets) > 1:
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 同时压到**两张不同网**的盘 "
                         "%s ⇒ **短路** ✗✗"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join("%s（网 %s，叠 %.3f mm）" % (k, n, o)
                                      for k, n, o, _e in hit)))
        else:
            # ★ 同网、但**不是 EPAD** ⇒ 仍然违规 ✗（用户点名的 `Via10`@`J1` 就是这种 ✓）
            probs.append("⑥ 过孔铜盘压盘：过孔 #%d @(%.2f,%.2f) mm 压在**同网**的盘 %s 上 ✗"
                         "（规则：只有 **EPAD** 上允许同网 via-in-pad ✓，接插件/电阻/电容的盘不行 ✗）"
                         % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK,
                            ", ".join("%s 叠 %.3f mm" % (k, o) for k, _n, o, _e in hit)))

    # ⑦ ★★ 过孔**安全距离** ✓（2026-10-01 用户定 ✗）：
    #   · 与**任何焊盘**（含同网 ✓）的净距 ≥ `VIA_SAFE_MM` ✓
    #   · 与**元件占位框**（本体墨迹框 ✓ `bodies` ✓）的净距 ≥ `VIA_SAFE_MM` ✓
    #     —— 即"通孔不能在元件内" ✓（在框内 ⇒ 净距 < 0 ⇒ 必定 FAIL ✓）
    #   量法：**矩形到点**的欧氏距离 ✓（在框内 = 0 ✓），再减铜盘半径 ✓ vs `VIA_SAFE_MM` ✓。
    for i, v in enumerate(vias):
        hd, rg = v.get("hole_mm"), v.get("ring_mm")
        if hd is None or rg is None:
            probs.append("⑦ 过孔 #%d 没写 `hole size` ⇒ 安全距离查不了 ✗（别静默跳过 ✗）" % i)
            continue
        r_mm = (hd + rg) / 2.0 + rg / 2.0                      # 铜盘半径 ✓（mm ✓）
        px, py = v["p"][0] * PW.SK, v["p"][1] * PW.SK
        worst = []
        for q in pads:                                         # ① 焊盘
            # ★★ 2026-10-05 修 ✗：改用**真铜**（`d_pt_pad` ✓）——旧版按 `box` ✗ ⇒
            #   实测把 **0.358 mm** 的真净距算成 **0.047 mm** ✗（方框角 ✗）⇒ 假报 ⑦ ✗。
            d0 = d_pt_pad(v["p"], q) * PW.SK      # ✗ 这里一律按 **mm** 算 ⇒ 换算一下 ✓
            # ★★ EPAD / 细间距例外 ✓（2026-10-01 修 ✗）：判据 = **这两件事同时成立** ✓
            #     ① 该盘是 EPAD 或**细间距**盘 ✓（`fine` ✓）；
            #     ② 过孔铜盘**确实压在这块盘上** ✓（= ⑥ 判过的那种 ✓）。
            #   ⇒ 这正是“**同网** via-in-pad”✓（⑥ 要求压到的盘**全是同一张网** ✓ 才会放行 ✓）
            #     ⇒ 这里**整块跳过** ✓，由 ⑥ 负责 ✓（不重复判 ✗）。
            if (q.get("epad") or q.get("fine")) and d0 < r_mm:
                continue
            d = d0 - r_mm
            if d < VIA_SAFE_MM:
                worst.append(("%s焊盘 %s.%s" % ("EPAD " if q.get("epad") else "",
                                                q["title"], q["cid"]), d))
        for q in model.get("bodies") or ():                    # ② 元件**画出来的铜** ✓
            for lay, b0, sid in q.get("shapes") or ():
                if lay not in ("copper0", "copper1"):
                    continue        # ✗ 丝印只是印油 ✓（孔上盖丝印是印刷问题 ✓，不是"打在元件上"✗）
                if "pad" in str(sid or "") or "pin" in str(sid or ""):
                    # ★★ 焊盘形状**跳掉** ✗（2026-10-01 修口径 ✗）：焊盘由 ⑥ / ⑦-焊盘 管 ✓，
                    #   这里再算一遍 ⇒ EPAD 上的合法 via-in-pad 会被重复报成违规 ✗
                    #   （实测：`过孔 #11 离 元件 U1 的 copper0 铜图形 −0.300 mm` ✗ 就是它 ✓）。
                    continue
                b = [t * PW.SK for t in b0]
                dx = max(b[0] - px, 0.0, px - b[2])
                dy = max(b[1] - py, 0.0, py - b[3])
                d = (dx * dx + dy * dy) ** 0.5 - r_mm
                if d < VIA_SAFE_MM:
                    worst.append(("元件 %s 的 `%s` 铜图形%s"
                                  % (q["title"], lay, "**上**" if d < -r_mm else ""), d))
        if worst:
            worst.sort(key=lambda z: z[1])
            k, d = worst[0]
            probs.append("⑦ 过孔 #%d @(%.2f,%.2f) mm 离 %s 只有 %+.3f mm ✗（需要 ≥ %.2f mm ✓；"
                         "铜盘 Ø%.2f mm ✓）"
                         % (i, px, py, k, d, VIA_SAFE_MM, 2 * r_mm))

    # ⑧ ★★ **同一层**的元件要留**安全间隔** ✓（2026-10-01 用户定 ✓：
    #   「v49 里，C1 是不是在同一面跟 U1 位置重叠了？这也不应该的，也需要一个规则禁止」✓
    #   「规则里还要元件之间保持安全间隔距离」✓）
    #   ★ 判据 = **逐图元 + 逐层**求净距 ✗（不是外框 ✗、也不是只看件的"面" ✗）：
    #     · 外框会把 NFC 线圈的中间空地当实体 ✗ ⇒ 实测假报 `L1×LED2` ✓
    #       （LED2 本来就坐在线圈中间的空地 ✓，天线绕着电路是标准做法 ✓）；
    #     · 只看"面"也不够 ✗ —— 线圈**两面都有铜** ✓（`copper0` 是背面那一圈 ✓）
    #       ⇒ 装在背面的件**不能压到线圈的背面铜** ✗，这只能按层判 ✓。
    #   ★ 层归并：`copper0`/`copper1` = 板的两层 ✓；`silkscreen`/`outline` = 该件所在那一面 ✓。
    #   ★ 相交 ⇒ 净距为负 ⇒ 必定违规 ✓；间隔必须 ≥ `PART_GAP_MM` ✓。
    def _laykey(lay, side):
        return lay if lay in ("copper0", "copper1") else "silk:" + str(side)

    bs = model.get("bodies") or []
    for a in range(len(bs)):
        for b in range(a + 1, len(bs)):
            A, B = bs[a], bs[b]
            worst, wk = None, None
            for la, ra, _ia in A.get("shapes") or ():
                for lb, rb, _ib in B.get("shapes") or ():
                    if _laykey(la, A.get("side")) != _laykey(lb, B.get("side")):
                        continue                               # 不同层 ⇒ 互不相干 ✓
                    ox = min(ra[2], rb[2]) - max(ra[0], rb[0])
                    oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
                    if ox >= 0 and oy >= 0:                    # 相交 ⇒ 净距 = −重叠量 ✓
                        gap = -min(ox, oy) * PW.SK
                    else:
                        dx = max(ra[0] - rb[2], 0.0, rb[0] - ra[2])
                        dy = max(ra[1] - rb[3], 0.0, rb[1] - ra[3])
                        gap = (dx * dx + dy * dy) ** 0.5 * PW.SK if (dx or dy) else 0.0
                    if worst is None or gap < worst:
                        worst, wk = gap, (la, lb)
            if worst is not None and worst < PART_GAP_MM - 1e-9:
                probs.append("⑧ 元件间隔不足：**%s**（%s）与 **%s**（%s）在同一层只有 %+.3f mm ✗"
                             "（需要 ≥ %.2f mm ✓；最近处 `%s` × `%s`）"
                             % (A["title"], ("背面" if A.get("side") == "bottom" else "正面"),
                                B["title"], ("背面" if B.get("side") == "bottom" else "正面"),
                                worst, PART_GAP_MM, wk[0], wk[1]))

    # ⑨ ★★ 安装孔 ✓（2026-10-01 用户定 ✓：「安装孔附近是不能布线的，更不能穿体」✓）
    #   判据 = 「**线段/点到孔心**的距离 − 孔半径」≥ `HOLE_CLEAR_MM` ✓（圆 ✓，不是方框 ✓）。
    #   ★ 为什么必须有这条 ✗：孔件是核心 `HoleModuleID` ✓、`hole size="2.2mm,0.0mm"`
    #     ⇒ **没有铜** ✗ ⇒ ①–⑧ 没一条看得见它 ✗ ⇒ 实测 `v50H.fzz` 有 4 根走线穿过孔 ✗
    #     （其中一根距内壁 **−1.100 mm** = 正穿孔心 ✓）。
    for hi, (c, dia, _cup) in enumerate(model.get("holes") or ()):
        r = (dia / 2.0) / PW.SK                        # 孔半径 ⇒ sketch 单位 ✓
        for i, t in enumerate(traces):
            # ★ 2026-10-08 改 ✓：弦 → **真几何** ✓（孔旁边弯过去的弧也要算 ✓）
            d = (d_pt_trace(c, t) - r) * PW.SK
            if d < HOLE_CLEAR_MM - 1e-9:
                probs.append("⑨ 安装孔：走线 #%d 距孔 #%d 内壁只有 %+.3f mm ✗"
                             "（需要 ≥ %.2f mm ✓；孔 Ø%.2f ✓%s）"
                             % (i, hi, d, HOLE_CLEAR_MM, dia,
                                "，**穿体** ✗" if d < 0 else ""))
        for i, v in enumerate(vias):
            d = (math.hypot(v["p"][0] - c[0], v["p"][1] - c[1]) - r) * PW.SK
            if d < HOLE_CLEAR_MM - 1e-9:
                probs.append("⑨ 安装孔：过孔 #%d 距孔 #%d 内壁只有 %+.3f mm ✗"
                             "（需要 ≥ %.2f mm ✓；孔 Ø%.2f ✓%s）"
                             % (i, hi, d, HOLE_CLEAR_MM, dia,
                                "，**落在孔里** ✗" if d < 0 else ""))

    # ② 板外 ✓
    r = model["board"]
    if r is None:
        notes.append("板框读不出 ⇒ **跳过②板外检查** ✗（请给带 `<board>` 与 PCB1 的 sketch ✓）")
    else:
        for i, t in enumerate(traces):
            # ★★ 2026-10-08 补 ✗：**弧的线身**也要查板上/板外 ✓ ——
            #   ✗ 旧版只看**两个端点** ✗ ⇒ 弧鼓出去（偏离弦 ≈2.5 mm ✗）时，两端都在板上
            #     ⇒ **整段鼓到板外却一个字都不报** ✗。★ 只对带弧的加采样点 ✓（直线的线身
            #     判据不动 ✗ ⇒ 已交付板子的报数不变 ✓）。
            pts = [(("起" if k == 0 else "终"), endpt(t, k)) for k in (0, 1)]
            if t.get("curve"):
                pts += [("线身", p) for p in t["pts"][1:-1]]
            for tag, e in pts:
                if not in_rect(e, r, 0.0):
                    probs.append("② 板外：走线 #%d 的%s (%.2f,%.2f) mm 板框是 (%.2f,%.2f)-(%.2f,%.2f) ✗"
                                 % (i, tag, e[0] * PW.SK, e[1] * PW.SK,
                                    r[0] * PW.SK, r[1] * PW.SK, r[2] * PW.SK, r[3] * PW.SK))
        for i, v in enumerate(vias):
            if not in_rect(v["p"], r, 0.0):
                probs.append("② 板外：过孔 #%d (%.2f,%.2f) mm ✗"
                             % (i, v["p"][0] * PW.SK, v["p"][1] * PW.SK))

    # ⑤ 连通性 == 网表 ✓
    groups = {}
    for q in pads:
        groups.setdefault(uf.find(("pad", q["title"], q["cid"])), set()).add((q["title"], q["cid"]))
    if expect:
        have = {(q["title"], q["cid"]) for q in pads}
        dup = len(pads) - len(have)
        in_nets = set()
        for net in sorted(expect):
            want = set()
            for m in expect[net]:
                if not isinstance(m, str) or "." not in m:
                    # ★ 2026-10-01 修 ✗：原来直接 `% m` ⇒ `m` 是**元组**时被当成参数列表**自己崩掉** ✗
                    #   （报错信息又把检查器弄崩 ⇒ 什么都看不到 ✗）。这里包一层元组 ✓。
                    probs.append("⑤ 期望表里的 `%s` 不是 `位号.connectorN` 格式 ✗" % (m,))
                    continue
                ref, cid = m.rsplit(".", 1)
                if (ref, cid) not in have:
                    probs.append("⑤ 网表里的脚 `%s` 在板上的焊盘里找不到 ✗（网 `%s`）" % (m, net))
                    continue
                want.add((ref, cid))
            in_nets |= want
            if not want:
                continue
            roots = {uf.find(("pad",) + k) for k in want}
            if len(roots) > 1:
                probs.append("⑤ 网 `%s` **没连通**：%d 个脚散在 %d 块铜里 ✗"
                             % (net, len(want), len(roots)))
            else:
                got = groups.get(roots.pop(), set())
                extra = got - want
                if extra:
                    probs.append("⑤ 网 `%s` **粘上了别的脚**（短接 ✗）：%s"
                                 % (net, ", ".join(sorted("%s.%s" % k for k in extra))[:90]))
        free = sorted(k for s in groups.values() for k in s if k not in in_nets)
        if free:
            notes.append("没有出现在任何网里的焊盘 %d 个：%s"
                         % (len(free), ", ".join("%s.%s" % k for k in free[:8])))
        if dup:
            notes.append("⚠️ 有 %d 个**同名位号**的焊盘多出来 ⇒ 网表按位号对会串 ✗（查位号 ✓）" % dup)
    return probs, notes, groups


def main(argv):
    nets, rest = projdata.strip_argv(argv)
    if not rest:
        print(__doc__)
        return 2
    path = rest[0]
    expect = None
    if nets:
        expect = projdata.load(nets, need=("EXPECT",)).EXPECT
        print("（网表：%s ✓）" % nets)
    else:
        print("（没给 `--nets` ⇒ **只跑 ①–④ · ⑥ 结构检查** ✓、跳过 ⑤ 网表比对 ✓）")
    model = collect(path)
    print("== %s（包内 %s）==" % (os.path.basename(path), model["name"]))
    print("   焊盘 %d 个 ✓（%d 个件）｜走线 %d 条 ✓｜过孔 %d 个 ✓｜板框 %s"
          % (len(model["pads"]), len({(q["title"]) for q in model["pads"]}),
             len(model["traces"]), len(model["vias"]),
             ("(%.2f,%.2f)-(%.2f,%.2f) mm" % tuple(v * PW.SK for v in model["board"]))
             if model["board"] else "读不出 ✗"))
    probs, notes, _g = check(model, expect)
    for n in notes[:12]:
        print("%s· %s" % (IND, n))
    if model["warns"]:
        for w in model["warns"][:4]:
            print("%s⚠️ %s" % (IND, w))
    if probs:
        print("%s✗ 问题 %d 条：" % (IND, len(probs)))
        for p in probs[:20]:
            print("%s  - %s" % (IND, p))
        if len(probs) > 20:
            print("%s  …（共 %d 条，只列前 20 ✓）" % (IND, len(probs)))
    cnt = {}
    for p in probs:
        k = p[:1]
        cnt[k] = cnt.get(k, 0) + 1
    names = {"①": "悬空端点", "②": "板外", "③": "孤立过孔", "④": "同层短接", "⑤": "网表",
             "⑥": "过孔压盘", "⑦": "过孔安全距离", "⑧": "同面元件相交", "⑨": "安装孔",
             "⑩": "声明未兼现", "⑫": "悬空声明",
             # ★ 2026-10-05 补 ✓：新加/改过的两条也要有名有姓 ✓（❓ 看着像工具坏了 ✗）
             "⑪": "孔↔孔间距"}
    if cnt:
        print("%s分类：%s" % (IND, "｜".join("%s%s %d" % (k, names.get(k, "?"), cnt[k])
                                     for k in sorted(cnt))))
    print("判定：%s" % ("✓ 全过" if not probs else "✗ 有问题（见上）"))
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
