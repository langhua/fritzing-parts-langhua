// Pixel 差异视图（差异图 + 差异清单）
//
// 用户 2026-10-07 要的：「把 md 文件与 svg/png 显示界面结合起来」。
//
// 干三件事：
//   ① 贡献一个**自定义编辑器**（viewType `pixelDiff.diffMd`），接管 `diff/diff-*.md`
//      ⇒ 打开清单时，左边就是那张叠合差异图（svg，矢量、可缩放），右边是清单。
//   ② 命令「比较两版」：从 `pixel-pcb-v*.fzz` 里选两版 ⇒ 跑 tools/diff_revs.py ⇒ 打开合并视图。
//   ③ 命令「比较两个文件」：fzz / svg 都行（svg 那侧用来比 Fritzing 导出的图）。
//
// 刻意**不做**的事（第一版求稳）：
//   · 不引任何依赖（纯 CommonJS，只要 node 内置模块）；
//   · webview **不开脚本**（enableScripts:false）⇒ 没有 CSP/nonce 那一摊事，也没有注入面；
//   · 不自己拼输出文件名 ✗ —— 生成完去 `diff/` 里挑**最新的 `diff-*.md`** ⇒
//     命名规则只有 diff_revs.py 一份实现（本仓老规矩：判据/公式只留一份）。

const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const path = require('path');

const VIEW = 'pixelDiff.diffMd';
const PY = process.env.PIXEL_PY || 'python';

let outCh = null;

function log(s) {
	if (!outCh) outCh = vscode.window.createOutputChannel('Pixel 差异');
	outCh.appendLine(s);
}

/** 找**项目目录**（放着 fzz 的那层 ✓，跑工具时当 cwd ✓）与**库仓根**（`tools/diff_revs.py` 在那儿 ✓）。
 *
 *  ★★ 2026-10-07 通用化 ✓（用户问：别的电路设计里怎么用 ✓）—— ✗ 不再只认
 *    `hardware/pixel` 那个死路径 ✗。探索顺序（先明确 ⇒ 后模糊 ✓）：
 *      ① 设置 `pixelDiff.projectDir` ✓（指哪就是哪 ✓）；
 *      ② 老路径 `<root>/hardware/pixel` ✓（本项目 ✓，保持兼容 ✓）；
 *      ③ `<root>` 自己 （含 fzz 就是 ✓）；
 *      ④ 往下**最多 3 层**找含 fzz 的目录 ✓（跳过 .git / node_modules / tools / diff …✓）。
 *    多个候选 ⇒ 取 **`diff/` 最近动过**的那个 ✓（正在干活的 ✓）；再平则**路径短**的 ✓（更靠上 ✓）。
 *
 *  ★ 实测（2026-10-07）：本项目 `hardware/pixel` 里 **151 个 fzz** ✓，但只有 **76 个**
 *    是 `pixel-pcb-v*` ✗（其余 75 个是 breadboard / schematic ✓）
 *    ⇒ 默认规则**不能**是「所有 fzz」✗ ⇒ 默认 `\.fzz$` ✓，本项目用设置钉住旧模式 ✓。
 */
function dirs() {
	const folders = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
	// ★ 找项目目录用**通用** fzz 规则 ✓（✗ 别用某个视图的模式 ✗ —— 这一层只要回答
	//   “哪个文件夹里放着电路稿” ✓，跟这次要比哪个视图无关 ✓）。
	const re = /\.fzz$/;
	let tool = null;
	for (const root of folders) {
		if (!tool && fs.existsSync(path.join(root, 'tools', 'diff_revs.py'))) tool = root;
	}
	const pinned = String(cfg().get('projectDir') || '').trim();
	const roots = pinned ? pinRoots(pinned, folders) : folders;
	const cands = [];
	const add = (d) => { if (d && !cands.includes(d) && fs.existsSync(d)) cands.push(d); };
	const walk = (dir, depth) => {
		if (depth > 3) return;                       // 边界：最多往下 3 层 ✓（别在大仓里乱转 ✗）
		if (hasFzz(dir, re)) add(dir);
		let ents;
		try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
		for (const e of ents) {
			if (!e.isDirectory() || e.name.startsWith('.') || SKIP_DIR.has(e.name)) continue;
			walk(path.join(dir, e.name), depth + 1);
		}
	};
	for (const root of roots) {
		add(path.join(root, 'hardware', 'pixel'));    // ② 老路径 ✓
		walk(root, 0);                                // ③④
	}
	cands.sort((a, b) => (recency(b) - recency(a)) || (a.length - b.length));
	return { proj: cands[0] || null, tool };
}

/** 扫目录时**跳过**的名字 ✓（避坑：`diff/` 里是 svg/png ✗、`tools/` 是工具 ✗）。 */
const SKIP_DIR = new Set(['node_modules', '__pycache__', '.venv', 'venv', 'env',
	'tools', 'diff', 'build', 'dist', 'out', 'target']);

/** 设置里的项目目录 ⇒ 绝对路径 ✓。
 *  ★ 绝对路径就直接用 ✓；**相对路径相对工作区根解** ✓ —— VS Code 设置里大家习惯写
 *    `hardware/pixel` 这种相对路径 ✓（写死在进程 cwd 上会找不到 ✗，实测踩到过 ✓）。
 */
function pinRoots(pinned, folders) {
	if (path.isAbsolute(pinned)) return [pinned];
	const all = folders.map((f) => path.join(f, pinned));
	const hit = all.filter((p) => fs.existsSync(p));
	return hit.length ? hit : all;
}

function cfg() { return vscode.workspace.getConfiguration('pixelDiff'); }

/** 视图 ⇒ 设置项名 ✓（一份实现管三个视图 ✓）。 */
const VIEW_PAT = { pcb: 'fzzPattern', bb: 'bbPattern', sch: 'schPattern' };
const VIEW_NAME = { pcb: 'PCB', bb: '面包板', sch: '原理图' };

/** `pixelDiff.<view>Pattern` ⇒ 正则 ✓（空/非法 ⇒ 退回 `\.fzz$` ＋ 记一笔 ✓）。 */
function patRe(view) {
	const key = VIEW_PAT[view] || 'fzzPattern';
	const raw = String(cfg().get(key) || '').trim() || '\\.fzz$';
	try { return new RegExp(raw); } catch (e) {
		log(`设置里 pixelDiff.${key} 不是合法正则 ⇒ 用默认 \\.fzz$ ：` + raw);
		return /\.fzz$/;
	}
}

/** PCB 的文件名模式 ✓（老名字，保留 ✓ —— 内部就是 `patRe('pcb')` ✓，不再有第二套 ✓）。 */
function fzzRe() { return patRe('pcb'); }

/** 这层目录里**有没有**符合模式的 fzz 文件 ✓（读不到就当没有 ✓）。 */
function hasFzz(dir, re) {
	try {
		return fs.readdirSync(dir, { withFileTypes: true })
			.some((e) => e.isFile() && re.test(e.name));
	} catch { return false; }
}

/** 这层目录的 `diff/` 里最后一次改动时间 ✓（用来挑"正在干活"的那个 ✓；没有=0 ✓）。 */
function recency(dir) {
	try {
		return fs.readdirSync(path.join(dir, 'diff'))
			.reduce((m, n) => Math.max(m, fs.statSync(path.join(dir, 'diff', n)).mtimeMs), 0);
	} catch { return 0; }
}

/** 当前模式下的版本文件 ✓（按版本号排 ✓；不像 `-vN` 的排最前 ✓）。
 *  ★ 模式从设置来 ✓（`pixelDiff.fzzPattern` ✓）—— ✗ 不再写死 `pixel-pcb-v` ✗。
 */
function listVersions(dir, pattern) {
	const re = pattern ? new RegExp(pattern) : fzzRe();
	const key = (n) => {
		const m = /-v(\d+)([\s\S]*)$/.exec(n.replace(/\.fzz$/, ''));
		return m ? [Number(m[1]), m[2] ? 1 : 0, m[2]] : [0, 0, n];
	};
	return fs.readdirSync(dir).filter((n) => re.test(n))
		.sort((a, b) => {
			const x = key(a), y = key(b);
			return (x[0] - y[0]) || (x[1] - y[1]) || String(x[2]).localeCompare(String(y[2]));
		});
}

/** 跑 `diff_revs.py` ✓（工具在库里 ✓、**cwd 给项目目录** ✓ ⇒ 输出落到项目的 `diff/` ✓）。
 *  ★ 两个文件都传**绝对路径** ✓ ⇒ `diff_revs.py` 的 `_resolve()` 直接命中
 *    ⇒ **文件名怎么取都行** ✓（解耦 ✓；不再要求 `-vN` 那种名字 ✓）。
 *  ★ `--pattern` 跟设置同步 ✓（工具只拿它去列 `have` ✓，传绝对路径后不影响结果 ✓）。
 *  日志进输出通道；`PYTHONIOENCODING` 必须给 —— 否则中文/✓ 会撞 GBK 控制台。
 */
function runDiff(toolDir, projDir, a, b, view) {
	const tool = path.join(toolDir, 'tools', 'diff_revs.py');
	const abs = (p) => (path.isAbsolute(p) ? p : path.join(projDir, p));
	const v = view || 'pcb';
	const args = [tool, '--view', v, '--pattern', patRe(v).source, abs(a), abs(b)];
	return new Promise((resolve) => {
		log(`\n> ${PY} ${args.map((s) => `"${s}"`).join(' ')}   （cwd=${projDir}）`);
		cp.execFile(PY, args, {
			cwd: projDir,
			env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8' }),
			maxBuffer: 32 * 1024 * 1024
		}, (err, stdout, stderr) => {
			const txt = String(stdout || '') + String(stderr || '');
			log(txt.trim());
			resolve({ code: err ? (err.code === undefined ? 1 : err.code) : 0, text: txt });
		});
	});
}

/** `diff/` 里最新的 `diff-*.md`（刚跑完那个）。 */
function newestDiffMd(dir) {
	const d = path.join(dir, 'diff');
	if (!fs.existsSync(d)) return null;
	const hit = fs.readdirSync(d).filter((n) => /^diff-.*\.md$/.test(n))
		.map((n) => ({ n, t: fs.statSync(path.join(d, n)).mtimeMs }))
		.sort((a, b) => b.t - a.t);
	return hit.length ? path.join(d, hit[0].n) : null;
}

function esc(s) {
	return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** 极简 markdown ⇒ html（只应付 diff_revs.py 写出来的那几种：标题 / 列表 / 引用 / 行内）。 */
function mdToHtml(md) {
	const inline = (s) => esc(s)
		.replace(/`([^`]+)`/g, '<code>$1</code>')
		.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
	const out = [];
	let inUl = false;
	const closeUl = () => { if (inUl) { out.push('</ul>'); inUl = false; } };
	for (const raw of String(md).split(/\r?\n/)) {
		const line = raw.replace(/\s+$/, '');
		let m;
		if (!line.trim()) { closeUl(); continue; }
		if ((m = /^#\s+(.*)$/.exec(line))) { closeUl(); out.push(`<h1>${inline(m[1])}</h1>`); continue; }
		if ((m = /^##\s+(.*)$/.exec(line))) { closeUl(); out.push(`<h2>${inline(m[1])}</h2>`); continue; }
		if ((m = /^###\s+(.*)$/.exec(line))) { closeUl(); out.push(`<h3>${inline(m[1])}</h3>`); continue; }
		if ((m = /^>\s?(.*)$/.exec(line))) { closeUl(); out.push(`<blockquote>${inline(m[1])}</blockquote>`); continue; }
		if ((m = /^\s*[-*]\s+(.*)$/.exec(line))) {
			if (!inUl) { out.push('<ul>'); inUl = true; }
			out.push(`<li>${inline(m[1])}</li>`);
			continue;
		}
		closeUl();
		out.push(`<p>${inline(line)}</p>`);
	}
	closeUl();
	return out.join('\n');
}

// 「点清单一条 ⇒ 图上高亮」的那段脚本（2026-10-07 用户要的）。
//   · 脚名从行**文字**里认：`C1.connector0` 这个形状 ✓
//     ★★ 2026-10-07 实测踩到 ✗：清单原文里脚名是**反引号**包着的（`C1.connector0` ✓），
//        但转成 HTML 后反引号变成 `<code>` 标记 ⇒ **`textContent` 里根本没有反引号** ✗
//        ⇒ 按反引号写的正则**一条都匹配不上** ✗ ⇒ 表现就是用户说的「**文字无法点击**」✗。
//        ⇒ 直接按"**位号.connectorN**"这个形状认 ✓（② 里“脚：U1.connector5、…”那种也能点 ✓，正好有用 ✓）。
//   · 高亮组是 diff_revs.py **已经写进 svg** 的隐藏组（id = `pd-<脚名>`）
//     ⇒ 这里只切 display，**不算任何坐标**（坐标只有工具一份）。
// ★ 用**单引号字符串数组**拼，不用模板串 —— 免得里面的反斜杠/花括号跟外层 `${}` 打架。
const PAD_RE_SRC = '([A-Za-z][\\w.-]*\\.connector\\d+)';   // 与单测共用这一份图案 ✓
// ★ 第二类可点的行 ✓（2026-10-07 加 ✓，同日修正 ✗）：面包板/原理图清单里的「**位号**：…」✓
//   —— 那儿的行没有 `.connectorN` ✗ ⇒ 靠「行首一个标识符 + 冒号」认 ✓。
//   ★★ 第一版写成 `\*\*([^*]+)\*\*[：:]` ✗ —— 那是按 **markdown 源码** 写的 ✗，
//      而浏览器里的文字早被 `mdToHtml` 转成 `<b>C1</b>：…` ✗ ⇒ `textContent` 里
//      **没有星号** ✗ ⇒ 一条也匹配不上 ✗（用户当场指出「右侧元件摆位下的内容无法点击」✗）。
//      **与上次那个反引号坑是同一类** ✗ ⇒ 图案一律按**渲染后的文字**写 ✓。
const ROW_RE_SRC = '^\\s*([A-Za-z][\\w.-]*)[：:]';

/** 把图案源码变成**能嵌进 webview 的正则字面量** ✓（只转义 `/` ✓）。
 *
 *  ★★ 2026-10-07 修 ✗：原来嵌的是 `new RegExp(JSON.stringify(PAD_RE_SRC))` ✗ ——
 *    `JSON.stringify` 会给源码**套上引号** ✓ ⇒ 正则就变成“要求两侧有字面量引号” ✗
 *    ⇒ **一条也匹配不上、哪里都点不动** ✗（含 PCB ✗）。
 *    而单测用的是 `new RegExp(PAD_RE_SRC)` ✗ ⇒ **抓不到这个错** ✗（正是“两套实现”的坑 ✓）
 *    ⇒ 注入与单测**共用这一个 `reLit`** ✓。
 */
function reLit(src) { return src.replace(/\//g, '\\/'); }

/** 图上**可点名字**的清单 ✓：`#pd-hits` 里那些 `pd-*` 组的组名 ✓（与工具**同一份数据** ✓）。
 *
 *  ★★ 2026-10-08 修 ✗：原来靠"从 `pd-hits` 切到 `pd-labels`"来划范围 ✗ ——
 *    而**标签层已经撤掉了** ✗（用户：「把这些文字提示去掉」✓）⇒ 那个右边界不存在了 ✓
 *    ⇒ 切到文末 ⇒ 会把别处的 `pd-*` 也收进来 ✓。⇒ 改成**按名收** ✓：
 *    凡 `<g id="pd-…">` 都算 ✓，只排除两个**容器**（`pd-hits` / `pd-labels` ✓）。
 */
function keysOf(svgText) {
	if (!svgText) return [];
	const set = new Set();
	for (const m of String(svgText).matchAll(/<g id="pd-([^"]+)"/g)) {
		if (m[1] !== 'hits' && m[1] !== 'labels') set.add(m[1]);
	}
	// ★ 键**长的在前** ✓（`RC.2` 必须先于 `RC` 去比 ✓）
	return [...set].sort((a, b) => b.length - a.length);
}

/** `mdToHtml()` 的产物 ⇒ 把**可点名字**逐个包成 `span.pd-hit` ✓（✗ 只在**文字**里包 ✗，属性里不碰 ✓）。
 *
 *  ★★ 2026-10-08 把这一步从**运行时 JS** 搬到这里 ✓（原来是往 webview 里塞一段 TreeWalker 脚本 ✗）：
 *    那段脚本有个**吃字**的 bug ✗ —— 它从头扫文本节点，**遇到第一个名字之前**攒下的字符
 *    **直接丢掉** ✗（`if (frag) buf += …` ✗，`frag` 还是 null 时就不攒了 ✓）⇒ 实测用户清单里
 *    「`**新增**：pin11I–pin13I（Wire90013126）`」**渲染出来只剩**「`新增Wire90013126）`」✗✗
 *    —— 前半句整段没了 ✓。搬到 Node 还有个好处 ✓：这是**纯函数** ✓ ⇒ 单测能直接判
 *    「**去标签后的文字 == 原文字**」✓（不吃字 ✓），不必开浏览器 ✓。
 */
function markNames(htmlText, keys) {
	if (!keys || !keys.length) return htmlText;
	const h = String(htmlText);
	let out = "", i = 0;
	while (i < h.length) {
		if (h[i] === '<') {                     // ★ 整段标签跳过 ✓（属性值里的名字**不动** ✓）
			const j = h.indexOf('>', i);
			const k = j < 0 ? h.length : j + 1;
			out += h.slice(i, k); i = k; continue;
		}
		let hit = null;
		for (const kk of keys) if (h.startsWith(kk, i)) { hit = kk; break; }
		if (!hit) { out += h[i]; i++; continue; }
		out += '<span class="pd-hit" data-k="pd-' + esc(hit) + '">' + esc(hit) + '</span>';
		i += hit.length;
	}
	return out;
}

/** ★★ 「点名字 ⇒ 图上高亮」的**点击**那半段 ✓ —— 自定义编辑器与幻灯片**共用这一份** ✗（别抄两遍 ✓）。
 *
 *  ★ 名字**由 `markNames()` 在 Node 里包好** ✓（见那里为什么搬过来 ✓）；这段只管**点** ✓。
 *  ★★ 2026-10-08 修 ✗：原来靠两条**图案**去文字里猜（`X.connectorN` ✗ / `行首标识符＋冒号` ✗）
 *    ⇒ 面包板/原理图清单里那种「新增：Wire90013119、Wire90013121、…」**两条都不像** ✗
 *    ⇒ 一整串导线名字点不动 ✗（用户截图当场指出 ✗）。
 *    ⇒ 改成**别猜** ✓：谁可点，**图上说了算** ✓ —— 可点名字 = `pd-*` 隐藏组的组名 ✓。
 *  ★ 高亮组本来就是 `diff_revs.py` **写进 svg** 的隐藏组（id = `pd-<名字>` ✓）
 *    ⇒ 这里只切 `display` ✓，**不算任何坐标** ✓（坐标只有工具一份 ✓）。
 */
function markJs(pane) {
	return [
		'  (function(){',
		'    var pane = document.querySelector(' + JSON.stringify(pane) + ');',
		'    if (!pane) return;',
		'    pane.addEventListener("click", function(e){',
		'      var t = e.target;',
		'      while (t && t !== pane && !(t.className && ("" + t.className).indexOf("pd-hit") >= 0)) t = t.parentNode;',
		'      if (!t || t === pane) return;',
		'      var el = document.getElementById(t.getAttribute("data-k"));',
		'      clear();',
		'      var sel = document.querySelectorAll(".pd-hit.sel");',
		'      for (var z = 0; z < sel.length; z++) sel[z].classList.remove("sel");',
		'      if (!el) return;',
		'      if (SVG) SVG.classList.add("pd-focus");',
		'      el.style.display = ""; t.classList.add("sel");',
		'    });',
		'  })();'
	].join('\n');
}
/** ★★ 「▶ 重放动画」的**起播那一段** ✓ —— 合并视图与幻灯片**共用这一份** ✗（别抄两遍 ✓）。
 *
 *  ★★ 2026-10-08 定（用户）：「**进入时不自动播放**，而是显示 A+B ✓；点击【重放动画】时，
 *    才从 A 开始变化到 B ✓，并在结束后**停留在 B**」✓。
 *  ★ 所以图（svg ✓）里只有 `data-anim="<名字>"`（每个变化组 ✓）＋ 根上的 `data-anim-dur`
 *    （一轮时长 s ✓）✓，`animation` 一律**不预先写** ✗ —— 写了就一进页面自己跑 ✓。
 *  ★ 起播为什么要"先置 `none` ⇒ 强制重排 ⇒ 再赋" ✗：同一条 `animation` 再赋一遍浏览器
 *    **不重启动画** ✗ ⇒ 点了没反应 ✓（这是"点按钮重播"最容易漏的一步 ✓）。
 *  ★✗ 为什么**不能**只写 `getAnimations().currentTime = 0` ✗（上一版就是那么写的 ✓）：
 *    那只能重播**已经在跑或已跑完**的动画 ✓ —— 而进来时**根本没有动画** ✗ ⇒ 点了毫无反应 ✓
 *    ⇒ 用户当场报「点击重放按钮没有反应」✓。**兜底**留着这一条 ✓：万一图还是**老格式**
 *    （`animation` 写死在元素上 ✓）也能重播 ✓。
 *  ★ `forwards` ✗ 不能省：不写的话动画一结束元素就**弹回**初始 ✗（A 又全亮 ✓、B 又全灭 ✓）
 *    ⇒ "停留在 B" 当场作废 ✓。
 *  ★ 按钮**回显**（「▶ 重放中…」⇒ 播完还原 ✓）：就一个 `setTimeout` ✓ ——
 *    它同时是**诊断** ✓：点了字会变 ⇒ 点击**收到了** ✓；字都不变 ⇒ 起播脚本根本没跑 ✓
 *    （多半是扩展没重载 ✓，见 README ✓）。
 *
 *  ★★ 2026-10-08 踩过的坑（**用户当场报「点击重放按钮没有反应」** ✓）：这段原来是**数组** ✓，
 *    而我在外层写成 `...replayJs(),` ✗ —— `Array.join()` 会把**嵌套数组**按 `,` 拼进来 ✗
 *    ⇒ 生成的是 `function pdReplay(){,    var svg = …` ✗ ⇒ **整段 webview 脚本语法错误** ✗
 *    ⇒ 一个字符都不执行 ✓ ⇒ 按钮**点了毫无反应** ✓（而且高亮、Esc 也一起失效 ✓）。
 *    ⇒ 必须写成 `...replayJs(),`（展开 ✓）；★ 并且**单测第 ⑰ 项**现在直接 `new Function(脚本)`
 *    做语法检查 ✓ —— ✗ 光"HTML 里有那串字"是不够的 ✗（这个坑就是这么溜过去的 ✓）。
 *
 * ★★ 2026-10-08：**派生的东西都收进来** ✓（定义 ＋ 绑事件），两个界面都只写 `...replayJs()` ✓ ——
 *   ✗ 别在合并视图里绑一遍、幻灯片里再绑一遍 ✗（`#pd-replay` 两边同名 ✓ ⇒ 一份就够 ✓，
 *   而且"只有一个实现"这件事**机器能验** ✓ —— 见单测第 ⑯ 项 ✓）。
 */
function replayJs() {
	return [
		'  function pdReplay(){',
		'    var svg = document.getElementById("pd-svg") || document.querySelector("#art svg")',
		'      || document.querySelector(".left svg") || document.querySelector("svg");',
		'    var dur = (svg && svg.getAttribute("data-anim-dur")) || "0";',
		'    var els = document.querySelectorAll("[data-anim]");',
		'    var n = 0, i;',
		'    if (els.length && Number(dur) > 0) {',
		'      for (i = 0; i < els.length; i++) els[i].style.animation = "none";',
		'      void document.body.offsetWidth;              // 强制重排 ⇒ 动画才真的从头 ✓',
		'      for (i = 0; i < els.length; i++) {',
		'        els[i].style.animation = els[i].getAttribute("data-anim") + " " + dur + "s linear 1 forwards";',
		'      }',
		'      n = els.length;',
		'    } else {',
		'      var as = document.getAnimations ? document.getAnimations() : [];',
		'      for (i = 0; i < as.length; i++) { try { as[i].currentTime = 0; } catch (e) {} }',
		'      n = as.length;',
		'    }',
		'    if (window.__pdLog) {',
		'      window.__pdLog("重放：图上 data-anim 元素 " + els.length + " 个、data-anim-dur = " + dur',
		'        + " ⇒ 起了 " + n + " 个动画" + (n ? "" : "（✗ 一个都没起 ⇒ 图是不是老格式 / 是不是没重载扩展）"));',
		'    }',
		'    var btn = document.getElementById("pd-replay") || document.getElementById("replay");',
		'    if (btn && n) {',
		// ★★ 回显**只改文字那一块** ✗ 别整个 textContent 覆盖 ✗（2026-10-08 实测撞到过 ✓）：
		//   · 幻灯片那个按钮里是"**画出来的图形** ＋ 文字" ✓（`.step` ＋ `.lbl` ✓）⇒
		//     整体覆盖会把图形**冲掉** ✓（回来的时候也只剩文字 ✗）；
		//   · 合并视图那个按钮**没有** `.lbl` ✓ ⇒ 回落到按钮自己 ✓（它就是一串文字 ✓）。
		// ★★ 原字**只记一次** ✓，计时器**先清再设** ✓（2026-10-08 用户报「点击一次，就一直在重放中，
		//   不会停止了吗？」✓ ⇒ 去连点两次复现了 ✓）：原来是每次点都 `t0 = 当前文字` ✗ ⇒
		//   播到一半再点一下，`t0` 抓到的已经是 **「重放中…」** ✓ ⇒ 到点还原成"重放中…" ✓
		//   ⇒ **永远卡在「重放中…」** ✗（实测点两次、再等 9 秒还是「重放中…」✓）。
		//   ⇒ 如今 `__pdT0` 存**第一次**的原字 ✓、`__pdTimer` 每次先 clearTimeout ✓
		//   ⇒ 点几次都能还原 ✓。
		'      var lbl = btn.querySelector(".lbl") || btn;',
		'      if (btn.__pdT0 == null) btn.__pdT0 = lbl.textContent;',
		'      lbl.textContent = "重放中…";',
		'      clearTimeout(btn.__pdTimer);',
		'      btn.__pdTimer = setTimeout(function(){',
		'        lbl.textContent = btn.__pdT0; btn.__pdT0 = null;',
		'      }, Number(dur) * 1000 + 200);',
		'    }',
		'  }',
		// ★ 绑事件也放这儿 ✓ ⇒ 两个界面都自动有 ✓（✗ 别各绑一遍 ✗）
		'  var rp = document.getElementById("pd-replay");',
		'  if (rp) rp.addEventListener("click", function(){ pdReplay(); });'
	];
}

const JS = [
	'(function(){',
	'  var api = null; try { api = acquireVsCodeApi(); } catch (e) {}',
	'  window.__pdLog = function(t){ try { if (api) api.postMessage({ cmd: "log", text: t }); } catch (e) {} };',
	'  var SVG = document.getElementById("pd-svg") || document.querySelector(".left svg") || document.querySelector("svg");',
	'  var li = Array.prototype.slice.call(document.querySelectorAll("li"));',
	'  function clear(){',
	'    if (SVG) SVG.classList.remove("pd-focus");',
	'    var g = document.querySelectorAll("#pd-hits > g");',
	'    for (var i = 0; i < g.length; i++) g[i].style.display = "none";',
	'    li.forEach(function(x){ x.classList.remove("sel"); });',
	'  }',
	markJs('.right'),
	'  document.addEventListener("keydown", function(e){ if (e.key === "Escape") clear(); });',
	'  if (SVG) SVG.addEventListener("click", clear);',
	// ★★ 2026-10-08 用户定 ✓：按钮**在图的下面** ✓（原话：「把这个嵌入在差异的下面就好了吧？」✓）——
	//   它原来在**右栏工具条**上 ✓，离图很远 ✗；现在贴在 `.left`（图那一栏 ✓）里图的**正下方** ✓，
	//   并且 `position:sticky; bottom:0` ✓ ⇒ 图比一屏高时也**始终够得着** ✓（✗ 别又变成"找不到按钮" ✗）。
	//   ★ 绑定在 `replayJs()` 里 ✓（两个界面共用一份 ✓），这里只把定义与绑定**展开**进来 ✓。
	...replayJs(),                       // ★ 展开 ✗ 别写成 `replayJs(),` ✗ —— 见 `replayJs()` 处的教训 ✓
	'})();'
].join('\n');

// ★ HTML/CSS **只留一份** ✓（自定义编辑器与幻灯片共用 ✓）—— ✗ 别在幻灯片里再抄一遍 ✗。
const CSS = `
  body { margin:0; font-family: var(--vscode-font-family); color: var(--vscode-editor-foreground); }
  .wrap { display:flex; height:100vh; }
  .pane { overflow:auto; }
  /* ★ 图的这一栏改成**竖排** ✓（图 ＋ 图下面那个「▶ 重放动画」✓）——
     ✗ 原来 justify-content:center 是"图只一个、横向居中"用的 ✓，多一个孩子就变成并排了 ✗。
     ★ 这里在**模板字符串**里 ⇒ ✗ 注释里别写反引号 ✗（一写就把模板截断 ✓ —— 当天踩过两次 ✓）。 */
  .left { flex:2 1 0; background:#ffffff; display:flex; flex-direction:column; align-items:center;
          padding:8px; box-sizing:border-box; }
  .art { max-width:100%; }
  .left img, .art svg { max-width:100%; height:auto; }
  .art svg { cursor:default; }
  /* ★★ 2026-10-08 用户定 ✓：「把这个（▶ 重放动画）**嵌入在差异的下面**就好了吧？」✓
     ⇒ 按钮贴在图的**正下方** ✓；sticky bottom ⇒ 图比一屏高时**始终够得着** ✓。 */
  .under { position:sticky; bottom:0; margin-top:8px; padding:2px 6px;
           background: var(--vscode-editor-background); border-radius:3px; }
  .right { flex:1 1 0; padding:10px 14px; border-left:1px solid var(--vscode-panel-border);
           /* ★★ 2026-10-08 用户定 ✗：「右侧内容字体可以小一些，**跟重放动画几个字的字体一样大**即可」✓
              ⇒ 整块右栏统一 **12px** ✓（＝ 那个按钮的字号 ✓），标题也不再放大（见下 ✓）。 */
           font-size:12px; line-height:1.5; }
  /* ★★ 2026-10-08：这条工具条现在**两个界面共用** ✓ ——
     · 合并视图：里面是那句高亮提示 ✓（要暗一些 ⇒ 提示自己带 .dim ✓）；
     · 幻灯片：里面是**「▶ 播放差异」** ✓（用户：「在右侧、『面包板差异清单』上方显示【播放差异】」✓）
       ★ ⇒ 那条 opacity:.75 **从 .bar 挪到 .bar .dim** ✓：✗ 放在 .bar 上会把按钮也一起调暗 ✗
       （opacity 不能靠孩子"调回来" ✓ —— 它是在**整棵子树渲染完**之后再统一压暗的 ✓）。
     ★ 钉在顶上 ✓：清单往往长过一屏 ✓ ⇒ 一滚按钮就"看不见"了 ✗。 */
  .bar { font-size:12px; padding:4px 8px; border-bottom:1px solid var(--vscode-panel-border);
         position:sticky; top:0; z-index:2; background: var(--vscode-editor-background); }
  .bar .dim { opacity:.75; }
  /* ★★ 2026-10-08：按钮**内容与文字都要竖向居中** ✓ —— 幻灯片那个按钮里是"画出来的图形 ＋ 文字" ✓
     （.step ＋ .lbl ✓），✗ 不是一整串文字 ✗ ⇒ 得让这两块自己对齐 ✓。
     ★ 对合并视图那个按钮**无害** ✓（它只有一个文本节点 ⇒ 匿名 flex item ✓，居中照旧 ✓）。 */
  .bar button, .under button { font-size:12px; cursor:pointer; color:inherit; background:transparent;
                border:1px solid var(--vscode-panel-border); border-radius:3px; padding:1px 6px;
                display:inline-flex; align-items:center; gap:4px; vertical-align:middle; }
  /* ★ 标题一律**跟正文同号** ✓（1em = 12px ✓）⇒ 只剩**粗体**做层级 ✓（用户要"一样大"✓） */
  h1, h2, h3 { font-size:1em; }
  h1 { margin:.2em 0 .4em; } h2 { margin-top:1.1em; } h3 { margin-top:1em; }
  code { background: var(--vscode-textCodeBlock-background); padding:0 3px; border-radius:3px; }
  blockquote { margin:.4em 0; padding-left:8px; border-left:3px solid var(--vscode-panel-border); opacity:.85; }
  ul { padding-left:1.2em; margin:.2em 0; }
  li.clickable { cursor:pointer; border-radius:3px; }
  li.clickable:hover { background: var(--vscode-list-hoverBackground); }
  li.sel { background: var(--vscode-list-activeSelectionBackground); }
  /* ★ 清单里的**单个名字**（由图上 pd-* 数据标出来 ✓）：点了就在图上亮那一条 ✓ */
  .pd-hit { cursor:pointer; border-radius:3px; padding:0 1px; }
  .pd-hit:hover { background: var(--vscode-list-hoverBackground); }
  .pd-hit.sel { background: var(--vscode-list-activeSelectionBackground); }
  .hint { color: var(--vscode-errorForeground); }
`;

/** 把某个 svg 读成**能内联**的片段 ✓（去掉 xml 声明/注释 ＋ 给根一个 id ✓）——
 *  自定义编辑器与幻灯片**共用这一份** ✓（✗ 别写两遍 ✗）。 */
function inlineSvg(svgPath) {
	if (!fs.existsSync(svgPath)) return null;
	return fs.readFileSync(svgPath, 'utf8')
		.replace(/^[\s\S]*?<svg\b/, '<svg')
		.replace(/^<svg\b(?!\s+id=)/, '<svg id="pd-svg"');
}

function html(webview, mdText, svgText, imgUri, imgName, hint, nonce) {
	const csp = `default-src 'none'; img-src ${webview.cspSource} data:; `
		+ `style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;
	const art = svgText
		? `<div class="art">${svgText}</div>`
		: (imgUri ? `<img src="${imgUri}" alt="${esc(imgName || 'diff')}">`
			: `<div class="hint" style="padding:16px">${esc(hint || '还没生成差异图')}</div>`);
	// ★★ 2026-10-08：`▶ 重放动画` 从右栏工具条**搬到了图的正下方** ✓（`.under` ✓ —— 见 CSS 与 JS 处的注释 ✓）。
	const under = svgText ? '<div class="under"><button id="pd-replay">▶ 重放动画</button></div>' : '';
	return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>${CSS}</style></head><body>
<div class="wrap">
  <div class="pane left">${art}${under}</div>
  <div class="pane right">
    <div class="bar"><span class="dim">${svgText ? '点 ① ② 里任意一条 ⇒ 图上高亮（Esc 或点图取消）'
		: (imgUri ? esc(imgName) : '（无图）')}</span></div>
    ${svgText ? markNames(mdToHtml(mdText), keysOf(svgText)) : mdToHtml(mdText)}
  </div>
</div>
<script nonce="${nonce}">${svgText ? JS : ''}</script>
</body></html>`;
}

// ── 幻灯片：把所有 `diff-*.md` 串起来，一页一页翻 / 自动播放 ✓（2026-10-07 用户要的 ✓）──
//   · **顺序**按版本号排 ✓（`diff-v59-v76.md` ⇒ (59, 76) ✓；同 A 的按 B 排 ✓）；
//   · 翻页/自动播放都在 **webview 里**（键盘 ←/→、空格 ✓）
//     ⇒ 扩展只负责「给我第 k 页」✓（每页现读现给 ✓ ⇒ 不把 N 页的 svg 一次性塞进内存 ✓）。
function pageList(proj) {
	const d = path.join(proj, 'diff');
	if (!fs.existsSync(d)) return [];
	// ★ 2026-10-07：名字多了**视图段** ✓ —— `diff-bb-v100-v104.md` / `diff-sch-v29-v40.md`
	//   （没视图段的就是老的 PCB ✓）。✗ 不改这条 ⇒ 新页会排在最后、顺序乱 ✗。
	const ORD = { pcb: 0, bb: 1, sch: 2 };
	const key = (n) => {
		const m = /^diff-(pcb-|bb-|sch-)?v(\d+)([^-]*)-v(\d+)([^.]*)\.md$/.exec(n);
		if (!m) return [9e8, 9e8, 9e8, n];                 // 认不出 ⇒ 排最后 ✓
		return [ORD[(m[1] || 'pcb-').slice(0, -1)], Number(m[2]), Number(m[4]), n];
	};
	return fs.readdirSync(d).filter((n) => /^diff-.*\.md$/.test(n))
		.sort((a, b) => {
			const x = key(a), y = key(b);
			return (x[0] - y[0]) || (x[1] - y[1]) || (x[2] - y[2])
				|| String(x[3]).localeCompare(String(y[3]));
		})
		.map((n) => path.join(d, n));
}

/** 一页的内容 ✓（标题 ＋ 内联 svg ＋ 已转好的清单 HTML ✓）。 */
function readPage(mdPath) {
	const dir = path.dirname(mdPath);
	const name = path.basename(mdPath);
	const stem = name.replace(/\.md$/, '');
	const svg = inlineSvg(path.join(dir, stem + '.svg'));
	// ★ 可点名字在**这里**（Node 一侧）就包好 ✓（与合并视图同一份 `markNames()` ✓，
	//   ✗ 别让 webview 再去猜文字 ✗ —— 见 `markNames()` 里那个"吃字"的教训 ✓）
	return {
		// ★★ 2026-10-08 用户问 ✓：「**文件名不加扩展名吗**？」✓ —— 原来是 `stem` ✗（`diff-bb-v95-v104` ✓）
		//   ⇒ 而同一目录里 `.md` / `.svg` / `.png` **同名的有三个** ✓ ⇒ 光看 stem **分不出指的是哪个** ✗。
		//   这一页本来就是那个 **`.md`**（双击进合并视图的就是它 ✓、幻灯片串的也是它 ✓）⇒ 带上 ✓。
		title: name,
		svg,
		html: markNames(mdToHtml(fs.readFileSync(mdPath, 'utf8')), keysOf(svg))
	};
}

// 幻灯片里的脚本：翻页 ＋ 自动播放 ＋ 键盘 ✓，并**保持**「点行 ⇒ 高亮」✓（每换一页重新绑 ✓）。
//   ★★ 2026-10-08 **第二次改**（用户：「面包板差异是可以在右侧、『面包板差异清单』上方
//     显示【播放差异】的吧？」✓）：**右栏顶上加回了播放按钮** ✓（`#pd-replay` ✓）——
//     ★ 撤掉的只是**顶栏（`← ▶ →` 那条）**上那个 ✗（用户：「建议删掉工具栏的【重放动画】按钮」✓）；
//     起播**共用** `replayJs()` ✓（函数 ＋ 绑事件都在里面 ✓ ⇒ 这里 `...replayJs()` 展开一次即可 ✓，
//     ✗ 别另写一段 ✗）。
//   ★ 「每换一页」时**不用做什么** ✓：新页的 svg 是**现读现给**的 ✓ ⇒ 里面**没有**内联
//     `animation` ✓ ⇒ 进来永远是**静止的 A+B** ✓，点了才从 A 演到 B ✓（与合并视图同一条口径 ✓）。
const SLIDE_JS = [
	'(function(){',
	'  var api = acquireVsCodeApi();',
	'  var idx = -1, total = 0, timer = null;',
	'  function $(id){ return document.getElementById(id); }',
	// ★★ 2026-10-08 用户定 ✓：「最长 40 个字符吧，再长就省略」✓
	//   ＋「**文件名不加扩展名吗**？」✓ ⇒ 显示的是**带扩展名**的名字 ✓（见 `readPage()` ✓）。
	//   ⇒ **显示**最多 40 个字符（把省略号也算进去 ✓），超了用省略号收尾 ✓，
	//     但**扩展名留到最后** ✗（超长时截**主干** ✓，尾巴补 `…` ＋ `.md` ✓ ——
	//     否则"要看见扩展名"这条在长名字上直接失效 ✓，整串仍 ≤ 40 ✓）。
	//   ★ 为什么不能只靠 CSS ✗：text-overflow:ellipsis 是**按宽度**截的 ✓ ——
	//     窗口宽时 100 个字符也照样全显示 ✗，压不住"最长 40 个"这条 ✓（两条一起用 ✓：
	//     这里限**字数** ✓，CSS 限**宽度** ✓）。title 仍挂全名 ✓（悬停看全 ✓）。
	'  function clip(s){',
	'    s = String(s);',
	'    var a = Array.prototype.slice.call(s);',   // 按**码位**数 ✓（✗ 别数 UTF-16 单元 ✗）
	'    if (a.length <= 40) return s;',
	'    var m = /\\.[0-9A-Za-z]+$/.exec(s);',
	'    var ext = (m && m[0].length <= 10) ? m[0] : "";',
	'    return a.slice(0, Math.max(0, 39 - ext.length)).join("") + "\\u2026" + ext;',
	'  }',
	// ★★ 2026-10-08 用户定 ✓：「每 3 秒那个输入框……限制为只能输入 3-99 的数字」✓
	//   ⇒ `min`/`max` **管得住箭头** ✗ 管不住**手打**的 0 或 500 ✗ ⇒ 起播前统一钳 ✓，
	//     并**回写**输入框 ✓（人一眼就看见被纠成了几 ✓）。四舍五入到整数 ✓（3.7 ⇒ 4 ✓）。
	//   ★ ✗ 别绑在 input 事件上 ✗（那样"先打 1"的瞬间就被拧成 3 ✓ ⇒ 12 打不出来 ✗），
	//     绑 change / blur ✓。
	'  function secs(){',
	'    var el = $("sec"), v = Math.round(Number(el.value));',
	'    if (!isFinite(v) || !v) v = 3;',
	'    v = Math.min(99, Math.max(3, v));',
	'    el.value = v;',
	'    return v;',
	'  }',
	'  $("sec").addEventListener("change", secs);',
	'  $("sec").addEventListener("blur", secs);',
	'  function bindHighlight(){',
	'    var SVG = $("pd-svg") || document.querySelector("#art svg") || document.querySelector("svg");',
	'    var li = Array.prototype.slice.call(document.querySelectorAll("#list li"));',
	'    function clear(){',
	'      if (SVG) SVG.classList.remove("pd-focus");',
	'      var g = document.querySelectorAll("#pd-hits > g");',
	'      for (var i = 0; i < g.length; i++) g[i].style.display = "none";',
	'      li.forEach(function(x){ x.classList.remove("sel"); });',
	'    }',
	markJs('#list'),
	'    document.addEventListener("keydown", function(e){ if (e.key === "Escape") clear(); });',
	'    if (SVG) SVG.addEventListener("click", clear);',
	'  }',
	'  function show(d){',
	'    idx = d.index; total = d.total;',
	'    $("art").innerHTML = d.svg || "<div class=\\"hint\\" style=\\"padding:16px\\">'
		+ '（这一条没找到 svg 图）</div>";',
	'    $("list").innerHTML = d.html;',
	'    $("pos").textContent = (idx + 1) + " / " + total;',
	// ★ 文件名**单独一行** ✓（`.name` ✓）：这里**限 40 个字符** ✓（超了用省略号收尾 ✓），
	//   CSS 再管**宽度**截断 ✓；`title` 给**全名** ✓（悬停就看得见 ✓）。
	'    $("name").textContent = clip(d.title);',
	'    $("name").title = d.title;',
	'    bindHighlight();',
	'  }',
	'  function go(n){',
	'    if (!total) return;',
	'    n = (n % total + total) % total;',          // 两头循环 ✓
	'    api.postMessage({ cmd: "page", index: n });',
	'  }',
	// ★★ 2026-10-08：**「▶ 播放差异」回来了** ✓（用户：「面包板差异是可以在右侧、
	//   『面包板差异清单』上方显示【播放差异】的吧？」✓ —— 撤掉的只是**顶栏**那个 ✗，见下 ✓）。
	//   ★ 实现**只有一份** ✓：`replayJs()`（函数 ＋ 绑事件 ✓）在 `JS` 与这里**各展开一次** ✓ ——
	//     ✗ 别在这儿另写一段"起播" ✗（上次"点了没反应"就是两份写法打架 ＋ 注入脚本语法错 ✓）。
	//   ★ 顺序要紧 ✗：`...replayJs()` 展开出来的是**顶层语句** ✓ ⇒ 放在 `api.postMessage({cmd:"ready"})`
	//     前后都行 ✓ —— 但它必须与 `$`/`idx` 那些**同一层** ✓（不是塞进某个函数里 ✓）。
	...replayJs(),
	'  $("prev").addEventListener("click", function(){ go(idx - 1); });',
	'  $("next").addEventListener("click", function(){ go(idx + 1); });',
	// ★★ 2026-10-08 用户定 ✗：**只用符号 ＋ `title` 提示** ✓ ——
	//   「▶ 自动播放」⇒ 按钮上只写 **▶** ✓（鼠标悬停显示「自动播放」✓）；
	//   点了 ⇒ 切成**停止符号 ■** ✓（悬停显示「停止」✓）。
	//   ★ 明确要求 ✗：**不用暂停符号、也不用「暂停」这个词** ✓（所以是 ■ / 停止 ✓，✗ 不是 ⏸ / 暂停 ✗）。
	'  function setPlay(on){',
	'    var b = $("play");',
	'    b.textContent = on ? "\\u25a0" : "\\u25b6";',
	'    b.title = on ? "停止" : "自动播放";',
	'  }',
	'  $("play").addEventListener("click", function(){',
	'    if (timer) { clearInterval(timer); timer = null; setPlay(false); return; }',
	'    var sec = secs();',                        // ★ 3..99 ✓（原来是 Math.max(1, …) ✗ ⇒ 0.5 秒都能进 ✗）
	'    timer = setInterval(function(){ go(idx + 1); }, sec * 1000);',
	'    setPlay(true);',
	'  });',
	// ★ 2026-10-08：「▶ 重放动画」**从这条工具条上撤掉了** ✗（用户要求 ✓ ——
	//   「点击截图1中工具栏上的【重放动画】按钮，没有反应。建议删掉工具栏的【重放动画】按钮，
	//   使用截图2的方式」✓）。重放去**合并视图**那条工具条上点 ✓（双击 `diff/*.md` ✓）。
	//   ⇒ 这里既不绑 `#replay` ✓、也不带 `replayJs()` ✓（✗ 别留死代码 ✗）。
	'  document.addEventListener("keydown", function(e){',
	'    if (e.key === "ArrowRight" || e.key === "PageDown") go(idx + 1);',
	'    else if (e.key === "ArrowLeft" || e.key === "PageUp") go(idx - 1);',
	'    else if (e.key === " ") { e.preventDefault(); $("play").click(); }',
	'  });',
	'  window.addEventListener("message", function(ev){',
	'    var d = ev.data; if (d && d.cmd === "page") show(d);',
	'  });',
	'  api.postMessage({ cmd: "ready" });',
	'})();'
].join('\n');

function slideshowHtml(webview, nonce, n) {
	const csp = `default-src 'none'; img-src ${webview.cspSource} data:; `
		+ `style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;
	return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>${CSS}
  /* ★★ 2026-10-08：多了**第二行**（文件名 ✓）⇒ ✗ 别再写死 34px 的偏移 ✗（加一行就错位 ✓）；
     改成"body 竖排 ＋ .wrap 吃掉剩下的高" ✓。 */
  body { display:flex; flex-direction:column; height:100vh; }
  .wrap { flex:1 1 auto; height:auto; min-height:0; }
  /* ★★ 2026-10-08 用户定 ✓：「把顶部变为**两列**，**左列两行**，**右列一行**。
     ←/→ 翻页　空格 播放/停止… **放到右列**」✓
     ⇒ 顶部 = 一行 flex，里头**两列** ✓：
        · 左列 .hcol = **两行** ✓（第 1 行 = 三个按钮 ＋ 每 N 秒 ＋ 页码 ✓；第 2 行 = 文件名 ✓）；
        · 右列 .tips = 那段快捷键提示 ✓（**一行** ✓ —— align-items:center ⇒
          跟左列**竖向居中**对齐 ✓，不贴着第 1 行 ✗）。
     ★ 还是那个**竖排横宽**的坑 ✗：左列是列向 flex ✓，它孩子里最宽的是第 1 行 ✓
     ⇒ 给 .hcol 和 .name 都留 min-width:0 ✓，窄窗口时文件名才截得到 ✓（见下 ✓）。 */
  /* ★★ 2026-10-08 用户报「顶部高度不够」✓（截图里那个「每 N 秒」输入框的**下边框没了** ✓、
     文件名那行只剩半截 ✓）—— 根因 ✗：.head 是 **body 那个竖排 flex 的孩子** ✓，
     默认 flex-shrink:1 ✓；而它又带了 overflow:hidden ✓ ⇒ 按 flex 规范，
     **overflow 不是 visible 的孩子，自动最小尺寸算 0** ✗ ⇒ 内容比一屏高时，
     它会跟 .wrap 一起**被压缩** ✓ —— 实测：需要 41px 的头被压到 **16~29px** ✓、
     scrollHeight 41 > clientHeight 29 ✓ ⇒ 于是 align-items:center 把左列（40px）
     往中间一挤 ✓ ⇒ **上下一起切** ✓（下边框 + 文件名行就这么没的 ✓）。
     ⇒ 头**不许缩** ✓：flex:0 0 auto ✓（要缩也只能缩 .wrap ✓，它本来就有 min-height:0 ✓）。 */
  .head { flex:0 0 auto; display:flex; gap:12px; align-items:center; padding:6px 10px;
          border-bottom:1px solid var(--vscode-panel-border); font-size:12px;
          min-width:0; overflow:hidden; }
  .hcol { display:flex; flex-direction:column; gap:3px; min-width:0; flex:0 1 auto; }
  .hrow { display:flex; gap:8px; align-items:center; }
  .head button { background: var(--vscode-button-background); color: var(--vscode-button-foreground);
                border:0; padding:3px 10px; border-radius:3px; cursor:pointer;
                /* ★★ 2026-10-08 用户定 ✗：按钮上只剩**一个符号**（← ▶ → ✓），
                   提示走 title 属性 ✓ ⇒ 三个按钮要**一样宽** ✓ 才不看着一高一低 ✗。
                   ★ 这里在**模板字符串**里 ⇒ ✗ 注释里别写反引号 ✗（一写就把模板截断 ✓ —— 当场踩过 ✓）。 */
                min-width:2.2em; text-align:center; }
  /* ★★ 2026-10-08 用户定 ✓：「每 3 秒那个输入框太长了，应限制为只能输入 3-99 的数字」✓
     ⇒ ① type=number ＋ min=3 ＋ max=99（语义与校验 ✓）；
       ② 去掉那两个上下箭头 ✗（Chromium 的箭头**占在框里面** ✓ ⇒ 看着又长又挤 ✓），
          宽度收到 2.4em ＋ 居中 ✓（实测 47px ⇒ 35px ✓；两位数够用 ✓，✗ 别贪大 ✗）；
       ③ 光靠属性不够 ✗（手打 0 / 500 照样进得去 ✓）⇒ 脚本里 secs() **回写** 3..99 ✓（见 SLIDE_JS ✓）。 */
  .head input { width:2.4em; text-align:center; padding:1px 2px;
               -webkit-appearance:none; appearance:none;
               background: var(--vscode-input-background);
               color: var(--vscode-input-foreground); border:1px solid var(--vscode-input-border); }
  /* ★★ 2026-10-08 用户定 ✓：「2 / 3 这个地方不能换行，必须在同一行」✓
     ⇒ 它是 flex 里可缩的孩子 ✓ ⇒ 窄窗口时被挤成**一列一个字**（实测 520px 窗口下 16×27 ✓ 两行 ✗）
     ⇒ white-space:nowrap ✓（✗ 不许它自己折行 ✗）。 */
  #pos { opacity:.85; white-space:nowrap; }
  /* ★★ 2026-10-08 用户定 ✓：「把文件名显示在 ← 下面那一行，如果文件名超过一定字符数，
     则用 ... 截断，鼠标放在上面时显示全文件名」✓ ＋「最长 40 个字符吧」✓
     ⇒ **两层截断** ✓：脚本限**字数**（超 40 ⇒ 收一个省略号 ✓，✗ CSS 做不到这个 ✗）
       ＋ 这里限**宽度** ✓（text-overflow:ellipsis ✓ —— 窄窗口也不撑破 ✓）；
       title 挂全名 ✓（悬停看全 ✓）。 */
  .name { min-width:0; opacity:.9;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  /* ★ 右列 ✓（2026-10-08 用户定 ✓：「←/→ 翻页　空格 播放/停止… 放到右列」✓）——
     flex:1 1 0 ⇒ 它吃掉**左列以外**的宽 ✓，所以"右列"是条真的列 ✓（✗ 不是跟在文件名后面的一截 ✗）；
     仍**允许折行** ✓（用户 2026-10-08 上一轮明说「这些是可以两行的」✓ —— 窄窗口下 2~3 行 ✓）。 */
  .tips { flex:1 1 0; min-width:0; opacity:.6; line-height:1.45; white-space:normal; }
  /* ★★ 2026-10-08 用户定 ✓：「**从 css 画**，border-left + 三角，**border-left 与三角要等高**」✓
     ⇒ 幻灯片的「播放差异」不用字符 ✓，**画出来** ✓（✗ 字符要么没有这个形状 ✗ ——
        Unicode 只有 ⏮/⏭ 那种**双三角** ✓；要么各机器字体不一样 ✗）。
     ★★ 等高怎么保住的 ✓（**每一步都量过** ✓）：
       · 两块都 height:100% ✓、挂在**同一个** height:12px 的盒子上 ✓ ⇒ **结构上等高** ✓；
       · 但用户 2026-10-08 又报「**黑色竖线仍然长了一些**」✓ ⇒ 去**数像素**（截图放大 + 逐列量覆盖 ✓）：
         竖线 **30** 个设备像素（两端都是满覆盖 ✓）、三角 **29** 个 ✓ ——
         ★ 三角顶端那一行的覆盖只有 **0.12** ✓：它那个尖角在 (0,0)，**笔画的斜边从角上起** ✓
         ⇒ 抗锯齿把最上面一行啃掉了 ✓（✗ 高度是 12px 也没用 ✗，**画出来**就是少一行 ✓）。
       · ⇒ 竖线**主动收半像素** ✓（height 写成 calc(100% - 0.5px) ✓）⇒ 它两端各收 0.25px ✓、
         量出来正好也是 **29** 行 ✓ ⇒ **两边看起来一样高** ✓（✗ 别再改回 100% ✗，一改就又长出来 ✓）。
     ★ 三角用 clip-path 画 ✓（不是边框拼的 ✓）；✗ 边框拼的那版量过是 11.799 vs 11.998 ✗
       —— 边框宽度会被吸附到设备像素 ✓，差 0.2px ✓，也不等 ✓。
     ★ 颜色都用 currentColor ✓ ⇒ 深浅跟着按钮自己的 color 走 ✓。 */
  .step { display:inline-flex; align-items:center; gap:2px; height:12px; }
  .step::before { content:""; width:0; height:calc(100% - 0.5px); border-left:2px solid currentColor; }
  .step::after { content:""; width:9px; height:100%; background:currentColor;
                 clip-path: polygon(0 0, 100% 50%, 0 100%); }
</style></head><body>
<div class="head">
  <div class="hcol">
    <div class="hrow">
      <button id="prev" title="上一条">←</button><button id="play" title="自动播放">▶</button><button id="next" title="下一条">→</button><span>每</span><input id="sec" type="number" min="3" max="99" step="1" value="3"><span>秒</span>
      <span id="pos">共 ${n} 条</span>
    </div>
    <div class="name" id="name"></div>
  </div>
  <div class="tips">←/→ 翻页　空格 播放/停止　Esc 取消高亮　点 ①② 里任意一条 高亮</div>
</div>
<div class="wrap">
  <div class="pane left"><div class="art" id="art"></div></div>
  <div class="pane right">
    <!-- ★★ 2026-10-08 用户定 ✓：「面包板差异**是可以在右侧、『面包板差异清单』上方显示【播放差异】的吧**？」✓
         ⇒ 右栏（清单那一栏 ✓）**顶上一条** ✓，.bar 与合并视图共用 ✓（字号/边框/钉顶都一致 ✓）；
         ★ 按钮 id 与合并视图**同名** ✓（pd-replay ✓）⇒ replayJs() 那一份**照旧能绑** ✓
         （✗ 别为幻灯片再写一套 ✓）。
         ★ 为什么按钮进 .bar 而提示留在 .head ✓：右栏没有"文件名/翻页"那些东西 ✓，
         那条 bar 本来就是右栏的**顶栏** ✓ ⇒ 按钮放这儿**贴着清单** ✓（正是用户指的位置 ✓）。
         ★★ 2026-10-08 用户又指一处 ✗：「两者**完全不同**啊！「▶ 重放动画」是从一个 md，到另一个 md。
         「▶ 播放差异」是**在一个 md 内，从 A 播放到 B**。⇒ 「▶ 播放差异」的 ▶ 应该换成步进播放含义的字符」✓
         ⇒ 最后定的是 **用 CSS 画** ✓（用户：「**从 css 画**，border-left + 三角，
         **border-left 与三角要等高**」✓ —— 见 .step ✓）✗ 不用字符 ✗：
         Unicode 里"竖线 ＋ 单个右三角"**没有整字** ✓（只有 ⏮/⏭ 那种**双三角** ✓，而且各机器字体不一 ✓）。
         ★ 图形 = .step ✓ 那个类 ✓（竖线用 border-left ✓、三角用 border 画 ✓，两块**等高 12px** ✓）；
         文字单独放 .lbl ✓ ⇒ 起播回显**只改它** ✓（✗ 别整个 textContent 覆盖 ✗，那会把图形冲掉 ✓）。 -->
    <div class="bar"><button id="pd-replay"><span class="step" aria-hidden="true"></span><span class="lbl">播放差异</span></button></div>
    <div id="list"></div>
  </div>
</div>
<script nonce="${nonce}">${SLIDE_JS}</script>
</body></html>`;
}

async function cmdSlideshow() {
	const { proj } = dirs();
	if (!proj) {
		return void vscode.window.showErrorMessage(
			'没找到项目目录（工作区里含 fzz 的那层，也可用设置 pixelDiff.projectDir 指定）');
	}
	const pages = pageList(proj);
	if (!pages.length) {
		return void vscode.window.showErrorMessage('diff/ 里还没有 diff-*.md ⇒ 先跑一次「比较两版」');
	}
	const panel = vscode.window.createWebviewPanel('pixelDiff.slides', 'Pixel 差异幻灯片',
		vscode.ViewColumn.Active, { enableScripts: true, localResourceRoots: [vscode.Uri.file(proj)] });
	panel.webview.html = slideshowHtml(panel.webview, String(Date.now()), pages.length);
	panel.webview.onDidReceiveMessage((msg) => {
		// ★ 图里那两段脚本会回话 ✓（`window.__pdLog` ✓）：起播成没成、起了几个动画 ✓ ——
		//   用户报「点了没反应」时，**先看这一行** ✓（✗ 别靠猜 ✗）。
		// ★ 2026-10-08：幻灯片那条工具条上**已经没有**「▶ 重放动画」了 ✗（用户要求撤掉 ✓）
		//   ⇒ 它不再发 `log` ✓；这一支**留着**也无害 ✓（哪天按钮回来了就直接能看日志 ✓）。
		if (msg && msg.cmd === 'log') return void log('[webview] ' + msg.text);
		if (!msg || (msg.cmd !== 'ready' && msg.cmd !== 'page')) return;
		const i = msg.cmd === 'ready' ? 0 : ((msg.index % pages.length) + pages.length) % pages.length;
		const p = readPage(pages[i]);
		panel.webview.postMessage({ cmd: 'page', index: i, total: pages.length,
			title: p.title, svg: p.svg, html: p.html });
	});
	log(`幻灯片：共 ${pages.length} 条（${pages.map((p) => path.basename(p)).slice(0, 3).join(', ')}…）`);
}

class DiffEditor {
	constructor(context) { this.context = context; }

	async resolveCustomTextEditor(document, panel) {
		const mdPath = document.uri.fsPath;
		const dir = path.dirname(mdPath);
		const stem = path.basename(mdPath).replace(/\.md$/, '');
		const svgPath = path.join(dir, stem + '.svg');
		const pngPath = path.join(dir, stem + '.png');
		// ★ 开了脚本：因为要「点清单一条 ⇒ 图上高亮」⇒ svg 必须**内联**进来
		//   ✗ `<img>` 里的 svg 父文档碰不到 ✗（改不了它里面的 display ✓）。
		panel.webview.options = { enableScripts: true, localResourceRoots: [vscode.Uri.file(dir)] };
		const draw = () => {
			let svgText = inlineSvg(svgPath);          // ★ 与幻灯片共用这一份 ✓
			const pngUri = (!svgText && fs.existsSync(pngPath))
				? panel.webview.asWebviewUri(vscode.Uri.file(pngPath)) : null;
			const nonce = String(Math.random()).slice(2) + String(Date.now());
			panel.webview.html = html(panel.webview, document.getText(), svgText, pngUri,
				pngUri ? path.basename(pngPath) : '',
				'这份清单旁边没有同名图 ⇒ 先跑 py tools\\diff_revs.py，或直接对我用命令「比较两版」',
				nonce);
		};
		draw();
		// ★ 图里那两段脚本会回话 ✓（`window.__pdLog` ✓）：起播成没成、起了几个动画 ✓ ——
		//   用户报「点了没反应」时，**先看「Pixel 差异」输出通道这一行** ✓（✗ 别靠猜 ✗）。
		panel.webview.onDidReceiveMessage((msg) => {
			if (msg && msg.cmd === 'log') log('[webview] ' + msg.text);
		});
		this.context.subscriptions.push(
			vscode.workspace.onDidChangeTextDocument((e) => {
				if (e.document.uri.toString() === document.uri.toString()) draw();
			}),
			vscode.workspace.onDidSaveTextDocument((e) => {
				if (e.uri.toString() === document.uri.toString()) draw();
			})
		);
	}
}

async function cmdCompare(context) {
	const { proj, tool } = dirs();
	if (!proj || !tool) {
		return void vscode.window.showErrorMessage(
			'没找到项目目录（工作区里含 fzz 的那层，也可用设置 pixelDiff.projectDir 指定）'
			+ '或库仓 tools/diff_revs.py（库仓要加进工作区）');
	}
	// ★ 先选**看哪个视图** ✓（2026-10-07 加 ✓）：PCB / 面包板 / 原理图
	//   ✗ 三个命令会挤满命令面板 ✗ ⇒ 用一个选择框（默认 PCB ✓）。
	const pickView = await vscode.window.showQuickPick(
		[{ label: 'PCB', v: 'pcb' }, { label: '面包板', v: 'bb' }, { label: '原理图', v: 'sch' }],
		{ placeHolder: '比哪个视图？（默认 PCB）' });
	const view = pickView ? pickView.v : 'pcb';
	const vers = listVersions(proj, patRe(view).source);
	if (vers.length < 2) {
		return void vscode.window.showErrorMessage(
			`${VIEW_NAME[view]}：这个目录里符合 pixelDiff.${VIEW_PAT[view]} 的文件少于两个`
			+ `（现在 ${vers.length} 个）：${proj}`);
	}
	const pick = (def) => vscode.window.showQuickPick(vers, { placeHolder: `选一版（默认 ${def}）` })
		.then((v) => v || def);
	const a = await pick(vers[vers.length - 2]);
	const b = await pick(vers[vers.length - 1]);
	await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `${VIEW_NAME[view]}差异图：${a} ⇒ ${b}` },
		() => runDiff(tool, proj, a, b, view));
	const md = newestDiffMd(proj);
	if (!md) return void vscode.window.showErrorMessage('跑完了但没有 diff-*.md，见「Pixel 差异」输出通道');
	await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(md), VIEW);
}

async function cmdCompareFiles() {
	const { proj, tool } = dirs();
	if (!tool) {
		return void vscode.window.showErrorMessage(
			'没找到库仓的 tools/diff_revs.py ⇒ 把 fritzing-parts-langhua 也加进工作区');
	}
	const one = await vscode.window.showOpenDialog({
		canSelectMany: false, openLabel: '选第一个（A）',
		defaultUri: proj ? vscode.Uri.file(proj) : undefined,
		filters: { 'fzz / svg': ['fzz', 'svg'] }
	});
	if (!one || !one.length) return;
	// ★ 没认出项目目录也不拦你 ✓：就用**你挑的那个文件所在目录**当项目 ✓
	//   （差异图/清单都会落在它旁边的 `diff/` ✓）⇒ 任何文件夹零配置就能比 ✓。
	const projDir = proj || path.dirname(one[0].fsPath);
	const two = await vscode.window.showOpenDialog({
		canSelectMany: false, openLabel: '选第二个（B）', defaultUri: vscode.Uri.file(projDir),
		filters: { 'fzz / svg': ['fzz', 'svg'] }
	});
	if (!two || !two.length) return;
	await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: '差异图' },
		() => runDiff(tool, projDir, one[0].fsPath, two[0].fsPath));
	const md = newestDiffMd(projDir);
	if (md) {
		await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(md), VIEW);
	} else {
		// 两边都是 svg 时不出清单，只出图 ⇒ 直接把图打开
		const png = path.join(projDir, 'diff');
		const hit = fs.existsSync(png)
			? fs.readdirSync(png).filter((n) => /^diff-.*\.png$/.test(n))
				.map((n) => ({ n, t: fs.statSync(path.join(png, n)).mtimeMs })).sort((x, y) => y.t - x.t)
			: [];
		if (hit.length) await vscode.commands.executeCommand('vscode.open', vscode.Uri.file(path.join(png, hit[0].n)));
		else vscode.window.showErrorMessage('没找到新生成的图，见「Pixel 差异」输出通道');
	}
}

function activate(context) {
	context.subscriptions.push(
		vscode.commands.registerCommand('pixelDiff.compare', () => cmdCompare(context)),		vscode.commands.registerCommand('pixelDiff.compareFiles', () => cmdCompareFiles()),	vscode.commands.registerCommand('pixelDiff.slideshow', () => cmdSlideshow()),
		vscode.window.registerCustomEditorProvider(VIEW, new DiffEditor(context),
			{ webviewOptions: { retainContextWhenHidden: true } })
	);
}

function deactivate() { }

// 把**纯函数**引出来给单测用（`_work/_test_ext.js`）——
// 扩展本体没法在这儿跑（要 VS Code 的扩展宿主），但"选版本 / 找最新清单 / 清单转 HTML"
// 这几件是纯逻辑，能单独验 —— 免得只靠"装上去点一下看看"。
module.exports = {
	activate, deactivate,
	_pure: { listVersions, newestDiffMd, mdToHtml, PAD_RE_SRC, ROW_RE_SRC, reLit, dirs, pageList,
	         readPage, CSS, slideshowHtml, html, patRe, keysOf, markNames }
};



