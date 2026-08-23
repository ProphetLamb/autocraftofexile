import {
  app,
  BrowserWindow,
  ipcMain,
  nativeImage,
  Tray,
  webContents,
} from "electron";
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

if (!app.requestSingleInstanceLock()) {
  app.quit();
}

const config = new Store<Config>();
const port = process.env.PORT || "5173";
const dev = !app.isPackaged;
let init: CreateWindowResult;
let settings: BrowserWindow | undefined;
let tray: Tray;

contextMenu({
  showLookUpSelection: false,
  showSearchWithGoogle: false,
  showCopyImage: false,
});

function createTray() {
  if (tray) {
    return;
  }
  const icon = nativeImage.createFromDataURL(
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAACTSURBVHgBpZKBCYAgEEV/TeAIjuIIbdQIuUGt0CS1gW1iZ2jIVaTnhw+Cvs8/OYDJA4Y8kR3ZR2/kmazxJbpUEfQ/Dm/UG7wVwHkjlQdMFfDdJMFaACebnjJGyDWgcnZu1/lrCrl6NCoEHJBrDwEr5NrT6ko/UV8xdLAC2N49mlc5CylpYh8wCwqrvbBGLoKGvz8Bfq0QPWEUo/EAAAAASUVORK5CYII=",
  );
  tray = new Tray(icon);
  tray.setToolTip("AutoCraftOfExile Settings");
  tray.on("click", () => {
    createSettingsWindow().show();
  });
}

function createSettingsWindow() {
  if (settings) {
    return settings;
  }
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
  return settings;
}

function createMainWindow() {
  if (init) {
    return init;
  }
  createTray();

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
  return init;
}

app.once("ready", createMainWindow);
app.on("activate", createMainWindow);
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
  }
});
