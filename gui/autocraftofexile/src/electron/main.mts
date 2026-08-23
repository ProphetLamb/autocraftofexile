import { app, BrowserWindow, ipcMain, webContents } from "electron";
import contextMenu from "electron-context-menu";
import serve from "electron-serve";
import { createWindow, loadVite } from "./windowMain.ts";
import { registerIpc } from "./ipcMain.ts";
import type { WebContents } from "./ipc.ts";

const serveURL = serve({ directory: "." });
const port = process.env.PORT || "5173";
const dev = !app.isPackaged;
let window: BrowserWindow;

contextMenu({
  showLookUpSelection: false,
  showSearchWithGoogle: false,
  showCopyImage: false,
});

function createMainWindow() {
  window = createWindow({
    dev,
    toggleMouseKey: "CmdOrCtrl + J",
    toggleShowKey: "CmdOrCtrl + K",
  });
  window.once("close", () => {
    window = null as unknown as BrowserWindow;
  });

  if (dev) loadVite(window, port);
  else serveURL(window);
}

app.once("ready", createMainWindow);
app.on("activate", () => {
  if (!window) {
    createMainWindow();
  }
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

registerIpc(
  ipcMain,
  () => window,
  () => webContents as unknown as WebContents,
);
