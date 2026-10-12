# checks 报告（fritzing-parts-langhua）

跑的时间：2026-10-13 02:42:42 ｜ python 3.13.14 ｜ 平台 win32
结果：**4 过 / 1 跳过 / 0 不合格**

| 闸门 | 结果 | 用时 |
|---|---|---|
| G1 文本卫生（全仓） | PASS | 0.5s |
| G2 README 一致性（全仓） | PASS | 0.1s |
| G3 生成器可重生成（全仓） | PASS | 4.7s |
| G4 fzpz 装箱一致（全仓） | PASS | 0.1s |
| G5 元件闸门（改动件） | SKIP | 0.2s |

## 明细

### G1 文本卫生（全仓） -> PASS
- tracked 文件 967 个；BOM 0、非 UTF-8 0、索引非 LF 0、垃圾路径 0

### G2 README 一致性（全仓） -> PASS
- check_readme_table.py rc=0；=== 全部通过 ===

### G3 生成器可重生成（全仓） -> PASS
- 带 gen_part.py 的件 53 个；逐字节不一致 0 个；已知例外 2 个
- 已知例外（允许清单，理由在代码里）：Capacitor-0402（入库那份 fzp 的 <description> 写的是 1 / 2，而生成器现在写 A generic capacitor（其余字节全同）⇒ 入库产物是旧版/手工版；要统一得重生成并提交该件（用户 2026-10-13 定：其它件先不动））：part.C0402_b41d7c0a5e93f2d86a14c7b3f5e90d21_1.fzp
- 已知例外（允许清单，理由在代码里）：T-Halow-RJ45（icon 与生成器产物不同（该件是 T-Halow-RJ45 仓的参考件，不进本库预览图/元件箱，见 AGENTS §10））：svg.icon.T-Halow-RJ45_icon.svg

### G4 fzpz 装箱一致（全仓） -> PASS
- 比对条目 280 条；跳过（名字带 hash = Fritzing 另存）324 条；找不到源 0 条；非零件条目 0 条
- 口径：与**入库那份**（LF）逐字节比 ✓ —— 工作区 CRLF 不算差异；zip 载荷本身必须是 LF（否则换平台解出来与 svg/ 不一致 ✗，跑 `py -3.13 tools\repack_fzpz.py` 修）

### G5 元件闸门（改动件） -> SKIP
- 没有改动到的元件目录 ⇒ B 档跳过（要看全仓就加 --all-parts）

## 口径与边界

- rc 0 且无 FAIL 才算过；`rc 2` = **明确跳过，不算通过**（上面单独列了）。
- `tools/check_deploy.py`（要用本机 Fritzing 的 MINE 目录）**不在 CI 里**。
- ★ 本工具**不能**证明零件在 Fritzing / Inkscape 里的观感、能不能插面包板 —— 那是人眼验收。
