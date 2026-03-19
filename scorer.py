def normalize_text(value):
    return str(value or "").strip()


def normalize_text_lower(value):
    return normalize_text(value).lower()


ROLE_FAMILIES = {
    "customer success": [
        "customer success",
        "client success",
        "customer experience",
        "account management",
        "account manager",
        "customer onboarding",
        "customer retention",
    ],
    "account manager": [
        "account manager",
        "account executive",
        "client partner",
        "customer success",
        "relationship manager",
    ],
    "business development": [
        "business development",
        "sales development",
        "partnerships",
        "growth",
        "revenue",
        "lead generation",
        "bdr",
        "sdr",
    ],
}


def expand_keywords(keywords):
    expanded = set()

    for keyword in keywords or []:
        keyword = normalize_text_lower(keyword)
        if not keyword:
            continue

        expanded.add(keyword)

        for family_name, family_terms in ROLE_FAMILIES.items():
            if keyword == family_name or keyword in family_terms:
                expanded.update(family_terms)

    return list(expanded)


def normalize_job(job, default_source=""):
    return {
        "company": normalize_text(job.get("company")),
        "position": normalize_text(job.get("position")),
        "location": normalize_text(job.get("location")),
        "link": normalize_text(job.get("link")),
        "source": normalize_text(job.get("source")) or default_source,
        "description": normalize_text(job.get("description")),
        "score_breakdown": {
            "keywords": 0,
            "location": 0,
            "company": 0,
            "semantic": 0,
            "final": 0,
        },
    }


def deduplicate_jobs(jobs):
    seen_links = set()
    deduped = []

    for job in jobs:
        link = normalize_text(job.get("link"))
        if not link or link in seen_links:
            continue
        seen_links.add(link)
        deduped.append(job)

    return deduped


def job_blob(job):
    return " ".join([
        normalize_text_lower(job.get("company")),
        normalize_text_lower(job.get("position")),
        normalize_text_lower(job.get("location")),
        normalize_text_lower(job.get("description")),
    ])


def job_matches_filters(job, filters):
    blob = job_blob(job)

    selected_sources = filters.get("sources", [])
    if selected_sources and job.get("source") not in selected_sources:
        return False

    exclude_terms = [normalize_text_lower(x) for x in filters.get("exclude", []) if x]
    if any(term in blob for term in exclude_terms):
        return False

    return True


def compute_keyword_score(job, keywords):
    expanded = expand_keywords(keywords)
    if not expanded:
        return 0

    title = normalize_text_lower(job.get("position"))
    description = normalize_text_lower(job.get("description"))

    score = 0
    for term in expanded:
        if term in title:
            score += 20
        elif term in description:
            score += 10

    return min(score, 100)


def compute_location_score(job, locations):
    if not locations:
        return 0

    job_location = normalize_text_lower(job.get("location"))
    best = 0

    for location in locations:
        location = normalize_text_lower(location)

        if location == job_location:
            best = max(best, 100)
        elif location in job_location:
            best = max(best, 80)
        elif location == "remote" and "remote" in job_location:
            best = max(best, 90)

    return best


def compute_company_score(job, companies):
    if not companies:
        return 0

    company = normalize_text_lower(job.get("company"))
    for target in companies:
        target = normalize_text_lower(target)
        if target == company:
            return 100
        if target in company:
            return 70

    return 0


def compute_semantic_score(job, keywords):
    expanded = expand_keywords(keywords)
    if not expanded:
        return 0

    title = normalize_text_lower(job.get("position"))
    title_tokens = set(title.replace("/", " ").replace("-", " ").split())

    overlap = 0
    for term in expanded:
        term_tokens = set(term.split())
        if term in title:
            overlap += 2
        elif term_tokens & title_tokens:
            overlap += 1

    return min(overlap * 12, 100)


def compute_final_score(job, filters, weights):
    keyword_score = compute_keyword_score(job, filters.get("keywords", []))
    location_score = compute_location_score(job, filters.get("locations", []))
    company_score = compute_company_score(job, filters.get("companies", []))
    semantic_score = compute_semantic_score(job, filters.get("keywords", []))

    wk = float(weights.get("keywords", 40))
    wl = float(weights.get("location", 20))
    wc = float(weights.get("company", 15))
    ws = float(weights.get("semantic", 25))

    total_weight = wk + wl + wc + ws
    if total_weight == 0:
        final_score = 0
    else:
        final_score = (
            keyword_score * wk +
            location_score * wl +
            company_score * wc +
            semantic_score * ws
        ) / total_weight

    return {
        "keywords": round(keyword_score, 2),
        "location": round(location_score, 2),
        "company": round(company_score, 2),
        "semantic": round(semantic_score, 2),
        "final": round(final_score, 2),
    }
