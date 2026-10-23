"""Rank destinations, explain matches, and enforce the hard budget limit."""
from .features import feature_vector, validate_request
from .budget import estimate_budget
from .model import suitability_probability

def recommend_destinations(frames, request, model, limit=5):
    request = validate_request(request)
    destinations = frames["destinations"]
    results = []
    for _, row in destinations.iterrows():
        destination = row.to_dict()
        if request["scope"] != "either" and destination["scope"] != request["scope"]:
            continue
        costs = estimate_budget(destination, frames["hotels"], request)
        if costs["total"] > request["budget"]:
            continue  # Strict rule: never recommend an over-budget destination.
        vector = feature_vector(destination, request)
        ml_probability = suitability_probability(model, vector)
        interest, climate, group, duration, scope = vector
        score = 100 * (0.38*interest + 0.18*climate + 0.18*group + 0.16*duration + 0.10*scope)
        # ML contributes a smaller tie-break influence; the rule-based score remains explainable.
        final_score = 0.8*score + 20*ml_probability
        reasons = []
        if interest > 0: reasons.append("matches some requested interests")
        if climate: reasons.append("matches climate preference")
        if group: reasons.append("suits the selected group type")
        if duration: reasons.append("fits the requested trip duration")
        if not reasons: reasons.append("fits the budget, but preference overlap is limited")
        results.append({
            "destination": destination, "costs": costs, "score": round(final_score, 2),
            "ml_probability": round(ml_probability, 3), "reasons": reasons,
        })
    results.sort(key=lambda item: (item["score"], -item["costs"]["total"]), reverse=True)
    return results[:max(0, int(limit))]
