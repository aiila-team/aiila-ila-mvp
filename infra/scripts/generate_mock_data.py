"""
ILA — Mock Data Generator
scripts/generate_mock_data.py

Generates realistic Indian threat scenario data:
  - 500 entities (persons, phones, Telegram handles, UPI IDs, emails, Twitter handles)
  - 1000 raw events (posts, transactions, news articles)
  - 50 risk alerts (pre-scored, realistic)

This script generates a JSON file. A separate loader (load_into_postgres.py)
reads that JSON and inserts into the database.

Why separate? So you can inspect the data before inserting, regenerate without
hitting the DB, and use the same data for testing.

Usage:
  python scripts/generate_mock_data.py
  → Outputs: scripts/mock_data.json

Requires: pip install faker
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from faker import Faker

# Initialize Faker with Indian locale
fake = Faker("en_IN")
Faker.seed(42)        # reproducible results — same seed = same data every run
random.seed(42)

# ─── Indian-specific data pools ───────────────────────────────────────────────
# These are fictional names, numbers, and handles — NOT real people

INDIAN_FIRST_NAMES = [
    "Ravi", "Amit", "Suresh", "Rahul", "Vikram", "Arjun", "Kiran", "Priya",
    "Deepak", "Sanjay", "Arun", "Manoj", "Rakesh", "Sunita", "Kavita", "Pooja",
    "Rajesh", "Mohan", "Ganesh", "Shankar", "Ramesh", "Dinesh", "Naresh", "Sunil",
    "Pavan", "Harish", "Mahesh", "Santosh", "Vijay", "Ajay", "Akash", "Rohit",
    "Nikhil", "Ankit", "Vishal", "Gaurav", "Sachin", "Manish", "Aakash", "Varun",
    "Abdul", "Mohammad", "Ali", "Ibrahim", "Hassan", "Imran", "Farhan", "Zaid",
    "Gurpreet", "Harpreet", "Jaswant", "Kulwant", "Balwant", "Manpreet", "Navpreet",
    "Aarav", "Ishaan", "Shiva", "Kartik", "Pranav", "Yash", "Harsh", "Dev",
    "Fatima", "Aisha", "Zara", "Noor", "Sana", "Ruhi", "Meher", "Afrin",
    "Lakshmi", "Saraswati", "Parvati", "Durga", "Ananya", "Divya", "Sneha", "Neha"
]

INDIAN_LAST_NAMES = [
    "Kumar", "Singh", "Sharma", "Verma", "Gupta", "Patel", "Shah", "Mehta",
    "Joshi", "Pandey", "Mishra", "Tiwari", "Yadav", "Chauhan", "Rajput",
    "Agarwal", "Bansal", "Goel", "Mittal", "Jain", "Malhotra", "Kapoor",
    "Bose", "Chatterjee", "Mukherjee", "Ghosh", "Das", "Dey", "Roy", "Sen",
    "Khan", "Sheikh", "Ansari", "Siddiqui", "Qureshi", "Malik", "Mirza",
    "Reddy", "Rao", "Naidu", "Pillai", "Nair", "Menon", "Iyer", "Krishnan",
    "Thakur", "Saxena", "Srivastava", "Shukla", "Dubey", "Tripathi", "Bajpai"
]

TELECOM_OPERATORS = {
    # prefix → operator name (fictional but realistic format)
    "70": "Jio",  "71": "Jio",  "72": "Jio",  "73": "Jio",
    "74": "Airtel", "75": "Airtel", "76": "Airtel",
    "77": "Vi",   "78": "Vi",   "79": "Vi",
    "80": "BSNL", "81": "BSNL",
    "90": "Jio",  "91": "Airtel", "94": "Vi",   "98": "Airtel",
    "99": "Jio",  "88": "Airtel", "87": "Vi",   "86": "Jio",
    "85": "Airtel", "83": "Jio",  "82": "Vi",
}

UPI_HANDLES = ["@okaxis", "@okhdfcbank", "@okicici", "@oksbi", "@ybl", "@ibl",
               "@paytm", "@axl", "@hdfcbank", "@upi", "@apl", "@boi"]

TELEGRAM_PREFIXES = [
    "india_news", "truth_india", "wake_up_bharat", "real_news", "expose_",
    "breaking_", "alert_", "india_", "bharat_", "desh_", "sach_",
    "security_watch", "cyber_india", "fraud_alert", "scam_buster",
    "terror_watch", "naxal_", "isi_expose", "anti_india_", "pak_",
    "hawala_", "crypto_india", "dark_", "anon_", "secret_"
]

THREAT_KEYWORDS = [
    "hawala", "hundi", "terrorist", "IED", "naxal", "LeT", "ISI",
    "black money", "mule account", "SIM swap", "phishing", "crypto",
    "fake news", "propaganda", "disinformation", "deepfake",
    "arms", "ammunition", "weapons", "explosives", "RDX",
    "separatist", "militancy", "insurgency", "radicalize",
    "darkweb", "tor", "bitcoin", "USDT", "hawala transfer"
]

FRAUD_PATTERNS = [
    "Crypto-to-UPI Layering Network",
    "SIM Swap Fraud Ring",
    "Coordinated Inauthentic Behavior",
    "Phishing Domain Cluster",
    "Mule Account Velocity Pattern",
    "Hawala Transfer Network",
    "QR Code Scam Ring",
    "OTP Fraud Network",
    "Loan Scam Cluster",
    "Investment Fraud Pyramid",
]

ALERT_TITLE_TEMPLATES = [
    "High-velocity UPI transactions detected: {entity} — {count} txns in {hrs}h",
    "Coordinated inauthentic behavior: {count} accounts posting identical content",
    "Keyword '{kw}' matched in {platform} post by {entity}",
    "Anomaly detected: {entity} transaction velocity 3σ above baseline",
    "Mule account network identified: {count}-hop graph cluster",
    "Suspected hawala network: {entity} linked to {count} intermediary accounts",
    "SIM swap fraud pattern: {entity} matches Template #7",
    "Propaganda cluster: {count} accounts amplifying identical narrative",
    "Cross-platform identity confirmed: {entity} active on {count} platforms",
    "Dark web mention: {entity} found in marketplace listing",
]

# Platform-appropriate content templates
PLATFORM_CONTENT = {
    "telegram": [
        "भारत को जगाओ! सरकार हमसे सच्चाई छुपा रही है। आज रात 10 बजे लाइव आओ। {keyword}",
        "Breaking: Major scam exposed. Forward to all groups. {keyword} #viral",
        "दोस्तों, यह message सभी को भेजो। बहुत ज़रूरी है। {keyword}",
        "Attention all members. Special operation begins tonight. Details via DM. {keyword}",
        "Verified source confirms: {keyword} operation active in {city}. Stay alert.",
        "आज रात 12 बजे के बाद अपने account में पैसे transfer मत करना। {keyword} warning.",
        "100% genuine investment opportunity. Guaranteed 3x returns. {keyword} crypto scheme.",
        "फर्जी ID बनाने का तरीका जानो। Telegram: @{handle} से संपर्क करो।",
        "सरकार ने बड़ा षड्यंत्र रचा है। सच्चाई यहाँ है: {keyword}. Share करो!",
        "Emergency alert: {keyword} detected near {city}. Evacuate immediately. Forward!",
    ],
    "twitter": [
        "BREAKING: {keyword} operation exposed! Government silent. RT before deletion #India",
        "They don't want you to know about {keyword}. Thread 🧵 [1/12]",
        "{keyword} is happening RIGHT NOW in {city}. No mainstream media coverage. #WakeUp",
        "Account: @{handle} is spreading {keyword} disinfo. Report & block! #CyberSecurity",
        "Fake news alert: viral post about {keyword} is FALSE. Fact check inside.",
        "UPI fraud alert: {phone} involved in {keyword} scam. Beware! #fraud #scam",
        "Dark truth about {keyword} — follow for more. Indian media suppressing this.",
        "URGENT: If you received a call from {phone} regarding {keyword}, report to cybercrime.",
    ],
    "rss_news": [
        "Cybercrime unit arrests {city} man for running UPI mule account network worth ₹{amount}Cr",
        "ED raids hawala operator in {city}; seizes ₹{amount}L in cash and crypto assets",
        "Fake social media accounts spreading propaganda about {keyword} traced to {city}",
        "Police bust SIM swap fraud ring operating from {city}; {count} arrested",
        "National Cyber Security advisory: New {keyword} phishing campaign targeting bank customers",
        "Intelligence agencies flag coordinated disinformation campaign ahead of elections",
        "{city} court sentences hawala agent to {count} years for terror financing links",
    ],
    "upi_transaction": [
        "UPI transfer of ₹{amount} from {upi_from} to {upi_to} — High velocity flag",
        "Rapid-fire: {count} transactions in {hrs}h from account {upi_from}",
        "New recipient: {upi_to} received funds from {count} unique senders in 24h",
        "Suspicious: Account {upi_from} created {days} days ago — already {count} transactions",
        "Cash-out pattern: {upi_from} → multiple agents → ATM withdrawals in {city}",
    ]
}

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Kanpur",
    "Nagpur", "Indore", "Patna", "Bhopal", "Ludhiana", "Agra",
    "Varanasi", "Nashik", "Meerut", "Amritsar", "Visakhapatnam",
    "Vadodara", "Raipur", "Coimbatore", "Thiruvananthapuram", "Ranchi"
]


# ─── Generator Functions ───────────────────────────────────────────────────────

def gen_indian_phone() -> str:
    """Generate a realistic +91 Indian mobile number."""
    prefix = random.choice(list(TELECOM_OPERATORS.keys()))
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"+91{prefix}{suffix}"


def gen_upi_id(name: str) -> str:
    """Generate a realistic UPI ID from a name."""
    clean = name.lower().replace(" ", "").replace(".", "")[:10]
    num = random.randint(1, 999)
    handle = random.choice(UPI_HANDLES)
    variants = [
        f"{clean}{handle}",
        f"{clean}{num}{handle}",
        f"{clean[:5]}{handle}",
    ]
    return random.choice(variants)


def gen_telegram_handle(name: str = None) -> str:
    """Generate a realistic Telegram handle."""
    if name and random.random() > 0.5:
        base = name.lower().replace(" ", "_")[:10]
        suffix = random.randint(1, 9999)
        return f"@{base}{suffix}"
    prefix = random.choice(TELEGRAM_PREFIXES)
    suffix = random.randint(100, 9999)
    return f"@{prefix}{suffix}"


def gen_twitter_handle(name: str = None) -> str:
    """Generate a realistic Twitter/X handle."""
    if name and random.random() > 0.4:
        base = name.lower().replace(" ", "_")[:12]
        suffix = random.randint(1, 999)
        return f"@{base}{suffix}"
    prefix = random.choice(["real_", "truth_", "official_", "the_", ""])
    base = name.lower().replace(" ", "")[:10] if name else fake.word()
    return f"@{prefix}{base}{random.randint(1, 9999)}"


def gen_email(name: str) -> str:
    """Generate a realistic email address."""
    clean = name.lower().replace(" ", ".")
    domains = ["gmail.com", "yahoo.co.in", "hotmail.com", "rediffmail.com",
               "outlook.com", "protonmail.com", "tutanota.com"]
    num = random.randint(1, 999) if random.random() > 0.5 else ""
    return f"{clean}{num}@{random.choice(domains)}"


def gen_crypto_wallet() -> str:
    """Generate a fake Bitcoin or USDT wallet address."""
    wallet_type = random.choice(["btc", "usdt_trc20", "usdt_erc20", "eth"])
    if wallet_type == "btc":
        chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return "1" + "".join(random.choices(chars, k=33))
    elif wallet_type in ["usdt_trc20"]:
        chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0123456789"
        return "T" + "".join(random.choices(chars, k=33))
    else:
        return "0x" + "".join(random.choices("0123456789abcdef", k=40))


def gen_content(platform: str, entity_phone: str = None, entity_handle: str = None) -> str:
    """Generate platform-appropriate realistic content."""
    templates = PLATFORM_CONTENT.get(platform, PLATFORM_CONTENT["telegram"])
    template = random.choice(templates)
    return template.format(
        keyword=random.choice(THREAT_KEYWORDS),
        city=random.choice(INDIAN_CITIES),
        phone=entity_phone or gen_indian_phone(),
        handle=(entity_handle or "@anon_user123").replace("@", ""),
        amount=random.randint(1, 500),
        count=random.randint(2, 50),
        hrs=random.randint(1, 24),
        days=random.randint(1, 30),
        upi_from=gen_upi_id("sender"),
        upi_to=gen_upi_id("receiver"),
    )


def assign_risk_level(score: float) -> str:
    if score < 4.0:
        return "low"
    elif score < 6.5:
        return "medium"
    elif score < 8.5:
        return "high"
    return "critical"


def compute_risk_score(
    anomaly_score: float,
    pattern_match: float,
    network_connections: int,
    velocity_score: float,
    sentiment_score: float,
    source_tier_multiplier: float,
) -> float:
    """
    Composite risk score formula from the PRD:
      risk = (anomaly*0.30 + pattern*0.25 + centrality*0.20 + velocity*0.15 + sentiment*0.10)
             × source_multiplier
    Capped at 10.0.
    """
    centrality = min(network_connections / 20.0, 1.0)  # normalize to 0-1
    base = (
        anomaly_score      * 0.30 +
        pattern_match      * 0.25 +
        centrality         * 0.20 +
        velocity_score     * 0.15 +
        abs(sentiment_score) * 0.10  # negative sentiment increases risk
    )
    return round(min(base * 10.0 * source_tier_multiplier, 10.0), 2)


# ─── Main Generator ────────────────────────────────────────────────────────────

def generate_all(
    num_persons: int = 100,
    num_entities: int = 500,
    num_events: int = 1000,
    num_alerts: int = 50,
) -> dict:
    """
    Generate the full mock dataset.

    Returns a dict with keys:
      sources, users, keywords, entities, events, alerts

    Entity composition (500 total):
      - 100 Person entities (with full alias sets)
      - 150 standalone Phone numbers (linked to persons or orphaned)
      - 100 Telegram handles
      - 80  UPI accounts
      - 40  Email addresses
      - 20  Twitter handles
      - 10  Crypto wallets
    """
    print("🔄 Generating mock data...")

    now = datetime.now(timezone.utc)

    # ── 1. Sources ────────────────────────────────────────────────────────────
    sources = [
        {
            "id": str(uuid.uuid4()),
            "name": "Mock Telegram Channel Feed",
            "source_type": "telegram_public",
            "tier": "tier_3",
            "url": "mock://telegram",
            "description": "Simulated Telegram public channel data",
            "is_active": True,
            "reliability_multiplier": 0.7,
            "crawl_interval_minutes": 5,
            "last_crawled_at": now.isoformat(),
            "event_count_today": 0,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mock UPI Transaction Stream",
            "source_type": "upi_transaction",
            "tier": "tier_2",
            "url": "mock://upi",
            "description": "Simulated UPI transaction alerts",
            "is_active": True,
            "reliability_multiplier": 1.0,
            "crawl_interval_minutes": 1,
            "last_crawled_at": now.isoformat(),
            "event_count_today": 0,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mock Twitter/X Threat Feed",
            "source_type": "twitter_x",
            "tier": "tier_3",
            "url": "mock://twitter",
            "description": "Simulated Twitter/X posts",
            "is_active": True,
            "reliability_multiplier": 0.7,
            "crawl_interval_minutes": 10,
            "last_crawled_at": now.isoformat(),
            "event_count_today": 0,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "NDTV RSS Feed",
            "source_type": "rss_news",
            "tier": "tier_1",
            "url": "https://feeds.feedburner.com/ndtvnews-india-news",
            "description": "NDTV India News RSS",
            "is_active": True,
            "reliability_multiplier": 1.5,
            "crawl_interval_minutes": 15,
            "last_crawled_at": now.isoformat(),
            "event_count_today": 0,
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Mock Dark Web Forum",
            "source_type": "dark_web",
            "tier": "tier_4",
            "url": "mock://darkweb",
            "description": "Simulated dark web forum posts",
            "is_active": True,
            "reliability_multiplier": 0.3,
            "crawl_interval_minutes": 60,
            "last_crawled_at": now.isoformat(),
            "event_count_today": 0,
        },
    ]
    source_ids = [s["id"] for s in sources]

    # ── 2. Users ──────────────────────────────────────────────────────────────
    # Hashed password for "password123" — bcrypt hash
    # In real code: from passlib.context import CryptContext; pwd_context.hash("password123")
    HASHED_PASSWORD = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

    users = [
        {
            "id": str(uuid.uuid4()),
            "username": "analyst_demo",
            "email": "analyst@aiila.in",
            "hashed_password": HASHED_PASSWORD,
            "full_name": "Demo Analyst",
            "role": "analyst",
            "is_active": True,
        },
        {
            "id": str(uuid.uuid4()),
            "username": "commander_01",
            "email": "commander@aiila.in",
            "hashed_password": HASHED_PASSWORD,
            "full_name": "Senior Commander",
            "role": "commander",
            "is_active": True,
        },
        {
            "id": str(uuid.uuid4()),
            "username": "specialist_fraud",
            "email": "specialist@aiila.in",
            "hashed_password": HASHED_PASSWORD,
            "full_name": "Fraud Specialist",
            "role": "specialist",
            "is_active": True,
        },
    ]

    # ── 3. Keywords ───────────────────────────────────────────────────────────
    keywords = []
    keyword_categories = {
        "financial_fraud": ["hawala", "hundi", "mule account", "UPI scam", "SIM swap",
                             "money laundering", "crypto fraud", "QR scam", "OTP fraud"],
        "terrorism":       ["IED", "LeT", "ISI", "explosives", "weapons cache",
                             "terror financing", "RDX", "militant"],
        "propaganda":      ["disinformation", "fake news", "deepfake", "psyops",
                             "coordinated inauthentic", "bot network", "troll farm"],
        "narcotics":       ["narcotics", "drug trafficking", "smuggling", "contraband",
                             "heroin", "methamphetamine"],
        "cybercrime":      ["phishing", "ransomware", "darkweb", "data breach",
                             "malware", "hacking", "credential theft"],
    }
    for category, words in keyword_categories.items():
        for word in words:
            keywords.append({
                "id": str(uuid.uuid4()),
                "word": word,
                "category": category,
                "language": "en",
                "is_active": True,
                "match_count": random.randint(0, 150),
            })

    # ── 4. Entities (persons + their aliases) ─────────────────────────────────
    entities = []
    aliases_all = []
    person_entities = []   # we'll reference these when generating events

    print(f"  Generating {num_persons} person entities with aliases...")
    for i in range(num_persons):
        first = random.choice(INDIAN_FIRST_NAMES)
        last = random.choice(INDIAN_LAST_NAMES)
        full_name = f"{first} {last}"

        phone      = gen_indian_phone()
        upi_id     = gen_upi_id(full_name)
        tg_handle  = gen_telegram_handle(full_name)
        tw_handle  = gen_twitter_handle(full_name)
        email_addr = gen_email(full_name)
        city       = random.choice(INDIAN_CITIES)

        # Risk profile varies across persons
        risk_profile = random.choices(
            ["low", "medium", "high", "critical"],
            weights=[40, 30, 20, 10]
        )[0]
        anomaly    = {"low": 0.1, "medium": 0.35, "high": 0.65, "critical": 0.88}[risk_profile]
        pattern    = {"low": 0.0, "medium": 0.2,  "high": 0.6,  "critical": 0.9}[risk_profile]
        velocity   = random.uniform(0, {"low": 0.2, "medium": 0.5, "high": 0.75, "critical": 0.95}[risk_profile])
        sentiment  = random.uniform(-1, {"low": 0.2, "medium": 0.0, "high": -0.4, "critical": -0.8}[risk_profile])
        n_conn     = {"low": 2, "medium": 8, "high": 15, "critical": 25}[risk_profile] + random.randint(0, 5)
        tier_mult  = random.choice([0.7, 1.0, 1.0, 1.5])

        risk_score = compute_risk_score(anomaly, pattern, n_conn, velocity, sentiment, tier_mult)
        risk_level = assign_risk_level(risk_score)
        is_flagged = risk_score >= 6.5

        # Determine risk factors for explainability
        factors = []
        if anomaly > 0.5:
            count = random.randint(10, 47)
            hrs = random.randint(1, 6)
            factors.append(f"Transaction velocity anomaly: {count} txns in {hrs}h (3σ above baseline)")
        if pattern > 0.4:
            factors.append(f"Matched {random.choice(FRAUD_PATTERNS)}")
        if n_conn > 10:
            factors.append(f"High network centrality: {n_conn} direct connections in entity graph")
        if sentiment < -0.4:
            factors.append(f"Consistently negative sentiment in {random.randint(5,15)} recent posts")
        if velocity > 0.6:
            factors.append(f"Unusual activity velocity spike in last 24h")
        factors = factors[:3]  # cap at top 3

        entity_id = str(uuid.uuid4())
        first_seen = now - timedelta(days=random.randint(1, 180))
        last_seen  = now - timedelta(hours=random.randint(0, 72))

        entity = {
            "id": entity_id,
            "entity_type": "person",
            "primary_identifier": full_name,
            "display_name": full_name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "influence_score": round(random.uniform(0, 1), 4),
            "anomaly_score": round(anomaly, 4),
            "sentiment_avg": round(sentiment, 4),
            "event_count": random.randint(1, 200),
            "first_seen": first_seen.isoformat(),
            "last_seen": last_seen.isoformat(),
            "is_flagged": is_flagged,
            "investigation_notes": None,
            "risk_factors": factors,
            "metadata_": {
                "city": city,
                "risk_profile_label": risk_profile,
                "network_connections": n_conn,
            },
        }
        entities.append(entity)
        person_entities.append({
            **entity,
            "phone": phone,
            "upi_id": upi_id,
            "tg_handle": tg_handle,
            "tw_handle": tw_handle,
            "email": email_addr,
            "city": city,
        })

        # Create aliases for this person
        alias_defs = [
            ("phone", phone, "exact"),
            ("upi_account", upi_id, "exact"),
            ("telegram", tg_handle, "exact"),
        ]
        # Not all persons have all identifiers
        if random.random() > 0.3:
            alias_defs.append(("social_handle", tw_handle, "exact"))
        if random.random() > 0.4:
            alias_defs.append(("email", email_addr, "exact"))
        if random.random() > 0.8:  # only some have crypto wallets
            alias_defs.append(("crypto_wallet", gen_crypto_wallet(), "exact"))

        for alias_type, alias_value, method in alias_defs:
            aliases_all.append({
                "id": str(uuid.uuid4()),
                "entity_id": entity_id,
                "alias_type": alias_type,
                "alias_value": alias_value,
                "platform": alias_type,
                "confidence": round(random.uniform(0.7, 1.0), 2),
                "resolution_method": method,
                "is_verified": random.random() > 0.5,
            })

    # Generate orphan non-person entities to reach num_entities
    print(f"  Generating {num_entities - num_persons} standalone entity identifiers...")
    remaining = num_entities - num_persons
    type_dist = {
        "phone": int(remaining * 0.35),
        "telegram": int(remaining * 0.25),
        "upi_account": int(remaining * 0.20),
        "email": int(remaining * 0.10),
        "social_handle": int(remaining * 0.07),
        "crypto_wallet": int(remaining * 0.03),
    }
    for etype, count in type_dist.items():
        for _ in range(count):
            if etype == "phone":
                identifier = gen_indian_phone()
            elif etype == "telegram":
                identifier = gen_telegram_handle()
            elif etype == "upi_account":
                identifier = gen_upi_id(fake.name())
            elif etype == "email":
                identifier = gen_email(fake.name())
            elif etype == "social_handle":
                identifier = gen_twitter_handle()
            else:
                identifier = gen_crypto_wallet()

            risk_score = round(random.uniform(0, 10), 2)
            entities.append({
                "id": str(uuid.uuid4()),
                "entity_type": etype,
                "primary_identifier": identifier,
                "display_name": identifier,
                "risk_score": risk_score,
                "risk_level": assign_risk_level(risk_score),
                "influence_score": round(random.uniform(0, 0.5), 4),
                "anomaly_score": round(random.uniform(0, 1), 4),
                "sentiment_avg": round(random.uniform(-1, 1), 4),
                "event_count": random.randint(0, 50),
                "first_seen": (now - timedelta(days=random.randint(1, 90))).isoformat(),
                "last_seen": (now - timedelta(hours=random.randint(0, 48))).isoformat(),
                "is_flagged": risk_score >= 6.5,
                "investigation_notes": None,
                "risk_factors": [],
                "metadata_": {},
            })

    # ── 5. Raw Events ──────────────────────────────────────────────────────────
    print(f"  Generating {num_events} raw events...")
    events = []
    platforms = ["telegram", "twitter", "upi_transaction", "rss_news", "dark_web"]
    platform_weights = [35, 25, 20, 15, 5]    # % distribution

    for i in range(num_events):
        platform = random.choices(platforms, weights=platform_weights)[0]
        source_id = random.choice(source_ids)
        person = random.choice(person_entities)

        published_at = now - timedelta(
            days=random.randint(0, 60),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

        content = gen_content(
            platform,
            entity_phone=person.get("phone"),
            entity_handle=person.get("tg_handle") if platform == "telegram" else person.get("tw_handle")
        )

        # Language distribution
        lang = random.choices(
            ["en", "hi", "ur", "bn", "ta", "te", "mr"],
            weights=[40, 30, 10, 5, 5, 5, 5]
        )[0]

        # Simulate enrichment results (as if pipeline already ran)
        extracted_entities = []
        if person.get("phone"):
            extracted_entities.append({
                "type": "phone", "value": person["phone"], "confidence": 0.95
            })
        if person.get("tg_handle") and platform == "telegram":
            extracted_entities.append({
                "type": "telegram", "value": person["tg_handle"], "confidence": 0.9
            })
        if random.random() > 0.6 and person.get("upi_id"):
            extracted_entities.append({
                "type": "upi_account", "value": person["upi_id"], "confidence": 0.88
            })

        matched_kws = []
        for kw in keywords:
            if kw["word"].lower() in content.lower():
                matched_kws.append(kw["id"])

        sentiment = person["sentiment_avg"] + random.uniform(-0.2, 0.2)
        sentiment = max(-1.0, min(1.0, sentiment))

        event = {
            "id": str(uuid.uuid4()),
            "source_id": source_id,
            "external_id": f"{platform}_{i}_{random.randint(100000, 999999)}",
            "content": content,
            "content_language": lang,
            "translated_content": content if lang == "en" else f"[TRANSLATED] {content}",
            "event_type": platform,  # Add event_type — same as platform
            "timestamp": published_at.isoformat(),  # Add timestamp — same as published_at
            "url": f"https://{platform}.example.com/post/{random.randint(100000, 999999)}",
            "author_handle": person.get("tg_handle") if platform == "telegram" else person.get("tw_handle"),
            "platform": platform,
            "published_at": published_at.isoformat(),
            "is_processed": True,
            "is_duplicate": False,
            "duplicate_of": None,
            "extracted_entities": extracted_entities,
            "sentiment_score": round(sentiment, 4),
            "anomaly_score": round(person["anomaly_score"] + random.uniform(-0.1, 0.1), 4),
            "matched_keywords": matched_kws[:3],   # top 3 matches
            "metadata_": {
                "city_inferred": person.get("city"),
                "platform_specific": {},
            },
            # Store person reference for entity_events linking
            "_person_entity_id": person["id"],
        }
        events.append(event)

    # ── 6. Risk Alerts ────────────────────────────────────────────────────────
    print(f"  Generating {num_alerts} risk alerts...")
    alerts = []

    # Only generate alerts for flagged entities
    flagged = [e for e in entities if e["is_flagged"]]
    if len(flagged) < num_alerts:
        # Supplement with high-scoring unflagged entities
        high_score = sorted(entities, key=lambda e: e["risk_score"], reverse=True)
        flagged = high_score[:num_alerts]

    alert_entities = random.sample(flagged, min(num_alerts, len(flagged)))

    for entity in alert_entities:
        risk_score = entity["risk_score"]
        alert_type = random.choices(
            ["financial_fraud", "coordinated_inauthentic", "keyword_match",
             "anomaly_detected", "network_cluster", "propaganda"],
            weights=[30, 20, 15, 15, 10, 10]
        )[0]

        pattern = random.choice(FRAUD_PATTERNS) if risk_score > 7 else None

        # Pick a recent trigger event for this entity
        entity_events = [e for e in events if e.get("_person_entity_id") == entity["id"]]
        trigger_event_id = entity_events[0]["id"] if entity_events else None

        title_tmpl = random.choice(ALERT_TITLE_TEMPLATES)
        title = title_tmpl.format(
            entity=entity["primary_identifier"][:30],
            count=random.randint(3, 30),
            hrs=random.randint(1, 12),
            kw=random.choice(THREAT_KEYWORDS),
            platform=random.choice(["Telegram", "Twitter"]),
            amount=random.randint(10, 500),
        )

        # Alert created_at — more recent for higher-risk alerts
        hours_ago = max(1, int((10 - risk_score) * 12))  # critical = 12h ago, low = 120h ago
        created_at = now - timedelta(hours=hours_ago + random.randint(0, 6))

        # Status distribution: most are new (for demo realism)
        status = random.choices(
            ["new", "under_review", "confirmed", "dismissed"],
            weights=[60, 20, 12, 8]
        )[0]

        alerts.append({
            "id": str(uuid.uuid4()),
            "entity_id": entity["id"],
            "alert_type": alert_type,
            "title": title[:500],
            "description": f"Automated analysis flagged {entity['primary_identifier']} based on "
                           f"behavioral patterns and network connections. Risk score: {risk_score}/10. "
                           f"Pattern match: {pattern or 'N/A'}.",
            "risk_score": risk_score,
            "risk_level": entity["risk_level"],
            "status": status,
            "trigger_event_id": trigger_event_id,
            "matched_pattern": pattern,
            "risk_factors": entity["risk_factors"],
            "evidence_data": {
                "network_size": entity["metadata_"].get("network_connections", 0),
                "city_inferred": entity["metadata_"].get("city", "Unknown"),
                "event_count": entity["event_count"],
            },
            "reviewed_by": None,
            "reviewed_at": None,
            "analyst_note": None,
            "created_at": created_at.isoformat(),
        })

    # Sort alerts by risk score descending (most urgent first)
    alerts.sort(key=lambda a: a["risk_score"], reverse=True)

    return {
        "meta": {
            "generated_at": now.isoformat(),
            "counts": {
                "sources":  len(sources),
                "users":    len(users),
                "keywords": len(keywords),
                "entities": len(entities),
                "aliases":  len(aliases_all),
                "events":   len(events),
                "alerts":   len(alerts),
            }
        },
        "sources":  sources,
        "users":    users,
        "keywords": keywords,
        "entities": entities,
        "aliases":  aliases_all,
        "events":   events,
        "alerts":   alerts,
    }


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os

    output_path = os.path.join(os.path.dirname(__file__), "mock_data.json")

    data = generate_all(
        num_persons=100,
        num_entities=500,
        num_events=1000,
        num_alerts=50,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    print("\n✅ Mock data generated!")
    print(f"   📁 Output: {output_path}")
    for k, v in data["meta"]["counts"].items():
        print(f"   {k:12s}: {v:>5}")
    print(f"\n   Total file size: {os.path.getsize(output_path) / 1024:.1f} KB")
    print("\n▶️  Next step: python scripts/load_into_postgres.py")
