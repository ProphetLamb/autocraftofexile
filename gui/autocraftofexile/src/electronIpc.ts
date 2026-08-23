import type { IpcMain as BaseIpcMain, IpcMainEvent as BaseIpcMainEvent, WebContents as BaseWebContents, IpcMainInvokeEvent } from 'electron';

/**
 * Channels the renderer may initiate with ipcRenderer.send(...)
 * Each key maps to the argument tuple the renderer will send.
 */
export interface RendererSendChannels {
	'to-main': [count: number];
	'hide': [];
	'show': [];
}

/**
 * Channels the renderer may initiate with ipcRenderer.invoke(...)
 * Each key maps to an object with args tuple and return type.
 */
export interface RendererInvokeChannels {
	'get-user': { args: [id: number]; return: { id: number; name: string } };
	'list-recipes': { args: [recipeDirectory: string], return: { recipeFilePaths: string[] } }
}

/**
 * Channels the main process may send to renderer via webContents.send(...)
 * Each key maps to the argument tuple the renderer will receive.
 */
export interface MainToRendererChannels {
	'from-main': [data: string];
}

/* Listener arg resolver for ipcMain.on */
export type IpcMainListenerArgs<
	K extends keyof RendererSendChannels | keyof RendererInvokeChannels
> = K extends keyof RendererSendChannels
	? RendererSendChannels[K]
	: K extends keyof RendererInvokeChannels
	? RendererInvokeChannels[K]['args']
	: never;

export interface IpcMainEvent<
	K extends keyof RendererSendChannels | keyof RendererInvokeChannels = keyof RendererSendChannels | keyof RendererInvokeChannels
> extends BaseIpcMainEvent {
	returnValue: K extends keyof RendererInvokeChannels ? RendererInvokeChannels[K]['return'] : never;
	reply<L extends keyof MainToRendererChannels>(channel: L, ...args: MainToRendererChannels[L]): void;
	reply<L extends keyof MainToRendererChannels>(channel: L, ...args: MainToRendererChannels[L]): void;
}

/**
 * Strongly-typed IpcMain: only allow .on for channels the renderer may initiate.
 */
export interface IpcMain extends BaseIpcMain {
	on<K extends keyof RendererSendChannels>(
		channel: K,
		listener: (event: IpcMainEvent<K>, ...args: IpcMainListenerArgs<K>) => void
	): this;
	handle<K extends keyof RendererInvokeChannels>(
		channel: K,
		handler: (event: IpcMainInvokeEvent, ...args: IpcMainListenerArgs<K>) => Promise<RendererInvokeChannels[K]["return"]> | RendererInvokeChannels[K]["return"]
	): void;
}

export interface WebContents extends BaseWebContents {
	send<L extends keyof MainToRendererChannels>(channel: L, ...args: MainToRendererChannels[L]): void;
}

export type RendererElectron = {
	/**
	 * send: only channels the renderer is allowed to send (RendererSendChannels)
	 */
	send<K extends keyof RendererSendChannels>(channel: K, ...args: RendererSendChannels[K]): void;

	/**
	 * invoke: only channels the renderer is allowed to invoke (RendererInvokeChannels)
	 */
	invoke<K extends keyof RendererInvokeChannels>(
		channel: K,
		...args: RendererInvokeChannels[K]['args']
	): Promise<RendererInvokeChannels[K]['return'] | undefined>;

	/**
	 * receive: only channels the main process is allowed to send (MainToRendererChannels)
	 * listener receives the same argument tuple the main used when sending.
	 */
	receive<K extends keyof MainToRendererChannels>(
		channel: K,
		listener: (...args: MainToRendererChannels[K]) => void
	): void;
};
