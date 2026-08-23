<script lang="ts">
  import "./layout.css";
  import favicon from "$lib/assets/favicon.svg";
  import { onMount } from "svelte";
  import { initSettings } from "$lib/client/settings";

  let { children } = $props();

  onMount(initSettings);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
{@render children()}
