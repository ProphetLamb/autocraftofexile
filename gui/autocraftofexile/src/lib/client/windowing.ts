import { createManager, createDesktop } from '@surdeddd/wmkit/svelte';
export const wm = createManager();
export const dk = createDesktop(wm);

restoreWm();
setInterval(saveWm, 2000);

export function restoreWm() {
    const serialized = import.meta.hot?.data.wm ?? window?.localStorage?.getItem('wm')
    if (serialized) {
        wm.hydrate(JSON.parse(serialized));
    }
}

export function saveWm() {
    const serialized = JSON.stringify(wm.serialize());
    if (import.meta.hot) {
        import.meta.hot.data.wm = serialized
    }
    if (window?.localStorage) {
        window.localStorage.setItem('wm', serialized)
    }
}

if (import.meta.hot) {
    restoreWm();
    import.meta.hot.accept();
    import.meta.hot.dispose(() => {
        saveWm();
    });
}