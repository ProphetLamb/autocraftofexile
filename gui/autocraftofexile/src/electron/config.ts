import type Store from "electron-store";

export interface Config {
  toggleKey: string;
}

export const defaultConfig = {
  toggleKey: "CmdOrCtrl + J"
} as Config

export function readConfig(config: Store<Config>) {
  return Object.fromEntries(
      Object.entries(defaultConfig).map(([key, defaultValue]) => {
        const value = config.get(key, undefined);
        if (value !== undefined) {
          return [key, value];
        }
        return [key, defaultValue];
      }),
    ) as Config;
}