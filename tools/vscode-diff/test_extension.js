// 扩展的纯逻辑单测（不用 VS Code：把 `vscode` 模块替换成替身）。
//   node _work\_test_ext.js
// 四项都拿**真的项目文件**跑，不是假数据：
//   ① 版本排序  ② 找最新清单  ③ 清单转 HTML  ④ 「点清单一条 ⇒ 图上高亮」的对应关系
//
// ★ 教训（2026-10-07，我在这儿栽过两次）：**别在自己写的测试里自加判据** ——
//   多写一个 `^`、多设一个阈值 ⇒ 假报失败 ⇒ 白白折腾几轮。
//   ⇒ 判据只留"有 / 没有"这种**最硬的**，其余**只打印真实计数**给人看。
const Module = require('module');
const fs = require('fs');
const os = require('os');
const path = require('path');

const stub = {
	workspace: {
		workspaceFolders: [],
		// ★ 设置读取的替身 ✓：真的 VS Code 里 `getConfiguration('pixelDiff').get('fzzPattern')`
		//   查的是 **`pixelDiff.fzzPattern`** ✓ ⇒ 桩也得先拼段名 ✗（★ 我第一版忘了 ✗ ⇒
		//   ① 打出 151 版 ⇒ 立刻看出来"设置没生效" ✓ —— 这就是为什么要打印真计数 ✓）。
		getConfiguration: () => ({
			get: (k, d) => {
				const c = stub.cfg || {}, kk = 'pixelDiff.' + k;
				return (kk in c) ? c[kk] : ((k in c) ? c[k] : d);
			}
		})
	},
	window: { createOutputChannel: () => ({ appendLine() { } }) },
	commands: { registerCommand() { }, executeCommand() { } },
	Uri: { file: (p) => ({ fsPath: p, toString: () => 'file://' + p }) },
	ProgressLocation: { Notification: 15 }
};
const orig = Module._load;
Module._load = function (req, parent, isMain) {
	if (req === 'vscode') return stub;
	return orig.apply(this, arguments);
};

// ★★ 2026-10-07 随扩展搬进库仓 ✓（通用工具 ✓）：扩展与单测都在 `tools/vscode-diff/` ✓。
//   要验的**项目目录**（生成 `diff/` 的那个 ✓）用**第一个参数**给 ✓；
//   不给就拿**当前目录** ✓（在项目目录里就能直接跑 ✓）。
const EXTDIR = __dirname;
const PIX = path.resolve(process.argv[2] || process.cwd());
const ext = require(path.join(EXTDIR, 'extension.js'));
const { listVersions, newestDiffMd, mdToHtml, PAD_RE_SRC, ROW_RE_SRC, reLit, dirs, pageList,
        readPage, CSS, slideshowHtml, html, patRe } = ext._pure;

// ★ 设置就用**项目自己的** `.vscode/settings.json` ✓（不是编一份假设置 ✓）——
//   这样"项目用设置钉住 `pixel-pcb-v*`"这件事本身也被验到了 ✓。
const projRoot = path.join(PIX, '..', '..');
const setFile = path.join(projRoot, '.vscode', 'settings.json');
stub.cfg = fs.existsSync(setFile)
	? JSON.parse(fs.readFileSync(setFile, 'utf8').replace(/^\s*\/\/.*$/gm, ''))
	: {};
console.log('⓪ 项目设置：%s ⇒ pixelDiff.fzzPattern = %s',
	fs.existsSync(setFile) ? '.vscode/settings.json' : '（没有）', stub.cfg['pixelDiff.fzzPattern'] || '（用默认）');

let bad = 0;
const fail = (s, ...a) => { console.log('   ✗ ' + s, ...a); bad++; };

// ① 版本排序
const vers = listVersions(PIX);
// 名字里没有 `-vN` 的（通用模式下会碰到 ✓）就给 -1 ✓ ⇒ 这里不假设它一定有 ✓
const nums = vers.map((n) => { const m = /-v(\d+)/.exec(n); return m ? Number(m[1]) : -1; });
const sorted = nums.every((v, i) => i === 0 || nums[i - 1] <= v);
console.log('① 版本排序：共 %d 版，最后 4 个 = %s；单调递增 = %s',
	vers.length, vers.slice(-4).join(', '), sorted);
if (!vers.length || !sorted) fail('版本排序不对');

// ② 找最新清单
// ★ 2026-10-07 修 ✗：`diff/` 里现在还有 bb / sch 的清单（`diff-bb-*` / `diff-sch-*` ✓），
//   它们常常比 PCB 那份**更新** ✗ ⇒ ②③④ 会拿它们当样本 ⇒ ④（`.connectorN` 那套）
//   必然对不上 ✗。⇒ ②③④ 固定挑 **PCB** 那份（无视图段 ✓）；没有才退回最新的 ✓。
const pcbs = fs.existsSync(path.join(PIX, 'diff'))
	? fs.readdirSync(path.join(PIX, 'diff')).filter((n) => /^diff-v\d.*\.md$/.test(n))
		.map((n) => ({ n, t: fs.statSync(path.join(PIX, 'diff', n)).mtimeMs }))
		.sort((a, b) => b.t - a.t)
	: [];
const md = pcbs.length ? path.join(PIX, 'diff', pcbs[0].n) : newestDiffMd(PIX);
console.log('② 最新清单：%s', md ? path.basename(md) : '（没有）');
if (!md) fail('找不到 diff-*.md');
else {
	const raw = fs.readFileSync(md, 'utf8');

	// ③ 清单转 HTML（只打印计数 + 两条最硬的判据）
	const h = mdToHtml(raw);
	const n = (re) => (h.match(re) || []).length;
	console.log('③ 清单转 HTML：%d 字节；h1=%d h2=%d li=%d blockquote=%d code=%d',
		h.length, n(/<h1>/g), n(/<h2>/g), n(/<li>/g), n(/<blockquote>/g), n(/<code>/g));
	if (h.indexOf('<h1>') < 0 || h.indexOf('<li>') < 0) fail('HTML 里没有标题或列表');

	// ④ 「点行 ⇒ 高亮」的对应关系（端到端：清单里的脚名 ↔ svg 里的隐藏组 id）
	// ★ 2026-10-07 修 ✗：**不是每份清单都有脚名行** ✓ —— 实测 `diff-v57-v59.md` 只有
	//   ① 摆位「没动」✓ ＋ ② 网 ✓ ＋ ③ 过孔 ✓ ⇒ 一个 `.connectorN` 都没有 ✓
	//   （那是**真实内容** ✓，不是功能坏了 ✗；原版测试认定"最新那份必有脚名行" ✗ ⇒ 误报 ✗）。
	// ⇒ 改成**更强**的判据：本目录里凡**带脚名行**的清单，**每一份都验** ✓
	//   （一份过 ✗ ⇒ 不代表都对 ✓），一份都没有才报 ✗。
	const dd = path.join(PIX, 'diff');
	const mds = fs.existsSync(dd) ? fs.readdirSync(dd).filter((n) => /^diff.*\.md$/.test(n)) : [];
	let files = 0, groups = 0, hit = 0, miss = 0;
	for (const f of mds) {
		const p = path.join(dd, f);
		const svgP = p.replace(/\.md$/, '.svg');
		if (!fs.existsSync(svgP)) continue;
		const textHtml = mdToHtml(fs.readFileSync(p, 'utf8')).replace(/<[^>]+>/g, ' ');
		const RE = new RegExp(PAD_RE_SRC, 'g');       // ★ 用扩展里**那一条**正则（不是另写一条 ✗）
		const seen = new Set();
		let mm;
		while ((mm = RE.exec(textHtml))) seen.add(mm[1]);
		if (!seen.size) continue;                     // 这份清单没有脚名行 ✓（合法 ✓）
		files++;
		const svg = fs.readFileSync(svgP, 'utf8');
		const ids = new Set((svg.match(/<g id="pd-[^"]+"/g) || [])
			.map((s) => /id="([^"]+)"/.exec(s)[1]));
		groups = Math.max(groups, ids.size);
		for (const pad of seen) {
			if (ids.has('pd-' + pad)) hit++;
			else { miss++; console.log('   ✗ %s 里的 %s 在 svg 里没有对应组', f, pad); }
		}
	}
	console.log('④ 点行 ⇒ 高亮：带脚名行的清单 %d 份（最多 %d 组）；认出 %d 个脚、对不上 %d 个',
		files, groups, hit, miss);
	if (!files || !hit || miss) fail('点行与高亮组的对应关系不成立');
}
// ⑤ 目录发现（工具已搬去库仓 ⇒ 要**同时**认出项目目录与库仓根）
//   ★ 路径都从**已知的两个目录**推 ✓（✗ 别再数层级 ✗ —— 我数错过一次 ✓）：
//     PIX = 项目目录 `…/hardware/pixel` ⇒ 往上 2 层 = 项目仓根 ✓；
//     EXTDIR = 库仓 `…/tools/vscode-diff` ⇒ 往上 2 层 = 库仓根 ✓。
stub.workspace.workspaceFolders = [
	{ uri: stub.Uri.file(path.join(PIX, '..', '..')) },
	{ uri: stub.Uri.file(path.join(EXTDIR, '..', '..')) }
];
const dd = dirs();
console.log('⑤ 目录发现：项目 = %s；库仓 = %s', dd.proj || '（没找到）', dd.tool || '（没找到）');
if (!dd.proj || !dd.tool) fail('dirs() 没能同时找到项目目录与库仓工具');

// ⑥ 幻灯片：页面列表（按版本号递增 ✓）＋ 单页读取（至少一页带 svg 图 ✓）
//   ＋ 两处必须是**同一套容器结构** ✓（幻灯片曾把 svg 直接塞进 .pane.left ✗ ⇒
//     `.art svg{max-width:100%}` 不命中 ✗ ⇒ 图上下各多一大块空白 ✓）
const pl = pageList(PIX);
const ORD = { pcb: 0, bb: 1, sch: 2 };
// ★ 页序 = （视图 ①⇒②⇒③，版本 A，版本 B）✓ —— 名字多了**视图段** ✓
//   （`diff-bb-v100-v104.md` ✓；没视图段 = 老的 PCB ✓）。
const seq = pl.map((p) => {
	const m = /^diff-(pcb-|bb-|sch-)?v(\d+)[^-]*-v(\d+)/.exec(path.basename(p));
	return m ? [ORD[(m[1] || 'pcb-').slice(0, -1)], Number(m[2]), Number(m[3])]
		: [9e9, 9e9, 9e9];
});
const cmpk = (a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2];
const inc = seq.every((v, i) => i === 0 || cmpk(seq[i - 1], v) <= 0);
const withSvg = pl.filter((p) => readPage(p).svg).length;
const slideHtml = slideshowHtml({ cspSource: '' }, 'n', pl.length);
const ART = '<div class="art"';
// ★ 编辑器那份 HTML 也用**真函数**生成 ✓（✗ 不手写一份来比 ✗ —— 那就成了跟自己比 ✓）
const edHtml = html({ cspSource: '' }, fs.readFileSync(md, 'utf8'), readPage(md).svg,
	'', '', '', 'n');
const sameArt = edHtml.indexOf(ART) >= 0 && slideHtml.indexOf(ART) >= 0;
console.log('⑥ 幻灯片：%d 页；版本序递增 = %s；带图 %d 页；两处 .art 容器一致 = %s（最后一页：%s）',
	pl.length, inc, withSvg, sameArt, pl.length ? path.basename(pl[pl.length - 1]) : '—');
if (!pl.length || !inc || !withSvg || !sameArt) fail('幻灯片页面列表 / 容器结构不对');

// ⑦ 通用识别：**别的电路设计**那种目录也得认出来 ✓（2026-10-07 通用化 ✓）
//   ★ 造一个临时项目：没有 `pixel_nets.py` ✗、目录名也不叫 `pixel` ✗
//     ⇒ 只能靠「含 fzz」这条通用规则认出来 ✓（老逻辑会认不出 ✗）。
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pixdiff-'));
const tproj = path.join(tmp, 'hardware', 'myboard');
fs.mkdirSync(path.join(tproj, 'diff'), { recursive: true });
for (const n of ['board-a.fzz', 'board-b.fzz']) fs.writeFileSync(path.join(tproj, n), 'x');
fs.writeFileSync(path.join(tproj, 'diff', 'diff-board-a-board-b.md'), 'x');
const libRoot = path.join(EXTDIR, '..', '..');
stub.workspace.workspaceFolders = [{ uri: stub.Uri.file(tmp) }, { uri: stub.Uri.file(libRoot) }];
// ★ 先清掉**项目自己的**设置 ✓ —— 钉住的模式是 `^pixel-pcb-v\d+` ✓，而临时项目里叫
//   `board-a.fzz` ✗ ⇒ 不清就认不出来 ✓（★ 实测踩到过：这一步恰恰反证了"模式真的生效" ✓）。
const savedPat = stub.cfg['pixelDiff.fzzPattern'], savedDir = stub.cfg['pixelDiff.projectDir'];
delete stub.cfg['pixelDiff.fzzPattern'];         // 退回默认：所有 fzz ✓
stub.cfg['pixelDiff.projectDir'] = '';           // 先清掉钉住 ✓ 才能验"自动找" ✓
const d2 = dirs();
// ② 设置指哪就是哪 ✓（`pixelDiff.projectDir` ✓）
stub.cfg['pixelDiff.projectDir'] = tproj;
const d3 = dirs();
// ③ 相对路径那份也得解对 ✓（项目里写的就是 `hardware/pixel` 这种 ✓）
stub.cfg['pixelDiff.projectDir'] = path.join('hardware', 'myboard');
const d4 = dirs();
if (savedPat !== undefined) stub.cfg['pixelDiff.fzzPattern'] = savedPat;
if (savedDir !== undefined) stub.cfg['pixelDiff.projectDir'] = savedDir;
fs.rmSync(tmp, { recursive: true, force: true });
console.log('⑦ 通用识别：自动找 = %s（要 = %s）；绝对路径设置 = %s；相对路径设置 = %s；库仓 = %s',
	d2.proj === tproj ? '对' : (d2.proj || '（没找到）'), tproj,
	d3.proj === tproj ? '对' : d3.proj, d4.proj === tproj ? '对' : d4.proj,
	d2.tool ? '认到' : '（没认到）');
if (d2.proj !== tproj || d3.proj !== tproj || d4.proj !== tproj) {
	fail('非 pixel 项目 / 绝对设置 / 相对设置 这几种情形没认对');
}

// ⑧ 模式生效：同一个目录，换模式 ⇒ 名单跟着变 ✓
//   ★ 本项目实测：`hardware/pixel` 里 151 个 fzz ✓，但只有 76 个是 `pixel-pcb-v*` ✓ ⇒
//     ✗ 默认「所有 fzz」会把 75 个面包板/原理图稿混进选择框 ✗ ⇒ 项目用设置钉住 ✓。
const PAT_OLD = '^pixel-pcb-v\\d+.*\\.fzz$';
const old = listVersions(PIX, PAT_OLD);
const all = listVersions(PIX, '\\.fzz$');
const allSet = new Set(all);
console.log('⑧ 模式生效：钉住老模式 %d 个（都在模式内 = %s，都是全量的子集 = %s）；全量 %d 个',
	old.length, old.every((n) => new RegExp(PAT_OLD).test(n)), old.every((n) => allSet.has(n)), all.length);
if (!old.length || !old.every((n) => new RegExp(PAT_OLD).test(n) && allSet.has(n))) fail('模式没生效');

// ⑨ 三个视图各自的模式都得能用 ✓ —— 设置就从项目的 `.vscode/settings.json` 来 ✓
//   （本项目实测：pcb 76 个 / 面包板 20 个 / 原理图 57 个 ✓，三个都非空 ✓）
let bad9 = 0;
for (const v of ['pcb', 'bb', 'sch']) {
	const re = patRe(v), lst = listVersions(PIX, re.source);
	console.log('⑨ %s：模式 %s ⇒ %d 个%s', v, re.source, lst.length, lst.length ? '' : ' ✗');
	if (!lst.length) bad9++;
}
if (bad9) fail('有视图的 fzzPattern 没配好（空名单）');

// ⑩ 两类可点的行都得在**渲染后的文字**上认出来 ✓ —— 这是踩过两次的坑 ✗：
//   第一次按「反引号」写 ✗、第二次按「markdown 的 `**`」写 ✗ —— 浏览器里那两种标记
//   **都不在了** ✗（`mdToHtml` 把它们变成了 `<code>` / `<b>` ✓）⇒ 拿**真清单**验 ✓。
//   ★★ 2026-10-08 修 ✗：原来只拿"最新的那一份"验 ✗，还要求它**必须有位号行** ✗ ——
//     而"最新那份"完全可能是一张**什么都没变**的图（实测：`diff-sch-v39-v40.md` 只剩 1 条 ✓，
//     位号行合法地为 0 ✓）⇒ 误报 ✗（与 ④ 上次那条"最新那份必有脚名行"是**同一个坑** ✓）。
//     ⇒ 改成**扫全部** bb/sch 清单 ✓：带星号的行**一条都不许**有 ✓（渲染后 ★ 必须没了 ✓）；
//       两种图案**至少有一种**在真清单上认出来过 ✓（一份都没有才报 ✗ —— 那才说明图案废了 ✓）。
const viewMds = fs.readdirSync(path.join(PIX, 'diff')).filter((n) => /^diff-(bb|sch)-.*\.md$/.test(n))
	.map((n) => ({ n, t: fs.statSync(path.join(PIX, 'diff', n)).mtimeMs }))
	.sort((a, b) => b.t - a.t);
if (viewMds.length) {
	// ★ 逐条 `<li>` 验 ✓ —— webview 是**一条一条**匹配的 ✓（`^` 才有意义 ✓）；
	//   ✗ 第一版把整篇压成一行再匹配 ⇒ 换行没了 ⇒ 带 `^` 的图案 0 命中 ✗（当场报出来 ✓）。
	//   ★ 去标签要用**空串** ✗ 不能用空格 ✗ —— 浏览器 `textContent` 里 `<b>C1</b>：` = `C1：`
	//     （标签不占字符 ✓）；换成空格就变成 ` C1 ：` ✗ ⇒ 带 `^` / 紧跟冒号的图案全废 ✗
	//     （这个坑今天第三次了：反引号 ✗、星号 ✗、空格 ✗ ⇒ 一律"按渲染后的文字"写 ✓）。
	const padRe = new RegExp(reLit(PAD_RE_SRC)), rowRe = new RegExp(reLit(ROW_RE_SRC));
	let totPad = 0, totRow = 0, totStar = 0, totItems = 0, scanned = 0;
	for (const v of viewMds) {
		const items = (mdToHtml(fs.readFileSync(path.join(PIX, 'diff', v.n), 'utf8'))
			.match(/<li>[\s\S]*?<\/li>/g) || []).map((s) => s.replace(/<[^>]+>/g, '').trim());
		totItems += items.length; scanned++;
		totPad += items.filter((s) => padRe.test(s)).length;
		totRow += items.filter((s) => rowRe.test(s)).length;
		totStar += items.filter((s) => /\*\*/.test(s)).length;
	}
	console.log('⑩ 视图清单 %d 份 / %d 条行 ⇒ 脚名行 %d ✓、位号行 %d ✓、带星号的行 %d ✓（应为 0 ✓）',
		scanned, totItems, totPad, totRow, totStar);
	if (totStar || (!totPad && !totRow)) fail('视图清单的行在渲染后的文字里认不出来');
} else {
	console.log('⑩ 没有 bb/sch 清单可验（先跑一次 --view bb）✓');
}

// ⑪ ★★ 可点名字**不再靠图案猜** ✓（2026-10-08 修 ✗）：可点名字 = 图上 `pd-*` 组名 ✓
//   —— 验**用户报的那一类** ✓：面包板清单里「新增：Wire…、Wire…」那种**导线名** ✓，
//   必须在**渲染后的文字**里确实出现 ✓（原来那两条图案都认不出这类 ⇒ 一整串点不动 ✗）。
//   ★ 顺带把**真合并视图 HTML** 写出来 ✓ ⇒ 能用浏览器**真点一下**验收 ✓（不是自证 ✓）。
const bbMds = fs.readdirSync(path.join(PIX, 'diff')).filter((n) => /^diff-bb-.*\.md$/.test(n))
	.map((n) => ({ n, t: fs.statSync(path.join(PIX, 'diff', n)).mtimeMs }))
	.sort((a, b) => b.t - a.t);
if (bbMds.length) {
	const mp = path.join(PIX, 'diff', bbMds[0].n), svgp = mp.replace(/\.md$/, '.svg');
	const svg = fs.readFileSync(svgp, 'utf8');
	const keys = [...new Set((svg.match(/<g id="pd-[^"]+"/g) || [])
		.map((s) => /id="pd-([^"]+)"/.exec(s)[1]))];
	const text = mdToHtml(fs.readFileSync(mp, 'utf8')).replace(/<[^>]+>/g, ' ');
	const wireKeys = keys.filter((k) => /^Wire\d/.test(k));
	const okWire = wireKeys.filter((k) => text.indexOf(k) >= 0);
	console.log('⑪ %s：图上可点名字 %d 个（导线名 %d 个）⇒ 文字里出现 %d 个；**导线名可点 %d 个**',
		bbMds[0].n, keys.length, wireKeys.length,
		keys.filter((k) => text.indexOf(k) >= 0).length, okWire.length);
	if (!wireKeys.length || !okWire.length) fail('导线名在清单文字里认不出来（会点不动）');
	const stub = { cspSource: 'vscode-webview://x', asWebviewUri: (u) => u };
	const page = html(stub, fs.readFileSync(mp, 'utf8'), svg, 'img.png', 'diff-bb.png', '', 'NONCE');
	// ★ 写到**仓库内的 `_scratch/`** ✓（不是系统 Temp ✗）：浏览器对 Temp 里的文件报
	//   `Forbidden. File does not reside within a trusted folder.` ✗ ⇒ 点不动 ✓
	//   （2026-10-07 实测 ✓）；`_scratch/` 在 .gitignore 里 ✓ ⇒ 不污染仓库 ✓。
	const scratch = path.join(__dirname, '..', '..', '_scratch');
	if (!fs.existsSync(scratch)) fs.mkdirSync(scratch, { recursive: true });
	const out = path.join(scratch, 'merged-' + bbMds[0].n.replace(/\.md$/, '') + '.html');
	// ★ 只在**导出样张**里拆掉 CSP 那条 meta ✓ —— file:// 下浏览器不认 VS Code 的 nonce ✗
	//   ⇒ 脚本被拦 ✗（实测报 `Executing inline script violates … 'script-src 'nonce-NONCE''` ✓）⇒
	//   手点验收就做不成 ✓。★ VS Code 里的 webview **一个字不动** ✓（它会给对的 nonce ✓）。
	const pageNoCsp = page.replace(/<meta[^>]*[Cc]ontent-[Ss]ecurity-[Pp]olicy[^>]*>/g, '');
	fs.writeFileSync(out, pageNoCsp, 'utf8');
	console.log('   合并视图 HTML 已写出 ⇒ %s（可用浏览器真点一下 ✓）', out);
} else {
	console.log('⑪ 没有 bb 清单可验（先跑一次 --view bb）✓');
}

// ⑫ ★★ 「▶ 重放动画」按钮的位置与字（2026-10-08 改过三次口径 ✓）——
//     ① **合并视图要有** ✓（双击 `diff/*.md` = 这个界面 ✓）；
//     ② **幻灯片那条工具条上要没有** ✗（用户 2026-10-08：「点击截图1中工具栏上的【重放动画】
//        按钮，没有反应。建议删掉工具栏的【重放动画】按钮，使用截图2的方式」✓ ⇒ 撤掉了 ✓）；
//     ③ ★ 按钮必须在**图那一栏里、图的正下方** ✓（用户：「把这个嵌入在**差异的下面**就好了吧？」✓）
//        —— ★ 这条单测**真的切开两栏**量位置 ✓（✗ 不是"HTML 里有这个 id"就算过 ✗：
//        原来按钮在**右栏工具条**上 ✓，图在左栏 ⇒ 离图十万八千里 ✗）；
//     ④ 它还得**钉在栏底** ✓（`position:sticky; bottom:0` ✓ —— 图比一屏高时也够得着 ✓）；
//     ⑤ 工具条**钉在顶上** ✓（清单比一屏长时，提示不许跟着滚走 ✗）；
//     ⑥ **右栏字号 = 按钮字号** ✓（用户：「右侧内容字体可以小一些，跟重放动画几个字的字体一样大即可」✓）
//        ⇒ `.right` 与 `h1/h2/h3` 都得是 **12px** ✓。
const edBar = html({ cspSource: '' }, fs.readFileSync(md, 'utf8'), readPage(md).svg, '', '', '', 'N');
const slBar = slideshowHtml({ cspSource: '' }, 'N', 1);
const hasId = (s, id) => s.indexOf('id="' + id + '"') >= 0;
const sticky = CSS.indexOf('position:sticky') >= 0;
const rightFs = /\.right \{[^}]*font-size:\s*12px/.test(CSS);
const headFs = /h1,\s*h2,\s*h3\s*\{\s*font-size:\s*1em/.test(CSS);
const leftPane = (/<div class="pane left">([\s\S]*?)<div class="pane right">/.exec(edBar) || [, ''])[1];
const rightPane = (/<div class="pane right">([\s\S]*?)<\/div>\s*<script/.exec(edBar) || [, ''])[1];
const underArt = leftPane.indexOf('class="art"') >= 0
	&& leftPane.indexOf('id="pd-replay"') > leftPane.indexOf('class="art"');
const notInRight = rightPane.indexOf('id="pd-replay"') < 0;
const underSticky = /\.under \{[^}]*position:\s*sticky[^}]*bottom:\s*0/.test(CSS);
console.log('⑫ 按钮与字号：合并视图按钮 = %s；幻灯片按钮 = %s（应为 false ✗）；'
	+ '按钮在图下面 = %s；不在右栏 = %s（应为 true ✓）；栏底钉住 = %s；'
	+ '工具条钉顶 = %s；右栏 12px = %s；标题 1em = %s',
	hasId(edBar, 'pd-replay'), hasId(slBar, 'replay'), underArt, notInRight, underSticky,
	sticky, rightFs, headFs);
if (!hasId(edBar, 'pd-replay') || hasId(slBar, 'replay') || !underArt || !notInRight
	|| !underSticky || !sticky || !rightFs || !headFs) {
	fail('「▶ 重放动画」按钮位置不对（该在图下面却没在 / 或右栏字号没跟按钮一样大）');
}

// ⑬ ★★ 面包板的**跳线身份是"接的哪两个孔"** ✗ 不是导线名 ✗（2026-10-08 修 ✓）——
//   用户原话：「面包板比较是这样的，看着很乱啊」✓。根因：Fritzing **一存就把所有 Wire 重新编号**
//   （实测 `pixel-breadboard95 ⇒ 104`：19 条连接里 **14 条一模一样** ✓，名字一条没留 ✗）
//   ⇒ 按名字比对时它们变成「28 条新增 ＋ 28 条没了」✗ ⇒ 图上凭空冒出 28 对红圈红字 ✓。
//   ⇒ 判据：清单里**必须**出现「没动 N 条」且 **N > 0** ✓（按名字比 ⇒ 恒为 0 ✗ ⇒ 当场报 ✗）；
//     并且每条连接都要写出**孔位** ✓（人一眼看懂接了哪儿 ✓）。
if (bbMds.length) {
	const txt = fs.readFileSync(path.join(PIX, 'diff', bbMds[0].n), 'utf8');
	const m13 = /没动\s*(\d+)\s*条/.exec(txt);
	const holes = (txt.match(/(?:^|[（、])(pin\d+[A-Z](?:[–-]pin\d+[A-Z])?)/gm) || []).length;
	const nLinks = Number(m13 ? m13[1] : -1);
	console.log('⑬ 跳线身份按孔对：%s ⇒ 没动 %d 条（>0 才说明"只改名"没被当成"没了"✓）；孔位写法 %d 处',
		bbMds[0].n, nLinks, holes);
	if (!(nLinks > 0) || !holes) fail('面包板跳线还是按名字比对（改名⇒全成"新增/没了"）');
} else {
	console.log('⑬ 没有 bb 清单可验（先跑一次 --view bb）✓');
}

// ⑭ ★★ 「点名字」**不许吃掉文字** ✗（2026-10-08 修 ✓）—— 用户清单里
//   「**新增**：pin11I–pin13I（Wire90013126）、…」渲染出来只剩「新增Wire90013126）、…」✗
//   （**遇到第一个名字之前**攒下的字符被丢掉 ✗ —— 那段 TreeWalker 脚本的 bug ✓）。
//   现在包名字这一步是 Node 里的**纯函数** `markNames()` ✓ ⇒ 不用开浏览器就能判死 ✓：
//   ① **去标签后的文字必须一字不差** ✓（等于 `mdToHtml` 的结果去掉标签 ✓）；
//   ② 包出来的 `span.pd-hit` 个数 == 文字里真出现的名字次数 ✓；
//   ③ 同一个名字**不许**在别处被误包（属性里不碰 ✓）。
const { keysOf, markNames } = ext._pure;
let totSpans = 0, totNames = 0, n14 = 0, lost = 0;
for (const n of fs.readdirSync(path.join(PIX, 'diff')).filter((x) => /^diff-(bb|sch)-.*\.md$/.test(x))) {
	const svgp = path.join(PIX, 'diff', n.replace(/\.md$/, '.svg'));
	if (!fs.existsSync(svgp)) continue;
	const raw = mdToHtml(fs.readFileSync(path.join(PIX, 'diff', n), 'utf8'));
	const keys = keysOf(fs.readFileSync(svgp, 'utf8'));
	const marked = markNames(raw, keys);
	const plain = (s) => s.replace(/<[^>]+>/g, '');
	// ① 吃字？⇒ 去标签后逐字节比 ✓（这里比的是"去掉 span 外壳后原样回来" ✓）
	if (plain(marked) !== plain(raw)) {
		lost++; console.log('   ✗ %s：包名字时**文字变了**（吃字 ✗）', n);
	}
	// ② 个数：文字里出现的名字次数（长的先算 ✓，与实现同序 ✓）应等于 span 个数 ✓
	const cntIn = (s) => {
		let c = 0, i = 0;
		while (i < s.length) {
			if (s[i] === '<') { const j = s.indexOf('>', i); i = j < 0 ? s.length : j + 1; continue; }
			const hit = keys.find((k) => s.startsWith(k, i));
			if (hit) { c++; i += hit.length; } else i++;
		}
		return c;
	};
	const want = cntIn(raw);
	const got = (marked.match(/class="pd-hit"/g) || []).length;
	if (want !== got) { lost++; console.log('   ✗ %s：想包 %d 个、实际包了 %d 个', n, want, got); }
	n14++; totSpans += got; totNames += keys.length;
}
console.log('⑭ 包名字不吃字：%d 份清单 ⇒ 包了 %d 个可点名字（图上共 %d 个键）；文字有出入 %d 份',
	n14, totSpans, totNames, lost);
if (!n14 || !totSpans || lost) fail('「点名字」这一步会吃掉/改动清单文字');

// ⑮ ★★ 图上**不许有文字提示** ✗（2026-10-08 下午定 ✓）—— 用户原话：
//   「面包板差异，仍然有新增跳线、线路变了、没了跳线等文字提示，请把这些文字提示去掉」✓。
//   ⇒ 判据：bb/sch 那两张图上**没有** `pd-labels` 层 ✓、也**没有**任何 `新增/没了/线路变了/Δ …`
//     的文字 ✓（渲染器自己画的零件字/丝印**不算** ✗ —— 那不是我们的提示 ✓）。
//   ★ 用**一条正则**判 ✓（见下 ✓），✗ 不逐个数 `<text>` ✗ —— 图里本来就有一百多个**零件**的字 ✓。
const ANN_RE = /<text[^>]*>[^<]*(新增|没了|线路变了|Δ)/;
let n15 = 0, ann = 0, lab = 0;
for (const f of fs.readdirSync(path.join(PIX, 'diff')).filter((x) => /^diff-(bb|sch)-.*\.svg$/.test(x))) {
	const svg = fs.readFileSync(path.join(PIX, 'diff', f), 'utf8');
	n15++;
	if (ANN_RE.test(svg)) { ann++; console.log('   ✗ %s：图上还有文字提示', f); }
	if (svg.indexOf('<g id="pd-labels">') >= 0) { lab++; console.log('   ✗ %s：标签层还在', f); }
}
console.log('⑮ 图上不写字：%d 张 bb/sch 图 ⇒ 带文字提示 %d 张、带标签层 %d 张（都应为 0 ✓）',
	n15, ann, lab);
if (!n15 || ann || lab) fail('图上还留着文字提示（用户要求去掉）');

// ⑯ ★★ 动画的**起播口径**：进来不自动播（= 看到的静止图是 A+B）；点「▶ 重放动画」才起播 ✓
//   —— 用户 2026-10-08 定：「进入时不自动播放，而是显示 A+B，点击【重放动画】时，
//   才从 A 开始变化到 B，并在结束后停留在 B」✓。四处都要对 ✓：
//     ① 图上**不许**有内联 `style="animation:"` ✗（有 ⇒ 一进页面自己就跑 ✓）；
//     ② 图上**不许**有那个内置播放键（`anim-btn` ✗ —— 用户要求撤掉 ✓）；
//     ③ 动画名字挂 `data-anim` ✓、一轮时长挂根上的 `data-anim-dur` ✓（两者都要有 ✓）；
//     ④ 两个界面的起播脚本都要**认 `data-anim`** ✓（✗ 不是把 currentTime 拨回 0 那套 ✗ ——
//        那套只能"重播已经在跑/已跑完"的动画 ✓，进来时根本没动画可拨 ✓）。
let n16 = 0, noDur = 0, inlineAnim = 0, btn = 0, mismatch = 0;
for (const f of fs.readdirSync(path.join(PIX, 'diff')).filter((x) => /^diff-(bb|sch)-.*\.svg$/.test(x))) {
	const svg = fs.readFileSync(path.join(PIX, 'diff', f), 'utf8');
	const kf = (svg.match(/@keyframes/g) || []).length;
	if (!kf) continue;                                    // 没变化的图没有动画 ✓ 跳过 ✓
	n16++;
	const root = (/<svg[^>]*>/.exec(svg) || [''])[0];
	if (!/data-anim-dur="[\d.]+"/.test(root)) { noDur++; console.log('   ✗ %s：根上没有 data-anim-dur', f); }
	if (/style="animation:/.test(svg)) { inlineAnim++; console.log('   ✗ %s：还有内联 animation（会自己播）', f); }
	if (svg.indexOf('anim-btn') >= 0) { btn++; console.log('   ✗ %s：图里那个播放键还在', f); }
	const n = (svg.match(/data-anim="/g) || []).length;
	if (n !== kf) { mismatch++; console.log('   ✗ %s：data-anim %d 条 ≠ keyframes %d 条', f, n, kf); }
}
// ★★ 2026-10-08 **第二次改口径** ✓（用户：「面包板差异是可以在右侧、『面包板差异清单』上方
//   显示【播放差异】的吧？」✓）：幻灯片**右栏顶上也放一个** ✓（`#pd-replay` ✓）——
//   ★ 撤掉的只是**顶栏**那条上的「▶ 重放动画」✗（`id="replay"` ✓，别又冒出来 ✗）。
//   ⇒ 这条现在守两件事 ✓：① 顶栏**没有**旧按钮 ✓；② 两处的起播**是同一份实现** ✓ ——
//   ✗ 不是"幻灯片里有没有按钮" ✗（那是第 ⑱ 项的事 ✓）。
//   ★ 注意 `edBar`/`slBar` 是在第 ⑫ 项那里生成的 ✓（两处 HTML ✓），这儿直接用 ✓。
// ★ 抓函数体**不能靠非贪婪正则** ✗ —— `function pdReplay(){…}` 里还有**内层**的 `}` ✓
//   （`for` / `if` 那些 ✓）⇒ `/…[\s\S]*?\n\s*\}/` 会**提前收尾** ✗（实测：抓到的半截里
//   连 `btn.textContent` 都没有 ✓ ⇒ 断言假失败 ✓）。⇒ 老老实实**数花括号** ✓。
const fnSrc = (s, name) => {
	const i = s.indexOf('function ' + name + '(');
	if (i < 0) return '';
	let depth = 0;
	for (let k = s.indexOf('{', i); k >= 0 && k < s.length; k++) {
		if (s[k] === '{') depth++;
		else if (s[k] === '}' && !--depth) return s.slice(i, k + 1);
	}
	return '';
};
const startCode = edBar.indexOf('getAttribute("data-anim")') >= 0;
const pdReplayOf = (s) => fnSrc(s, 'pdReplay');
const noOldButton = slBar.indexOf('id="replay"') < 0;
const oneImpl = pdReplayOf(edBar) !== '' && pdReplayOf(edBar) === pdReplayOf(slBar);
// ★★ 回显**不能把按钮内容整体覆盖** ✗（2026-10-08 实测撞到 ✓）：幻灯片那个按钮里是
//   "**画出来的图形** ＋ 文字" ✓ ⇒ 整体覆盖会把图形**冲掉** ✓（`.lbl` ✓ 就是为这个拆出来的 ✓）。
//   ⇒ 判据：脚本里得**先找 `.lbl`、找不到才回落到按钮** ✓（合并视图那个没有 `.lbl` ✓）。
const fbOk = /querySelector\("\.lbl"\) \|\| btn/.test(pdReplayOf(slBar))
	&& /lbl\.textContent = "重放中/.test(pdReplayOf(slBar))
	&& !/btn\.textContent\s*=\s*[^;]*重放中/.test(pdReplayOf(slBar));
console.log('⑯ 起播口径：%d 张带动画的图 ⇒ 缺 data-anim-dur %d、内联 animation %d、图内播放键 %d、条数不匹配 %d；'
	+ '合并视图脚本认 data-anim = %s；幻灯片顶栏没有旧按钮 = %s；两处起播同一份实现 = %s；'
	+ '回显只改文字（✗ 不冲掉图形） = %s',
	n16, noDur, inlineAnim, btn, mismatch, startCode, noOldButton, oneImpl, fbOk);
if (!n16 || noDur || inlineAnim || btn || mismatch || !startCode || !noOldButton || !oneImpl || !fbOk) {
	fail('动画要么会自己播、要么点了播不起来（口径：进来 = A+B、点了从 A 到 B、停在 B）');
}

// ⑰ ★★ **注入 webview 的脚本必须语法正确** ✗ —— 2026-10-08 的实锤 ✓：
//   为了共用起播那段，我把它抽成 `replayJs()`（返回**数组** ✓），外层却写成 `replayJs(),` ✗
//   ⇒ `Array.join()` 把**嵌套数组**按 `,` 拼进来 ✗ ⇒ 生成 `function pdReplay(){,    var svg = …` ✗
//   ⇒ **整段脚本语法错误** ✓ ⇒ webview 里**一个字符都不执行** ✓ ⇒ 用户报「点击重放按钮没有反应」✓
//   （而且点行高亮、Esc 也一起失效 ✓ —— 症状比"按钮没反应"更宽 ✓）。
//   ★ 教训 ✗：上一版测试只断言"HTML 里出现过 `data-anim` 这串字" ✓ —— 那**语法错也照样过** ✗。
//   ⇒ 这里直接 `new Function(脚本)` ✓（**不是**自己再写一条判据 ✓）：语法错就抛 ✓，当场抓住 ✓。
let n17 = 0, bad17 = 0;
for (const [name, s] of [['合并视图', edBar], ['幻灯片', slBar]]) {
	const m = /<script nonce="[^"]*">([\s\S]*?)<\/script>/.exec(s);
	if (!m || !m[1].trim()) { bad17++; console.log('   ✗ %s：抽不到注入脚本', name); continue; }
	n17++;
	try {
		new Function(m[1]);                        // ★ 只为**语法**检查 ✓（不执行 ✓）
	} catch (e) {
		bad17++;
		console.log('   ✗ %s：注入脚本语法错 ⇒ webview 里整段不跑：%s', name, e.message);
	}
	// ★ 顺带把"抽出来的脚本"落盘 ✓ ⇒ 出事时能直接 `node --check` 那份 ✓（= 可复核 ✓）
	const dump = path.join(__dirname, '..', '..', '_scratch', 'inject-' + (name === '幻灯片' ? 'slide' : 'editor') + '.js');
	try { fs.writeFileSync(dump, m[1], 'utf8'); } catch (e) { /* 落盘失败不算错 ✓ */ }
}
console.log('⑰ 注入脚本语法：%d 份 ⇒ 语法错 %d 份（落盘在 _scratch/inject-*.js ✓ 出事能直接 node --check ✓）',
	n17, bad17);
if (!n17 || bad17) fail('注入 webview 的脚本语法错 → 按钮/高亮全都没反应');

// ⑱ ★★ 幻灯片工具的**三个按钮**（2026-10-08 用户定 ✓）——
//   「1. <上一条 改为←，鼠标放在←上时，显示上一条 2. 下一条> 改为→ … 显示下一条
//     3. ▶自动播放 改为 ▶，… 显示自动播放；点击▶，切换为停止符号，… 显示停止，
//     **不用暂停符号和暂停词语**」✓ ⇒ 五件事都要对上 ✓：
//     ① 按钮上**只有符号** ✓（`←` / `▶` / `→` ✓ —— ✗ 不许再带「上一条 / 自动播放」的字 ✗）；
//     ② 提示走 **`title`** ✓（`上一条` / `下一条` / `自动播放` ✓）；
//     ③ 点 ▶ ⇒ 文字变 **`■`** ✓、`title` 变 **`停止`** ✓；
//     ④ ✗ **不许出现「暂停」二字、也不许出现 ⏸** ✗（用户明确否掉 ✓）；
//     ⑤ ★ **顺序是 `← ▶ →`** ✓（用户：「把 **▶ 和 → 互换一下位置**」✓ —— 原来是 `← → ▶` ✗）
//        ⇒ 从 HTML 里**按出现次序**抠出三个 id 来对 ✓（✗ 不是"三个都在"就算过 ✗）；
//     ⑥ ★ **文件名另起一行** ✓（用户：「把文件名显示在 ← 下面那一行 …… 超了用 … 截断、
//        悬停看全名」✓）⇒ **左列的第 2 行** ✓（见 ⑪ ✓）；
//     ⑦ ★ **文件名最多 40 个字符** ✓（用户 2026-10-08：「最长 40 个字符吧，再长就省略」✓）
//        ＋ ★ **要带扩展名** ✓（用户：「文件名不加扩展名吗？」✓ —— 原来 `title` 是 stem ✗，
//        可同名的 `.md`/`.svg`/`.png` 有三个 ✓ ⇒ 分不出指的是哪个 ✗）
//        ⇒ 见下面那段：**真跑**注入脚本里的 `clip()` ✓（✗ 别在测试里再抄一遍规则 ✗）；
//        ★ 截长名字时**扩展名要留到最后** ✓（截主干 ✓ ⇒ 否则"要看见扩展名"在长名字上失效 ✗）。
//     ⑧ ★ **`每 N 秒` 只能 3..99** ✓（用户：「那个输入框太长了，应限制为只能输入 3-99 的数字」✓）
//        ⇒ `type=number` ＋ `min`/`max` ✓（箭头用 ✓）＋ **真跑** `secs()` ✓ 钳手打的 0 / 500 ✓；
//     ⑨ ★ **`2 / 3` 不许折行** ✓（用户：「不能换行，必须在同一行了」✓）⇒ `#pos` 得 `white-space:nowrap` ✓
//        —— ★ 实测过它真的会折 ✓（520px 窗口下量到 16×27 ✓ = 一列一个字 ✓）；
//     ⑩ ★ **提示挪到右列** ✓（用户：「←/→ 翻页 空格 播放/停止… 这些是可以两行的，
//        用文件名后面的空间写两行」✓ ＋「**放到右列**」✓）⇒ 提示在 `.head` 里、
//        但**不在** `.hcol`（左列）里 ✓，且 `.tips` **允许折行** ✓；
//     ⑪ ★★ **顶部 = 两列，左列两行，右列一行** ✓（用户 2026-10-08：「把顶部变为两列，
//        左列两行，右列一行」✓）⇒ `.head` 的直接孩子就是 `.hcol` ＋ `.tips` 两列 ✓；
//        **左列**里头是 `hrow`（按钮行 ✓）＋ `.name`（文件名 ✓）**两行** ✓，且**文件名在后** ✓
//        （★ 量的是**标签顺序** ✓ —— ✗ 不是"两个都在"就算过 ✗，顺序反了就是文件名在上面 ✗）。
const slHtml = slideshowHtml({ cspSource: '' }, 'N', 1);
const tips = ['上一条', '下一条', '自动播放'];
const noWords = !/<button[^>]*>(?![←→▶■])[^<]*(上一条|下一条|自动播放|暂停)/.test(slHtml);
const hasTitles = tips.every((t) => slHtml.indexOf('title="' + t + '"') >= 0);
const stopOk = slHtml.indexOf('\\u25a0') >= 0 && slHtml.indexOf('停止') >= 0;
const noPause = slHtml.indexOf('暂停') < 0 && slHtml.indexOf('⏸') < 0 && slHtml.indexOf('\\u23f8') < 0;
// ★ 顶部结构：`.head` 里 = `.hcol` ＋ `.tips` 两列；`.hcol` 里 = `hrow` ＋ `.name` 两行。
const headBlock = (/<div class="head">([\s\S]*?)<div class="wrap">/.exec(slHtml) || [, ''])[1];
const hcolBlock = (/<div class="hcol">([\s\S]*?)<div class="tips">/.exec(slHtml) || [, ''])[1];
const hrowBlock = (/<div class="hrow">([\s\S]*?)<\/div>/.exec(slHtml) || [, ''])[1];
const twoCols = headBlock.indexOf('class="hcol"') >= 0 && headBlock.indexOf('class="tips"') > headBlock.indexOf('class="hcol"');
const leftTwoRows = hcolBlock.indexOf('class="hrow"') >= 0
	&& hcolBlock.indexOf('id="name"') > hcolBlock.indexOf('class="hrow"');
const row1All = ['prev', 'play', 'next', 'sec', 'pos'].every((id) => hrowBlock.indexOf('id="' + id + '"') >= 0);
const hintInRight = headBlock.indexOf('翻页') > headBlock.indexOf('class="hcol"')
	&& hcolBlock.indexOf('翻页') < 0 && /\.tips \{[^}]*white-space:normal/.test(slHtml);
// ★★ 顺序量的是**那条按钮行** ✓（`hrow` ✓）—— ✗ 不是"整页的按钮" ✗：
//   2026-10-08 右栏**顶上**又多了个 `#pd-replay` ✓（用户要的 ✓）⇒ 按整页抠会把它算进来 ✗
//   ⇒ 顺序看着就"多了一个"✓ —— 但它根本不在顶栏那条上 ✓（这是**量错了地方** ✗，不是改坏了 ✓）。
const btnOrder = (hrowBlock.match(/<button id="([^"]+)"/g) || []).map((s) => /id="([^"]+)"/.exec(s)[1]).join(',');
const orderOk = btnOrder === 'prev,play,next';
const numbersOnly = /<input id="sec" type="number" min="3" max="99"/.test(slHtml);
const posNowrap = /#pos \{[^}]*white-space:nowrap/.test(slHtml);
// ★★ 2026-10-08 用户定 ✓：「面包板差异**是可以在右侧、『面包板差异清单』上方显示【播放差异】的吧**？」✓
//   ⇒ 右栏**顶上一条**放着按钮 ✓，**在 `#list` 之前** ✓（`#list` 里就是「面包板差异清单」那份清单 ✓）。
//   ★ 量**位置关系** ✓（✗ 不是"页面上有这个 id"就算过 ✗ —— 那样它跑到别处也照样过 ✓）。
//   ★★ 2026-10-08 用户指出的**语义差别** ✓：「两者完全不同啊！「▶ 重放动画」是从一个 md，到另一个 md。
//     「▶ 播放差异」是**在一个 md 内，从 A 播放到 B**。⇒ 「▶ 播放差异」的 ▶ 应该换成
//     **步进播放含义的字符**」✓ ⇒ 两处符号 **⏭**（U+23ED ✓，步进/跳到下一处 ✓）——
//     ★ 这条单测因此**盯住"两边符号不一样"** ✓：合并视图 = ▶（重放 ✓）、幻灯片 = ⏭（步进 ✓）
//     （✗ 不许又变回同一个符号 ✗ —— 那会把两个不同的动作看成一个 ✓）。
const slRightPane = (/<div class="pane right">([\s\S]*?)<script/.exec(slHtml) || [, ''])[1];
// ★★ 2026-10-08 用户定 ✓：幻灯片那个按钮的记号**用 CSS 画** ✓（「**从 css 画**，border-left + 三角，
//   **border-left 与三角要等高**」✓）—— ✗ 不是字符 ✗（Unicode 里"竖线 ＋ 单个右三角"没有整字 ✓）。
//   ⇒ 守四件事 ✓：① 按钮里有 `.step` ＋ `.lbl` ✓（文字单独一块 ✓，回显才不会把图形冲掉 ✓）；
//   ② ⚠ **等高**：容器一个 height ✓ ＋ 两块都 height:100% ✓ ⇒ **结构上就是同一个高度** ✓
//      （✗ 第一版三角用 border 拼 ✗ ⇒ 实测 11.80 vs 11.9988 ✓：**边框宽度会被吸附到设备像素** ✓，
//       高度不会 ✓ ⇒ "等高"当场不成立 ✗ —— 所以不能靠"数相加 == 容器高" ✗，得靠**同源** ✓）；
//   ③ 竖线**就是 border-left** ✓（用户原话 ✓）；④ 三角是 clip-path 切出来的 ✓、颜色 currentColor ✓。
const replayInRight = slRightPane.indexOf('id="pd-replay"') >= 0
	&& slRightPane.indexOf('id="pd-replay"') < slRightPane.indexOf('id="list"')
	&& /<div class="bar"><button id="pd-replay">\s*<span class="step" aria-hidden="true"><\/span>\s*<span class="lbl">播放差异<\/span><\/button><\/div>/.test(slRightPane);
const px = (css, re) => { const m = re.exec(css); return m ? Number(m[1]) : NaN; };
const stepBox = /\.step \{([^}]*)\}/.exec(slHtml);
const stepBefore = /\.step::before \{([^}]*)\}/.exec(slHtml);
const stepAfter = /\.step::after \{([^}]*)\}/.exec(slHtml);
const stepH = stepBox ? px(stepBox[1], /height:\s*([\d.]+)px/) : NaN;
const bothPercent = !!stepBefore && !!stepAfter && /height:\s*100%/.test(stepBefore[1]) && /height:\s*100%/.test(stepAfter[1]);
const stepCentered = !!stepBox && /align-items:\s*center/.test(stepBox[1]);
const barIsBorder = !!stepBefore && /border-left:\s*[\d.]+px solid currentColor/.test(stepBefore[1]);
const triIsClip = !!stepAfter && /clip-path:\s*polygon\(/.test(stepAfter[1]);
const heightsEqual = stepH > 0 && bothPercent;                     // ★ 同源 ⇒ 一定相等 ✓
const stepSample = `容器高 ${stepH}px；竖线 height:100% = ${bothPercent}；竖线是 border-left = ${barIsBorder}；`
	+ `三角 clip-path = ${triIsClip}；居中 = ${stepCentered}`;
// ★ 两处记号**仍然不同** ✓（用户：「两者**完全不同**啊！」✓）——
//   合并视图 = **▶ 字符**（重放 ✓）；幻灯片 = **CSS 画的 `.step`**（步进 ✓）。
//   ★ 判据必须**只看那个按钮自己** ✗（✗ 别看整个页面 ✗ —— 实测栽过 ✓：
//     `slHtml` 里本来就有别的 ▶ ✓（那是"自动播放"按钮 ✓）、⏭ 也只是**注释里提过** ✓
//     ⇒ 全页搜字符必然假失败 ✓）。
const btnOf = (s) => (/<button id="pd-replay">([\s\S]*?)<\/button>/.exec(s) || [, ''])[1].trim();
const edBtn = btnOf(edBar), slBtn = btnOf(slHtml);
const glyphsDiffer = edBtn === '\u25B6 重放动画'
	&& /class="step"/.test(slBtn) && /class="lbl">播放差异</.test(slBtn)
	&& !/[\u25B6\u23ED\u23EE\u21E5\u23F5]/.test(slBtn);     // ★ 幻灯片那个按钮里**不许有字符记号** ✓
// ★★ 「文件名不加扩展名吗？」（2026-10-08 用户问 ✓）—— ★ 这条**真读一页** ✓
//   （✗ 不是"源码里有没有 basename"就算过 ✗）：同名的 `.md` / `.svg` / `.png` 有三个 ✓
//   ⇒ 名字里**必须**带 `.<ext>` ✓，否则分不出这一页指的是哪个文件 ✗。
let titleOk = false, titleSample = '没找到 diff-*.md 可读';
{
	const bbMd = fs.readdirSync(path.join(PIX, 'diff'))
		.filter((n) => /^diff-.*\.md$/.test(n)).sort()[0];
	if (bbMd) {
		const t = readPage(path.join(PIX, 'diff', bbMd)).title;
		titleOk = t === bbMd && /\.md$/.test(t);
		titleSample = `${bbMd} ⇒ title = ${t}`;
	}
}
// ★★ 2026-10-08 用户报「**顶部高度不够**」✓ —— 截图上那个「每 N 秒」输入框**下边框没了** ✓、
//   文件名只剩半截 ✓。根因**不是**"头写矮了" ✗，是**头被压缩了** ✗：
//   `.head` 是 body 那个**竖排 flex** 的孩子 ✓ ⇒ 默认 `flex-shrink:1` ✓；
//   而它为了"横向不撑破"带了 `overflow:hidden` ✓ ⇒ **按 flex 规范，overflow 不是 visible 的孩子
//   自动最小尺寸算 0** ✗ ⇒ 内容比一屏高时它**跟 .wrap 一起被压** ✓（实测：需要 41px 的头被压到
//   16~29px ✓、`scrollHeight 41 > clientHeight 29` ✓）⇒ `align-items:center` 再把 40px 的左列
//   往中间一挤 ✓ ⇒ **上下一起切** ✗ —— 看着就像"高度不够" ✓。
//   ⇒ 头**不许缩** ✓（`flex:0 0 auto` ✓）；★ 这条量的是**病因**本身 ✓（✗ 不是"有没有 52px" ✗
//   —— 那得跑浏览器 ✓）：只要 `.head` 又是 `overflow:hidden` 又**没**钉住 flex-shrink ⇒ 就会复发 ✓。
const headCss = (/\.head \{([^}]*)\}/.exec(slHtml) || [, ''])[1];
const headNoShrink = /flex:0 0 auto/.test(headCss) || /flex-shrink:\s*0/.test(headCss);
const headHazard = /overflow:hidden/.test(headCss) && !headNoShrink;
const wrapShrinks = /\.wrap \{[^}]*flex:1 1 auto/.test(slHtml) && /\.wrap \{[^}]*min-height:0/.test(slHtml);
// ★★ 文件名**最多 40 个字符** ✓ —— ★ 这里**把注入脚本里那个 clip() 抠出来真跑一遍** ✓
//   （✗ 不是"源码里有 40 这串字"就算过 ✗，也不是在这里**再写一遍**截断规则 ✗ —— 那就是两份实现 ✓）。
// ★★ 文件名**最多 40 个字符** ✓ —— ★ 这里**把注入脚本里那个 clip() 抠出来真跑一遍** ✓
//   （✗ 不是"源码里有 40 这串字"就算过 ✗，也不是在这里**再写一遍**截断规则 ✗ —— 那就是两份实现 ✓）。
const clipSrc = fnSrc(slHtml, 'clip');
let clipOk = false, clipSample = '抠不到 clip()';
if (clipSrc) {
	try {
		const clip = new Function('return (' + clipSrc + ')')();
		const A = (s) => Array.from(s);
		const long = clip('diff-bb-v100-v104_' + 'x'.repeat(60) + '.md');   // 83 字
		const at40 = clip('y'.repeat(40));
		const at39 = clip('y'.repeat(39));
		const at41 = clip('y'.repeat(41));
		const longNoExt = clip('z'.repeat(60));
		clipSample = `83 字（带 .md）⇒ ${A(long).length} 字（末四字 ${A(long).slice(-4).join('')}）；`
			+ `41 字 ⇒ ${A(at41).length}（末字 ${A(at41).slice(-1)[0]}）；`
			+ `40 字 ⇒ ${A(at40).length}（原样 = ${at40 === 'y'.repeat(40)}）；`
			+ `39 字 ⇒ ${A(at39).length}（原样 = ${at39 === 'y'.repeat(39)}）；`
			+ `60 字无扩展名 ⇒ ${A(longNoExt).length}`;
		clipOk = A(long).length === 40 && long.endsWith('.md') && long.indexOf('…') >= 0   // ★ 扩展名留着 ✓
			&& A(at41).length === 40 && A(longNoExt).length === 40
			&& at40 === 'y'.repeat(40) && at39 === 'y'.repeat(39)
			// ★ 还得**真用上** ✓（✗ 定义了却没人调，等于没限 ✗）
			&& slHtml.indexOf('$("name").textContent = clip(d.title)') >= 0;
	} catch (e) { clipSample = 'clip() 跑不起来：' + e.message; }
}
// ★★ `每 N 秒` 只能 3..99 ✓ —— 同法：**把 secs() 抠出来，喂几个越界的值真跑一遍** ✓。
const secsSrc = fnSrc(slHtml, 'secs');
let secsOk = false, secsSample = '抠不到 secs()';
if (secsSrc) {
	try {
		// 注入那句是 `$("sec")` ✓ ⇒ 给个假 `$` 就够 ✓（✗ 不用真 DOM ✗）
		const field = { value: '' };
		const secs = new Function('$', 'return (' + secsSrc + ')')(() => field);
		const run = (v) => { field.value = v; const got = secs(); return `${got}（回写 ${field.value}）`; };
		const s0 = run(0), s500 = run(500), s12 = run(12), sabc = run('abc'), sfrac = run(3.7);
		secsSample = `0 ⇒ ${s0}；500 ⇒ ${s500}；12 ⇒ ${s12}；abc ⇒ ${sabc}；3.7 ⇒ ${sfrac}`;
		secsOk = s0 === '3（回写 3）' && s500 === '99（回写 99）' && s12 === '12（回写 12）'
			&& sabc === '3（回写 3）' && sfrac === '4（回写 4）'
			&& slHtml.indexOf('var sec = secs();') >= 0;      // ★ 起播真用上它 ✓（✗ 定义了不用 ✗）
	} catch (e) { secsSample = 'secs() 跑不起来：' + e.message; }
}
console.log('⑱ 幻灯片按钮：只有符号 = %s；title 三条齐 = %s；点 ▶ 变 ■/停止 = %s；'
	+ '没有「暂停」/⏸ = %s；顺序 = %s（应为 prev,play,next = ← ▶ → ✓）；'
	+ '文件名 ≤ 40 字 = %s（%s）',
	noWords, hasTitles, stopOk, noPause, btnOrder, clipOk, clipSample);
console.log('   ⑱ 续：顶部两列 = %s；左列两行（文件名在第 2 行）= %s；'
	+ '按钮行里 prev/play/next/秒数/页码 齐全 = %s；提示在右列且可折行 = %s；'
	+ '每 N 秒只用数字 = %s；3..99 真的钳住 = %s（%s）；「2 / 3」不折行 = %s',
	twoCols, leftTwoRows, row1All, hintInRight, numbersOnly, secsOk, secsSample, posNowrap);
console.log('   ⑱ 再续：头部「不会被压扁」 = %s（窄窗口/矮窗口时不许被切 ✓）；'
	+ '该缩的是内容区 = %s（flex:1 1 auto ＋ min-height:0 ✓）；文件名**带扩展名** = %s（%s）；'
	+ '右栏清单上方有【播放差异】 = %s；两处记号**不同** = %s'
	+ '（合并视图 ›▶ 重放‹ 用字符 ✓ / 幻灯片 ›步进‹ 用 CSS 画 ✓）；'
	+ '**图形与竖线等高** = %s（%s）',
	!headHazard, wrapShrinks, titleOk, titleSample, replayInRight, glyphsDiffer, heightsEqual, stepSample);
if (!noWords || !hasTitles || !stopOk || !noPause || !orderOk || !clipOk
	|| !twoCols || !leftTwoRows || !row1All || !hintInRight
	|| !numbersOnly || !secsOk || !posNowrap || headHazard || !wrapShrinks || !titleOk
	|| !replayInRight || !glyphsDiffer || !heightsEqual || !barIsBorder || !triIsClip || !stepCentered) {
	fail('幻灯片顶部没按用户要求（两列：左列两行 = 按钮行＋文件名，右列一行 = 快捷键提示）'
		+ '，或按钮/秒数/文件名那几条没守住，或头部会被压扁（overflow:hidden 的孩子自动最小高度为 0 ⇒ 得 flex:0 0 auto）'
		+ '，或文件名没带扩展名（同名的 .md/.svg/.png 有三个 ⇒ 分不出是哪个）'
		+ '，或两个播放按钮的符号不区分（合并视图该是 ▶ 重放 / 幻灯片该是 ⏭ 步进）');
}

// ⑲ ★★ **CSS 注释里不许写反引号** ✗ —— 2026-10-08 一天踩了**三次** ✓，值得一条机器守 ✓：
//   `.left` 那段 CSS 在 `const CSS = \`…\`` **模板字符串**里 ✓ ⇒ 注释里一个反引号就把模板**截断** ✗
//   ⇒ `SyntaxError: Unexpected identifier 'sticky'` ✓（`node --check` 当场就报 ✓）；
//   更阴的是**幻灯片那份 CSS** ✓ —— 它在 `slideshowHtml()` 返回的模板里 ✓ ⇒ 语法**过得去** ✗，
//   但反引号里的字变成了 `${…}` **表达式** ✓ ⇒ 运行时 `TypeError: cspCSS.wrap is not a function` ✗✗
//   （✗ `node --check` 抓不到这一种 ✗ —— 必须**真的调一次** `slideshowHtml()` ✓）。
//   ⇒ 这条同时做两件事 ✓：① 语法检查 extension.js 本体 ✓；② **真调**两个 HTML 生成函数 ✓。
let n19 = 0, bad19 = 0;
const extSrc = fs.readFileSync(path.join(EXTDIR, 'extension.js'), 'utf8');
try { new Function(extSrc); n19++; }                    // ① 本体语法（截断型 ⇒ 这里就报 ✓）
catch (e) { bad19++; console.log('   ✗ extension.js 本体语法错：%s', e.message); }
try {                                                    // ② 真渲染两种界面（运行期 substitutions ✓）
	html({ cspSource: '' }, fs.readFileSync(md, 'utf8'), readPage(md).svg, '', '', '', 'N');
	slideshowHtml({ cspSource: '' }, 'N', 1);
	n19++;
} catch (e) {
	bad19++;
	console.log('   ✗ 渲染 HTML 时抛异常（多半是 CSS 注释里写了反引号 ⇒ 变成了 JS 表达式）：%s', e.message);
}
const cssRegion = /const CSS = `[\s\S]*?`;/.exec(extSrc);
const cssTicks = cssRegion ? (cssRegion[0].match(/`/g) || []).length : -1;
console.log('⑲ 模板字符串体检：extension.js 语法 = %s；两种界面能渲染 = %s；'
	+ 'CSS 模板里的反引号 = %d（应为 2 ✓ = 开头结尾各一个 ✓）',
	n19 === 2 ? 'OK' : 'BAD', n19 === 2 ? 'OK' : 'BAD', cssTicks);
if (bad19 || cssTicks !== 2) fail('CSS 模板字符串被反引号截断（注释里别写反引号）');

console.log(bad ? '\n✗ 有 %d 项不对' : '\n✓ 十九项都过', bad || '');
process.exit(bad ? 1 : 0);
