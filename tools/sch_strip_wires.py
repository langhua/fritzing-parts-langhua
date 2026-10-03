# -*- coding: utf-8 -*-
r"""★★ 剥掉 sketch 的**原理图导线** ⇒ 「干净画布」✓（2026-10-03 入库 ✓）

为什么要有它 ✓：项目侧的布线器 `gen_schematic_wires.py` 要的输入是**只有摆位、没有导线**的
画布 ✓（它自己会画线 ✓）。而**用户手里的图**总是带着他手画的线 ✗ ⇒ 想拿"**用户的摆位**"去
喂布线器（看它在**人调过的摆位**上画得怎么样 ✓），就得先把线剥掉 ⇒ 本工具 ✓。

★ 只剥**原理图**那一条 ✗（`<schematicView>` ✓），**不删实例本身** ✓：
  本板有些导线实例**同时**带面包板/PCB 视图 ✓（`<connect layer="breadboardWire"/>` /
  `copper0trace` ✓）⇒ 整条实例删掉会把**面包板跳线和 PCB 走线一起削掉** ✗✗（实测踩过 ✓）。
★ 同时删掉零件上指向导线的 `<connect … layer="schematicTrace"/>` ✓
  （线都没了还留着 ⇒ 就是"接在不存在的东西上" ✗ ⇒ 网表/布线器会报 ✗；实测 69 条 ✓）。

用法 ✓：

    py -3.13 sch_strip_wires.py <in.fzz> <out.fzz> [--dry]

库用法 ✓：

    from sch_strip_wires import strip_text
    new_text, n_view, n_con = strip_text(old_text)      # 纯文本 → 纯文本 ✓（可测 ✓）
    from sch_strip_wires import strip_file
    strip_file("a.fzz", "clean.fzz")                    # 文件 → 文件 ✓
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

RE_INST = re.compile(r"(?s)<instance\b.*?</instance>")
RE_VIEW = re.compile(r"(?s)\s*<schematicView\b.*?</schematicView>")
RE_CON = re.compile(r'\s*<connect\b[^>]*layer="schematicTrace"[^>]*/>')


def strip_text(text):
    """→ `(新文本, 剥掉几个视图, 删掉几条连接)` ✓ —— ★ 纯函数 ✓（好测 ✓、不碰文件 ✓）"""
    n = [0, 0]

    def one(m):
        blk = m.group(0)
        if not re.search(r'moduleIdRef="Wire', blk):
            return blk
        new, k = RE_VIEW.subn("", blk)
        n[0] += k
        return new

    text = RE_INST.sub(one, text)
    text, n[1] = RE_CON.subn("", text)
    return text, n[0], n[1]


def load(path):
    """→ `(文本, 包, .fz 名)` ✓（`.fz` 时后两个为 None ✓）—— 魔数判 zip ✓ 别看扩展名 ✗"""
    path = str(path)
    with open(path, "rb") as fh:
        if fh.read(2) == b"PK":
            z = zipfile.ZipFile(path)
            name = [n for n in z.namelist() if n.endswith(".fz")][0]
            return z.read(name).decode("utf-8"), z, name
    return open(path, encoding="utf-8").read(), None, None


def save(path, text, pack, name):
    """★ 绝不"边读边写同一个 zip" ✗ ⇒ 先写临时文件 ✓；收 `str` 也收 `Path` ✓"""
    path = str(path)
    tmp = path + ".tmp"
    if pack is None:
        open(tmp, "w", encoding="utf-8").write(text)
    else:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
            for n in pack.namelist():
                zo.writestr(n, text.encode("utf-8") if n == name else pack.read(n))
        pack.close()
    os.replace(tmp, path)


def strip_file(src, out):
    """→ `dict(views=…, connects=…, out=…)` ✓；★ 剥完**先解析** ✓，解析不了**不写** ✗"""
    text, pack, name = load(src)
    new, n_view, n_con = strip_text(text)
    try:
        ET.fromstring(new)
    except Exception as ex:
        raise SystemExit("✗✗ 剥完的 XML 解析不了（%s）⇒ **不写文件** ✗" % ex)
    save(out, new, pack, name)
    return dict(views=n_view, connects=n_con, out=str(out))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print("用法: py -3.13 sch_strip_wires.py <in.fzz> <out.fzz> [--dry]")
        return 2
    src, out = args[0], args[1]
    text, pack, name = load(src)
    new, n_view, n_con = strip_text(text)
    print("剥掉 `<schematicView>` %d 处 ✓｜删掉指向导线的 `<connect>` %d 条 ✓" % (n_view, n_con))
    try:
        ET.fromstring(new)
        print("XML 可解析 ✓")
    except Exception as ex:
        print("✗✗ 剥完解析不了（%s）⇒ 不写文件 ✗" % ex)
        return 2
    if "--dry" in argv:
        print("（--dry ⇒ 不写 ✓）")
        return 0
    save(out, new, pack, name)
    print("写入 %s ✓" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
