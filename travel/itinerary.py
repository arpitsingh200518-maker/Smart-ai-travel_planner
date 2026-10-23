"""Simple day-by-day itinerary scheduling with a seven-hour daily cap."""
def build_itinerary(destination_id, attractions, days, daily_cap=7.0):
    rows = attractions[attractions["destination_id"].astype(str) == str(destination_id)].copy()
    if rows.empty:
        return [[] for _ in range(days)]
    rows = rows.sort_values(["duration_hours", "estimated_cost_per_person"], ascending=[True, True])
    itinerary = [[] for _ in range(days)]
    used = [0.0] * days
    day_index = 0
    for _, row in rows.iterrows():
        duration = float(row["duration_hours"])
        if duration > daily_cap:
            continue
        placed = False
        for offset in range(days):
            idx = (day_index + offset) % days
            if used[idx] + duration <= daily_cap:
                itinerary[idx].append({
                    "name": str(row["attraction_name"]),
                    "category": str(row["category"]),
                    "duration_hours": duration,
                    "estimated_cost_per_person": float(row["estimated_cost_per_person"]),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                })
                used[idx] += duration
                day_index = (idx + 1) % days
                placed = True
                break
        if not placed:
            continue
    return itinerary
