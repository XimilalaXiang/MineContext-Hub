const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, shell, dialog } = require('electron');
const path = require('path');
const Store = require('electron-store');
const { SyncEngine } = require('./sync-engine');

const isDev = process.env.NODE_ENV === 'development';
const store = new Store({
  defaults: {
    hub_url: 'https://context.ximilala.com',
    hub_token: '',
    db_path: '',
    sync_interval_seconds: 60,
    batch_size: 100,
    sync_types: ['vaults', 'todo', 'activity', 'tips', 'conversations', 'messages', 'monitoring_data_stats'],
    auto_start: false,
    minimize_to_tray: true,
    language: 'zh',
  },
});

let mainWindow = null;
let tray = null;
let syncEngine = null;

function getIconPath() {
  if (isDev) {
    return path.join(__dirname, '..', 'public', 'icon.png');
  }
  return path.join(process.resourcesPath, 'app', 'dist', 'icon.png');
}

function createTrayIcon() {
  const size = 16;
  const canvas = nativeImage.createFromBuffer(
    Buffer.alloc(size * size * 4, 0),
    { width: size, height: size }
  );
  return canvas;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 680,
    minWidth: 800,
    minHeight: 600,
    title: 'MineContext Hub',
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.on('close', (e) => {
    if (store.get('minimize_to_tray') && !app.isQuiting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });
}

function createTray() {
  let trayIcon;
  try {
    const iconPath = getIconPath();
    trayIcon = nativeImage.createFromPath(iconPath);
    if (trayIcon.isEmpty()) throw new Error('empty');
  } catch {
    trayIcon = createTrayIcon();
  }

  tray = new Tray(trayIcon.resize({ width: 16, height: 16 }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'MineContext Hub',
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '显示主窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: '立即同步',
      click: () => {
        if (syncEngine) syncEngine.syncOnce();
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuiting = true;
        if (syncEngine) syncEngine.stop();
        app.quit();
      },
    },
  ]);

  tray.setToolTip('MineContext Hub - 数据同步客户端');
  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function initSyncEngine() {
  syncEngine = new SyncEngine(store);

  syncEngine.on('status', (status) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('sync:status', status);
    }
  });

  syncEngine.on('log', (entry) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('sync:log', entry);
    }
  });

  syncEngine.on('stats', (stats) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('sync:stats', stats);
    }
  });

  if (store.get('hub_token')) {
    syncEngine.start();
  }
}

function setupIPC() {
  ipcMain.handle('config:get', () => store.store);

  ipcMain.handle('config:set', (_, key, value) => {
    store.set(key, value);
    if (['hub_url', 'hub_token', 'db_path', 'sync_interval_seconds', 'batch_size', 'sync_types'].includes(key)) {
      if (syncEngine) syncEngine.restart();
    }
    return true;
  });

  ipcMain.handle('config:setAll', (_, config) => {
    for (const [key, value] of Object.entries(config)) {
      store.set(key, value);
    }
    if (syncEngine) syncEngine.restart();
    return true;
  });

  ipcMain.handle('sync:start', () => {
    if (syncEngine) syncEngine.start();
  });

  ipcMain.handle('sync:stop', () => {
    if (syncEngine) syncEngine.stop();
  });

  ipcMain.handle('sync:once', () => {
    if (syncEngine) syncEngine.syncOnce();
  });

  ipcMain.handle('sync:getStatus', () => {
    if (syncEngine) return syncEngine.getStatus();
    return null;
  });

  ipcMain.handle('sync:getLogs', () => {
    if (syncEngine) return syncEngine.getLogs();
    return [];
  });

  ipcMain.handle('sync:getStats', () => {
    if (syncEngine) return syncEngine.getStats();
    return null;
  });

  ipcMain.handle('app:selectFile', async (_, options) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile'],
      filters: options?.filters || [{ name: 'SQLite DB', extensions: ['db', 'sqlite'] }],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  ipcMain.handle('window:minimize', () => mainWindow?.minimize());
  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize();
    else mainWindow?.maximize();
  });
  ipcMain.handle('window:close', () => mainWindow?.close());
  ipcMain.handle('window:isMaximized', () => mainWindow?.isMaximized() ?? false);

  ipcMain.handle('app:openExternal', (_, url) => shell.openExternal(url));
  ipcMain.handle('app:getVersion', () => app.getVersion());

  ipcMain.handle('autostart:get', () => {
    return app.getLoginItemSettings().openAtLogin;
  });

  ipcMain.handle('autostart:set', (_, enable) => {
    app.setLoginItemSettings({ openAtLogin: enable });
    store.set('auto_start', enable);
  });
}

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    setupIPC();
    createWindow();
    createTray();
    initSyncEngine();
  });

  app.on('window-all-closed', () => {
    // keep running in tray
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });

  app.on('before-quit', () => {
    app.isQuiting = true;
    if (syncEngine) syncEngine.stop();
  });
}
