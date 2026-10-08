# Fritzing 1.0.3b 草图（`.fzz`）格式：实测到的坑与"乱写"

> **用途**：本仓/本项目要**用脚本往 `.fzz` 里注入走线**（AuroraTessellation pixel 板自动布线 ✓），
> 于是拿 **Fritzing 自己写的文件**当权威样例逐项对照 ✓。
> 过程中发现 Fritzing 自己也有若干不一致、甚至明显写坏的地方 —— **本文只记"实测到的事实"** ✓，
> 每条都带**证据（哪个文件、多少条、怎么数的）** ✓，供将来给 fritzing-app 提 **PR / issue** 时引用 ✓。
>
> **规矩**：只写**量过**的 ✓；没量过的一律放 §4「待确认」 ✗ 不混进事实 ✗。

---

## 0. 证据来源（都能复现 ✓）

| 编号 | 来源 | 规模 |
|---|---|---|
| S1 | Fritzing 自带样例 `C:\Users\<用户>\AppData\Local\Programs\Fritzing\sketches\core\*.fzz` | **44 份**、`WireModuleID` 走线 **4149 条**、含 PCB 走线的 **135 份** |
| S2 | 用户项目 `AuroraTessellation-NFC/hardware/subboard_4x4/single-channel/single-channel.fzz` | 走线 212 条，其中 **PCB 走线 190 条** |
| S3 | 本项目 `AuroraTessellation-NFC/hardware/pixel/pixel-pcb-v28.fzz`（脚本注入后） | 我插的走线 129 条 + 过孔 18 个 |
| S4 | 对照脚本（scratch，见 §5） | — |

---

## 1. 实测事实（每条：现象 + 证据 + 怎么量的）

### F1 · 走线实例的**视图数**：Fritzing 自己 4148/4149 都写 3 个视图
- **现象** ✓：`WireModuleID` 实例一条 = 一个 `<views>` 里放
  `breadboardView(layer="breadboardWire")` + `pcbView(layer="copper?trace")` + `schematicView(layer="schematicTrace")` ✓，
  三个视图**各自的 connectors 都写全**（`connector0`/`connector1` 各一份 ✓）。
- **证据** ✓（S1 全量）：4149 条中 **4148 条 = 3 视图** ✓；**1 条 = `<views />`（空！）** ✗。
- **那一条** ✗：`sketches\core\Melody.fzz`，`<instance modelIndex="1858468" moduleIdRef="WireModuleID" …><views /></instance>`
  ⇒ **Fritzing 自己会写出"一个视图都没有"的走线** ✗（能随样例一起发布 ⇒ 至少加载时被容忍 ✓）。
- **怎么量的** ✓：按 `<instance …</instance>` 切块，统计块内 `<breadboardView|schematicView|pcbView|iconView` 出现次数。
- **对我们的意义** ✓：**"只有 `pcbView` 一个视图"在 Fritzing 自己的输出里从来没出现过**（S1 里 0 例 ✗）——
  是不是硬要求**还没定** ✓，见 §4-Q1。

### F2 · 连接**两侧都写**（回指 100% ✓）
- **现象** ✓：一条走线的 `connectorK` 里写 `<connect connectorId=… modelIndex=… layer=…/>`；
  **对方（焊盘 / 另一条走线 / 过孔）那一侧也写一条指回来** ✓。
- **证据** ✓（S1 的 PCB 走线全量）：**8270 处** connect，**目标侧有回指 8270 处** ✓、**无回指 0 处** ✗、空 `<connects>` 0 处 ✓。
- **怎么量的** ✓：对每条 PCB 走线的每个 connector connect，去目标 `modelIndex` 的 instance 块里找
  `<connect connectorId="{源connector}" modelIndex="{源modelIndex}"`。
- **对我们的意义** ✓：S3 原来**只写了一侧** ✗（80 处缺回指 ✗）⇒ 已列为必修 ✓。

### F3 · 面包板连接写在 `<pcbView>` 里（标签名与视图不符 ✗）
- **现象** ✓：面包板元件（`Breadboard1` / `SYB-118`）的**面包板**连接，存在
  `<pcbView layer="breadboardbreadboard">` 里 ✗ —— 名字叫 `pcbView`，内容却是面包板视图 ✓。
- **证据** ✓（S3）：`<title>Breadboard1</title>` 的实例里 `<pcbView layer="breadboardbreadboard">`，
  其 connectors `connectorId="pin31E"` 等 ✓。
- **对我们的意义** ✓：**任何"读 pcbView"的脚本必须再筛 `layer` 含 `copper`** ✗，
  否则会把面包板连接当成 PCB 连接 ✗（本项目踩过：解析出一堆"跨视图层对不上"的假警报 ✗）。

### F4 · `<connect layer="…">` 的语义 = **目标**那一层；且同一走线的三视图**共用 connectors**
- **现象** ✓：
  - 走线 → **焊盘**：`layer` 写**焊盘**的层（例：`copper1trace` 的线接 THT 盘，写 `layer="copper0"` ✓）；
  - 走线 → **走线**：写 `copper?trace` ✓；
  - 走线 → **过孔**：写 `copper0` ✓。
- **证据** ✓（S2 逐字）：`single-channel.fzz` 一条 `pcbView layer="copper1trace"` 的线，
  `connector1` → `<connect connectorId="connector0" modelIndex="90005428" layer="copper0"/>` ✓。
- **特例（跨视图）** ✗：`sketches\core\7Segment_direct.fzz` 第一条 PCB 走线
  （`pcbView layer="copper1trace"`）的 `connector0` →
  `<connect connectorId="pin16I" modelIndex="1820496" layer="breadboardbreadboard"/>` ✗
  —— **PCB 的连接指向一个面包板孔** ✓。
- **解释** ✓（与 F1 一致）：该走线是**一条实例横跨三视图** ✓ ⇒ connectors 只有一份 ✓、
  连接只记一份 ✓ ⇒ 记到哪个视图的端点取决于"当时怎么建的" ✓。
- **对我们的意义** ✓：我原来把 `layer` 写成**走线自己**的层 ✗ ⇒ 底层 SMD 盘被写成 `layer="copper1"` ✗
  ⇒ 盘根本不在那层 ✗ ⇒ 整组线失效 ✗。**已修** ✓（写"对面那层" ✓）。

### F5 · 过孔（`ViaModuleID`）的写法 ✓
- **现象** ✓（S1 原文）：
  ```xml
  <instance moduleIdRef="ViaModuleID" modelIndex="655431" path=":/resources/parts/core/via.fzp">
      <property name="hole size" value="0.6mm,0.3mm"/>
      <title>Via1</title>
      <views>
          <breadboardView layer="copper0"> … <connector connectorId="connector0" layer="copper0">
              <connects><connect connectorId="connector1" modelIndex="655448" layer="breadboardWire"/>
                        <connect connectorId="connector0" modelIndex="655453" layer="breadboardWire"/></connects>
          </connector> …</breadboardView>
          <pcbView layer="copper0">     … <connect connectorId="connector1" modelIndex="655448" layer="copper0trace"/></pcbView>
          <schematicView layer="copper0"> … layer="schematicTrace" …</schematicView>
      </views>
  </instance>
  ```
- **要点** ✓：**三视图都写** ✓、layer 用 `copper0` ✓、`wireFlags="0"` ✓、
  **`connector0` 里列出它接的线（= 回指）** ✓。
- **对我们的意义** ✓：S3 的过孔**完全没有 `<connects>`** ✗ ⇒ 必修 ✓。

### F6 · `wireFlags` 取值不统一（语义未见文档）
- **现象/证据** ✓：
  - `single-channel.fzz`：面包板 `128` ✓、PCB `128` ✓、原理图 `64` ✓；
  - `7Segment_direct.fzz`：PCB `64` ✓；
  - 过孔：`0` ✓。
- **结论** ✓：同一个"PCB 走线"，不同文件写 `128` 或 `64` ✗ ⇒ **不能当判据** ✗，
  照抄"同文件同视图"的值最安全 ✓。

### F7 · `geometry@z` 不统一
- **现象/证据** ✓：走线 `z≈9.5` ✓、过孔 `z≈5.5` ✓、元件 `z≈5.5 / 8.5` ✓（S1、S2、S3 一致方向）✓。
- **结论** ✓：z 只影响叠放 ✓，没有"必须等于某值" ✓；照抄同类型元素的值 ✓。

### F8 · 本项目实测后果（S3）：**只有 pcbView + 缺回指 ⇒ 整组走线不被认**
- **现象** ✗：Fritzing 打开 `pixel-pcb-v28.fzz` ⇒ 状态栏 **「7 中的 0 网络布线完成」**、
  **「42 个接插件仍然需要布线」** ✗；画面上是**飞线（ratsnest）** ✗，看不到布好的走线 ✗。
- **同时排除的** ✓：文件**是合法 XML** ✓（`xml.etree` 解析通过 ✓）、
  实例块**确实插在 `<instances>` 里** ✓（184/184 ✓）、
  走线的 pcbView **逐标签与 Fritzing 自己的完全同构** ✓（`geometry > wireExtras > connectors > …` ✓）、
  目标 `modelIndex` **都存在** ✓（0 处悬空 ✓）。
- **⇒ 剩下的差异只有 F1（视图数）与 F2（回指）** ✓ —— 修的顺序：先 F2（纯功能、必写 ✓），再看 F1 ✓。

### F9 · ★★ **走线实例的视图数是硬要求**（用户实验**判决** ✓✓）
- **实验** ✓（用户亲手做 ✓）：在 Fritzing 里、就这份草图的 **PCB 视图**上手画一根线 ⇒ 另存为
  `pixel-pcb-wire-test.fzz` ✓（= **Fritzing 亲手重存**我的文件 ✓）。
- **读数** ✓：
  | 文件 | 状态栏 | 说明 |
  |---|---|---|
  | `pixel-pcb-v30.fzz`（我写的 ✓） | **7 中的 0** ✗／42 | 我 129 条**单视图**线 ⇒ **一条都没算** ✗ |
  | `pixel-pcb-wire-test.fzz`（Fritzing 重存 ✓） | **7 中的 0** ✗／**41** | 他手画那根（**三视图** ✓）⇒ **算上了一只脚** ✓（42→41 ✓） |
- **⇒ 结论** ✓：**单视图（只有 `pcbView`）的走线不参与 PCB 连通** ✗；
  而且此时**层已被 Fritzing 自动纠正** ✓（见 F10）、**回指也在** ✓ ⇒ 变量只剩视图数 ✓。
- **另一条同源事实** ✓：Fritzing 自己**保留**了那 129 条单视图线（原样存回 ✓、只补了 `bottom="true"`、
  把 `z` 重编号 ✓）⇒ 它是**收下了但不算连通** ✓ —— 也解释了为什么“看着在、就是 0 完成” ✗。
- **非 PCB 视图怎么写** ✗：Fritzing 给**每个视图写各自的坐标** ✓，且两视图**路径互不相同** ✗
  （同一段：PCB `(131.154,30.195)→(+14.133,-5.434)` ✓／面包板 `(152.41,39.007)→(+7.67939,9.6132)` ✓）
  ⇒ **不能把 PCB 坐标抄进面包板视图** ✗（会把人手工摆的面包板画花 ✗）。
  本项目采用 **零长度占位** ✓（实例在 ✓、不画线 ✓、不编坐标 ✗）—— 待验 ✓。

### F10 · ★★ `<connect layer="X">` 的 X = **目标 connector 在**该视图**里声明的层**（照文件字面值 ✓）
- **反面实测** ✗：我原来用的层是**推导**出来的（`pcb_check.collect` ✓，背面件会翻面 ✓），
  与文件里 connector 那行的**字面值不总一样** ✗ —— 在同一份草图上实测 **27 处对不上** ✗
  （例：U1/J1/J2/D3 我写 `copper0` ✗／文件声明 `copper1` ✓；L1 的 THT 盘我更写成 `both` ✗
  —— **`both` 根本不是合法的层名** ✗）。
- **Fritzing 的裁定** ✓：它把同一份草图**重存**一遍后，那 27 处**全部自动纠正成"文件声明的层"** ✓
  （重存后 266 处连接**全对得上** ✓）⇒ 照文件声明值写 ✓ 才是对的口径 ✓。
- **修后实测** ✓：`pixel-pcb-v30.fzz` ⇒ **256 处全部对得上** ✓、0 处不对 ✗
  （只剩 EPAD 那 2 处“目标没有 pcbView 条目” ✓ —— 这类在 Fritzing 自己文件里有 **108 处** ✓ 合法 ✓）。
- ★ 附带闸门 ✗：**回指补不全就不写文件** ✗；但“目标本来就没这个 connector”属**合法** ⇒ 只报数 ✓。

### F11 · ★★ `wireFlags` **决定这条线算哪种铜**（源码铁证 ✓✓）

- **源码** ✓（本地源码 `F:\build-fritzing\fritzing-app\src\viewgeometry.h` ✓）：
  ```cpp
  enum WireFlag {
      NoFlag = 0, RoutedFlag = 2, PCBTraceFlag = 4, ObsoleteJumperFlag = 8,
      RatsnestFlag = 16, AutoroutableFlag = 32, NormalFlag = 64, SchematicTraceFlag = 128
  };
  ```
  且 `wireFlags` 就是实例该视图 `geometry` 上的那个属性 ✓（`viewgeometry.cpp`：`m_wireFlags(geometry.attribute("wireFlags").toInt())` ✓）。
- **Fritzing 自己的分布** ✓（45 份文件 / 4398 个走线过孔 ✓ `_work/flags_stat.py` ✓）：
  `4 PCBTrace` 1390 ✓／`128 SchematicTrace` 1486 ✗／`64 Normal` 708 ✓／`36 = 4|32` 564 ✓；
  过孔 `0` 11 ✓／`32` 19 ✓。★ **同一条线的三个视图写同一个值** ✓。
- **我的错** ✗：PCB 走线写成了 **`128`（= SchematicTraceFlag ✗）** ⇒ Fritzing 认为它**不是 PCB 铜** ✗
  ⇒ **PCB 上不算连通** ✓ —— 这就是“线看得见、却永远 **0/7 布线完成**”的根 ✓。
- **修** ✓：PCB 走线三视图统一写 **`4`** ✓；过孔保持 `32` ✓（Fritzing 自己也在用 ✓）。
- ★ 另一条同源事实 ✓：**带 `RatsnestFlag(16)` 的走线实例在加载时会被直接删掉** ✗
  （`modelbase.cpp` 的 `isRatsnest()` + `instances.removeChild(instance)` ✓）⇒ 我们绝不能写 16 ✓。

### F12 · ★★ 两套单位：`.fzz` 内部 **1/90 in** ✓、导出 SVG **1/72 in** ✓（比值 0.8 ✓）

- **导出 SVG** ✓：头里 `width="1.1058in"` ↔ `viewBox="0 0 79.6176 99.7544"` ⇒ **72 单位/英寸** ✓（1 单位 = 0.35278 mm ✓）。
- **`.fzz` 内部坐标** ✓：用**两个物理锚**互校 ✓（元件规格是**外部事实** ✓，不是我方常数 ✗）——
  JST **SH 1.0 系列脚距 = 1.00 mm** ✓ ⇒ 内部 **3.5433** / 导出 **2.8346** 单位 ✓；
  QFN **0.40 mm** ✓ ⇒ 内部 **1.4173** / 导出 **1.1339** ✓
  ⇒ 内部 **0.28222 mm = 1/90 in** ✓、导出 **0.35278 mm** ✓、比值 **0.8** ✓。
- **我踩的坑** ✗：一开始把内部单位当成 **0.254 mm**（= 1/100 in ✗）⇒ 所有长度**齐刷 111%** ✗
  ⇒ 看着像“Fritzing 把线拉长了 11%” ✗ —— 其实是自己算错 ✓。
  纪律 ✓：**“每单位多少 mm”必须指得出来源** ✓（物理锚 / 规格表 / 实测 ✓），✗ 别凭习惯写 ✗。

### F13 · 导出 SVG 的结构：`partID` = `modelIndex` + 层号 ✓；每个元件出现**两次** ✗

- `<g partID="900127260">` / `<g partID="900127261">` ⇒ **同一个元件两份** ✓（copper0 / copper1 各一份 ✓）
  ⇒ 按 `partID` 认线要用 **`mi` + 1 位层号** 前缀匹配 ✓（`900131750` ⇒ `mi=90013175` ✓；走线只出一份 ✓）。
- ★ **每个元件还有第三个组** ✗：`<g id="partLabel" partID="…">`（位号文字 ✓）——
  ✗ 用 `d[pid] = …` 会被它**覆盖** ✗（我中过一次 ⇒ 定标全错 ✗）⇒ 必须 `setdefault(...).extend(...)` + 跳过 `partLabel` ✓。
  ★ 2026-10-08 ✓：**我们自己那个 `render_sch.py` 现在也照这个形状写** ✓
  （`<g id="partLabel" partID="…0" font-family="DroidSans" …>` ✓）—— 不是为了像 ✗，
  而是**差异图的动画要靠它** ✓（位号据此**并进它那个零件那一处** ✓，见 `docs/diff-animation.md` ✓）。
  ⚠ 于是我们自己渲的 svg 里 `id="partLabel"` 会**重复 9 次** ✓ —— 与 Fritzing 导出**同病** ✓
  （它每个位号组都叫这个名字 ✓）；★ 谁要按 id 找位号，**别用 `getElementById`** ✗，
  按 `partID` 找 ✓。
- 走线 = `<g partID="mi+层号"><line … stroke-width="0.864"/></g>` ✓（0.864 导出单位 = 12 mil ✓）。

### F14 · ★★ **Fritzing 载入时会把走线端点吸到它自己的连接点** ✗

- 实测 ✓（`pixel-pcb-v41.fzz` ↔ 用户导出的 `_图示.svg` ✓，按 `partID` 逐条对 ✓）：
  **130/130 线**、**18/18 过孔**都在 ✓；线宽/颜色全对 ✓；**元件几何零残差** ✓（33 对焊盘配准、最大 0.00002 mm ✓）；
  但 **260 个端点里 81 个被挪** ✗（挪 **0.07～0.66 mm** ✓），挪完**仍在所连焊盘内** ✓（离最近边 0.045～0.25 mm ✓）。
- ⇒ 合计线长 **我 198.5 mm → 它画 182.1 mm** ✗（**短 8.3%** ✗）⇒
  **“我给的几何” ≠ “它显示/保存的几何”** ✗（在 Fritzing 里再存一次，文件里的几何就变了 ✓）。
- **纪律** ✓：报**线长/坐标/间隙**时**必须拿导出复核** ✗ —— 自己的渲染器与自己的写回器共用一份几何 ⇒ **自证** ✗。

### F15 · ★★ 写回器按“**端点坐标**”认焊盘 ⇒ **线经过盘心 = 接上了** ✗

- 机制 ✓（`gen_routes.build_xml` ✓）：端点→焊盘是**按坐标查表**（`pad_at[(x,y,层)]` ✓）
  ⇒ **只要线端正好落在某只盘的中心，就会给那只盘写 `<connect>`** ✗。
- 实例 ✓：v41 的 `Wire90013154` 端**正落在 U1 的空脚 PC0 盘心**（0.000 mm ✗）⇒ 写了 `connector6` ✗
  ⇒ **Fritzing 里 PC0 被算进 5V** ✗；v47 同一条线**停在结点上、离 PC0 盘心 0.18 mm** ✓ ⇒ 不写 ✓。
- ⇒ 规矩 ✓：**线端/线身不许落在“非本网”的焊盘上** ✓（含**空脚** ✓）——
  但改它要连带解决“端点必须正中”（否则写回器报悬空 ✗），2026-10-01 两版都没成 ✓ ⇒ 见 §4-Q5 ✓。

### F16 · 网表名 vs 库里焊盘名 **不是一回事** ✗

- 本项目网表写 **(位号, 引脚名)** ✓：`("U1","VDD")`、`("U1","EPAD")`、`("D3","A1")` ✓；
  但也有 `("C1","#1")`、`("R1","Pin 0")` ✗ —— 而 `pcb_check` 读出的焊盘名是 **`0` / `1` / `Pin 0`** ✓
  ⇒ **同一只件两边名字对不上** ✗（U1 这类真引脚名才对得上 ✓）。
- ⇒ 纪律 ✓：网表→焊盘**只走 `pcb_route.resolve_nets` 那条唯一实现** ✓（它会处理别名 ✓）；
  ✗ 别自己按名字“对号” ✗ —— 我这么干过 ⇒ 130 条线**全部**认不出网 ✗、结论全废 ✗。

### F17 · ★★ 过孔**画出来是“环 + 孔”** ✓，尺寸口径 = `hole size = "<孔直径>,<环宽>"` ✓✓

- **现象** ✓（源：用户 Fritzing 导出的 `pixel-pcb-v47_图示.svg` ✓，18 个过孔 ✓）：
  ```xml
  <g partID="900131570"><g transform="translate(37.4544,44.8711)">
      <g id="copper0">
        <circle cx="2.45039" cy="2.45039" fill="none" id="connector0pin"
                r="0.637795" stroke="#f9a435" stroke-width="0.425197"/>
  ```
  —— 每个过孔 **两个同心圆**、`fill="none"`（= **圆环** ✗ 不是实心点 ✗）：
  一个 `#f9a435`（copper0 底层 ✓）、一个 `#fdde68`（copper1 顶层 ✓）✓，**半径相同、圆心相同** ✓
  （两层圆心实测偏差 **0.0001 mm** ✓ ⇒ **同心** ✓）。
- **换算** ✓（1 导出单位 = 1/72 in = 0.35277778 mm ✓，见 F12 ✓）：
  `r=0.637795` ⇒ 中心线半径 **0.2250 mm** ✓；`stroke-width=0.425197` ⇒ 环宽 **0.1500 mm** ✓
  ⇒ **孔内径 0.3000 mm ✓、铜盘外径 0.6000 mm ✓** —— 与件属性 `hole size="0.3mm,0.15mm"`
  **逐位对上** ✓✓ ⇒ **口径 = `<孔直径>,<环宽>`** ✓（✗ 不是“盘直径,孔直径” ✗，也不是“半径” ✗）。
- **位置** ✓：36 个圆相对 `.fzz` 的 `<geometry>` 点做“偏移投票”⇒ **同一偏移 36/36 全票** ✓
  ★★ **但当时把这个偏移读成了 0** ✗（2026-10-02 修 ✓）：投票“全票”只能证明
  **36 个圆彼此一致** ✓，**证不了它是 0** ✗ —— 同一个导出里 `translate` 也是“画布原点”
  口径 ⇒ 两处都少算了**同一份**局部偏移 ✓，于是“相对差”就都是 0 ✓。
  **真规则**（2026-10-02 ✓，三个**互相独立**的实测点全中 ✓）：
  $$\text{偏移(mm)} = \underbrace{\text{孔径}/2 + \text{环宽}}_{\text{铜半径}} + \underbrace{0.56444}_{\text{画布留白 = 2 sketch 单位}}$$
  · 默认过孔 `0.3,0.15` ⇒ 0.30 + 0.56444 = **0.86444** ✓（= 用户导出 `2.45039` pt ÷72×25.4 ✓）
  · 安装孔 `2.2,0.0` ⇒ 1.10 + 0.56444 = **1.66444** ✓（导出 `4.71811` pt ✓ ——
    ✗ 代码里曾写成 `1.66454`，是把第 4/5 位**写反**了 ✗，已改对 ✓）
  · ★ 用户手加的 `0.4,0.3` 过孔 ⇒ 0.50 + 0.56444 = **1.06444** ✓ —— 这条**不靠导出读数** ✓，
    是**用户在 Fritzing 里把线端拖到过孔上**后文件里存的端点 ✓（两实例 × 两轴 4 个读数全中 ✓）
  ⇒ ★★ **教训**：**尺寸相关的公式，别拿一个尺寸量出的常数当通则** ✗ —— 单一常数只对
  `0.3/0.15` 成立 ✓；套到外径 1.00 的过孔上 ⇒ 铜心偏 **0.2 mm/轴** ✗ ⇒ 校验器把**接好的**
  过孔报成“孤立过孔 ＋ 悬空端点” ✗，而 Fritzing 里明明是通的 ✗（2026-10-02 用户当场指出 ✓：
  「我在 Fritzing 里点击线上节点，显示是通的」✓）。
  ★ 实现只有一份 ✓：`part_box.ring_off_mm(hole, ring)` ✓（`pcb_check` / `pcb_pads.holes` /
  `render_pcb` / `gen_routes` 全调它 ✓）。
  ★ 旁证 ✓：**Fritzing 的连接是显式写的** ✓ —— 那个 `.fzz` 里
  `Wire90014056` 的 `<connect … modelIndex="90014051" layer="copper0"/>` 就明写“接在过孔上” ✓
  ⇒ 校验器**只按几何判**时会与 Fritzing 相反 ✗ ⇒ 两者不一致时，先怀疑**自己的几何口径** ✓。
- **对我们的意义** ✓：预览器要**照它画** ✓（环 + 白心孔 ✓）——
  第一版画成**实心绿点** ✗ ⇒ 图上与焊盘无异 ✗、孔眼看不出来 ✗
  （用户 2026-10-01：「过孔都画错了」✓）；**已修** ✓（`render_pcb.py` 的
  `C_VIA_BOT` / `C_VIA_TOP` ✓，尺寸由 `pcb_check` 读件属性放进 via 字典 ✓）。
- ★ **预览器与交付文件是两回事** ✓：改画法**只动 `tools/render_pcb.py`** ✓，
  `.fzz` 里过孔的写法一个字没改 ✗（它本来就是 Fritzing 认的写法 ✓）。

### F18 · ★★ 走线可以是**三次贝塞尔** ⇒ 预览不能把弧拉直 ✗（2026-10-08 ✓）

- **现象** ✓（源：用户对图指出 ✗：「v59 里的 5V 和 GND **24mil 线**」✗）：`.fzz` 里
  `<pcbView layer="copper0trace"><geometry z x y x1 y1 x2 y2 wireFlags/>` **只写了弦的两端** ✓，
  **真形状在同级的 `<wireExtras>` 里** ✓：
  ```xml
  <wireExtras mils="24" color="#f28a00" opacity="1" banded="0">
    <bezier><cp0 x="-22.2088" y="-8.74887"/><cp1 x="-36.5347" y="1.16353"/></bezier>
  </wireExtras>
  ```
  ⇒ **三次贝塞尔** ✓：`p0 = geometry@(x+x1, y+y1)`、`p3 = geometry@(x+x2, y+y2)`、
  控制点 = `geometry@(x,y) + cp0/cp1` ✓（`cp0/cp1` 与 `x1..y2` **同一个局部系** ✓，
  口径与源码 `src/utils/bezier.h` 的 `Bezier(p0, p1, cp0, cp1)` 一致 ✓）。
- **量** ✓（v59 ✓）：**168 条走线**里 **15 条 `24 mil`**（= 电源粗线 ✓：copper0 14 条 ✓ / copper1 1 条 ✓），
  其中 **5 条带 `<bezier>`** ✓；沿弧的最大偏离弦 **≈2.5 mm** ✗（板上 25 mm ⇒ 一眼可见 ✗）。
  ★ 全项目扫（151 个 `.fzz` ✓）：**22 个有弯线、合计 182 条，全部在 `pcbView`** ✓
  （`breadboardView` / `schematicView` **一条都没有** ✓）⇒ `render_sch.py` / `render_bb.py` 不用动 ✓。
- **旁证** ✓（只认 Fritzing 自己 ✓，F14 的纪律 ✓）：`Fritzing.exe -svg <目录>` 导出的
  `pixel-pcb-v59_pcb.svg` 里，15 条 `stroke-width="24"` 中 **5 条写成 `<path d="M…C…">`** ✓
  （其余 10 条 `<line>` ✓）；与 `.fzz` 的 `p0/cp0/cp1/p3` 做**平移无关的形状比对** ⇒
  **逐点差 ≤ 0.000073 mm** ✓（1 导出单位 = 0.0254 mm ✓）⇒ 它画的弧**就是**文件里这条弧 ✓。
- **✗ 病根** ✓：`pcb_check.collect()` 只把两端点放进 `traces[i]` ✓ ⇒ `render_pcb` 只能画
  `<line>` ✗ ⇒ **弧被拉直** ✗ —— 而需求是「**Fritzing 里的画法我改不了，我只能看你两者是否一致**」✓
  （2026-10-01 用户定 ✓）。
- **已修** ✓（2026-10-08 ✓）：`pcb_wire.ctrl_pts()`（唯一定义 ✓）→ `pcb_check` 放进
  `traces[i]["bez"]` ✓ → `render_pcb` **有控制点就出 `<path d="M…C…">`** ✓（写法与导出一致 ✓，
  没有控制点的仍是 `<line>` ✓）。复核 ✓：重渲后我们自己的 5 条弧 vs 导出 **最大形状差 0.000256 mm** ✓
  （= 画布单位换算的取整 ✓）；栅格上沿**真弧**采样离墨 **≤0.9 px** ✓、沿**弦**采样离墨 **2.9～12.7 px** ✓。
  ⇒ 顺手重出了 14 版受影响的可提交预览（`pixel-pcb-v51/v57…v69_preview.*` ✓）＋ 库里那 3 张
  `diff-pcb-*` 差异图 ✓。
- ★★ **已全部改按真弧** ✓（2026-10-08 第二轮 ✓，用户「好的，改吧」✓）—— ✗ 上一轮只改到**渲染** ✗
  ⇒ 校验/量尺那一侧仍在按弦算 ✓，本轮补齐 ✓。分工与证据：

  | 谁 | 改了什么 ✓ | 依据 / 证据 ✓ |
  |---|---|---|
  | `pcb_wire.py` | 新增 `trace_pts()`／`poly_len()` = "**走线的真形状**"与"**沿真形状的总长**"的**唯一定义** ✓ | `ctrl_pts()` 那份控制点换算 ✓ |
  | `pcb_check.py` | `collect()` 给每条走线带 `pts`（采样点表 ✓）与 `curve`（是不是弧 ✓）；新增 `segs_of()` / `d_pt_trace()` / `trace_near_pt()` / `trace_rect_hit()` / `trace_trace_hit()` ✓ ⇒ ①端点挨线 ②板外 ④交叉 ④b压盘 ③过孔挨铜 ⑨安装孔 ⑩声明兼现 **一律看真几何** ✓ | **151 个 sketch 全扫** ✓：判词/条数变化 **0** ✓（✗ 一个也不许变 ✗）；纯直线的 `v47` 逐项**完全相同** ✓ |
  | ② 板外 ＋ ① 悬空 | 弧的**线身**也查 ✓（✗ 旧版只看两个端点 ✗ ⇒ 弧鼓出板外一个字不报 ✗） | 合成局：弧顶出板 **5.6 mm** ⇒ 旧 0 条、新 1 条 ✓ |
  | `pcb_metrics.py` | 线长 = 沿真弧 ✓ 拐角 = **端点处的切线** ✓（✗ 弦 ✗） | v59 总长 287.60 → **289.80 mm** ✓（弧比弦长 ≈0.8% ✓）；`v47` 198.40 → **198.40** ✓ 不变 |
  | `diff_revs.py` | 每块铜的线长同样走 `poly_len()` ✓ | `diff-pcb-v57-v59.md`：`5V` 37.0 → **38.4 mm** ✓、`GND` 40.9 → **41.1** ✓ |
  | `render_pcb.py` | 视口 bbox 也把**弧的采样点**包进来 ✓（✗ 只包两端点 ⇒ 弧鼓出去那段被裁掉 ✗） | 与本轮渲染修复同源 ✓ |

- ★★ **机器守** ✓（新增 ✓，`tools/pcb_curve_selftest.py` ✓）：**不用 fzz** ✓，直接在内存里合一个
  "弦看不见、弧看得见"的局 ✓ ⇒ 逐条验上面四条 ✓；退出码 0/1 ✓。四条局 + 反向自检
  （换成同一条弦的直线 ⇒ ②/⑨/④b 必须**全不报** ✓）实测：
  ① 弧线身贴另一条线（弦距 **8.47 mm** vs 真弧 **0.56 mm**）✓ 不报悬空 ✓；
  ② 弧鼓出板 5.6 mm ✓ 报 ✓；③ 过孔在弧上（弦距 8.47 mm）⇒ ✗ 弦口径报**假**孤立过孔 1 条 ✓、
  新口径 0 条 ✓；⑨ 孔被弧压 ⇒ 旧 0 条、新 **-0.536 mm** 1 条 ✓；④b 弧压别的网的盘 ⇒
  旧 0 条、新 1 条 ✓。★ 两边都实测过 ✓（弦那份跑在 `git worktree` 出来的旧提交上 ✓）。
- ★★ **两个坑**（都当场踩到过 ✓，写在这儿省下一次 ✓）：
  ① **"是不是弧"必须另有记号** ✗ —— `pts` **人人都有** ✓（直线就是 2 个点 ✓）⇒ ✗ 拿
     `pts` 当"有弧"的判据 ✗（第一版就这么写 ✓ ⇒ 量尺报成"**168 条弯曲**" ✗、整个角度谱变空 ✗）；
  ② 改了判据之后，**合模型的测试夹具**也得跟着补那个记号 ✗（否则五条局全假失败 ✓）。
- ★ 真实数据上"弦 vs 弧"的**量级** ✓（`_scratch/realdiff.py` ✓，v59/v65 共 18 条弧）：
  到板框的净距差最多 **2.03 mm** ✓、到过孔最多 **0.48 mm** ✓、到焊盘 **0.00** ✓（那几条弧本来
  就压在盘上 ✓）⇒ **差是真的** ✓，只是这 18 条恰好都没跨过阈值 ✓ ⇒ 判词才 0 变化 ✓。
- ★ **机器判据** ✓（2026-10-08 入库 ✓）：`tools/pcb_curve_check.py <sketch.fzz> <fritzing.svg>
  [--ours=<我们渲的.svg>]` ✓ —— ① 条数 ② **平移无关的形状**（逐点 ≤0.01 mm ✓）③ 我们渲的图里
  弯 `path` 条数必须 == 文件里的弯线数 ✓；退出码 0/1 ⇒ 可串进提交前检查 ✓。
  ★ **两个负例都当场打出来过** ✓：拿修之前的渲染 ⇒ 报「弯 `path` 0 条 ⇒ 有弧被拉成直弦了」✗ 退出 1 ✓；
  拿**不带 `--board-only`** 的渲染 ⇒ 报「板框 rect 宽高比 1.0052 ≠ 板的 1.0000 ⇒ 它多半是**取景框**」✗ 退出 1 ✓
  （这条 guard 是必需的 ✓：`render_pcb` 不带开关时会把视口胀成「板框 ∪ 墨迹」✗ ⇒ 拿它定标差 ~1% ✗，
  实测踩到过一次 ✓）。★ 拿导出当基准时**别按"板框就在页原点"读** ✗ —— 导出是**另开的页面** ✓，
  按那个假设读会整体错位 ✓（也踩过 ✗）⇒ 所以判据要**先去掉平移** ✓。

---

## 2. 我们照抄的口径（脚本里已执行的 ✓）

1. `wireExtras mils` 用**自己选的那一档** ✓（别写模块默认值 ✗）。
2. 数字**不用科学计数法** ✗ —— Fritzing 写的是 `0` / `-0.35466` 这种普通小数 ✓（`%.6g` 会写 `-3e-05` ✗）。
3. `<connect layer>` 写**对面那层** ✓（见 F4）。
4. `schematic`/`breadboard` 视图的连接**不在** PCB 走线上乱写 ✓。
5. **应补未补**：① 目标侧回指（F2 ✓）② 过孔 `<connects>`（F5 ✓）③ 视图数（待 §4-Q1 定 ✓）。
6. 读**导出 SVG** ✓：`partID` = `modelIndex` + **1 位层号** ✓；同件有**图形组 + `partLabel` 组** ✗ ⇒ 累加、跳过位号组 ✓（F13）。
7. 单位 ✓：`.fzz` 内部 **1/90 in** ✓、导出 **1/72 in** ✓ ⇒ 比值 **0.8** ✓（✗ 别写成 0.72 ✗，见 F12）。
8. 报“线长/位置/间隙”**只认导出复核** ✗ —— 我方渲染是自证 ✗（F14）。
9. 线端/线身**不许落在非本网焊盘**上（含**空脚** ✓）—— 但改前先看 §4-Q5 的连带问题 ✓。

---

## 3. 与本仓其它文档的关系

- 元件层（`.fzp` + 4 视图 svg）规则见 `docs/part-dev-guide.md` ✓；
- 本文只管**草图（`.fzz` 里的 `<instances>`）** ✓，两者不要混 ✗。

---

## 4. 待确认（下一步要量/要实验的 ✗）

- **Q1（已答 ✓，见 F9）**：**只带 `pcbView` 的走线实例，Fritzing 不认** ✗ ——
  用户实验判决：三视图的线**算** ✓（42→41 ✓）、我的单视图线**一条不算** ✗ ⇒ 必须写三视图 ✓。
  - 而非 PCB 两个视图的**坐标怎么填**仍未定 ✗（Fritzing 是各视图独立坐标 ✗）⇒
    本项目先试**零长度占位** ✓（不编坐标 ✗）；不行再算“PCB→面包板”的映射 ✓（会把面包板画花 ✗）。
- **Q2** ✗：`wireFlags` 的语义（128 / 64 / 0 / 32 都见过 ✓）—— 提 issue 可问 ✓。
- **Q3** ✗：`wireExtras` 的 `banded="0"` / `opacity` 语义 ✓。
- **Q4** ✗：`<property name="hole size">` 的合法取值表（见过 `0.6mm,0.3mm`、`0.4mm,0.3mm`）✓。
- **Q5** ✗（2026-10-01）：“**不许线压焊盘**”（含空脚 ✓）怎么落地 ——
  判据已有 ✓（`pcb_route.seg_hits_rect` / `pads_covered` ✓，一份实现 ✓），但**试过两版都坏** ✗：
  ① “压了就改成**端点不吸附**” ⇒ 端点差**半个格**（0.071 mm ✗）⇒ 写回器“端必须正中”的判据对不上 ✗
  ⇒ 报 6 个悬空端点 ✗ ⇒ **整份文件不写** ✗；
  ② “**永远吸附** + 被压的盘加硬禁位重布（避不开就保底留吸附版）” ⇒ 仍报 2 个悬空端点 ✗。
  ⇒ 真难点是**写回器的“端↔端 / 端↔盘 必须正中”** vs **布线器端点在栅格上** 这对矛盾 ✗
  ⇒ 先解它 ✓（或改走“焊盘净空大一点 + 栅格细一点”的路线 ✓）。

## 5. 可提给 Fritzing 的点（PR / issue 备选 ✓）

1. **静默忽略** ✗：走线实例结构不合口味时，**不报错、不提示、也不计入连通** ✗ ——
   用户只看到"0 网络布线完成" ✓，无从定位 ✓。（建议：加载时对"被丢弃的走线"给一条日志/提示 ✓）
2. **`<pcbView layer="breadboardbreadboard">`** ✗：面包板内容藏在 `pcbView` 标签里 ✓ ——
   读写方都要额外筛 `layer` ✓，容易错 ✓（见 F3）。
3. **一条走线实例三视图共用 connectors** ✓ ⇒ `<connect>` 只记一份、且可能指向**别的视图**的端点 ✓
   （F4 的 `pin16I` 例 ✗）⇒ 解析方无法"按视图"读连接 ✓，语义含糊 ✓。
4. **`Melody.fzz` 里 `<views />` 空走线实例** ✗（F1）—— 可能是历史遗留 ✓，可作为最小复现 ✓。
5. **`wireFlags` 无文档** ✗（F6）✓。
6. **载入时静默改写走线几何** ✗（F14）：81/260 个端点被挪 ✓、合计长度差 8.3% ✗ ——
   用户看到的图与自己给的几何不同 ✓，而且**没有任何提示** ✓
   （建议：日志/状态栏里说明“已吸附 N 处端点” ✓）。

## 6. 复现命令（scratch 脚本在项目仓 `hardware/pixel/_work/` ✓）

```powershell
# ① 逐项结构对照（样例 vs 我写的）
py -3.13 _work\cmp_wires.py <样例.fzz> <我写的.fzz> out.txt
# ② 一份 fzz 里"我插的 / 原有的"走线视图组合分布
py -3.13 _work\view_probe.py <要查.fzz> <扫描根…> out.txt
# ③ Fritzing 自带样例的全量统计（视图组合 / 回指）
py -3.13 _work\fritzing_stats.py "<Fritzing>\sketches\core" out.txt
# ④ 过孔原文取样
py -3.13 _work\via_probe.py "<Fritzing>\sketches\core" out.txt
# ⑤ XML 合法性（正则读不出语法错 ✗，必须用真解析器 ✓）
py -3.13 _work\xml_validate.py <a.fzz> [b.fzz …]
# ⑥ 拿导出 svg 与 fzz 逐条对账（单位 / partID / 端点位移）✓
py -3.13 _work\cmp_export2.py <fzz> <导出.svg> <out.txt>
# ⑦ 只查一件事：空脚（网表里没有的焊盘）被哪个铜碰到 ✗（端落在盘心 / 只是擦过 ✓）
py -3.13 _work\spare_pads.py <fzz> [<fzz> …]
# ⑧ 过孔的“真几何”：从**导出 svg** 量环的内外径 ＋ 与 fzz 声明点对账 ✓（F17 ✓）
py -3.13 _work\probe_via11.py
```

★ 注意 ✓：这些脚本目前是 **scratch（`_work/`）** ✓；
若将来要把 §5 提成 issue/PR，**建议把它们整理进 `tools/`** ✓（可复现 ✓）。
