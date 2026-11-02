import { useSyncExternalStore } from "react";

export interface Store<T> {
  get(): T;
  set(next: T | ((previous: T) => T)): void;
  subscribe(listener: () => void): () => void;
}

/** A tiny external store for game state that the loop mutates and the UI reads. */
export function createStore<T>(initial: T): Store<T> {
  let state = initial;
  const listeners = new Set<() => void>();
  return {
    get: () => state,
    set(next) {
      state = typeof next === "function" ? (next as (previous: T) => T)(state) : next;
      for (const listener of listeners) listener();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

/** Subscribe to a store. Select a primitive or an existing object; a fresh object per call re-renders forever. */
export function useStore<T, S = T>(store: Store<T>, select: (state: T) => S = (state) => state as unknown as S): S {
  return useSyncExternalStore(store.subscribe, () => select(store.get()));
}

/** Read and write a JSON value in localStorage, tolerating private windows and blocked storage. */
export const saved = {
  get<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : (JSON.parse(raw) as T);
    } catch {
      return fallback;
    }
  },
  set(key: string, value: unknown) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* storage unavailable: the artifact still works, it just forgets */
    }
  },
};
