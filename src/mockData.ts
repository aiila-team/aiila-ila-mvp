export const DASHBOARD_STATS = {
  total_entities: 1243,
  alerts_today: 47,
  high_risk_entities: 12,
  sources_active: 5,
  alerts_per_hour: [8, 12, 5, 15, 22, 18, 25, 19, 14, 11, 16, 20, 18, 24, 17, 13, 21, 19, 15, 10, 14, 12, 18, 16],
};

export const MOCK_ALERTS = [
  {
    id: 1,
    entity_name: "threat-actor-001",
    entity_type: "Threat Actor",
    alert_type: "High Activity",
    risk_score: 9.2,
    timestamp: "2026-05-12T14:32:00Z",
  },
  {
    id: 2,
    entity_name: "malware-payload-x",
    entity_type: "Malware",
    alert_type: "Detection",
    risk_score: 8.7,
    timestamp: "2026-05-12T13:45:00Z",
  },
  {
    id: 3,
    entity_name: "phishing-domain-192",
    entity_type: "Domain",
    alert_type: "Phishing Campaign",
    risk_score: 7.4,
    timestamp: "2026-05-12T13:12:00Z",
  },
  {
    id: 4,
    entity_name: "ip-address-suspicious",
    entity_type: "IP Address",
    alert_type: "C2 Communication",
    risk_score: 8.9,
    timestamp: "2026-05-12T12:58:00Z",
  },
  {
    id: 5,
    entity_name: "ransomware-variant-v2",
    entity_type: "Malware",
    alert_type: "Detection",
    risk_score: 9.1,
    timestamp: "2026-05-12T12:23:00Z",
  },
  {
    id: 6,
    entity_name: "compromised-credential",
    entity_type: "Credential",
    alert_type: "Leaked Data",
    risk_score: 7.8,
    timestamp: "2026-05-12T11:45:00Z",
  },
];
