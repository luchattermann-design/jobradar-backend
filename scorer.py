KEYWORDS = [
    "customer success", "customer success manager", "account manager",
    "account executive", "business development", "partnerships",
    "graduate program", "graduate scheme", "management trainee",
    "early careers", "entry level", "client success",
    "relationship manager", "growth associate", "onboarding manager",
]

LOCATION_SCORES = {
    "switzerland": 50, "suisse": 50, "zurich": 50, "zürich": 50,
    "geneva": 50, "genève": 50, "lausanne": 50, "basel": 50,
    "germany": 30, "berlin": 30, "munich": 30, "frankfurt": 30,
    "netherlands": 30, "amsterdam": 30,
    "france": 15, "paris": 20,
    "spain": 10, "barcelona": 15, "madrid": 15,
    "remote": 25, "eu": 15, "europe": 15, "emea": 15,
}

COMPANY_BONUS = [
    "bcg", "mckinsey", "bain", "deloitte", "ey", "pwc", "kpmg",
    "amazon", "google", "microsoft", "salesforce", "hubspot",
    "stripe", "revolut", "n26", "sap", "oracle", "notion",
    "airtable", "figma", "intercom", "zendesk",
]

EXCLUDED_WORDS = [
    "senior", "lead", "director", "head", "principal",
    "vp", "vice president", "chief", "staff", "architect",
]

BAD_WORDS = [
    "intern", "internship", "stage", "working student", "phd", "research",
]

def score_job(job):
    score = 0
    text = " ".join([
        job.get("company", ""),
        job.get("position", ""),
        job.get("location", ""),
        job.get("description", ""),
    ]).lower()

    for keyword in KEYWORDS:
        if keyword.lower() in text:
            score += 10

    for location, value in LOCATION_SCORES.items():
        if location in text:
            score += value

    for company in COMPANY_BONUS:
        if company in text:
            score += 20

    if "remote" in text:
        score += 10

    for word in EXCLUDED_WORDS:
        if word.lower() in text:
            score -= 80

    for word in BAD_WORDS:
        if word.lower() in text:
            score -= 60

    return score
