import { browser } from '$app/env'
import { writable as internal, get, type Writable } from 'svelte/store'

export function writable<T>(key: string, initialValue: T): Writable<T> {
    const store = internal(initialValue)
    if (browser) {
        const json = localStorage.getItem(key)
        if (json) { store.set(JSON.parse(json)) }
    }

    function set(value: T) {
        if (browser) {
            localStorage.setItem(key, JSON.stringify(value))
        }
        store.set(value)
    }

    return {
        set,
        update(cb) {
            set(cb(get(store)))
        },
        subscribe: store.subscribe
    }
} 