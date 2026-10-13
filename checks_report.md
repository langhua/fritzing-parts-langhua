# checks 报告（fritzing-parts-langhua）

跑的时间：2026-10-13 21:56:26 ｜ python 3.13.14 ｜ 平台 win32
结果：**6 过 / 0 跳过 / 0 不合格**

| 闸门 | 结果 | 用时 |
|---|---|---|
| G1 文本卫生（全仓） | PASS | 0.5s |
| G2 README 一致性（全仓） | PASS | 0.1s |
| G3 生成器可重生成（全仓） | PASS | 5.2s |
| G4 fzpz 装箱一致（全仓） | PASS | 0.2s |
| G5 元件闸门（改动件） | PASS | 2.5s |
| G6 单位口径（全仓） | PASS | 0.1s |

## 明细

### G1 文本卫生（全仓） -> PASS
- tracked 文件 1034 个；BOM 0、非 UTF-8 0、索引非 LF 0、垃圾路径 0

### G2 README 一致性（全仓） -> PASS
- check_readme_table.py rc=0；=== 全部通过 ===

### G3 生成器可重生成（全仓） -> PASS
- 带 gen_part.py 的件 63 个；逐字节不一致 0 个；已知例外 2 个
- 已知例外（允许清单，理由在代码里）：Capacitor-0402（入库那份 fzp 的 <description> 写的是 1 / 2，而生成器现在写 A generic capacitor（其余字节全同）⇒ 入库产物是旧版/手工版；要统一得重生成并提交该件（用户 2026-10-13 定：其它件先不动））：part.C0402_b41d7c0a5e93f2d86a14c7b3f5e90d21_1.fzp
- 已知例外（允许清单，理由在代码里）：T-Halow-RJ45（icon 与生成器产物不同（该件是 T-Halow-RJ45 仓的参考件，不进本库预览图/元件箱，见 AGENTS §10））：svg.icon.T-Halow-RJ45_icon.svg

### G4 fzpz 装箱一致（全仓） -> PASS
- 比对条目 654 条；外来包 1 个（整包都没有同名源 ⇒ 只提示）；条目对不上源 0 条；同名源不唯一 0 条；非零件条目 0 条
- 口径：与**入库那份**（LF）逐字节比 ✓ —— 工作区 CRLF 不算差异；zip 载荷本身必须是 LF（否则换平台解出来与 svg/ 不一致 ✗，跑 `py -3.13 tools\repack_fzpz.py` 修）
- 注（外来包，仓库里没有同名源文件 ⇒ 不判它）：LM393-A3144-HALL-3PINS.fzpz（5 条）

### G5 元件闸门（改动件） -> PASS
- B 档范围 = 本次改动到的件（基线 HEAD~1）；共 13 个件
- 已过：DW01A / fzp_check rc=0
- 已过：DW01A / schem_check rc=0
- 已过：Resistor-01005 / fzp_check rc=0
- 已过：Resistor-0201 / fzp_check rc=0
- 已过：Resistor-0402 / fzp_check rc=0
- 已过：Resistor-0603 / fzp_check rc=0
- 已过：Resistor-0805 / fzp_check rc=0
- 已过：Resistor-1206 / fzp_check rc=0
- 已过：Resistor-1210 / fzp_check rc=0
- 已过：Resistor-1812 / fzp_check rc=0
- 已过：Resistor-2010 / fzp_check rc=0
- 已过：Resistor-2512 / fzp_check rc=0
- 已过：Supercap-0.47F / fzp_check rc=0
- 已过：Supercap-1.5F / fzp_check rc=0
- 跳过：Resistor-01005 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-0201 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-0402 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-0603 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-0805 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-1206 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-1210 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-1812 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-2010 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Resistor-2512 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：Supercap-0.47F / schem_check rc=2（跳过/提示）：=== 不适用：只有 1/2 个脚的引线贴着框 —— 这套符号的脚不是沿方框四边排的 ===
- 跳过：Supercap-1.5F / schem_check rc=2（跳过/提示）：=== 不适用：只有 1/2 个脚的引线贴着框 —— 这套符号的脚不是沿方框四边排的 ===

### G6 单位口径（全仓） -> PASS
-    ⚠ ③ part_box.py:357 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：★★ 2026-09-27 修 ✓：`px` 由 **25.4/96 ✗ 改成 25.4/72** ✓（= 1/72 英寸 ✓）。
-    ⚠ ③ run_checks.py:171 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：★ 守什么 ✗：`px` 多长，这个量在库仓曾同时有 **25.4/96 ✗ / 25.4/72 ✓ / 25.4/90 ✗**
-    ⚠ ③ sch_box.py:38 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：#     ⇒ 同一个量（px 多长）在库里曾同时存在 **25.4/96 / 25.4/72 / 25.4/90** 三个值 ✗✗。

## 口径与边界

- rc 0 且无 FAIL 才算过；`rc 2` = **明确跳过，不算通过**（上面单独列了）。
- `tools/check_deploy.py`（要用本机 Fritzing 的 MINE 目录）**不在 CI 里**。
- ★ 本工具**不能**证明零件在 Fritzing / Inkscape 里的观感、能不能插面包板 —— 那是人眼验收。
