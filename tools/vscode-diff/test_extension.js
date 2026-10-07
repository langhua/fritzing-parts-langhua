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
const { listVersions, newestDiffMd, mdToHtml, PAD_RE_SRC, dirs, pageList, readPage,
        CSS, slideshowHtml, html, patRe } = ext._pure;

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
	const svgPath = md.replace(/\.md$/, '.svg');
	if (!fs.existsSync(svgPath)) fail('旁边没有 svg（先跑一次 diff_revs.py）');
	else {
		const svg = fs.readFileSync(svgPath, 'utf8');
		const ids = new Set((svg.match(/<g id="pd-[^"]+"/g) || [])
			.map((s) => /id="([^"]+)"/.exec(s)[1]));
		const RE = new RegExp(PAD_RE_SRC, 'g');           // ★ 用扩展里**那一条**正则（不是另写一条 ✗）
		const textHtml = h.replace(/<[^>]+>/g, ' ');     // ≈ 浏览器里的 textContent ✓
		const seen = new Set();
		let hit = 0, miss = 0, mm;
		while ((mm = RE.exec(textHtml))) {
			if (seen.has(mm[1])) continue;
			seen.add(mm[1]);
			if (ids.has('pd-' + mm[1])) hit++;
			else { miss++; console.log('   ✗ 文字里的 %s 在 svg 里没有对应组', mm[1]); }
		}
		console.log('④ 点行 ⇒ 高亮：svg 里 %d 组；文字里认出 %d 个脚、对不上 %d 个',
			ids.size, hit, miss);
		if (!ids.size || !hit || miss) fail('点行与高亮组的对应关系不成立');
	}
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

console.log(bad ? '\n✗ 有 %d 项不对' : '\n✓ 九项都过', bad || '');
process.exit(bad ? 1 : 0);
