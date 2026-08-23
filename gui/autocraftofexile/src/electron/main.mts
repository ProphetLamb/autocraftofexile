import { app, BrowserWindow, ipcMain, webContents } from "electron";
import contextMenu from "electron-context-menu";
import serve from "electron-serve";
import {
  createWindow,
  type CreateWindowResult,
  getWebPreferences,
  loadVite,
} from "./windowMain.ts";
import { registerIpc } from "./ipcMain.ts";
import type { WebContents } from "./ipc.ts";
import type { Config } from "./config.ts";
import Store from "electron-store";

const config = new Store<Config>();
const port = process.env.PORT || "5173";
const dev = !app.isPackaged;
let init: CreateWindowResult;
let settings: BrowserWindow | undefined;

contextMenu({
  showLookUpSelection: false,
  showSearchWithGoogle: false,
  showCopyImage: false,
});

function createSettingsWindow() {
  settings = new BrowserWindow({
    resizable: false,
    width: 400,
    height: 600,
    webPreferences: getWebPreferences(dev),
  });
  settings.removeMenu();
  settings.on("ready-to-show", () => settings?.show());
  settings.on("close", () => (settings = undefined));
  if (dev) loadVite(settings, port, "/settings");
  else serve({ directory: "./settings" })(settings);
}

function createMainWindow() {
  if (!config.get("toggleKey", "")) {
    createSettingsWindow();
  }

  init = createWindow({
    dev,
    config,
  });
  init.window.once("close", () => {
    init.window = null as unknown as BrowserWindow;
  });

  if (dev) loadVite(init.window, port);
  else serve({ directory: "." })(init.window);
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

registerIpc(ipcMain, {
  config,
  window() {
    return init.window;
  },
  interactivity() {
    return init.interativity;
  },
  webContents() {
    return webContents as unknown as WebContents;
  },
});