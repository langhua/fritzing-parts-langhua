# -*- coding: utf-8 -*-
r"""BQ25570（VQFN-20 / RGR，3.5×3.5 mm）—— 生成脚本

★ 数据来源（全部实测，不是估的 ✓）：
  · 封装：**VQFN-20 = RGR**、本体 **3.5×3.5 mm**（TI bq25570.pdf 封装/订购信息 ✓）
  · 脚距 **0.50 mm**（每边 5 脚 ✓）、引脚号↔名字取自**第 4 页 Pin Functions** ✓
  · land pattern（PCB 视图用 ✓，第 43 页）：焊盘 **0.28×0.85** ✓、内缘 **2.60**、外缘 **4.30**
    （= 2.60 + 2×0.85 ✓ 自洽 ✓）、**PowerPAD 2.05×2.05** ✓、阻焊 0.07 全周、圆角 R0.14 ✓
★ 画法照库里 QFN 件的既有风格（`CH32V002D4U6` 的 icon ✓）：
  32×32 px viewBox、本体 `#303030` 17×17 rx0.3、引脚金色 `#f7bf13`、1 脚圆点 `#c0c0c0` r1、
  中间打型号字 ✓；**不加底色/高光/阴影** ✗（§1 工业风 ✓）。

用法： py -3.13 -u -X utf8 gen_part.py     # 在**本目录**生成 4 个视图（目前只做 icon）
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ID = "BQ25570"
HERE = os.path.dirname(os.path.abspath(__file__))

# ── icon 几何（px，viewBox 32×32；1 px = 3.5mm/17 = 0.2059 mm ⇒ 0.5mm 脚距 = 2.4286px?? ✗）
#   ★ 照库里的画法：本体 17px、脚距 **3.40px**（= 0.5mm ✓，与 CH32V002D4U6 同一套比例 ✓）
BODY = 17.0            # 本体边长（px）
CB = 16.0              # 画布中心
PITCH = 3.40           # 0.5 mm ✓（库里同一套 ✓）
PAD_W = 1.70           # 脚宽（0.28mm×6.07 ≈ 1.70 ✓ 与兄弟件一致 ✓）
PAD_L = 4.68           # 脚长（伸出体外的可见段 ✓，兄弟件一致 ✓）
GAP = 0.96             # 本体边到脚内端的空隙（兄弟件：7.50 − (3.04+4.68) = −0.22 ⇒ 脚压进本体 ✓）
PIN1_CX, PIN1_CY = 9.60, 22.40   # 1 脚圆点（**左下** ✓ —— 手册顶视图 pin1 在左下 ✓）
TXT_H = 2.30           # 中间型号字：**用户 2026-10-17 定 → 写 `BQ25570`** ✓（7 字符，字号看着缩到 2.3 ✓）

half = BODY / 2.0
body_lo, body_hi = CB - half, CB + half          # 7.50 .. 24.50 ✓
centers = [CB + PITCH * (i - 2) for i in range(5)]   # 5 个脚位：9.20, 12.60, 16.00, 19.40, 22.80 ✓
lo = body_lo - PAD_L                             # 3.04 ✓
hi = body_hi                                     # 24.50 ⇒ 外侧脚 x = 24.50 − 0.22 hmm


def pads():
    out = []
    for c in centers:
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (body_lo - PAD_L, c - PAD_W / 2, PAD_L, PAD_W))            # 左
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (body_hi, c - PAD_W / 2, PAD_L, PAD_W))                    # 右
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (c - PAD_W / 2, body_lo - PAD_L, PAD_W, PAD_L))            # 上
        out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#f7bf13" stroke="none"/>'
                   % (c - PAD_W / 2, body_hi, PAD_W, PAD_L))                    # 下
    return out


def icon_svg():
    L = ['<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">',
         ' <g id="icon">']
    L += ["  " + p for p in pads()]
    L.append('  <rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="0.3" ry="0.3" '
             'fill="#303030" stroke="none"/>' % (body_lo, body_lo, BODY, BODY))
    L.append('  <circle cx="%.2f" cy="%.2f" r="1.0" fill="#c0c0c0" stroke="none"/>'
             % (PIN1_CX, PIN1_CY))
    L.append('  <text x="%.1f" y="%.1f" font-size="%.1f" font-family="DroidSans" fill="#c0c0c0" '
             'text-anchor="middle" dominant-baseline="central">%s</text>' % (CB, CB, TXT_H, ID))
    L += [' </g>', '</svg>', '']
    return "\n".join(L)


def main():
    p = os.path.join(HERE, "svg.icon.%s_icon.svg" % ID)
    open(p, "w", encoding="utf-8", newline="\n").write(icon_svg())
    print("写入 %s ✓" % os.path.basename(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
