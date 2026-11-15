"""Load and validate the local CSV datasets."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

REQUIRED = {
    "destinations.csv": {"destination_id", "name", "country", "scope", "climate", "interests", "group_types", "min_days", "max_days", "transport_per_person", "hotel_price_per_room_night", "food_per_person_day", "activities_per_person", "latitude", "longitude", "description"},
    "hotels.csv": {"destination_id", "hotel_name", "price_per_room_night", "category"},
    "attractions.csv": {"destination_id", "attraction_name", "category", "estimated_cost_per_person", "duration_hours", "latitude", "longitude"},
}

def load_data(data_dir=None):
    folder = Path(data_dir) if data_dir else DATA_DIR
    frames = {}
    for filename, required in REQUIRED.items():
        path = folder / filename
        if not path.exists():
            raise FileNotFoundError(f"Required data file not found: {path}")
        frame = pd.read_csv(path)
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{filename} is missing columns: {', '.join(sorted(missing))}")
        frames[filename.removesuffix(".csv")] = frame
    destination_ids = set(frames["destinations"]["destination_id"].astype(str))
    for key in ("hotels", "attractions"):
        unknown = set(frames[key]["destination_id"].astype(str)) - destination_ids
        if unknown:
            raise ValueError(f"{key}.csv contains unknown destination IDs: {', '.join(sorted(unknown))}")
    return frames
