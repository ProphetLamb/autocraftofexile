import type {
  IpcMain as BaseIpcMain,
  IpcMainEvent as BaseIpcMainEvent,
  WebContents as BaseWebContents,
  IpcMainInvokeEvent,
} from "electron";
import type { Config } from "./config";

/**
 * Channels the renderer may initiate with ipcRenderer.send(...)
 * Each key maps to the argument tuple the renderer will send.
 */
export interface RendererSendChannels {
  "to-main": { args: [count: number]; return: never };
  hide: { args: []; return: never };
  show: { args: []; return: never };
  "set-config": {
    args: [config: Partial<Config>];
    return: never;
  };
}

/**
 * Channels the renderer may initiate with ipcRenderer.invoke(...)
 * Each key maps to an object with args tuple and return type.
 */
export interface RendererInvokeChannels {
  "get-user": { args: [id: number]; return: { id: number; name: string } };
  "list-recipes": { args: []; return: { recipes: string[] } };
  "get-config": { args: []; return: Config };
  "has-focus": { args: []; return: boolean };
}

/**
 * Channels the main process may send to renderer via webContents.send(...)
 * Each key maps to the argument tuple the renderer will receive.
 */
export interface MainToRendererChannels {
  "from-main": [data: string];
  "focus-change": [focussed: boolean];
  "config-change": [config: Config];
}

/* Listener arg resolver for ipcMain.on */
export type IpcMainListenerArgs<
  K extends keyof RendererSendChannels | keyof RendererInvokeChannels,
> = K extends keyof RendererSendChannels
  ? RendererSendChannels[K]["args"]
  : K extends keyof RendererInvokeChannels
    ? RendererInvokeChannels[K]["args"]
    : never;

export interface IpcMainEvent<
  K extends keyof RendererSendChannels | keyof RendererInvokeChannels =
    keyof RendererSendChannels | keyof RendererInvokeChannels,
> extends BaseIpcMainEvent {
  returnValue: K extends keyof RendererSendChannels
    ? RendererSendChannels[K]["return"]
    : never;
  reply<L extends keyof MainToRendererChannels>(
    channel: L,
    ...args: MainToRendererChannels[L]
  ): void;
  reply<L extends keyof MainToRendererChannels>(
    channel: L,
    ...args: MainToRendererChannels[L]
  ): void;
}

/**
 * Strongly-typed IpcMain: only allow .on for channels the renderer may initiate.
 */
export interface IpcMain extends BaseIpcMain {
  on<K extends keyof RendererSendChannels>(
    channel: K,
    listener: (event: IpcMainEvent<K>, ...args: IpcMainListenerArgs<K>) => void,
  ): this;
  handle<K extends keyof RendererInvokeChannels>(
    channel: K,
    handler: (
      event: IpcMainInvokeEvent,
      ...args: IpcMainListenerArgs<K>
    ) =>
      | Promise<RendererInvokeChannels[K]["return"]>
      | RendererInvokeChannels[K]["return"],
  ): void;
}

export interface WebContents extends BaseWebContents {
  send<L extends keyof MainToRendererChannels>(
    channel: L,
    ...args: MainToRendererChannels[L]
  ): void;
}

export type RendererElectron = {
  send<K extends keyof RendererSendChannels>(
    channel: K,
    ...args: RendererSendChannels[K]["args"]
  ): void;
  sendSync<K extends keyof RendererSendChannels>(
    channel: K,
    ...args: RendererSendChannels[K]["args"]
  ): RendererSendChannels[K]["return"];
  invoke<K extends keyof RendererInvokeChannels>(
    channel: K,
    ...args: RendererInvokeChannels[K]["args"]
  ): Promise<RendererInvokeChannels[K]["return"] | undefined>;
  receive<K extends keyof MainToRendererChannels>(
    channel: K,
    listener: (...args: MainToRendererChannels[K]) => void,
  ): void;
};
