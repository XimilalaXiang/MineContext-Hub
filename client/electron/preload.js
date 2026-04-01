const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    set: (key, value) => ipcRenderer.invoke('config:set', key, value),
    setAll: (config) => ipcRenderer.invoke('config:setAll', config),
  },
  sync: {
    start: () => ipcRenderer.invoke('sync:start'),
    stop: () => ipcRenderer.invoke('sync:stop'),
    once: () => ipcRenderer.invoke('sync:once'),
    getStatus: () => ipcRenderer.invoke('sync:getStatus'),
    getLogs: () => ipcRenderer.invoke('sync:getLogs'),
    getStats: () => ipcRenderer.invoke('sync:getStats'),
    onStatus: (callback) => {
      const handler = (_, data) => callback(data);
      ipcRenderer.on('sync:status', handler);
      return () => ipcRenderer.removeListener('sync:status', handler);
    },
    onLog: (callback) => {
      const handler = (_, data) => callback(data);
      ipcRenderer.on('sync:log', handler);
      return () => ipcRenderer.removeListener('sync:log', handler);
    },
    onStats: (callback) => {
      const handler = (_, data) => callback(data);
      ipcRenderer.on('sync:stats', handler);
      return () => ipcRenderer.removeListener('sync:stats', handler);
    },
  },
  app: {
    selectFile: (options) => ipcRenderer.invoke('app:selectFile', options),
    openExternal: (url) => ipcRenderer.invoke('app:openExternal', url),
    getVersion: () => ipcRenderer.invoke('app:getVersion'),
  },
  autostart: {
    get: () => ipcRenderer.invoke('autostart:get'),
    set: (enable) => ipcRenderer.invoke('autostart:set', enable),
  },
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:isMaximized'),
  },
});
