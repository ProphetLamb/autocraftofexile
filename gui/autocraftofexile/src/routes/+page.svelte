<script lang="ts">
	import '@surdeddd/wmkit/themes/glass.css';
	import { dk, wm } from '$lib/client/windowing';
	import Window from '$lib/client/Window.svelte';

	wm.open({ id: 'main', title: 'Hello' });

	let count = $state(0);
	let desktop = $state('');

	window.electron.receive('from-main', (data) => {
		desktop = `Received Message "${data}" from Electron`;
		console.log(desktop);
	});
	const props = $state({ maximizable: false, minimizable: false });
</script>

<div use:dk.desktop class="h-screen">
	<Window id="main" {props}>
		<p>stores and actions, no wrapper components</p>
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
