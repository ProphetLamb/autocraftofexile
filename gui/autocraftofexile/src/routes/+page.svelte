<script lang="ts">
  import { dk, wm } from "$lib/client/windowing";
  import Window from "$lib/client/Window.svelte";
  import { onMount } from "svelte";
  import type { WindowStage, WindowUpdate } from "@surdeddd/wmkit";
  import { settings } from "$lib/client/settings";
  import { updateMouseCoords } from "$lib/client/mouseTracker";
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
  } as Partial<WindowUpdate>);
  const hide = () => window.electron.send("hide");
  window.addEventListener("keyup", (e) => {
    if (e.key == "Escape" && !e.defaultPrevented && !e.altKey && !e.ctrlKey) {
      hide();
    }
  });

  onMount(async () => {
    const user = await window.electron.invoke("get-user", 12);
    if (user) {
      props.title = `Hello ${user.name}!`;
    }
  });

  let settingsStage: WindowStage = $state("minimized");
</script>

<div
  use:dk.desktop
  use:updateMouseCoords
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
