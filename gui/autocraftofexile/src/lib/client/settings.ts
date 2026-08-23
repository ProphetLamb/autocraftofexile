import { writable } from "$lib/client/localStore";

type Settings = {
    recipeDirectory: string
}

export const settings = writable<Settings>("settings", {
    recipeDirectory: '~/.config/autocraftofexile/recipes'
})