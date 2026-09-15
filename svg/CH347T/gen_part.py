#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
gen_part.py — CH347T 高速 USB 转 SPI/I2C/JTAG/UART 芯片（WCH）Fritzing 元件生成器。
================================================================================
元件形态（用户 2026-09-14 定）：
  - **芯片**（CH347T）出 icon / 原理图 / PCB 三个视图；
  - **面板上用的那块官方评估板 CH347T-EVT-R0-1v1** 只出现在**面包板视图**，
    板上排针**全部做成可连线 connector**（按信号名映射到芯片脚；3V3/GND/5V 用 <buses> 互通）。

资料（都在本机，不是猜的）：
  · `D:\Downloads\CH347DS1.PDF`（CH347 手册 V1.5）：
      - 封装：**TSSOP20，塑体 4.4×6.5mm，引脚节距 0.65mm**；CH347F = QFN28 4×4mm / 0.4mm；
      - 第 3 页引脚排列图（TOP VIEW，本脚本引脚的来源）：
          左侧 上→下 = 1..10；右侧 下→上 = 11..20；
          1 RST# | 2 CTS1/GPIO6 | 3 TXD1 | 4 RXD1 | 5 DSR0/GPIO2/SCS0/TMS |
          6 CTS0/GPIO0/SCK/TCK | 7 RTS0/GPIO1/MISO/TDO | 8 TXD0/MOSI/TDI |
          9 TNOW0/DTR0/GPIO5/SCS1/TRST | 10 TNOW1/DTR1 |
          11 RI0/GPIO3/SCL | 12 RXD0/SDA | 13 RTS1/GPIO7 | 14 VCC | 15 DCD0/GPIO4/ACT |
          16 UD- | 17 UD+ | 18 GND | 19 XI | 20 XO
      - CH347T 靠 **CFG0/CFG1 引脚上电时的电平** 选工作模式：
          0 = 双 UART；1 = 单 UART(VCP)+SPI+I2C；2 = 单 UART(HID)+SPI+I2C；3 = 单 UART+JTAG/SWD
  · `D:\Downloads\CH347EVT\EVT\PUB\CH347EVT_EN.pdf`（评估板说明 V1.5）：板级单元说明 + 实物照片；
  · `D:\Downloads\CH347EVT\EVT\PCB\CH347SCH.pdf`：评估板原理图（面包板视图的排针定义来源）。

进度（按 fritzing-parts-langhua AGENTS.md §2 芯片类工作流）：
  [x] 1. icon（TSSOP20 顶视图：黑体 4.4×6.5 + 两侧金脚 + pin1 圆点）
  [ ] 2. breadboard（= CH347T-EVT-R0-1v1 整块评估板）
  [ ] 3. schematic（矩形 20 脚符号）
  [ ] 4. pcb（TSSOP20 4.4×6.5 P0.65）
  [ ] 5. part.CH347T.fzp + 打包 fzpz
"""
import os

import bb_board                       # 面包板视图（= CH347T-EVT-R0-1v1 整块板）的几何表 + 出图

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

# 颜色（与仓库其它芯片 icon 一致）
BODY = "#303030"
PAD = "#f7bf13"
MARK = "#c0c0c0"
TXT = "#c0c0c0"

# ---- 几何（mm，1:1 实物）----------------------------------------------------
BODY_W = 4.4          # 塑体宽（引脚在左右两侧伸出）
BODY_H = 6.5          # 塑体高
LEAD_L = 1.0          # 引脚伸出长度（用户 2026-09-14：0.25 x 1mm）
LEAD_W = 0.25         # 引脚宽
PITCH = 0.65          # 节距
N_PER_SIDE = 10       # 每侧 10 脚
TOT_W = BODY_W + 2 * LEAD_L
TOT_H = BODY_H

# 引脚名（datasheet 第 3 页排列图）—— **单源在 bb_board.PIN_NAMES**（面包板视图也要用它
# 把每个焊盘映射到芯片脚号），这里只做个别名，免得两边各抄一份。
PIN_NAMES = bb_board.PIN_NAMES


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
    # pin1 圆点：左上角内侧
    L.append('    <circle cx="%.2f" cy="%.2f" r="0.18" fill="%s" stroke="none"/>\n'
             % (LEAD_L + 0.45, _centers()[0] + 0.45, MARK))
    cx = TOT_W / 2.0
    L.append('    <text x="%.2f" y="%.2f" font-size="0.62" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">CH347T</text>\n' % (cx, TOT_H / 2 - 0.15, TXT))
    L.append('    <text x="%.2f" y="%.2f" font-size="0.34" font-family="DroidSans" fill="%s" '
             'text-anchor="middle" stroke="none">TSSOP20</text>\n' % (cx, TOT_H / 2 + 0.62, TXT))
    L.append('  </g>\n')
    L.append('</svg>\n')
    return "".join(L)


def main():
    files = {ICON_SVG: icon_svg(), BB_SVG: bb_board.gen_breadboard_svg(OUT_DIR)}
    for name, content in files.items():
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        print("wrote", name)


if __name__ == "__main__":
    main()
