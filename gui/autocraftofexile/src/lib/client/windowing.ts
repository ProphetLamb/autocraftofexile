import { createManager, createDesktop } from '@surdeddd/wmkit/svelte';
export const wm = createManager();
export const dk = createDesktop(wm);

if (import.meta.hot) {
    if (import.meta.hot.data.wm) {
        wm.hydrate(import.meta.hot.data.wm);
    }
    import.meta.hot.accept();
    import.meta.hot.dispose(() => {
        if (import.meta.hot) {
            import.meta.hot.data.wm = wm.serialize();
        }
    });
}