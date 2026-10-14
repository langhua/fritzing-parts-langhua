# checks 报告（fritzing-parts-langhua）

跑的时间：2026-10-15 02:33:49 ｜ python 3.13.14 ｜ 平台 win32
结果：**6 过 / 0 跳过 / 0 不合格**

| 闸门 | 结果 | 用时 |
|---|---|---|
| G1 文本卫生（全仓） | PASS | 0.6s |
| G2 README 一致性（全仓） | PASS | 0.1s |
| G3 生成器可重生成（全仓） | PASS | 5.5s |
| G4 fzpz 装箱一致（全仓） | PASS | 0.2s |
| G5 元件闸门（改动件） | PASS | 5.7s |
| G6 单位口径（全仓） | PASS | 0.1s |

## 明细

### G1 文本卫生（全仓） -> PASS
- tracked 文件 1063 个；BOM 0、非 UTF-8 0、索引非 LF 0、垃圾路径 0

### G2 README 一致性（全仓） -> PASS
- check_readme_table.py rc=0；=== 全部通过 ===

### G3 生成器可重生成（全仓） -> PASS
- 带 gen_part.py 的件 64 个；逐字节不一致 0 个；已知例外 2 个
- 已知例外（允许清单，理由在代码里）：Capacitor-0402（入库那份 fzp 的 <description> 写的是 1 / 2，而生成器现在写 A generic capacitor（其余字节全同）⇒ 入库产物是旧版/手工版；要统一得重生成并提交该件（用户 2026-10-13 定：其它件先不动））：svg.pcb.C0402_b41d7c0a5e93f2d86a14c7b3f5e90d21_1-CapacitorModuleID_pcb.svg
- 已知例外（允许清单，理由在代码里）：T-Halow-RJ45（icon 与生成器产物不同（该件是 T-Halow-RJ45 仓的参考件，不进本库预览图/元件箱，见 AGENTS §10））：svg.icon.T-Halow-RJ45_icon.svg

### G4 fzpz 装箱一致（全仓） -> PASS
- 比对条目 659 条；外来包 1 个（整包都没有同名源 ⇒ 只提示）；条目对不上源 0 条；同名源不唯一 0 条；非零件条目 0 条
- 口径：与**入库那份**（LF）逐字节比 ✓ —— 工作区 CRLF 不算差异；zip 载荷本身必须是 LF（否则换平台解出来与 svg/ 不一致 ✗，跑 `py -3.13 tools\repack_fzpz.py` 修）
- 注（外来包，仓库里没有同名源文件 ⇒ 不判它）：LM393-A3144-HALL-3PINS.fzpz（5 条）

### G5 元件闸门（改动件） -> PASS
- B 档范围 = 本次改动到的件（基线 HEAD~1）；共 30 个件
- 已过：AT24C02 / fzp_check rc=0
- 已过：AT24C02 / schem_check rc=0
- 已过：CH32V203C8T6 / fzp_check rc=0
- 已过：CH32V203C8T6 / schem_check rc=0
- 已过：CH340C / fzp_check rc=0
- 已过：CH340C / schem_check rc=0
- 已过：CH340E / fzp_check rc=0
- 已过：CH340E / schem_check rc=0
- 已过：CH340K / fzp_check rc=0
- 已过：CH340N / fzp_check rc=0
- 已过：CH340N / schem_check rc=0
- 已过：CH340X / fzp_check rc=0
- 已过：CN3165 / fzp_check rc=0
- 已过：ESP-12F / fzp_check rc=0
- 已过：ETA3425S2F / fzp_check rc=0
- 已过：ETA3425S2F / schem_check rc=0
- 已过：FPC-05F-12P-H15 / fzp_check rc=0
- 已过：H1102NLT / fzp_check rc=0
- 已过：H1102NLT / schem_check rc=0
- 已过：LD1117 / fzp_check rc=0
- 已过：LD1117 / schem_check rc=0
- 已过：PC817_SOP4 / fzp_check rc=0
- 已过：RT6150AGQW_rev_1 / fzp_check rc=0
- 已过：RT6150AGQW_rev_1 / schem_check rc=0
- 已过：RT9013 / fzp_check rc=0
- 已过：RT9193 / fzp_check rc=0
- 已过：SOD-123 / fzp_check rc=0
- 已过：SOD-123FL / fzp_check rc=0
- 已过：SOD-323 / fzp_check rc=0
- 已过：SOD-523 / fzp_check rc=0
- 已过：SY8089 / fzp_check rc=0
- 已过：SY8089 / schem_check rc=0
- 已过：TPS63051RMWR / fzp_check rc=0
- 已过：TX-AH-R900PNR / fzp_check rc=0
- 已过：TX-AH-R900PNR / schem_check rc=0
- 已过：TX-AH-R900PNR_rev_1 / fzp_check rc=0
- 已过：TX-AH-R900PNR_rev_1 / schem_check rc=0
- 已过：TXW8301 / fzp_check rc=0
- 已过：TXW8301 / schem_check rc=0
- 已过：USB-B01 / fzp_check rc=0
- 已过：USB-B01 / schem_check rc=0
- 已过：W25Q16JV / fzp_check rc=0
- 已过：W25Q16JV / schem_check rc=0
- 已过：XC6206P332MR / fzp_check rc=0
- 已过：XC6206P332MR / schem_check rc=0
- 已知例外（允许清单，理由在代码里）：CH340K：schem_check：=== 6 项 FAIL ===（schem_check 6 项既存 FAIL（pin 缺 class="pin"/connectorname 等；2026-10-15 核过：改前 6 == 改后 6））
- 已知例外（允许清单，理由在代码里）：CN3165：schem_check：=== 1 项 FAIL ===（schem_check 1 项既存 FAIL（同上口径：改前 1 == 改后 1））
- 已知例外（允许清单，理由在代码里）：ESP-12F：schem_check：=== 33 项 FAIL ===（schem_check 33 项既存 FAIL（大部分是 pin 缺 class/connectorname；2026-10-15 核过：改前 34 ⇒ 改后 33，本次还少 1 条 ✓））
- 已知例外（允许清单，理由在代码里）：FPC05-2H10PX：fzp_check：=== 1 项 FAIL ===（fzp_check 1 项既存 FAIL：缺 icon 视图 svg（老件，icon 从未入库；2026-10-15 核过：改前 1 == 改后 1））
- 跳过：CH340X / schem_check rc=2（跳过/提示）：=== 不适用：没有文字 —— 不是“矩形符号”原理图 ===
- 跳过：FPC-05F-12P-H15 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：FPC05-2H10PX / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：PC817_SOP4 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：RT9013 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：RT9193 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：SOD-123 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：SOD-123FL / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：SOD-323 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：SOD-523 / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===
- 跳过：TPS63051RMWR / schem_check rc=2（跳过/提示）：=== 不适用：没找到符号框 —— 这看起来不是“矩形符号”原理图 ===

### G6 单位口径（全仓） -> PASS
-    ⚠ ③ part_box.py:357 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：★★ 2026-09-27 修 ✓：`px` 由 **25.4/96 ✗ 改成 25.4/72** ✓（= 1/72 英寸 ✓）。
-    ⚠ ③ run_checks.py:188 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：★ 守什么 ✗：`px` 多长，这个量在库仓曾同时有 **25.4/96 ✗ / 25.4/72 ✓ / 25.4/90 ✗**
-    ⚠ ③ sch_box.py:38 在说明文字里提到旧值（不算错 ✓，过一眼即可 ✓）：#     ⇒ 同一个量（px 多长）在库里曾同时存在 **25.4/96 / 25.4/72 / 25.4/90** 三个值 ✗✗。

## 口径与边界

- rc 0 且无 FAIL 才算过；`rc 2` = **明确跳过，不算通过**（上面单独列了）。
- `tools/check_deploy.py`（要用本机 Fritzing 的 MINE 目录）**不在 CI 里**。
- ★ 本工具**不能**证明零件在 Fritzing / Inkscape 里的观感、能不能插面包板 —— 那是人眼验收。
