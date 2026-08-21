const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// Resolve the shared `inkmimic-core` workspace package (lives outside this
// app's own root, at <repo>/packages/inkmimic-core) — Metro doesn't watch
// or resolve outside its project root by default, unlike Vite.
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];
config.resolver.unstable_enableSymlinks = true;

// The web app pins React 18.3.1, this app pins React 19.1.0 (RN 0.81.4
// requires it) — a real version conflict across the workspace. Verified
// after `npm install` that npm's own dependency resolution already
// handles this correctly: it nested a private react@18.3.1 under the web
// app's own node_modules (since the hoisted root copy is 19.1.0, to
// satisfy mobile, and the two ranges don't overlap), so mobile safely
// resolves react from the hoisted root and web resolves its own nested
// copy — no extra resolver config needed here. (An earlier version of
// this file disabled hierarchical lookup to guard against exactly this,
// but that also broke Metro's ability to resolve expo's own hoisted
// internals — e.g. `expo/src/launch/registerRootComponent` from
// AppEntry.js — so it's been removed. See docs/adr/0006-mobile-tech-stack.md.)

module.exports = withNativeWind(config, { input: './global.css' });
