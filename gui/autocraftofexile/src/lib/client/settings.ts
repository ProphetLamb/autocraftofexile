import { writable } from "svelte/store";
import { defaultConfig, type Config } from "$lib/../electron/config";

type Settings = {
  isInteractive: boolean;
  config: Config;
};

export const settings = writable<Settings>({
  isInteractive: false,
  config: defaultConfig,
});

export async function initSettings() {
  const config = await window.electron.invoke("get-config");
  if (config) {
    settings.update((s) => {
      return { ...s, config: config };
    });
  }
  return settings;
};

window.electron.receive("focus-change", (focussed) => {
  settings.update((s) => {
    return { ...s, isInteractive: focussed };
  });
});

window.electron.receive("config-change", (config) => {
  settings.update((s) => {
    return { ...s, config };
  });
});
