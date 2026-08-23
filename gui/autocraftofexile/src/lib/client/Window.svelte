<script module lang="ts">
  import { wmWindowStore } from "@surdeddd/wmkit/svelte";
  import {
    type Bounds,
    type ManagerEvents,
    type WindowStage,
    type WindowUpdate,
  } from "@surdeddd/wmkit";
  import { dk, wm } from "$lib/client/windowing";
  import { type Snippet } from "svelte";
  import { settings } from "$lib/client/settings";
</script>

<script lang="ts">
  export interface Props {
    id: string;
    stage?: WindowStage;
    props?: Partial<WindowUpdate> & Partial<Bounds>;
    class?: string;
    frameClass?: string;
    titlebarClass?: string;
    titleClass?: string;
    title?: Snippet;
    titlebarLeft?: Snippet;
    children?: Snippet;
    onclose?: (e: ManagerEvents["close"]) => void;
    onopen?: (e: ManagerEvents["open"]) => void;
  }
  let {
    id,
    stage = $bindable(),
    props,
    class: clazz,
    frameClass,
    titlebarClass,
    titleClass,
    title,
    titlebarLeft,
    children,
    onclose,
    onopen,
  }: Props = $props();
  // svelte-ignore state_referenced_locally
  const windowState = wmWindowStore(wm, id);
  const destroy: (() => unknown)[] = [
    wm.on("stage", (e) => {
      if (e.window.id === id) {
        if (e.window.stage === "minimized") {
          onclose?.(e);
        }
      }
    }),
    wm.on("open", (e) => {
      if (e.window.id === id) {
        onopen?.(e);
      }
    }),
  ];

  $effect(() => {
    const state = wm.get(id);
    if ($settings.isInteractive) {
      if (state && stage !== "minimized") {
        wm.restore(id);
      }
      if (!state) {
        // @ts-expect-error some additional properties
        wm.open({ ...(props || {}), id, stage });
      }
    } else if (state) {
      wm.minimize(id);
    }
  });

  $effect(() => {
    if (wm.get(id)) {
      wm.update(id, props as Partial<WindowUpdate>);
      if (props?.x && props?.y) {
        wm.move(id, props.x, props.y);
      }
      if (props?.width || props?.height) {
        wm.resize(id, props as Partial<Bounds>);
      }
    }
  });
  $effect.pre(() => {
    return () => Promise.all(destroy.map((f) => f()));
  });

  function kbClose(e: KeyboardEvent) {
    e.preventDefault();
    e.stopPropagation();
    wm.minimize(id);
    stage = "minimized";
  }
  function onkeyup(e: KeyboardEvent) {
    if (e.defaultPrevented) {
      return;
    }
    if (e.key == "Escape" && !e.altKey && !e.ctrlKey) {
      kbClose(e);
    }
    if (e.key == "w" && e.ctrlKey && !e.altKey) {
      kbClose(e);
    }
  }
</script>

<section
  use:dk.window={{ id: id, removeOnClose: true }}
  data-wm-skin="default"
  class={frameClass || ""}
  role="none"
  {onkeyup}
>
  <header data-wm-drag class={titlebarClass || ""}>
    {@render titlebarLeft?.()}
    <span data-wm-title class={titleClass || ""}>
      {#if title}
        {@render title()}
      {:else}
        {$windowState?.title}
      {/if}
    </span>
    <span>
      {#if $windowState?.maximizable}
        <button
          type="button"
          data-wm-maximize
          aria-label="Maximize {$windowState?.title}"
          title="Maximize">&nbsp;</button
        >
      {/if}
      {#if $windowState?.minimizable}
        <button
          type="button"
          data-wm-minimize
          aria-label="Close {$windowState?.title}"
          title="Close"
          onclick={() => (stage = "minimized")}>&nbsp;</button
        >
      {/if}
    </span>
  </header>
  <article data-wm-content class={clazz || ""}>
    {@render children?.()}
  </article>
</section>
