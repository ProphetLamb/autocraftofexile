import {
  screen,
  type IpcMain as BaseIpcMain,
  type BrowserWindow,
} from "electron";
import type { WebContents, IpcMain } from "./ipc.ts";
import type { MakeInteractiveResult } from "./interactivity.ts";
import type Store from "electron-store";
import { defaultConfig, readConfig, type Config } from "./config.ts";

function withTracing(ipcMain: BaseIpcMain): IpcMain {
  // TODO replace on, handle etc to log trace
  return ipcMain as IpcMain;
}

export function registerIpc(
  ipcMain: BaseIpcMain,
  options: {
    config: Store<Config>;
    window: () => BrowserWindow;
    interactivity: () => MakeInteractiveResult;
  },
) {
  const { config, interactivity, window } = options;
  const ipc = withTracing(ipcMain);
  ipc.on("to-main", (event, count) => {
    event.reply("from-main", `next count is ${count + 1}`);
  });
  ipc.on("hide", () => {
    interactivity().set(false);
  });
  ipc.on("show", () => {
    interactivity().set(true);
  });
  ipc.handle("get-user", (_, id) => {
    return { id, name: "Christian" };
  });
  ipc.handle("list-recipes", () => {
    return {
      recipes: [],
    };
  });
  ipc.handle("get-config", () => {
    return readConfig(config);
  });
  ipc.handle("has-focus", () => {
    return interactivity().get();
  });
  ipc.on("set-config", (_event, update) => {
    Object.entries(update).forEach(([key, value]) => {
      if (value !== undefined && Object.hasOwn(defaultConfig, key)) {
        config.set(key, value);
      }
    });
    interactivity().updateHotkey();
    window().webContents.send("config-change", readConfig(config));
  });
  ipc.handle("get-mouse-coords", () => {
    const absolute = screen.getCursorScreenPoint();
    const [x, y] = window().getPosition();
    return { x: absolute.x - x, y: absolute.y - y };
  });
}
