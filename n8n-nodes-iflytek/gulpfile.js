const { src, dest } = require('gulp');

// Copy node SVG icons into the compiled dist tree (tsc emits only JS).
function buildIcons() {
	return src('nodes/**/*.svg').pipe(dest('dist/nodes'));
}

exports['build:icons'] = buildIcons;
exports.default = buildIcons;
