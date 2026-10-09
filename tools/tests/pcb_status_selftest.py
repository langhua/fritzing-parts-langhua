# -*- coding: utf-8 -*-
r"""pcb_status_selftest：`tools\pcb_status.py`（**Fritzing 状态栏仿真引擎** ✓）的单元自测 ✓

★ 为什么要有它 ✗✓：这把尺子的**全部价值在于"照源码算"** ✓ ⇒ 必须用**不依赖任何项目文件**的
  合成 sketch 把它**逐条钉住** ✓ —— 否则它就是"自己说自己对" ✗（本项目吃过这个亏 ✓）。

七段 ✓（**双向**都要过 ✓ —— 只会"放行"的尺子等于没尺子 ✗）：
  ① 两个件 + 一根线 ⇒ **M=1 / K=0** ✓（= `Routing completed` ✓）
  ② **把线删掉** ⇒ M=0 ✓ 且**两片都被丢弃**（每片只剩 1 只脚 ✓）= `sketchwidget.cpp:7013` ✓
     —— ★ 这一段同时把"**单刀切开一张网，状态栏不会报未布**"钉成**事实** ✓（见引擎头 ② ✓）
  ③ 单脚网 ⇒ 不计数 ✓（同一处源码 ✓）
  ④ **跨视图 glue**：`pcbView` 里脚↔面包板孔（`layer=breadboardbreadboard` ✓）
     ⇒ **两张网被并成一张**（M=2→1 ✓）、且 **K=1** ✓（铜碎成 2 块 ✓）
     ⇒ 这就是 v81「7 中的 5 … 2 个连接仍然需要布线」的机理 ✓
  ⑤ ★ 同一个 glue 放在 **`breadboardView`** 里 ⇒ **K=0** ✓（面包板在那儿**可见** ✓ ⇒
     `collectBreadboard` 会补边 ✓）—— 与④对照即锁死 `setEverVisible` 这条分水岭 ✓
  ⑥ 过孔 ⇒ 两层**算一个节点** ✓、把上下层的线接上 ⇒ K=0 ✓
  ⑦ **空网/无名件**不吃惊 ✓（没有脚的组不计数 ✓）
  ⑧ ★ **命令行** ✓（2026-10-10 补 ✓）：`tools\pcb_status.py` 的**退出码** 0/1/2 ✓ ——
     不给文件 ⇒ `2` ✓；A/B/C 全过 ⇒ `0` ✓；网表里有网没"成型" ⇒ `1` ✓（`--sens` 同闸门 ✓）

用法：`py -X utf8 tools\tests\pcb_status_selftest.py` ⇒ 全过 exit 0 ✓
"""
import contextlib
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pcb_status as ST                                        # noqa: E402

ok = True


def chk(name, cond, extra=""):
    global ok
    print("  %s %s %s" % ("✓" if cond else "✗", name, extra))
    if not cond:
        ok = False


EMPTY_MODEL = dict(pads=[], traces=[], vias=[], holes=[])


def sketch(instances):
    """合成一份 .fzz ✓（zip 里一个 `.fz` ✓）；`instances` = `<instance>` 块文本 ✓"""
    tmp = tempfile.NamedTemporaryFile(suffix=".fzz", delete=False)
    tmp.close()
    with zipfile.ZipFile(tmp.name, "w") as z:
        z.writestr("t.fz", '<?xml version="1.0"?>\n<module><sketch>\n%s\n</sketch></module>'
                   % "\n".join(instances))
    return tmp.name


def part(mi, mod, view, conns, title=None, path=None):
    """一个件 ✓；`conns` = `[(connectorId, layer, [(tcid, tmi)])]` ✓ → 实例块文本 ✓

    ★ 必须**逐行**写（`INST_RE` 是按"同缩进配对"切的 ✓，`</instance>` 得独占一行 ✓）。
    ★ 线的 `path` 用**真核心路径串** ✓ ⇒ `pcb_status.CORE_BUS` 才认得出"线身是一根导体" ✓。
    """
    if path is None:
        if mod == "WireModuleID":
            path = ":/resources/parts/core/wire.fzp"
        elif mod == "ViaModuleID":
            path = ":/resources/parts/core/via.fzp"
        else:
            path = "/dev/null.fzp"
    body = []
    for cid, layer, decl in conns:
        ds = "".join('<connect connectorId="%s" modelIndex="%s" layer="%s"/>' % (t, m, layer)
                     for (t, m) in decl)
        body.append('        <connector connectorId="%s" layer="%s">\n'
                    '          <geometry x="0" y="0"/>\n'
                    "          <connects>%s</connects>\n"
                    "        </connector>" % (cid, layer, ds))
    return ('<instance moduleIdRef="%s" modelIndex="%s" path="%s">\n'
            "  <title>%s</title>\n"
            "  <views>\n"
            '    <%s layer="L">\n'
            '      <geometry z="1" x="0" y="0" wireFlags="%d"/>\n'
            "      <connectors>\n%s\n      </connectors>\n"
            "    </%s>\n"
            "  </views>\n"
            "</instance>"
            % (mod, mi, path, title or ("P" + mi), view, ST.TRACE_FLAG[view],
               "\n".join(body), view))


def status(instances, expect=None, view="pcbView", drop=None):
    p = sketch(instances)
    try:
        st = ST.Status(p, expect or {}, model=EMPTY_MODEL)
        return st, st.view(view, drop)
    finally:
        os.remove(p)


TWO_PARTS = [part("1", "SomePartModuleID", "pcbView", [("connector0", "copper0", [("connector0", "5")])]),
             part("9", "SomePartModuleID", "pcbView", [("connector0", "copper0", [("connector1", "5")])]),
             part("5", "WireModuleID", "pcbView", [("connector0", "copper0trace", [("connector0", "1")]),
                                                   ("connector1", "copper0trace", [("connector0", "9")])])]

print("== ① 两个件 + 一根线 ⇒ M=1 / K=0 ✓ ==")
_st, r = status(TWO_PARTS)
chk("M = 1 ✓", r["M"] == 1, "M=%d" % r["M"])
chk("K = 0 ✓（状态栏会说 `Routing completed` ✓）", r["K"] == 0, "K=%d" % r["K"])
chk("文案 = `Routing completed` ✓", _st.text("pcbView") == "Routing completed", _st.text("pcbView"))

print("\n== ② **把线删掉** ⇒ 两片都被丢弃（每片 1 只脚）⇒ M=0、文案**没变** ✓ ×（Fritzing 口径 ✓）==")
_st2, r2 = status(TWO_PARTS, drop="5")
chk("M = 0 ✓（两张都被 `partConnectorItems.count() <= 1` 跳过 ✓）", r2["M"] == 0, "M=%d" % r2["M"])
chk("K = 0 ✓（所以仍然不报「未布」 ✗ —— 这是 Fritzing 自身口径 ✓）", r2["K"] == 0, "K=%d" % r2["K"])
chk("有脚却被丢掉的组 = 2 ✓", len(r2["dropped_with_parts"]) == 2,
    str(len(r2["dropped_with_parts"])))
chk("文案仍是 `Routing completed` ✓（= 用户看到的「删了也还是布线完成」 ✓）",
    _st2.text("pcbView") == "Routing completed", _st2.text("pcbView"))

print("\n== ③ 单脚网 ⇒ 不计数 ✓ ==")
_st3, r3 = status([part("1", "SomePartModuleID", "pcbView", [("connector0", "copper0", [])])])
chk("M = 0 ✓", r3["M"] == 0, "M=%d" % r3["M"])

def temp_fzp(buses):
    """合成一个件的 `.fzp` ✓（只为让 `fzp_buses` 有文件可读 ✓）⇒ 路径串 ✓"""
    t = tempfile.NamedTemporaryFile(suffix=".fzp", delete=False, mode="w", encoding="utf-8")
    t.write('<?xml version="1.0"?>\n<module moduleId="BB"><buses>%s</buses></module>'
            % "".join('<bus id="b%d">%s</bus>'
                      % (i, "".join('<nodeMember connectorId="%s"/>' % c for c in grp))
                      for i, grp in enumerate(buses)))
    t.close()
    return t.name


GLUE = None


def glue_sketch(view):
    """脚↔孔（跨视图记录 ✓）＋ 孔↔孔 同 bus ✓ ⇒ 一张网、两块铜 ✓"""
    fzp = temp_fzp([["pin1A", "pin1B"]])
    return [part("5785", "Breadboard-RSR03MB102-ModuleID", view,
                 [("pin1A", "breadboardbreadboard", []), ("pin1B", "breadboardbreadboard", [])],
                 title="BB", path=fzp),
            part("1", "SomePartModuleID", view,
                 [("connector0", "copper0", [("pin1A", "5785")])], title="A"),
            part("2", "SomePartModuleID", view,
                 [("connector0", "copper0", [("pin1B", "5785")])], title="B"),
            part("5", "WireModuleID", view,
                 [("connector0", "copper0trace", [("connector0", "1")]), ("connector1", "copper0trace", [])])]


print("\n== ④ 跨视图 glue（脚↔孔，在 `pcbView`）⇒ 并网 + K=1 ✓ ==")
_st4, r4 = status(glue_sketch("pcbView"))
chk("M = 1 ✓（A、B 的脚被**并成一张网** ✗）", r4["M"] == 1, "M=%d" % r4["M"])
chk("K = 1 ✓（铜其实只连着 A ⇒ 碎成 2 块 ⇒ 报「1 条未布」 ✗）", r4["K"] == 1, "K=%d" % r4["K"])
chk("文案含 `1 connector(s) still to be routed` ✓",
    "1 connector(s) still to be routed" in _st4.text("pcbView"), _st4.text("pcbView"))

print("\n== ⑤ 同一个 glue 放到 `breadboardView` ⇒ K=0 ✓（面包板在那儿可见 ✓）==")
_st5, r5 = status(glue_sketch("breadboardView"), view="breadboardView")
chk("M = 1 ✓（一样并网 ✓）", r5["M"] == 1, "M=%d" % r5["M"])
chk("K = 0 ✓（`collectBreadboard` 补了边 ✓ —— 这就是两条视图的**分水岭** ✓）", r5["K"] == 0,
    "K=%d" % r5["K"])

VIA = [part("1", "SomePartModuleID", "pcbView", [("connector0", "copper0", [("connector0", "6")])]),
       part("9", "SomePartModuleID", "pcbView", [("connector0", "copper0", [("connector1", "8")])]),
       part("7", "ViaModuleID", "pcbView", [("connector0", "copper0", [])]),
       part("6", "WireModuleID", "pcbView", [("connector0", "copper0trace", [("connector0", "1")]),
                                             ("connector1", "copper0trace", [("connector0", "7")])]),
       part("8", "WireModuleID", "pcbView", [("connector0", "copper1trace", [("connector0", "7")]),
                                             ("connector1", "copper1trace", [("connector0", "9")])])]
print("\n== ⑥ 过孔（两层 ⇒ 一个节点 ✓）＝ 线身的一站 ✓（`pad→线→过孔→线→pad` ✓）==")
_st6, r6 = status(VIA)
chk("M = 1 ✓", r6["M"] == 1, "M=%d" % r6["M"])
chk("K = 0 ✓（换层不改「还剩几条」 ✓）", r6["K"] == 0, "K=%d" % r6["K"])

print("\n== ⑦ 没有脚的空组不吃惊 ✓ ==")
_st7, r7 = status([part("5", "WireModuleID", "pcbView", [("connector0", "copper0trace", []),
                                                         ("connector1", "copper0trace", [])])])
chk("M = 0 ✓、无异常 ✓", r7["M"] == 0, "M=%d" % r7["M"])

print("\n== ⑧ 命令行 ✓（退出码 0 / 1 / 2 ✓）==")


def cli(argv):
    """跑 `ST.main` ✓ 并把 stdout 收起来 ✓（免得把用法整篇刷进自测输出 ✗）"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ST.main(argv)
    return rc, buf.getvalue()


def part3(mi, mod, conns, title=None, path=None):
    """一个件**同时出现在三个视图里** ✓ —— `⑧` 要考"每张网在**每个视图**里都成型" ✓"""
    if path is None:
        path = (":/resources/parts/core/wire.fzp" if mod == "WireModuleID"
                else "/dev/null.fzp")
    body = []
    for cid, layer, decl in conns:
        ds = "".join('<connect connectorId="%s" modelIndex="%s" layer="%s"/>' % (t, m, layer)
                     for (t, m) in decl)
        body.append('        <connector connectorId="%s" layer="%s">\n'
                    '          <geometry x="0" y="0"/>\n'
                    "          <connects>%s</connects>\n"
                    "        </connector>" % (cid, layer, ds))
    vs = "".join('    <%s layer="L">\n      <geometry z="1" x="0" y="0" wireFlags="%d"/>\n'
                 "      <connectors>\n%s\n      </connectors>\n    </%s>\n"
                 % (v, ST.TRACE_FLAG[v], "\n".join(body), v) for v in ST.VIEWS)
    return ('<instance moduleIdRef="%s" modelIndex="%s" path="%s">\n  <title>%s</title>\n'
            "  <views>\n%s  </views>\n</instance>"
            % (mod, mi, path, title or ("P" + mi), vs))


_rc, _out = cli([])
chk("不给文件 ⇒ exit 2 ✓ 且打印用法 ✓", _rc == 2 and "## 命令行" in _out, "rc=%d" % _rc)

_NET = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8")
_NET.write("# 合成网表 ✓\nEXPECT = {'N': {'P1.connector0', 'P9.connector0'}}\n")
_NET.close()
_3V = [part3("1", "SomePartModuleID", [("connector0", "copper0", [("connector0", "5")])]),
       part3("9", "SomePartModuleID", [("connector0", "copper0", [("connector1", "5")])]),
       part3("5", "WireModuleID", [("connector0", "copper0trace", [("connector0", "1")]),
                                   ("connector1", "copper0trace", [("connector0", "9")])])]
_f1 = sketch(_3V)
_f2 = sketch([part3("1", "SomePartModuleID", [("connector0", "copper0", [])])])
try:
    _rc, _out = cli([_f1, "--nets=" + _NET.name])
    chk("合格件 ⇒ exit 0 ✓", _rc == 0, "rc=%d" % _rc)
    chk("逐视图 M/K 都印出来 ✓", "M=" in _out and "K=" in _out, "")
    _rc, _ = cli([_f1, "--nets=" + _NET.name, "--sens"])
    chk("`--sens` 同一套闸门 ⇒ exit 0 ✓", _rc == 0, "rc=%d" % _rc)
    _rc, _out = cli([_f2, "--nets=" + _NET.name])
    chk("★ 网表里的网没\"成型\" ⇒ exit 1 ✓（A 条 ✓）", _rc == 1, "rc=%d" % _rc)
    chk("报出 A 条 ✓", "A " in _out, "")
finally:
    for _p in (_f1, _f2, _NET.name):
        os.remove(_p)

print("\n⇒ %s" % ("✓ 全过" if ok else "✗ 有不过"))
sys.exit(0 if ok else 1)
