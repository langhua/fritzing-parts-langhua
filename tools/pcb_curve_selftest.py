# -*- coding: utf-8 -*-
r"""★★ 曲线几何**单测** ✓：合出来的模型里放一条**鼓出去的弧** ⇒ 校验器必须看得见它 ✓
（2026-10-08 立 ✓，见 `docs/fritzing-sketch-format-notes.md` **F18** ✓）

为什么要有它 ✗：弧的真形状在 `<bezier>` 里 ✓ ⇒ ✗ 谁拿两端点的**弦**当"线在哪"，
在弧上就是错的 ✗（实测 v59 那条 `24 mil` 电源弧偏离弦最多 **≈2.5 mm** ✗）。
★ 但"我把判据改成看弧了"这件事**不能靠读代码相信** ✗ —— 这个单测**不用 fzz** ✓，
  直接在内存里合一个模型 ✓（`pcb_check.check()` 收的就是模型字典 ✓）⇒ 想验哪个判据就摆哪个局 ✓。

四条判据（各摆一个"弦看不见、弧看得见"的局 ✓；✗ 弦口径下必然**不报/报歪** ✗）：
  ① 弧**线身**贴着别的走线 ⇒ 不算**悬空端点** ✓
  ② 弧**鼓到板外** ⇒ 必须报 ②（✗ 弦口径看两端点都在板上 ⇒ 一个字不报 ✗）
  ③ 过孔落在**弧上**、离弦很远 ⇒ 不能报**孤立过孔** ✓
  ⑨ 安装孔落在**弧上**、离弦很远 ⇒ 必须报 ⑨（孔不许被线碰 ✓）
  ④ 弧压到**别的网**的盘 ⇒ 必须报 ④b（✗ 弦离那个盘很远 ⇒ 漏报 ✗）

用法：`py tools\pcb_curve_check.py --selftest` 或直接跑本文件 ✓；退出码 0 = 全过 ✓
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_check as PC                                             # noqa: E402
import pcb_wire as PW                                              # noqa: E402

SK = PW.SK
FAILS = []


def pad(title, cid, box, layer="copper0", thr=False, mi=None, circle=None, nm=None):
    return dict(title=title, cid=cid, box=box, layer=layer, thr=thr, mi=mi,
                circle=circle, nm=nm, box2=None)


def trace(geo, bezier=None, layer="copper0", mils=24.0, inst="1", ends=None):
    """按 `pcb_check.collect()` 的同一套口径合一条走线 ✓（字段一个都不能少 ✗）

    ★ `curve` 是"**这条线是不是弧**"的记号 ✓ —— ✗ 漏了它就等于告诉校验器"这是直线" ✗
      （这块自己踩过：改完 `curve` 判据后本文件没跟着补 ⇒ 五条局全假失败 ✓）。
    """
    t = dict(layer=layer, geo=geo, bezier=bezier, mils=mils, ends=ends or {})
    a, b = PW.abs_ends(geo)
    return dict(layer=layer, a=a, b=b, pts=PW.trace_pts(t), curve=bool(bezier),
                bez=PW.ctrl_pts(geo, bezier), mils=mils, inst=inst, ends=ends or {})


def model(traces, pads=(), vias=(), board=(0.0, 0.0, 100.0, 100.0), holes=(), expect=None):
    return dict(pads=list(pads), traces=list(traces), vias=list(vias), board=board,
                bodies=[], holes=list(holes), text="", name="synthetic.fzz",
                parts=[], net_pads={}, warns=[])


def check(name, cond, detail):
    print("   %s %s" % ("✓" if cond else "✗", name))
    print("       %s" % detail)
    if not cond:
        FAILS.append(name)


# ── 那条弧：p0 = (20,20)、p3 = (60,20)、控制点把它鼓到 y ≈ 20+? ────────────────
#   `cp0 = (30, 60)`、`cp1 = (50, 60)`（相对 loc ✓）⇒ 顶点在 y = 20 + 0.75*40 = 50 ✓
GEO = dict(x="20", y="20", x1="0", y1="0", x2="40", y2="0")
BEZ = ((30.0, 60.0), (50.0, 60.0))
P0, P3 = (20.0, 20.0), (60.0, 20.0)
TOP = (40.0, 50.0)          # 弧顶（对称 ⇒ t = 0.5 ✓：0.125*20+0.375*50+0.375*70+0.125*60 = 50 ✓）

print("== 局 ① 弧线身贴着另一条走线 ⇒ 不算「悬空端点」==")
t_arc = trace(GEO, BEZ, layer="copper0")
#   ★ 那条竖线**两端也要锚好** ✗ —— 否则它自己那两条"越过交点后剩下的死头"本来就是悬空的 ✓
#     （① 判的是"这一端有没有接上" ✓：线身穿过另一条线后，越过去的那截确实是**天线** ✗
#      ⇒ 报它是对的 ✓；本局要验的是**弧那一侧** ✓。）
u = trace(dict(x="40", y="40", x1="0", y1="0", x2="0", y2="20"), layer="copper0")
p_A = pad("U1", "connector0", (18.0, 18.0, 22.0, 22.0))
p_B = pad("U1", "connector1", (58.0, 18.0, 62.0, 22.0))
p_C = pad("U2", "connector0", (38.0, 38.0, 42.0, 42.0))
p_D = pad("U2", "connector1", (38.0, 58.0, 42.0, 62.0))
probs, _notes, _g = PC.check(model([t_arc, u], [p_A, p_B, p_C, p_D]))
d_chord = PC.d_pt_seg(TOP, P0, P3) * SK
d_arc = PC.d_pt_trace(TOP, t_arc) * SK
has1 = [p for p in probs if p.startswith("①")]
check("① 弧线身接上另一条线 ⇒ 一条悬空都不报", not has1,
      "弧到线身那点：弦距 **%.2f mm**（> TOL %.2f ⇒ 弦口径看不见 ✗）｜真弧距 **%.3f mm** ✓"
      "｜实报：%s" % (d_chord, PC.TOL * SK, d_arc,
                     (has1[0][:60] + "…") if has1 else "（没有 ✓）"))
print()


print("== 局 ② 弧鼓到板外 ⇒ 必须报 ②（弦口径看不见）==")
probs2, _n2, _g2 = PC.check(model([t_arc], [p_A, p_B], board=(10.0, 10.0, 70.0, 30.0)))
has2 = [p for p in probs2 if p.startswith("②")]
check("② 弧鼓出板框 ⇒ 报「板外」", bool(has2),
      "弧顶 y = %.1f 板框下沿 y = 30 ⇒ 鼓出 %.1f mm ✓；两端 (%.0f,%.0f)/(%.0f,%.0f) 都在板上 ✓ ⇒ "
      "弦口径一个字都不会报 ✗｜实报：%s"
      % (TOP[1] * SK, (TOP[1] - 30.0) * SK, P0[0] * SK, P0[1] * SK, P3[0] * SK, P3[1] * SK,
         (has2[0][:60] + "…") if has2 else "（没有 ✗）"))
print()


print("== 局 ③⑨ 过孔 / 安装孔落在弧上、离弦很远 ⇒ 不许报「孤立」，必须报 ⑨ ==")
v_on = dict(layer="copper0", p=TOP, geo=TOP, off=0.0, inst=None, ttl="Via1",
            hole_mm=0.3, ring_mm=0.15)
#   ★ 这一局**不能**在弧顶放焊盘 ✗ —— 放了的话**弦口径也会**因为"孔心落在盘框里"而放行 ✓
#     ⇒ 那样就验不出差异了 ✓（✗ 第一版就是这么写的 ✗，`_scratch` 的对账当场揭穿 ✓）。
prof3 = PC.d_pt_seg(TOP, P0, P3) * SK
pads3 = [pad("U1", "connector0", (18.0, 18.0, 22.0, 22.0)),
         pad("U1", "connector1", (58.0, 18.0, 62.0, 22.0))]
probs3, notes3, _g3 = PC.check(model([t_arc], pads3, [v_on]))
has3 = [p for p in probs3 if p.startswith("③")]
check("③ 过孔在弧上 ⇒ 不报孤立过孔", not has3,
      "过孔到**弦** %.2f mm（> 盘半径 0.30 + 半宽 0.30 ⇒ 弦口径**必报孤立** ✗，已实测 ✓）"
      "｜到**弧** %.3f mm ✓｜实报：%s"
      % (prof3, PC.d_pt_trace(TOP, t_arc) * SK, (has3[0][:50] + "…") if has3 else "（没有 ✓）"))
check("③ 顺带：它被算作「挨到 copper0」", any("挨到" in n and "过孔 #0" in n for n in notes3),
      "notes 里应有 `过孔 #0 … 挨到 …` ✓")

probs3b, _n3b, _g3b = PC.check(model([t_arc], pads3, [],
                                     holes=[(TOP, 2.2, None)]))
has9 = [p for p in probs3b if p.startswith("⑨")]
check("⑨ 安装孔在弧上 ⇒ 报「离孔太近」", bool(has9),
      "孔在弧顶 ⇒ 弧到孔心 **0.000 mm** ✓（弦距 %.2f mm ⇒ 弦口径漏报 ✗，已实测 ✓）｜实报：%s"
      % (prof3, (has9[0][:60] + "…") if has9 else "（没有 ✗）"))
print()


print("== 局 ④b 弧压到**别的网**的盘 ⇒ 必须报（弦离那只盘很远）==")
#   弧顶 y=50 处摆一只 `X1.connector0` 的盘 ✓、网表说它是 `BR+` ⇒ 与弧所在的 `5V` 不同网 ✓
p_other = pad("X1", "connector0", (38.0, 48.0, 42.0, 52.0))
pads4 = [pad("U1", "connector0", (18.0, 18.0, 22.0, 22.0)),
         pad("U1", "connector1", (58.0, 18.0, 62.0, 22.0)), p_other]
expect = {"5V": ["U1.connector0", "U1.connector1"], "BR+": ["X1.connector0"]}
probs4, _n4, _g4 = PC.check(model([t_arc], pads4, [], expect=expect), expect)
has4b = [p for p in probs4 if p.startswith("④b")]
check("④b 弧身压别的网的盘 ⇒ 报短路桥", bool(has4b),
      "弧身到那只盘 **0.000 mm**（弦距 %.2f mm ⇒ 弦口径漏报 ✗，已实测 ✓）｜实报：%s"
      % (prof3, (has4b[0][:70] + "…") if has4b else "（没有 ✗）"))

print()
print("== 反向自检 ✗：把弧换成**同一条弦**的直线 ⇒ 上面 ②/⑨/④b 必须全**不报** ✓ ==")
t_line = trace(dict(x="20", y="20", x1="0", y1="0", x2="40", y2="0"), None,
               layer="copper0", mils=24.0, inst="1")
l2, _n5, _g5 = PC.check(model([t_line], [p_A, p_B], [], board=(10.0, 10.0, 70.0, 30.0)))
check("直线 ⇒ 没有 ②", not [p for p in l2 if p.startswith("②")], "直线完全在板内 ✓")
l3, _n6, _g6 = PC.check(model([t_line], pads4, [], expect=expect), expect)
check("直线 ⇒ 没有 ④b", not [p for p in l3 if p.startswith("④b")],
      "直线离那只盘 %.2f mm ✓（这就是**弦口径**下会发生的事 ✓ —— 弧上却是 0 ✓）" % prof3)

print()
print("== 弧长 / 弦长 的量 ✓（`pcb_wire.poly_len` ✓）==")
arc_mm = PW.poly_len(t_arc["pts"]) * SK
chord_mm = math.hypot(P3[0] - P0[0], P3[1] - P0[1]) * SK
print("   弧长 %.3f mm ｜ 弦长 %.3f mm ⇒ 弧**长 %.1f%%** ✓" % (arc_mm, chord_mm,
                                                            (arc_mm / chord_mm - 1) * 100))
check("弧长 > 弦长", arc_mm > chord_mm + 1e-9, "这是「弦口径线长少报」的量化 ✓")

print()
if FAILS:
    print("✗ %d 条不过：%s" % (len(FAILS), "、".join(FAILS)))
    raise SystemExit(1)
print("✓ 全部通过：弦看不见的四处，弧这一口径**都看得见** ✓")
raise SystemExit(0)
