<script lang="ts">
  import { dk, wm } from "$lib/client/windowing";
  import Window from "$lib/client/Window.svelte";
  import { onMount } from "svelte";
  import type { Bounds, WindowStage, WindowUpdate } from "@surdeddd/wmkit";
  import { settings } from "$lib/client/settings";
  import Settings from "$lib/client/Settings.svelte";

  let count = $state(0);
  let desktop = $state("");

  window.electron.receive("from-main", (data) => {
    desktop = `Received Message "${data}" from Electron`;
    console.log(desktop);
  });
  const props = $state({
    maximizable: false,
    minimizable: true,
    closable: false,
    resizable: false,
  } as Partial<WindowUpdate> & Partial<Bounds>);

  async function updateMainTitle() {
    const user = await window.electron.invoke("get-user", 12);
    if (user) {
      props.title = `Hello ${user.name}!`;
    }
  }

  function hide() {
    $settings.isInteractive = false;
  }

  function keyupListener(e: KeyboardEvent) {
    if (e.key == "Escape" && !e.defaultPrevented && !e.altKey && !e.ctrlKey) {
      hide();
    }
  }

  onMount(() => {
    updateMainTitle();

    window.electron.receive("focus-change", async (focussed) => {
      if (focussed) {
        const coords = await window.electron.invoke("get-mouse-coords");
        if (coords) {
          props.x = coords.x + 10;
          props.y = coords.y - 30;
        }
      }
    });

    window.addEventListener("keyup", keyupListener);

    return () => {
      window.removeEventListener("keyup", keyupListener);
    };
  });

  let settingsStage: WindowStage = $state("minimized");
</script>

<div
  use:dk.desktop
  class="relative h-screen overflow-hidden {$settings.isInteractive
    ? 'bg-surface-500/50'
    : 'hidden'}"
>
  <button
    type="button"
    class="absolute top-4 right-4 btn preset-filled-brand"
    onclick={() =>
      (settingsStage = settingsStage !== "minimized" ? "minimized" : "normal")}
    >Settings</button
  >
  <Window id="main" {props} onclose={hide} class="flex flex-col space-y-2">
    <button
      type="button"
      class="btn preset-filled-brand"
      onclick={() => {
        window.electron.send("to-main", count++);
        props.maximizable = !props.maximizable;
      }}>Test</button
    >
    <textarea class="textarea" value={desktop}></textarea>
  </Window>
  <Window
    id="settings"
    bind:stage={settingsStage}
    props={{
      title: "Settings",
      maximizable: false,
      closable: false,
    }}
  >
    <Settings />
  </Window>
</div>
