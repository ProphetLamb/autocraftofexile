import { BrowserWindow, globalShortcut } from "electron";
import { OverlayController } from "electron-overlay-window";
import type Store from "electron-store";
import { defaultConfig, type Config } from "./config.ts";

export interface MakeInteractiveParam {
  dev: boolean;
  config: Store<Config>;
}
export interface MakeInteractiveResult {
  get(): boolean;
  set(newValue: boolean): void;
  updateHotkey(): void;
}

export function makeInteractive(
  window: BrowserWindow,
  param: MakeInteractiveParam,
): MakeInteractiveResult {
  let isInteractable = false;
  let toggleKey = "";
  function set(newValue: boolean) {
    if (!newValue) {
      isInteractable = false;
      OverlayController.focusTarget();
      window.webContents.send("focus-change", false);
    } else {
      isInteractable = true;
      OverlayController.activateOverlay();
      window.webContents.send("focus-change", true);
    }
  }

  function updateHotkey() {
    if (toggleKey) {
      globalShortcut.unregister(toggleKey);
    }
    toggleKey = param.config.get("toggleKey", defaultConfig.toggleKey);
    if (toggleKey) {
      globalShortcut.register(toggleKey, () => set(!isInteractable));
    }
  }

  window.on("blur", () => {
    isInteractable = false;
    window.webContents.send("focus-change", false);
  });

  updateHotkey();

  return {
    get() {
      return isInteractable;
    },
    set,
    updateHotkey,
  };
}
