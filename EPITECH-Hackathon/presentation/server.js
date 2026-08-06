#!/usr/bin/env node
/*
 * Minimal static file server for the reveal.js deck.
 * Zero dependencies: uses only Node's standard library.
 * Run with `npm start`, then open http://localhost:8000
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8000;
const ROOT = __dirname;

const MIME = {
	'.html': 'text/html; charset=utf-8',
	'.js': 'text/javascript; charset=utf-8',
	'.mjs': 'text/javascript; charset=utf-8',
	'.css': 'text/css; charset=utf-8',
	'.json': 'application/json; charset=utf-8',
	'.svg': 'image/svg+xml',
	'.png': 'image/png',
	'.jpg': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.gif': 'image/gif',
	'.woff': 'font/woff',
	'.woff2': 'font/woff2',
	'.ttf': 'font/ttf',
	'.map': 'application/json; charset=utf-8',
	'.html.md': 'text/markdown; charset=utf-8',
};

const server = http.createServer((req, res) => {
	let urlPath = decodeURIComponent(req.url.split('?')[0]);
	if (urlPath === '/') urlPath = '/index.html';

	// resolve and prevent path traversal outside ROOT
	const filePath = path.join(ROOT, urlPath);
	if (!filePath.startsWith(ROOT)) {
		res.writeHead(403);
		res.end('403 Forbidden');
		return;
	}

	fs.stat(filePath, (err, stat) => {
		if (err || !stat.isFile()) {
			res.writeHead(404, { 'Content-Type': 'text/plain' });
			res.end('404 Not Found');
			return;
		}
		const ext = path.extname(filePath).toLowerCase();
		res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
		fs.createReadStream(filePath).pipe(res);
	});
});

server.listen(PORT, () => {
	console.log(`\n  In The Loop — deck served at  http://localhost:${PORT}\n`);
	console.log('  Press Ctrl+C to stop.\n');
});
