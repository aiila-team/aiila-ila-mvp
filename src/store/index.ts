import { create } from 'zustand';
import { Alert, Entity, User, DashboardStats } from '../types';

// ─── Auth Store ─────────────────────────────────────────────────────────────────
interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('auth_token'),
  isLoading: false,
  error: null,
  login: (user, token) => {
    localStorage.setItem('auth_token', token);
    set({ user, isAuthenticated: true, error: null });
  },
  logout: () => {
    localStorage.removeItem('auth_token');
    set({ user: null, isAuthenticated: false });
  },
  setError: (error) => set({ error }),
  setLoading: (isLoading) => set({ isLoading }),
}));

// ─── Alert Store ─────────────────────────────────────────────────────────────────
interface AlertStore {
  alerts: Alert[];
  unreadCount: number;
  isLoading: boolean;
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  updateAlert: (id: string, updates: Partial<Alert>) => void;
  removeAlert: (id: string) => void;
  setLoading: (loading: boolean) => void;
  clearUnread: () => void;
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  unreadCount: 0,
  isLoading: false,
  setAlerts: (alerts) => set({ alerts }),
  addAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
      unreadCount: state.unreadCount + 1,
    })),
  updateAlert: (id, updates) =>
    set((state) => ({
      alerts: state.alerts.map((a) => (a.id === id ? { ...a, ...updates } : a)),
    })),
  removeAlert: (id) =>
    set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),
  setLoading: (isLoading) => set({ isLoading }),
  clearUnread: () => set({ unreadCount: 0 }),
}));

// ─── Entity Store ────────────────────────────────────────────────────────────────
interface EntityStore {
  entities: Entity[];
  selectedEntity: Entity | null;
  isLoading: boolean;
  setEntities: (entities: Entity[]) => void;
  setSelectedEntity: (entity: Entity | null) => void;
  updateEntity: (id: string, updates: Partial<Entity>) => void;
  setLoading: (loading: boolean) => void;
}

export const useEntityStore = create<EntityStore>((set) => ({
  entities: [],
  selectedEntity: null,
  isLoading: false,
  setEntities: (entities) => set({ entities }),
  setSelectedEntity: (selectedEntity) => set({ selectedEntity }),
  updateEntity: (id, updates) =>
    set((state) => ({
      entities: state.entities.map((e) => (e.id === id ? { ...e, ...updates } : e)),
    })),
  setLoading: (isLoading) => set({ isLoading }),
}));

// ─── UI Store ────────────────────────────────────────────────────────────────────
interface UIStore {
  sidebarOpen: boolean;
  searchQuery: string;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSearchQuery: (query: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  searchQuery: '',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
}));
