# -*- coding: utf-8 -*-
r"""读**项目数据模块** —— ★ 通用工具取"项目专有数据"的**唯一实现** ✓（2026-09-30 ✓）

★ 为什么要有它 ✗✓：通用工具（`check_netlist.py` / `bb_route4.py` …）**不该写着某块板的
  网名、颜色、期望网表** ✗ —— 那些是**项目数据** ✓。⇒ 工具只收一个路径：
      `--nets=<项目数据.py>`（缺省 = **当前目录**的 `pixel_nets.py` ✓ ⇒ 老命令照用 ✓）
  文件里备好工具要的那几张表（`NETS` / `EXPECT` / `COLOR` ✓…）。
  例：`hardware/pixel/pixel_nets.py` ✓（本仓旁边那个项目仓里 ✓）。

★ 读法 ✓：**`importlib` 按路径导入** ✓ —— 不 `exec` 字符串 ✗、不把项目目录塞进
  `sys.path` ✗（后者会把项目目录顶到最前 ✗，正是 `toolpaths.py` 记的那次踩坑 ✓）。
★ **不静默退化** ✗：文件找不到、或缺表 ⇒ **报错退出** ✗（不许"读不到 = 当空表" ✗）。
"""
import importlib.util
import os

DEFAULT = "pixel_nets.py"


def load(path=None, need=()):
    """按路径导入项目数据模块 ✓；`need` 里的名字缺一个就报错退出 ✗"""
    p = path or os.path.join(os.getcwd(), DEFAULT)
    if not os.path.isfile(p):
        raise SystemExit("✗ 找不到项目数据文件：%s\n"
                         "  用法：--nets=<项目数据.py>（缺省 = 当前目录的 %s ✓）" % (p, DEFAULT))
    spec = importlib.util.spec_from_file_location("proj_data", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    miss = [n for n in need if not hasattr(mod, n)]
    if miss:
        raise SystemExit("✗ 项目数据文件 %s 里缺：%s ✗" % (p, ", ".join(miss)))
    return mod


def strip_argv(argv):
    """把 `--nets=<file>` 从参数表里摘出来 ✓ ⇒ 返回 `(file 或 None, 其余参数 ✓)`

    ★ 位置上必须**先摘再给位置参数** ✗：两个工具都用 `argv[0]/argv[1]` 当
      "输入 fzz / 输出" ✓ ⇒ 不摘掉 `--nets=…` 会把位置参数错位 ✗。
    """
    val = next((a.split("=", 1)[1] for a in argv if a.startswith("--nets=")), None)
    return val, [a for a in argv if not a.startswith("--nets=")]
