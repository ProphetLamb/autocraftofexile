import {
  writable,
  type StartStopNotifier,
  type Subscriber,
  type Unsubscriber,
  type Updater,
  type Writable,
} from "svelte/store";
import { defaultConfig, type Config } from "$lib/../electron/config";
import { deepEqual } from "$lib";

type Settings = {
  isInteractive: boolean;
  config: Config;
};

const initial = {
  isInteractive: false,
  config: defaultConfig,
} as Settings;

function noop() {}

function createSettings(
  initial: Settings,
  start: StartStopNotifier<Settings> = noop,
): Writable<Settings> {
  const inner = writable<Settings>(initial, start);
  let timeout: NodeJS.Timeout | null = null;

  function updateInner(updater: Updater<Settings>) {
    inner.update((s) => {
      const newValue = updater(s);
      return deepEqual(s, newValue) ? s : newValue;
    });
  }

  async function get() {
    const current = {
      config: (await window.electron.invoke("get-config")) || initial.config,
      isInteractive:
        (await window.electron.invoke("has-focus")) || initial.isInteractive,
    };
    updateInner(() => current);
    return current;
  }

  window.electron.receive("focus-change", (isInteractive) => {
    console.log("focus-change", isInteractive);
    updateInner((s) => {
      return { ...s, isInteractive };
    });
  });

  window.electron.receive("config-change", (config) => {
    console.log("config-change", config);
    updateInner((s) => {
      return { ...s, config };
    });
  });

  async function set(value: Settings) {
    inner.set(value);
    await Promise.all([
      window.electron.send("set-config", value.config),
      window.electron.send(value.isInteractive ? "show" : "hide"),
    ]);
  }

  async function update(updater: Updater<Settings>) {
    const oldValue = await get();
    const newValue = updater(oldValue);
    inner.set(newValue);
    await Promise.all([
      deepEqual(oldValue.config, newValue.config)
        ? Promise.resolve()
        : window.electron.send("set-config", newValue.config),
      oldValue.isInteractive == newValue.isInteractive
        ? Promise.resolve()
        : window.electron.send(newValue.isInteractive ? "show" : "hide"),
    ]);
  }

  function subscribe(
    run: Subscriber<Settings>,
    invalidate: () => void,
  ): Unsubscriber {
    const u = inner.subscribe(run, invalidate);
    timeout = timeout || setInterval(get, 2000);
    return u;
  }

  return { set, update, subscribe };
}

export const settings = createSettings(initial);
