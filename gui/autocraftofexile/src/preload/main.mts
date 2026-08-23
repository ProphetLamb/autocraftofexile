import { contextBridge, ipcRenderer } from 'electron';
import type { RendererElectron } from '../electron/ipc'

contextBridge.exposeInMainWorld('electron', {
  send: (channel, ...args) => {
    ipcRenderer.send(channel, ...args);
  },

  invoke: (channel, ...args) => {
    return ipcRenderer.invoke(channel, ...args);
  },

  receive: (channel, listener) => {
    // @ts-expect-error ..args genereic cast
    ipcRenderer.on(channel, (_event, ...args) => listener(...args));
  }
} as RendererElectron);