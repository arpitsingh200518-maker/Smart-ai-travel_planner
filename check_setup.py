"""Quick environment and dataset diagnostic."""
import sys
from pathlib import Path

def main():
    print("Python:", sys.version.split()[0])
    root = Path(__file__).resolve().parent
    missing = [str(root / "data" / name) for name in ("destinations.csv", "hotels.csv", "attractions.csv") if not (root / "data" / name).exists()]
    if missing:
        print("Missing data files:")
        print("\n".join(missing))
        return 1
    try:
        import pandas, sklearn, folium
        from travel.data_loader import load_data
        frames = load_data()
        print("pandas:", pandas.__version__)
        print("scikit-learn:", sklearn.__version__)
        print("folium:", folium.__version__)
        print("Destinations:", len(frames["destinations"]))
        print("Hotels:", len(frames["hotels"]))
        print("Attractions:", len(frames["attractions"]))
    except Exception as exc:
        print("Setup check failed:", exc)
        print("Install dependencies with: python -m pip install -r requirements.txt")
        return 1
    print("Setup check passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
