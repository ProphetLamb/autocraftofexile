import { BrowserWindow, globalShortcut } from "electron";
import {
  OverlayController,
  OVERLAY_WINDOW_OPTS,
} from "electron-overlay-window";
import path from "path";

type CreateWindowConfig = { dev: boolean } & MakeInteractiveConfig;

export function createWindow(config: CreateWindowConfig) {
  const window = new BrowserWindow({
    resizable: false,
    frame: false,
    transparent: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: true,
      spellcheck: false,
      devTools: config.dev,
      preload: path.join(import.meta.dirname, "../preload/main.mts"),
    },
    ...OVERLAY_WINDOW_OPTS,
  });

  if (!config.dev) {
    window.setSkipTaskbar(true);
  }
  window.removeMenu();
  makeInteractive(window, config);
  OverlayController.attachByTitle(window, "Untitled - Notepad");

  return window;
}

type MakeInteractiveConfig = { toggleMouseKey: string; toggleShowKey: string };

function makeInteractive(window: BrowserWindow, config: MakeInteractiveConfig) {
  let isInteractable = false;

  function toggleOverlayState() {
    if (isInteractable) {
      isInteractable = false;
      OverlayController.focusTarget();
      window.webContents.send("focus-change", false);
    } else {
      isInteractable = true;
      OverlayController.activateOverlay();
      window.webContents.send("focus-change", true);
    }
  }

  window.on("blur", () => {
    isInteractable = false;
    window.webContents.send("focus-change", false);
  });

  globalShortcut.register(config.toggleMouseKey, toggleOverlayState);

  globalShortcut.register(config.toggleShowKey, () => {
    window.webContents.send("visibility-change", false);
  });
}

export function loadVite(window: BrowserWindow, port: string) {
  window.loadURL(`http://localhost:${port}`).catch((e) => {
    console.log("Error loading URL, retrying", e);
    setTimeout(() => {
      loadVite(window, port);
    }, 200);
  });
}
