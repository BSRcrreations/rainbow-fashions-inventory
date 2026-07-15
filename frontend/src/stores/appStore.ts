import { create } from "zustand";


interface AppState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
}


export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
