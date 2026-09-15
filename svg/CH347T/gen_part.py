#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — CH347T 高速 USB 转 SPI/I2C/JTAG/UART 芯片（WCH）Fritzing 元件生成器。
================================================================================
元件形态（用户 2026-09-14 定）：
  - **芯片**（CH347T）出 icon / 原理图 / PCB 三个视图；
  - **面板上用的那块官方评估板 CH347T-EVT-R0-1v1** 只出现在**面包板视图**，
    板上排针**全部做成可连线 connector**（按信号名映射到芯片脚；同网用 <buses> 互联）。

资料（都在本机，不是猜的）：
  · `D:\Downloads\CH347DS1.PDF`（CH347 手册 V1.5）：
      - 封装：**TSSOP20，塑体 4.4×6.5mm，引脚节距 0.65mm**；CH347F = QFN28 4×4mm / 0.4mm；
      - 第 3 页引脚排列图（TOP VIEW，本脚本 PIN_NAMES 的来源）：
          左侧 上→下 = 1..10；右侧 下→上 = 11..20；
          1 RST# | 2 CTS1/GPIO6 | 3 TXD1 | 4 RXD1 | 5 DSR0/GPIO2/SCS0/TMS |
          6 CTS0/GPIO0/SCK/TCK | 7 RTS0/GPIO1/MISO/TDO | 8 TXD0/MOSI/TDI |
          9 TNOW0/DTR0/GPIO5/SCS1/TRST | 10 TNOW1/DTR1 |
          11 RI0/GPIO3/SCL | 12 RXD0/SDA | 13 RTS1/GPIO7 | 14 VCC | 15 DCD0/GPIO4/ACT |
          16 UD- | 17 UD+ | 18 GND | 19 XI | 20 XO
      - CH347T 靠 **CFG0/CFG1 引脚上电时的电平** 选工作模式：
          0 = 双 UART；1 = 单 UART(VCP)+SPI+I2C；2 = 单 UART(HID)+SPI+I2C；3 = 单 UART+JTAG/SWD
  · `D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf`（评估板说明 V1.5）：
      第 2/3/5 页的板级单元表 + 第 3/4 页的 **P9–P14 功能脚配置表**；第 2 页有实物照片。
  · `D:\Downloads\CH347EVT\EVT\PCB\CH347SCH.pdf` 第 2 页：CH347T 评估板原理图（网名来源）。

面包板视图的几何**不在这里**（与 svg/CH347F 一样分成三个文件）：
  ① 用户在 Inkscape 里拿实物照片当底手工对齐 → `svg.breadboard.CH347T_breadboard_byHand.svg`
     （带照片的草稿，已在 .gitignore 里）；
  ② `tools/byhand_export.py svg\CH347T` → **`byHand_tables.py`**（纯数据，入库）；
  ③ 本文件只负责**照着表出图**。以后挪排针 = 改手工版重跑 ②，不要在本文件里改坐标。

进度（按 fritzing-parts-langhua AGENTS.md §2 芯片类工作流）：
  [x] 1. icon（TSSOP20 顶视图：黑体 4.4×6.5 + 两侧金脚 + pin1 圆点）
  [x] 2. breadboard（= CH347T-EVT-R0-1v1 整块评估板）
  [x] 3. schematic（矩形 20 脚符号：左 1..10 / 右 20..11）
  [x] 4. pcb（TSSOP20 4.4×6.5 P0.65，含脚总宽 6.4）
  [x] 5. part.CH347T.fzp + 打包 fzpz
"""
import os
import re
import zipfile

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PART_ID = "CH347T"
TITLE = "CH347T (USB to SPI/I2C/JTAG/UART, TSSOP20)"
LABEL = "U"
PACKAGE = "TSSOP20"
FAMILY = "WCH USB Bridge"
FZPZ = "CH347T.fzpz"
ICON_SVG = "svg.icon.%s_icon.svg" % PART_ID
BB_SVG = "svg.breadboard.%s_breadboard.svg" % PART_ID
SCHEM_SVG = "svg.schematic.%s_schematic.svg" % PART_ID
PCB_SVG = "svg.pcb.%s_pcb.svg" % PART_ID
FZP = "part.%s.fzp" % PART_ID

# 颜色（与仓库其它芯片 icon 一致）
BODY = "#303030"
PAD = "#f7bf13"
MARK = "#c0c0c0"
TXT = "#c0c0c0"

# ---- icon 几何（mm，1:1 实物）------------------------------------------------
BODY_W = 4.4          # 塑体宽（引脚在左右两侧伸出）
BODY_H = 6.5          # 塑体高
LEAD_L = 1.0          # 引脚伸出长度（用户 2026-09-14：0.25 x 1mm）
LEAD_W = 0.25         # 引脚宽
PITCH = 0.65          # 节距
N_PER_SIDE = 10       # 每侧 10 脚
TOT_W = BODY_W + 2 * LEAD_L
TOT_H = BODY_H

# 引脚名（datasheet 第 3 页排列图）—— **面包板的网名/connector 号也按它算**（见 pad_map）
PIN_NAMES = {
    1: "RST#", 2: "CTS1/GPIO6", 3: "TXD1", 4: "RXD1", 5: "DSR0/GPIO2/SCS0/TMS",
    6: "CTS0/GPIO0/SCK/TCK", 7: "RTS0/GPIO1/MISO/TDO", 8: "TXD0/MOSI/TDI",
    9: "TNOW0/DTR0/GPIO5/SCS1/TRST", 10: "TNOW1/DTR1",
    11: "RI0/GPIO3/SCL", 12: "RXD0/SDA", 13: "RTS1/GPIO7", 14: "VCC",
    15: "DCD0/GPIO4/ACT", 16: "UD-", 17: "UD+", 18: "GND", 19: "XI", 20: "XO",
}

# 板上额外网络：**没有对应芯片脚号**（CFG0/CFG1 是模式脚，CH347 手册第 3 页的 20 脚表里
# 没有单列；GND/KEY 是按键扫描线，不是地）→ 一律发板级号，且**不许按 "/" 拆开去猜**
# （拆开 "GND/KEY" 会拆出 "GND" 而误并到地上 —— CH347F 上踩过的同类坑）。
BOARD_NETS = {"CFG0", "CFG1", "GND/KEY"}

# =============================================================================
# 板上网络（用户 2026-09-16 定，两条规则）
#
# ① **名字用板上丝印**（不是芯片脚名）：P4 = `CS0/CS1/SCK/MISO/MOSI`、
#    P5 右列 = `TMS/TCK/TDO/TDI/TRST`、P3 = `SCL/SDA`、P7 = UART0 那几个线名 …
# ② **只有名字完全一致的焊盘才共一条总线**（不做"别名/近似"合并）——
#    所以"哪两个脚同网"完全由名字决定，名字写对就对了。
#
# 出处 = `CH347SCH.pdf` 第 2 页各排针块的网名 + 手工版底图上的丝印：
#   P3 I2C : 1=3V3 2=GND 3=SCL 4=SDA                P4 SPI : 1=3V3 2=GND 3=CS0 4=CS1
#                                                            5=SCK 6=MISO 7=MOSI
#   P7 UART0: 1=3V3 2=GND 3=RXD0 4=TXD0 5=RTS0/GP1 6=CTS0/GP0
#             7=DTR0/GP5 8=DSR0/GP2 9=RI0/GP3 10=DCD0/GP4
#   P8 UART1: 1=3V3 2=GND 3=RXD1 4=TXD1 5=RTS1/GP7 6=CTS1/GP6 7=DTR1
#   P5 JTAG : 左列 1=3V3 3=GND 5=GND 7=GND/KEY 9=GND；右列 = TMS/TCK/TDO/TDI/TRST
#   P6 CFG  : 上=3V3 中=GND/KEY（连 P5 的 pin7）下=GND
#   P9–P14  : 3 焊点焊接跳线，见 `_JUMPERS`
# =============================================================================
# 板上 3V3 轨在本表里仍叫 **VCC**：它就是芯片 14 脚（直接相连、同名共总线），
# 改成 "3V3" 反而会把它和芯片脚拆开（这一条我按"同名才同网"倒推的，报告里写了）。
_PAD_RENAME = [                                  # (列 x, 行 y, 板上丝印名)
    (181.6, 177.6, "SDA"), (181.6, 277.6, "SCL"),                    # P3 = I2C 头
    (1764.2, 362.2, "CS0"), (1764.2, 462.2, "CS1"),                  # P4 = SPI 头
    (1764.2, 562.2, "SCK"), (1764.2, 662.2, "MISO"), (1764.2, 762.2, "MOSI"),
    (1775.2, 1093.2, "TMS"), (1775.2, 1193.2, "TCK"),                # P5 右列 = JTAG
    (1775.2, 1293.2, "TDO"), (1775.2, 1393.2, "TDI"), (1775.2, 1493.2, "TRST"),
    # P7 = UART0 头：**板上丝印就是缩写**（手工版里的 <text> 写的是 RXD/TXD/RTS…）
    (190.9, 992.5, "RXD"), (190.9, 1092.5, "TXD"),
    (190.9, 1192.5, "RTS"), (190.9, 1292.5, "CTS"),
    (190.9, 1392.5, "DTR"), (190.9, 1492.5, "DSR"),
    (190.9, 1592.5, "RI"), (190.9, 1692.5, "DCD"),
    # P8 = UART1 头（丝印同样带 1：RXD1/TXD1/RTS1…）
    (290.9, 1292.0, "RXD1"), (290.9, 1392.0, "TXD1"), (290.9, 1492.0, "RTS1"),
    (290.9, 1592.0, "CTS1"), (290.9, 1692.0, "DTR1"),
    # P6（3 脚）：手工版里被 Ctrl+D 复制成同名 GND/KEY ×3 → 按**丝印**写回（丝印就是 3V3）
    (1453.0, 1293.6, "3V3"), (1453.0, 1393.6, "GND/KEY"), (1453.0, 1493.9, "GND"),
    (1675.2, 1393.2, "GND/KEY"),          # P5 左列第 4 脚（= pin7，与 P6 中脚同一根线）
]

# 板上 3V3 轨：手工版里 pad 元素的 connectorname 写的是 `VCC`（Ctrl+D 拄来的芯片脚名），
# 但**丝印是 `3V3`** → 按规则以丝印为准改名；它仍然是芯片 14 脚那条线（`BUSES` 里显式并）。
_RENAME_BY_NAME = {"VCC": "3V3"}

# P9–P14 = **3 焊点焊接跳线**（"IO SWITCH" 区，手册第 4 页的四）—— 每个脚各接一条线：
#   上脚 = UART0 侧那条线   → 与 P7 的同名脚共总线（丝印写法不同时用 `_LINE_TIES` 显式并）
#   中脚 = **芯片脚本身**   → 名字用**丝印上的组合名**（如 `RTS0/MISO/TDO`），
#                             connector 号 = 该芯片脚（显式指定，面包板上代表该脚的就是它）
#   下脚 = SPI/I2C 侧那条线 → 与 P4/P3 的同名脚共总线
# 三个名字都照**板上丝印/手册里那张表的写法**（用户 2026-09-16：以丝印名为准）。
_JUMPERS = [                    # (列 x, 芯片脚号, 上脚名, 中脚名, 下脚名, 排针名)
    (676.4, 12, "RXD0", "RXD0/SDA", "SDA", "P14"),
    (800.0, 11, "RI0/GP3", "RI0/SCL", "SCL", "P13"),
    (923.6, 8, "TXD0", "TXD0/MOSI/TDI", "MOSI", "P12"),
    (1047.2, 7, "RTS0/GP1", "RTS0/MISO/TDO", "MISO", "P10"),
    (1174.0, 6, "CTS0/GP0", "CTS0/SCK/TCK", "SCK", "P11"),
    (1294.5, 5, "DSR0/GP2", "DSR0/CS0/TMS", "CS0", "P9"),
]

# **同一根线、但板上两处丝印写法不同**（P7 写你缩写、跳线区写全名）→ 得显式并成一条总线。
# 名字写对就自动成线；这两处丝印实在对不上，只能点出来（列表本身也是给人校对的）。
_LINE_TIES = [                  # (总线名, [(列 x, 行 y), …])
    ("RXD0", [(190.9, 992.5), (676.4, 799.2)]),        # P7 的 RXD ↔ P14 上脚 RXD0
    ("TXD0", [(190.9, 1092.5), (923.6, 799.2)]),       # P7 的 TXD ↔ P12 上脚 TXD0
    ("RTS0/GP1", [(190.9, 1192.5), (1047.2, 799.2)]),  # P7 的 RTS ↔ P10 上脚 RTS0/GP1
    ("CTS0/GP0", [(190.9, 1292.5), (1174.0, 799.2)]),  # P7 的 CTS ↔ P11 上脚 CTS0/GP0
    ("DSR0/GP2", [(190.9, 1492.5), (1294.5, 799.2)]),  # P7 的 DSR ↔ P9 上脚 DSR0/GP2
    ("RI0/GP3", [(190.9, 1592.5), (800.0, 799.2)]),     # P7 的 RI  ↔ P13 上脚 RI0/GP3
]
_NET_TOL = 3.0                            # 内部单位（100 = 2.54mm）→ 3 ≈ 0.076mm


def jumper_zone():
    """P9–P14 那 18 个跳线焊盘的范围（内部单位 x0, y0, x1, y1）—— 从 `_JUMPERS` 算。"""
    xs = [x for x, *_r in _JUMPERS]
    return min(xs) - 60, 750.0, max(xs) + 60, 1050.0


def is_config_pad(x, y):
    """P9–P14 焊接跳线的焊盘（每个脚各接一条线，见 `_JUMPERS`）"""
    x0, y0, x1, y1 = jumper_zone()
    return x0 <= x <= x1 and y0 <= y <= y1


def _one_pad(cols, kx, ky, why):
    """按 (列 x, 行 y) 找**唯一**那个焊盘；配不上/找到多个就报错。"""
    hit = [(x, y) for x, ys in cols.items() for (y, _n) in ys
           if abs(x - kx) <= _NET_TOL and abs(y - ky) <= _NET_TOL]
    if len(hit) != 1:
        raise SystemExit("%s (%s, %s) 对上了 %d 个焊盘：%s" % (why, kx, ky, len(hit), hit))
    return hit[0]


def _row_names(cols):
    """→ {(x, y): 名字}：手工版里的原名字 + 用户核过的修正（`_PAD_RENAME` / `_JUMPERS`）。

    `cols` = {列 x: [(y, 原名字), …]}。名字一律取**板上丝印的写法**（用户 2026-09-16：
    "手工修改的板，以丝印名为准" —— 丝印人眼可校对，藏在 svg 源码里的名字人看不见）。
    **配不上就报错** —— 静默失效会让总线悄悄连错（CH347F 上踩过：键是浮点算出来的 x）。
    """
    fixed = {}
    for kx, ky, net in _PAD_RENAME:
        fixed[_one_pad(cols, kx, ky, "_PAD_RENAME")] = net
    for kx, _pin, up, mid, dn, tag in _JUMPERS:
        col = [(y, x) for x, ys in cols.items() if abs(x - kx) <= _NET_TOL
               for (y, _n) in ys]
        if len(col) != 3:
            raise SystemExit("%s 那一列（x≈%.1f）有 %d 个焊盘（应 3 个）" % (tag, kx, len(col)))
        for k, (y, x) in enumerate(sorted(col)):
            fixed[(x, y)] = [up, mid, dn][k]
    return fixed


def jumper_pin_of(cols):
    """→ {(x, y): 芯片脚 connector 号}：跳线的**中脚**就是那个芯片脚（上/下脚不是）。"""
    out = {}
    for kx, pin, _up, _mid, _dn, tag in _JUMPERS:
        col = sorted((y, x) for x, ys in cols.items() if abs(x - kx) <= _NET_TOL
                     for (y, _n) in ys)
        if len(col) != 3:
            raise SystemExit("%s 那一列（x≈%.1f）有 %d 个焊盘（应 3 个）" % (tag, kx, len(col)))
        out[(col[1][1], col[1][0])] = pin - 1
    return out


# 同网总线（`.fzp` 的 <buses>）：(总线名, 芯片脚 connector 号, 板上网名)
#   芯片脚号 = **引脚号 − 1**（connector0 = 引脚 1）。
#   ⚠ 焊盘之间靠**名字完全一致**自动成线（用户 2026-09-16 定），这里只补三件事：
#     ① 芯片脚本身（如 3V3 轨其实是 14 脚 VCC）；
#     ② **没有跳线、直连到芯片脚的那些线**（JTAG 头 P5 的 TMS/TCK/TDO/TDI/TRST、
#        P4 的 CS1、P7 的 DTR / DCD）；
#     ③ 同一根线但两处丝印写法不同的（见 `_LINE_TIES`）。
BUSES = [("GND", (17,), ("GND",)),                 # 17 = 18 脚 GND
         ("3V3", (13,), ("3V3",)),                 # 13 = 14 脚 VCC（板上丝印叫 3V3）
         ("KEY", (), ("GND/KEY",)),                # 按键/配置线（不是地）
         ("TCK", (5,), ("TCK",)),                  # 6 脚  ↔ P5 的 TCK（直连）
         ("TMS", (4,), ("TMS",)),                  # 5 脚  ↔ P5 的 TMS（直连）
         ("TDO", (6,), ("TDO",)),                  # 7 脚  ↔ P5 的 TDO（直连）
         ("TDI", (7,), ("TDI",)),                  # 8 脚  ↔ P5 的 TDI（直连）
         ("TRST", (8,), ("TRST", "CS1", "DTR")),  # 9 脚  ↔ TRST / CS1 / DTR
         ("DCD", (14,), ("DCD",))]                 # 15 脚 ↔ P7 的 DCD（直连）


def _centers():
    """每侧 10 个引脚中心（沿边方向，从上到下），对称于本体中心。"""
    c0 = TOT_H / 2.0 - (N_PER_SIDE - 1) * PITCH / 2.0
    return [c0 + i * PITCH for i in range(N_PER_SIDE)]


def icon_svg():
    """TSSOP20 顶视图 icon：黑体 4.4×6.5 + 左右各 10 金脚 + pin1 圆点 + 丝印名。"""
    L = []
    L.append('<?xml version="1.0" encoding="UTF-8"?>\n')
    L.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.1fmm" '
             'viewBox="0 0 %.2f %.1f">\n' % (TOT_W, TOT_H, TOT_W, TOT_H))
    L.append('  <g id="icon">\n')
    for c in _centers():
        L.append('    <rect x="0" y="%.3f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (c - LEAD_W / 2, LEAD_L, LEAD_W, PAD))                       # 左
        L.append('    <rect x="%.2f" y="%.3f" width="%.2f" height="%.2f" fill="%s" stroke="none"/>\n'
                 % (LEAD_L + BODY_W, c - LEAD_W / 2, LEAD_L, LEAD_W, PAD))      # 右
    L.append('    <rect x="%.2f" y="0" width="%.2f" height="%.1f" '
             'fill="%s" stroke="none"/>\n' % (LEAD_L, BODY_W, BODY_H, BODY))
    L.append('    <circle cx="%.2f" cy="%.2f" r="0.18" fill="%s" stroke="none"/>\n'
             % (LEAD_L + 0.45, _centers()[0] + 0.45, MARK))                     # pin1 圆点
    cx = TOT_W / 2.0
    L.append('    <text x="%.2f" y="%.2f" font-size="0.62" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">CH347T</text>\n' % (cx, TOT_H / 2 - 0.15, TXT))
    L.append('    <text x="%.2f" y="%.2f" font-size="0.34" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">TSSOP20</text>\n' % (cx, TOT_H / 2 + 0.62, TXT))
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


# =============================================================================
# 面包板视图 —— CH347T-EVT-R0-1v1 评估板
#
# 几何**全部来自 byHand_tables.py**（用户手工对齐 → tools/byhand_export.py 导出）。
# 本文件只负责照表出图；换位置请改手工版重跑导出，**不要在这里改坐标**。
#
# 坐标口径（沿用 AGENTS §5 与 CH347F）：内部单位 100 = 2.54mm；输出时 ×S 换成 viewBox 单位。
# 板尺寸：用户 2026-09-15 卡尺实测 50.1 × 61.2 mm（含边）。
# =============================================================================
S = 0.072                                # 内部单位（100 = 2.54mm）→ viewBox 单位
MM_U = 39.37 * S                         # 1mm → viewBox 单位

BOARD_MM = (50.1, 61.2)                  # 卡尺实测（含边）
BOARD_W, BOARD_H = BOARD_MM[0] * MM_U, BOARD_MM[1] * MM_U
BOARD_RX = 1.5 * MM_U                    # 板框圆角半径（1.5mm，量自实物照片）
BOARD_SW = 0.35 * MM_U                   # 板框描边（mm）
PCB_BLUE = "#002d68"
PCB_EDGE = "#001745"
PIN_FILL = "#d0d0d0"
PIN_EDGE = "#8a8a8a"

from byHand_tables import PAD_R, PAD_SW, SHAPES, ICONS, TEXTS      # noqa: E402

# 焊盘：SHAPES 里的 ("pad", id, net, x, y)；下面 pad_map() 给它们发 connector 号
PADS = [(i, s[1], s[2], s[3], s[4]) for i, s in enumerate(SHAPES) if s[0] == "pad"]


def pad_map():
    """→ {SHAPES 下标: connector 号}（另有 pad_rows() 给 .fzp 用的明细）

    分配顺序（可复现，与 CH347F / CH32V203C8T6 / SMA 同一套规矩）：
      ① 名字**与芯片脚主名完全一致**的焊盘优先拿该脚号（如 `VCC` 拿 14、
        跳线的中脚拿 5/6/7/8/11/12）；
      ② 其余焊盘按 上→下、左→右：名字完全对得上、且还没被占的芯片脚就拿脚号，否则发板级号；
      ③ 地的脚号（18 GND）发给最先遇到的 GND 焊盘，剩下的 GND 发板级号；
      ④ `BOARD_NETS` 里的网络一律板级号。
      ❗**不认别名**（用户 2026-09-16：「只有名字完全一致的才能共 bus」）——
      否则板上的 `MISO` 会被当成芯片 7 脚的 MISO 而偷偷并上去。
    每个焊盘**各自是一个 connector**（都能接线），同网再用 .fzp 的 <buses> 互联。
    """
    return {sidx: cn for sidx, _cid, _nm, _x, _y, cn in pad_rows()}


def pad_rows():
    """→ [(SHAPES 下标, 原 id, 网名, x, y, connector 号)]（按 上→下、左→右 发号）

    网名 = 手工版里的原值 + 用户核过的修正（`_row_names()`：**以板上丝印为准**）。
    这里定下来的就是 `.fzp` 与面包板 svg **共同的那一份**（两边必须逐字一致）。
    """
    pin_of = {nm: n - 1 for n, nm in PIN_NAMES.items()}   # 只认全名（不做别名）
    cols = {}
    for _i, _cid, nm, x, y in PADS:
        cols.setdefault(x, []).append((y, nm))
    fixed = _row_names(cols)
    jump = jumper_pin_of(cols)               # 跳线的**中脚**就是那个芯片脚
    rows = [[i, cid, fixed.get((x, y), _RENAME_BY_NAME.get(nm, nm)), x, y, None]
            for i, cid, nm, x, y in sorted(PADS, key=lambda p: (p[4], p[3]))]
    used, rail = {}, [20]
    for row in rows:                                   # ⓪ 跳线中脚 = 芯片脚（显式）
        cn = jump.get((row[3], row[4]))
        if cn is not None:
            used[cn], row[5] = cn, cn
    for row in rows:                                   # ① 主名优先
        if row[5] is not None:
            continue
        pin = None if row[2] in BOARD_NETS else pin_of.get(row[2])
        if pin is None or pin in used or row[2] == "GND":
            continue
        if row[2] == PIN_NAMES[pin + 1].split("/")[0]:
            used[pin], row[5] = pin, pin
    for row in rows:                                   # ② 其余（地除外）
        if row[5] is not None or row[2] == "GND":
            continue
        pin = None if row[2] in BOARD_NETS else pin_of.get(row[2])
        if pin is not None and pin not in used:
            used[pin], row[5] = pin, pin
        else:
            row[5] = rail[0]
            rail[0] += 1
    for row in [r for r in rows if r[5] is None]:      # ③ 地
        pin = 18 - 1                                   # 18 = GND
        if pin not in used:
            used[pin], row[5] = pin, pin
        else:
            row[5] = rail[0]
            rail[0] += 1
    return [tuple(r) for r in rows]


def buses():
    """→ [(总线名, [connector 号…])]：**同名**的焊盘并一条总线（用户 2026-09-16 定：
    「只有名字完全一致的，才能共 bus」）。

    成员 = ① 芯片脚（`BUSES` 里显式写的，如 GND=17 / VCC=13 / GND-KEY）+ ② 板上同名的**每个**
    焊盘（各自独立 connector、都能接线）。同名焊盘必然落进同一条总线 —— `fzp_check.py`
    第 ⑦ 条会守住这件事（少并一条 = 点一个焊盘时别的同网焊盘不亮）。
    """
    grp = {}
    for _sidx, _cid, net, _x, _y, cn in pad_rows():
        grp.setdefault(net, set()).add(cn)
    out = []
    for bid, pins, nets in BUSES:
        members = set(pins)
        for net in nets:
            members |= grp.pop(net, set())
        out.append((bid, sorted(members)))
    by_pos = [(x, y, cn) for _s, _c, _n, x, y, cn in pad_rows()]

    def cn_at(kx, ky):
        hit = [cn for x, y, cn in by_pos
               if abs(x - kx) <= _NET_TOL and abs(y - ky) <= _NET_TOL]
        if len(hit) != 1:
            raise SystemExit("_LINE_TIES (%s, %s) 对上了 %d 个焊盘" % (kx, ky, len(hit)))
        return hit[0]

    for bid, pts in _LINE_TIES:           # 同一条线、两处丝印写法不同 → 显式并
        members = sorted(cn_at(kx, ky) for kx, ky in pts)
        for cns in grp.values():
            cns.difference_update(members)
        out.append((bid, members))
    for net, cns in sorted(grp.items()):          # 表里剩下的同网焊盘（≥2 个）自动成一条
        if len(cns) >= 2:
            out.append((net, sorted(cns)))
    return out


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _bake_icon(part_id, cx, cy, rot=0):
    """把 `../<part_id>/svg.icon.<part_id>_icon.svg` 的 `<g id="icon">` 按 1:1 真实尺寸
    **烘成绝对坐标**嵌入（cx, cy 为内部单位，图标 viewBox 中心对准它，再绕中心转 rot 度）。

    为什么烘（AGENTS §5）：嵌套 transform 在 Inkscape / Fritzing / VS Code 预览里解释不一致
    （会出现"芯片缩小到看不见"）；烘成绝对值就与别的元件一致。rect/circle 全烘成绝对坐标，
    只有**文字**保留 rotate()（Fritzing 官方也这么写）。
    （本元件的手工版里器件是"烘进去的矩形"，所以 ICONS 现在是空的；表里出现图标时会走这里。）
    """
    import re
    path = os.path.join(OUT_DIR, "..", part_id, "svg.icon.%s_icon.svg" % part_id)
    art = open(path, encoding="utf-8").read()
    m = re.search(r'viewBox="([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+) ([-\d.eE]+)"', art)
    b = re.search(r'<g\s+id="icon">(.*)</g>', art, re.S)
    if not m or not b:
        raise RuntimeError("图标几何读不到（%s）：需要 viewBox + <g id=\"icon\">" % path)
    x0, y0, w, h = (float(v) for v in m.groups())
    ccx, ccy = x0 + w / 2.0, y0 + h / 2.0
    cx, cy = cx * S, cy * S
    ca, sa = {0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1), -90: (0, -1)}[rot]

    def mp(px, py):
        dx, dy = (px - ccx) * MM_U, (py - ccy) * MM_U
        return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)

    out = []
    for rm in re.finditer(r'<rect\s+([^>]*?)/>', b.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', rm.group(1)))
        rx, ry = float(a["x"]), float(a["y"])
        rw, rh = float(a["width"]), float(a["height"])
        ps = [mp(rx, ry), mp(rx + rw, ry), mp(rx, ry + rh), mp(rx + rw, ry + rh)]
        xs = [p[0] for p in ps]
        ys = [p[1] for p in ps]
        attrs = ' fill="%s"' % a.get("fill", "none")
        if a.get("stroke") and a["stroke"] != "none":
            attrs += ' stroke="%s" stroke-width="%.3f"' % (
                a["stroke"], float(a.get("stroke-width", 0)) * MM_U)
        out.append('  <rect x="%.3f" y="%.3f" width="%.3f" height="%.3f"%s/>\n'
                   % (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys), attrs))
    for cm in re.finditer(r'<circle\s+([^>]*?)/>', b.group(1)):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', cm.group(1)))
        p = mp(float(a["cx"]), float(a["cy"]))
        out.append('  <circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="none"/>\n'
                   % (p[0], p[1], float(a["r"]) * MM_U, a.get("fill", "none")))
    for tm in re.finditer(r'<text\s+([^>]*?)>(.*?)</text>', b.group(1), re.S):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', tm.group(1)))
        p = mp(float(a.get("x", 0)), float(a.get("y", 0)))
        t = ('  <text x="%.3f" y="%.3f" font-size="%.3f" font-family="DroidSans" fill="%s"'
             % (p[0], p[1], float(a.get("font-size", 1)) * MM_U, a.get("fill", "#c0c0c0")))
        if a.get("text-anchor"):
            t += ' text-anchor="%s"' % a["text-anchor"]
        if rot:
            t += ' transform="rotate(%.1f,%.3f,%.3f)"' % (rot, p[0], p[1])
        out.append(t + '>%s</text>\n' % tm.group(2).strip())
    other = set(re.findall(r'<(\w+)', b.group(1))) - {"rect", "circle", "text"}
    if other:
        raise RuntimeError("%s 的 icon 里有本函数不支持的图元：%s" % (part_id, sorted(other)))
    return "".join(out)


def gen_breadboard_svg():
    """CH347T-EVT-R0-1v1 面包板视图（几何来自 byHand_tables.py；**零嵌套变换**）。

    板框在**这里**画（手工版那块 #002d68 的矩形被 byHand_export 的 SKIP_RECT_FILL 丢掉了，
    免得直角框盖掉圆角）；其它图形由 `SHAPES` 按**手工版里的先后顺序**带过来 ——
    叠放次序就是画法次序（踩过：把 rect 全画在 circle 前面，跳线的黄条会被圆圈埋掉）。
    """
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
         'viewBox="0 0 %.1f %.1f">\n'
         % (BOARD_MM[0], BOARD_MM[1], BOARD_W, BOARD_H),
         ' <g id="breadboard">\n',
         '  <rect id="board" x="0" y="0" width="%.1f" height="%.1f" rx="%.2f" ry="%.2f" '
         'fill="%s" stroke="%s" stroke-width="%.2f"/>\n'
         % (BOARD_W, BOARD_H, BOARD_RX, BOARD_RX, PCB_BLUE, PCB_EDGE, BOARD_SW)]
    cns = pad_map()
    # 网名也走 pad_rows()（含 P9–P14 配置点命名与 P6/P5 修正）—— svg 的 connectorname
    # 与 .fzp 的 connector name / <buses> 必须是**同一份**，否则表面看不出来、接线时才错。
    nets = {sidx: net for sidx, _cid, net, _x, _y, _cn in pad_rows()}
    for i, s in enumerate(SHAPES):
        kind = s[0]
        if kind == "rect":
            _k, x, y, w, h, fill, _rot, stroke, sw = s
            a = ' fill="%s"' % fill if fill and fill != "None" else ' fill="none"'
            if stroke and stroke != "None":
                a += ' stroke="%s"' % stroke
                if sw and sw != "None":
                    a += ' stroke-width="%.3f"' % (float(sw) * S)
            L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f"%s/>\n'
                     % (x * S, y * S, w * S, h * S, a))
        elif kind == "circle":
            _k, x, y, r, fill, stroke, sw = s
            a = ' fill="%s"' % (fill if fill and fill != "None" else "none")
            if stroke and stroke != "None":
                a += ' stroke="%s"' % stroke
                if sw and sw != "None":
                    a += ' stroke-width="%.3f"' % (float(sw) * S)
            L.append('  <circle cx="%.2f" cy="%.2f" r="%.2f"%s/>\n' % (x * S, y * S, r * S, a))
        elif kind == "pad":
            _k, _cid, net, x, y = s
            net = nets[i]
            L.append('  <circle id="connector%dpin" connectorname="%s" cx="%.2f" cy="%.2f" '
                     'r="%.2f" fill="%s" stroke="%s" stroke-width="%.2f"/>\n'
                     % (cns[i], _esc(net), x * S, y * S, PAD_R * S, PIN_FILL, PIN_EDGE,
                        PAD_SW * S))
        elif kind == "line":
            _k, x1, y1, x2, y2, stroke, sw = s
            L.append('  <line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" '
                     'stroke-width="%.2f"/>\n'
                     % (x1 * S, y1 * S, x2 * S, y2 * S, stroke, (float(sw) if sw else 1.0) * S))
    # 板上器件（手工版里若做成"带缩放的组"，byhand_export 会认出来放进 ICONS）
    for part, x, y, rot in ICONS:
        L.append(_bake_icon(part, x, y, rot))
    # 丝印（只有带旋转的才带 transform）
    for txt, x, y, fs, anchor, rot, fill, fw in TEXTS:
        a = ' fill="%s"' % (fill if fill and fill != "None" else "#ffffff")
        if anchor and anchor != "None":
            a += ' text-anchor="%s"' % anchor
        if fw:
            a += ' font-weight="%s"' % fw
        if rot:
            a += ' transform="rotate(%.1f,%.2f,%.2f)"' % (rot, x * S, y * S)
        L.append('  <text x="%.2f" y="%.2f" font-size="%.2f" font-family="DroidSans"%s>%s'
                 '</text>\n' % (x * S, y * S, fs * S, a, _esc(txt)))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


# =============================================================================
# 原理图 —— 矩形符号（20 脚，左右各 10）
#
# 排布口径（单一源 = 手册第 3 页 TSSOP20 顶视图 + AGENTS §2「引脚号逆时针」）：
#   左列（上→下）= 1..10；右列（上→下）= 20..11（也就是 11..20 **从下往上**）。
#   这就是手册顶视图的物理排列，也正好是逆时针：1 左上 → 沿左列向下 → 10 左下 →
#   11 右下 → 沿右列向上 → 20 右上。
#   列数选择：**两排封装（SOP/TSSOP/MSOP）用左右两列**（CH340C 16 脚 / CH340E 10 脚同）；
#   四排封装（QFN/LQFP）才用四边符号（CH347F / CH32V203C8T6）。
#
# 几何口径（AGENTS §5「矩形封装（方框）原理图符号规则」）：
#   1. 左右引脚数字在引线**上方**（不与引线相交），整图同字号 FN=35（≈0.889mm，
#      对齐 Fritzing 官方引脚数字 0.881944mm）；芯片名 79（2.0mm，醒目）。
#   2. 引脚名在框内、与引脚水平中线对齐 —— 手动基线偏移 BASELINE_OFF（**不用**
#      dominant-baseline：cairosvg/Fritzing 不支持，左右名会不居中）。
#   3. 名 / 数字 / 引线**同色**（用户 2026-09-15 定：全黑）。
#   4. 名与边框留一个字符 CH=FN；数字在引线外侧，与名互不重叠。
#   5. 端点 = 22×22 **不可见** rect（靠引线末端吸附连线，不画夸张黑点）。
#   6. 本符号**没有上下引脚** → 不需要 AGENTS 的「四角无引脚区」（那是防上下名与左右名
#      在四角交叉用的）；上下只留 CH + P/2 边距。框宽按最长引脚名 + 芯片名算出来。
#   物理尺寸用 in（1000 单位 = 1in，AGENTS §5）；viewBox 贴合内容（裁边）。
# =============================================================================
SCHEM_INTERIOR = "#787878"       # 框线：Fritzing 官方 IC 符号的浅灰（CH340C/CH347F 同）


def gen_schematic_svg():
    """矩形符号：左右各 10 脚（见上面口径）。"""
    P, WIRE, CH, FN = 100, 130, 35, 35        # 脚距 2.54mm / 引线长 / 一字符间距 / 整图字号
    CHIP_FS = 79                              # 芯片名字号（2.0mm）
    BASELINE_OFF = round(FN * 0.35)           # 手动垂直居中
    per = len(PIN_NAMES)                      # 20 脚 → 每列 10
    per //= 2
    PAD_V = CH + P // 2                       # 上下边距
    # 框宽：左右各"一个字符 + 最长引脚名 + 留白"，中间还要放得下芯片名
    name_w = max(len(n) for n in PIN_NAMES.values()) * int(FN * 0.58)
    chip_w = len(PART_ID) * int(CHIP_FS * 0.58)
    GAP = 40
    BW = 2 * (CH + name_w + GAP) + chip_w
    BH = (per - 1) * P + 2 * PAD_V
    BX0, BY0 = 340, 200
    BX1, BY1 = BX0 + BW, BY0 + BH
    VBX, VBY = BX0 - WIRE - 5, BY0 - 5        # viewBox 贴合内容（裁边）
    VBW, VBH = BW + 2 * WIRE + 10, BH + 10
    L = ['<?xml version="1.0" encoding="utf-8"?>\n',
         '<svg xmlns="http://www.w3.org/2000/svg" width="%.6fin" height="%.6fin" '
         'viewBox="%d %d %d %d">\n' % (VBW / 1000.0, VBH / 1000.0, VBX, VBY, VBW, VBH),
         ' <g id="schematic">\n',
         '  <rect class="interior rect" x="%d" y="%d" width="%d" height="%d" '
         'fill="#FFFFFF" stroke="%s" stroke-width="5"/>\n' % (BX0, BY0, BW, BH, SCHEM_INTERIOR)]

    def wire(cn, x1, y1, x2, y2, tx, ty):
        """一条引脚的**线 + 不可见端点**（端点落在引线末端，靠它吸附连线）。"""
        L.append('  <line class="pin" id="connector%dpin" connectorname="%s" x1="%d" y1="%d" '
                 'x2="%d" y2="%d" stroke="#000000" stroke-width="5"/>\n'
                 % (cn, _esc(PIN_NAMES[cn + 1]), x1, y1, x2, y2))
        L.append('  <rect class="terminal" id="connector%dterminal" x="%d" y="%d" width="22" '
                 'height="22" fill="none" stroke="none"/>\n' % (cn, tx - 11, ty - 11))

    for i in range(per):                      # 左列 1..10（上→下）
        cn = i
        y = BY0 + PAD_V + i * P
        wire(cn, BX0, y, BX0 - WIRE, y, BX0 - WIRE, y)
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans">%d</text>\n' % (BX0 - WIRE // 2, y - 24, FN, cn + 1))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="start" '
                 'font-family="DroidSans">%s</text>\n'
                 % (BX0 + CH, y + BASELINE_OFF, FN, _esc(PIN_NAMES[cn + 1])))
    for i in range(per):                      # 右列 20..11（上→下；= 11..20 从下往上）
        cn = per * 2 - 1 - i
        y = BY0 + PAD_V + i * P
        wire(cn, BX1, y, BX1 + WIRE, y, BX1 + WIRE, y)
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
                 'font-family="DroidSans">%d</text>\n' % (BX1 + WIRE // 2, y - 24, FN, cn + 1))
        L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="end" '
                 'font-family="DroidSans">%s</text>\n'
                 % (BX1 - CH, y + BASELINE_OFF, FN, _esc(PIN_NAMES[cn + 1])))
    L.append('  <text x="%d" y="%d" font-size="%d" fill="#000000" text-anchor="middle" '
             'font-family="DroidSans">%s</text>\n'
             % (BX0 + BW // 2, BY0 + BH // 2 + round(CHIP_FS * 0.35), CHIP_FS, PART_ID))
    L += [' </g>\n', '</svg>\n']
    return "".join(L)


# =============================================================================
# PCB —— TSSOP20（本体 4.4×6.5、节距 0.65、含脚总宽 6.4），1 单位 = 1mm
#
# 尺寸出处 = 手册（CH347DS1.PDF）第 12 页 7.2 TSSOP20 三视图：
#   本体 4.4 × 6.5；节距 e=0.65（标称，无误差）；脚宽 0.25；**含脚总宽 6.4**
#   → 脚伸出 (6.4 − 4.4)/2 = 1.0；总高 1.1（与焊盘无关）。
# 焊盘（land）由封装尺寸推（手册没给推荐 land，与 CH347F 同一套推法）：
#   沿边 0.4 × 跨边 1.5 —— 脚跟（体边 2.2）**内** 0.15、脚尖（6.4/2 = 3.2）**外** 0.35
#   → 内缘 2.05、外缘 3.55、行中心 2.8。0.65 节距下相邻焊盘留 0.25 间隙（不打架）。
# 排列与 icon / 手册顶视图一致：左列 1..10 上→下、右列 11..20 下→上（逆时针）。
# 丝印：本体两条**横边**（y=±3.25，跨 4.4；脚在左右两侧，横线不压焊盘）+ pin1 实心圆点
#   （1 脚焊盘外侧）。**不画左右两条竖边** —— 它们正好压在焊盘上（同 CH340E 的取舍）。
# =============================================================================
def gen_pcb_svg():
    """TSSOP20 land（copper1 + silkscreen，viewBox 单位 = mm，贴合内容裁边）。"""
    PITCH, PAD_W = 0.65, 0.4
    BODY_W, BODY_L, TOT_W = 4.4, 6.5, 6.4     # 本体宽 / 本体长 / 含脚总宽（手册第 12 页）
    IN_EDGE = BODY_W / 2 - 0.15               # 焊盘内缘 2.05（脚跟处体边内 0.15）
    OUT_EDGE = TOT_W / 2 + 0.35               # 焊盘外缘 3.55（脚尖处体边外 0.35）
    PAD_L = OUT_EDGE - IN_EDGE                # 1.5
    ROW = (IN_EDGE + OUT_EDGE) / 2.0          # 行中心 2.8
    per = len(PIN_NAMES) // 2                 # 每列 10
    y0 = -(per - 1) * PITCH / 2.0             # -2.925
    pads, silk = [], []

    def pad(cn, x, y):
        pads.append('<rect id="connector%dpad" connectorname="%s" x="%.3f" y="%.3f" '
                    'width="%.3f" height="%.3f" fill="#F7BD13" stroke="none"/>'
                    % (cn, _esc(PIN_NAMES[cn + 1]), x, y, PAD_L, PAD_W))

    for i in range(per):                      # 左列 1..10（上→下）
        pad(i, -ROW - PAD_L / 2, y0 + i * PITCH - PAD_W / 2)
    for i in range(per):                      # 右列 20..11（上→下）
        pad(per * 2 - 1 - i, ROW - PAD_L / 2, y0 + i * PITCH - PAD_W / 2)
    for sy in (-1, 1):                        # 本体上下两条横边（不压焊盘）
        silk.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="#f0f0f0" '
                    'stroke-width="0.12"/>' % (-BODY_W / 2, sy * BODY_L / 2, BODY_W / 2,
                                               sy * BODY_L / 2))
    # pin1 标记：**实心圆点放在 1 脚焊盘的上边**（用户 2026-09-15 定；放左边会把 viewBox 撑宽）
    dot_x, dot_y = -ROW, y0 - PAD_W / 2 - 0.3
    silk.append('<circle cx="%.3f" cy="%.3f" r="0.15" fill="#f0f0f0" stroke="none" '
                'class="other"/>' % (dot_x, dot_y))
    # 裁边：内容 = 焊盘（x ±3.55 / y ±3.125）、丝印上下横边（y ±3.25）、pin1 圆点（y 到 ‑3.575）
    M = 0.15
    vb_x0, vb_x1 = -(ROW + PAD_L / 2) - M, ROW + PAD_L / 2 + M
    vb_y0 = min(-BODY_L / 2, dot_y - 0.15) - M
    vb_y1 = max(BODY_L / 2, dot_y + 0.15) + M
    vw, vh = vb_x1 - vb_x0, vb_y1 - vb_y0
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" '
            'viewBox="%.2f %.2f %.2f %.2f">\n'
            '  <g id="copper1">\n    ' % (vw, vh, vb_x0, vb_y0, vw, vh)
            + '\n    '.join(pads)
            + '\n  </g>\n  <g id="silkscreen">\n    '
            + '\n    '.join(silk) + '\n  </g>\n</svg>\n')


def gen_fzp():
    """.fzp：芯片 20 脚（connector0..19 = 引脚 1..20）+ 面包板专用连接器（20 起）。

    视图分配：
      · 芯片脚 → 原理图（pin + terminal）+ PCB（pad）**都有**；面包板只给"评估板上真引到
        排针"的那些（XI/XO/RST#/UD± 直接进晶体/复位/USB 座，板上没引出来）。
      · 面包板专用号（20 起）→ **只有面包板视图**（板上额外的 CFG0/CFG1/多路 GND/VCC…）。
      · 同网用 <buses> 互联（见 `buses()`）。
    """
    net_of = {cn: net for _sidx, _cid, net, _x, _y, cn in pad_rows()}
    board = sorted(net_of)
    chip_on_board = {cn for cn in board if cn < len(PIN_NAMES)}
    conns = []
    for cn in range(len(PIN_NAMES)):
        nm = _esc(PIN_NAMES[cn + 1])
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>%s</description>\n   <views>\n' % (cn, nm, nm))
        if cn in chip_on_board:
            conns.append('    <breadboardView><p layer="breadboard" svgId="connector%dpin"/>'
                         '</breadboardView>\n' % cn)
        conns.append('    <schematicView><p layer="schematic" svgId="connector%dpin" '
                     'terminalId="connector%dterminal"/></schematicView>\n' % (cn, cn))
        conns.append('    <pcbView><p layer="copper1" svgId="connector%dpad"/></pcbView>\n' % cn)
        conns.append('   </views>\n  </connector>\n')
    for cn in [c for c in board if c >= len(PIN_NAMES)]:
        nm = _esc(net_of[cn])
        conns.append('  <connector id="connector%d" name="%s" type="male">\n'
                     '   <description>%s (board rail)</description>\n   <views>\n'
                     '    <breadboardView><p layer="breadboard" svgId="connector%dpin"/>'
                     '</breadboardView>\n   </views>\n  </connector>\n' % (cn, nm, nm, cn))
    bus_xml = [" <buses>\n"]
    for bid, cns in buses():
        bus_xml.append('  <bus id="%s">\n' % _esc(bid))
        for c in cns:
            bus_xml.append('   <nodeMember connectorId="connector%d"/>\n' % c)
        bus_xml.append('  </bus>\n')
    bus_xml.append(' </buses>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<module fritzingVersion="1.0.3" moduleId="%s">\n'
            ' <version>4</version>\n <date>2026-09-15</date>\n'
            ' <label>%s</label>\n <author>Shi Jinghai</author>\n'
            ' <title>%s</title>\n'
            ' <tags><tag>CH347T</tag><tag>USB</tag><tag>SPI</tag><tag>I2C</tag>'
            '<tag>JTAG</tag><tag>UART</tag><tag>WCH</tag></tags>\n'
            ' <properties>\n'
            '  <property name="package">%s</property>\n'
            '  <property name="family">%s</property>\n'
            '  <property name="chip">CH347T</property>\n'
            '  <property name="pins">20</property>\n'
            ' </properties>\n'
            ' <views>\n'
            '  <iconView><layers image="icon/%s_icon.svg"><layer layerId="icon"/></layers>'
            '</iconView>\n'
            '  <breadboardView fliphorizontal="true" flipvertical="true">'
            '<layers image="breadboard/%s_breadboard.svg"><layer layerId="breadboard"/></layers>'
            '</breadboardView>\n'
            '  <schematicView fliphorizontal="true" flipvertical="true">'
            '<layers image="schematic/%s_schematic.svg"><layer layerId="schematic"/></layers>'
            '</schematicView>\n'
            '  <pcbView><layers image="pcb/%s_pcb.svg"><layer layerId="copper1"/>'
            '<layer layerId="silkscreen"/></layers></pcbView>\n'
            ' </views>\n'
            ' <connectors>\n%s</connectors>\n%s'
            '</module>\n'
            % (PART_ID, LABEL, TITLE, PACKAGE, FAMILY, PART_ID, PART_ID, PART_ID, PART_ID,
               "".join(conns), "".join(bus_xml)))


def main():
    files = {ICON_SVG: icon_svg(), BB_SVG: gen_breadboard_svg(),
             SCHEM_SVG: gen_schematic_svg(), PCB_SVG: gen_pcb_svg(), FZP: gen_fzp()}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)
    fzpz_dir = os.path.abspath(os.path.join(OUT_DIR, "..", "..", "fzpz"))
    os.makedirs(fzpz_dir, exist_ok=True)
    path = os.path.join(fzpz_dir, FZPZ)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(os.path.join(OUT_DIR, name), arcname=name)   # 包里**平铺**，不放子目录
    print("wrote", path)


if __name__ == "__main__":
    main()
