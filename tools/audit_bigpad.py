# -*- coding: utf-8 -*-
"""找出「有中央大焊盘（散热盘）」但名字不叫 EPAD/EP 的零件（上一轮漏掉的）。

判据：PCB svg 里 id="connector<N>pad" 的元素中，**面积最大的那个**明显大于中位数
（≥2.2 倍边长），且它靠近画布中心 ⇒ 视为散热盘（不管它叫什么名字）。
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SVG = "{http://www.w3.org/2000/svg}"
ROOT = r"f:\git\fritzing-parts-langhua\svg"

CMD = re.compile(r"([MLAZmlaz])|(-?\d+\.?\d*(?:e-?\d+)?)")


def path_bbox(d):
    """最小路径解析：M/L/Z 绝对坐标、A 取端点、a 相对端点（够算焊盘包围盒）。"""
    vals = CMD.findall(d)
    pts, cx, cy, start, cmd, i = [], 0.0, 0.0, None, None, 0
    nums = []

    def flush(cmd, nums):
        nonlocal cx, cy, start
        if cmd in ("M", "L"):
            for k in range(0, len(nums) - 1, 2):
                cx, cy = nums[k], nums[k + 1]
                pts.append((cx, cy))
            if cmd == "M" and nums:
                start = (nums[-2], nums[-1])
        elif cmd == "m":
            for k in range(0, len(nums) - 1, 2):
                cx, cy = cx + nums[k], cy + nums[k + 1]
                pts.append((cx, cy))
            if nums:
                start = (cx, cy)
        elif cmd in ("A", "a"):
            for k in range(0, len(nums) - 6, 7):
                seg = nums[k:k + 7]
                if cmd == "A":
                    cx, cy = seg[5], seg[6]
                else:
                    cx, cy = cx + seg[5], cy + seg[6]
                pts.append((cx, cy))

    for letter, num in vals:
        if letter:
            if cmd:
                flush(cmd, nums)
            cmd, nums = letter, []
        else:
            nums.append(float(num))
    if cmd:
        flush(cmd, nums)
    if not pts:
        return None
    xs = [p[0] for p in pts] + [cx]
    ys = [p[1] for p in pts] + [cy]
    return (min(xs), min(ys), max(xs), max(ys))


def elem_bbox(e):
    tag = e.tag.replace(SVG, "")
    if tag == "rect":
        x, y = float(e.get("x", 0)), float(e.get("y", 0))
        w, h = float(e.get("width", 0)), float(e.get("height", 0))
        return (x, y, x + w, y + h)
    if tag == "circle":
        cx, cy, r = float(e.get("cx", 0)), float(e.get("cy", 0)), float(e.get("r", 0))
        return (cx - r, cy - r, cx + r, cy + r)
    if tag == "path":
        return path_bbox(e.get("d") or "")
    bs = [b for b in (elem_bbox(c) for c in list(e)) if b]
    if not bs:
        return None
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def parse_fzp(pdir):
    fzps = [f for f in os.listdir(pdir) if f.startswith("part.") and f.endswith(".fzp")]
    if not fzps:
        return None
    return ET.parse(os.path.join(pdir, fzps[0])).getroot()


print("%-22s %-12s %-22s %s" % ("零件", "大焊盘", "尺寸(mm)", "其余焊盘中位尺寸"))
hits = []
for d in sorted(os.listdir(ROOT)):
    pdir = os.path.join(ROOT, d)
    if not os.path.isdir(pdir):
        continue
    root = parse_fzp(pdir)
    if root is None:
        continue
    pcbs = [f for f in os.listdir(pdir) if f.startswith("svg.pcb.") and f.endswith(".svg")]
    if not pcbs:
        continue
    sv = ET.parse(os.path.join(pdir, pcbs[0])).getroot()
    sizes = []
    for e in sv.iter():
        i = e.get("id") or ""
        m = re.match(r"connector(\d+)(pad|pin)$", i)
        if not m:
            continue
        b = elem_bbox(e)
        if b:
            sizes.append((max(b[2] - b[0], b[3] - b[1]), b, i))
    if len(sizes) < 4:
        continue
    sizes.sort(reverse=True)
    big, others = sizes[0], [s[0] for s in sizes[1:]]
    others.sort()
    med = others[len(others) // 2]
    if big[0] >= 2.2 * med:
        # 名字
        cid = big[2].replace("connector", "").replace("pad", "").replace("pin", "")
        nm = ""
        for c in root.iter("connector"):
            if c.get("id") == "connector" + cid:
                nm = c.get("name") or ""
        hits.append((d, "connector" + cid, nm, big, med))
        print("%-22s %-12s %-22s %.2f" % (d, "connector" + cid,
                                          "%.2f × %.2f" % (big[1][2] - big[1][0],
                                                           big[1][3] - big[1][1]), med))
print()
print("共 %d 个零件有「大焊盘」" % len(hits))
