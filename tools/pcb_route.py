# -*- coding: utf-8 -*-
r"""PCB **网格布线器**（两层 + 过孔 ✓）2026-09-30 立

★★ 为什么用**网格**而不是"几何直搜" ✓：
  · 几何搜索要自己保证"不自交、不重叠、间距够" ✗（每条新线都要和已有线两两判 ✗，容易错 ✗）；
  · 网格里**障碍就是被占的格子** ✓ ⇒ 间距/重叠**由构造保证** ✓（一格不能被走两遍 ✓），
    同层"交叉"根本不可能发生 ✓ —— 只剩"不同层交叉" ✓ 那是**允许的** ✓（不花代价 ✓）。
  ⇒ 代价 = **长度 + K_VIA×过孔数** ✓（§6.1：「走线尽量短」✓）。

前提（都由调用方给 ✓）：
  · `model` = `pcb_check.collect()` 的结果 ✓（含每个焊盘的**绝对框**＋它**在板上的层** ✓；
    背面件的层已经在 `pcb_pads` 里**对调**过了 ✓）
  · 障碍（**都要栅格化 ✓**）：① 焊盘铜（含净空 ✓）② 件自己的**铜箔图形**（例：线圈绕组
    722 条 ✓ —— 不挡它，线会压在绕组上 ✗）③ 板边留边 ✓ ④ 已布好的线 ✓
  · 通孔盘（`thr` ✓）两层都算铜 ✓

用法（**只算不写** ✓）：
  py -3.13 tools\pcb_route.py <sketch.fzz> --nets=<项目数据.py> [--cell 0.25] [--mil 12] [--dry]

★ 线宽 `--mil` **只能取那六档** ✓（8/12/16/24/32/48 ✓，见下方 `MIL_TIERS` ✓）。
"""
import math
import os
import re
import sys
import heapq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import part_box as PB                                             # noqa: E402
import pcb_check as PC                                            # noqa: E402
import pcb_pads as PP                                             # noqa: E402
import projdata                                                   # noqa: E402

SK = PB.MM
MM = lambda u: u / SK                                             # noqa: E402
U = lambda m: m * SK                                             # noqa: E402

CELL_MM = 0.15
# ★★ 线宽**只能用 Fritzing 给的那几档** ✓（用户 2026-09-30 定 ✓）
#   —— 就是 Fritzing「指示栏 → 属性 → 宽度」下拉里那六档 ✓：
#      超细 8 ／ 特细 12 ／ 薄 16 ／ **标准 24** ／ 厚 32 ／ 特厚 48（mil ✓）
#   ✗ 自创值（我先前写的 `9.8425` = 0.25 mm ✗）**不算一档** ✗ ⇒
#     和「颜色只能用官方配色表」同理 ✓：面板认不出来 ✗（下拉会回退到第一项 ✗）。
#   ⇒ 写进 `<wireExtras mils="…">` 的必须是**这几档的原值** ✓（`gen_routes.py` 照抄 ✓）。
MIL_MM = 0.0254
MIL_TIERS = {8: "超细", 12: "特细", 16: "薄", 24: "标准", 32: "厚", 48: "特厚"}
TRACE_MIL = 24                 # 默认**标准 24 mil** ✓（= 0.6096 mm ✓；就是 Fritzing 下拉里默认点中的那档 ✓）
TRACE_MM = TRACE_MIL * MIL_MM  # 线宽 ✓（跟着上面那一档走 ✓）
CLEAR_MM = 0.15            # 铜与铜的净空 ✓（**工艺值** ✓，不是"档"）
#   ★★ 2026-10-01 由 0.20 收到 0.15 ✗（起因：加"过孔不许压盘"后布不通 ✓）：
#     0.20 是**保守**值 ✗；嘉立创 1 oz 铜的**最小线间距**是 **0.127 mm**（5 mil ✓，工艺能力表 ✓）
#     ⇒ 0.15 合法且留了余量 ✓。
#     ★ 实测（`hardware/pixel/_work/diag_keepout_sweep.py` ✓）：`DATA_IN` 在**空板**上，
#       用 0.20 净空 + 0.45 过孔禁落区**根本无解** ✗ —— 而 A* 是**完备**的 ✓
#       ⇒ 不是"搜不出来" ✗，是**真没有合法走法** ✗。
#     ⇒ 把净空收到工艺允许的值是**必须**的 ✓（否则只剩"过孔压在别人盘上"那种违法走法 ✗）。
# ★ 过孔**盘半径** ✓（用户 2026-09-30 定：过孔尺寸取 `hole size="0.3mm,0.15mm"` ✓
#   —— 注意 Fritzing 的格式是「**钻孔 , 环宽**」✓（`mazerouter.cpp:2430` ✓），不是盘径 ✗
#   ⇒ 盘径 = 0.3 + 2×0.15 = **0.6 mm** ✓ ⇒ 半径 0.30 ✓。
# ★ 过孔**盘半径** ✓（2026-09-30 立 ✓；2026-10-01 复核 ✗）：
#   过孔写作 `hole size="0.3mm,0.15mm"` ✓ —— Fritzing 的格式是「**钻孔 , 环宽**」✓
#   （`mazerouter.cpp:2430` ✓），不是盘径 ✗ ⇒ 盘径 = 0.3 + 2×0.15 = **0.6 mm** ✓ ⇒ 半径 **0.30** ✓。
#   用途：① 算"过孔不许碰元件"的外扩量 ✓；② 算"过孔不许压盘"的禁落区 ✓（`VIA_PAD_KEEPOUT_MM` ✓）。
#   ★ 改了过孔尺寸就**必须同步改这里** ✓（盘半径写错 ⇒ 又会压盘 ✗）。
#   ★ 试过缩到 0.2/0.15 与 0.2/0.1 想省禁落区 ✗ ⇒ **实测没变好** ✗（8/9 → 7/9 ✓）⇒ 已回退 ✓。
VIA_CLEAR_MM = 0.30
# ★★ 过孔**不许压盘**的禁落量 ✓（2026-10-01 修 ✗ —— 用户点名的"通孔严重错误" ✓）：
#   孔心到**任何焊盘框**的距离必须 ≥ `VIA_CLEAR_MM`（= 铜盘半径 0.30 ✓）+ `CLEAR_MM`（净空 0.20 ✓）
#   —— ✗ 旧版只禁"**孔心落在盘框内**" ✗ ⇒ 孔心落在盘外一点点就"合法" ✗，
#     而它的**铜盘**（Ø0.60 ✓）恰好压进盘里 ✗✗：实测 v47 有 **7/18** 个孔压盘 ✗，
#     其中 `Via18`（RC 网）把 **DATA_IN** 的盘压了 **0.20 mm** ⇒ **两张网并在一起（短路）** ✗✗
#     —— 用户拿图一眼就看出来了 ✗，而我当时还写了句"只禁盘内 ⇒ 不会出现环套环"的错结论 ✗。
#   ★ 代价要认 ✓：禁落区变大 ⇒ 过孔会变多 ✓（实测外扩 0.2 mm 时 18→28 颗 ✗），
#     但**短路不能接受** ✗ ⇒ 多几颗孔是必须付的 ✓。
#   ★★ 净空取 **0.15 mm**（不是走线用的 0.20 ✓）：工艺上 1 oz 铜**最小线间距**只要
#      **0.127 mm**（5 mil ✓，嘉立创工艺能力表 ✓）⇒ 0.15 mm 是**合法且安全**的 ✓；
#      而 0.20 mm 在这个 0.4 mm 间距的 QFN 旁边会把可落孔区吃光 ✗
#      ⇒ 实测：0.20 时只能连通 **4/9** ✗（布不出来 ✓），必须先保铜面再谈美观 ✓。
#   ★★ 净空值必须是**规则值 `VIA_SAFE_MM` = 0.25** ✗（2026-10-01 第二次修 ✗）：
#     ✗ 之前写 0.15（按“1 oz 铜最小间距 0.127 ✓”订的工艺下限 ✓）⇒ 布出来的孔
#       **净距只有 0.15 mm** ✗ ⇒ 违反用户规则 ✗，而且闸门 `via_pad_conflicts` 只报 1 处、
#       独立校验器 `pcb_check` 报 3 处 ✗（实测 ✓）—— 差的就是这 0.10 mm ✓。
#     ★ 教训 ✓：**布线时的搜索余量**不能比**规则值**松 ✗ —— 闸门只能“事后否决”✗，
#       不能“绕开”✗ ⇒ 搜索必须按规则值躲 ✓。
#     ★ 定义在 `VIA_SAFE_MM` **之后** ✓（要用到它 ✗ —— 先前排前面会 NameError ✗）。
# ★★ 过孔**安全距离**规则值 ✓（2026-10-01 用户定 ✓）：「通孔不能在元件内，并与有安全距离」✓
#   = 过孔**铜盘边** → 焊盘框边的**最小净距** ✓（**同网的盘也一样** ✗ ⇒ 不许 via-in-pad ✗）。
#   ★ 和 `pcb_check.VIA_SAFE_MM` **同值、各自实现** ✓（故意的 ✓ —— 布线与校验不许共用一份 ✗，
#     否则一边错两边一起错 ✗）；改这里就**必须同步**改那边 ✓，两处都写了这条注释 ✓。
#   ★ 值 0.25 mm 的理由（我定的 ✓，可调 ✓）：1 oz 铜**最小线间距 0.127 mm**（嘉立创工艺表 ✓）
#     ⇒ 0.25 是留了一档余量的安全值 ✓。
#   ★★ 用法警告 ✗：它是「**盘边**→盘边」✓ ⇒ 当作「**孔心**→盘边」用的时候
#     **必须加铜盘半径** ✓（`VIA_CLEAR_MM` = 0.30 ✓）—— 少加就会让孔压到盘上 ✗。
VIA_SAFE_MM = 0.25
VIA_PAD_CLEAR_MM = VIA_SAFE_MM                    # = 0.25 ✓（盘边→盘边的规则值 ✓）
VIA_PAD_KEEPOUT_MM = VIA_CLEAR_MM + VIA_PAD_CLEAR_MM   # = 0.55 ✓（**孔心**→盘边 ✓）
# ★★ 细间距区**缩宽（neck-down）** ✓（2026-10-01 用户选 ① ✓）：
#   进**细间距元件**（`fine` = 同件最近盘中心距 ≤ 0.65 mm ✓，如 QFN 0.4 ✓）
#   **前 `NECK_ZONE_MM`（1.5 mm ✓）** 内，**所有网**的线宽收到 **`NECK_MIL` = 10 mil** ✓。
#   ★ 值怎么来的（算的 ✓，不是拍的 ✗）：`VSS` 中心离 `PA2` 盘边 0.300 ✓、净距规则 0.15
#     ⇒ 半宽上限 0.150 ⇒ **线宽上限 0.300 mm** ⇒ **12 mil（0.3048）差 0.0048 mm 过不去** ✗
#     ⇒ 取 10 mil（0.254 ✓ 半宽 0.127 ✓ 净距 0.173 ✓ ≥ 0.15 ✓）。
#   ★ 理由（工艺 ✓）：0.4 mm 间距的 QFN 不能整根跑 24 mil ✓；缩最后一段是业界常规做法 ✓
#     （载流靠整段铜面 ✓，0.5 mm 的 10 mil 短头子对载流几乎无影响 ✓）。
NECK_MIL = 8
NECK_W_MM = NECK_MIL * 25.4 / 1000.0              # = 0.254 mm ✓（半宽 0.127 ✓）
NECK_ZONE_MM = 1.5
# ★★ 安装孔的**禁落区** ✓（2026-10-01 用户定 ✓：「安装孔附近是不能布线的，更不能穿体」✓）：
#   核心孔件 `HoleModuleID` 的 `hole size="2.2mm,0.0mm"` ⇒ **没有铜** ✗
#   ⇒ 以前 `obstacles()` 里它一个障碍都不产生 ✗ ⇒ 实测 `v50H.fzz` 有 **4 根走线穿过孔** ✗
#     （距内壁 −1.100 / −0.900 / −0.800 / −0.300 mm ✓，其中 −1.100 = 正穿孔心 ✓）。
#   ★ 挡法 = **方框**（`孔外接框 + HOLE_CLEAR_MM` ✓）—— 比方孔多挡四个角 ✓（更严 ✓，代价小 ✓）；
#     校验器 `pcb_check` 第 ⑨ 条用**圆**的精确判据 ✓（两边各自实现 ✓，互不背书 ✓）。
#   ★ 与 `pcb_check.HOLE_CLEAR_MM` **同值** ✓（改一处必须同步 ✓）。
HOLE_CLEAR_MM = 0.25
# ★★ 过孔**递增代价** ✓（2026-09-30 用户定："改代价结构" ✓）——
#   同一张网里**每多用一颗过孔**，下一颗就更贵 `VIA_ESCALATE` 倍 ✓：
#     第 1 颗 = 1.0× ✓、第 2 颗 = 1.6× ✓、第 3 颗 = 2.2× ✓ …
#   背景（实测 ✓）：过孔在旧口径下"躲一个交叉就钻一颗" ✗ ⇒ 9 张网用了 18 颗 ✓
#   （理论下限 5 颗 ✓）；而把 via_cost 平着调高（20/60 ✓）只降到 16 颗 ✗、到顶 ✓。
#   递增才是对症的 ✓：它惩罚的是"一条网上反复钻来钻去" ✓。
VIA_ESCALATE = 0.6
# ★★ 拐弯代价 ✓ / 主层优惠 ✓（2026-09-30 用户定 ✓，原话："现在的 PCB 文件我看不懂、也改不了" ✓
#   = 线路**碎**、折点多 ✓）——
#   `TURN_COST`：每拐一次弯加多少分 ✓（直行一格 = 1.0 ✓）⇒ 路径更直 ✓、折点更少 ✓
#     ⇒ **走线对象变少** ✓（`split_touchings` 按折点切段 ✓）⇒ Fritzing 里更好读、好改 ✓；
#   `LAYER_PEN`：走在**非主层**上每格加多少分 ✓ ⇒ 每张网尽量待在自己的主层 ✓、
#     只在必要时跨层 ✓ ⇒ 过孔自然减少 ✓（本板理论下限 5 ✓、原来 18 ✗）。
TURN_COST = 0.5
LAYER_PEN = 0.35
# ★★ 「留路」✓（2026-09-30 ✓，仓规 §5b 第 ⑩ 条的同一条病 ✓）：
#   先布的**电源/地**不许把中间（φ8 那片拥挤区 ✓）占满 ✗ ⇒
#   中间走廊留给后面的信号线 ✓。实测证据 ✓：电源 16 mil + 信号 12 mil 时
#   9 网只通 8 ✗，唯一没通的是 `LED_DIN` ✗（被先布的电源堵死 ✓ ——
#   而 12 mil 全一样宽时反而 9/9 ✓ ⇒ 卡住的是"路" ✓，不是"宽" ✓）。
#   `MID_KEEP_MM` = 被保护的中间半径 ✓；`MID_KEEP_W` = 罚多少格 ✓
#   （A* 走一格算 1.0 ✓，罚 8 格 ≈ 1.2 mm ✓ ≈ 绕 12 mm 才开始划算 ✓）。
MID_KEEP_MM = 4.0
MID_KEEP_W = 8.0
EDGE_MM = 0.30             # 线离板边 ✓
K_VIA = 10.0               # 一个过孔按"多少格长度"算 ✓（系数可调 ✓）
LAYERS = ("copper0", "copper1")


class Grid(object):
    """两层栅格 ✓：`1` = 可以走 ✓ / `0` = 被占 ✗"""

    def __init__(self, rect, cell_mm=CELL_MM):
        self.cell = U(cell_mm)
        self.x0, self.y0 = rect[0], rect[1]
        self.nx = int((rect[2] - rect[0]) / self.cell) + 1
        self.ny = int((rect[3] - rect[1]) / self.cell) + 1
        self.g = {lay: bytearray(b"\x01" * (self.nx * self.ny)) for lay in LAYERS}

    def xy(self, ix, iy):
        return (self.x0 + ix * self.cell, self.y0 + iy * self.cell)

    def rc(self, x, y):
        return (int(round((x - self.x0) / self.cell)), int(round((y - self.y0) / self.cell)))

    def inside(self, ix, iy):
        return 0 <= ix < self.nx and 0 <= iy < self.ny

    def free(self, lay, ix, iy):
        return self.inside(ix, iy) and self.g[lay][iy * self.nx + ix]

    def free_box(self, lay, box, grow, free=True):
        """把矩形（`box` + `grow`）标成可走/不可走 ✓（`free=False` ⇒ 挡 ✓）"""
        i0, j0 = self.rc(box[0] - grow, box[1] - grow)
        i1, j1 = self.rc(box[2] + grow, box[3] + grow)
        v = 1 if free else 0
        for j in range(max(0, j0), min(self.ny - 1, j1) + 1):
            row = j * self.nx
            for i in range(max(0, i0), min(self.nx - 1, i1) + 1):
                self.g[lay][row + i] = v

    def block_box(self, lay, box, grow):
        self.free_box(lay, box, grow, free=False)

    def clone(self):
        """拷一份 ✓（每张网一层子拷贝 ✓ —— 比每次重建障碍快得多 ✓）"""
        o = Grid.__new__(Grid)
        o.cell, o.x0, o.y0, o.nx, o.ny = self.cell, self.x0, self.y0, self.nx, self.ny
        o.g = {k: bytearray(v) for k, v in self.g.items()}
        return o

    def block_frame(self, margin):
        """只挡**四周一圈** ✓（离板边 < margin ✓）—— ✗ 不能拿一个矩形当障碍：
        那是**整块板** ✓ ⇒ 可走 0 格 ✗（2026-09-30 实测：0.0% ✓ 当场看出来 ✓）。"""
        m = int(margin / self.cell) + 1
        for lay in LAYERS:
            for j in range(self.ny):
                for i in range(self.nx):
                    if min(i, j, self.nx - 1 - i, self.ny - 1 - j) < m:
                        self.g[lay][j * self.nx + i] = 0

    def block_seg(self, lay, a, b, grow, steps=24):
        """把一条**线段**（按小矩形拆 ✓）标成不可走 ✓ —— 件自己的铜箔是细长图形 ✓"""
        for k in range(steps):
            t0, t1 = k / float(steps), (k + 1) / float(steps)
            x = a[0] + (b[0] - a[0]) * t0
            y = a[1] + (b[1] - a[1]) * t0
            x2 = a[0] + (b[0] - a[0]) * t1
            y2 = a[1] + (b[1] - a[1]) * t1
            self.block_box(lay, (min(x, x2), min(y, y2), max(x, x2), max(y, y2)), grow)


def obstacles(model, part_copper=True):
    """把障碍整理成**带归属的表** ✓ ⇒ `([(lay, box, grow, tag)], 统计)`

    ★★ `tag` = 这块障碍"属于哪张网的焊盘" ✓（件铜箔/板边 = `None` ✓）。
      为什么要归属 ✗：**同一张网的线不该被自己焊盘的净空挡住** ✓（不然线根本进不了盘 ✗
      —— 第一版就是这么失败的 ✗：GND 9 个脚一出发就出不去 ✗）。
      ⇒ 布某张网时，把 `tag == 本网` 的障碍**减掉**、别人网的照旧挡着 ✓。
    """
    items = []
    grow = U(TRACE_MM / 2 + CLEAR_MM)
    n_hole = 0
    # ① 板边留边 ✓ ⇒ 由 `make_grid` 调 `block_frame` ✓（✗ 不能写成一块矩形障碍：
    #   那是**整块板** ✓ ⇒ 一格都走不了 ✗ —— 2026-09-30 实测踩到过 ✓）
    # ② 焊盘铜 ✓（带网名 ✓；通孔盘两层都算 ✓）
    net_of = {}
    n_pad = 0
    for q in model["pads"]:
        lays = LAYERS if q["thr"] else (q["layer"],)
        nm = None
        for net, mem in (model.get("net_pads") or {}).items():
            if (q["title"], q["cid"]) in mem:
                nm = net
                break
        net_of[(q["title"], q["cid"])] = nm
        # ★★ 细间距盘：障碍净空也按**缩宽后**算 ✓（2026-10-01 用户定 ① 之后补 ✗）：
        #   ✗ 若按**信号粗档**（0.302 ✓）挡 ⇒ 隔壁盘的禁落区把 `VSS` 前面那道
        #     “只能过细线”的缝**吃掉了** ✗ ⇒ A* 直接报布不通 ✓（实测：改前 2/9 ✓ ⇒ 一改就 **0/9** ✗）。
        #   ✓ 按 `NECK_MIL`（10 mil ⇒ 净空 0.277 ✓）算 ⇒ 缝还在 ✓
        #     而进去的那一段由写回器**真的变成 10 mil** ✓（`gen_routes.split_neck` ✓）
        #     ⇒ 模型与实际铜面一致 ✓。
        gp = U(NECK_W_MM / 2 + CLEAR_MM) if q.get("tight") else grow
        for lay in lays:
            if lay in LAYERS:
                items.append((lay, q["box"], gp, nm))
                n_pad += 1
    # ③ 件自己的**铜箔图形** ✓（线圈绕组 722 条 ✓ —— 不挡它线会压在绕组上 ✗；tag=None ✓）
    # ★★ ③b 安装孔 ✓（2026-10-01 用户定 ✓，见 `HOLE_CLEAR_MM` ✓）—— 孔件**没有铜** ✗，
    #   所以必须**单独**按它的**外接框**挡 ✓（否则走线会直接穿过去 ✗，实测 4 根 ✓）。
    for (c, dia, _cup) in (model.get("holes") or ()):
        rr = U(dia / 2.0)                              # 孔半径 ⇒ sketch 单位 ✓
        items.append(("both", (c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr),
                      U(HOLE_CLEAR_MM), None))
        n_hole += 1
    n_cu = 0
    if part_copper:
        import xml.etree.ElementTree as ET
        for p in model.get("parts", []):
            if p.get("svg_text") is None or "loc" not in p:
                continue
            mid = p.get("moduleId") or ""
            if mid == PP.BOARD_MID or mid.startswith(("Breadboard", "Via", "Wire")):
                continue
            try:
                root = ET.fromstring(p["svg_text"])
                k, (ox, oy) = PB.svg_k(root)
                shapes, _bad = PP.copper_shapes(root)
            except Exception:                                      # noqa: BLE001
                continue
            flip = ((p.get("pv") or {}).get("bottom") or "").lower() == "true"
            to_lay = (lambda L: ("copper0" if L == "copper1" else "copper1")) if flip else (lambda L: L)
            for s in shapes:
                lay = to_lay(s["layer"])
                if lay not in LAYERS or s["id"]:
                    continue                                       # 带 id 的 = 焊盘 ✓ 已算过 ✓
                b = s["box"]
                pts = [PB.apply(p["M"], (u - ox) * k, (v - oy) * k) for u, v in
                       ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]))]
                n_cu += 1
                xs = [p["loc"][0] + q[0] for q in pts]
                ys = [p["loc"][1] + q[1] for q in pts]
                items.append((lay, (min(xs), min(ys), max(xs), max(ys)), grow, None))
    return items, dict(pads=n_pad, copper=n_cu, net_of=net_of, holes=n_hole)


def make_grid(rect, cell, items, extra=(), skip_tag=None):
    """⇒ 基准栅格 ✓（障碍表全挡上 ✓；板边留边 ✓）

    ★★ 每张网用 `base.clone()` ✓ 再把自己焊盘的地盘 `free_box` 挖回来 ✓ ——
      比"每段重建一次障碍"快得多 ✓（0.15 mm 网格有 2.8 万格 ✗）。
    """
    grid = Grid(rect, cell)
    grid.block_frame(U(EDGE_MM) + U(TRACE_MM / 2 + CLEAR_MM))
    for it in items:
        lay, box, grow, _tag = it
        for l2 in (LAYERS if lay == "both" else (lay,)):
            grid.block_box(l2, box, grow)
    for lay, box, grow in extra:
        for l2 in (LAYERS if lay == "both" else (lay,)):
            grid.block_box(l2, box, grow)
    return grid


def neck_zones(pads, grow_mm=None):
    """⇒ `[(box, mm 净宽上限), …]` ✓ = **细间距元件附近要缩宽**的区域 ✓（2026-10-01 用户定 ✓）

    起因（实测 ✓，不是推测 ✗）：`U1` = QFN **0.400 mm 间距** ✓、盘 0.600×0.200 ✓
    ⇒ 相邻两盘**边缘只隔 0.200 mm** ✓；而电源网走 **24 mil（0.6096 ✓ 半宽 0.305 ✓）**
    ⇒ 瞄 `VSS` 中心（离 `PA2` 盘边 **0.300** ✓）时 **超了 0.005 mm** ✗
    ⇒ 铜盖住 `PA2` ⇒ **真短路** ✗（独立校验器 ⑤ 抓到 ✓）。

    ★ 缩宽量是**算出来**的 ✓（不拍脑袋 ✗）：净距规则 `CLEAR_MM` = 0.15 ✓、可用间隙 0.300 ✓
      ⇒ **半宽上限 = 0.150** ✓ ⇒ **线宽上限 = 0.300 mm** ✓
      ⇒ **12 mil（0.3048）过不去** ✗（超 0.0048 ✓）⇒ 取 **`NECK_MIL` = 10 mil（0.254 ✓ 半宽 0.127 ✓）** ✓。
    ★ 只**缩**不涨 ✓：信号线本来 12 mil ⇒ 进区也变 10 ✓（绝不把细线“涨”成粗线 ✗）。
    """
    if grow_mm is None:
        grow_mm = NECK_ZONE_MM
    g = U(grow_mm)
    out = []
    for _k, q in pads.items():
        if not q.get("tight"):
            continue                        # ✗ 只对**间隙放不下线宽**的盘缩宽 ✓（2026-10-01 ✓）
        b = q.get("box")
        if not b:
            continue
        out.append(((b[0] - g, b[1] - g, b[2] + g, b[3] + g), NECK_W_MM))
    return out


def in_neck(x, y, zones):
    """点是否落在**缩宽区**里 ✓"""
    for (b, _w) in zones:
        if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
            return True
    return False


def carve_pads(grid, pads, mem, grow, neck_grow=None):
    """把**本网自己焊盘**的铜与净空区改回可走 ✓ ⇒ 线才进得去 ✓

    ✗ 不挖会怎样（实测 ✓）：`U1` 是 QFN20、脚距 0.4 mm ✗ —— 邻脚的净空就把出口
    堵死了 ✗ ⇒ 逐网 0 段全败 ✗。
    """
    for t, c in mem:
        q = pads.get((t, c))
        if not q:
            continue
        # ★★ 细间距盘：只能按**缩宽后的净空**挖 ✓（2026-10-01 用户定 ✓）：
        #   ✗ 按粗线的 `grow`（GND 0.455 ✓）挖 ⇒ 把**隔壁盘的禁落区**一起挖掉了 ✗
        #     ⇒ 粗线就能从别人盘上穿过去 ✓✓（实测这就是 `GND`↔`PA2` 短路的机制 ✓：
        #     `VSS` 与 `PA2` 只隔 0.4 mm ⇒ VSS 的 0.455 挖盘区把 PA2 也包了进去 ✗）。
        gg = grow
        if neck_grow is not None and q.get("tight"):
            gg = neck_grow
            # ★ 与 `obstacles` 里“细间距盘按缩宽算”**同一个值** ✓（两处必须一致 ✗：
            #   一边 0.277 ✓ 一边 0.302 ✗ ⇒ 挖出来的比挡住的还小 ⇒ 一格可走的都没有 ✓）
        for lay in q["lays"]:
            grid.free_box(lay, q["box"], gg, free=True)


# ★★ A* 的**展开上限** ✓（2026-10-01 抽出来并放大 ✗）：
#   ✗ 旧值是硬写的 `400000` ✗ ⇒ 本板 0.10 mm 格 ~ 250×250×2 层×4 向 ≈ **50 万状态** ✗
#     ⇒ **很容易撞上限** ✗ ⇒ `astar` 返回 None ✗ ⇒ 把"其实能布通"误报成"布不通" ✗✗
#     （而且完全不提示 ✗ —— 我当时据此下了"这个摆位无解"的结论 ✗，**是错的** ✗）。
#   ⇒ 默认放大 10 倍 ✓；真撞上也会在下面打印一声 ✗（不静默 ✗）。
ASTAR_LIMIT = 4000000
_ASTAR_HIT = []          # 撞上限**只报一次** ✓（免得刷屏 ✗）


# ★★ 布不通时的**诊断** ✓（2026-10-01 立 ✓，只需 `--why` 打开 ✓）：
#   目的 —— 区分两件事 ✗（以前不分 ✓，所以老在猜 ✗）：
#     ① **真没路** ✗（障碍模型把目标周围堵死了 ✓）；
#     ② **有路但 A* 没搜到 / 代价结构不对** ✗（如撞上限 ✓、或拐弯/换层代价把它顶歪 ✓）。
#   做法：从起点泛洪一遍 ✓（步法、`no_via` 与 `astar` **同口径** ✓）⇒ 看目标格在不在可达集里 ✓。
DIAG = {"on": False, "fails": []}


def flood(grid, lay0, start, no_via=()):
    """从起点泛洪 ✓ ⇒ 可达状态集 `{(层, (ix, iy))}` ✓（与 `astar` 同口径 ✓）"""
    s = (lay0, grid.rc(*start))
    if not grid.free(s[0], s[1][0], s[1][1]):
        return set()
    seen = {s}
    st = [s]
    while st:
        cl, (ix, iy) = st.pop()
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cl, (ix + dx, iy + dy))
            if nxt in seen or not grid.free(cl, ix + dx, iy + dy):
                continue
            seen.add(nxt)
            st.append(nxt)
        nl = "copper1" if cl == "copper0" else "copper0"
        nxt = (nl, (ix, iy))
        if nxt not in seen and grid.free(nl, ix, iy):
            seen.add(nxt)
            st.append(nxt)
    return seen


def astar(grid, lay0, start, goals, via_cost, blocked_extra=None, avoid=None, avoid_w=0.0,
          no_via=(), turn=0.0, pen_layer=None, pen=0.0):
    """两层 A* ✓：`start`/`goals` = `(lay, (x, y))` ✓ ⇒ 路径 `[(lay, (x,y)), …]` 或 None ✓

    `avoid` = **加罚的格子**（`{(ix, iy)}` ✓）+ `avoid_w` = 每格加罚多少 ✓
      ⇒ 电源/地走中间时被顶去绕边 ✓（**「留路」** ✓，见 `MID_KEEP_*` ✓）。
      ★ 罚不是"禁止" ✓ —— 中间确有要接的脚（QFN 在内）✓ ⇒ 只把"穿过"变贵 ✓，
        还是**能走到** ✓（保证不会因禁死而变成布不通 ✗）。

    ★★ 2026-09-30 修 ✗：**过孔不许打在起点/终点盘的格子上** ✓（用户原话：
      「有时候需要添加过孔，来跨层连接」✓ —— 过孔是对的 ✓，但**位置**必须是
      "**离开焊盘之后**" ✓）。
      ✗ 旧写法允许"一开场就在起点盘上换层" ✗ ⇒ 写回时又把该段起点**吸附到焊盘中心** ✗
        ⇒ 那是一条 **copper1 的铜从 copper0 的 SMD 盘正中心出发** ✗ ——
        **看着接上了、电气上根本没接** ✗（实测三处悬空端点就是这个 ✓）。
      ⇒ 现在：起点/终点那两格**只准走本层** ✓，要换层得**先离开盘** ✓ 再换、
        再绕回盘自己那层来收尾 ✓（这才是过孔真正的用法 ✓）。
    """
    def key(S):
        return S
    # ★★ 2026-09-30 加两项（用户："PCB 文件看不懂也改不了" ✓）：
    #   · `turn` = **拐弯代价** ✓ —— ✗ 旧状态只有 `(层, 格)` ✗ ⇒ 无法给拐弯计费 ✗；
    #     现在状态 = `(层, 格, 来向)` ✓（来向 4 = 起点 ✓）⇒ 直行 1.0 ✓、拐弯 +`turn` ✓
    #     ⇒ 路径更直 ✓、折点更少 ✓ ⇒ `split_touchings` 切出的走线对象更少 ✓ ⇒ **Fritzing 里好读好改** ✓。
    #   · `pen_layer`/`pen` = **非主层**每格加 `pen` 分 ✓ ⇒ 每张网尽量待在自己的主层 ✓
    #     ⇒ 只在必要时跨层 ✓ ⇒ 过孔变少 ✓（本板下限 5 ✓、旧版 18 ✗）。
    DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
    s = (lay0, grid.rc(*start), 4)
    if not grid.free(s[0], s[1][0], s[1][1]):
        return None
    gset = set()
    for lay, xy in goals:
        gset.add((lay, grid.rc(*xy)))
    if (s[0], s[1]) in gset:
        return [(s[0], s[1])]
    s_cell = s[1]
    g_cells = {g[1] for g in gset}
    seen = {s: 0.0}
    pq = [(0.0, 0, s)]
    prev = {}
    cnt = 0
    while pq:
        f, _o, cur = heapq.heappop(pq)
        cl, (ix, iy), cd = cur
        if (cl, (ix, iy)) in gset:
            path, node = [], cur
            while node in prev:
                path.append((node[0], node[1]))
                node = prev[node]
            path.append((node[0], node[1]))
            return list(reversed(path))
        cnt += 1
        if cnt > ASTAR_LIMIT:
            # ★ 撞上限时**报一声** ✗（不静默 ✗）—— 否则"能布"会被当成"无解" ✗（2026-10-01 踩过 ✓）
            if not _ASTAR_HIT:
                _ASTAR_HIT.append(1)
                print("   ⚠ A* 展开到上限 %d ⇒ 这条**可能**本来布得通 ✗（不得当\"无解\" ✗）"
                      % ASTAR_LIMIT)
            return None
        g0 = seen[cur]
        onpen = pen if (pen_layer is not None and cl == pen_layer) else 0.0
        nbrs = []
        for di, (dx, dy) in enumerate(DIRS):
            step = 1.0 + onpen
            if cd != 4 and cd != di:
                step += turn                       # ★ 拐弯加钱 ✓
            nbrs.append(((cl, (ix + dx, iy + dy), di), step))
        # ★★ 过孔只准打在"**离开焊盘之后**" ✓ —— 起点/终点那两格禁掉 ✗（见函数头注 ✓）：
        #   ✗ 否则过孔会落在 SMD 盘中心 ✗ ⇒ 换层后的铜虽然"看着从盘心出发"✗，
        #     但那个盘在**另一层** ✗ ⇒ 电气上没接上 ✗（实测三处悬空端点 ✓）。
        if (ix, iy) != s_cell and (ix, iy) not in g_cells and (ix, iy) not in no_via:
            nbrs.append((('copper0' if cl == 'copper1' else 'copper1', (ix, iy), cd), via_cost))
        for nxt, w in nbrs:
            nl, (jx, jy), _nd = nxt
            if not grid.free(nl, jx, jy):
                continue
            ng = g0 + w
            if avoid is not None and (jx, jy) in avoid:
                ng += avoid_w          # ★ 「留路」加罚 ✓（不是禁死 ✓，仍能走到 ✓）
            if ng < seen.get(nxt, 1e18):
                seen[nxt] = ng
                prev[nxt] = cur
                h = min(abs(jx - g[1][0]) + abs(jy - g[1][1]) + (0 if nl == g[0] else via_cost)
                        for g in gset)
                heapq.heappush(pq, (ng + h, -ng, nxt))
    return None


def _flush(segs, cur, grid):
    """把一段（同层、同向 ✓）收成线段 ✓"""
    if len(cur) >= 2:
        segs.append((cur[0][0], grid.xy(*cur[0][1]), grid.xy(*cur[-1][1])))


def path_to_segments(path, grid):
    """格子路径 ⇒ 线段（同层、同方向合并 ✓）＋ 过孔位置 ✓

    ★★ 转角必须**收到转角点本身** ✓（即 `b` ✓）—— ✗ 老版收到 `path[j-1]` ✗
      ⇒ 相邻两段之间**正好空一格** ✗（实测 0.150 mm ✓）⇒ 整条铜箔是**断**的 ✗
      （而且布线器自己的 `ok` 只说明「A* 找到了路」✗，从不检查拼出来的几何 ✗
       ⇒ 是**写回器的独立复核**抓出来的 ✓ —— 见仓规「不许自证」✓）。
      ⇒ 判据：段与段**必须共享端点** ✓（Fritzing 的 `<connect>` 只认端↔端 ✓）。
    """
    segs, vias = [], []
    cur = [path[0]]                      # 当前段：同层、同向的点列 ✓
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:                 # 换层 ⇒ 过孔 ✓
            vias.append(grid.xy(*a[1]))
            _flush(segs, cur, grid)
            cur = [b]
            continue
        if len(cur) >= 2:
            d1 = (a[1][0] - cur[-2][1][0], a[1][1] - cur[-2][1][1])
            d2 = (b[1][0] - a[1][0], b[1][1] - a[1][1])
            if d1 != d2:                 # 转向 ⇒ 本段收到**转角 a** ✓
                cur.append(a)
                _flush(segs, cur, grid)
                cur = [a]
        cur.append(b)
    _flush(segs, cur, grid)
    return segs, vias


def seg_hits_rect(p, q, rect, half=0.0):
    r"""线段（沿法向展宽 `half` ✓）与矩形相碰 ⇒ True ✓

    ★ 用途 ✓：判“这段铜是不是**压住**了某个焊盘” ✓ —— 用户 2026-09-30 定：
      **不许线压任何焊盘** ✓，含**没有网的空脚** ✓。
      理由 ✗（实测 ✓）：Fritzing 里“线盖住盘”就等于**接通** ✗
      ⇒ 空脚会被悄悄接进那条网 ✗；且以后要用那个脚时才发现短线 ✗。
    ★ 只管几何 ✓；**层由调用者先筛** ✓（不同层不算碰 ✓ ——
      ✗ 实测：分层前报出过 5 个假阳性 ✗，全是 copper1 的线从 copper0 的盘上方经过 ✓）。
    """
    x0, y0, x1, y1 = rect[0] - half, rect[1] - half, rect[2] + half, rect[3] + half

    def inside(z):
        return x0 <= z[0] <= x1 and y0 <= z[1] <= y1

    if inside(p) or inside(q):
        return True

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def onseg(o, a, b):
        return (min(o[0], b[0]) - 1e-12 <= a[0] <= max(o[0], b[0]) + 1e-12
                and min(o[1], b[1]) - 1e-12 <= a[1] <= max(o[1], b[1]) + 1e-12)

    for e1, e2 in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
                   ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        d1, d2 = cr(e1, e2, p), cr(e1, e2, q)
        d3, d4 = cr(p, q, e1), cr(p, q, e2)
        if ((d1 * d2 < 0 and d3 * d4 < 0)
                or (abs(d1) < 1e-12 and onseg(e1, p, e2))
                or (abs(d2) < 1e-12 and onseg(e1, q, e2))
                or (abs(d3) < 1e-12 and onseg(p, e1, q))
                or (abs(d4) < 1e-12 and onseg(p, e2, q))):
            return True
    return False


def pads_covered(segs, pads, own, half):
    r"""⇒ 被这段铜**压住**的焊盘 key 集合 ✓（`own` = 这条线自己的两端 ✓ 不算 ✓）

    ★★ 层字段**只能用 `pad_index` 的那一套** ✓（`lays` ✓）——
      ✗ 我第一版写成 `w.get("thr")`/`w.get("layer")` ✗ ⇒ 两者都是 None ✗
      ⇒ `lays=(None,)` ⇒ `lay not in lays` 永远成立 ⇒ **一次也没触发** ✗
      ⇒ 跑出来的文件与改之前**字节级相同** ✗（实测 ✓ 这才发现 ✓）。
      教训（本仓第 8 条 ✓）：**改前先看结构里到底叫什么** ✗。
    """
    bad = set()
    for lay, p, q in segs:
        for key, w in pads.items():
            if key in own:
                continue
            lays = w.get("lays") or (LAYERS if w.get("thr") else (w.get("layer"),))
            if lay not in lays:
                continue
            b = w.get("box")
            if b and seg_hits_rect(p, q, b, half):
                bad.add(key)
    return bad


def pad_index(model):
    """⇒ `{(位号, connectorN): dict(lays, c, box)}` ✓（层已含"翻面对调"的修正 ✓）"""
    out = {}
    for q in model["pads"]:
        lays = [l for l in (LAYERS if q["thr"] else (q["layer"],)) if l in LAYERS]
        if not lays:
            continue
        out[(q["title"], q["cid"])] = dict(
            lays=lays, box=q["box"],
            # ★★ 过孔例外的两个标记要**带过来** ✓（2026-10-01 ✓，否则布线器看不见 ✗）：
            #   `epad` = 裸露焊盘 ✓、`fine` = 细间距盘 ✓ ⇒ 同网时它们不设禁落区 ✓
            #   （校验器 `pcb_check` 用**同一套**标记判 ✓，两边口径一致 ✓）
            epad=bool(q.get("epad")), fine=bool(q.get("fine")),
            # ★★ 「该缩宽」标记也必须带过来 ✗（2026-10-01 实测踩过 ✓）：
            #   ✗ 漏了它 ⇒ `neck_zones()` 拿到的一律是 `None` ⇒ **缩宽区是空的** ✗
            #     ⇒ 写回不缩宽 ✗ ⇒ 实测「缩宽段 **0** 条」✗ + 独立复核报
            #       「④ 同层交叉 6 处」✗ 与「⑤ GND 粘上 U1.connector2」✗ 一起回来 ✓。
            #   ★ 判据本身只写在 `pcb_check.collect` 一处 ✓（`tight` / `gap_mm` ✓）⇒ 这里只**搬运** ✓。
            tight=bool(q.get("tight")), gap=q.get("gap_mm"),
            # ★ 焊盘中心**只有一个口径** ✓：用 `part_pads` 的 `abs` ✓
            #   ✗ 别自作聪明取外接框中心 ✗ —— 两者实测差 0.05 mm ✗ ⇒
            #   布线器吸附到 A ✓、写回器按 B 找焊盘 ✗ ⇒ 焊盘端对不上 ✗（悬空端点 ✗）。
            c=q["c"])
    return out


def _net_keys(net_pads, pads):
    """几种**排序键** ✓（= \"先布哪张网\"的几种策略 ✓）—— 单次序不稳 ✗，多种取优 ✓

    ✗ 实测教训（2026-09-30 ✓）：**先布 GND/5V** ⇒ 中间走廊被抢光 ✗ ⇒ 小网接不上 ✗；
      **只改成\"短网先\"** ⇒ 又把 `COIL_B`/`DATA_OUT`/`5V` 挤掉 ✗（失败只是换了个位置 ✗）
      ⇒ 单贪心不够 ✓ ⇒ 多跑几个次序、比较取优 ✓（见 `route` ✓）。
    """
    def pts(n):
        return [pads[k]["c"] for k in net_pads[n] if k in pads]

    def area(n):
        p = pts(n)
        if len(p) < 2:
            return 0.0
        return ((max(q[0] for q in p) - min(q[0] for q in p))
                * (max(q[1] for q in p) - min(q[1] for q in p)))

    def span(n):
        p = pts(n)
        if len(p) < 2:
            return 0.0
        return ((max(q[0] for q in p) - min(q[0] for q in p))
                + (max(q[1] for q in p) - min(q[1] for q in p)))
    return [("短网先（面积↑）", lambda n: area(n)),
            ("脚数↑", lambda n: len(net_pads[n])),
            ("周长↑", lambda n: span(n)),
            ("长网先（面积↓）", lambda n: -area(n)),
            ("多脚先（脚数↓）", lambda n: -len(net_pads[n])),
            ("周长↓", lambda n: -span(n))]


def route(items, rect, net_pads, pads, cell=CELL_MM, via_cost=K_VIA, verbose=True, tries=6,
          width_of=None, first=(), mid_keep=(), ban_via=(), copper_keep=()):
    """⇒ **多种次序里最优的那份** ✓（先比连通网数 ✓，再比总长 ✓）

    ★★ 2026-09-30 加**按网分宽** ✓（用户定 ✓：「用与 JST-SH 1.0 功率匹配的 5V 和 GND 线宽 ✓，
      信号线 12 或 8 mil ✓」）——JST SH 官方额定 **1 A/触点**（AWG #28 ✓）⇒ 电源网要宽 ✓。
      · `width_of(net)` ⇒ 该网的**线宽 mm** ✓（同时决定它的净空 ✓）；缺省 ⇒ `TRACE_MM` ✓；
      · `first` ⇒ **先布的网** ✓（宽线要先占地方 ✗ —— 这就是仓规 §5b 第 ⑩ 条"留路"的"先宽后细"版 ✓）。
    """
    w_of = width_of or (lambda n: TRACE_MM)
    best = None
    for name, key in _net_keys(net_pads, pads)[:tries]:
        order = sorted(net_pads, key=lambda n: (0 if n in tuple(first) else 1, key(n)))
        res = _route_once(items, rect, net_pads, pads, cell, via_cost, order,
                          width_of=w_of, mid_keep=mid_keep, ban_via=ban_via,
                          copper_keep=copper_keep)
        n_ok = sum(1 for d in res.values() if d["ok"])
        ln = sum(math.hypot(s[1][0] - s[2][0], s[1][1] - s[2][1])
                 for d in res.values() for s in d["segs"])
        if verbose:
            print("   次序《%-14s》：连通 %d/%d ✓｜长 %6.1f mm" % (name, n_ok, len(res), MM(ln)))
        if best is None or (n_ok, -ln) > (best[0], -best[1]):
            best = (n_ok, ln, res, name)
    if verbose and best:
        print("   ⇒ 取《%s》那份 ✓（连通 %d/%d ✓）" % (best[3], best[0], len(best[2])))
    return best[2]


def _score(res):
    """打分 ✓（**先比连通网数 ✓，再比总长 ✓**）—— 拆线重布就靠它决定"接不接受" ✓"""
    n_ok = sum(1 for d in res.values() if d["ok"])
    ln = sum(math.hypot(s[1][0] - s[2][0], s[1][1] - s[2][1])
             for d in res.values() for s in d["segs"])
    return (n_ok, -ln)


def route_ripup(items, rect, net_pads, pads, cell, via_cost, tries=6, passes=4,
                blockers=8, verbose=True, width_of=None, first=(), mid_keep=(), ban_via=(),
                copper_keep=()):
    """先多次序布 ✓，再对布不通的网**拆掉挡它的线**重来 ✓（rip-up & reroute ✓）

    ★ 为什么要它 ✓（实测 2026-09-30 ✓）：9 个网只连通 3 个 ✗，而线宽 8～32 mil 全一样 ✗
      ⇒ 卡住的不是宽窄 ✓，是**先布的网把走廊占光了** ✗（贪心只看已放好的线 ✗，
      看不见后面的需要 ✗ —— 正是仓规 §5b 第 ⑩ 条「留路」的同一条病 ✓）。
    ★★ 两条铁律 ✓：
      ① **只在总分变好时接受** ✓（`(连通数, -线长)` ✓）⇒ 拆完更差就**原样退回** ✓
         （不许悄悄变差 ✗）；
      ② 每轮只拆**一张**网 ✓、拆完**必须把它重布回去** ✓ —— 否则数字好看 ✗
         但板上少了几条线 ✗（自欺 ✓）。
    """
    best = route(items, rect, net_pads, pads, cell, via_cost, verbose=verbose, tries=tries,
                 width_of=width_of, first=first, mid_keep=mid_keep, ban_via=ban_via,
                 copper_keep=copper_keep)
    best_s = _score(best)
    if verbose:
        print("   [拆线重布] 起点：连通 %d/%d ✓｜长 %.1f mm"
              % (best_s[0], len(best), -best_s[1]))

    def near_net(net, other):
        """两张网最近的一对焊盘距离 ✓（用来猜"谁挡住了我" ✓）"""
        bestd = 1e18
        for a in net_pads[net]:
            if a not in pads:
                continue
            for b in net_pads[other]:
                if b not in pads:
                    continue
                d = math.hypot(pads[a]["c"][0] - pads[b]["c"][0],
                               pads[a]["c"][1] - pads[b]["c"][1])
                bestd = min(bestd, d)
        return bestd

    for rnd in range(1, passes + 1):
        fails = sorted([n for n in best if not best[n]["ok"]], key=lambda n: len(net_pads[n]))
        if not fails:
            break
        gain = False
        for net in fails:
            cand = [n for n in best if n != net and best[n]["ok"] and best[n]["segs"]]
            for blk in sorted(cand, key=lambda n: near_net(net, n))[:blockers]:
                pre = {k: v for k, v in best.items() if k not in (net, blk)}
                trial = _route_once(items, rect, net_pads, pads, cell, via_cost,
                                    [net, blk], pre=pre, width_of=width_of,
                                    mid_keep=mid_keep, ban_via=ban_via,
                                    copper_keep=copper_keep)
                s = _score(trial)
                if s > best_s:
                    best, best_s, gain = trial, s, True
                    if verbose:
                        print("   [拆线重布] 第 %d 轮：拆《%s》⇒ 重布《%s》✓｜连通 %d/%d ✓｜长 %.1f mm"
                              % (rnd, blk, net, s[0], len(trial), -s[1]))
                    break
            if gain:
                break
        if not gain:
            if verbose:
                print("   [拆线重布] 第 %d 轮：没有一种拆法更优 ⇒ 停 ✓" % rnd)
            break
    return best


def _snap_ends(sg, pa, pb):
    r"""把首段的起点吸到 `pa` ✓、末段的终点吸到 `pb` ✓ —— ★★ 必须**保持横平竖直** ✗✓

    （2026-10-01 定案 ✓，实测真凶 ✓）
    ✗ 旧写法直接改端点 ✗ ⇒ 那一段变成**斜段** ✗（实测 **33 条** ✓，斜 0.025∼0.067 mm
      = **半个格** ✓）⇒ 写回器按“横平竖直”切缩宽区（`split_neck` ✓）时把它当竖线处理 ✗
      ⇒ **把端点搬走** ✗ ⇒ 报 **17 处「悬空端点」** ✗（独立复核也 8 处 ✗），
      而且逐点看都“有主” ✓ ⇒ 极难查 ✗。
    ✓ 现在：吸附偏移在**半个格**之内 ✓ ⇒ 用**两条正交小折线**接过去 ✓（拐点取
      `(吸附点.x, 原 y)` 或 `(原 x, 吸附点.y)` ✓）⇒ 全仓「线都横平竖直」的前提继续成立 ✓。
    """
    if not sg:
        return sg
    out = list(sg)
    # 首段：`(lay, a, b)` ⇒ 改成 `pa → 拐点 → b` ✓（拐点选得让**两段都正交** ✓）
    lay, a, b = out[0]
    if a != pa:
        hor = abs(a[1] - b[1]) < 1e-9
        corner = (pa[0], a[1]) if hor else (a[0], pa[1])
        out[0:1] = [(lay, pa, corner), (lay, corner, b)]
    # 末段：`(lay, a, b)` ⇒ 改成 `a → 拐点 → pb` ✓
    lay, a, b = out[-1]
    if b != pb:
        hor = abs(a[1] - b[1]) < 1e-9
        corner = (pb[0], b[1]) if hor else (b[0], pb[1])
        out[-1:] = [(lay, a, corner), (lay, corner, pb)]
    return [s for s in out if s[1] != s[2]]            # 零长段丢掉 ✓


def _route_once(items, rect, net_pads, pads, cell, via_cost, order, pre=None, width_of=None,
                mid_keep=(), ban_via=(), copper_keep=()):
    """按给定次序贪心布一遍 ✓ ⇒ `{net: dict(ok, segs, vias, note)}`

    `pre` = **已经布好**的 `{net: d}` ✓ —— 它们既不重布 ✓、又照旧当障碍 ✓（拆线重布用 ✓）。

    ★★ 每**段**重建栅格 ✓：**只挡别人网**的线 ✓（同网铜相碰合法 ✓；
      把自己挡死会让多脚网再也接不上剩下的脚 ✗ —— 实测 GND 1 段之后 7 段全败 ✗）。
    ★ 每段都把自己焊盘的地盘**挖回可走** ✓（`carve_pads` ✓）—— 否则 QFN 的脚距
      0.4 mm ✗、邻脚净空就把出口堵死 ✗（逐网 0 段全败 ✗）。
    ★★ 端点**吸附到焊盘中心** ✓ —— 栅格化会舍成整格（≤0.075 mm ✗），
      而最小的焊盘只有 0.2 mm ✗ ⇒ 不舍回去可能"落在盘外" ✗。
    """
    w_of = width_of or (lambda n: TRACE_MM)   # ★ 按网分宽 ✓（没给 ⇒ 用全局那一档 ✓）
    grow = U(TRACE_MM / 2 + CLEAR_MM)         # 兜底 ✓（报不出网名时用 ✓）
    zones = neck_zones(pads)                  # ★ 缩宽区 ✓（闸门要按**局部**线宽算 ✓）
    out, traces = dict(pre or {}), {}
    # ★ 把 `pre` 里已布的铜箔**原样**收进障碍表 ✓（并集要跟正常布线时一模一样 ✓，
    #   否则"拆线重布"就是在跟一个假障碍打过 ✗）
    for net2, d in (pre or {}).items():
        g2 = U(w_of(net2) / 2 + CLEAR_MM)      # ★ 预置网按**它自己**的宽度算净空 ✓
        for lay, p, q in d["segs"]:
            traces.setdefault(net2, []).append(
                (lay, (min(p[0], q[0]), min(p[1], q[1]),
                       max(p[0], q[0]), max(p[1], q[1])), g2))
        for p in d["vias"]:
            traces.setdefault(net2, []).append(
                ("both", (p[0], p[1], p[0], p[1]), U(0.45)))
    base = make_grid(rect, cell, items)
    # ★★ 「留路」✓（2026-09-30 ✓）：把"中间"那圈子算出来 —— `mid_keep` 里的网
    #   （电源/地 ✓）走它们要加罚 ✓ ⇒ 中间走廊留给后面的信号线 ✓。
    keep_cells = set()
    if mid_keep:
        cx, cy = (rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0
        i0, j0 = base.rc(cx - MID_KEEP_MM, cy - MID_KEEP_MM)
        i1, j1 = base.rc(cx + MID_KEEP_MM, cy + MID_KEEP_MM)
        for ix in range(i0, i1 + 1):
            for jy in range(j0, j1 + 1):
                x, y = base.xy(ix, jy)
                if (x - cx) ** 2 + (y - cy) ** 2 <= MID_KEEP_MM ** 2:
                    keep_cells.add((ix, jy))
    # ★ 实测记录 ✓（2026-09-30，**已回退** ✗）：这里曾加过"过孔不许落在焊盘框内"
    #   （起因：v35 的 18 个过孔里有 5 个压在焊盘上 ✓）——但实测**反而更差** ✗：
    #   过孔 18 → **28** ✗、走线 129 → **196** 条 ✗、总长 196.8 → **278.8 mm** ✗
    #   （不让它"在盘上换层" ⇒ 它绕远去换层 ✓）⇒ 已回退 ✓。
    #   要想真正降过孔，得换策略（先布长干、少换层 ✓），不是加禁令 ✗。
    # ★★ 过孔**绝对不许与元件重叠** ✓（2026-09-30 用户定，硬规矩 ✓）：
    #   把**元件本体框**（= 障碍表里带 `tag` 的那些 ✓）外扩"过孔环 + 净空" ⇒ 该范围内禁止过孔 ✓。
    #   ★ 与上次失败的"禁止压焊盘"不同 ✗：那次禁的是**焊盘框**（布线必须用的地方 ✗
    #     ⇒ 逼它绕远 ✓，过孔 18→28 ✗）；这次禁的是**元件肚子里**（本来就不许走线 ✓）
    #     ⇒ 只切掉"贴着元件边钻出来的孔" ✓，代价应该小得多 ✓（做完**量结果** ✓，变差就回退 ✗）。
    novia = set()
    for _lay, box, grow, tag in (items or ()):
        if tag is None:
            continue
        g = grow + U(VIA_CLEAR_MM)
        i0, j0 = base.rc(box[0] - g, box[1] - g)
        i1, j1 = base.rc(box[2] + g, box[3] + g)
        for ix in range(i0, i1 + 1):
            for jy in range(j0, j1 + 1):
                novia.add((ix, jy))
    # ★★ 焊盘禁落区 ✓ —— **按网**分开算 ✓（2026-10-01 修 ✗，见 `VIA_PAD_KEEPOUT_MM` ✓）：
    #   · **别的网**的盘：禁落区 = 盘框 + 铜盘半径 + 净空 ✓（= 0.45 ✓）—— 这是**硬**的 ✓
    #     （v47 就是这里出的事 ✗：孔心离盘边 0.10 mm 也能落 ✓ ⇒ 铜盘压进别人的盘 ⇒ 短路 ✗✗）。
    #   · **本网自己**的盘：**不设**禁落区 ✓ ⇒ 允许落在本网盘里（via-in-pad ✓，QFN 常见做法 ✓、
    #     同网本就不短路 ✓）—— ★ 实测：一刀全禁（不分网）时只连通 **5/9** ✗；
    #     按网分后布线器才有地方换层 ✓（本板 0.4 mm 间距 QFN ⇒ 禁止向盘内落孔等于封死扇出 ✗）。
    #   · 取整余量只给**半格** ✓；剩下的交给**精确闸门**兜底 ✓（`via_pad_conflicts` ✓ 真几何 ✓）。
    #   ★★ 2026-10-01 用户定 ✗：**同网络的 via-in-pad 也不再放行** ✗ ——
    #     原话：「我想先实现通孔不能在元件内，并与有安全距离的规则，比如 Via10 在 J1 焊盘上打孔了」✓
    #     ⇒ `keep_own` 与 `keep` **同值** ✓（下面那行 = 规则的落点 ✓）。
    #     ✗ 旧口径（同网只留 `VIA_CLEAR_MM` = 盘半径 ⇒ 允许落在自己盘里 ✗）已被用户否掉 ✗；
    #       当时写成"via-in-pad ✓ 合法 ✓"✗，理由是 QFN 扇出方便 ✗ ⇒ 现在按用户规则走 ✓。
    #     ★ 代价要认 ✓：扇出会变难 ✓ ⇒ **布不通就报出来** ✓（不许为了好看偷偷放行 ✗）。
    keep = U(VIA_PAD_KEEPOUT_MM) + 0.5 * base.cell      # ★ 一律 0.55（= 铜盘 0.30 + 规则 0.25 ✓）
    # ★ 本网的盘⇒**同一个值** ✗（2026-10-01 第二次修 ✗）：
    #   ✗ 旧值 `U(VIA_SAFE_MM)` = 0.25 是当作「**孔心**→盘边」用的 ✗ ⇒ 实际净距 = 0.25 − 0.30 = **−0.05** ✗
    #     ⇒ 同网的盘**一定被压** ✗（实测 `#3` 压 `C2.connector0` 叠 0.300 mm ✗ 就是它 ✓）。
    #   ★ `VIA_SAFE_MM` 的语义是「**铜盘边**→盘边」✓（见它的定义 ✓）⇒ 用的时候**必须加铜盘半径** ✓。
    keep_own = keep
    # ★★ EPAD / 细间距例外 ✓（2026-10-01 用户定 ✓）：「是在 EPAD 上开通孔接 GND 吗？这个必须允许」✓
    #   这两类盘上**完全不设**禁落区 ✓（允许孔落在它里面 ✓ = via-in-pad ✓）——
    #   QFN 的中央散热盘接地就是这么接 ✓、0.4 mm 间距的脚也是靠它扇出 ✓；
    #   其余盘（接插件 / 电阻 / 电容，**含同网的** ✗）一律按规则躲 ✓。
    halo, halo_own = {}, {}
    for key, q in pads.items():
        box = q.get("box")
        if not box:
            continue
        st, st2 = set(), set()
        i0, j0 = base.rc(box[0] - keep, box[1] - keep)
        i1, j1 = base.rc(box[2] + keep, box[3] + keep)
        for ix in range(i0, i1 + 1):
            for jy in range(j0, j1 + 1):
                st.add((ix, jy))
        # ★★ 本网自己的盘也同样要躲 ✗（2026-10-01 第三次修 ✗）：
        #   ✗ `keep_own` 先前**算出来但从来没被用上** ✗ —— 组网时只 OR 了「**别的网**的 `halo`」✗
        #     ⇒ 本网的盘**完全不设防** ✗ ⇒ 实测 3 处真违规**全部是同网的盘** ✓
        #     （`#3`@`C2.connector0` 叠 0.300 ✗、`#7`@`R1.connector0` 0.353 ✗、`#10`@`LED2.connector1` 0.474 ✗
        #     —— 需要 0.550 ✓）⇒ 这就是“改了禁落区、孔却纹丝不动”的原因 ✓。
        #   ★ EPAD / 细间距盘 = **例外** ✓ ⇒ `st2` 保持**空集** ✓（不设任何禁落区 ✓）。
        if q.get("epad") or q.get("fine"):
            halo[key], halo_own[key] = st, st2
            continue
        i0, j0 = base.rc(box[0] - keep_own, box[1] - keep_own)
        i1, j1 = base.rc(box[2] + keep_own, box[3] + keep_own)
        for ix in range(i0, i1 + 1):
            for jy in range(j0, j1 + 1):
                st2.add((ix, jy))
        halo[key], halo_own[key] = st, st2
    # ★ 外部点名要禁的过孔位 ✓（`ban_via` = **点** `(x, y)` ✓，单位 = 草图单位 ✓）——
    #   用于"成对过孔回收" ✓：把"下去一小段又上来"的那两个孔位禁掉再布一遍 ✓。
    for (bx, by) in ban_via or ():
        novia.add(base.rc(bx, by))
    # ★★ 元件**画出来的铜**（`copper_keep` ✓ 矩形表 ✓，含 NFC 线圈那几百条螺旋 ✓）——
    #   2026-10-01 用户定 ✗：「通孔不能在元件内，并与有安全距离」✓
    #   （校验器那边是第 ⑦ 条 ✓，**各自实现** ✓ 不许共用一份 ✗）。
    #   ✗ 旧版只按"带 `tag` 的障碍框"禁 ✓ ⇒ 线圈这类"画出来的铜"完全没管 ✗
    #     ⇒ 实测 v49 有 **7 个孔**贴着/压着线圈的铜 ✗（如 `Via15` 距 −0.006 mm ✗）。
    for box in copper_keep or ():
        g = U(VIA_CLEAR_MM + VIA_SAFE_MM)          # 铜盘半径 + 安全间隔 ✓
        i0, j0 = base.rc(box[0] - g, box[1] - g)
        i1, j1 = base.rc(box[2] + g, box[3] + g)
        for ix in range(i0, i1 + 1):
            for jy in range(j0, j1 + 1):
                novia.add((ix, jy))
    for net in order:
        if net in (pre or {}):
            continue
        mem = [(t, c) for t, c in net_pads[net] if (t, c) in pads]
        miss = ["%s.%s" % (t, c) for t, c in net_pads[net] if (t, c) not in pads]
        if len(mem) < 2:
            out[net] = dict(ok=len(mem) == 1, segs=[], vias=[],
                            note="单脚网 ✓" if mem else "无脚 ✗")
            continue
        # ★★ 每张网的**主层** ✓（2026-09-30 用户要求"图要能看懂能改" ✓）：
        #   "脚多在哪层就选哪层" ✓（平手取 copper0 ✓）⇒ A* 会尽量待在主层 ✓、
        #   只在必要时跨层 ✓ ⇒ 过孔自然变少 ✓。
        cntl = {}
        for (t, c) in mem:
            for l in pads[(t, c)]["lays"]:
                cntl[l] = cntl.get(l, 0) + 1
        pref = "copper1" if cntl.get("copper1", 0) > cntl.get("copper0", 0) else "copper0"
        other = "copper1" if pref == "copper0" else "copper0"
        linked, todo = [mem[0]], list(mem[1:])
        segs, vias, fails = [], [], 0
        # ★★ 这张网的**禁落孔集合** ✓ = 元件体禁落区 ✓ ∪ **所有焊盘**的禁落区 ✓：
        #   · 别的网 ⇒ 用 `halo` ✓（⚠ 0.55 ✓）；
        #   · **本网自己** ⇒ 用 `halo_own` ✓（同样是 0.55 ✓，**除了** EPAD/细间距 ⇒ 空集 ✓）。
        #   ✗ 2026-10-01 第三次修 ✓：原来本网只写“不设禁落区”✗ ⇒ 3 处真违规全是本网盘被压 ✓。
        mykeys = set(mem)
        no_via = set(novia)
        for k2, st2 in halo.items():
            no_via |= (halo_own[k2] if k2 in mykeys else st2)
        # ★★ 这张网**自己的**净空 ✓（按网分宽 ✓）—— 宽网要多占地方 ✓、细网不必陪跑 ✗。
        grow = U(w_of(net) / 2 + CLEAR_MM)
        # ★★ 细间距区：只按**缩宽后**的净空挖盘 ✓（否则粗线能借“挖盘”穿过别人盘 ✗，
        #   见 `carve_pads` 的注释 ✓ —— 实测就是 `GND`↔`PA2` 短路的机制 ✓）
        neck_grow = U(min(w_of(net), NECK_W_MM) / 2 + CLEAR_MM)
        while todo:
            best = None
            for a in linked:
                for b in todo:
                    d = math.hypot(pads[a]["c"][0] - pads[b]["c"][0],
                                   pads[a]["c"][1] - pads[b]["c"][1])
                    if best is None or d < best[0]:
                        best = (d, a, b)
            _d, a, b = best
            # ★★ 每段重建栅格：**只挡别人网**的线 ✓ —— 同网铜相碰是合法的 ✓，
            #    而"把自己挡死"会让多脚网再也接不上剩下的脚 ✗（实测：GND 1 段之后 7 段全败 ✗）。
            grid = base.clone()
            # ★★ 按**自己的线宽**多留余量 ✓（2026-10-01 用户定 ✓，实测根因 ✓）：
            #   ✗ 障碍表（焊盘 / 件铜 / 安装孔 / 板边 ✓）的净空是按**信号档**（`TRACE_MM` = 12 mil
            #     ⇒ 半宽 0.152 ✓）算的 ✗ ⇒ **粗电源线**（24 mil ⇒ 半宽 **0.305** ✓）照那样走 ⇒
            #     铜**外溢 0.153 mm** ✗ ⇒ 独立复核报「④ 同层交叉 4 处」✗ + 「⑤ 粘上了别的脚」✗
            #     （`DATA_IN` / `GND` 粘一堆 ✓）。和「`VSS` 差 0.005 mm」是同一类算术坑 ✓。
            #   ✓ 现在：把障碍**再挡一圈** = `(自己的半宽 − 信号半宽)` ✓ —— 物理上就是
            #     “宽线离障碍更远” ✓。
            #   ★ **跳掉紧间隙盘** ✗（`grow` 已经是缩宽档的那些 ✓）：那些地方线会缩到 10 mil ✓
            #     ⇒ 不能再按粗线挡 ✗（否则一格可走的都没有 ⇒ 实测掉到 **0/9** ✗，前车之鉴 ✓）。
            extra = U(max(0.0, w_of(net) / 2.0 - TRACE_MM / 2.0))
            if extra > 1e-9:
                neck_g = U(NECK_W_MM / 2 + CLEAR_MM)
                for (lay, box, grow0, _tag) in items:
                    if abs(grow0 - neck_g) < 1e-9:
                        continue
                    for l2 in (LAYERS if lay == "both" else (lay,)):
                        grid.block_box(l2, box, grow0 + extra)
                grid.block_frame(U(EDGE_MM) + U(w_of(net) / 2 + CLEAR_MM))
            for net2, tlist in traces.items():
                if net2 == net:
                    continue
                for lay, box, gr in tlist:
                    for l2 in (LAYERS if lay == "both" else (lay,)):
                        grid.block_box(l2, box, gr)
            carve_pads(grid, pads, mem, grow, neck_grow)
            # ★★ 挖完自己的盘之后，把**别人的盘框本身**重新挡住 ✗✓（2026-10-01 ✓）
            #   为什么需要 ✗（实测 ✓）：`carve_pads` 为让线进自己的盘会挖 0.277 mm ✓，
            #   而 QFN 脚距只有 0.400 mm ✓ ⇒ 挖开区**盖住隔壁盘框的一角** ✗
            #   ⇒ 栅格以为能走 ✓ ⇒ 实测 `网 GND（EPAD→VSS）` 的线在 y=16.922 横穿 `PA2` 的盘框 ✗
            #     （`_work/repro_clash.py` 量过 ✓：与 PA2 的框 x 交 **+0.377 mm**、y 交 **+0.177 mm** ✓
            #      ⇒ **真压盘** ✗，不是误判 ✓）⇒ 直接短路 ✗。
            #   ★ 只挡**盘框本身**（`grow=0` ✓、不加肥 ✓）：线仍可从盘**外侧的净空**里绕 ✓
            #     ⇒ 不会把细间距件的出口堵死 ✓（对比：按净空挡会 ⇒ 实测 0/9 ✗）。
            for k2, q2 in pads.items():
                if k2 in mykeys:
                    continue
                bb = q2.get("box")
                if not bb:
                    continue
                # ★★ 只挡**盘框本身**（`grow=0` ✓）—— 试过「按净空挡」✗、**更差** ✗：
                #   2026-10-01 实测 ✓：按 `半宽 + 净空` 挡（紧间隙盘按缩宽后的半宽 ✓ 也不行 ✗）
                #     ⇒ 连通 **3/9 → 0/9** ✗、问题 6 → **10 处** ✗，还多出一处 GND↔RC 短路 ✗。
                #   ⇒ 维持 `grow=0` ✓（用户 2026-10-01 选定的“零短路”配置 ✓）；
                #     要再往前走，得从**摆位/拓扑**下手 ✓（≠ 调这个系数 ✗）。
                for l2 in q2["lays"]:
                    grid.block_box(l2, bb, 0.0)
            path = None
            for la in pads[a]["lays"]:
                # ★ 本网**已用几颗过孔** ⇒ 下一颗贵多少 ✓（递增 ✓，见 `VIA_ESCALATE` ✓）
                vc = via_cost * (1.0 + VIA_ESCALATE * len(vias))
                path = astar(grid, la, pads[a]["c"],
                             [(lb, pads[b]["c"]) for lb in pads[b]["lays"]], vc,
                             avoid=keep_cells if net in tuple(mid_keep) else None,
                             avoid_w=MID_KEEP_W, no_via=no_via,
                             turn=TURN_COST, pen_layer=other, pen=LAYER_PEN)
                if path:
                    break
            if not path:
                fails += 1
                if DIAG["on"]:
                    for la in pads[a]["lays"]:
                        reach = flood(grid, la, pads[a]["c"], no_via)
                        hit = [lb for lb in pads[b]["lays"]
                               if (lb, grid.rc(*pads[b]["c"])) in reach]
                        DIAG["fails"].append(
                            "网 %s：%s.%s → %s.%s｜起点层 %s ⇒ 可达 %d 格 ✓｜"
                            "目标%s"
                            % (net, a[0], a[1], b[0], b[1], la, len(reach),
                               ("**可达** ⇒ A* 的问题（上限/代价）✗" if hit
                                else "**不可达** ⇒ 障碍模型堵死了 ✗")))
                todo.remove(b)
                continue
            sg, vs = path_to_segments(path, grid)
            # ★★ 吸附前先验**层** ✗（2026-09-30 补 ✓，就是那三处悬空端点的病因 ✓）：
            #   ✗ 旧版无条件把段的两端吸到焊盘中心 ✗ ⇒ 段在 copper1、盘在 copper0 时，
            #     端点**正好落在盘心**✗ ⇒ 写回器以为接上了（其实是错的 ✗），或报一个
            #     "差 0.000 mm 却接不上"的怪悬空 ✗（两种都是自欺 ✓）。
            #   ⇒ 现在：层对不上就**记失败** ✓（宁可不通、不许假装通 ✓）。
            if sg and (sg[0][0] not in pads[a]["lays"] or sg[-1][0] not in pads[b]["lays"]):
                fails += 1
                todo.remove(b)
                continue
            if sg:
                # ★★ 吸附到两个盘心 ✓ —— 用 `_snap_ends` ✓（**保持横平竖直** ✗✓，2026-10-01 ✓）
                sg = _snap_ends(sg, pads[a]["c"], pads[b]["c"])
                # ★★★ 闸门 ✓：线身/折线段**不许压「别的网」的盘框** ✗（2026-10-01 装回 ✓）
                #   ★ 曾撤过一次、现装回 ✓ —— 撤的理由是“误判太多”✗，而 `_work/repro_clash.py`
                #     复现下来 **闸门是对的** ✓：真正压盘的是 `y=16.922` 那根 ✓
                #     （与 `PA2` 的框 x 交 **+0.377 mm** ✓、y 交 **+0.177 mm** ✓ —— 就是那条短路 ✓）；
                #     当时是我把“哪根线”记混了 ✗（mm 与内部单位混着看 ✓）。
                #   ★ 配套：栅格已把**别人的盘框**挡住（上面那段 ✓）⇒ 正常路线不该命中 ✓；
                #     命中即“这段真会压盘”✗ ⇒ 记失败、换走法 ✗。
                _half = grow - U(CLEAR_MM)                 # = 本网线宽的一半 ✓
                _half_neck = U(NECK_W_MM / 2)              # = 缩宽区内那一半 ✓（10 mil ✓）
                _clash = None
                for (lay2, p2, q2) in sg:
                    _mx, _my = (p2[0] + q2[0]) / 2.0, (p2[1] + q2[1]) / 2.0
                    hw = _half_neck if in_neck(_mx, _my, zones) else _half
                    bx = (min(p2[0], q2[0]) - hw, min(p2[1], q2[1]) - hw,
                          max(p2[0], q2[0]) + hw, max(p2[1], q2[1]) + hw)
                    for k2, q in pads.items():
                        if k2 in mykeys:
                            continue
                        bb = q.get("box")
                        if not bb:
                            continue
                        if bx[0] <= bb[2] and bb[0] <= bx[2] and \
                                bx[1] <= bb[3] and bb[1] <= bx[3]:
                            _clash = (lay2, p2, q2, k2)
                            break
                    if _clash:
                        break
                if _clash and DIAG["on"]:
                    # ✗ 别用 `MM(...)` ✗ —— 那是 `gen_routes` 的函数 ✓，本模块没有 ⇒ 会 NameError 崩掉 ✓
                    #   （实测踩过 ✓）；本模块用 `U()` 作 mm↔单位 的换算 ✓ ⇒ 反算 = `值 / U(1.0)` ✓。
                    DIAG["fails"].append(
                        "net %s: %s.%s -> %s.%s | CLASH pad %s.%s | line (%.3f,%.3f)-(%.3f,%.3f)"
                        % (net, a[0], a[1], b[0], b[1], _clash[3][0], _clash[3][1],
                           _clash[1][0] / U(1.0), _clash[1][1] / U(1.0),
                           _clash[2][0] / U(1.0), _clash[2][1] / U(1.0)))
                if _clash:
                    fails += 1
                    todo.remove(b)
                    continue
            # ★★ 2026-10-01：“不许压焊盘”**试过两版、都撤了** ✗ —— 不再往这里加补偿改动 ✗：
            #   ① 先试“吸附 ⇒ 压了就改成不吸附” ✗：端点差**半个格**（0.071 mm ✗）⇒
            #      写回器“端↔端/端↔盘必须正中”的判据对不上 ✗ ⇒ 报 6 个悬空端点 ✗ ⇒ **文件写不出** ✗；
            #   ② 再试“永远吸附 + 被压的盘加硬禁位重布（避不开就保底留吸附版）” ✗：
            #      仍报 2 个悬空端点 ✗（其中一处是: 端点正好落在 `D3.connector4` 盘心 0.000 mm
            #      却“谁也没接上” ✗）⇒ **文件还是不写** ✗。
            #   ⇒ 结论（待办 ✗）：要改得先解决两件事 ——
            #      (a) **写回器的“端必须正中”判据** vs **布线器端点落在栅格上** 这对矛盾 ✗；
            #      (b) “真压了盘”的**证据本身** ✗：我那 5 处是从**导出 svg** 里按
            #          `partID = modelIndex + 层号` **前缀匹配**认出来的 ✗ ⇒
            #          8/9 位 modelIndex 会**前缀碰撞** ✗（`9001317`+`5` vs `90013175` ✓）⇒
            #          可能认错了线 ✗ ⇒ **先在自家几何上用无碰撞的对应关系复测** ✓ 再谈改 ✗。
            #   判据函数 `pads_covered`/`seg_hits_rect` **保留** ✓（供**独立核对**脚本用 ✓，
            #   布线期不用 ✗）—— “一份实现、两处调用” ✓。
            segs += sg
            vias += vs
            for lay, p, q in sg:
                traces.setdefault(net, []).append(
                    (lay, (min(p[0], q[0]), min(p[1], q[1]),
                           max(p[0], q[0]), max(p[1], q[1])), grow))
            for p in vs:
                traces.setdefault(net, []).append(
                    ("both", (p[0], p[1], p[0], p[1]), U(0.45)))
            linked.append(b)
            todo.remove(b)
        note = "" if not fails else "有 %d 段没连上 ✗" % fails
        if miss:
            note = (note + "；网表里的 %s 在板上找不到 ✗" % ",".join(miss)).strip("；")
        out[net] = dict(ok=not fails, segs=segs, vias=vias, note=note)
    return out


def resolve_nets(model, nets):
    """网表 `{网: [(位号, 脚名)]}` ⇒ `{(位号, connectorN)}` ✓（**唯一实现** ✓）

    ★ 为什么要抽出来 ✓：写回器也要把网表变成 `(位号, connectorN)` ✓ ——
      两头各写一份 ⇒ 一处改了另一处不跟 ✗（第 §5 「一份实现」纪律 ✓）。
    """
    byttl = {}
    for p in model.get("parts", []):
        if p.get("fzp") is not None and "title" in p:
            byttl[p["title"]] = (p.get("names") or {}, set(p.get("connectors") or []))
    net_pads, unresolved = {}, []
    for net, lst in nets.items():
        got = []
        for t, nm in lst:
            names, cids = byttl.get(t, ({}, set()))
            cid = PP.cid_of(names, cids, nm)
            if cid is None:
                unresolved.append("%s.%s（网 %s）" % (t, nm, net))
                continue
            got.append((t, cid))
        net_pads[net] = got
    return net_pads, unresolved


def via_pad_conflicts(vias, pads, net_of_pad, keep_mm=VIA_PAD_KEEPOUT_MM):
    """⇒ `[(网, (x,y), 位号, cid, 距边 mm, 需要 mm), …]` ✓（空 = 全过 ✓）
    `vias` = `[(网, (x, y)), …]` ✓；`pads` = `{(位号, cid): dict(box=…)}` ✓

    ★ 这是**生成器的硬闸门** ✓：非空就**不许写文件** ✗（与"悬空端点必须 0"同级 ✓）。
    ★ 与校验器 `pcb_check` 的第 ⑥ 条**各自实现** ✓（不许自证 ✗）：
      那边按“**铜盘与盘框重叠**”判 ✗（严格 0 重叠 ✓）；这边按“**净空够不够**”判 ✓。
      ★★ 2026-10-01 二次修 ✗：两边**都按规则值 0.25 mm** ✓ —— 这边比的是
        「**孔心**→盘框 ≥ `keep_mm` = 0.55 ✓（= 铜盘半径 0.30 + 0.25 ✓）」✓；
        ✗ 旧口径按同网/异网分 0.25 / 0.45 ✗ ⇒ **同网少了铜盘半径** ✗ ⇒ 实测 `#3`/#7/#10 漏过去 ✓。
    """
    bad = []
    for net, (x, y) in vias:
        for (ttl, cid), q in pads.items():
            b = q.get("box")
            if not b:
                continue
            dx = max(b[0] - x, 0.0, x - b[2])
            dy = max(b[1] - y, 0.0, y - b[3])
            d = MM((dx * dx + dy * dy) ** 0.5)
            # ★ 同网的盘：只要**铜盘不伸出到别人头上**就合法 ✓ ⇒ 这里只要求"不叠"（≥ 0.30 ✓）；
            #   真正确保邻盘安全的是**别的网那一条**（≥ 0.45 ✓）⇒ 短路仍然抓得住 ✓。
            # ★★ 同网的盘：**压上去也合法** ✓（via-in-pad ✓，同网铜相接 ✓，电气不断路 ✓）
            #   ⇒ 判据是 **0**（不管）；真正要守的是**别的网那条 0.45** ✓ —— 短路仍然抓得住 ✓
            #   （从 0.30 改成 0.0 的依据 ✗：本板实测 ✓ 一刀禁本网盘 ⇒ 只剩 8/9 ✗；
            #     允许本网盘内落孔 ⇒ 9/9 ✓ 且**异网零重叠** ✓ —— 拿 `pcb_check` ⑥ 复核过 ✓）。
            # ★★★ 2026-10-01 用户规则 ✓：**同网的盘要 0.25 mm** ✗（不许 via-in-pad ✗）——
            #   ✗ 旧口径写的是 `need = 0.0 if 同网 else 0.45` ✗（把同网盘当“随便压”✗）。
            #   ★★ 但 **EPAD 是例外** ✓（2026-10-01 用户定 ✓）：「在 EPAD 上开通孔接 GND……必须允许」✓
            #     ⇒ 同网 + EPAD ⇒ `need = 0.0` ✓（允许孔落在 EPAD 里 ✓）；其余同网盘仍需 0.25 ✓。
            # ★★ 例外（同网 + EPAD / 细间距盘 ✓）⇒ `need = 0.0` ✓（允许孔落在它里面 ✓）；
            #   其余的盘**一律** `VID_PAD_KEEPOUT_MM` = 0.55 ✓ —— 即「**孔心**→盘边 ≥ 铜盘半径 0.30
            #   + 规则 0.25」✓（✗ 旧口径按同网/异网分 0.25 / 0.45 ✗ ⇒ 同网少了铜盘半径
            #     ⇒ 实测 `#7`（离 `R1` 盘边 0.053 mm ✗）、`#10`（0.150 ✗）就是这么漏过去的 ✓）。
            if net_of_pad.get((ttl, cid)) == net and (q.get("epad") or q.get("fine")):
                need = 0.0
            else:
                need = keep_mm
            if d < need - 1e-9:
                bad.append((net, (x, y), ttl, cid, d, need))
    return bad


def opt(argv, name, default=None, cast=str):
    """取命令行选项 ✓ —— **两种写法都认**：`--x=1` ✓ 与 `--x 1` ✓。

    ✗ 教训（2026-09-30 ✓）：原来只写 `"--via" in argv` ✗ ⇒ 我传 `--via=40` ✗
      ⇒ 选项**被静默忽略** ✗ ⇒ 跑出的结果与没传时**一模一样** ✗，
      而我还把"数字没变"当成"参数无效" ✗ ⇒ 差点当场下错结论 ✗。
    """
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return cast(argv[i + 1])
        if a.startswith(name + "="):
            return cast(a.split("=", 1)[1])
    return default


def main(argv):
    netsf, rest = projdata.strip_argv(argv)
    if not rest:
        print(__doc__)
        return 2
    fzz = rest[0]
    data = projdata.load(netsf, need=("NETS",))
    cell = opt(argv, "--cell", CELL_MM, float)
    via_cost = opt(argv, "--via", K_VIA, float)
    tries = opt(argv, "--tries", 6, int)
    passes = opt(argv, "--passes", 4, int)
    mil = opt(argv, "--mil", TRACE_MIL, int)
    if mil not in MIL_TIERS:
        raise SystemExit("✗ 线宽只能是这几档 ✓（Fritzing 的宽度下拉 ✓）：%s（mil ✓）"
                         % "、".join("%s %d" % (MIL_TIERS[k], k) for k in sorted(MIL_TIERS)))
    global TRACE_MM
    TRACE_MM = mil * MIL_MM
    model = PC.collect(fzz)
    r = model["board"]
    pads = pad_index(model)
    # ★ 先把网表**解析成 (位号, connectorN)** ✓ 再建障碍 ✓（障碍要按网打标签 ✓）
    net_pads, unresolved = resolve_nets(model, data.NETS)
    model["net_pads"] = net_pads
    print("== 布线（**只算不写** ✓）：%s ==" % os.path.basename(fzz))
    print("   板 %.2f×%.2f mm｜栅格 %.2f mm｜线宽 %s %d mil（%.4f mm ✓）｜净空 %.2f｜过孔折 %.0f 格"
          % (MM(r[2] - r[0]), MM(r[3] - r[1]), cell, MIL_TIERS[mil], mil, TRACE_MM,
             CLEAR_MM, via_cost))
    items, st = obstacles(model)
    g0 = make_grid(r, cell, items)
    tot = g0.nx * g0.ny
    for lay in LAYERS:
        print("   %s：可走 %d / %d 格（%.1f%% ✓）｜障碍：焊盘 %d ＋ 件铜箔 %d 条"
              % (lay, sum(g0.g[lay]), tot, 100.0 * sum(g0.g[lay]) / tot,
                 st["pads"], st["copper"]))
    if unresolved:
        print("   ✗ 脚名解析不了：%s" % ", ".join(unresolved))

    res = route_ripup(items, r, net_pads, pads, cell, via_cost, tries=tries, passes=passes)
    print("\n== 逐网 ==")
    tot_len = tot_via = 0.0
    n_ok = 0
    for net in sorted(res, key=lambda n: -len(net_pads[n])):
        d = res[net]
        ln = sum(math.hypot(s[1][0] - s[2][0], s[1][1] - s[2][1]) for s in d["segs"])
        tot_len += ln
        tot_via += len(d["vias"])
        n_ok += 1 if d["ok"] else 0
        print("   %-9s 脚 %d｜%s｜段 %2d｜长 %6.2f mm｜过孔 %d %s"
              % (net, len(net_pads[net]), "✓" if d["ok"] else "✗", len(d["segs"]),
                 MM(ln), len(d["vias"]), d["note"]))
    print("\n   合计：**%d/%d 个网连通** ✓｜线长 **%.1f mm**｜过孔 **%d** 个"
          % (n_ok, len(res), MM(tot_len), int(tot_via)))
    return 0 if n_ok == len(res) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
