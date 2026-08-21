<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { dev } from '$app/env';

	let { children } = $props();

	if (dev) {
		window.electron.send('show');
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
{@render children()}
