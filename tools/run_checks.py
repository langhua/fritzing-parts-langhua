#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fritzing-parts-langhua 一键闸门（A 档 = 全仓；B 档 = 本次改动到的元件）。

用法::

    py -3.13 tools\\run_checks.py                     # 本地：A 档全仓 + B 档（自动找基线）
    py -3.13 tools\\run_checks.py --all-parts         # B 档也扫全仓（会暴露既存 FAIL）
    py -3.13 tools\\run_checks.py --diff-base <rev>   # CI：指定比对基线（PR 的 base / push 的 before）
    py -3.13 tools\\run_checks.py --report <path>     # 报告落盘（默认仓库根 checks_report.md）

闸门清单
--------
A 档（全仓、便宜、今天应全绿）
  G1 文本卫生       tracked 文件：无 BOM / 合法 UTF-8 / 索引里行尾是 LF / 没有把
                    `__pycache__`、`.pyc`、`*_byHand.svg`、`.bak` 之类带进库
  G2 README 一致性  `tools/check_readme_table.py`（部件表 / 两个数量 / 预览拼版数）
  G3 可重生成       每个带 `gen_part.py` 的件：在**临时副本**里重跑生成器，产物必须与仓库
                    里的 svg/fzp **逐字节一致**（改生成器忘了重跑、或产物被手工改过 ⇒ 立刻红）
  G4 fzpz 装箱      `fzpz/*.fzpz` 里的条目必须与 `svg/` 下的源文件**内容一致**
                    （✗ 不比 zip 字节 —— 时间戳会变）；★ 2026-10-13 修：判据 = **svg/ 下有没有
                    唯一同名源** ✓（✗ 原来是“名字带 32 位 hash 就跳过” ✗ —— 本库自己的
                    moduleId 就带 hash ⇒ 那条把**所有本库件**都放过了 ✗ ⇒ 改了源也报绿 ✗）
B 档（只对本次改动到的元件）
  G5 元件闸门       `fzp_check.py` / `schem_check.py` 必须 rc=0（rc 2 = 该件没有这个视图 ⇒ 跳过）                    「改动」= 动了 `svg/<部件>/…`，**或**动了 `fzpz/<部件>.fzpz` 且**载荷真的变了**
                    （只改时间戳 / 重打包不算 ✗ —— 按包内条目反查部件，与 G4 同一套口径 ✓）

判定口径（与兄弟仓一致）
------------------------
* 退出码 0 **且** 输出里没有 FAIL 才算过；**rc 2 = 明确跳过，不算通过**（报告里单独列）。
* `tools/check_deploy.py` 依赖**本机** Fritzing 的 MINE 目录 ⇒ **不进 CI**，只在本机按需跑。

★ 本工具**不能**证明什么（写在这里免得以后误读）
------------------------------------------------
零件在 **Fritzing / Inkscape** 里好不好看、能不能插面包板、颜色与审美是否达标 ——
那是**人眼在 Fritzing 里**的验收，任何脚本都替代不了。
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
PY = sys.executable

TEXT_EXT = (".svg", ".fzp", ".md", ".py", ".txt", ".json", ".yml", ".yaml", ".ipynb",
            ".cmd", ".bat", ".fzb")
JUNK_RE = re.compile(r"(__pycache__/|\.pyc$|^\.venv/|_byHand\.svg$|\.bak$|\.orig$"
                     r"|\.DS_Store$|Thumbs\.db$|~\$)")
# ★ 2026-10-13：`HASH_RE` 已删 ✓ —— “名字里带 32 位 hash”**不是**判据 ✗
#   （本库自己的 moduleId 就带 hash ✓；G4 现在按“svg/ 下有没有唯一同名源”判 ✓）
_DEP_RE = re.compile(r"(ModuleNotFoundError|ImportError)")

# G3 已知例外：**带理由**的允许清单（不是静默跳过 —— 报告里会点名打出来）
GEN_DRIFT_ALLOW = {
    "T-Halow-RJ45": "icon 与生成器产物不同（该件是 T-Halow-RJ45 仓的参考件，"
                    "不进本库预览图/元件箱，见 AGENTS §10）",
    "Capacitor-0402": "入库那份 fzp 的 <description> 写的是 1 / 2，而生成器现在写 "
                      "A generic capacitor（其余字节全同）⇒ 入库产物是旧版/手工版；"
                      "要统一得重生成并提交该件（用户 2026-10-13 定：其它件先不动）",
}

# ★ G5 已知例外：这些件带着**既存**的检查器 FAIL（**不是**本次改动引入的 ✗）——
#   2026-10-15 端子居中推平时，B 档“改动件”口径把它们拉进来判 ⇒ 没被改过的旧账
#   变成了眼前的红 ✗。证据口径（**不许猜** ✓）：用 `git show HEAD:<旧文件>` 取改前那份
#   到临时目录，跑**同一个**检查器 ⇒ rc 与 FAIL 条数与改后**相同**（`ESP-12F` 甚至
#   从 34 减到 33 ✓，因为越界的端子被移回了画布内 ✓）。
#   口径：命中本表 ⇒ **不判 FAIL**，但报告里**点名打出**（不是静默跳过 ✗）。
#   ⇒ 这些件要正式整理时，一条条消掉并把这里删空 ✓。
PART_CHECK_ALLOW = {
    "CH340K": "schem_check 6 项既存 FAIL（pin 缺 class=\"pin\"/connectorname 等；"
              "2026-10-15 核过：改前 6 == 改后 6）",
    "CN3165": "schem_check 1 项既存 FAIL（同上口径：改前 1 == 改后 1）",
    "ESP-12F": "schem_check 33 项既存 FAIL（大部分是 pin 缺 class/connectorname；"
               "2026-10-15 核过：改前 34 ⇒ 改后 33，本次还少 1 条 ✓）",
    "FPC05-2H10PX": "fzp_check 1 项既存 FAIL：缺 icon 视图 svg（老件，icon 从未入库；"
                    "2026-10-15 核过：改前 1 == 改后 1）",
    # 2026-10-17 补散热盘热过孔时改动到的三件老元件（无生成器）。它们的 schem_check
    # FAIL（端点没落外端 / 引线没贴框）是**改前就有**的，与本次（只动 pcb 图层）无关；
    # 证据 = `git show HEAD:<旧文件>` 取回改前那份，跑同一个检查器 ⇒ rc 与 FAIL 行数相同。
    "RT6150AGQW": "schem_check 3 项既存 FAIL（端点未落外端/引线未贴框；"
                  "2026-10-17 核过：改前 3 == 改后 3）",
    "SM5206": "schem_check 4 项既存 FAIL（同上；2026-10-17 核过：改前 4 == 改后 4）",
    "TP4056": "schem_check 3 项既存 FAIL（同上；2026-10-17 核过：改前 3 == 改后 3）",
}


def _out(s=""):
    print(s, flush=True)


def norm(b):
    """入库那份 = LF（git 归一化后的形态）⇒ 工作区是 CRLF（core.autocrlf）不算差异。

    ★ 没有这一步时，G3/G4 会**看平台变脸**：Windows 上"工作区 CRLF 与 zip 里的 CRLF 一起错"
    ⇒ 本机反而报通过 ✗（2026-10-13 CI 的 Linux 栏一眼看穿 ✓）。
    """
    return b.replace(b"\r\n", b"\n")


def sh(args, cwd=None, timeout=600):
    """跑子进程。统一给 UTF-8：Windows 控制台是 GBK，脚本里打 ✓/✗ 会直接崩。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([str(a) for a in args], cwd=str(cwd or ROOT), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, timeout=timeout)
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def git(*args):
    rc, out = sh(["git"] + list(args), timeout=300)
    return out.splitlines() if rc == 0 else []


def part_dirs(with_gen=False, with_fzp=False):
    """真元件目录：`svg/<dir>/`。with_gen = 带 gen_part.py；with_fzp = 带 part*.fzp。"""
    out = []
    for d in sorted((ROOT / "svg").iterdir()):
        if not d.is_dir():
            continue
        if with_gen and not (d / "gen_part.py").exists():
            continue
        if with_fzp and not list(d.glob("part*.fzp")):
            continue
        out.append(d)
    return out


# --------------------------------------------------------------- G1 文本卫生
def gate_text():
    """tracked 文件：无 BOM / 合法 UTF-8 / 索引里行尾 LF / 没带垃圾文件进库。"""
    fails, skips = [], []
    files = [f for f in git("ls-files") if f.strip()]
    if not files:
        return "SKIP", ["不在 git 仓库里（或 git 不可用）⇒ 跳过"], skips
    junk = [f for f in files if JUNK_RE.search(f)]
    if junk:
        fails.append("这些文件不该入库：%s" % ", ".join(junk[:5]))

    bom, bad = [], []
    for f in files:
        p = ROOT / f
        if not (f.lower().endswith(TEXT_EXT) or os.path.basename(f) == ".gitignore"):
            continue
        if not p.is_file():
            continue
        b = p.read_bytes()
        if b.startswith(b"\xef\xbb\xbf"):
            bom.append(f)
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            bad.append(f)
    if bom:
        fails.append("带 BOM（本仓规矩 = UTF-8 无 BOM）：%s" % ", ".join(bom[:5]))
    if bad:
        fails.append("不是合法 UTF-8：%s" % ", ".join(bad[:5]))

    # 索引里的行尾：工作区是 CRLF（core.autocrlf）不影响判据，看的是**入库那份**
    crlf = []
    for line in git("ls-files", "--eol"):
        m = re.match(r"i/(\S+)\s+w/(\S+)\s+(.*)$", line)
        if m and m.group(1) in ("crlf", "mixed"):
            crlf.append(m.group(3))
    if crlf:
        fails.append("入库那份不是 LF：%s" % ", ".join(crlf[:5]))

    detail = ["tracked 文件 %d 个；BOM %d、非 UTF-8 %d、索引非 LF %d、垃圾路径 %d"
              % (len(files), len(bom), len(bad), len(crlf), len(junk))]
    return ("FAIL" if fails else "PASS"), fails + detail, skips


# ------------------------------------------------------------ G2 README 一致性
def gate_readme():
    rc, out = sh([PY, TOOLS / "check_readme_table.py"], timeout=600)
    tail = out.splitlines()[-1] if out else ""
    if rc == 0:
        return "PASS", ["check_readme_table.py rc=0；%s" % tail], []
    if _DEP_RE.search(out):
        return "SKIP", ["本环境缺依赖 ⇒ G2 跳过（%s）" % tail[:100]], []
    return "FAIL", ["check_readme_table.py rc=%d" % rc] + out.splitlines()[-6:], []


# ---------------------------------------------------------- G6 单位口径（全仓）
def gate_units():
    r"""**同一个物理量只许一处定义** ✓（用户 2026-10-13 定 ✓：「总犯这个错误 ⇒ 写入规则」）

    ★ 守什么 ✗：`px` 多长，这个量在库仓曾同时有 **25.4/96 ✗ / 25.4/72 ✓ / 25.4/90 ✗**
      三个值 ⇒ 原理图那套按 90 算 ⇒ **每个 px 声明件的脚位都偏 20%** ✗ ⇒ 用户看到
      「线没接到端点上」✗（而我自己那套判据报 (A)(B)=0 ✗ = 自证 ✗）。
    ★ 判据全在 `tools/check_units.py` 里 ✓（本函数只负责**把它当一个闸门跑** ✓，不另写一份 ✗）。
    """
    rc, out = sh([PY, TOOLS / "check_units.py"], timeout=120)
    if rc == 2:
        return "SKIP", ["本环境 import 不了库仓工具 ⇒ G6 跳过（%s）" % (out or "")[:100]], []
    tail = [l for l in (out or "").splitlines() if l.strip()]
    fails = [l.strip() for l in tail if l.strip().startswith("✗")]
    if rc == 0 and not fails:
        return "PASS", tail[-3:], []
    return "FAIL", (fails or tail[-6:]), []


# ------------------------------------------------------------- G3 可重生成
def gate_regen():
    """在临时副本里重跑每个生成器，产物必须与仓库里的 svg/fzp 逐字节一致。"""
    parts = part_dirs(with_gen=True)
    if not parts:
        return "SKIP", ["没有带 gen_part.py 的元件目录"], []
    tmp = Path(tempfile.mkdtemp(prefix="fpl_regen_"))
    fails, skips, allowed = [], [], []
    try:
        shutil.copytree(ROOT, tmp, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        for d in parts:
            rel = d.relative_to(ROOT)
            rc, out = sh([PY, "gen_part.py"], cwd=tmp / rel, timeout=300)
            if rc != 0:
                if _DEP_RE.search(out):      # 本环境缺依赖 ⇒ 明确跳过（不算通过）
                    skips.append("%s：生成器缺依赖 ⇒ 跳过（%s）"
                                 % (rel.name, (out.splitlines() or [""])[-1][:80]))
                else:
                    fails.append("%s：生成器 rc=%d %s"
                                 % (rel.name, rc, out.splitlines()[-1] if out else ""))
                continue
            a, b = d, tmp / rel
            diff = []
            for f in sorted(a.iterdir()):
                if not f.is_file() or f.suffix.lower() not in (".svg", ".fzp"):
                    continue
                other = b / f.name
                if not other.exists() or norm(f.read_bytes()) != norm(other.read_bytes()):
                    diff.append(f.name)
            if not diff:
                continue
            if rel.name in GEN_DRIFT_ALLOW:
                allowed.append("%s（%s）：%s" % (rel.name, GEN_DRIFT_ALLOW[rel.name],
                                               ", ".join(diff)))
            else:
                fails.append("%s：重跑产物与仓库不一致 -> %s" % (rel.name, ", ".join(diff)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    detail = ["带 gen_part.py 的件 %d 个；逐字节不一致 %d 个；已知例外 %d 个"
              % (len(parts), len(fails), len(allowed))]
    detail += ["已知例外（允许清单，理由在代码里）：" + s for s in allowed]
    return ("FAIL" if fails else "PASS"), fails + detail, skips


# ------------------------------------------------------------- G4 fzpz 装箱
_SVG_IDX = None


def svg_index():
    """basename -> [路径…]（G4 与 B 档**共用**同一套对照口径，别写第二份）。"""
    global _SVG_IDX
    if _SVG_IDX is None:
        idx = {}
        for root, _dirs, files in os.walk(ROOT / "svg"):
            for f in files:
                idx.setdefault(f, []).append(Path(root) / f)
        _SVG_IDX = idx
    return _SVG_IDX


def gate_fzpz():
    idx = svg_index()
    zdir = ROOT / "fzpz"
    if not zdir.is_dir():
        return "SKIP", ["没有 fzpz/ 目录"], []
    fails, compared, miss, extra, ambiguous, orphan = [], 0, [], [], [], []
    for z in sorted(zdir.glob("*.fzpz")):
        # ★★ 判据（2026-10-13 第二版 ✓）：**整包都找不到同名源** ⇒ 外来包 ✓（只提示 ✗ 不判 FAIL ✓）。
        #   ✗ 第一版拿“`svg/<fzpz 名>/` 目录存在吗”判 ✗ ⇒ 把 `WS2812B-5050.fzpz`（源在
        #   `svg/WS2812B/5050/` ✓ 子目录 ✓）、`SHC0420.fzpz` 这些**本库件**也报了外来 ✗
        #   （一次多出 85 条假提示 ✗）⇒ **判据锚错了层** ✗（包 ↔ 文件，不是包 ↔ 目录名 ✓）。
        #   锚在**文件名**上就同时满足两头 ✓：本库件（含子目录布局 ✓）条条对得上 ✓；
        #   真“另存”包（如 `LM393-A3144-HALL-3PINS.fzpz` ✓）条条对不上 ✓。
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            parts = [n for n in names if Path(n).suffix.lower() in (".svg", ".fzp")]
            if parts and not any(os.path.basename(n) in idx for n in parts):
                orphan.append("%s（%d 条）" % (z.name, len(parts)))
                continue
            for n in names:
                if Path(n).suffix.lower() not in (".svg", ".fzp"):
                    extra.append("%s :: %s" % (z.name, n))     # 零件包里不该有别的东西
                    continue
                # ★★ 2026-10-13 修 ✓：判据 = **svg/ 下有没有唯一同名源** ✓
                #   ✗ 原来在这里拿 `HASH_RE` 跳过 ✗ —— 而本库自己的命名规范就是
                #   `<字母><尺寸>_<32位hex>_<n>` ✓ ⇒ 那一条把**所有本库件都放过** ✗
                #   ⇒ “改了源、包没跟着变”照样报绿 ✗（自证 ✓，实测 `Resistor-*.fzpz` 中招 ✓）。
                cand = idx.get(os.path.basename(n))
                if not cand:
                    miss.append("%s :: %s" % (z.name, n))
                    continue
                if len(cand) > 1:
                    ambiguous.append("%s :: %s（svg/ 下有 %d 个同名文件）"
                                     % (z.name, n, len(cand)))
                    continue
                compared += 1
                if norm(cand[0].read_bytes()) != zf.read(n):
                    fails.append("%s :: %s 与入库源文件内容不一致" % (z.name, n))
    fails += ["源文件找不到（包里有别的条目能对上、这一条对不上 ⇒ 包与 svg 不同步 ✗）：" + m
              for m in miss]
    fails += ["同名源不唯一（对账不了 ⇒ 请人工看）：" + m for m in ambiguous]
    fails += ["零件包里不该有非零件条目（跑 tools\\repack_fzpz.py 清）：" + m for m in extra]
    detail = ["比对条目 %d 条；外来包 %d 个（整包都没有同名源 ⇒ 只提示）；条目对不上源 %d 条；"
              "同名源不唯一 %d 条；非零件条目 %d 条"
              % (compared, len(orphan), len(miss), len(ambiguous), len(extra)),
              "口径：与**入库那份**（LF）逐字节比 ✓ —— 工作区 CRLF 不算差异；"
              "zip 载荷本身必须是 LF（否则换平台解出来与 svg/ 不一致 ✗，跑 "
              "`py -3.13 tools\\repack_fzpz.py` 修）"]
    if orphan:
        detail.append("注（外来包，仓库里没有同名源文件 ⇒ 不判它）：" + "；".join(orphan))
    return ("FAIL" if fails else "PASS"), fails + detail, []


# --------------------------------------------------------- G5 元件闸门（B 档）
def git_blob(rev, rel):
    """`git show <rev>:<rel>` 的**原始字节**（二进制安全；sh() 是文本模式，不能用 ✗）。"""
    p = subprocess.run(["git", "show", "%s:%s" % (rev, rel)], cwd=str(ROOT), capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=300)
    return p.stdout if p.returncode == 0 else None


def zip_payload(data):
    """zip 载荷 = {条目名: 归一化字节}；解不开返回 None。

    ★ 只比**载荷** ⇒ 时间戳/重打包变化**不算** ✗（否則一次全仓重打包会把上百个件
    拖进 B 档，把既存 FAIL 变成红 ✗ —— 2026-10-13 实测过）。
    """
    if not data:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return {n: norm(zf.read(n)) for n in zf.namelist()}
    except (OSError, zipfile.BadZipFile):
        return None


def package_part_dirs(rel):
    """`fzpz/X.fzpz` 里装的就是某个件的东西 ⇒ 由**条目名**反查 `svg/<部件>/`。

    改了包、没动源文件时也要查那个件（2026-10-13 用户定）—— 口径与 G4 一致（按 basename 对照）。
    """
    z = ROOT / rel
    if not z.exists():
        return set()
    try:
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
    except (OSError, zipfile.BadZipFile):
        return set()
    idx, out = svg_index(), set()
    for n in names:
        for c in idx.get(os.path.basename(n), []):
            out.add(c.parent.name)
    return out


def changed_part_dirs(base):
    paths = []
    if base:
        paths += git("diff", "--name-only", base, "HEAD")
    paths += git("diff", "--name-only")              # 工作区 vs 索引
    paths += git("diff", "--name-only", "--cached")   # 索引 vs HEAD
    paths += git("ls-files", "--others", "--exclude-standard")
    dirs = set()
    for p in paths:
        p = p.strip()
        if p.startswith("svg/") and p.count("/") >= 2:
            dirs.add(p.split("/")[1])
        elif p.startswith("fzpz/") and p.endswith(".fzpz"):
            new = zip_payload((ROOT / p).read_bytes()) if (ROOT / p).is_file() else None
            old = zip_payload(git_blob(base or "HEAD", p))
            if new != old:                           # 载荷真变了 ⇒ 那个件也要查
                dirs |= package_part_dirs(p)
    # ★ 判据 = 「**这个目录里有 `part.*.fzp`**」✓（= 它到底是不是一个**部件** ✓）——
    #   ✗ 不能只看「`svg/<名>/` 是个目录」✗：`svg/_assets/` 是**素材目录** ✓
    #   （外部图形 + 它的许可文件 ✓，AGENTS §4 ✓），拿它去跑 `fzp_check` 会报
    #   「没找到 .fzp」✗ 并被记成 G5 FAIL ✗（2026-10-13 实测中招 ✓：新加原理图素材后红了一条 ✓）。
    #   与全仓那支 `part_dirs(with_fzp=True)` **同一把尺子** ✓（一处判据两处用 ✓）。
    return sorted(d for d in dirs if any((ROOT / "svg" / d).glob("part.*.fzp")))


def gate_parts(base, all_parts):
    if all_parts:
        targets, why = [d.name for d in part_dirs(with_fzp=True)], "--all-parts（全仓）"
    else:
        targets = changed_part_dirs(base)
        why = "本次改动到的件（基线 %s）" % (base or "无 ⇒ 只看未提交改动")
    if not targets:
        return "SKIP", ["没有改动到的元件目录 ⇒ B 档跳过（要看全仓就加 --all-parts）"], []

    fails, skips, passed = [], [], []
    allowed = []

    def _add_fail(msg, name):
        """★ 命中 `PART_CHECK_ALLOW` ⇒ 进**允许清单**（报告里点名打出 ✓），不判 FAIL ✓。"""
        if name in PART_CHECK_ALLOW:
            allowed.append("%s：%s（%s）" % (name, msg, PART_CHECK_ALLOW[name]))
        else:
            fails.append("%s：%s" % (name, msg))

    for name in targets:
        d = ROOT / "svg" / name
        if not d.is_dir():
            continue
        rc, out = sh([PY, TOOLS / "fzp_check.py", d], timeout=300)
        last = (out.splitlines() or [""])[-1]
        if rc == 1:
            _add_fail("fzp_check：%s" % last, name)
        elif rc == 0:
            passed.append("%s / fzp_check rc=0" % name)
        elif re.search(r"(ModuleNotFoundError|ImportError)", out):
            skips.append("%s / fzp_check 本环境缺依赖 ⇒ 跳过（%s）"
                         % (name, out.splitlines()[-1][:80]))
        else:
            _add_fail("fzp_check rc=%d：%s" % (rc, last), name)
        if list(d.glob("svg.schematic.*_schematic.svg")):
            rc, out = sh([PY, TOOLS / "schem_check.py", d], timeout=300)
            last = (out.splitlines() or [""])[-1]
            if rc == 1:
                _add_fail("schem_check：%s" % last, name)
            elif rc == 2:
                skips.append("%s / schem_check rc=2（跳过/提示）：%s" % (name, last[:80]))
            elif rc == 0:
                passed.append("%s / schem_check rc=0" % name)
            elif re.search(r"(ModuleNotFoundError|ImportError)", out):
                skips.append("%s / schem_check 本环境缺依赖 ⇒ 跳过" % name)
            else:
                _add_fail("schem_check rc=%d：%s" % (rc, last), name)
    detail = ["B 档范围 = %s；共 %d 个件" % (why, len(targets))]
    detail += ["已过：" + s for s in passed]
    detail += ["已知例外（允许清单，理由在代码里）：" + s for s in allowed]
    return ("FAIL" if fails else "PASS"), fails + detail, skips


# ------------------------------------------------------------------ 主流程
def main(argv):
    ap = argparse.ArgumentParser(description="fritzing-parts-langhua 一键闸门")
    ap.add_argument("--diff-base", default=os.environ.get("DIFF_BASE", ""),
                    help="B 档比对基线（CI：PR 的 base sha / push 的 before）")
    ap.add_argument("--all-parts", action="store_true", help="B 档扫全仓（会暴露既存 FAIL）")
    ap.add_argument("--report", default=str(ROOT / "checks_report.md"))
    args = ap.parse_args(argv)

    base = args.diff_base.strip()
    if base and set(base) == {"0"}:          # push 的首个提交：before 全是 0
        base = ""
    if not base and not args.all_parts:
        base = "HEAD~1" if git("rev-parse", "--verify", "HEAD~1") else ""

    _out("fritzing-parts-langhua checks  (%s)" % time.strftime("%Y-%m-%d %H:%M:%S"))
    _out("python %s | 平台 %s" % (sys.version.split()[0], sys.platform))
    _out("仓库 %s" % ROOT)
    try:
        import cairosvg  # noqa: F401
        dep = "cairosvg 可用"
    except Exception as e:                    # noqa: BLE001
        dep = "cairosvg **不可用**（%s）⇒ 依赖它的闸门会明确跳过" % type(e).__name__
    _out("依赖：%s\n" % dep)

    gates = [("G1 文本卫生（全仓）", lambda: gate_text()),
             ("G2 README 一致性（全仓）", lambda: gate_readme()),
             ("G3 生成器可重生成（全仓）", lambda: gate_regen()),
             ("G4 fzpz 装箱一致（全仓）", lambda: gate_fzpz()),
             ("G5 元件闸门（改动件）", lambda: gate_parts(base, args.all_parts)),
             ("G6 单位口径（全仓）", lambda: gate_units())]

    rows, hard = [], []
    for title, fn in gates:
        t0 = time.time()
        try:
            state, detail, skips = fn()
        except Exception as e:                # noqa: BLE001
            state, detail, skips = "FAIL", ["闸门自己抛异常：%r" % (e,)], []
        dt = time.time() - t0
        rows.append((title, state, dt, detail, skips))
        _out("%-4s %-26s %5.1fs" % (state, title, dt))
        for d in detail:
            _out("       %s" % d)
        for s in skips[:6]:
            _out("       跳过: %s" % s)
        if state == "FAIL":
            hard.append(title)

    n_pass = sum(1 for r in rows if r[1] == "PASS")
    n_skip = sum(1 for r in rows if r[1] == "SKIP")
    n_fail = len(hard)
    _out("\n=== %d 过 / %d 跳过 / %d 不合格 ===" % (n_pass, n_skip, n_fail))
    _out("★ 本工具不能证明：零件在 Fritzing / Inkscape 里的观感与可插性 —— 那要人眼验收；")
    _out("  `tools/check_deploy.py` 依赖本机 Fritzing 目录，不在闸门里。")

    try:
        lines = ["# checks 报告（fritzing-parts-langhua）", "",
                 "跑的时间：%s ｜ python %s ｜ 平台 %s" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                                     sys.version.split()[0], sys.platform),
                 "结果：**%d 过 / %d 跳过 / %d 不合格**" % (n_pass, n_skip, n_fail), "",
                 "| 闸门 | 结果 | 用时 |", "|---|---|---|"]
        for title, state, dt, _d, _s in rows:
            lines.append("| %s | %s | %.1fs |" % (title, state, dt))
        lines += ["", "## 明细", ""]
        for title, state, _dt, detail, skips in rows:
            lines.append("### %s -> %s" % (title, state))
            lines += ["- " + d for d in detail] or ["- （无）"]
            lines += ["- 跳过：%s" % s for s in skips]
            lines.append("")
        lines += ["## 口径与边界", "",
                  "- rc 0 且无 FAIL 才算过；`rc 2` = **明确跳过，不算通过**（上面单独列了）。",
                  "- `tools/check_deploy.py`（要用本机 Fritzing 的 MINE 目录）**不在 CI 里**。",
                  "- ★ 本工具**不能**证明零件在 Fritzing / Inkscape 里的观感、能不能插面包板 —— "
                  "那是人眼验收。", ""]
        Path(args.report).write_text("\n".join(lines), encoding="utf-8", newline="\n")
        _out("报告 -> %s" % args.report)
    except OSError as e:
        _out("报告写入失败：%r" % (e,))

    return 1 if hard else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:                                        # noqa: BLE001
            pass
    sys.exit(main(sys.argv[1:]))
