from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock, Thread
from time import sleep
from typing import Any
import re
from urllib.parse import quote_plus

from flask import Flask, jsonify, request, send_from_directory


app = Flask(__name__, static_folder="static", static_url_path="/static")

BACKEND_VERSION = "jobradar-search-links-v4"


@app.after_request
def add_cors_headers(response: Any) -> Any:
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


SOURCE_COMPANIES: dict[str, list[str]] = {
    "Greenhouse": ["HubSpot", "Notion", "Intercom"],
    "Lever": ["Gartner", "Monzo", "Wise"],
    "Ashby": ["OpenAI", "Linear", "Airtable"],
    "RemoteOK": ["ScaleUp Beta", "Pipeline Cloud", "SaaS Orbit"],
    "YCombinator": ["ArcFlow", "LedgerLoop", "SignalStack"],
    "Welcome to the Jungle": ["PayFit", "Qonto", "Alan"],
    "Himalayas": ["RemoteFirst Labs", "OpsPilot", "DemandCraft"],
    "We Work Remotely": ["RenewFlow", "PartnerBase", "ClientLoop"],
    "Hacker News": ["Bootstrap Labs", "Commerce Forge", "Signal Path"],
    "Otta": ["Ramp", "Pleo", "Pigment"],
    "Wellfound": ["LaunchGrid", "OutboundOS", "MarketPulse"],
    "LinkedIn": ["Microsoft", "Google", "Atlassian"],
    "Indeed": ["Contentsquare", "Miro", "Aircall"],
    "Glassdoor": ["Stripe", "Zendesk", "Zapier"],
    "Flexa": ["Personio", "Mollie", "Spendesk"],
    "EuroTechJobs": ["Celonis", "Mews", "Deel"],
    "Built In": ["Figma", "Shopify", "Datadog"],
    "JobTeaser": ["L'Oreal", "Danone", "Publicis"],
    "Talent.com": ["Adobe", "SAP", "Uber"],
    "StepStone": ["HelloFresh", "N26", "Revolut"],
    "Adzuna": ["Salesforce", "ServiceNow", "Workday"],
    "Reed": ["Oracle", "IBM", "Accenture"],
}


LOCATION_LIBRARY = [
    "Remote",
    "Remote - Europe",
    "Barcelona, Spain",
    "Madrid, Spain",
    "Paris, France",
    "London, United Kingdom",
    "Dublin, Ireland",
    "Berlin, Germany",
    "Amsterdam, Netherlands",
    "Zurich, Switzerland",
    "Geneva, Switzerland",
]


ROLE_LIBRARY: list[dict[str, str]] = [
    {
        "title": "Account Executive",
        "description": "Own discovery calls, demos, negotiations, and closing across a structured B2B sales cycle.",
    },
    {
        "title": "Mid-Market Account Executive",
        "description": "Drive new business growth across mid-market accounts with a consultative commercial approach.",
    },
    {
        "title": "Enterprise Account Executive",
        "description": "Navigate complex stakeholders, build business cases, and close enterprise opportunities.",
    },
    {
        "title": "Sales Development Representative",
        "description": "Prospect target accounts, qualify opportunities, and create pipeline for the closing team.",
    },
    {
        "title": "Business Development Representative",
        "description": "Generate outbound demand, run qualification, and support go-to-market execution.",
    },
    {
        "title": "Business Development Manager",
        "description": "Open new markets, structure prospecting motions, and convert strategic commercial opportunities.",
    },
    {
        "title": "Key Account Manager",
        "description": "Manage strategic customer portfolios, protect revenue, and develop long-term account plans.",
    },
    {
        "title": "Strategic Account Manager",
        "description": "Grow large customer relationships through retention, cross-sell, and executive stakeholder management.",
    },
    {
        "title": "Account Manager",
        "description": "Own day-to-day client relationships, renewals, upsell opportunities, and commercial follow-up.",
    },
    {
        "title": "Customer Success Manager",
        "description": "Lead onboarding, adoption, retention, and value realization for a portfolio of customers.",
    },
    {
        "title": "Customer Success Specialist",
        "description": "Support customer onboarding, training, and proactive retention work across the full lifecycle.",
    },
    {
        "title": "Customer Success Operations Analyst",
        "description": "Build reporting, optimize workflows, and improve efficiency for customer-facing teams.",
    },
    {
        "title": "Customer Education Manager",
        "description": "Create enablement programs, webinars, and training content to improve adoption.",
    },
    {
        "title": "Implementation Manager",
        "description": "Coordinate customer launches, stakeholder alignment, and early-stage product adoption.",
    },
    {
        "title": "Partnerships Manager",
        "description": "Develop strategic partnerships, manage partner pipelines, and launch joint go-to-market initiatives.",
    },
    {
        "title": "Channel Partnerships Manager",
        "description": "Scale indirect revenue through channel partners, enablement, and co-selling programs.",
    },
    {
        "title": "Alliances Manager",
        "description": "Build ecosystem relationships and structure alliances that accelerate commercial growth.",
    },
    {
        "title": "Revenue Operations Analyst",
        "description": "Support forecasting, reporting, CRM hygiene, and commercial performance analysis.",
    },
    {
        "title": "Revenue Operations Manager",
        "description": "Own GTM tooling, dashboards, process design, and forecast reliability across teams.",
    },
    {
        "title": "Sales Operations Analyst",
        "description": "Improve sales reporting, data quality, process discipline, and performance visibility.",
    },
    {
        "title": "Business Operations Associate",
        "description": "Support planning, internal reporting, and cross-functional business process execution.",
    },
    {
        "title": "Business Operations Manager",
        "description": "Drive cross-functional projects, operating rhythms, and scalable internal processes.",
    },
    {
        "title": "Growth Manager",
        "description": "Own experiments across acquisition, activation, retention, and expansion loops.",
    },
    {
        "title": "Growth Marketing Manager",
        "description": "Plan campaigns, optimize channels, and improve pipeline contribution through measurable growth work.",
    },
    {
        "title": "Lifecycle Marketing Manager",
        "description": "Design CRM journeys, segmentation, and messaging to improve activation and retention.",
    },
    {
        "title": "Demand Generation Manager",
        "description": "Build inbound pipeline with campaigns, paid programs, and conversion-focused messaging.",
    },
    {
        "title": "Product Marketing Manager",
        "description": "Own positioning, messaging, launches, and sales enablement for product adoption.",
    },
    {
        "title": "Brand Manager",
        "description": "Shape brand positioning, campaign planning, and market visibility across target segments.",
    },
    {
        "title": "Luxury Brand Manager",
        "description": "Lead premium brand positioning, launch plans, and market execution in a high-end environment.",
    },
    {
        "title": "Category Manager",
        "description": "Manage category performance, assortment strategy, and commercial optimization initiatives.",
    },
    {
        "title": "Category Development Manager",
        "description": "Drive category growth plans with retailers through insights, assortment, and commercial recommendations.",
    },
    {
        "title": "CRM Manager",
        "description": "Lead CRM strategy, automation, segmentation, and lifecycle program performance.",
    },
    {
        "title": "Go-to-Market Manager",
        "description": "Coordinate launch planning, target segments, messaging, and cross-functional market execution.",
    },
    {
        "title": "Strategy Associate",
        "description": "Support market analysis, planning, and strategic recommendations for business growth.",
    },
    {
        "title": "Business Analyst",
        "description": "Analyze performance, structure recommendations, and translate data into business decisions.",
    },
    {
        "title": "Commercial Analyst",
        "description": "Track commercial KPIs, analyze pipeline trends, and support pricing and planning decisions.",
    },
    {
        "title": "Pricing Analyst",
        "description": "Work on pricing models, margin analysis, and revenue optimization initiatives.",
    },
    {
        "title": "FP&A Analyst",
        "description": "Support budgeting, forecasting, management reporting, and business performance planning.",
    },
    {
        "title": "Management Consultant",
        "description": "Structure business problems, run analyses, and prepare strategic recommendations for clients.",
    },
    {
        "title": "Project Manager",
        "description": "Coordinate timelines, stakeholders, and delivery across commercial and operational projects.",
    },
    {
        "title": "Program Manager",
        "description": "Lead complex workstreams across teams with strong planning and execution discipline.",
    },
    {
        "title": "E-commerce Manager",
        "description": "Improve online commercial performance through merchandising, conversion, and channel optimization.",
    },
    {
        "title": "Supply Chain Analyst",
        "description": "Analyze flows, inventory, and operational performance to improve business efficiency.",
    },
    {
        "title": "Procurement Manager",
        "description": "Lead sourcing strategy, supplier negotiations, and cost optimization programs.",
    },
    {
        "title": "Market Research Analyst",
        "description": "Study market trends, customer insights, and competitive dynamics to support business strategy.",
    },
    {
        "title": "Consumer Insights Manager",
        "description": "Translate customer behavior and market research into decisions for brand, growth, and portfolio strategy.",
    },
    {
        "title": "Sales Enablement Manager",
        "description": "Create sales playbooks, training, and content that improve commercial execution quality.",
    },
    {
        "title": "Customer Insights Analyst",
        "description": "Turn customer feedback and behavioral data into actions for growth and retention.",
    },
    {
        "title": "Trade Marketing Manager",
        "description": "Drive retail activation, channel marketing, and commercial excellence initiatives.",
    },
    {
        "title": "Retail Merchandising Manager",
        "description": "Optimize assortment visibility, in-store execution, and sell-out performance across retail channels.",
    },
    {
        "title": "Shopper Marketing Manager",
        "description": "Build shopper-focused activations, channel plans, and retail campaigns linked to commercial goals.",
    },
]


ROLE_FAMILIES: dict[str, list[str]] = {
    "sales": [
        "sales",
        "sales executive",
        "sales representative",
        "sales specialist",
        "inside sales",
        "commercial",
        "new business",
        "closing",
    ],
    "account executive": [
        "account executive",
        "mid-market account executive",
        "enterprise account executive",
        "ae",
        "sales executive",
    ],
    "key account manager": [
        "key account manager",
        "strategic account manager",
        "global account manager",
        "major account manager",
        "national account manager",
    ],
    "account manager": [
        "account manager",
        "client partner",
        "relationship manager",
        "account director",
        "portfolio manager",
    ],
    "customer success": [
        "customer success",
        "customer success manager",
        "customer success specialist",
        "client success",
        "retention",
        "renewals",
        "onboarding",
        "implementation",
    ],
    "business development": [
        "business development",
        "business development representative",
        "business development manager",
        "sales development",
        "sales development representative",
        "sdr",
        "bdr",
        "prospecting",
        "pipeline",
    ],
    "partnerships": [
        "partnerships",
        "partnerships manager",
        "channel partnerships",
        "alliances",
        "partner manager",
        "ecosystem",
        "co-selling",
    ],
    "revenue operations": [
        "revenue operations",
        "revops",
        "sales operations",
        "customer success operations",
        "go to market operations",
        "gtm operations",
        "forecasting",
        "crm",
    ],
    "business operations": [
        "business operations",
        "bizops",
        "operations associate",
        "operations manager",
        "commercial operations",
        "planning",
        "reporting",
    ],
    "growth": [
        "growth",
        "growth manager",
        "growth marketing",
        "acquisition",
        "activation",
        "retention marketing",
        "expansion",
    ],
    "marketing": [
        "marketing",
        "growth marketing",
        "demand generation",
        "field marketing",
        "campaign",
        "content marketing",
    ],
    "product marketing": [
        "product marketing",
        "product marketing manager",
        "positioning",
        "messaging",
        "launch",
        "sales enablement",
    ],
    "brand management": [
        "brand manager",
        "luxury brand manager",
        "brand management",
        "brand marketing",
        "trade marketing",
        "retail activation",
    ],
    "luxury": [
        "luxury",
        "premium",
        "luxury brand manager",
        "high-end",
        "selective retail",
    ],
    "fmcg": [
        "fmcg",
        "consumer goods",
        "cpg",
        "shopper marketing",
        "sell-out",
        "retail excellence",
    ],
    "category management": [
        "category manager",
        "category development manager",
        "category management",
        "assortment",
        "merchandising",
        "commercial optimization",
    ],
    "crm": [
        "crm",
        "crm manager",
        "lifecycle marketing",
        "automation",
        "segmentation",
        "email marketing",
    ],
    "strategy": [
        "strategy",
        "strategy associate",
        "commercial strategy",
        "go-to-market manager",
        "go to market",
        "pricing",
    ],
    "consulting": [
        "consulting",
        "consultant",
        "management consultant",
        "problem solving",
        "recommendations",
    ],
    "finance": [
        "finance",
        "fp&a",
        "fp&a analyst",
        "budgeting",
        "forecasting",
        "management reporting",
        "margin",
    ],
    "business analyst": [
        "business analyst",
        "commercial analyst",
        "analyst",
        "kpi",
        "performance analysis",
        "data analysis",
    ],
    "project management": [
        "project manager",
        "program manager",
        "project management",
        "stakeholder management",
        "delivery",
    ],
    "operations": [
        "operations",
        "operations manager",
        "operations associate",
        "process improvement",
        "execution",
    ],
    "supply chain": [
        "supply chain",
        "supply chain analyst",
        "inventory",
        "planning",
        "flow",
    ],
    "procurement": [
        "procurement",
        "procurement manager",
        "sourcing",
        "supplier negotiations",
        "vendor management",
    ],
    "e-commerce": [
        "e-commerce",
        "ecommerce",
        "e-commerce manager",
        "conversion",
        "online commercial performance",
    ],
    "market research": [
        "market research",
        "market research analyst",
        "customer insights",
        "consumer insights",
        "consumer insights manager",
        "competitive analysis",
        "consumer insights",
    ],
    "retail": [
        "retail",
        "retail merchandising manager",
        "merchandising",
        "shopper marketing",
        "point of sale",
        "sell-out",
    ],
    "sales enablement": [
        "sales enablement",
        "enablement",
        "playbooks",
        "training",
        "commercial excellence",
    ],
    "customer education": [
        "customer education",
        "customer education manager",
        "customer training",
        "adoption programs",
        "webinars",
    ],
}


DEFAULT_ROLE_KEYWORDS = [
    "sales",
    "account executive",
    "key account manager",
    "account manager",
    "customer success",
    "business development",
    "partnerships",
    "revenue operations",
    "business operations",
    "growth",
    "marketing",
    "product marketing",
    "brand management",
    "category management",
    "crm",
    "strategy",
    "consulting",
    "finance",
    "business analyst",
    "project management",
    "operations",
    "supply chain",
    "procurement",
    "e-commerce",
    "market research",
]


AVAILABLE_SOURCES = list(SOURCE_COMPANIES.keys())


DEFAULT_SCAN_PAYLOAD: dict[str, Any] = {
    "filters": {
        "keywords": DEFAULT_ROLE_KEYWORDS,
        "exclude": ["intern", "internship", "director", "vp", "head of", "chief"],
        "locations": [
            "switzerland",
            "barcelona",
            "madrid",
            "paris",
            "london",
            "berlin",
            "amsterdam",
            "dublin",
            "remote",
        ],
        "levels": ["junior", "mid", "senior"],
        "sources": AVAILABLE_SOURCES,
        "companies": [],
    },
    "weights": {
        "keywords": 40,
        "location": 20,
        "company": 10,
        "semantic": 30,
    },
    "display": {
        "limit": 80,
        "min_score": 12,
    },
}


scan_lock = Lock()
scan_state: dict[str, Any] = {
    "running": False,
    "progress": 0,
    "status": "Idle",
    "count": 0,
    "sources": AVAILABLE_SOURCES,
    "jobs": [],
    "raw_jobs": [],
    "request": deepcopy(DEFAULT_SCAN_PAYLOAD),
}


@dataclass
class ScanContext:
    filters: dict[str, list[str]]
    weights: dict[str, int | float]
    display: dict[str, int | float]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "job"


SOURCE_SEARCH_HINTS: dict[str, str] = {
    "Greenhouse": "site:boards.greenhouse.io",
    "Lever": "site:jobs.lever.co",
    "Ashby": "site:jobs.ashbyhq.com",
    "RemoteOK": "site:remoteok.com",
    "YCombinator": "site:workatastartup.com",
    "Welcome to the Jungle": "site:welcometothejungle.com",
    "Himalayas": "site:himalayas.app",
    "We Work Remotely": "site:weworkremotely.com",
    "Hacker News": 'site:news.ycombinator.com "Who is hiring"',
    "Otta": "Otta jobs",
    "Wellfound": "Wellfound jobs",
    "Indeed": "Indeed jobs",
    "Glassdoor": "Glassdoor jobs",
    "Flexa": "Flexa careers",
    "EuroTechJobs": "EuroTechJobs",
    "Built In": "Built In jobs",
    "JobTeaser": "JobTeaser jobs",
    "Talent.com": "Talent.com jobs",
    "StepStone": "StepStone jobs",
    "Adzuna": "Adzuna jobs",
    "Reed": "Reed jobs",
}


def build_google_search_link(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def build_external_search_link(
    source: str,
    company: str,
    position: str,
    location: str,
) -> str:
    search_terms = " ".join(part for part in [position, company] if part).strip()
    encoded_keywords = quote_plus(search_terms or position or company or "jobs")
    encoded_location = quote_plus(location or "")

    if source == "LinkedIn":
        base_url = "https://www.linkedin.com/jobs/search/"
        if encoded_location:
            return f"{base_url}?keywords={encoded_keywords}&location={encoded_location}"
        return f"{base_url}?keywords={encoded_keywords}"

    if source == "Indeed":
        base_url = "https://www.indeed.com/jobs"
        if encoded_location:
            return f"{base_url}?q={encoded_keywords}&l={encoded_location}"
        return f"{base_url}?q={encoded_keywords}"

    hint = SOURCE_SEARCH_HINTS.get(source, source)
    query_parts = [hint, position, company, location]
    query = " ".join(part for part in query_parts if part)
    return build_google_search_link(query)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [normalize_text(item) for item in values if normalize_text(item)]


def mock_job(
    source: str,
    company: str,
    position: str,
    location: str,
    description: str,
    level: str,
) -> dict[str, Any]:
    # FIX Bug 7: include location in the slug so distinct jobs at different
    # locations don't collapse onto the same deduplication key.
    slug = slugify(f"{source}-{company}-{position}-{location}")
    source_slug = slugify(source)
    external_search_link = build_external_search_link(
        source=source,
        company=company,
        position=position,
        location=location,
    )
    return {
        "company": company,
        "position": position,
        "location": location,
        # Append slug as a fragment so same-source jobs with identical search
        # params are still treated as distinct records during deduplication.
        "link": (external_search_link or f"https://example.com/{source_slug}/{slug}") + f"#{slug}",
        "source": source,
        "description": description,
        "level": level,
    }


def infer_level(position: str) -> str:
    title = normalize_text(position)

    if any(term in title for term in ["enterprise", "strategic", "global", "lead", "senior"]):
        return "senior"
    if any(term in title for term in ["associate", "specialist", "representative", "analyst", "coordinator"]):
        return "junior"
    return "mid"


def build_mock_source_data() -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}

    for source_index, (source, companies) in enumerate(SOURCE_COMPANIES.items()):
        jobs: list[dict[str, Any]] = []
        for company_index, company in enumerate(companies):
            for offset in range(3):
                role = ROLE_LIBRARY[(source_index * 4 + company_index * 3 + offset) % len(ROLE_LIBRARY)]
                location = LOCATION_LIBRARY[(source_index * 2 + company_index + offset) % len(LOCATION_LIBRARY)]
                description = (
                    f"{role['description']} "
                    f"This role sits in a business-oriented team and values commercial judgment, communication, "
                    f"analysis, stakeholder management, and strong execution."
                )
                level = infer_level(role["title"])
                jobs.append(
                    mock_job(
                        source=source,
                        company=company,
                        position=role["title"],
                        location=location,
                        description=description,
                        level=level,
                    )
                )
        data[source] = jobs

    return data


MOCK_SOURCE_DATA = build_mock_source_data()


def build_context(payload: dict[str, Any]) -> ScanContext:
    filters = payload.get("filters", {})
    weights = payload.get("weights", {})
    display = payload.get("display", {})

    # FIX Bug 9: preserve original casing for source names so they match
    # SOURCE_COMPANIES keys (e.g. "LinkedIn", "Welcome to the Jungle").
    requested_sources = [
        str(item).strip() for item in filters.get("sources", []) if str(item).strip()
    ]

    return ScanContext(
        filters={
            "keywords": normalize_list(filters.get("keywords")),
            "exclude": normalize_list(filters.get("exclude")),
            "locations": normalize_list(filters.get("locations")),
            "levels": normalize_list(filters.get("levels")),
            "sources": requested_sources,
            "companies": normalize_list(filters.get("companies")),
        },
        weights={
            "keywords": float(weights.get("keywords", 40)),
            "location": float(weights.get("location", 20)),
            "company": float(weights.get("company", 10)),
            "semantic": float(weights.get("semantic", 30)),
        },
        display={
            "limit": int(display.get("limit", 80)),
            "min_score": float(display.get("min_score", 12)),
        },
    )


def normalize_job(job: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "company": str(job.get("company", "")).strip(),
        "position": str(job.get("position", "")).strip(),
        "location": str(job.get("location", "")).strip(),
        "link": str(job.get("link", "")).strip(),
        "source": str(job.get("source", "")).strip(),
        "description": str(job.get("description", "")).strip(),
        "level": str(job.get("level", "mid")).strip().lower() or "mid",
    }
    normalized["score_breakdown"] = {
        "keywords": 0,
        "location": 0,
        "company": 0,
        "semantic": 0,
        "final": 0,
    }
    return normalized


def job_search_blob(job: dict[str, Any]) -> str:
    parts = [
        job.get("company", ""),
        job.get("position", ""),
        job.get("location", ""),
        job.get("description", ""),
    ]
    return " ".join(parts).lower()


def expand_keywords(keywords: list[str]) -> list[str]:
    expanded: set[str] = set()

    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue

        expanded.add(normalized_keyword)

        for family, terms in ROLE_FAMILIES.items():
            if normalized_keyword == family or normalized_keyword in terms:
                expanded.add(family)
                expanded.update(terms)

    return sorted(expanded)


def job_matches_filters(job: dict[str, Any], filters: dict[str, list[str]]) -> bool:
    source_filter = filters.get("sources", [])
    if source_filter and job.get("source") not in source_filter:
        return False

    blob = job_search_blob(job)
    exclude_terms = filters.get("exclude", [])
    if any(term in blob for term in exclude_terms):
        return False

    return True


def compute_keyword_score(job: dict[str, Any], keywords: list[str], expanded: list[str]) -> float:
    # FIX Bug 8: accept pre-computed expanded keywords to avoid redundant work.
    if not keywords:
        return 0.0

    title = normalize_text(job.get("position"))
    description = normalize_text(job.get("description"))

    score = 0.0

    if any(normalize_text(term) in title for term in keywords):
        score = max(score, 92.0)
    if any(term in title for term in expanded):
        score = max(score, 78.0)
    if any(normalize_text(term) in description for term in keywords):
        score = max(score, 58.0)
    if any(term in description for term in expanded):
        score = max(score, 42.0)

    title_hits = sum(1 for term in expanded if term in title)
    description_hits = sum(1 for term in expanded if term in description)
    score += min(22.0, title_hits * 4.0 + description_hits * 1.5)

    return min(100.0, score)


def compute_location_score(job: dict[str, Any], locations: list[str]) -> float:
    if not locations:
        return 0.0

    job_location = normalize_text(job.get("location"))
    if not job_location:
        return 0.0

    best_score = 0.0
    for location in locations:
        if location == job_location:
            best_score = max(best_score, 100.0)
        elif location in job_location:
            best_score = max(best_score, 82.0)
        elif location == "remote" and "remote" in job_location:
            best_score = max(best_score, 92.0)

    return best_score


def compute_company_score(job: dict[str, Any], companies: list[str]) -> float:
    if not companies:
        return 0.0

    company = normalize_text(job.get("company"))
    if not company:
        return 0.0

    if company in companies:
        return 100.0

    if any(target in company for target in companies):
        return 72.0

    return 0.0


def compute_semantic_score(job: dict[str, Any], expanded: list[str]) -> float:
    # FIX Bug 8: accept pre-computed expanded keywords.
    title = normalize_text(job.get("position"))
    description = normalize_text(job.get("description"))

    if not expanded:
        return 0.0

    overlap = 0
    for term in expanded:
        if term in title or term in description:
            overlap += 1

    denominator = max(8, int(len(expanded) * 0.32))
    return min(100.0, (overlap / denominator) * 100.0)


def compute_final_score(
    job: dict[str, Any],
    filters: dict[str, list[str]],
    weights: dict[str, int | float],
) -> dict[str, float]:
    # FIX Bug 8: expand keywords once and reuse across all score functions.
    keywords = filters.get("keywords", [])
    expanded = expand_keywords(keywords)

    keyword_score = compute_keyword_score(job, keywords, expanded)
    location_score = compute_location_score(job, filters.get("locations", []))
    company_score = compute_company_score(job, filters.get("companies", []))
    semantic_score = compute_semantic_score(job, expanded)

    # FIX Bug 2: always include active dimensions in the denominator so that
    # a zero location score actually penalises the final result instead of
    # being silently dropped.  A dimension is "active" whenever the
    # corresponding filter is non-empty (i.e. the user cares about it).
    active_parts: list[tuple[float, float]] = []

    if filters.get("keywords"):
        active_parts.append((keyword_score, float(weights.get("keywords", 0))))
        active_parts.append((semantic_score, float(weights.get("semantic", 0))))

    if filters.get("locations"):
        active_parts.append((location_score, float(weights.get("location", 0))))

    if filters.get("companies"):
        active_parts.append((company_score, float(weights.get("company", 0))))

    total_weight = sum(weight for _, weight in active_parts)
    weighted_sum = sum(score * weight for score, weight in active_parts)
    final_score = weighted_sum / total_weight if total_weight else keyword_score

    return {
        "keywords": round(keyword_score, 2),
        "location": round(location_score, 2),
        "company": round(company_score, 2),
        "semantic": round(semantic_score, 2),
        "final": round(final_score, 2),
    }


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_links: set[str] = set()

    for job in jobs:
        link = job.get("link")
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        deduped.append(job)

    return deduped


def fetch_jobs_for_source(source: str) -> list[dict[str, Any]]:
    sleep(0.08)
    return [normalize_job(job) for job in MOCK_SOURCE_DATA.get(source, [])]


def update_scan_state(**kwargs: Any) -> None:
    with scan_lock:
        scan_state.update(kwargs)


def run_scan(payload: dict[str, Any]) -> None:
    context = build_context(payload)
    active_sources = context.filters["sources"] or AVAILABLE_SOURCES
    collected_jobs: list[dict[str, Any]] = []

    update_scan_state(
        running=True,
        progress=0,
        status="Initialisation du scan...",
        count=0,
        sources=active_sources,
        jobs=[],
        raw_jobs=[],
        request=deepcopy(payload),
    )

    total_steps = max(len(active_sources), 1) + 4

    for index, source in enumerate(active_sources, start=1):
        update_scan_state(
            status=f"Scan {source}...",
            progress=int((index - 1) / total_steps * 100),
        )
        collected_jobs.extend(fetch_jobs_for_source(source))
        update_scan_state(count=len(collected_jobs))

    update_scan_state(
        status="Normalisation et dedoublonnage...",
        progress=int(len(active_sources) / total_steps * 100),
    )
    deduped_jobs = deduplicate_jobs(collected_jobs)

    update_scan_state(
        status="Filtrage des offres...",
        progress=int((len(active_sources) + 1) / total_steps * 100),
        raw_jobs=deepcopy(deduped_jobs),
    )
    filtered_jobs = [job for job in deduped_jobs if job_matches_filters(job, context.filters)]

    update_scan_state(
        status="Scoring des offres...",
        progress=int((len(active_sources) + 2) / total_steps * 100),
    )
    scored_jobs: list[dict[str, Any]] = []
    for job in filtered_jobs:
        job["score_breakdown"] = compute_final_score(job, context.filters, context.weights)
        scored_jobs.append(job)

    scored_jobs.sort(key=lambda item: item["score_breakdown"]["final"], reverse=True)

    update_scan_state(
        running=False,
        progress=100,
        status="Scan termine",
        count=len(scored_jobs),
        jobs=scored_jobs,
    )


@app.get("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


@app.post("/scan")
def start_scan() -> Any:
    # FIX Bug 6: acquire the lock for the full check-and-start sequence so
    # concurrent POST requests cannot both pass the running guard before either
    # thread sets running=True.
    with scan_lock:
        if scan_state["running"]:
            return jsonify({"message": "Un scan est deja en cours"}), 409
        # Mark as running immediately inside the lock so no second request
        # can sneak through before the worker thread calls update_scan_state.
        scan_state["running"] = True

    # FIX Bug 3: always deepcopy the incoming payload so mutations inside
    # run_scan / build_context never corrupt the caller's dict.
    raw_payload = request.get_json(silent=True)
    payload = deepcopy(raw_payload) if raw_payload is not None else deepcopy(DEFAULT_SCAN_PAYLOAD)

    worker = Thread(target=run_scan, args=(payload,), daemon=True)
    worker.start()
    return jsonify(
        {
            "message": "Scan demarre",
            "version": BACKEND_VERSION,
            "sources": payload.get("filters", {}).get("sources", AVAILABLE_SOURCES),
        }
    )


@app.get("/status")
def get_status() -> Any:
    with scan_lock:
        return jsonify(
            {
                "version": BACKEND_VERSION,
                "running": scan_state["running"],
                "progress": scan_state["progress"],
                "status": scan_state["status"],
                "count": scan_state["count"],
                "sources": scan_state["sources"],
            }
        )


@app.get("/jobs")
def get_jobs() -> Any:
    limit_arg = request.args.get("limit")
    min_score_arg = request.args.get("min_score")
    levels_arg = request.args.get("levels", "")
    sources_arg = request.args.get("sources", "")

    with scan_lock:
        jobs = deepcopy(scan_state["jobs"])
        request_payload = deepcopy(scan_state["request"])

    try:
        limit = (
            int(limit_arg)
            if limit_arg is not None
            else int(request_payload["display"].get("limit", 80))
        )
    except (TypeError, ValueError):
        limit = 80

    try:
        min_score = (
            float(min_score_arg)
            if min_score_arg is not None
            else float(request_payload["display"].get("min_score", 12))
        )
    except (TypeError, ValueError):
        min_score = 12

    requested_levels = {normalize_text(level) for level in levels_arg.split(",") if normalize_text(level)}
    requested_sources = {source.strip() for source in sources_arg.split(",") if source.strip()}

    visible_jobs = [job for job in jobs if job["score_breakdown"]["final"] >= min_score]

    if requested_levels:
        visible_jobs = [job for job in visible_jobs if normalize_text(job.get("level")) in requested_levels]

    if requested_sources:
        visible_jobs = [job for job in visible_jobs if job.get("source") in requested_sources]

    visible_jobs = visible_jobs[:limit]
    return jsonify({"jobs": visible_jobs})


@app.get("/health")
def health() -> Any:
    return jsonify(
        {
            "ok": True,
            "version": BACKEND_VERSION,
            "sources": len(AVAILABLE_SOURCES),
            "roles": len(ROLE_LIBRARY),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
