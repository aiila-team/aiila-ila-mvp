import json
import os
import sys
from pathlib import Path
# pyrefly: ignore [missing-import]
from neo4j import GraphDatabase

MOCK_DATA_PATH = Path(__file__).parent / "mock_data.json"


def load_env_file(env_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file if present."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


ROOT = Path(__file__).parent.parent
load_env_file(ROOT / ".env")
load_env_file(ROOT.parent / ".env")

RESET = os.getenv("RESET", "false").lower() == "true" or "--reset" in sys.argv or "-r" in sys.argv

# Neo4j connection details (from environment variables)
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
    raise ValueError(
        "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD environment variables must be set. "
        "Please configure these before running this script."
    )

def clear_graph(session):
    print("Clearing existing Neo4j graph...")
    session.run("MATCH (n) DETACH DELETE n")


def _entity_label(entity_type: str) -> str:
    return {
        "person": "Person",
        "phone": "Phone",
        "ip_address": "IPAddress",
        "upi_account": "UPIAccount",
        "email": "EmailAddress",
        "social_handle": "SocialAccount",
        "telegram": "SocialAccount",
        "imei": "IMEIDevice",
        "crypto_wallet": "CryptoWallet",
    }.get(entity_type, entity_type.title().replace("_", ""))

def load_entities(session, entities):
    print(f"Loading {len(entities)} primary entities into Neo4j...")
    for ent in entities:
        # Dynamically create the label based on entity_type (e.g., 'person' -> 'Person')
        label = _entity_label(ent.get("entity_type", "Unknown"))
        
        query = f"""
        MERGE (n:{label} {{id: $id}})
        SET n.primary_identifier = $identifier,
            n.risk_score = $risk_score,
            n.risk_level = $risk_level,
            n.is_flagged = $is_flagged
        """
        session.run(
            query, 
            id=ent["id"], 
            identifier=ent["primary_identifier"],
            risk_score=ent.get("risk_score", 0.0),
            risk_level=ent.get("risk_level", "low"),
            is_flagged=ent.get("is_flagged", False)
        )

        ip_address = ent.get("metadata_", {}).get("ip_address")
        if ip_address:
            session.run(
                """
                MERGE (ip:IPAddress {id: $ip_address})
                SET ip.address = $ip_address,
                    ip.entity_id = $entity_id,
                    ip.source = 'entity_metadata'
                WITH ip
                MATCH (person:Person {id: $entity_id})
                MERGE (person)-[:USES]->(ip)
                """,
                entity_id=ent["id"],
                ip_address=ip_address,
            )

def load_aliases(session, aliases):
    print(f"Loading {len(aliases)} aliases and linking to entities...")
    for alias in aliases:
        # E.g., 'phone' -> 'Phone', 'social_handle' -> 'SocialHandle'
        alias_label = _entity_label(alias.get("alias_type", "Unknown"))
        
        query = f"""
        MATCH (e {{id: $entity_id}})
        MERGE (a:{alias_label} {{id: $alias_value}})
        SET a.value = $alias_value
        MERGE (e)-[:HAS_IDENTIFIER]->(a)
        """
        session.run(
            query,
            entity_id=alias["entity_id"],
            alias_value=alias["alias_value"]
        )

def load_events(session, events):
    print(f"Loading {len(events)} events and creating MENTIONED_IN / POSTED relationships...")
    for ev in events:
        query = """
        MERGE (v:RawEvent {id: $id})
        SET v.platform = $platform,
            v.published_at = $published_at
        """
        session.run(
            query,
            id=ev["id"],
            platform=ev.get("platform", "unknown"),
            published_at=ev.get("published_at", "")
        )

        # Link event to the person entity if the helper field exists
        person_id = ev.get("_person_entity_id")
        if person_id:
            link_query = """
            MATCH (e {id: $entity_id})
            MATCH (v:RawEvent {id: $event_id})
            MERGE (e)-[:MENTIONED_IN]->(v)
            """
            session.run(link_query, entity_id=person_id, event_id=ev["id"])

        author_handle = ev.get("author_handle")
        if author_handle:
            posted_query = """
            MATCH (v:RawEvent {id: $event_id})
            MERGE (author:SocialAccount {id: $author_handle})
            SET author.handle = $author_handle
            MERGE (author)-[:POSTED]->(v)
            """
            session.run(
                posted_query,
                event_id=ev["id"],
                author_handle=author_handle,
            )

        for extracted in ev.get("extracted_entities", []):
            if extracted.get("type") != "ip_address":
                continue

            ip_address = extracted.get("value")
            if not ip_address:
                continue

            ip_query = """
            MATCH (v:RawEvent {id: $event_id})
            MATCH (e {id: $entity_id})
            MERGE (ip:IPAddress {id: $ip_address})
            SET ip.address = $ip_address,
                ip.source = 'event_extraction'
            MERGE (e)-[:USES]->(ip)
            MERGE (v)-[:MENTIONS]->(ip)
            """
            session.run(
                ip_query,
                event_id=ev["id"],
                entity_id=person_id or ev.get("_person_entity_id"),
                ip_address=ip_address,
            )

def load_relationships(session, relationships):
    print(f"Loading {len(relationships)} direct relationships...")
    for rel in relationships:
        query = f"""
        MATCH (src {{id: $source_id}})
        MATCH (tgt {{id: $target_id}})
        MERGE (src)-[r:{rel['type']}]->(tgt)
        SET r.weight = $weight,
            r.description = $description
        """
        session.run(
            query,
            source_id=rel["source_id"],
            target_id=rel["target_id"],
            weight=rel.get("weight", 1.0),
            description=rel.get("description", ""),
        )

def main():
    print("Starting Neo4j Data Loader...")
    
    if not MOCK_DATA_PATH.exists():
        print(f"❌ Error: {MOCK_DATA_PATH.name} not found. Run generate_mock_data.py first.")
        return

    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    try:
        with driver.session() as session:
            if RESET:
                clear_graph(session)
            else:
                print("Preserving existing Neo4j graph (set RESET=true to clear it).")
            load_entities(session, data.get("entities", []))
            load_aliases(session, data.get("aliases", []))
            load_events(session, data.get("events", []))
            load_relationships(session, data.get("relationships", []))
            print("✅ Successfully loaded graph data into Neo4j!")
    except Exception as e:
        print(f"❌ Error loading data into Neo4j: {e}")
    finally:
        driver.close()

if __name__ == "__main__":
    main()
