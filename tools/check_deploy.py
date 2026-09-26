#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_deploy.py —— 核对「仓库里的元件」与「Fritzing MINE 里装的那份」是否一致（只读 ✓，可选 --fix）。

为什么需要它（2026-09-27 踩坑 ✗）：
  往 Fritzing 的「我的元件」目录（MINE = `%USERPROFILE%/Documents/Fritzing/parts`）手工部署时，
  我照**仓库里的文件名**拷贝（`part.<id>.fzp`、`svg.breadboard.<id>_breadboard.svg`）✗ ——
  而那套名字**恰好就是 `.fzpz` 的内部名** ✗，于是 MINE 里：

      · 多出一份**没有任何 fzp 引用它**的文件 ✓（`part.CH340C.fzp`、`svg.breadboard.CH340C_breadboard.svg`）；
      · **真正被引用的那份还是旧的** ✗（`CH340C.fzp` 时间戳停在 9/17 ✗）。

  ⇒ 生成器改了 ✓、`.fzpz` 重打了 ✓、我自以为"部署好了" ✓，**可 Fritzing 里看到的还是旧图** ✗。
  ⇒ 结论：**"我执行过部署命令"不等于"Fritzing 里就是新的"** ✗ —— 必须**另写一份独立的核对**
     （不许自证 ✓，见 AGENTS §5b 第 10 条 ⑥ ✓）。

Fritzing 的真实口径（本工具**不假设**，而是从 fzp 自己声明的字段反推 ✓ —— 2026-09-27 实测 141 例一致 ✓）：

    fzp 文件名  =  fzp 里 `moduleId="…"` 的值 + `.fzp`
    fzp 位置    =  `parts/user/<moduleId>.fzp`
    图形位置    =  `parts/svg/user/` + fzp 里 `image="<view>/<名>.svg"` 那条原样

  仓库侧的对应文件 = 元件目录里 `svg.<view>.<名>.svg`（`<名>` = image 路径的文件名部分）✓。

用法：
    py -3.13 tools/check_deploy.py                    # 扫全仓 svg/ 下所有带 *.fzp 的元件目录
    py -3.13 tools/check_deploy.py FPC05-2H10PX CH340C   # 只查这几件（名字或路径都行）
    py -3.13 tools/check_deploy.py --mine <目录>       # 指定 MINE（默认 %USERPROFILE%/Documents/Fritzing/parts）
    py -3.13 tools/check_deploy.py --stray            # 顺带列出 MINE 里 .fzpz 内部名的残留文件
    py -3.13 tools/check_deploy.py <件> --diff         # 把「旧」的实际差异打出来（覆盖前先看清 ✗）
    py -3.13 tools/check_deploy.py <件> --fix          # 不一致就照仓库覆盖到**正确路径**（覆盖前自动备份 ✓，不删 ✗）
    py -3.13 tools/check_deploy.py --clean-stray       # 把 .fzpz 内部名的残留**移到** parts 之外的备份目录（不删 ✗）

退出码：0 = 全部一致 ✓；1 = 有 ✗（缺文件 / 内容旧 / 名字不符）。
"""
import argparse
import datetime
import difflib
import hashlib
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SVG_ROOT = os.path.join(REPO, "svg")

# .fzpz 的内部名（= 仓库里的文件名）✗ —— 出现在 MINE 里就是"没按 Fritzing 口径部署"的残留
STRAY_PREFIXES = ("part.", "svg.")


def default_mine():
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.join(home, "Documents", "Fritzing", "parts")


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def mtime_str(path):
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "?"


def parse_fzp(path):
    """返回 (moduleId, [image 路径...])；解析不出 moduleId 就返回 (None, images)。"""
    txt = read_text(path)
    m = re.search(r'moduleId\s*=\s*"([^"]+)"', txt)
    images = re.findall(r'image\s*=\s*"([^"]+)"', txt)
    return (m.group(1) if m else None), images


def find_parts(names):
    """没给名字 ⇒ 扫全仓；给了 ⇒ 支持「目录名」或「路径」。"""
    if names:
        out = []
        for n in names:
            cand = n if os.path.isabs(n) else os.path.join(SVG_ROOT, n)
            if not os.path.isdir(cand):
                cand2 = os.path.join(REPO, n)
                cand = cand2 if os.path.isdir(cand2) else None
            if not cand:
                print(f"  ✗ 找不到元件目录：{n}")
                continue
            out.append(os.path.abspath(cand))
        return out
    out = []
    for dirpath, _dirnames, filenames in os.walk(SVG_ROOT):
        if any(f.lower().endswith(".fzp") for f in filenames):
            out.append(dirpath)
    return sorted(out)


def build_mine_fzp_index(user_dir):
    """moduleId -> [MINE 里的 fzp 文件名...]（用于识别「同 moduleId 但文件名不符」✗）。"""
    idx = {}
    if not os.path.isdir(user_dir):
        return idx
    for name in sorted(os.listdir(user_dir)):
        if not name.lower().endswith(".fzp"):
            continue
        mid, _ = parse_fzp(os.path.join(user_dir, name))
        if mid:
            idx.setdefault(mid, []).append(name)
    return idx


def find_alias(view_dir, basename):
    """在 MINE 的某个视图目录里找"文件名不符但显然是同一张图"的文件（如 svg.breadboard.X.svg）✗。"""
    if not os.path.isdir(view_dir):
        return None
    hits = []
    for name in sorted(os.listdir(view_dir)):
        if name == basename or name.endswith(basename):
            hits.append(name)
    return hits


def print_diff(repo_path, mine_path, label, limit):
    """把仓库 / MINE 两份的**实际差异**打出来（`--diff`）——覆盖前先看自己会不会冲掉别人的改动 ✓。"""
    try:
        a = read_text(repo_path).splitlines()
        b = read_text(mine_path).splitlines()
    except OSError as e:
        print(f"        （diff 读文件失败：{e}）")
        return
    d = list(difflib.unified_diff(b, a, fromfile=f"MINE/{label}", tofile=f"仓库/{label}", lineterm="", n=1))
    if not d:
        print("        （逐行内容相同 —— 差异只在行尾/空白或编码 ✗）")
        return
    shown = 0
    for line in d:
        if shown >= limit:
            print(f"        …（其余 {len(d) - shown} 行略，调大 --diff-lines 可看全）")
            break
        print("        " + line[:200])
        shown += 1


def main():
    ap = argparse.ArgumentParser(description="核对仓库元件与 Fritzing MINE 是否一致（只读，可选 --fix）")
    ap.add_argument("parts", nargs="*", help="元件目录名或路径（缺省 = 扫全仓）")
    ap.add_argument("--mine", default=default_mine(), help="MINE 的 parts 目录")
    ap.add_argument("--fix", action="store_true", help="不一致就照仓库覆盖到正确路径（覆盖前自动备份 ✓，不删 ✗）")
    ap.add_argument("--no-backup", action="store_true", help="--fix 时不要备份（默认会备 ✓）")
    ap.add_argument("--stray", action="store_true", help="列出 .fzpz 内部名的残留文件")
    ap.add_argument("--clean-stray", action="store_true", help="把残留文件移到 parts 之外的备份目录")
    ap.add_argument("--diff", action="store_true", help="把「旧」的文件差异打出来（覆盖前先看清 ✗）")
    ap.add_argument("--diff-lines", type=int, default=20, help="--diff 每处最多打多少行（默认 20）")
    args = ap.parse_args()

    mine = os.path.abspath(args.mine)
    user_dir = os.path.join(mine, "user")
    svg_user = os.path.join(mine, "svg", "user")

    print(f"仓库：{REPO}")
    print(f"MINE：{mine}   存在={os.path.isdir(mine)}")
    if not os.path.isdir(mine):
        print("✗ MINE 不存在，无法核对")
        return 1

    mine_idx = build_mine_fzp_index(user_dir)
    parts = find_parts(args.parts)
    print(f"待核元件：{len(parts)} 个\n")

    # --fix 覆盖前先备份被覆盖的那份（MINE 是用户的 Fritzing 目录 ⇒ 必须留后路 ✓）
    backup_root = os.path.join(os.path.dirname(mine),
                               "_deploy_backup_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    n_backup = [0]

    bad, fixed, no_repo_fzp = [], [], []
    n_ok = 0
    for d in parts:
        name = os.path.relpath(d, SVG_ROOT).replace("\\", "/")
        fzps = [f for f in sorted(os.listdir(d)) if f.lower().endswith(".fzp")]
        if not fzps:
            continue
        # 一个目录里有多个 fzp（变体）都查 ✓
        for fzp_name in fzps:
            fzp_repo = os.path.join(d, fzp_name)
            mid, images = parse_fzp(fzp_repo)
            if not mid:
                print(f"  ? {name}/{fzp_name}：解析不出 moduleId，跳过")
                continue

            problems = []   # 致命 ⇒ 算 ✗：(视图, 症状, 说明, 目标路径, 源路径) —— 源/目标都现成 ✓，--fix 直接照抄
            notes = []      # 提示 ⇒ 不算 ✗：（实测 Fritzing 自己导入时也会给 fzp 改名 ✓）
            # ① fzp 本身
            mine_fzp_name = mid + ".fzp"
            mine_fzp = os.path.join(user_dir, mine_fzp_name)
            if os.path.isfile(mine_fzp):
                if sha1(mine_fzp) != sha1(fzp_repo):
                    problems.append(("fzp", "旧", f"{mine_fzp_name}  (仓库 {mtime_str(fzp_repo)} / MINE {mtime_str(mine_fzp)})",
                                     mine_fzp, fzp_repo))
            else:
                alias = [n for n in mine_idx.get(mid, []) if n != mine_fzp_name]
                if alias:
                    # ★ 不是故障 ✗：Fritzing 导入 .fzpz 时**自己**也会写成 `<moduleId>_<hash>_<ver>.fzp`
                    #   甚至 `SYB-118.fzp`（moduleId 叫 Breadboard-SYB118-ModuleID ✗）—— 实测它在用 ✓。
                    #   真正致命的是 **fzp 引用到的图形文件不在那儿** ✗（见 ②）。
                    notes.append(f"fzp 文件名与 moduleId 不一致（应为 {mine_fzp_name}，实际 {', '.join(alias)}）"
                                 " —— Fritzing 自己导入时也会这样命名，能用 ✓")
                else:
                    problems.append(("fzp", "缺", mine_fzp_name, mine_fzp, fzp_repo))

            # ② 每个视图 svg（按 fzp 自己声明的路径）—— **这才是致命的那一类** ✓：
            #    fzp 说 image="breadboard/X.svg"，可 X.svg 不在 / 内容是旧的 ⇒ Fritzing 里看到的就是旧的 ✗
            for img in images:
                img = img.replace("\\", "/")
                view, base = os.path.split(img)
                repo_svg = os.path.join(d, "svg." + view + "." + base)
                if not os.path.isfile(repo_svg):
                    no_repo_fzp.append(f"{name}: 仓库无 svg.{view}.{base}（该视图不在仓里 ⇒ 跳过）")
                    continue
                mine_svg = os.path.join(svg_user, view, base)
                if os.path.isfile(mine_svg):
                    if sha1(mine_svg) != sha1(repo_svg):
                        problems.append((view, "旧", f"{base}  (仓库 {mtime_str(repo_svg)} / MINE {mtime_str(mine_svg)})",
                                         mine_svg, repo_svg))
                else:
                    alias = find_alias(os.path.join(svg_user, view), base)
                    if alias:
                        problems.append((view, "名字不符",
                                         f"fzp 引用 {base}，实际只有 {', '.join(alias)}（引用落空 ✗）",
                                         mine_svg, repo_svg))
                    else:
                        problems.append((view, "缺", base, mine_svg, repo_svg))

            if not problems:
                n_ok += 1
                if notes:
                    print(f"  ✓ {name}/{fzp_name}  (moduleId={mid})")
                    for nt in notes:
                        print(f"      注：{nt}")
                else:
                    print(f"  ✓ {name}/{fzp_name}  (moduleId={mid})")
                continue

            bad.append(f"{name}/{fzp_name}")
            print(f"  ✗ {name}/{fzp_name}  (moduleId={mid})")
            for what, kind, detail, target, src in problems:
                print(f"      {what}: {kind}  {detail}")
                if args.diff and kind == "旧":
                    print_diff(src, target, os.path.basename(target), args.diff_lines)
                if args.fix:
                    # 不论「旧 / 缺 / 名字不符」，做法都一样：把仓库那份写到**正确路径** ✓
                    # （残留的旧名字文件不在这里删 ✗ —— 交给 --clean-stray ✓）
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    if not args.no_backup and os.path.isfile(target):
                        dst = os.path.join(backup_root, os.path.relpath(target, mine))
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copyfile(target, dst)
                        n_backup[0] += 1
                    shutil.copyfile(src, target)
                    print(f"      ⇒ 已写入 {target}")

    print()
    if no_repo_fzp:
        print(f"注：{len(no_repo_fzp)} 条「仓库缺该视图文件」（不算 ✗，只是没得核）：")
        for line in no_repo_fzp[:20]:
            print("    · " + line)
        print()

    print(f"结果：一致 ✓ {n_ok} 个 fzp；有问题 ✗ {len(bad)} 个")
    for b in bad:
        print("    ✗ " + b)
    if args.fix and n_backup[0]:
        print(f"\n备份：被覆盖的 {n_backup[0]} 个文件已存到 {backup_root}（没删 ✓，确认没问题再自己删）")

    if args.stray or args.clean_stray:
        strays = []
        for root_dir, sub in ((user_dir, ""), (svg_user, "")):
            if not os.path.isdir(root_dir):
                continue
            for dirpath, _dn, fns in os.walk(root_dir):
                for fn in sorted(fns):
                    if fn.startswith(STRAY_PREFIXES):
                        strays.append(os.path.join(dirpath, fn))
        print(f"\n.fzpz 内部名的残留文件：{len(strays)} 个")
        for p in strays:
            ts = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")
            print(f"    · {os.path.relpath(p, mine)}   ({ts})")
        if args.clean_stray and strays:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = os.path.join(os.path.dirname(mine), f"_deploy_stray_{stamp}")
            os.makedirs(backup, exist_ok=True)
            for p in strays:
                rel = os.path.relpath(p, mine)
                dst = os.path.join(backup, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.move(p, dst)
            print(f"    ⇒ 已移到 {backup}（没有删除 ✓，确认没问题再自己删）")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
