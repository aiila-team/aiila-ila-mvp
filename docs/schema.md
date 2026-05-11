ILA Data Model

This diagram reflects the current SQLAlchemy models in `backend/app/models/__init__.py`.
It is intentionally focused on the tables that power ingestion, enrichment, alerting,
and analyst workflows.

```mermaid
erDiagram
    users {
        UUID id PK
        string username
        string email
        string hashed_password
        string full_name
        enum role
        boolean is_active
        timestamp created_at
        timestamp last_login
    }

    sources {
        UUID id PK
        string name
        enum source_type
        enum tier
        string url
        text description
        boolean is_active
        float reliability_multiplier
        int crawl_interval_minutes
        timestamp last_crawled_at
        int event_count_today
        timestamp created_at
    }

    keywords {
        UUID id PK
        string word
        string category
        string language
        boolean is_active
        int match_count
        UUID created_by FK
        timestamp created_at
    }

    raw_events {
        UUID id PK
        UUID source_id FK
        string external_id
        text content
        string content_language
        text translated_content
        string url
        string author_handle
        string platform
        timestamp published_at
        timestamp ingested_at
        boolean is_processed
        boolean is_duplicate
        UUID duplicate_of FK
        jsonb extracted_entities
        float sentiment_score
        float anomaly_score
        jsonb matched_keywords
        jsonb minhash_signature
        jsonb metadata
        tsvector search_vector
    }

    entities {
        UUID id PK
        enum entity_type
        string primary_identifier
        string display_name
        float risk_score
        enum risk_level
        float influence_score
        float anomaly_score
        float sentiment_avg
        int event_count
        timestamp first_seen
        timestamp last_seen
        boolean is_flagged
        text investigation_notes
        jsonb risk_factors
        jsonb metadata
    }

    entity_aliases {
        UUID id PK
        UUID entity_id FK
        string alias_type
        string alias_value
        string platform
        float confidence
        string resolution_method
        timestamp first_seen
        boolean is_verified
    }

    entity_events {
        UUID id PK
        UUID entity_id FK
        UUID event_id FK
        string role
        timestamp created_at
    }

    relationships {
        UUID id PK
        UUID source_entity_id FK
        UUID target_entity_id FK
        string relationship_type
        timestamp created_at
    }

    risk_alerts {
        UUID id PK
        UUID entity_id FK
        enum alert_type
        string title
        text description
        float risk_score
        enum risk_level
        enum status
        UUID trigger_event_id FK
        string matched_pattern
        jsonb risk_factors
        jsonb evidence_data
        UUID reviewed_by FK
        timestamp reviewed_at
        text analyst_note
        timestamp created_at
        timestamp updated_at
    }

    evidence_packages {
        UUID id PK
        UUID entity_id FK
        UUID generated_by FK
        string case_id
        string file_path
        jsonb entities_included
        int events_count
        text analyst_note
        text legal_disclaimer
        timestamp generated_at
        timestamp expires_at
    }

    %% Relationships
    users ||--o{ keywords : "created_by"
    users ||--o{ risk_alerts : "reviewed_by"
    users ||--o{ evidence_packages : "generated_by"

    sources ||--o{ raw_events : "ingests"

    raw_events ||--o{ raw_events : "duplicate_of"
    raw_events ||--o{ entity_events : "event_id"
    raw_events ||--o{ risk_alerts : "trigger_event_id"

    entities ||--o{ entity_aliases : "has_alias"
    entities ||--o{ entity_events : "entity_id"
    entities ||--o{ relationships : "is_source_of"
    entities ||--o{ relationships : "is_target_of"
    entities ||--o{ risk_alerts : "alerts"
    entities ||--o{ evidence_packages : "documented_in"

    entities ||--o{ raw_events : "mentioned_in"
```

## Notes

- `entity_events` is the join table between `entities` and `raw_events`.
- `risk_alerts` are analyst-facing records generated from the enrichment pipeline.
- `evidence_packages` are generated on demand for a specific entity or case.
- `keywords.created_by` links back to `users`, but it is optional in the current loader flow.
- Some columns such as `search_vector`, `minhash_signature`, and `metadata` are implementation-oriented fields used by search and enrichment code.
