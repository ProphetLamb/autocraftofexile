/* eslint-disable @typescript-eslint/no-unused-vars */
/* eslint-disable @typescript-eslint/no-require-imports */
const windowStateManager = require('electron-window-state');
const { app, BrowserWindow, ipcMain, Menu } = require('electron');
const { default: contextMenu } = require('electron-context-menu');
const { default: serve } = require('electron-serve');
const path = require('path');
const { electron } = require('process');
/** @typedef {import('./electronIpc').IpcMain} IpcMain */
/** @typedef {import('./electronIpc').WebContents} WebContents */

try {
	require('electron-reloader')(module);
} catch (e) {
	console.error(e);
}

const serveURL = serve({ directory: '.' });
const port = process.env.PORT || 5173;
const dev = !app.isPackaged;
/** @type {BrowserWindow} */
let mainWindow;

function createWindow() {
	const windowState = windowStateManager({
		defaultWidth: 800,
		defaultHeight: 600
	});

	const mainWindow = new BrowserWindow({
		resizable: false,
		frame: false,
		transparent: true,
		fullscreen: true,
		webPreferences: {
			enableRemoteModule: true,
			contextIsolation: true,
			nodeIntegration: true,
			spellcheck: false,
			devTools: dev,
			preload: path.join(__dirname, 'preload.cjs')
		},
		x: windowState.x,
		y: windowState.y,
		width: windowState.width,
		height: windowState.height
	});

	windowState.manage(mainWindow);
	if (!dev) {
		mainWindow.setSkipTaskbar(true);
	}
	mainWindow.removeMenu();

	mainWindow.once('ready-to-show', () => {
		if (dev) {
			mainWindow.show();
			mainWindow.focus();
		}
	});

	mainWindow.on('close', () => {
		windowState.saveState(mainWindow);
	});

	return mainWindow;
}

contextMenu({
	showLookUpSelection: false,
	showSearchWithGoogle: false,
	showCopyImage: false,
	prepend: (defaultActions, params, browserWindow) => [
		{
			label: 'Make App 💻'
		}
	]
});

function loadVite(port) {
	mainWindow.loadURL(`http://localhost:${port}`).catch((e) => {
		console.log('Error loading URL, retrying', e);
		setTimeout(() => {
			loadVite(port);
		}, 200);
	});
}

function createMainWindow() {
	mainWindow = createWindow();
	mainWindow.once('close', () => {
		mainWindow = null;
	});

	if (dev) loadVite(port);
	else serveURL(mainWindow);
}

app.once('ready', createMainWindow);
app.on('activate', () => {
	if (!mainWindow) {
		createMainWindow();
	}
});
app.on('window-all-closed', () => {
	if (process.platform !== 'darwin') app.quit();
});

/** @type {IpcMain} */
const ipc = ipcMain;
/** @type {() => WebContents} */
const webContents = () => mainWindow.webContents;

ipc.on('to-main', (event, count) => {
	event.reply('from-main', `next count is ${count + 1}`);
});
ipc.handle('get-user', (event, name) => {
	return { id: 12, name: 'Christian' };
});
ipc.on('hide', (event) => {
	mainWindow.hide();
});
ipc.on('show', (event) => {
	mainWindow.show();
});
