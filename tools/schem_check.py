#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
schem_check.py — **开发辅助**：检查"矩形符号原理图"（AGENTS §5）是否合规矩。

用法（在仓库根跑）：
    C:\Python313\python.exe tools\schem_check.py svg\CH347F
    C:\Python313\python.exe tools\schem_check.py svg\CH347F --png   # 另渲染一张白底图
    C:\Python313\python.exe tools\schem_check.py svg\XXX --no-ccw  # 跳过"逆时针"检查
      （**功能分区**符号例外：像 CD74HC4067 那样按信号分组排脚的，
        不走"沿框逆时针"那一套，用这个开关跳过）

查什么：
  ① `<svg>` 头**同时**有 width 与 height（只有 width 时 Fritzing 会"不能创建渲染"）；
     viewBox 能不能装下所有图元（会被裁掉的一眼看出）
  ② connector 齐全：每个脚都有 `connectorNpin`（线）+ `connectorNterminal`（端点），
     且**端点落在引线的外端**（差远了就连不上）
  ③ 每个脚**一个编号 + 一个名**：编号在框外贴着引线，名在框内贴着框；
     名/编号同字号（AGENTS §5「整图同字号」）
  ④ **脚号逆时针连续**：沿 框(左→下→右→上) 走一圈（每边按逆时针方向，
     即 左:上→下、下:左→右、右:下→上、上:右→左），得到的序列必须是
     所有 connector 号的一个**循环移位**，且是**递增**方向。
     （2026-09-15 踩过：右边写成 `range(14,7,-1)` → 8 跑到顶上、成了顺时针）

两种写法都认（仓库里都有）：
  · 引线 `x1,y1` 贴框、`x2,y2` 朝外（CH340C / CH32V203C8T6 / CH347F 这一派）
  · 引线 `x1,y1` 朝外、`x2,y2` 贴框（Fritzing 官方小符号那一派，如 RT6150AGQW/BAT54S）
  —— 脚本按"哪端挨着框"自动判断，所以别把两端的含义写死在检查里。

判定：退出码 0 且输出里没有 `FAIL`（**改完原理图就跑一次**）。
      退出码 2 = **不适用**（不是"矩形符号"原理图，比如两脚件/排针/整块板）。
注意：渲染 `--png` 时要**白底** —— 原理图框外是黑字，直接渲成透明底再用
PIL 转 RGB 会变黑底 → 黑字看不见（踩过，不是图错了）。
"""
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
ON_EDGE = 1.01          # "贴在框上"的容差（viewBox 单位；小符号件也够用）


def num(sv, d=0.0):
    try:
        return float(re.sub(r"[^0-9.\-]", "", sv or "") or d)
    except ValueError:
        return d


def rot_shift(seq, ref):
    """seq 是否为 ref 的循环移位。"""
    if len(seq) != len(ref) or sorted(seq) != sorted(ref):
        return False
    a = seq.index(ref[0])
    return all(seq[(a + i) % len(seq)] == ref[i] for i in range(len(seq)))


def line_ends(root):
    return [((num(e.get("x1")), num(e.get("y1"))), (num(e.get("x2")), num(e.get("y2"))))
            for e in root.iter(NS + "line")]


def find_box(root, ends):
    """找**符号框**：先认 class 含 interior 的；没有就取"引线端点贴上去最多"的那个 rect。

    为什么不直接取最大 rect：小符号件里最大的矩形常是底色，认错框会把
    "引线贴框"这类判定全部误报。
    """
    for e in root.iter(NS + "rect"):
        if (e.get("class") or "").find("interior") >= 0:
            return e, True
    best, best_hit = None, -1
    for e in root.iter(NS + "rect"):
        if e.get("id") or (e.get("fill") or "") == "none":
            continue
        x0, y0 = num(e.get("x")), num(e.get("y"))
        x1, y1 = x0 + num(e.get("width")), y0 + num(e.get("height"))
        hit = 0
        for a, b in ends:
            for p in (a, b):
                if min(abs(p[0] - x0), abs(p[0] - x1), abs(p[1] - y0), abs(p[1] - y1)) < ON_EDGE:
                    hit += 1
                    break
        if hit > best_hit:
            best, best_hit = e, hit
    return best, False


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    part_dir = os.path.abspath(argv[0])
    part = os.path.basename(part_dir)
    src = os.path.join(part_dir, "svg.schematic.%s_schematic.svg" % part)
    if not os.path.isfile(src):
        c = glob.glob(os.path.join(part_dir, "svg.schematic.*_schematic.svg"))
        if not c:
            raise SystemExit("没找到原理图：%s" % src)
        src = c[0]
    root = ET.parse(src).getroot()
    fails = []

    def na(why):
        print("\n=== 不适用：%s ===" % why)
        return 2

    if not (root.get("width") and root.get("height")):
        fails.append("FAIL <svg> 缺 width 或 height（Fritzing 会报“不能为 SVG 创建渲染”）")
    print("文件: %s" % os.path.relpath(src, os.path.dirname(part_dir)))
    print("svg: width=%s height=%s viewBox=%s" % (root.get("width"), root.get("height"),
                                                  root.get("viewBox")))
    vb = [num(v) for v in (root.get("viewBox") or "0 0 0 0").split()]
    if len(vb) == 4:
        vx, vy, vw, vh = vb
        out_of_vb = []
        for e in root.iter():
            tag = e.tag.replace(NS, "")
            if (e.get("fill") or "") == "none" and (e.get("stroke") in (None, "none")):
                continue                     # 不可见图元（terminal 那种）不参与
            x = y = None
            if tag == "line":
                x, y = num(e.get("x1")), num(e.get("y1"))
            elif tag in ("rect", "text"):
                x, y = num(e.get("x")), num(e.get("y"))
            if x is not None and not (vx <= x <= vx + vw and vy <= y <= vy + vh):
                out_of_vb.append("%s(%s,%s)" % (tag, x, y))
        if out_of_vb:
            fails.append("FAIL 有 %d 个图元在 viewBox 外（会被裁掉）：%s"
                         % (len(out_of_vb), ", ".join(out_of_vb[:4])))
        unit = "in" if (root.get("width") or "").endswith("in") else \
            ("mm" if (root.get("width") or "").endswith("mm") else "")
        print("物理尺寸: %.3f × %.3f %s（AGENTS §5：schematic 尺寸由 width/height 定）"
              % (vw / 1000.0, vh / 1000.0, unit or "单位?"))
        if not unit:
            print("注: width/height 没带单位 → Fritzing 按默认 DPI 解释，尺寸会超大"
                  "（AGENTS §5 踩过）")

    ends = line_ends(root)
    box, has_class = find_box(root, ends)
    if box is None:
        return na("没找到符号框 —— 这看起来不是“矩形符号”原理图")
    BX0, BY0 = num(box.get("x")), num(box.get("y"))
    BW, BH = num(box.get("width")), num(box.get("height"))
    BX1, BY1 = BX0 + BW, BY0 + BH
    print("框: (%g,%g)-(%g,%g)  %g × %g%s"
          % (BX0, BY0, BX1, BY1, BW, BH,
             "" if has_class else "　（按“引线端点贴得最多”认出来的）"))

    def edge_dist(x, y):
        return min(abs(x - BX0), abs(x - BX1), abs(y - BY0), abs(y - BY1))

    pins, terms = {}, {}
    for e in root.iter(NS + "line"):
        m = re.fullmatch(r"connector(\d+)pin", e.get("id") or "")
        if not m:
            continue
        n = int(m.group(1))
        e1 = (num(e.get("x1")), num(e.get("y1")))
        e2 = (num(e.get("x2")), num(e.get("y2")))
        ax, ox = (e1, e2) if edge_dist(*e1) <= edge_dist(*e2) else (e2, e1)
        pins[n] = {"el": e, "attach": ax, "outer": ox}
    for e in root.iter(NS + "rect"):
        m = re.fullmatch(r"connector(\d+)terminal", e.get("id") or "")
        if m:
            terms[int(m.group(1))] = e
    ids = sorted(set(pins) | set(terms))
    if not ids:
        return na("没有 connectorNpin/terminal —— 不是“矩形符号”原理图")
    on_box = [n for n in ids if n in pins and edge_dist(*pins[n]["attach"]) < ON_EDGE]
    if len(on_box) < 0.8 * len(ids):
        return na("只有 %d/%d 个脚的引线贴着框 —— 这套符号的脚不是沿方框四边排的"
                  % (len(on_box), len(ids)))

    missing = [n for n in ids if n not in pins or n not in terms]
    if missing:
        fails.append("FAIL 这些 connector 缺 pin 或 terminal: %s" % missing)
    off = []
    for n in ids:
        if n not in pins or n not in terms:
            continue
        ox, oy = pins[n]["outer"]
        t = terms[n]
        tx0, ty0 = num(t.get("x")), num(t.get("y"))
        tx1, ty1 = tx0 + num(t.get("width")), ty0 + num(t.get("height"))
        # 端点只要盖住引线**外端**就算过：仓库两种摆法（居中 / 左上角对齐）都认
        if not (tx0 - 1 <= ox <= tx1 + 1 and ty0 - 1 <= oy <= ty1 + 1):
            off.append(n)
    if off:
        fails.append("FAIL 这些端点没落在引线外端（会连不上）: %s" % off)
    print("connector: %d 个（%d..%d）；缺件 %s；端点偏位 %s"
          % (len(ids), ids[0], ids[-1], missing or "无", off or "无"))

    # 编号/名：按"沿边坐标"配对（名在框内贴框、编号在框外贴线）
    texts = [("".join(e.itertext()).strip(), num(e.get("x")), num(e.get("y")),
              num(e.get("font-size"))) for e in root.iter(NS + "text")
             if "".join(e.itertext()).strip()]
    if not texts:
        return na("没有文字 —— 不是“矩形符号”原理图")
    fss = {}
    for _, _, _, fs in texts:
        fss[fs] = fss.get(fs, 0) + 1
    print("字号: %s" % ", ".join("%g×%d" % (k, v) for k, v in sorted(fss.items())))

    sides = {"left": [], "bottom": [], "right": [], "top": []}
    for n in ids:
        if n not in pins:
            continue
        ax, ay = pins[n]["attach"]
        d = (abs(ax - BX0), abs(ay - BY1), abs(ax - BX1), abs(ay - BY0))
        k = d.index(min(d))
        if min(d) >= ON_EDGE:
            fails.append("FAIL connector%d 的引线没贴在框上（贴框端 %g,%g）" % (n, ax, ay))
            continue
        sides[("left", "bottom", "right", "top")[k]].append((ay if k in (0, 2) else ax, n))
        el = pins[n]["el"]
        if (el.get("class") or "") != "pin":
            fails.append('FAIL connector%dpin 缺 class="pin"（Fritzing 不认）' % n)
        if not el.get("connectorname"):
            fails.append("FAIL connector%dpin 缺 connectorname" % n)

    # 编号/名：按"沿边坐标"配对（编号框外贴线、名框内贴框）。
    #   容差一律按**文字自己的字号**算 —— 仓库里符号尺度差两个数量级
    #   （CH347F 的字号 35，官方小符号件 0.88），写死绝对值必然误报。
    def cross_and_depth(side, x, y):
        """沿边坐标 / 到该边的带符号距离（框外为正、框内为负）。"""
        if side == "bottom":
            return x, y - BY1
        if side == "top":
            return x, BY0 - y
        if side == "left":
            return y, BX0 - x
        return y, x - BX1

    def nearest_side(x, y):
        return max(("left", "right", "bottom", "top"),
                   key=lambda s: cross_and_depth(s, x, y)[1])

    numbers, names = {}, {}
    for s, x, y, fs in texts:
        if fs <= 0 or (BX0 < x < BX1 and BY0 < y < BY1):
            continue                                   # 只看框外的（编号候选）
        side = nearest_side(x, y)
        c, dep = cross_and_depth(side, x, y)
        if 0 < dep <= 2.5 * fs + 0.5:                   # 贴着自己的引线
            numbers.setdefault(side, []).append((c, fs, s))
    num_fs = {fs for v in numbers.values() for _, fs, _ in v}
    ref_fs = max(num_fs) if num_fs else max(fs for _, _, _, fs in texts)
    names, names_old = {}, {}      # names_old = 老判据（最近边），只当新判据找不到时的兜底
    for s, x, y, fs in texts:
        # 只认"框内、贴着自己的边、且**不比脚号大多少**"的文字为引脚名：
        #   芯片名/图例（79 vs 35）比脚号大得多，若不排除，它会落在框中间，
        #   稍一凑巧就把某个脚的"名"配成两条（W25Q16JV 踩过）。
        if fs <= 0 or fs > 1.3 * ref_fs or not (BX0 < x < BX1 and BY0 < y < BY1):
            continue
        s_old = nearest_side(x, y)
        c_old, dep_old = cross_and_depth(s_old, x, y)
        if abs(dep_old) <= len(s) * 0.58 * fs + 1.2 * fs:
            names_old.setdefault(s_old, []).append((c_old, fs, s))
        # 归侧（2026-09-25 修，用户：「是识别错误」）：以前按"最近边"定侧 ——
        #   画在框上边最左的 EPAD，它的名字离**左边**比离上边更近 ✗ ⇒ 名字被算成
        #   left，上边的脚反而报"找不到名"（CH32V002D4U6 [12] / CH32V002F4U6 [20] /
        #   CH32V003F4U6 [20] 三件，全是假报 ✗）。
        #   现在：候选 =「深度在贴身带内」**且**「横轴对得上该边某个脚」的边，
        #   再按（横轴距离, 深度）取**唯一的**最近边 ⇒ 每个名字只归一条边 ✓。
        #   ★ 试过两种错法：①"满足条件的边都登记一次" ⇒ SOP8 的 J4M6 撞成"找到多个" ✗；
        #   ②"只按横轴兜底" ⇒ 左边的 VSS 名被算进上边 ✗ ⇒ 都回退了。
        cand = []
        for side in ("left", "right", "bottom", "top"):
            c, dep = cross_and_depth(side, x, y)
            if abs(dep) > len(s) * 0.58 * fs + 1.2 * fs:      # 名要贴着自己的边
                continue
            dx = min([abs(c - cc) for cc, _n in sides.get(side, [])] or [1e9])
            if dx > 1.2 * ref_fs:                            # 横轴得对得上这条边的某个脚
                continue
            cand.append((dx, abs(dep), side, c))
        if not cand:
            continue
        near = nearest_side(x, y)          # 原判据：最近边 —— 先信它（保住老行为 ✓）
        pick = next((t for t in cand if t[2] == near), None)
        if pick is None:                   # 只有"最近边底下根本没有这个脚"时才换边 ✓
            pick = min(cand)               # （角上的名字就是这种情况 ✗）
        _dx, _dp, side, c = pick
        names.setdefault(side, []).append((c, fs, s))
    name_fs = {fs for v in list(names.values()) + list(names_old.values()) for _, fs, _ in v}

    side_of = {n: s for s in sides for _, n in sides[s]}
    no_num, no_name = [], []
    for n in ids:
        side = side_of.get(n)
        if side is None or n not in pins:
            continue
        ax, ay = pins[n]["attach"]
        on_axis = ax if side in ("bottom", "top") else ay
        if len([1 for c, _, _ in numbers.get(side, []) if abs(c - on_axis) <= 1.2 * ref_fs]) != 1:
            no_num.append(n)
        got = len([1 for c, _, _ in names.get(side, []) if abs(c - on_axis) <= 1.2 * ref_fs])
        if got != 1:
            # 新判据不是"正好 1 条"时，退回**老判据（最近边）** ✓ —— 小符号（SOP8 的
            # J4M6）的名字紧贴角上，新判据会归错边（0 条或 2 条 ✗），老判据能对上 ✓；
            # 这样改完**不会新增任何误报**（老判据能过的仍过 ✓），只是多修掉角上的假报 ✓。
            got = len([1 for c, _, _ in names_old.get(side, [])
                       if abs(c - on_axis) <= 1.2 * ref_fs])
        if got != 1:
            no_name.append(n)
    if no_num:
        fails.append("FAIL 这些脚找不到（或找到多个）**编号**（应贴在框外引线边）：%s"
                     % no_num[:8])
    if no_name:
        # 名的检查只对"§5 方框风格"生效：那种符号 名与编号同字号、名在框内。
        # 官方小符号风格（如 ME4054/TP4057）名很小或干脆不写 → 只提示，不判 FAIL。
        if name_fs and num_fs and max(name_fs) < 0.8 * min(num_fs):
            print("注: 本符号的引脚名比编号小得多（官方小符号风格）→ 跳过“名”的检查")
            print("    （未必真少名，只是没按 §5 的“名与编号同字号”画）")
        elif not name_fs:
            print("注: 本符号不写引脚名（只标编号）→ 跳过“名”的检查")
        else:
            fails.append("FAIL 这些脚找不到（或找到多个）**引脚名**（应在框内、贴着自己的边）：%s"
                         % no_name[:8])

    # ④ 逆时针连续：左(上→下) → 下(左→右) → 右(下→上) → 上(右→左)
    walk = ([n for _, n in sorted(sides["left"])]
            + [n for _, n in sorted(sides["bottom"])]
            + [n for _, n in sorted(sides["right"], reverse=True)]
            + [n for _, n in sorted(sides["top"], reverse=True)])
    print("逆时针展开: %s" % " ".join(str(n) for n in walk))
    if "--no-ccw" in argv:
        print("→ 跳过“逆时针”检查（--no-ccw：功能分区符号不适用）")
    elif rot_shift(walk, ids):
        print("→ 脚号逆时针连续 ✓")
    elif rot_shift(list(reversed(walk)), ids):
        fails.append("FAIL 脚号整圈排反了（现在是**顺时针**连续）：把每条边的方向都倒过来")
    else:
        brk = [i for i in range(len(walk) - 1) if walk[i + 1] != walk[i] + 1]
        real = [i for i in brk if not (walk[i] == ids[-1] and walk[i + 1] == ids[0])]
        if not real:
            fails.append("FAIL 沿边走一圈看不出规律（脚号本身也不连续）：%s" % walk)
        else:
            det = "；".join("第 %d 个脚后 %d→%d（本该 %d→%d）"
                            % (i + 1, walk[i], walk[i + 1], walk[i], walk[i] + 1)
                            for i in real[:3]) + ("　…等 %d 处" % len(real)
                                                  if len(real) > 3 else "")
            fails.append("FAIL 脚号不是逆时针连续的：不该断的地方断了 %d 处 —— %s"
                         "（正常只该在绕回起点处断一次）。多半是某条边的 range 方向写反、"
                         "或该边起点没接上一条边的终点"
                         "（2026-09-15 踩过：右边写成 range(14,7,-1) → 8 跑到顶上）"
                         % (len(real), det))

    if "--png" in argv:
        import cairosvg
        out = os.path.join(os.environ.get("TEMP", "."), "schemcheck_%s_white.png" % part)
        cairosvg.svg2png(url=src, write_to=out, output_width=1400, background_color="white")
        print("白底渲染: %s（透明底会让框外黑字看不见）" % out)

    print()
    if fails:
        print("\n".join(fails))
        print("=== %d 项 FAIL ===" % len(fails))
        return 1
    print("=== 全部通过 ===")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main(sys.argv[1:]))
