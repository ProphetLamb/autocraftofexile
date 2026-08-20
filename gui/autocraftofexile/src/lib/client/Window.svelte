<script lang="ts">
	import { wmWindowStore } from '@surdeddd/wmkit/svelte';
	import { type WindowUpdate } from '@surdeddd/wmkit';
	import { dk, wm } from '$lib/client/windowing';
	import { type Snippet } from 'svelte';

	export interface Props {
		id: string;
		props?: Partial<WindowUpdate>;
		class?: string;
		frameClass?: string;
		titlebarClass?: string;
		titleClass?: string;
		title?: Snippet;
		titlebarLeft?: Snippet;
		children?: Snippet;
	}
	const {
		id,
		props,
		class: clazz,
		frameClass,
		titlebarClass,
		titleClass,
		title,
		titlebarLeft,
		children
	}: Props = $props();
	// svelte-ignore state_referenced_locally
	const window = wmWindowStore(wm, id);
	$effect(() => {
		wm.update(id, props as WindowUpdate);
	});
</script>

<section
	use:dk.window={{ id: id, removeOnClose: true }}
	data-wm-skin="default"
	class={frameClass || ''}
>
	<header data-wm-drag class={titlebarClass || ''}>
		{@render titlebarLeft?.()}
		<span data-wm-title class={titleClass || ''}>
			{#if title}
				{@render title()}
			{:else}
				{$window?.title}
			{/if}
		</span>
		<span>
			{#if $window?.minimizable}
				<button
					type="button"
					data-wm-minimize
					aria-label="Minimize {$window?.title}"
					title="Minimize"
				></button>
			{/if}
			{#if $window?.maximizable}
				<button
					type="button"
					data-wm-maximize
					aria-label="Maximize {$window?.title}"
					title="Maximize"
				></button>
			{/if}
			{#if $window?.closable}
				<button type="button" data-wm-close aria-label="Close {$window?.title}" title="Close"
				></button>
			{/if}
		</span>
	</header>
	<article data-wm-content class={clazz || ''}>
		{@render children?.()}
	</article>
</section>
