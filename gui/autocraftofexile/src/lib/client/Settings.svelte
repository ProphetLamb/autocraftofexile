<script lang="ts">
  import { settings } from "$lib/client/settings";

  let config = $derived($settings.config);

  function toggleKeyListener(ev: KeyboardEvent) {
    ev.preventDefault();
    let code = ev.key.toLocaleUpperCase();
    if (!/^(?:[Ff][0-9]+)|[A-Z0-9\s\p{P}]$/u.test(code)) {
      console.log("invalid electron hotkey", ev);
      return;
    }
    if (code === " ") {
      code = "Space";
    }
    if (ev.metaKey) {
      code = `Super + ${code}`;
    }
    if (ev.shiftKey) {
      code = `Shift + ${code}`;
    }
    if (ev.altKey) {
      code = `Alt + ${code}`;
    }
    if (ev.ctrlKey) {
      code = `CmdOrCtrl + ${code}`;
    }
    config.toggleKey = code;
  }
</script>

<form
  class="grid grid-flow-row gap-4 items-center-safe"
  onsubmit={() => window.electron.send("set-config", { ...config })}
>
  <label class="label">
    <span class="label-text"> Hotkey </span>
    <div class="field-group grid-cols-[1fr_auto]">
      <input
        readonly
        type="text"
        name="toggleKey"
        id="toggleKey"
        class="input"
        onfocusin={() => window.addEventListener("keydown", toggleKeyListener)}
        onfocusout={() =>
          window.removeEventListener("keydown", toggleKeyListener)}
        value={config.toggleKey}
      />
      <button
        type="button"
        class="btn preset-tonal-secondary"
        onclick={() => (config.toggleKey = $settings.config.toggleKey)}
        >Reset</button
      >
    </div>
  </label>
  <button type="submit" class="btn preset-filled-brand">Save</button>
</form>
