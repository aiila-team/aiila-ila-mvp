# ILA Database Schema (MVP)

* **users**: Analysts accessing the system.
* **sources**: Live data origins (e.g., RSS, Telegram).
* **raw_events**: Unprocessed text/data ingested from sources.
* **entities**: Extracted actors (Person, Phone, Telegram, UPI).
* **entity_aliases**: Linked identifiers resolving to a single entity.
* **relationships**: Edges connecting entities (e.g., OWNS, TRANSFERRED_TO).
* **risk_alerts**: Threats flagged by the risk scoring engine.
* **keywords**: Terms actively monitored by analysts.
* **evidence_packages**: Generated PDF report metadata.
