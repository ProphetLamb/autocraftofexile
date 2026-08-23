<script lang="ts">
	import '@surdeddd/wmkit/themes/glass.css';
	import { dk } from '$lib/client/windowing';
	import Window from '$lib/client/Window.svelte';
	import { settings } from '$lib/client/settings';
	import { onMount } from 'svelte';
	import type { WindowUpdate } from '@surdeddd/wmkit';
	import { electron } from 'process';

	let count = $state(0);
	let desktop = $state('');

	window.electron.receive('from-main', (data) => {
		desktop = `Received Message "${data}" from Electron`;
		console.log(desktop);
	});
	const props = $state({ maximizable: false, minimizable: false } as Partial<WindowUpdate>);
	const hide = () => window.electron.send('hide');
	window.addEventListener('keyup', (e) => {
		if (e.key == 'Escape' && !e.defaultPrevented && !e.altKey && !e.ctrlKey) {
			hide();
		}
	});

	onMount(async () => {
		const user = await window.electron.invoke('get-user', 12);
		if (user) {
			props.title = `Hello ${user.name}!`;
		}
	});

	const listRecipes = async () => {
		return await window.electron.invoke('list-recipes', $settings.recipeDirectory);
	};
</script>

<div use:dk.desktop class="h-screen" onfocus={hide}>
	<Window id="main" {props} onclose={hide} class="flex flex-col space-y-2">
		{#await listRecipes()}
			<p>stores and actions, no wrapper components</p>
		{:then recipes}
			<ul>
				{#each recipes?.recipeFilePaths as recipe}
					<li>{recipe}</li>
				{/each}
			</ul>
		{/await}
		<button
			type="button"
			class="btn preset-filled-brand"
			onclick={() => {
				window.electron.send('to-main', count++);
				props.maximizable = !props.maximizable;
			}}>Test</button
		>
		<textarea class="textarea" value={desktop}></textarea>
	</Window>
</div>
