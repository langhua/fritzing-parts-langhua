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
                    （✗ 不比 zip 字节 —— 时间戳会变；名字带 32 位 hash 的条目是 Fritzing
                    "另存"产物、仓库没有同名源 ⇒ **计数后跳过**，不静默）
B 档（只对本次改动到的元件）
  G5 元件闸门       `fzp_check.py` / `schem_check.py` 必须 rc=0（rc 2 = 该件没有这个视图 ⇒ 跳过）

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
HASH_RE = re.compile(r"_[0-9a-f]{32}_")
_DEP_RE = re.compile(r"(ModuleNotFoundError|ImportError)")

# G3 已知例外：**带理由**的允许清单（不是静默跳过 —— 报告里会点名打出来）
GEN_DRIFT_ALLOW = {
    "T-Halow-RJ45": "icon 与生成器产物不同（该件是 T-Halow-RJ45 仓的参考件，"
                    "不进本库预览图/元件箱，见 AGENTS §10）",
    "Capacitor-0402": "入库那份 fzp 的 <description> 写的是 1 / 2，而生成器现在写 "
                      "A generic capacitor（其余字节全同）⇒ 入库产物是旧版/手工版；"
                      "要统一得重生成并提交该件（用户 2026-10-13 定：其它件先不动）",
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
def gate_fzpz():
    idx = {}
    for root, _dirs, files in os.walk(ROOT / "svg"):
        for f in files:
            idx.setdefault(f, []).append(Path(root) / f)
    zdir = ROOT / "fzpz"
    if not zdir.is_dir():
        return "SKIP", ["没有 fzpz/ 目录"], []
    fails, skipped_hash, compared, miss, extra = [], 0, 0, [], []
    for z in sorted(zdir.glob("*.fzpz")):
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if Path(n).suffix.lower() not in (".svg", ".fzp"):
                    extra.append("%s :: %s" % (z.name, n))     # 零件包里不该有别的东西
                    continue
                if HASH_RE.search(os.path.basename(n)):
                    skipped_hash += 1          # Fritzing "另存"命名，仓库没有同名源
                    continue
                cand = idx.get(os.path.basename(n))
                if not cand:
                    miss.append("%s :: %s" % (z.name, n))
                    continue
                compared += 1
                if not any(norm(c.read_bytes()) == zf.read(n) for c in cand):
                    fails.append("%s :: %s 与入库源文件内容不一致" % (z.name, n))
    fails += ["源文件找不到：" + m for m in miss]
    fails += ["零件包里不该有非零件条目（跑 tools\\repack_fzpz.py 清）：" + m for m in extra]
    detail = ["比对条目 %d 条；跳过（名字带 hash = Fritzing 另存）%d 条；找不到源 %d 条；非零件条目 %d 条"
              % (compared, skipped_hash, len(miss), len(extra)),
              "口径：与**入库那份**（LF）逐字节比 ✓ —— 工作区 CRLF 不算差异；"
              "zip 载荷本身必须是 LF（否则换平台解出来与 svg/ 不一致 ✗，跑 "
              "`py -3.13 tools\\repack_fzpz.py` 修）"]
    return ("FAIL" if fails else "PASS"), fails + detail, []


# --------------------------------------------------------- G5 元件闸门（B 档）
def changed_part_dirs(base):
    paths = []
    if base:
        paths += git("diff", "--name-only", base, "HEAD")
    paths += git("diff", "--name-only")             # 工作区 vs 索引
    paths += git("diff", "--name-only", "--cached")  # 索引 vs HEAD
    paths += git("ls-files", "--others", "--exclude-standard")
    dirs = set()
    for p in paths:
        p = p.strip()
        if p.startswith("svg/") and p.count("/") >= 2:
            dirs.add((ROOT / "svg" / p.split("/")[1]).name)
    return sorted(dirs)


def gate_parts(base, all_parts):
    if all_parts:
        targets, why = [d.name for d in part_dirs(with_fzp=True)], "--all-parts（全仓）"
    else:
        targets = changed_part_dirs(base)
        why = "本次改动到的件（基线 %s）" % (base or "无 ⇒ 只看未提交改动")
    if not targets:
        return "SKIP", ["没有改动到的元件目录 ⇒ B 档跳过（要看全仓就加 --all-parts）"], []

    fails, skips, passed = [], [], []
    for name in targets:
        d = ROOT / "svg" / name
        if not d.is_dir():
            continue
        rc, out = sh([PY, TOOLS / "fzp_check.py", d], timeout=300)
        last = (out.splitlines() or [""])[-1]
        if rc == 1:
            fails.append("%s / fzp_check：%s" % (name, last))
        elif rc == 0:
            passed.append("%s / fzp_check rc=0" % name)
        elif re.search(r"(ModuleNotFoundError|ImportError)", out):
            skips.append("%s / fzp_check 本环境缺依赖 ⇒ 跳过（%s）"
                         % (name, out.splitlines()[-1][:80]))
        else:
            fails.append("%s / fzp_check rc=%d：%s" % (name, rc, last))
        if list(d.glob("svg.schematic.*_schematic.svg")):
            rc, out = sh([PY, TOOLS / "schem_check.py", d], timeout=300)
            last = (out.splitlines() or [""])[-1]
            if rc == 1:
                fails.append("%s / schem_check：%s" % (name, last))
            elif rc == 2:
                skips.append("%s / schem_check rc=2（跳过/提示）：%s" % (name, last[:80]))
            elif rc == 0:
                passed.append("%s / schem_check rc=0" % name)
            elif re.search(r"(ModuleNotFoundError|ImportError)", out):
                skips.append("%s / schem_check 本环境缺依赖 ⇒ 跳过" % name)
            else:
                fails.append("%s / schem_check rc=%d：%s" % (name, rc, last))
    detail = ["B 档范围 = %s；共 %d 个件" % (why, len(targets))]
    detail += ["已过：" + s for s in passed]
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
             ("G5 元件闸门（改动件）", lambda: gate_parts(base, args.all_parts))]

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
