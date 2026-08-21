// Custom entry point, used instead of `expo/AppEntry.js`.
//
// AppEntry.js locates the app root via a relative path (`../../App`)
// assuming it lives at <project>/node_modules/expo/AppEntry.js. In this
// npm workspace, `expo` is hoisted to the repo root's node_modules
// (nothing else in the workspace pins a conflicting version, so nothing
// forces a nested copy here — see metro.config.js) — so that relative
// path no longer points at this app's own App.js. A local entry point
// with a genuinely relative `./App` import, plus a normal bare-specifier
// import of `expo`, sidesteps the assumption entirely. This is Expo's
// own documented fix for monorepos.
import { registerRootComponent } from 'expo';

import App from './App';

registerRootComponent(App);
