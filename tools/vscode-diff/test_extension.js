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
const path = require('path');

const stub = {
	workspace: { workspaceFolders: [] },
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
const { listVersions, newestDiffMd, mdToHtml, PAD_RE_SRC, dirs, pageList, readPage } = ext._pure;

let bad = 0;
const fail = (s, ...a) => { console.log('   ✗ ' + s, ...a); bad++; };

// ① 版本排序
const vers = listVersions(PIX);
const nums = vers.map((n) => Number(/-v(\d+)/.exec(n)[1]));
const sorted = nums.every((v, i) => i === 0 || nums[i - 1] <= v);
console.log('① 版本排序：共 %d 版，最后 4 个 = %s；单调递增 = %s',
	vers.length, vers.slice(-4).join(', '), sorted);
if (!vers.length || !sorted) fail('版本排序不对');

// ② 找最新清单
const md = newestDiffMd(PIX);
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
const pl = pageList(PIX);
const seq = pl.map((p) => {
	const m = /diff-v(\d+)[^-]*-v(\d+)/.exec(path.basename(p));
	return m ? [Number(m[1]), Number(m[2])] : [1e9, 1e9];
});
const inc = seq.every((v, i) => i === 0
	|| seq[i - 1][0] < v[0] || (seq[i - 1][0] === v[0] && seq[i - 1][1] <= v[1]));
const withSvg = pl.filter((p) => readPage(p).svg).length;
console.log('⑥ 幻灯片：%d 页；版本序递增 = %s；带图 %d 页（最后一页：%s）',
	pl.length, inc, withSvg, pl.length ? path.basename(pl[pl.length - 1]) : '—');
if (!pl.length || !inc || !withSvg) fail('幻灯片页面列表不对');

console.log(bad ? '\n✗ 有 %d 项不对' : '\n✓ 六项都过', bad || '');
process.exit(bad ? 1 : 0);
