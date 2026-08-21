<script lang="ts">
	import { wmWindowStore } from '@surdeddd/wmkit/svelte';
	import { type ManagerEvents, type WindowUpdate } from '@surdeddd/wmkit';
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
		onclose?: (e: ManagerEvents['close']) => void;
		onopen?: (e: ManagerEvents['open']) => void;
		onresize?: (e: ManagerEvents['resize']) => void;
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
		children,
		onclose,
		onopen,
		onresize
	}: Props = $props();
	// svelte-ignore state_referenced_locally
	const windowState = wmWindowStore(wm, id);
	const destroy: (() => any | Promise<any>)[] = [
		wm.on('close', (e) => {
			if (e.window.id === id) {
				onclose?.(e);
			}
		}),
		wm.on('open', (e) => {
			if (e.window.id === id) {
				onopen?.(e);
			}
		}),
		wm.on('resize', (e) => {
			if (e.window.id === id) {
				onresize?.(e);
			}
		})
	];

	$effect(() => {
		wm.update(id, props as WindowUpdate);
	});
	$effect.pre(() => {
		if (!wm.get(id)) {
			// @ts-expect-error
			wm.open({ ...(props || {}), id });
		}
		return () => Promise.all(destroy.map((f) => f()));
	})

	const close = (e: KeyboardEvent) => {
		e.preventDefault();
		e.stopPropagation();
		wm.close(id);
	};
	const onkeyup = (e: KeyboardEvent) => {
		if (e.defaultPrevented) {
			return;
		}
		if (e.key == 'Escape' && !e.altKey && !e.ctrlKey) {
			close(e);
		}
		if (e.key == 'w' && e.ctrlKey && !e.altKey) {
			close(e);
		}
	};
</script>

<section
	use:dk.window={{ id: id, removeOnClose: true }}
	data-wm-skin="default"
	class={frameClass || ''}
	role="none"
	{onkeyup}
>
	<header data-wm-drag class={titlebarClass || ''}>
		{@render titlebarLeft?.()}
		<span data-wm-title class={titleClass || ''}>
			{#if title}
				{@render title()}
			{:else}
				{$windowState?.title}
			{/if}
		</span>
		<span>
			{#if $windowState?.minimizable}
				<button
					type="button"
					data-wm-minimize
					aria-label="Minimize {$windowState?.title}"
					title="Minimize"
				></button>
			{/if}
			{#if $windowState?.maximizable}
				<button
					type="button"
					data-wm-maximize
					aria-label="Maximize {$windowState?.title}"
					title="Maximize"
				></button>
			{/if}
			{#if $windowState?.closable}
				<button type="button" data-wm-close aria-label="Close {$windowState?.title}" title="Close"
				></button>
			{/if}
		</span>
	</header>
	<article data-wm-content class={clazz || ''}>
		{@render children?.()}
	</article>
</section>
