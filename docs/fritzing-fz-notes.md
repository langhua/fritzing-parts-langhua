# Fritzing 写出来的 `.fz` 文件：实测笔记（可复查 ✓）

★ 本文件记的都是**实测** ✓（拿 Fritzing 1.0.3b **自己另存**的文件跟我们的对照 ✓），
每一条都附**怎么核** ✓ —— 目的：下次写解析器/生成器时**不要再猜** ✗。

对照文件 ✓：`AuroraTessellation-NFC/hardware/pixel/pixel-pcb-v61_byHand.fzz`
（= 用户在 Fritzing 里 `Ctrl+S` 另存的那份 ✓）与同目录的 `pixel-pcb-v59/v61/v62.fzz`（我们生成的 ✓）。

## 1. `<instances>` 是**外层容器** ✗ ⇒ 别用 `count("<instance")` 数实例

```xml
<instances>
    <instance moduleIdRef="…" modelIndex="…" path="…">
        …
    </instance>
    …
</instances>
```

- ✗ `text.count("<instance")` 会**把 `<instances>` 也算进去** ⇒ 天然**多 1** ✓
  （实测 v62：`<instance` 数出 298、`</instance>` 297 ✗ ⇒ 看着像"少一个闭合" ✗✓，
  其实**配平是好的** ✓）。
- ✓ 正确数法：`len(re.findall(r"<instance[\s>]", text))` ✓ 或 `r"<instance\b"` ✓。
- 核法 ✓：`hardware/pixel/check_instance_tags.py <fzz>` ⇒ 真 XML 解析器（`xml.etree`）
  **能解析** ✓（结构合法 ✓）。

## 2. 实例块的收盘缩进：Fritzing 是**同缩进** ✓

- 实测 ✓：Fritzing 写的每个 `<instance>` 都以 `\n<与开标签相同的缩进></instance>` 收盘 ✓
  ⇒ 按缩进配对（如 `tools/pcb_wire.py` 的 `blocks()` ✓）在**它的文件上**能读全 ✓
  （实测它另存的文件：过孔 **18/18** 全读到 ✓）。
- ✗ **我们自己的生成器**曾经在个别块上缩进不齐 ✗ ⇒ 同一个 `blocks()` 就只读到 16/18 ✗
  ⇒ **那是我们的问题** ✗，不是 Fritzing 的 ✓（别搞反了方向 ✓）。

## 3. 另存时 Fritzing 会把 **modelIndex 全部重新编号** ✗

- 实测 ✓：同一块板，另存前后 `modelIndex` 几乎全变 ✓。
- ⇒ 比较两份文件的连接时**必须按 `<title>` 对齐** ✓（`<title>` 是稳定的 ✓）。
  实现 ✓：`hardware/pixel/fz_conn_diff.py` ✓。

## 4. 另存时 Fritzing 会**补写**"几何上真的碰到一起"的连接 ✓

- 实测 ✓（这块板）：另存后 `<connect>` **多出 46 条** ✓，**全是 `Wire → Wire`** ✓，
  而且我们一条也没被它删 ✗（"仅我有 = 0" ✓）。
- ⇒ 它认"**一条走线的端点落在另一条走线身上**"为接上了 ✓ —— 我们的判据原来只认记录 ✗
  ⇒ 这是"判据与 Fritzing 不一致"的**实证之一** ✓（已补 ✓，见 `hardware/pixel/fz_exact.py` ✓）。

## 5. `<buses>` 在**核心件**里，而核心件**不在 `.fzz` 包里** ✗

- `.fz` 的 `path="…"` 指向 `.fzp` ✓：
  · 用户件 ⇒ `C:\Users\<user>\Documents\Fritzing\parts\user\…fzp` ✓（绝对路径 ✓）；
  · 核心件 ⇒ `:/resources/parts/core/…fzp` ✓ ⇒ 要去 **Fritzing 安装目录**找 ✓
    （`…\Fritzing\fritzing-parts\core\…` ✓）。
- 实测有总线的核心件 ✓：`wire.fzp` → `wirebus` ✓、`netlabel.fzp` → `label` ✓、
  `ground.fzp` → `groundbus` ✓（`via.fzp` **没有** ✓）。
- ✗ 我们自己在 `.fzz` 包里找 ⇒ 只找到 7 个 `.fzp` ✗ ⇒ "同 `bus()` 合并"**从未生效** ✗
  （已修 ✓，见 `fz_exact.py` 的 `bus_by_file` ✓）。
- 核法 ✓：`hardware/pixel/fz_buses.py <fzz>` ✓。

## 6. `wireFlags` 与"算不算铜"

- 实测 ✓：走线/过孔都带 `wireFlags="…"` ✓；PCB 铜 = **`& 4`**（`PCBTraceFlag` ✓）。
- ★ 闸门**只作用在与脚直接相接的那条走线**上 ✓（`utils/graphutils.cpp:550` ✓）；
  过孔自己写的是 `32`（`AutoroutableFlag` ✓）或 `0` ✓ ⇒ 它**不是** PCB 铜 ✓，
  但串链时**会被穿过去** ✓（`Wire::collectChained` ✓，见 `AGENTS.md` §13 ✓）。

## 7. 过孔的**铜心 ≠ 文件里的 `x,y`** ✗

- 实测 ✓（这块板 37 处一致 ✓）：恒差 **(+0.8644, +0.8644) mm** ✓
  = 孔径/2 + 环宽 + **0.56444**（画布留白 = 2 sketch 单位 ✓）
  ⇒ 唯一实现 = `tools/part_box.ring_off_mm(hole, ring)` ✓（`pcb-rules.md` §12 ✓）。
- 核法 ✓：`hardware/pixel/fz_via_probe.py <fzz> Via1` ✓（打印"离铜心 0.000 mm" ✓）。

## 8. ★ 我们踩过的两个坑（都不是 Fritzing 的 bug ✗）

| 坑 | 真相 |
|---|---|
| 以为 `<instance>` 少了闭合 ✗ | 是 `<instances>` 容器 ✓（见第 1 条 ✓） |
| 以为"按缩进配对读不全"是 Fritzing 的毛病 ✗ | 是**我们生成器**的缩进不齐 ✗（第 2 条 ✓） |

⇒ 教训 ✓：**先把自己那边的计数/解析核准** ✓，再谈"是不是它的问题" ✓
（本仓 §0 那条"自证不算数"同理 ✓）。

## 9. netlabel（同名连通）在 **PCB 视图**里的写法 ✓ 2026-10-02 实测

- 实测 ✓（`hardware/pixel/_work/probe_netlabel.py` ✓）：板上两个 `RC` netlabel ✓，
  **都有 `pcbView`** ✓、各有 **1 个脚**（`connector0` ✓），而它记的唯一连接是
  **`schematicTrace`**（原理图里的线 ✗）⇒ ⇒ 在 **PCB 视图里它没有任何铜/走线** ✗
  ⇒ 它就是"**有脚、没接线**"的连接件 ✓。
- ⇒ ★ 这解释了一个**计数现象** ✓：Fritzing 状态栏那句「**N 个接插件仍然需要布线**」
  **会把这种"光脚"算进去** ✓（本板 2 个 netlabel ⇒ 正好 2 个 ✗✓）。
- ★ 但**同名并网**这件事在 PCB 视图里**成不成立**，本次**没有核准** ✗ ——
  用户给的飞线两端是 `Via1`/`C1.pin1` 与 `L1.inner`/`Via8`（都是铜 ✓），
  **不是 netlabel** ✗ ⇒ 所以"9 个网 vs 它 7 个网"还不能归因到 netlabel ✓（**待核** ✗，别写死 ✗）。
- 核法 ✓：`_work/probe_netlabel.py <fzz>` ✓（打印每个 netlabel 的视图、脚、连接 ✓）。

