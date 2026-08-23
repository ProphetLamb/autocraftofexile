import { writable } from "svelte/store";

export const mouseCoords = writable({
  x: 0,
  y: 0,
});

export function updateMouseCoords(html: HTMLElement) {
  html.addEventListener("mousemove", (e) => {
    mouseCoords.set({
      x: e.offsetX,
      y: e.offsetY,
    });
  });
}
