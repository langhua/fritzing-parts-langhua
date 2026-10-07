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

/** 找**项目目录**（放着 fzz / `pixel_nets.py` 的那个）与**工具所在目录**（库仓根 ✓）。
 *
 *  ★★ 2026-10-07 按约定搬家 ✓（用户指出：通用工具应放库下 ✓，项目里**不留副本** ✗ ——
 *    项目根的 `toolpaths.py` 里就写着这条 ✓）：`diff_revs.py` 现在在
 *    `fritzing-parts-langhua/tools/` ✓ ⇒ 这里要同时找两处 ✓：
 *      · **项目目录** ⇒ 跑的时候当 **cwd** ✓（工具按 cwd 找 fzz ✓、找 `pixel_nets.py` ✓）；
 *      · **库仓根** ⇒ 工具本体在那儿 ✓。
 */
function dirs() {
	const folders = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
	let proj = null, tool = null;
	for (const root of folders) {
		if (!proj && fs.existsSync(path.join(root, 'hardware', 'pixel', 'pixel_nets.py'))) {
			proj = path.join(root, 'hardware', 'pixel');
		}
		if (!proj && fs.existsSync(path.join(root, 'pixel_nets.py'))) proj = root;
		if (!tool && fs.existsSync(path.join(root, 'tools', 'diff_revs.py'))) tool = root;
	}
	return { proj, tool };
}

/** `pixel-pcb-v*.fzz` ⇒ 按版本号排（后缀如 `_byHand` 排在同号之后）。 */
function listVersions(dir) {
	const key = (n) => {
		const m = /-v(\d+)([\s\S]*)$/.exec(n.replace(/\.fzz$/, ''));
		return m ? [Number(m[1]), m[2] ? 1 : 0, m[2]] : [0, 0, n];
	};
	return fs.readdirSync(dir).filter((n) => /^pixel-pcb-v\d+.*\.fzz$/.test(n))
		.sort((a, b) => {
			const x = key(a), y = key(b);
			return (x[0] - y[0]) || (x[1] - y[1]) || String(x[2]).localeCompare(String(y[2]));
		});
}

/** 跑 `diff_revs.py` ✓（工具在库里 ✓、**cwd 给项目目录** ✓ ⇒ fzz 与网表都自己找得到 ✓）。
 *  日志进输出通道；`PYTHONIOENCODING` 必须给 —— 否则中文/✓ 会撞 GBK 控制台。
 */
function runDiff(toolDir, projDir, a, b) {
	const tool = path.join(toolDir, 'tools', 'diff_revs.py');
	return new Promise((resolve) => {
		log(`\n> ${PY} "${tool}" "${a}" "${b}"   （cwd=${projDir}）`);
		cp.execFile(PY, [tool, a, b], {
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
const JS = [
	'(function(){',
	'  var SVG = document.getElementById("pd-svg");',
	'  var li = Array.prototype.slice.call(document.querySelectorAll("li"));',
	'  var RE = new RegExp(' + JSON.stringify(PAD_RE_SRC) + ');',
	'  function clear(){',
	'    if (SVG) SVG.classList.remove("pd-focus");',
	'    var g = document.querySelectorAll("#pd-hits > g");',
	'    for (var i = 0; i < g.length; i++) g[i].style.display = "none";',
	'    li.forEach(function(x){ x.classList.remove("sel"); });',
	'  }',
	'  li.forEach(function(x){',
	'    var m = RE.exec(x.textContent || "");',
	'    if (!m) return;',
	'    x.classList.add("clickable");',
	'    x.title = "点一下：在图上高亮 " + m[1];',
	'    x.addEventListener("click", function(){',
	'      clear();',
	'      if (SVG) SVG.classList.add("pd-focus");',
	'      var t = document.getElementById("pd-" + m[1]);',
	'      if (t) { t.style.display = ""; x.classList.add("sel"); }',
	'    });',
	'  });',
	'  document.addEventListener("keydown", function(e){ if (e.key === "Escape") clear(); });',
	'  if (SVG) SVG.addEventListener("click", clear);',
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
  .bar { font-size:12px; opacity:.75; padding:4px 8px; border-bottom:1px solid var(--vscode-panel-border); }
  h1 { font-size:1.15em; } h2 { font-size:1.05em; margin-top:1.1em; } h3 { font-size:1em; }
  code { background: var(--vscode-textCodeBlock-background); padding:0 3px; border-radius:3px; }
  blockquote { margin:.4em 0; padding-left:8px; border-left:3px solid var(--vscode-panel-border); opacity:.85; }
  ul { padding-left:1.2em; margin:.2em 0; }
  li.clickable { cursor:pointer; border-radius:3px; }
  li.clickable:hover { background: var(--vscode-list-hoverBackground); }
  li.sel { background: var(--vscode-list-activeSelectionBackground); }
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
    <div class="bar">${svgText ? '点 ① 里任意一条 ⇒ 图上高亮（Esc 或点图取消）'
		: (imgUri ? esc(imgName) : '（无图）')}</div>
    ${mdToHtml(mdText)}
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
	const key = (n) => {
		const m = /^diff-v(\d+)([^-]*)-v(\d+)([^.]*)\.md$/.exec(n);
		return m ? [Number(m[1]), Number(m[3]), n] : [1e9, 1e9, n];   // 认不出号的排最后 ✓
	};
	return fs.readdirSync(d).filter((n) => /^diff-.*\.md$/.test(n))
		.sort((a, b) => {
			const x = key(a), y = key(b);
			return (x[0] - y[0]) || (x[1] - y[1]) || String(x[2]).localeCompare(String(y[2]));
		})
		.map((n) => path.join(d, n));
}

/** 一页的内容 ✓（标题 ＋ 内联 svg ＋ 已转好的清单 HTML ✓）。 */
function readPage(mdPath) {
	const dir = path.dirname(mdPath);
	const stem = path.basename(mdPath).replace(/\.md$/, '');
	return {
		title: stem,
		svg: inlineSvg(path.join(dir, stem + '.svg')),
		html: mdToHtml(fs.readFileSync(mdPath, 'utf8'))
	};
}

// 幻灯片里的脚本：翻页 ＋ 自动播放 ＋ 键盘 ✓，并**保持**「点行 ⇒ 高亮」✓（每换一页重新绑 ✓）。
const SLIDE_JS = [
	'(function(){',
	'  var api = acquireVsCodeApi();',
	'  var idx = -1, total = 0, timer = null;',
	'  function $(id){ return document.getElementById(id); }',
	'  function bindHighlight(){',
	'    var SVG = $("pd-svg");',
	'    var li = Array.prototype.slice.call(document.querySelectorAll("#list li"));',
	'    var RE = new RegExp(' + JSON.stringify(PAD_RE_SRC) + ');',
	'    function clear(){',
	'      if (SVG) SVG.classList.remove("pd-focus");',
	'      var g = document.querySelectorAll("#pd-hits > g");',
	'      for (var i = 0; i < g.length; i++) g[i].style.display = "none";',
	'      li.forEach(function(x){ x.classList.remove("sel"); });',
	'    }',
	'    li.forEach(function(x){',
	'      var m = RE.exec(x.textContent || "");',
	'      if (!m) return;',
	'      x.classList.add("clickable");',
	'      x.title = "点一下：在图上高亮 " + m[1];',
	'      x.addEventListener("click", function(){',
	'        clear();',
	'        if (SVG) SVG.classList.add("pd-focus");',
	'        var t = $("pd-" + m[1]);',
	'        if (t) { t.style.display = ""; x.classList.add("sel"); }',
	'      });',
	'    });',
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
  <span id="pos">共 ${n} 条</span>
  <span style="opacity:.6">←/→ 翻页　空格 播放/暂停　Esc 取消高亮　点清单一条 高亮</span>
</div>
<div class="wrap">
  <div class="pane left" id="art"></div>
  <div class="pane right" id="list"></div>
</div>
<script nonce="${nonce}">${SLIDE_JS}</script>
</body></html>`;
}

async function cmdSlideshow() {
	const { proj } = dirs();
	if (!proj) return void vscode.window.showErrorMessage('找不到项目目录（要有 pixel_nets.py）');
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
			'找不到项目目录（要有 pixel_nets.py）或库仓 tools/diff_revs.py —— 两者都要在工作区里');
	}
	const vers = listVersions(proj);
	if (vers.length < 2) return void vscode.window.showErrorMessage('这个目录里少于两版 fzz');
	const pick = (def) => vscode.window.showQuickPick(vers, { placeHolder: `选一版（默认 ${def}）` })
		.then((v) => v || def);
	const a = await pick(vers[vers.length - 2]);
	const b = await pick(vers[vers.length - 1]);
	await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: `差异图：${a} ⇒ ${b}` },
		() => runDiff(tool, proj, a, b));
	const md = newestDiffMd(proj);
	if (!md) return void vscode.window.showErrorMessage('跑完了但没有 diff-*.md，见「Pixel 差异」输出通道');
	await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(md), VIEW);
}

async function cmdCompareFiles() {
	const { proj, tool } = dirs();
	if (!proj || !tool) {
		return void vscode.window.showErrorMessage(
			'找不到项目目录（要有 pixel_nets.py）或库仓 tools/diff_revs.py —— 两者都要在工作区里');
	}
	const one = await vscode.window.showOpenDialog({
		canSelectMany: false, openLabel: '选第一个（A）', defaultUri: vscode.Uri.file(proj),
		filters: { 'fzz / svg': ['fzz', 'svg'] }
	});
	if (!one || !one.length) return;
	const two = await vscode.window.showOpenDialog({
		canSelectMany: false, openLabel: '选第二个（B）', defaultUri: vscode.Uri.file(proj),
		filters: { 'fzz / svg': ['fzz', 'svg'] }
	});
	if (!two || !two.length) return;
	await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: '差异图' },
		() => runDiff(tool, proj, one[0].fsPath, two[0].fsPath));
	const md = newestDiffMd(proj);
	if (md) {
		await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(md), VIEW);
	} else {
		// 两边都是 svg 时不出清单，只出图 ⇒ 直接把图打开
		const png = path.join(proj, 'diff');
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
	_pure: { listVersions, newestDiffMd, mdToHtml, PAD_RE_SRC, dirs, pageList, readPage }
};
