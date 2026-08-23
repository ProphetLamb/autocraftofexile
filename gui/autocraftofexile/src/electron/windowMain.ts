import { BrowserWindow } from "electron";
import {
  OverlayController,
  OVERLAY_WINDOW_OPTS,
} from "electron-overlay-window";
import path from "path";
import type Store from "electron-store";
import { type Config } from "./config.ts";
import {
  makeInteractive,
  type MakeInteractiveParam,
  type MakeInteractiveResult,
} from "./interactivity.ts";

export interface CreateWindowParam extends MakeInteractiveParam {
  dev: boolean;
  config: Store<Config>;
}

export interface CreateWindowResult {
  window: BrowserWindow;
  interativity: MakeInteractiveResult;
}

export function createWindow(config: CreateWindowParam): CreateWindowResult {
  const window = new BrowserWindow({
    resizable: false,
    frame: false,
    transparent: true,
    webPreferences: getWebPreferences(config.dev),
    ...OVERLAY_WINDOW_OPTS,
  });

  if (!config.dev) {
    window.setSkipTaskbar(true);
  }
  window.removeMenu();
  const interativity = makeInteractive(window, config);
  OverlayController.attachByTitle(window, "Untitled - Notepad");

  return { window, interativity };
}

export function getWebPreferences(
  dev: boolean,
): Electron.WebPreferences {
  return {
    contextIsolation: true,
    nodeIntegration: true,
    spellcheck: false,
    devTools: dev,
    preload: path.join(import.meta.dirname, "../preload/main.mts"),
  };
}

export function loadVite(window: BrowserWindow, port: string, path?: string) {
  window.loadURL(`http://localhost:${port}${path || ""}`).catch((e) => {
    console.log("Error loading URL, retrying", e);
    setTimeout(() => {
      loadVite(window, port);
    }, 200);
  });
}
