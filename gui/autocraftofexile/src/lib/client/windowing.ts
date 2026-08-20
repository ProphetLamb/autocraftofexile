import { createManager, createDesktop } from '@surdeddd/wmkit/svelte';
export const wm = createManager();
export const dk = createDesktop(wm);

if (import.meta.hot) {
    console.log('restoring wm', import.meta.hot.data.wm)
    if (import.meta.hot.data.wm) {			
        wm.hydrate(import.meta.hot.data.wm);
    }
    import.meta.hot.accept();
    import.meta.hot.dispose(() => {
        console.log('storing wm', wm.serialize())
        if (import.meta.hot) {
            import.meta.hot.data.wm = wm.serialize();
        }
    });
}