/**
 * Copy the skill scripts from the repo's skills/ tree into <package>/skills so
 * the published npm package is self-contained. runSkill() resolves scripts at
 * <package>/skills/iflytek-<name>/scripts (override the root with
 * IFLY_SKILLS_ROOT for a local checkout).
 */
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const srcSkills = path.join(repoRoot, 'skills');
const destSkills = path.resolve(__dirname, '..', 'skills');

function copyDir(from, to) {
	fs.mkdirSync(to, { recursive: true });
	for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
		const s = path.join(from, entry.name);
		const d = path.join(to, entry.name);
		if (entry.isDirectory()) copyDir(s, d);
		else fs.copyFileSync(s, d);
	}
}

let count = 0;
for (const name of fs.readdirSync(srcSkills)) {
	if (!name.startsWith('iflytek-')) continue;
	const scripts = path.join(srcSkills, name, 'scripts');
	if (fs.existsSync(scripts)) {
		copyDir(scripts, path.join(destSkills, name, 'scripts'));
		count++;
	}
}
console.log(`bundled ${count} skill script folders into ${destSkills}`);
