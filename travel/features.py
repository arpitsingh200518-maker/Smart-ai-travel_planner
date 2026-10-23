"""Request validation and shared recommendation features."""
VALID_SCOPES = {"domestic", "international", "either"}
VALID_GROUPS = {"solo", "couple", "family", "friends"}
VALID_CLIMATES = {"cold", "mild", "hot", "dry", "tropical", "any"}

def validate_request(request):
    errors = []
    if int(request.get("people", 0)) < 1:
        errors.append("Travellers must be at least 1.")
    if int(request.get("days", 0)) < 1:
        errors.append("Trip duration must be at least 1 day.")
    if float(request.get("budget", 0)) <= 0:
        errors.append("Budget must be greater than zero.")
    if request.get("scope", "either") not in VALID_SCOPES:
        errors.append("Scope must be domestic, international, or either.")
    if request.get("group_type", "solo") not in VALID_GROUPS:
        errors.append("Group type must be solo, couple, family, or friends.")
    if request.get("climate", "any") not in VALID_CLIMATES:
        errors.append("Climate must be cold, mild, hot, dry, tropical, or any.")
    if errors:
        raise ValueError(" ".join(errors))
    normalized = dict(request)
    normalized["people"] = int(normalized["people"])
    normalized["days"] = int(normalized["days"])
    normalized["budget"] = float(normalized["budget"])
    normalized.setdefault("scope", "either")
    normalized.setdefault("group_type", "solo")
    normalized.setdefault("climate", "any")
    normalized.setdefault("interests", ["nature"])
    normalized.setdefault("start_city", "Not specified")
    if isinstance(normalized["interests"], str):
        normalized["interests"] = [x.strip().lower() for x in normalized["interests"].split(",") if x.strip()]
    else:
        normalized["interests"] = [str(x).strip().lower() for x in normalized["interests"] if str(x).strip()]
    return normalized

def feature_vector(destination, request):
    interests = set(str(destination["interests"]).lower().split(","))
    wanted = set(request["interests"])
    group_types = set(str(destination["group_types"]).lower().split(","))
    scope_match = 1.0 if request["scope"] == "either" or destination["scope"] == request["scope"] else 0.0
    climate_match = 1.0 if request["climate"] == "any" or destination["climate"] == request["climate"] else 0.0
    interest_match = len(interests & wanted) / max(1, len(wanted))
    group_match = 1.0 if request["group_type"] in group_types else 0.0
    duration_fit = 1.0 if int(destination["min_days"]) <= request["days"] <= int(destination["max_days"]) else 0.0
    return [interest_match, climate_match, group_match, duration_fit, scope_match]

def rule_label(vector):
    """Synthetic label rule used only to create transparent training targets."""
    interest, climate, group, duration, scope = vector
    score = 0.38*interest + 0.18*climate + 0.18*group + 0.16*duration + 0.10*scope
    return int(score >= 0.52)
