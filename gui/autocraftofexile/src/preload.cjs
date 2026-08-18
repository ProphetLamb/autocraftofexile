/* eslint-disable @typescript-eslint/no-require-imports */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  send: (channel, ...args) => {
    ipcRenderer.send(channel, ...args);
  },

  invoke: (channel, ...args) => {
    return ipcRenderer.invoke(channel, ...args);
  },

  receive: (channel, listener) => {
    ipcRenderer.on(channel, (_event, ...args) => listener(...args));
  }
});