// ─── Alert Types ───────────────────────────────────────────────────────────────
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type AlertStatus = 'open' | 'in_review' | 'resolved' | 'dismissed';

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  status: AlertStatus;
  source: string;
  entity_id?: string;
  entity_name?: string;
  timestamp: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

// ─── Entity Types ───────────────────────────────────────────────────────────────
export type EntityType = 'person' | 'organization' | 'domain' | 'ip' | 'url' | 'hash';

export interface Entity {
  id: string;
  name: string;
  type: EntityType;
  risk_score: number;
  description?: string;
  aliases?: string[];
  tags?: string[];
  first_seen: string;
  last_seen: string;
  metadata?: Record<string, any>;
  linked_entities?: string[];
}

// ─── Graph Types ────────────────────────────────────────────────────────────────
export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  risk_score?: number;
  x?: number;
  y?: number;
  metadata?: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  weight?: number;
  metadata?: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ─── Evidence Types ─────────────────────────────────────────────────────────────
export type EvidenceType = 'document' | 'image' | 'url' | 'social_post' | 'network_log' | 'other';

export interface Evidence {
  id: string;
  title: string;
  type: EvidenceType;
  source_url?: string;
  content?: string;
  entity_ids?: string[];
  alert_ids?: string[];
  collected_at: string;
  hash?: string;
  metadata?: Record<string, any>;
}

// ─── Source Monitor Types ───────────────────────────────────────────────────────
export type SourceStatus = 'active' | 'inactive' | 'error' | 'rate_limited';

export interface Source {
  id: string;
  name: string;
  url: string;
  type: string;
  status: SourceStatus;
  last_checked?: string;
  error_message?: string;
  keywords?: string[];
  metadata?: Record<string, any>;
}

// ─── Keyword Types ──────────────────────────────────────────────────────────────
export interface Keyword {
  id: string;
  value: string;
  category?: string;
  alert_count?: number;
  created_at: string;
}

// ─── Investigation Types ────────────────────────────────────────────────────────
export type InvestigationStatus = 'open' | 'in_progress' | 'closed';

export interface Investigation {
  id: string;
  title: string;
  description?: string;
  status: InvestigationStatus;
  entity_ids?: string[];
  alert_ids?: string[];
  created_at: string;
  updated_at: string;
  assignee?: string;
  tags?: string[];
}

// ─── User / Auth Types ──────────────────────────────────────────────────────────
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'analyst' | 'viewer';
  token?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

// ─── API Types ──────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// ─── Dashboard / Stats Types ────────────────────────────────────────────────────
export interface DashboardStats {
  total_alerts: number;
  open_alerts: number;
  critical_alerts: number;
  total_entities: number;
  active_sources: number;
  recent_alerts: Alert[];
}

// ─── WebSocket Message Types ────────────────────────────────────────────────────
export type WsMessageType = 'alert' | 'entity_update' | 'source_update' | 'ping';

export interface WsMessage {
  type: WsMessageType;
  payload: any;
  timestamp: string;
}
