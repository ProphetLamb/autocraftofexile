---
paths:
  - 'gui/electron-autocraftofexile/src/main/**/*.ts'
  - 'gui/electron-autocraftofexile/src/preload/**/*.ts'
  - 'gui/electron-autocraftofexile/src/renderer/**/*.{ts,tsx}'
---

# Electron Conventions

stem-magic is split into three processes. These rules enforce the Electron security model and the process boundary.

## Process boundaries

| Process  | Directory      | Runtime        | Allowed imports                                                      |
| -------- | -------------- | -------------- | -------------------------------------------------------------------- |
| Main     | `src/main`     | Node           | Node built-ins, `electron`, `src/shared`                             |
| Preload  | `src/preload`  | Node (sandbox) | `electron` (`contextBridge`, `ipcRenderer`), `src/shared` types only |
| Renderer | `src/renderer` | Browser        | React, DOM APIs, `window.api`, `src/shared` types only               |

**Hard rules:**

- `src/main` MUST NOT import from `src/renderer`.
- `src/renderer` MUST NOT import from `src/main`.
- `src/preload` MUST NOT import any runtime code from renderer — only shared types.
- Shared code (plain types, constants) goes in `src/shared/`.

## Security defaults

Every `BrowserWindow` uses:

- `contextIsolation: true`
- `nodeIntegration: false`
- `sandbox: true`
- `webSecurity: true`

**Never** change these. If you think you need to, ask first — there is almost always a better approach.

## IPC pattern

All renderer → main communication goes through a typed `contextBridge` API defined in `src/preload/index.ts`. The renderer calls `window.api.<method>()`; the main process registers matching `ipcMain.handle(...)` handlers.

To add a new IPC method:

1. Add a handler in `src/main/index.ts`: `ipcMain.handle('my-method', (_event, arg: MyArg) => { ... })`
2. Add the exposed method in `src/preload/index.ts`:
   ```ts
   const api = {
     myMethod: (arg: MyArg): Promise<MyResult> => ipcRenderer.invoke('my-method', arg),
   } as const;
   ```
3. The `Api` type is auto-exported from preload; `src/preload/index.d.ts` augments `window.api`.
4. Call it from the renderer: `await window.api.myMethod(arg)`.

**Validate all inputs at the main-process boundary.** Treat IPC args as untrusted — in a full app, validate with Zod or similar before touching the filesystem or shelling out.

## Window lifecycle

- On macOS, keep the app running when all windows close — handled in `src/main/index.ts` by gating `app.quit()` on `process.platform !== 'darwin'`.
- Re-create a window on `app.on('activate')` if none exist (standard macOS behavior).

## Filesystem & native APIs

Never import `fs`, `child_process`, `path`, `os`, or other Node built-ins from the renderer. If the renderer needs filesystem access, add an IPC method in main. The renderer is sandboxed — this is intentional.

## Code signing & notarization

The scaffold does **not** sign or notarize builds. Distributable `.dmg` builds require:

- Apple Developer ID Application certificate
- `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID` env vars
- `afterSign` notarization hook in `electron-builder.yml`

Mark this as TODO when you first need to ship builds.

