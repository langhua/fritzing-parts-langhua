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

/** 图上**可点名字**的清单 ✓：`#pd-hits` 里那些 `pd-*` 组的组名 ✓（与工具**同一份数据** ✓）。 */
function keysOf(svgText) {
	if (!svgText) return [];
	const i = svgText.indexOf('id="pd-hits"');
	const j = svgText.indexOf('id="pd-labels"', i < 0 ? 0 : i);
	const seg = i < 0 ? svgText : svgText.slice(i, j < 0 ? undefined : j);
	const set = new Set();
	for (const m of seg.matchAll(/<g id="pd-([^"]+)"/g)) set.add(m[1]);
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
const JS = [
	'(function(){',
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
	// ★★ 工具条上的「重放」✓（2026-10-08 加 ✓）：svg 里那个按钮只在**把 svg 当文档**打开时
	//   能点 ✓ —— 在 VS Code 的**图片预览**里它是 `<img>` ✗（脚本一律不跑 ✗）、
	//   在**合并视图**里又会被 webview 的 CSP（nonce ✓）挡掉 ✗ ⇒ 用户点着没反应 ✗。
	//   ⇒ 在**外面**给一个按钮 ✓：它只管把动画的 `currentTime` 拨回 0 ✓（只播一遍 + forwards ✓）。
	//   ★ 同一份逻辑**幻灯片那边也有** ✓（`SLIDE_JS` 的 `#replay` ✓）—— 两处都别漏 ✗
	//     （工具打印的那句「合并视图/幻灯片另有按钮」必须是**真的** ✓）。
	'  var rp = document.getElementById("pd-replay");',
	'  if (rp) rp.addEventListener("click", function(){ replay(); });',
	'  function replay(){',
	'    var as = document.getAnimations();',
	'    for (var i = 0; i < as.length; i++) { try { as[i].currentTime = 0; } catch (e) {} }',
	'  }',
	'})();'
].join('\n');

// ★ HTML/CSS **只留一份** ✓（自定义编辑器与幻灯片共用 ✓）—— ✗ 别在幻灯片里再抄一遍 ✗。
const CSS = `
  body { margin:0; font-family: var(--vscode-font-family); color: var(--vscode-editor-foreground); }
  .wrap { display:flex; height:100vh; }
  .pane { overflow:auto; }
  .left { flex:2 1 0; background:#ffffff; display:flex; align-items:flex-start; justify-content:center;
          padding:8px; box-sizing:border-box; }
  .left img, .art svg { max-width:100%; height:auto; }
  .art svg { cursor:default; }
  .right { flex:1 1 0; padding:10px 14px; border-left:1px solid var(--vscode-panel-border); }
  .bar { font-size:12px; opacity:.75; padding:4px 8px; border-bottom:1px solid var(--vscode-panel-border);
         /* ★★ 2026-10-08 修 ✗：工具条**钉在顶上** ✓ —— 它是「▶ 重放动画」唯一的落脚处 ✓，
            而清单往往长过一屏 ✓ ⇒ 一滚就"看不到按钮"了 ✗（用户原话：「没有看到「▶ 重放动画」按钮」✓）。 */
         position:sticky; top:0; z-index:2; background: var(--vscode-editor-background); }
  .bar button { font-size:12px; cursor:pointer; color:inherit; background:transparent;
                border:1px solid var(--vscode-panel-border); border-radius:3px; padding:1px 6px; }
  h1 { font-size:1.15em; } h2 { font-size:1.05em; margin-top:1.1em; } h3 { font-size:1em; }
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
	return `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<style>${CSS}</style></head><body>
<div class="wrap">
  <div class="pane left">${art}</div>
  <div class="pane right">
    <div class="bar">${svgText ? '<button id="pd-replay">▶ 重放动画</button>　点 ① 里任意一条 ⇒ 图上高亮（Esc 或点图取消）'
		: (imgUri ? esc(imgName) : '（无图）')}</div>
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
	const stem = path.basename(mdPath).replace(/\.md$/, '');
	const svg = inlineSvg(path.join(dir, stem + '.svg'));
	// ★ 可点名字在**这里**（Node 一侧）就包好 ✓（与合并视图同一份 `markNames()` ✓，
	//   ✗ 别让 webview 再去猜文字 ✗ —— 见 `markNames()` 里那个"吃字"的教训 ✓）
	return {
		title: stem,
		svg,
		html: markNames(mdToHtml(fs.readFileSync(mdPath, 'utf8')), keysOf(svg))
	};
}

// 幻灯片里的脚本：翻页 ＋ 自动播放 ＋ 键盘 ✓，并**保持**「点行 ⇒ 高亮」✓（每换一页重新绑 ✓）。
const SLIDE_JS = [
	'(function(){',
	'  var api = acquireVsCodeApi();',
	'  var idx = -1, total = 0, timer = null;',
	'  function $(id){ return document.getElementById(id); }',
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
	'    $("pos").textContent = (idx + 1) + " / " + total + "　" + d.title;',
	'    bindHighlight();',
	'  }',
	'  function go(n){',
	'    if (!total) return;',
	'    n = (n % total + total) % total;',          // 两头循环 ✓
	'    api.postMessage({ cmd: "page", index: n });',
	'  }',
	'  $("prev").addEventListener("click", function(){ go(idx - 1); });',
	'  $("next").addEventListener("click", function(){ go(idx + 1); });',
	'  $("play").addEventListener("click", function(){',
	'    if (timer) { clearInterval(timer); timer = null; $("play").textContent = "▶ 自动播放"; return; }',
	'    var sec = Math.max(1, Number($("sec").value) || 3);',
	'    timer = setInterval(function(){ go(idx + 1); }, sec * 1000);',
	'    $("play").textContent = "⏸ 暂停";',
	'  });',
	// ★★ 2026-10-08 加 ✓：**本页**动画重放 ✓ —— 桩与合并视图那份**同一套** ✓（`getAnimations()`
	//   ＋ `currentTime = 0` ✓）：幻灯片一页只有一个 svg ✓ ⇒ 拨到的就是当前这页 ✓。
	'  $("replay").addEventListener("click", function(){',
	'    var as = document.getAnimations();',
	'    for (var i = 0; i < as.length; i++) { try { as[i].currentTime = 0; } catch (e) {} }',
	'  });',
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
  .wrap { height: calc(100vh - 34px); }
  .top { display:flex; gap:8px; align-items:center; padding:6px 10px;
         border-bottom:1px solid var(--vscode-panel-border); font-size:12px; }
  .top button { background: var(--vscode-button-background); color: var(--vscode-button-foreground);
                border:0; padding:3px 10px; border-radius:3px; cursor:pointer; }
  .top input { width:3.2em; background: var(--vscode-input-background);
               color: var(--vscode-input-foreground); border:1px solid var(--vscode-input-border); }
  #pos { opacity:.85; }
</style></head><body>
<div class="top">
  <button id="prev">⟨ 上一条</button><button id="next">下一条 ⟩</button>
  <button id="play">▶ 自动播放</button><span>每</span><input id="sec" value="3"><span>秒</span>
  <button id="replay">▶ 重放动画</button>
  <span id="pos">共 ${n} 条</span>
  <span style="opacity:.6">←/→ 翻页　空格 播放/暂停　Esc 取消高亮　点清单一条 高亮</span>
</div>
<div class="wrap">
  <div class="pane left"><div class="art" id="art"></div></div>
  <div class="pane right" id="list"></div>
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
