<script lang="ts">
	import { browser } from "$app/env";

    let count = $state(0)
    let desktop = $state("")

	if (window.electron && browser) {
		window.electron.receive('from-main', (data) => {
			desktop = `Received Message "${data}" from Electron`;
			console.log(desktop);
		});
	}
</script>

<div class="card h-56 w-56 justify-center self-center bg-amber-600">
	<button type="button" class="btn" onclick={() => window.electron.send('to-main', count++)}
		>Test</button
	>
    <textarea value={desktop}></textarea>
</div>
