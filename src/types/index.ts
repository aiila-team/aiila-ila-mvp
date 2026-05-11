// src/types/index.ts
// Shared TypeScript interfaces — keep in sync with Likhita's Pydantic schemas

export type EntityType = 'Person' | 'Phone' | 'SocialAccount' | 'UPIAccount' | 'EmailAddress' | 'Phone_Cluster';

export type AlertStatus = 'new' | 'under_review' | 'confirmed' | 'dismissed';

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type SourceTier = 1 | 2 | 3 | 4;

export interface Alert {
  id: string;
  entity_name: string;
  entity_type: EntityType;
  primary_id: string;
  aliases: string[];
  alert_type: string;
  source: string;
  source_tier: SourceTier;
  risk_score: number;       // 0-10
  sentiment: number;        // -1 to 1
  status: AlertStatus;
  timestamp: string;        // ISO8601
  summary: string;
  event_count: number;
  flags: string[];
  risk_factors: string[];   // Top-3 from Mythresh's explainability service
}

export interface Entity {
  id: string;
  entity_type: EntityType;
  primary_id: string;
  aliases: string[];
  risk_score: number;
  first_seen: string;
  last_seen: string;
  event_count: number;
  source_count: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: EntityType;
  risk: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: 'OWNS' | 'CONTROLS' | 'POSTED' | 'KNOWS' | 'TRANSFERRED_TO';
}

export interface DataSource {
  id: string;
  name: string;
  type: 'rss' | 'telegram' | 'social' | 'mock';
  status: 'active' | 'error' | 'paused';
  tier: SourceTier;
  events_today: number;
  last_crawl: string;
}

export interface Keyword {
  id: string;
  word: string;
  group: string;
  hits_today: number;
  enabled: boolean;
}

export interface DashboardStats {
  total_entities: number;
  alerts_today: number;
  high_risk_entities: number;
  sources_active: number;
  alerts_per_hour: number[];
}
