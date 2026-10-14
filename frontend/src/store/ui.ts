import { create } from "zustand";
type UIState = { sidebarOpen: boolean; query: string; setSidebarOpen: (open: boolean) => void; setQuery: (query: string) => void };
export const useUIStore = create<UIState>((set) => ({ sidebarOpen: true, query: "", setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }), setQuery: (query) => set({ query }) }));
