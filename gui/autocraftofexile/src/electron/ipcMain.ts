import type { IpcMain as BaseIpcMain, BrowserWindow } from "electron";
import type { WebContents, IpcMain } from "./ipc.ts";

function withTracing(ipcMain: BaseIpcMain): IpcMain {
  // TODO replace on, handle etc to log trace
  return ipcMain as IpcMain;
}

export function registerIpc(
  ipc: BaseIpcMain,
  window: () => BrowserWindow,
  webContents: () => WebContents,
) {
  ipc = withTracing(ipc);
  ipc.on("to-main", (event, count) => {
    event.reply("from-main", `next count is ${count + 1}`);
  });
  ipc.on("hide", () => {
    window().hide();
  });
  ipc.on("show", () => {
    window().show();
  });
  ipc.handle("get-user", (_, id) => {
    return { id, name: "Christian" };
  });
  ipc.handle("list-recipes", () => {
    return {
      recipes: [],
    };
  });
}
