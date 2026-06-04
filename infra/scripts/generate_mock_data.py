"""
ILA — Advanced Mock Data Generator  v2
scripts/generate_mock_data.py

Simulates REAL-WORLD threat intelligence scenarios:

  NETWORK ARCHITECTURES GENERATED:
  ─────────────────────────────────
  1.  Hawala Transfer Network (Hub-and-Spoke)
      1 Hawala Broker → 4 City-Level Coordinators → 12 Mule Accounts each
      Shared crypto wallet + IMEI device per coordinator

  2.  Crypto-to-UPI Layering Ring
      3 crypto source wallets → 2 exchange proxies → 8 UPI collector accounts
      Person entities linked across wallets + UPI + phones

  3.  Coordinated Inauthentic Behaviour (Propaganda Farm)
      1 Handler → 5 Sub-handlers → 20 Bot Accounts
      All share same IP subnet + post within same 30-minute windows

  4.  SIM Swap Fraud Cluster
      4 Telecom Insiders → 15 Victim Accounts (SIM swapped)
      Insider → Swapper → Mule chain

  5.  Phishing Domain Network
      1 Registrant → 8 Domains → Linked persons via email + IP

  6.  Person-to-Person KNOWS graph
      City-level co-occurrence, family name clustering, phone tower proximity

  ENTITY STATISTICS (1 full run):
  ────────────────────────────────
  ~180 person entities
  ~500 total entities (incl. phones, UPI, Telegram, email, crypto, IMEI)
  ~1 200 raw events (with realistic content per threat scenario)
  ~80  risk alerts
  ~600 direct relationships (KNOWS, OWNS, CONTROLS, OPERATES, LINKED_TO)
  ~800 entity aliases

Usage:
  pip install faker
  python scripts/generate_mock_data.py
  → Outputs: scripts/mock_data.json
"""

import json
import random
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from faker import Faker

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

# ─────────────────────────────────────────────────────────────────────────────
# DATA POOLS
# ─────────────────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Ravi","Amit","Suresh","Rahul","Vikram","Arjun","Kiran","Priya","Deepak",
    "Sanjay","Arun","Manoj","Rakesh","Sunita","Kavita","Pooja","Rajesh","Mohan",
    "Ganesh","Shankar","Ramesh","Dinesh","Naresh","Sunil","Pavan","Harish",
    "Mahesh","Santosh","Vijay","Ajay","Akash","Rohit","Nikhil","Ankit","Vishal",
    "Gaurav","Sachin","Manish","Varun","Abdul","Mohammad","Ali","Ibrahim",
    "Hassan","Imran","Farhan","Zaid","Gurpreet","Harpreet","Jaswant","Kulwant",
    "Balwant","Manpreet","Navpreet","Aarav","Ishaan","Shiva","Kartik","Pranav",
    "Yash","Harsh","Dev","Fatima","Aisha","Zara","Noor","Sana","Ruhi","Meher",
    "Lakshmi","Saraswati","Parvati","Durga","Ananya","Divya","Sneha","Neha",
    "Ramakrishna","Venkatesan","Subramaniam","Krishnamurthy","Balasubramanian",
    "Thiruvengadam","Narayanasamy","Radhakrishnan","Parthasarathy","Venkataraman",
    "Brijesh","Chandrakant","Dharmendra","Fulchand","Govind","Hemant","Indrajeet",
]

LAST_NAMES = [
    "Kumar","Singh","Sharma","Verma","Gupta","Patel","Shah","Mehta","Joshi",
    "Pandey","Mishra","Tiwari","Yadav","Chauhan","Rajput","Agarwal","Bansal",
    "Goel","Mittal","Jain","Malhotra","Kapoor","Bose","Chatterjee","Mukherjee",
    "Ghosh","Das","Dey","Roy","Sen","Khan","Sheikh","Ansari","Siddiqui",
    "Qureshi","Malik","Mirza","Reddy","Rao","Naidu","Pillai","Nair","Menon",
    "Iyer","Krishnan","Thakur","Saxena","Srivastava","Shukla","Dubey","Tripathi",
    "Bajpai","Chaudhary","Bhatt","Pathak","Kulkarni","Desai","Patil","Sawant",
    "Subramaniam","Venkatesh","Narayanan","Rajan","Chandran","Natarajan",
    "Raghunathan","Krishnaswamy","Swaminathan","Muthusamy","Annamalai",
]

UPI_PROVIDERS = [
    "@okaxis","@okhdfcbank","@okicici","@oksbi","@ybl","@ibl",
    "@paytm","@axl","@hdfcbank","@upi","@apl","@boi","@freecharge",
    "@jio","@airtel","@barodampay","@allbank","@utibankAxispaytm",
]

TELEGRAM_PREFIXES = [
    "india_news","truth_india","wake_up_bharat","real_news","expose_",
    "breaking_","alert_","india_","bharat_","desh_","sach_",
    "security_watch","cyber_india","fraud_alert","scam_buster",
    "terror_watch","naxal_","isi_expose","anti_india_","pak_",
    "hawala_","crypto_india","dark_","anon_","secret_","money_",
    "transfer_","op_","shadow_","proxy_","relay_",
]

INDIAN_CITIES = [
    "Mumbai","Delhi","Bengaluru","Hyderabad","Chennai","Kolkata","Pune",
    "Ahmedabad","Surat","Jaipur","Lucknow","Kanpur","Nagpur","Indore",
    "Patna","Bhopal","Ludhiana","Agra","Varanasi","Nashik","Meerut",
    "Amritsar","Visakhapatnam","Vadodara","Raipur","Coimbatore",
    "Thiruvananthapuram","Ranchi","Guwahati","Jammu","Srinagar",
    "Dhanbad","Jodhpur","Kota","Gwalior","Vijayawada","Chandigarh",
]

THREAT_KEYWORDS = [
    "hawala","hundi","terrorist","IED","naxal","LeT","ISI",
    "black money","mule account","SIM swap","phishing","crypto",
    "fake news","propaganda","disinformation","deepfake",
    "arms","ammunition","weapons","explosives","RDX",
    "separatist","militancy","insurgency","radicalize",
    "darkweb","tor","bitcoin","USDT","hawala transfer",
    "OTP share","account blocked","verify now","urgent transfer",
]

FRAUD_PATTERNS = [
    "FT-001: Mule Account Velocity Pattern",
    "FT-002: Coordinated Inauthentic Posting",
    "FT-003: SIM Swap Fraud",
    "FT-004: Phishing Domain Cluster",
    "FT-005: Crypto-to-UPI Layering Network",
    "FT-006: Hawala Network Node",
    "FT-007: Radicalization Content Amplifier",
    "FT-008: OTP Harvesting Scam",
]

DOMAIN_SUFFIXES = [".in",".co.in",".net.in",".org.in",".info",".co",".xyz",".top"]
LEGIT_DOMAINS   = ["sbi","hdfc","icicipay","paytm","nsdl","uidai","irctc","incometax","epf"]

# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

NOW = now_utc()

def dt_ago(days=0, hours=0, minutes=0) -> datetime:
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)

def rand_dt(min_days=0, max_days=90, min_hours=0, max_hours=23) -> datetime:
    return NOW - timedelta(
        days=random.randint(min_days, max_days),
        hours=random.randint(min_hours, max_hours),
        minutes=random.randint(0, 59),
    )

def gen_phone() -> str:
    prefix = random.choice(["70","71","72","73","74","75","76","77","78","79",
                             "80","81","82","83","85","86","87","88","90","91",
                             "94","98","99"])
    return f"+91{prefix}{''.join(str(random.randint(0,9)) for _ in range(8))}"

def gen_ip(subnet: str = None) -> str:
    if subnet:
        parts = subnet.split(".")
        return f"{parts[0]}.{parts[1]}.{random.randint(1,254)}.{random.randint(1,254)}"
    first = random.choice([13,14,27,36,43,49,52,103,106,111,112,115,
                           117,122,123,124,125,139,144,157,182,183,202,
                           203,210,218,223])
    return f"{first}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def gen_upi(name: str = "") -> str:
    clean = (name or "user").lower().replace(" ","")[:10]
    num   = random.randint(1, 999)
    prov  = random.choice(UPI_PROVIDERS)
    return random.choice([f"{clean}{prov}", f"{clean}{num}{prov}", f"{clean[:5]}{num}{prov}"])

def gen_tg(name: str = "") -> str:
    if name and random.random() > 0.45:
        base = name.lower().replace(" ","_")[:10]
        return f"@{base}{random.randint(1,9999)}"
    return f"@{random.choice(TELEGRAM_PREFIXES)}{random.randint(100,9999)}"

def gen_tw(name: str = "") -> str:
    pfx  = random.choice(["real_","truth_","official_","the_",""])
    base = (name.lower().replace(" ","")[:10] if name else fake.word())
    return f"@{pfx}{base}{random.randint(1,9999)}"

def gen_email(name: str = "") -> str:
    clean = (name or "user").lower().replace(" ",".")
    doms  = ["gmail.com","yahoo.co.in","hotmail.com","rediffmail.com",
             "outlook.com","protonmail.com","tutanota.com","mail.com"]
    num   = random.randint(1,999) if random.random() > 0.5 else ""
    return f"{clean}{num}@{random.choice(doms)}"

def gen_crypto(wallet_type: str = None) -> str:
    wt = wallet_type or random.choice(["btc","usdt_trc20","eth"])
    b58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if wt == "btc":
        return "1" + "".join(random.choices(b58, k=33))
    elif wt == "usdt_trc20":
        return "T" + "".join(random.choices(b58, k=33))
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))

def gen_imei() -> str:
    return "86" + "".join(str(random.randint(0,9)) for _ in range(13))

def gen_phishing_domain(seed: str = None) -> str:
    base   = seed or random.choice(LEGIT_DOMAINS)
    prefix = random.choice(["secure-","verify-","update-","login-","net-","my-","new-","alert-"])
    suffix = random.choice(DOMAIN_SUFFIXES)
    return f"{prefix}{base}{random.randint(1,999)}{suffix}"

def risk_level(score: float) -> str:
    if score >= 8.5:  return "critical"
    if score >= 6.5:  return "high"
    if score >= 4.0:  return "medium"
    return "low"

def composite_risk(anomaly, pattern, connections, velocity, sentiment, multiplier=1.0) -> float:
    centrality = min(connections / 25.0, 1.0)
    base = (anomaly * 0.30 + pattern * 0.25 + centrality * 0.20 +
            velocity * 0.15 + abs(sentiment) * 0.10)
    return round(min(base * 10.0 * multiplier, 10.0), 2)

def person_record(name, phone, upi_id, tg, tw, email, ip, city,
                  risk_score, anomaly, sentiment, velocity,
                  n_conn, factors, first_seen=None, last_seen=None,
                  crypto_wallet=None, imei=None, extra_meta=None):
    eid = uid()
    rl  = risk_level(risk_score)
    return {
        "id":                 eid,
        "entity_type":        "person",
        "primary_identifier": name,
        "display_name":       name,
        "risk_score":         risk_score,
        "risk_level":         rl,
        "influence_score":    round(random.uniform(0.01, 1.0), 4),
        "anomaly_score":      round(anomaly, 4),
        "sentiment_avg":      round(sentiment, 4),
        "event_count":        random.randint(3, 250),
        "first_seen":         (first_seen or rand_dt(30, 180)).isoformat(),
        "last_seen":          (last_seen  or rand_dt(0,  48)).isoformat(),
        "is_flagged":         risk_score >= 6.5,
        "investigation_notes":None,
        "risk_factors":       factors[:3],
        "metadata_": {
            "city":                city,
            "ip_address":          ip,
            "network_connections": n_conn,
            **(extra_meta or {}),
        },
        # runtime-only fields for generation pipeline
        "_phone":        phone,
        "_upi":          upi_id,
        "_tg":           tg,
        "_tw":           tw,
        "_email":        email,
        "_ip":           ip,
        "_city":         city,
        "_crypto":       crypto_wallet,
        "_imei":         imei,
    }

def build_aliases(entity_id: str, person: dict) -> list:
    defs = [
        ("phone",         person["_phone"],  "telegram"),
        ("upi_account",   person["_upi"],    "upi"),
        ("telegram",      person["_tg"],     "telegram"),
    ]
    if person.get("_tw")     and random.random() > 0.25:
        defs.append(("social_handle", person["_tw"],     "twitter"))
    if person.get("_email")  and random.random() > 0.35:
        defs.append(("email",         person["_email"],  "email"))
    if person.get("_crypto"):
        defs.append(("crypto_wallet", person["_crypto"], "crypto"))
    if person.get("_imei"):
        defs.append(("imei",          person["_imei"],   "device"))
    return [
        {
            "id":               uid(),
            "entity_id":        entity_id,
            "alias_type":       atype,
            "alias_value":      avalue,
            "platform":         platform,
            "confidence":       round(random.uniform(0.72, 1.0), 2),
            "resolution_method":"exact",
            "is_verified":      random.random() > 0.45,
        }
        for atype, avalue, platform in defs
    ]

def rel(src, tgt, rel_type, weight=None, desc=""):
    return {
        "source_id":   src,
        "target_id":   tgt,
        "type":        rel_type,
        "weight":      weight or round(random.uniform(0.6, 1.0), 2),
        "description": desc,
    }

# ─────────────────────────────────────────────────────────────────────────────
# NETWORK BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _n(name): return f"{name[0]} {name[1]}"

class NetworkBuilder:
    """
    All network builders return:
        entities, aliases, relationships
    All entities are in the full DB-ready format.
    All aliases are ready for entity_aliases table.
    All relationships are Neo4j relationship dicts.
    """

    @staticmethod
    def hawala_network(num_hubs=1, coordinators_per_hub=4, mules_per_coordinator=8):
        """
        Hawala Hub-and-Spoke:
          Broker (1)
            └─ City Coordinator (4, one per city)
                └─ Mule Account Holders (8 each)
        Cross-connections: coordinators share same IMEI batches;
                           some mules appear in multiple city networks (overlap).
        """
        entities = []
        aliases  = []
        rels     = []

        # Shared crypto wallet for entire hawala network (single BTC cold wallet)
        shared_btc = gen_crypto("btc")

        # ── Broker ────────────────────────────────────────────────────────────
        for _h in range(num_hubs):
            broker_name  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            broker_phone = gen_phone()
            broker_upi   = gen_upi(broker_name)
            broker_tg    = gen_tg(broker_name)
            broker_email = gen_email(broker_name)
            broker_city  = random.choice(["Dubai","Karachi_equiv","Kathmandu"])  # hint
            broker_ip    = gen_ip()
            broker_imei  = gen_imei()

            broker = person_record(
                name=broker_name, phone=broker_phone, upi_id=broker_upi,
                tg=broker_tg, tw=gen_tw(broker_name), email=broker_email,
                ip=broker_ip, city=broker_city,
                risk_score=9.8, anomaly=0.97, sentiment=-0.92,
                velocity=0.95, n_conn=coordinators_per_hub * mules_per_coordinator,
                factors=[
                    "Hawala broker — hub of entire transfer network",
                    f"FT-006 matched: {coordinators_per_hub * mules_per_coordinator} direct connections",
                    "BTC cold wallet linked to UPI mule fan-out",
                ],
                crypto_wallet=shared_btc, imei=broker_imei,
                extra_meta={"role": "hawala_broker", "network": "hawala"},
            )
            entities.append(broker)
            aliases += build_aliases(broker["id"], broker)

            coordinator_ids = []
            for c in range(coordinators_per_hub):
                cname  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                ccity  = random.choice(INDIAN_CITIES)
                cip    = gen_ip(f"{random.randint(100,200)}.{random.randint(10,250)}")
                cimei  = gen_imei()
                c_btc  = gen_crypto("btc")  # secondary wallet per coordinator

                coord = person_record(
                    name=cname, phone=gen_phone(), upi_id=gen_upi(cname),
                    tg=gen_tg(cname), tw=gen_tw(cname), email=gen_email(cname),
                    ip=cip, city=ccity,
                    risk_score=round(random.uniform(8.0, 9.4), 2),
                    anomaly=round(random.uniform(0.78, 0.95), 2),
                    sentiment=round(random.uniform(-0.9, -0.6), 2),
                    velocity=round(random.uniform(0.75, 0.95), 2),
                    n_conn=mules_per_coordinator + 3,
                    factors=[
                        f"City coordinator: {ccity} hub",
                        f"FT-006: {mules_per_coordinator} mules under control",
                        "Shared IMEI with known hawala device",
                    ],
                    crypto_wallet=c_btc, imei=cimei,
                    extra_meta={"role": "hawala_coordinator", "city": ccity, "network": "hawala"},
                )
                entities.append(coord)
                aliases += build_aliases(coord["id"], coord)
                coordinator_ids.append(coord["id"])

                # Broker → Coordinator
                rels.append(rel(broker["id"], coord["id"], "CONTROLS",
                                weight=0.95, desc="Hawala broker controls city coordinator"))
                # Coordinator → Broker (bidirectional flow acknowledgement)
                rels.append(rel(coord["id"], broker["id"], "REPORTS_TO",
                                weight=0.90, desc="City coordinator reports to broker"))

                mule_ids = []
                for m in range(mules_per_coordinator):
                    mname  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                    mule_upi = gen_upi(mname)
                    # Some mules share IMEI (device sharing)
                    mimei = cimei if random.random() > 0.6 else gen_imei()

                    mule = person_record(
                        name=mname, phone=gen_phone(), upi_id=mule_upi,
                        tg=gen_tg(mname), tw=gen_tw(mname), email=gen_email(mname),
                        ip=gen_ip(cip[:cip.rfind(".")]),   # same /24 subnet as coordinator
                        city=ccity,
                        risk_score=round(random.uniform(7.0, 8.8), 2),
                        anomaly=round(random.uniform(0.65, 0.90), 2),
                        sentiment=round(random.uniform(-0.8, -0.3), 2),
                        velocity=round(random.uniform(0.70, 0.95), 2),
                        n_conn=random.randint(4, 12),
                        factors=[
                            f"Mule account: receives from {cname[:15]}",
                            "FT-001: High UPI velocity in 1-hour window",
                            f"Shared IMEI device in {ccity}",
                        ],
                        imei=mimei,
                        extra_meta={"role": "mule", "coordinator": coord["id"], "network": "hawala"},
                    )
                    entities.append(mule)
                    aliases += build_aliases(mule["id"], mule)
                    mule_ids.append(mule["id"])

                    # Coordinator → Mule
                    rels.append(rel(coord["id"], mule["id"], "CONTROLS",
                                    weight=round(random.uniform(0.78, 0.95), 2),
                                    desc="Coordinator directs mule account"))
                    # Mule → Coordinator (reverse transfer)
                    rels.append(rel(mule["id"], coord["id"], "TRANSFERS_TO",
                                    weight=round(random.uniform(0.70, 0.90), 2),
                                    desc="Mule forwards collected funds"))

                # Mule-to-mule: some cross-transfer between mules in same city
                for i in range(len(mule_ids)):
                    for j in range(i+1, len(mule_ids)):
                        if random.random() > 0.72:
                            rels.append(rel(mule_ids[i], mule_ids[j], "LINKED_TO",
                                            weight=round(random.uniform(0.45, 0.75), 2),
                                            desc="Co-located mule accounts, shared device"))

        return entities, aliases, rels

    @staticmethod
    def crypto_upi_ring(num_source_wallets=3, num_exchanges=2, num_collectors=8):
        """
        Crypto-to-UPI Layering:
          Crypto Source Wallets → Exchange Proxy Persons → UPI Collector Accounts
          All linked via shared telegram group + overlapping IPs.
        """
        entities = []
        aliases  = []
        rels     = []

        shared_tg_group = gen_tg("crypto_ring")
        shared_subnet   = f"{random.randint(100,200)}.{random.randint(10,200)}"

        # Source wallet holders
        source_ids = []
        for _ in range(num_source_wallets):
            name  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            btc   = gen_crypto("btc")
            eth   = gen_crypto("eth")
            pers  = person_record(
                name=name, phone=gen_phone(), upi_id=gen_upi(name),
                tg=shared_tg_group,    # same TG group
                tw=gen_tw(name), email=gen_email(name),
                ip=gen_ip(shared_subnet), city=random.choice(INDIAN_CITIES),
                risk_score=round(random.uniform(8.5, 9.7), 2),
                anomaly=round(random.uniform(0.82, 0.97), 2),
                sentiment=round(random.uniform(-0.9, -0.65), 2),
                velocity=round(random.uniform(0.80, 0.96), 2),
                n_conn=num_exchanges + num_collectors,
                factors=[
                    "FT-005: Crypto source node in layering network",
                    f"BTC + ETH wallets linked to {num_exchanges} exchange proxies",
                    "Negative sentiment in 9/10 recent posts",
                ],
                crypto_wallet=btc,
                extra_meta={"role": "crypto_source", "eth_wallet": eth, "network": "crypto_upi"},
            )
            entities.append(pers)
            aliases += build_aliases(pers["id"], pers)
            source_ids.append(pers["id"])

        # Exchange proxy persons (OTC dealers)
        exchange_ids = []
        for _ in range(num_exchanges):
            name  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            usdt  = gen_crypto("usdt_trc20")
            pers  = person_record(
                name=name, phone=gen_phone(), upi_id=gen_upi(name),
                tg=gen_tg(name), tw=gen_tw(name), email=gen_email(name),
                ip=gen_ip(shared_subnet),   # same subnet — co-located
                city=random.choice(INDIAN_CITIES),
                risk_score=round(random.uniform(8.0, 9.2), 2),
                anomaly=round(random.uniform(0.75, 0.92), 2),
                sentiment=round(random.uniform(-0.85, -0.55), 2),
                velocity=round(random.uniform(0.75, 0.92), 2),
                n_conn=num_source_wallets + num_collectors,
                factors=[
                    "FT-005: OTC exchange proxy in crypto-UPI chain",
                    "USDT→INR conversion via multiple UPI collector accounts",
                    "High transaction velocity 2σ above baseline",
                ],
                crypto_wallet=usdt,
                extra_meta={"role": "exchange_proxy", "network": "crypto_upi"},
            )
            entities.append(pers)
            aliases += build_aliases(pers["id"], pers)
            exchange_ids.append(pers["id"])
            for src_id in source_ids:
                rels.append(rel(src_id, pers["id"], "TRANSFERS_TO",
                                weight=round(random.uniform(0.80, 0.98), 2),
                                desc="Crypto source to exchange proxy"))

        # UPI collector accounts
        collector_ids = []
        for _ in range(num_collectors):
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            pers = person_record(
                name=name, phone=gen_phone(), upi_id=gen_upi(name),
                tg=gen_tg(name), tw=gen_tw(name), email=gen_email(name),
                ip=gen_ip(shared_subnet),
                city=random.choice(INDIAN_CITIES),
                risk_score=round(random.uniform(6.8, 8.5), 2),
                anomaly=round(random.uniform(0.60, 0.85), 2),
                sentiment=round(random.uniform(-0.7, -0.2), 2),
                velocity=round(random.uniform(0.65, 0.90), 2),
                n_conn=random.randint(3, 10),
                factors=[
                    "FT-001: UPI collector — receives from multiple OTC proxies",
                    "Transaction velocity 3σ above baseline",
                    "New account — < 30 days old, high volume",
                ],
                extra_meta={"role": "upi_collector", "network": "crypto_upi"},
            )
            entities.append(pers)
            aliases += build_aliases(pers["id"], pers)
            collector_ids.append(pers["id"])
            # Each collector linked to random exchange proxies
            for exc_id in random.sample(exchange_ids, min(2, len(exchange_ids))):
                rels.append(rel(exc_id, pers["id"], "TRANSFERS_TO",
                                weight=round(random.uniform(0.72, 0.95), 2),
                                desc="OTC proxy distributes INR to collector"))

        # Collectors sometimes transfer to each other (layering)
        for i in range(len(collector_ids)):
            for j in range(i+1, len(collector_ids)):
                if random.random() > 0.75:
                    rels.append(rel(collector_ids[i], collector_ids[j], "LINKED_TO",
                                    weight=round(random.uniform(0.40, 0.70), 2),
                                    desc="Cross-collector UPI layering"))

        return entities, aliases, rels

    @staticmethod
    def propaganda_farm(num_handlers=1, sub_handlers=5, bots_per_sub=10):
        """
        Coordinated Inauthentic Behaviour:
          Central Handler → Sub-Handlers → Bot Accounts
          All bots share same IP subnet; post within 30-min windows.
        """
        entities = []
        aliases  = []
        rels     = []

        shared_subnet = f"{random.randint(14,200)}.{random.randint(10,200)}"
        shared_imei   = gen_imei()  # handler uses one physical device for all accounts

        # Central handler
        for _ in range(num_handlers):
            hname = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            handler = person_record(
                name=hname, phone=gen_phone(), upi_id=gen_upi(hname),
                tg=gen_tg(hname), tw=gen_tw(hname), email=gen_email(hname),
                ip=gen_ip(shared_subnet), city=random.choice(INDIAN_CITIES),
                risk_score=round(random.uniform(9.0, 9.9), 2),
                anomaly=round(random.uniform(0.90, 0.99), 2),
                sentiment=round(random.uniform(-1.0, -0.85), 2),
                velocity=round(random.uniform(0.90, 0.99), 2),
                n_conn=sub_handlers * bots_per_sub,
                factors=[
                    "FT-002: Central handler of propaganda farm",
                    f"Controls {sub_handlers * bots_per_sub} coordinated accounts",
                    "Consistent negative sentiment across all posts",
                ],
                imei=shared_imei,
                extra_meta={"role": "propaganda_handler", "network": "propaganda"},
            )
            entities.append(handler)
            aliases += build_aliases(handler["id"], handler)

            sub_ids = []
            for s in range(sub_handlers):
                sname = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                sub   = person_record(
                    name=sname, phone=gen_phone(), upi_id=gen_upi(sname),
                    tg=gen_tg(sname), tw=gen_tw(sname), email=gen_email(sname),
                    ip=gen_ip(shared_subnet),
                    city=random.choice(INDIAN_CITIES),
                    risk_score=round(random.uniform(8.2, 9.1), 2),
                    anomaly=round(random.uniform(0.82, 0.95), 2),
                    sentiment=round(random.uniform(-0.95, -0.75), 2),
                    velocity=round(random.uniform(0.85, 0.98), 2),
                    n_conn=bots_per_sub + 2,
                    factors=[
                        "FT-002: Sub-handler in propaganda farm",
                        f"Controls {bots_per_sub} bot accounts in cluster",
                        "Posts timed within 15-minute windows of handler",
                    ],
                    imei=gen_imei(),
                    extra_meta={"role": "sub_handler", "network": "propaganda"},
                )
                entities.append(sub)
                aliases += build_aliases(sub["id"], sub)
                sub_ids.append(sub["id"])
                rels.append(rel(handler["id"], sub["id"], "CONTROLS",
                                weight=0.95, desc="Central handler → sub-handler"))

                # Bots under this sub-handler
                bot_ids_local = []
                for b in range(bots_per_sub):
                    bname = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                    bot   = person_record(
                        name=bname, phone=gen_phone(), upi_id=gen_upi(bname),
                        tg=gen_tg(bname), tw=gen_tw(bname), email=gen_email(bname),
                        ip=gen_ip(shared_subnet),   # all bots same /16 subnet
                        city=random.choice(INDIAN_CITIES),
                        risk_score=round(random.uniform(6.5, 8.0), 2),
                        anomaly=round(random.uniform(0.55, 0.82), 2),
                        sentiment=round(random.uniform(-0.9, -0.6), 2),
                        velocity=round(random.uniform(0.75, 0.98), 2),
                        n_conn=random.randint(2, 8),
                        factors=[
                            "FT-002: Bot account in coordinated inauthentic behaviour cluster",
                            "Post frequency > 30/hour — exceeds human baseline",
                            "Reply ratio 0.02 — pure broadcast behaviour",
                        ],
                        extra_meta={"role": "bot_account", "network": "propaganda"},
                    )
                    entities.append(bot)
                    aliases += build_aliases(bot["id"], bot)
                    bot_ids_local.append(bot["id"])
                    rels.append(rel(sub["id"], bot["id"], "CONTROLS",
                                    weight=round(random.uniform(0.78, 0.95), 2),
                                    desc="Sub-handler operates bot account"))

                # Bots know each other (same posting window co-occurrence)
                for i in range(len(bot_ids_local)):
                    for j in range(i+1, len(bot_ids_local)):
                        if random.random() > 0.60:
                            rels.append(rel(bot_ids_local[i], bot_ids_local[j], "KNOWS",
                                            weight=round(random.uniform(0.45, 0.80), 2),
                                            desc="Same posting window co-occurrence"))

            # Sub-handlers form a ring (cross-coordination)
            for i in range(len(sub_ids)):
                rels.append(rel(sub_ids[i], sub_ids[(i+1) % len(sub_ids)], "KNOWS",
                                weight=round(random.uniform(0.60, 0.88), 2),
                                desc="Sub-handlers share coordination channel"))

        return entities, aliases, rels

    @staticmethod
    def sim_swap_cluster(num_insiders=4, victims_per_insider=5):
        """
        SIM Swap Fraud:
          Telecom Insider → SIM Swapper → Mule Account chain
          Insider has verified telecom IMEI; swapper shares device; mule receives funds.
        """
        entities = []
        aliases  = []
        rels     = []

        for _ in range(num_insiders):
            iname   = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            i_imei  = gen_imei()
            i_city  = random.choice(INDIAN_CITIES)

            insider = person_record(
                name=iname, phone=gen_phone(), upi_id=gen_upi(iname),
                tg=gen_tg(iname), tw=gen_tw(iname), email=gen_email(iname),
                ip=gen_ip(), city=i_city,
                risk_score=round(random.uniform(8.8, 9.6), 2),
                anomaly=round(random.uniform(0.85, 0.97), 2),
                sentiment=round(random.uniform(-0.8, -0.6), 2),
                velocity=round(random.uniform(0.80, 0.96), 2),
                n_conn=victims_per_insider * 2,
                factors=[
                    "FT-003: Telecom insider enabling SIM swap fraud",
                    f"Linked to {victims_per_insider} SIM swap victims",
                    "Device change flag triggered on target accounts",
                ],
                imei=i_imei,
                extra_meta={"role": "telecom_insider", "network": "sim_swap"},
            )
            entities.append(insider)
            aliases += build_aliases(insider["id"], insider)

            swapper_id = None
            for v in range(victims_per_insider):
                # The actual swapper (intermediary)
                if v == 0:
                    sname   = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                    swapper = person_record(
                        name=sname, phone=gen_phone(), upi_id=gen_upi(sname),
                        tg=gen_tg(sname), tw=gen_tw(sname), email=gen_email(sname),
                        ip=gen_ip(), city=i_city,
                        risk_score=round(random.uniform(8.0, 9.0), 2),
                        anomaly=round(random.uniform(0.78, 0.93), 2),
                        sentiment=round(random.uniform(-0.75, -0.5), 2),
                        velocity=round(random.uniform(0.75, 0.92), 2),
                        n_conn=victims_per_insider,
                        factors=[
                            "FT-003: SIM swapper — executes the swap on behalf of insider",
                            f"Shared IMEI {i_imei[:8]}… with telecom insider",
                            "Transaction burst post device-change matches SIM swap pattern",
                        ],
                        imei=i_imei,   # shares device with insider
                        extra_meta={"role": "sim_swapper", "network": "sim_swap"},
                    )
                    entities.append(swapper)
                    aliases += build_aliases(swapper["id"], swapper)
                    swapper_id = swapper["id"]
                    rels.append(rel(insider["id"], swapper["id"], "KNOWS",
                                    weight=0.95, desc="Telecom insider uses swapper as executor"))

                # Mule account that receives the funds post-swap
                mname = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                mule  = person_record(
                    name=mname, phone=gen_phone(), upi_id=gen_upi(mname),
                    tg=gen_tg(mname), tw=gen_tw(mname), email=gen_email(mname),
                    ip=gen_ip(), city=random.choice(INDIAN_CITIES),
                    risk_score=round(random.uniform(6.5, 8.2), 2),
                    anomaly=round(random.uniform(0.60, 0.85), 2),
                    sentiment=round(random.uniform(-0.6, -0.1), 2),
                    velocity=round(random.uniform(0.65, 0.90), 2),
                    n_conn=random.randint(3, 8),
                    factors=[
                        "FT-003: Mule account receives SIM swap fraud proceeds",
                        "High UPI velocity immediately post device-change",
                        "Linked to swapper through transaction chain",
                    ],
                    extra_meta={"role": "mule_sim_swap", "network": "sim_swap"},
                )
                entities.append(mule)
                aliases += build_aliases(mule["id"], mule)
                if swapper_id:
                    rels.append(rel(swapper_id, mule["id"], "TRANSFERS_TO",
                                    weight=round(random.uniform(0.75, 0.92), 2),
                                    desc="Swapper transfers fraud proceeds to mule"))

        return entities, aliases, rels

    @staticmethod
    def phishing_network(num_registrants=2, domains_per_registrant=5):
        """
        Phishing Domain Network:
          Domain Registrant → Phishing Domains → Persons who clicked / victims
        """
        entities = []
        aliases  = []
        rels     = []

        for _ in range(num_registrants):
            rname = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            remail = gen_email(rname)
            rp    = person_record(
                name=rname, phone=gen_phone(), upi_id=gen_upi(rname),
                tg=gen_tg(rname), tw=gen_tw(rname), email=remail,
                ip=gen_ip(), city=random.choice(INDIAN_CITIES),
                risk_score=round(random.uniform(7.5, 9.0), 2),
                anomaly=round(random.uniform(0.70, 0.90), 2),
                sentiment=round(random.uniform(-0.8, -0.5), 2),
                velocity=round(random.uniform(0.65, 0.85), 2),
                n_conn=domains_per_registrant * 4,
                factors=[
                    "FT-004: Phishing domain registrant",
                    f"Bulk-registered {domains_per_registrant} typosquat domains in 7 days",
                    "Domains similarity ≥ 0.78 to legitimate banking portals",
                ],
                extra_meta={"role": "phishing_registrant", "network": "phishing"},
            )
            entities.append(rp)
            aliases += build_aliases(rp["id"], rp)

            for d in range(domains_per_registrant):
                seed   = random.choice(LEGIT_DOMAINS)
                domain = gen_phishing_domain(seed)
                domain_entity = {
                    "id":                 uid(),
                    "entity_type":        "website",
                    "primary_identifier": domain,
                    "display_name":       domain,
                    "risk_score":         round(random.uniform(7.0, 9.2), 2),
                    "risk_level":         "high",
                    "influence_score":    round(random.uniform(0.1, 0.5), 4),
                    "anomaly_score":      round(random.uniform(0.65, 0.92), 4),
                    "sentiment_avg":      round(random.uniform(-0.8, -0.4), 4),
                    "event_count":        random.randint(10, 200),
                    "first_seen":         rand_dt(1, 30).isoformat(),
                    "last_seen":          rand_dt(0, 5).isoformat(),
                    "is_flagged":         True,
                    "investigation_notes":None,
                    "risk_factors": [
                        f"Domain similarity {round(random.uniform(0.75,0.95),2)} to {seed}.co.in",
                        f"Registered {random.randint(1,15)} days ago — newly active",
                        "Used in active phishing campaign targeting bank customers",
                    ],
                    "metadata_": {
                        "registrant_entity_id": rp["id"],
                        "spoofed_brand": seed,
                        "domain_age_days": random.randint(1, 15),
                        "network": "phishing",
                    },
                    "_phone": None, "_upi": None, "_tg": None, "_tw": None,
                    "_email": None, "_ip": None, "_city": None,
                    "_crypto": None, "_imei": None,
                }
                entities.append(domain_entity)
                rels.append(rel(rp["id"], domain_entity["id"], "OPERATES",
                                weight=round(random.uniform(0.85, 0.99), 2),
                                desc=f"Registrant operates phishing domain {domain}"))

                # Add some victim-like persons who "clicked" (associated IP)
                for _ in range(random.randint(2, 5)):
                    vname  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                    victim = person_record(
                        name=vname, phone=gen_phone(), upi_id=gen_upi(vname),
                        tg=gen_tg(vname), tw=gen_tw(vname), email=gen_email(vname),
                        ip=gen_ip(), city=random.choice(INDIAN_CITIES),
                        risk_score=round(random.uniform(3.0, 6.0), 2),
                        anomaly=round(random.uniform(0.20, 0.55), 2),
                        sentiment=round(random.uniform(-0.4, 0.2), 2),
                        velocity=round(random.uniform(0.10, 0.45), 2),
                        n_conn=random.randint(1, 5),
                        factors=[
                            "Potential phishing victim — IP visited spoofed domain",
                            "OTP harvesting attempt logged from device",
                        ],
                        extra_meta={"role": "phishing_victim", "domain": domain, "network": "phishing"},
                    )
                    entities.append(victim)
                    aliases += build_aliases(victim["id"], victim)
                    rels.append(rel(domain_entity["id"], victim["id"], "LINKED_TO",
                                    weight=round(random.uniform(0.40, 0.70), 2),
                                    desc="Victim IP visited phishing domain"))

        return entities, aliases, rels


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT GENERATORS (realistic threat events per scenario)
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_TEMPLATES = {
    "hawala": [
        "रात को 11 बजे transfer करना है। {amount}L ready है। {city} वाले से संपर्क करो। @{handle}",
        "Hawala route confirmed. {city} → Dubai. Rate: {rate}/USD. Contact {phone}.",
        "भाई, {amount} हजार की हवाला आज भेजनी है। {city} agent ready है।",
        "Routing update: all cash to {city} point. New UPI: {upi}. Old burned.",
        "Coordinator confirmed receipt of ₹{amount}L. Proceed to next node.",
        "Emergency: switch to backup UPI {upi}. Previous account flagged by bank.",
        "आज रात {amount} lakh की transaction है। IMEI change कर लो पहले।",
    ],
    "crypto_upi": [
        "USDT received. Converting to INR via OTC. Splitting to {count} accounts.",
        "BTC cold wallet balance: {amount} BTC. Send to exchange: {wallet}",
        "UPI cashout complete. ₹{amount}L distributed to {count} accounts in {city}.",
        "ETH → USDT → INR chain operational. {count} txns in last {hrs}h.",
        "Collector account {upi} flagged. Burn and create new with {phone}.",
        "P2P OTC dealer in {city} confirmed. Rate: {rate}. Proceed.",
        "Transaction velocity trigger avoided. Splitting ₹{amount} across {count} UPIs.",
    ],
    "propaganda": [
        "भारत को जगाओ! सरकार यह सच्चाई छुपा रही है। {keyword}. सभी groups में share करो।",
        "BREAKING: {keyword} exposed! RT immediately before deletion. #WakeUpIndia",
        "They don't want you to know: {keyword} is real. Thread 🧵 [1/{count}]",
        "Forward to all: {keyword} operation active in {city}. Stay alert. #India",
        "सच्चाई: {keyword} का षड्यंत्र! सरकार मीडिया से दबा रही है। Share करो!",
        "Verified intel: {keyword} confirmed by independent source. Mainstream media silent.",
        "आज रात {city} में {keyword} घटना होगी। सभी को बताओ। Forward करो!",
        "Bot wave activated: push {keyword} narrative to 50K+ accounts by 0200h.",
    ],
    "sim_swap": [
        "SIM port request processed for {phone}. New SIM active in {city}.",
        "Target {phone} OTP intercepted. Proceeding to UPI access.",
        "Device fingerprint changed for account {upi}. Transaction window: 2 hours.",
        "SIM swap successful. Bank OTP received. Initiating transfer of ₹{amount}.",
        "Insider confirmed: {phone} number ported to our SIM. Ready for cash-out.",
        "{city} telecom employee confirmed cooperation. {count} numbers ready.",
        "Victim {phone} has ₹{amount}L in account. Swap in progress.",
    ],
    "phishing": [
        "Your SBI account has been suspended. Verify immediately: http://{domain}",
        "URGENT: Your HDFC UPI is blocked. Re-activate now: https://{domain}",
        "Income Tax refund of ₹{amount} pending. Claim: {domain}",
        "आपका account block हो गया है। अभी verify करें: {domain}",
        "IRCTC booking failed. Update payment details: https://{domain}",
        "Your Aadhaar linked mobile needs verification. Visit: {domain}",
        "EPF withdrawal request pending. Confirm via: https://{domain}",
    ],
    "general_threat": [
        "Cybercrime unit arrests {city} man for running UPI mule account network worth ₹{amount}Cr",
        "ED raids hawala operator in {city}; seizes ₹{amount}L in cash and crypto",
        "Police bust SIM swap fraud ring from {city}; {count} arrested",
        "Intelligence agencies flag coordinated disinformation ahead of elections",
        "{city} court sentences hawala agent to {count} years for terror financing",
        "National Cyber Security advisory: {keyword} phishing campaign targeting bank customers",
        "Threat intel bulletin flags server at {ip} used in coordinated campaign",
    ],
}

def gen_event_content(scenario: str, person: dict) -> str:
    templates = CONTENT_TEMPLATES.get(scenario, CONTENT_TEMPLATES["general_threat"])
    tmpl = random.choice(templates)
    return tmpl.format(
        amount=random.randint(1, 500),
        city=person.get("_city") or random.choice(INDIAN_CITIES),
        phone=person.get("_phone") or gen_phone(),
        handle=(person.get("_tg") or "@anon").lstrip("@"),
        upi=person.get("_upi") or gen_upi("temp"),
        wallet=person.get("_crypto") or gen_crypto(),
        keyword=random.choice(THREAT_KEYWORDS),
        count=random.randint(2, 50),
        hrs=random.randint(1, 12),
        rate=round(random.uniform(82, 88), 2),
        domain=gen_phishing_domain(),
        ip=person.get("_ip") or gen_ip(),
    )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_all(
    num_standalone_persons: int = 60,
    events_per_person: int = 6,
    num_alerts: int = 80,
) -> dict:
    print("🔄 ILA Advanced Mock Data Generator v2")
    print("=" * 56)

    # ── 1. Sources ────────────────────────────────────────────────────────────
    sources = [
        {"id": uid(), "name": "Mock Telegram Channel Feed",
         "source_type": "telegram_public", "tier": "tier_3", "url": "mock://telegram",
         "description": "Simulated Telegram public channel data", "is_active": True,
         "reliability_multiplier": 0.7, "crawl_interval_minutes": 5,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
        {"id": uid(), "name": "Mock UPI Transaction Stream",
         "source_type": "upi_transaction", "tier": "tier_2", "url": "mock://upi",
         "description": "Simulated UPI transaction alerts", "is_active": True,
         "reliability_multiplier": 1.0, "crawl_interval_minutes": 1,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
        {"id": uid(), "name": "Mock Twitter/X Threat Feed",
         "source_type": "twitter_x", "tier": "tier_3", "url": "mock://twitter",
         "description": "Simulated Twitter/X posts", "is_active": True,
         "reliability_multiplier": 0.7, "crawl_interval_minutes": 10,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
        {"id": uid(), "name": "NDTV RSS Feed",
         "source_type": "rss_news", "tier": "tier_1",
         "url": "https://feeds.feedburner.com/ndtvnews-india-news",
         "description": "NDTV India News RSS", "is_active": True,
         "reliability_multiplier": 1.5, "crawl_interval_minutes": 15,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
        {"id": uid(), "name": "Mock Dark Web Forum",
         "source_type": "dark_web", "tier": "tier_4", "url": "mock://darkweb",
         "description": "Simulated dark web forum posts", "is_active": True,
         "reliability_multiplier": 0.3, "crawl_interval_minutes": 60,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
        {"id": uid(), "name": "ANI News RSS",
         "source_type": "rss_news", "tier": "tier_1", "url": "https://aninews.in/rss/",
         "description": "ANI News RSS", "is_active": True,
         "reliability_multiplier": 1.5, "crawl_interval_minutes": 15,
         "last_crawled_at": NOW.isoformat(), "event_count_today": 0},
    ]
    source_ids = [s["id"] for s in sources]

    # ── 2. Users ──────────────────────────────────────────────────────────────
    HASHED_PW = "$pbkdf2-sha256$29000$b82Zs5YyBkAoZey9V0oppQ$lNT/5DHUKHkuEul5myB0.Wtfv1tG6s7i0VMC.6JSvM0"
    users = [
        {"id": uid(), "username": "analyst_demo",   "email": "analyst@aiila.in",
         "hashed_password": HASHED_PW, "full_name": "Demo Analyst",     "role": "analyst",    "is_active": True},
        {"id": uid(), "username": "commander_01",   "email": "commander@aiila.in",
         "hashed_password": HASHED_PW, "full_name": "Senior Commander", "role": "commander",  "is_active": True},
        {"id": uid(), "username": "specialist_fraud","email": "specialist@aiila.in",
         "hashed_password": HASHED_PW, "full_name": "Fraud Specialist", "role": "specialist", "is_active": True},
        {"id": uid(), "username": "geetanjali",      "email": "geetanjali@aiila.in",
         "hashed_password": HASHED_PW, "full_name": "Geetanjali",       "role": "analyst",    "is_active": True},
        {"id": uid(), "username": "mythresh",        "email": "mythresh@aiila.in",
         "hashed_password": HASHED_PW, "full_name": "Mythresh",         "role": "analyst",    "is_active": True},
    ]

    # ── 3. Keywords ───────────────────────────────────────────────────────────
    keyword_defs = {
        "financial_fraud": ["hawala","hundi","mule account","UPI scam","SIM swap",
                            "money laundering","crypto fraud","QR scam","OTP fraud",
                            "transfer now","account verify","layering"],
        "terrorism":       ["IED","LeT","ISI","explosives","weapons cache",
                            "terror financing","RDX","militant","sleeper cell"],
        "propaganda":      ["disinformation","fake news","deepfake","psyops",
                            "coordinated inauthentic","bot network","troll farm","viral campaign"],
        "narcotics":       ["narcotics","drug trafficking","smuggling","contraband",
                            "heroin","methamphetamine","dark market"],
        "cybercrime":      ["phishing","ransomware","darkweb","data breach",
                            "malware","hacking","credential theft","OTP intercept"],
        "hindi_threats":   ["हवाला","पैसे भेजो","OTP share करो","अकाउंट बंद",
                            "तुरंत verify करें","धमकी","आतंकवाद"],
    }
    keywords = []
    for cat, words in keyword_defs.items():
        for w in words:
            lang = "hi" if any(ord(c) > 127 for c in w) else "en"
            keywords.append({"id": uid(), "word": w, "category": cat, "language": lang,
                              "is_active": True, "match_count": random.randint(0, 200)})

    # ── 4. Build threat networks ───────────────────────────────────────────────
    print("  Building Hawala Hub-and-Spoke network...")
    h_ents, h_aliases, h_rels = NetworkBuilder.hawala_network(
        num_hubs=1, coordinators_per_hub=4, mules_per_coordinator=8)

    print("  Building Crypto-to-UPI Layering ring...")
    c_ents, c_aliases, c_rels = NetworkBuilder.crypto_upi_ring(
        num_source_wallets=3, num_exchanges=2, num_collectors=8)

    print("  Building Propaganda Farm...")
    p_ents, p_aliases, p_rels = NetworkBuilder.propaganda_farm(
        num_handlers=1, sub_handlers=4, bots_per_sub=8)

    print("  Building SIM Swap Cluster...")
    s_ents, s_aliases, s_rels = NetworkBuilder.sim_swap_cluster(
        num_insiders=3, victims_per_insider=5)

    print("  Building Phishing Domain Network...")
    ph_ents, ph_aliases, ph_rels = NetworkBuilder.phishing_network(
        num_registrants=2, domains_per_registrant=4)

    # ── 5. Standalone persons (general population — various risk levels) ──────
    print(f"  Generating {num_standalone_persons} standalone persons...")
    sa_ents, sa_aliases, sa_rels = [], [], []

    # Explicitly add "Mythresh" as a person entity
    mythresh_name = "Mythresh"
    mythresh_pers = person_record(
        name=mythresh_name,
        phone=gen_phone(),
        upi_id=gen_upi(mythresh_name),
        tg=gen_tg(mythresh_name),
        tw=gen_tw(mythresh_name),
        email="mythresh@aiila.in",
        ip=gen_ip(),
        city="Bengaluru",
        risk_score=4.5,
        anomaly=0.3,
        sentiment=0.1,
        velocity=0.2,
        n_conn=5,
        factors=["Associated analyst account matches system user profile"],
        extra_meta={"role": "analyst_entity", "risk_profile": "medium"}
    )
    sa_ents.append(mythresh_pers)
    sa_aliases += build_aliases(mythresh_pers["id"], mythresh_pers)

    for i in range(num_standalone_persons):
        name  = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        city  = random.choice(INDIAN_CITIES)
        ip    = gen_ip()
        rp    = random.choices(["low","medium","high","critical"], weights=[40,30,20,10])[0]
        anom  = {"low":0.10,"medium":0.35,"high":0.65,"critical":0.88}[rp]
        pat   = {"low":0.05,"medium":0.25,"high":0.60,"critical":0.90}[rp]
        vel   = random.uniform(0, {"low":0.2,"medium":0.5,"high":0.75,"critical":0.95}[rp])
        sent  = random.uniform(-1.0, {"low":0.3,"medium":0.0,"high":-0.4,"critical":-0.8}[rp])
        nconn = {"low":2,"medium":7,"high":14,"critical":24}[rp] + random.randint(0,5)
        mult  = random.choice([0.7, 1.0, 1.0, 1.5])
        score = composite_risk(anom, pat, nconn, vel, sent, mult)
        factors = []
        if anom > 0.5:
            factors.append(f"Transaction velocity anomaly: {random.randint(10,47)} txns in {random.randint(1,6)}h")
        if pat > 0.4:
            factors.append(f"Matched {random.choice(FRAUD_PATTERNS)}")
        if nconn > 10:
            factors.append(f"High network centrality: {nconn} direct connections")
        if sent < -0.4:
            factors.append(f"Negative sentiment in {random.randint(5,15)} recent posts")

        crypto_w = gen_crypto() if random.random() > 0.85 else None
        imei_v   = gen_imei()   if random.random() > 0.70 else None
        pers = person_record(
            name=name, phone=gen_phone(), upi_id=gen_upi(name),
            tg=gen_tg(name), tw=gen_tw(name), email=gen_email(name),
            ip=ip, city=city, risk_score=score,
            anomaly=anom, sentiment=sent, velocity=vel, n_conn=nconn,
            factors=factors[:3], crypto_wallet=crypto_w, imei=imei_v,
            extra_meta={"risk_profile": rp},
        )
        sa_ents.append(pers)
        sa_aliases += build_aliases(pers["id"], pers)

        # City-based KNOWS relationships
        if i > 5 and random.random() > 0.55:
            city_peers = [e for e in sa_ents[:-1] if e.get("metadata_",{}).get("city") == city]
            if city_peers:
                peer = random.choice(city_peers)
                sa_rels.append(rel(pers["id"], peer["id"], "KNOWS",
                                   weight=round(random.uniform(0.30, 0.75), 2),
                                   desc=f"Same-city co-occurrence in {city}"))

        # Name-cluster KNOWS (same surname → family / community link)
        if i > 10 and random.random() > 0.70:
            surname = name.split()[-1]
            name_peers = [e for e in sa_ents[:-1] if e["primary_identifier"].endswith(surname)]
            if name_peers:
                peer = random.choice(name_peers)
                sa_rels.append(rel(pers["id"], peer["id"], "KNOWS",
                                   weight=round(random.uniform(0.55, 0.85), 2),
                                   desc=f"Family name cluster — shared surname: {surname}"))

    # ── Merge all entities, aliases, relationships ─────────────────────────────
    all_entities: list = h_ents + c_ents + p_ents + s_ents + ph_ents + sa_ents
    all_aliases:  list = h_aliases + c_aliases + p_aliases + s_aliases + ph_aliases + sa_aliases
    all_rels:     list = h_rels + c_rels + p_rels + s_rels + ph_rels + sa_rels

    # Cross-network KNOWS: some hawala mules overlap with crypto collectors
    mule_ids  = [e["id"] for e in h_ents if e.get("metadata_",{}).get("role") == "mule"]
    coll_ids  = [e["id"] for e in c_ents if e.get("metadata_",{}).get("role") == "upi_collector"]
    for mid in random.sample(mule_ids, min(4, len(mule_ids))):
        for cid in random.sample(coll_ids, min(2, len(coll_ids))):
            all_rels.append(rel(mid, cid, "LINKED_TO",
                                weight=round(random.uniform(0.55, 0.80), 2),
                                desc="Shared UPI account across hawala + crypto networks"))

    # Cross-network: propaganda bots amplify phishing content
    bot_ids  = [e["id"] for e in p_ents if e.get("metadata_",{}).get("role") == "bot_account"]
    phish_ids= [e["id"] for e in ph_ents if e.get("entity_type") == "website"]
    for bid in random.sample(bot_ids, min(6, len(bot_ids))):
        if phish_ids:
            all_rels.append(rel(bid, random.choice(phish_ids), "LINKED_TO",
                                weight=round(random.uniform(0.45, 0.72), 2),
                                desc="Bot account amplified phishing domain links"))

    print(f"  Total entities: {len(all_entities)}")
    print(f"  Total aliases:  {len(all_aliases)}")
    print(f"  Total rels:     {len(all_rels)}")

    # ── 6. Add standalone non-person entities to reach richer graph ────────────
    # Additional UPI / phone / crypto entities not linked to a specific person
    print("  Generating additional standalone identifier entities...")
    standalone_ids = []
    for etype, count, gen_fn in [
        ("phone",         40, lambda: gen_phone()),
        ("telegram",      30, lambda: gen_tg()),
        ("upi_account",   25, lambda: gen_upi(fake.name())),
        ("email",         15, lambda: gen_email(fake.name())),
        ("social_handle", 10, lambda: gen_tw()),
        ("crypto_wallet", 10, lambda: gen_crypto()),
        ("imei",           5, lambda: gen_imei()),
    ]:
        for _ in range(count):
            ident = gen_fn()
            rs    = round(random.uniform(0, 10), 2)
            eid   = uid()
            all_entities.append({
                "id": eid, "entity_type": etype,
                "primary_identifier": ident, "display_name": ident,
                "risk_score": rs, "risk_level": risk_level(rs),
                "influence_score": round(random.uniform(0, 0.4), 4),
                "anomaly_score":   round(random.uniform(0, 1), 4),
                "sentiment_avg":   round(random.uniform(-1, 1), 4),
                "event_count":     random.randint(0, 60),
                "first_seen": rand_dt(1, 90).isoformat(),
                "last_seen":  rand_dt(0, 48).isoformat(),
                "is_flagged": rs >= 6.5,
                "investigation_notes": None,
                "risk_factors": [],
                "metadata_": {},
                "_phone": None, "_upi": None, "_tg": None, "_tw": None,
                "_email": None, "_ip": None, "_city": None,
                "_crypto": None, "_imei": None,
            })
            standalone_ids.append(eid)

    # Link some standalone entities to existing persons
    person_ents = [e for e in all_entities if e["entity_type"] == "person"]
    for sid in random.sample(standalone_ids, min(30, len(standalone_ids))):
        if person_ents:
            target = random.choice(person_ents)
            all_rels.append(rel(target["id"], sid, "OWNS",
                                weight=round(random.uniform(0.6, 0.95), 2),
                                desc="Person owns identifier"))
            # Also add to aliases for this person
            s_ent = next(e for e in all_entities if e["id"] == sid)
            all_aliases.append({
                "id": uid(), "entity_id": target["id"],
                "alias_type": s_ent["entity_type"],
                "alias_value": s_ent["primary_identifier"],
                "platform": s_ent["entity_type"],
                "confidence": round(random.uniform(0.60, 0.90), 2),
                "resolution_method": "graph",
                "is_verified": False,
            })

    # ── 7. Raw Events ──────────────────────────────────────────────────────────
    print(f"  Generating events ({events_per_person} per person × {len(person_ents)} persons)...")
    events = []
    platforms = ["telegram","twitter","upi_transaction","rss_news","dark_web"]
    plat_weights = [35, 25, 20, 15, 5]

    # Map network roles to content scenarios
    ROLE_SCENARIO = {
        "hawala_broker":       "hawala",
        "hawala_coordinator":  "hawala",
        "mule":                "hawala",
        "crypto_source":       "crypto_upi",
        "exchange_proxy":      "crypto_upi",
        "upi_collector":       "crypto_upi",
        "propaganda_handler":  "propaganda",
        "sub_handler":         "propaganda",
        "bot_account":         "propaganda",
        "telecom_insider":     "sim_swap",
        "sim_swapper":         "sim_swap",
        "mule_sim_swap":       "sim_swap",
        "phishing_registrant": "phishing",
        "phishing_victim":     "phishing",
    }

    kw_ids = [k["id"] for k in keywords]

    for person in person_ents:
        role     = person.get("metadata_", {}).get("role", "")
        scenario = ROLE_SCENARIO.get(role, "general_threat")
        n_events = events_per_person + (3 if person["risk_score"] >= 7 else 0)

        for _ in range(n_events):
            plat = random.choices(platforms, weights=plat_weights)[0]
            pub  = rand_dt(0, 60)
            cont = gen_event_content(scenario, person)
            lang = random.choices(
                ["en","hi","ur","bn","ta","te","mr"],
                weights=[40,30,10,5,5,5,5]
            )[0]

            extracted = []
            if person.get("_phone"):
                extracted.append({"type":"phone","value":person["_phone"],"confidence":0.95})
            if person.get("_ip"):
                extracted.append({"type":"ip_address","value":person["_ip"],"confidence":0.90})
            if person.get("_tg") and plat == "telegram":
                extracted.append({"type":"telegram","value":person["_tg"],"confidence":0.88})
            if person.get("_upi") and random.random() > 0.5:
                extracted.append({"type":"upi_account","value":person["_upi"],"confidence":0.85})
            if person.get("_crypto") and random.random() > 0.7:
                extracted.append({"type":"crypto_wallet","value":person["_crypto"],"confidence":0.82})
            if person.get("_email") and random.random() > 0.75:
                extracted.append({"type":"email","value":person["_email"],"confidence":0.87})

            matched_kw = [k for k in keywords if k["word"].lower() in cont.lower()]

            events.append({
                "id":               uid(),
                "source_id":        random.choice(source_ids),
                "external_id":      f"{plat}_{random.randint(100000,999999)}",
                "content":          cont,
                "content_language": lang,
                "translated_content": cont if lang == "en" else f"[TRANSLATED] {cont}",
                "url":              f"https://{plat}.example.com/post/{random.randint(100000,999999)}",
                "author_handle":    person.get("_tg") if plat == "telegram" else person.get("_tw"),
                "platform":         plat,
                "published_at":     pub.isoformat(),
                "is_processed":     True,
                "is_duplicate":     False,
                "duplicate_of":     None,
                "extracted_entities": extracted,
                "sentiment_score":  round(person["sentiment_avg"] + random.uniform(-0.15,0.15), 4),
                "anomaly_score":    round(person["anomaly_score"]  + random.uniform(-0.05,0.05), 4),
                "matched_keywords": [k["id"] for k in matched_kw[:3]],
                "metadata_": {
                    "city_inferred":   person.get("_city"),
                    "platform_specific": {},
                },
                "_person_entity_id": person["id"],
                "_scenario":         scenario,
            })

    print(f"  Total events: {len(events)}")

    # ── 8. Risk Alerts ────────────────────────────────────────────────────────
    print(f"  Generating {num_alerts} risk alerts...")
    flagged = [e for e in all_entities if e.get("is_flagged")]
    flagged.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    alert_pool = flagged[:num_alerts]

    ALERT_TITLE_TEMPLATES = [
        "High-velocity UPI transactions: {entity} — {count} txns in {hrs}h",
        "Coordinated inauthentic behaviour: {count} accounts posting identical content",
        "Keyword '{kw}' matched in {platform} post by {entity}",
        "Anomaly detected: {entity} transaction velocity 3σ above baseline",
        "Mule account network: {entity} — {count}-hop graph cluster",
        "Hawala network node: {entity} linked to {count} intermediaries",
        "SIM swap fraud pattern: {entity} matches FT-003",
        "Propaganda cluster: {count} bot accounts amplifying narrative",
        "Cross-platform identity: {entity} active on {count} platforms",
        "Dark web mention: {entity} found in marketplace listing",
        "Phishing domain cluster: {entity} registered {count} typosquat domains",
        "Crypto-UPI layering: {entity} converted {count} BTC to INR via mule chain",
    ]

    alerts = []
    seen_entity_alerts: dict = defaultdict(int)

    for ent in alert_pool:
        if seen_entity_alerts[ent["id"]] >= 3:
            continue

        rs   = ent.get("risk_score", 5.0)
        role = ent.get("metadata_",{}).get("role", "")
        network = ent.get("metadata_",{}).get("network", "")

        # Determine alert type from network
        atype_map = {
            "hawala":     "financial_fraud",
            "crypto_upi": "financial_fraud",
            "propaganda": "coordinated_inauthentic",
            "sim_swap":   "sim_swap",
            "phishing":   "phishing",
        }
        atype = atype_map.get(network) or random.choices(
            ["financial_fraud","coordinated_inauthentic","keyword_match",
             "anomaly_detected","network_cluster","propaganda","phishing","sim_swap"],
            weights=[25, 20, 15, 15, 10, 7, 5, 3]
        )[0]

        pattern = random.choice(FRAUD_PATTERNS) if rs >= 7 else None
        ent_events = [e for e in events if e.get("_person_entity_id") == ent["id"]]
        trigger_id = ent_events[0]["id"] if ent_events else None

        tmpl  = random.choice(ALERT_TITLE_TEMPLATES)
        title = tmpl.format(
            entity   = ent["primary_identifier"][:30],
            count    = random.randint(3, 30),
            hrs      = random.randint(1, 12),
            kw       = random.choice(THREAT_KEYWORDS),
            platform = random.choice(["Telegram","Twitter"]),
        )

        hrs_ago = max(1, int((10 - rs) * 10))
        created = dt_ago(hours=hrs_ago + random.randint(0, 4))

        status = random.choices(
            ["new","under_review","confirmed","dismissed"],
            weights=[55, 25, 12, 8]
        )[0]

        alerts.append({
            "id": uid(), "entity_id": ent["id"], "alert_type": atype,
            "title": title[:500],
            "description": (
                f"Automated analysis flagged {ent['primary_identifier']} "
                f"based on behavioural patterns and network connections. "
                f"Risk score: {rs}/10. Network role: {role or 'unknown'}. "
                f"Pattern: {pattern or 'N/A'}."
            ),
            "risk_score":    rs,
            "risk_level":    ent.get("risk_level","low"),
            "status":        status,
            "trigger_event_id": trigger_id,
            "matched_pattern":  pattern,
            "risk_factors":     ent.get("risk_factors", []),
            "evidence_data": {
                "network_role":    role,
                "network":         network,
                "city_inferred":   ent.get("metadata_",{}).get("city","Unknown"),
                "event_count":     ent.get("event_count", 0),
            },
            "reviewed_by":  None,
            "reviewed_at":  None,
            "analyst_note": None,
            "created_at":   created.isoformat(),
        })
        seen_entity_alerts[ent["id"]] += 1

    alerts.sort(key=lambda a: a["risk_score"], reverse=True)
    print(f"  Total alerts: {len(alerts)}")

    # ── Clean up runtime-only fields before serialisation ─────────────────────
    for e in all_entities:
        for k in ["_phone","_upi","_tg","_tw","_email","_ip","_city","_crypto","_imei"]:
            e.pop(k, None)

    return {
        "meta": {
            "generated_at": NOW.isoformat(),
            "version": "2.0",
            "networks": ["hawala","crypto_upi","propaganda","sim_swap","phishing"],
            "counts": {
                "sources":       len(sources),
                "users":         len(users),
                "keywords":      len(keywords),
                "entities":      len(all_entities),
                "aliases":       len(all_aliases),
                "events":        len(events),
                "alerts":        len(alerts),
                "relationships": len(all_rels),
            }
        },
        "sources":       sources,
        "users":         users,
        "keywords":      keywords,
        "entities":      all_entities,
        "aliases":       all_aliases,
        "events":        events,
        "alerts":        alerts,
        "relationships": all_rels,
    }


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os

    output_path = os.path.join(os.path.dirname(__file__), "mock_data.json")

    data = generate_all(
        num_standalone_persons=60,
        events_per_person=6,
        num_alerts=80,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print("\n✅ Mock data generated!")
    print(f"   📁 Output: {output_path}")
    for k, v in data["meta"]["counts"].items():
        print(f"   {k:16s}: {v:>6}")
    print(f"\n   File size: {os.path.getsize(output_path) / 1024:.1f} KB")
    print("\n▶️  Next: python scripts/load_into_postgres.py")
    print("▶️  Then: python scripts/load_neo4j.py")
