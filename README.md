# Smart AI Travel Planner

An offline-first, intelligent travel recommendation, budgeting, and itinerary planning system built with Python, scikit-learn, Folium, and Tkinter.

Smart AI Travel Planner combines machine learning preference scoring, route-specific commercial flight fare lookups, realistic hotel pricing, and daily itinerary scheduling to generate tailored travel packages with interactive multi-layer maps.

---

## Key Highlights

- **100% Local & Offline:** Operates entirely on curated local CSV datasets with zero external API dependencies, network calls, or API keys required.
- **30 Curated Destinations:** 21 domestic Indian destinations and 9 top international gateways with rich climate, interest, and duration metadata.
- **Route-Aware Dynamic Flight Pricing:** 237 origin-destination airfare quotes across 8 major Indian departure hubs (Delhi, Mumbai, Bengaluru, Kolkata, Chennai, Hyderabad, Chandigarh, Ahmedabad) with minimum saver and peak fare ranges.
- **90 Accommodations:** 3 realistic hotel tiers per destination (Budget, Standard, Premium) with per-room-night rates and party-size room allocation ($1\text{ room} / 2\text{ travelers}$).
- **240 Attractions:** 8 iconic sights per destination with GPS coordinates, entry fees, and visit duration estimates.
- **Hybrid AI Recommender:** Random Forest classifier trained on synthetic traveler profiles paired with multi-criteria rule scoring and strict budget cutoffs.
- **Interactive Multi-Layer Maps:** Generates dynamic Folium HTML maps with Esri World Street Map, Topographic, and Satellite tiles, hotel pins, numbered daily stops, and route polylines.
- **Multiple Interfaces:** Includes a modern glassmorphic Tkinter Desktop GUI, a terminal CLI, and a standalone client-side Web application.

---

## System Architecture

```text
smart_ai_travel_planner/
├── artifacts/
│   ├── travel_banner.jpg          # GUI visual assets
│   ├── travel_bg_clean.jpg        # GUI background backdrop
│   └── travel_map.html            # Generated interactive Folium trip map
├── data/
│   ├── attractions.csv            # 240 attractions (8 per destination, GPS & fees)
│   ├── destinations.csv           # 30 destinations (climate, interests, defaults)
│   ├── flights.csv                # 237 route quotes across 8 departure hubs
│   └── hotels.csv                 # 90 accommodations (Budget, Standard, Premium)
├── tests/
│   └── test_planner.py            # Automated unit test suite (12 tests)
├── travel/
│   ├── __init__.py                # Package exports
│   ├── budget.py                  # Route-aware pricing, room math & cost ranges
│   ├── data_loader.py             # CSV schema & relational integrity validation
│   ├── features.py                # Profile encoding & synthetic profile generator
│   ├── itinerary.py               # Day-by-day scheduler with 7-hour daily caps
│   ├── map_builder.py             # Folium interactive map generator (Esri tiles)
│   ├── model.py                   # Random Forest suitability classifier
│   └── recommender.py             # Hybrid recommendation engine & explanations
├── check_setup.py                 # Diagnostic environment & dataset validator
├── gui.py                         # Tkinter Desktop GUI with glassmorphism UI
├── index.html                     # Standalone client-side Web application
├── main.py                        # Terminal interactive CLI entry point
├── README.md                      # Project documentation
└── requirements.txt               # Python package dependencies
```

---

## Core Features

### 1. Hybrid AI Recommendation Engine
- **Feature Vector:** Normalizes 5 core signals: Interest Alignment, Climate Match, Group Compatibility, Trip Duration Fit, and Scope (Domestic vs. International).
- **Machine Learning Model:** Random Forest classifier (`travel/model.py`) trained on synthetic traveler profiles to predict trip suitability probabilities.
- **Transparent Explanations:** Highlights exact reasons for recommendations (e.g., *"matches requested climate"*, *"strong interest alignment"*, *"fits duration"*).

### 2. Route-Aware Dynamic Flight Pricing
- Reads origin-destination commercial airfare quotes from `data/flights.csv`.
- Supports 8 major Indian departure hubs: **Delhi, Mumbai, Bengaluru, Kolkata, Chennai, Hyderabad, Chandigarh, Ahmedabad**.
- Provides realistic **Min Saver** and **Max Peak** fare ranges per seat along with flight duration.
- Gracefully falls back to destination baseline averages when an unlisted departure city is entered.

### 3. Strict Budget Filtering & Cost Breakdown
- Destinations whose estimated total minimum cost exceeds the group's maximum budget are strictly excluded.
- Calculates costs using realistic group dynamics:
  $$\text{Total Trip Cost} = (\text{Flight Fare} \times \text{People}) + (\text{Room Rate} \times \lceil\text{People}/2\rceil \times \text{Nights}) + (\text{Food Rate} \times \text{People} \times \text{Days}) + (\text{Activities} \times \text{People})$$
- Itemizes expenses into Flight, Stay, Food, Activities, and Estimated Total in both the GUI and CLI.

### 4. Smart Day-by-Day Itinerary Scheduler
- Distributes curated attractions across the requested trip duration.
- Enforces a **7-hour maximum daily activity cap** to avoid traveler fatigue.
- Balances attraction categories (cultural, nature, adventure, relaxation) and tracks cumulative visiting costs.

### 5. Multi-Layer Interactive Maps
- Built with **Folium** and saved to `artifacts/travel_map.html`.
- Powered by high-reliability **Esri ArcGIS Online** tiles:
  - *Esri World Street Map* (default high-detail road and transit view)
  - *Esri World Topographic* (terrain and relief contours)
  - *Esri World Imagery* (satellite aerial imagery)
- Pins selected hotels with blue bed markers and day-by-day attractions with numbered color-coded pins connected by route lines.
- Automatically launches in the user's default browser.

---

## Interfaces

### 1. Desktop GUI (`gui.py`)
A desktop application built with Python Tkinter featuring:
- Glassmorphic translucent cards over scenic travel photography.
- City dropdown, duration sliders, traveler counter, and interactive interest chip selectors.
- Live-filtered destination cards showing hotel choices, flight routes, and cost breakdowns.
- Side-by-side day-by-day itinerary drawer with a 1-click **Open Interactive Map** launcher.

Run via:
```powershell
python gui.py
```

### 2. Terminal CLI (`main.py`)
An interactive command-line interface:
- Prompts for departure city, travel scope, group type, traveler count, trip duration, budget, climate, and interests.
- Displays ranked recommendations with match scores and itemized costs.
- Automatically generates the Folium map and detailed itinerary table.

Run via:
```powershell
python main.py
```

### 3. Standalone Web App (`index.html`)
- Completely offline, self-contained HTML/CSS/JS application.
- Mirrors the 30-destination dataset, flight route calculations, and itinerary builder with an embedded Leaflet map.
- Open `index.html` in any modern web browser directly (no local web server required).

---

## Supported Destinations & Hubs

### 8 Departure Hubs
- **North:** Delhi (DEL), Chandigarh (IXC)
- **West:** Mumbai (BOM), Ahmedabad (AMD)
- **South:** Bengaluru (BLR), Chennai (MAA), Hyderabad (HYD)
- **East:** Kolkata (CCU)

### 30 Curated Destinations
| Region | Scope | Destinations |
| :--- | :--- | :--- |
| **North India** | Domestic | Agra, Amritsar, Ladakh, Manali, Rishikesh, Shimla, Srinagar, Varanasi |
| **West India** | Domestic | Goa, Jaipur, Jaisalmer, Udaipur |
| **South India** | Domestic | Coorg, Hampi, Kerala (Kochi/Munnar), Munnar, Mysore, Ooty, Pondicherry |
| **East & Islands** | Domestic | Andaman Islands (Port Blair), Darjeeling |
| **Middle East & Asia** | International | Bangkok, Bali, Dubai, Singapore, Tokyo |
| **Europe** | International | London, Paris, Rome, Zurich |

---

## Setup & Installation

### Requirements
- Python 3.10, 3.11, 3.12, or 3.13
- Windows, macOS, or Linux

### 1. Clone or Extract the Project
Open the project directory in your terminal or VS Code:
```powershell
cd smart_ai_travel_planner
```

### 2. Create and Activate Virtual Environment
On Windows (PowerShell):
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*(On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`)*

### 3. Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Setup
Run the diagnostic script to confirm Python version, libraries, and CSV integrity:
```powershell
python check_setup.py
```

Expected output:
```text
Python: 3.13.x
pandas: 2.2.x
scikit-learn: 1.x
folium: 0.20.x
Destinations: 30
Hotels: 90
Attractions: 240
Flights: 237
Setup check passed.
```

---

## Running the Application

### Launch the Desktop GUI
```powershell
python gui.py
```

### Launch the Console CLI
```powershell
python main.py
```

### Launch the Web Version
Double-click `index.html` or open it in your preferred browser:
```powershell
start index.html
```

---

## Running Automated Tests

The test suite validates data schemas, flight lookups, budget constraints, feature encoders, ML training, and map rendering:

```powershell
python -m unittest discover tests -v
```

All 12 unit tests should execute and pass cleanly:
```text
test_attractions_exist (test_planner.TestTravelPlanner) ... ok
test_budget_math (test_planner.TestTravelPlanner) ... ok
test_data_loader_success (test_planner.TestTravelPlanner) ... ok
test_destinations_not_empty (test_planner.TestTravelPlanner) ... ok
test_feature_vector_bounds (test_planner.TestTravelPlanner) ... ok
test_flights_exist (test_planner.TestTravelPlanner) ... ok
test_hotels_exist (test_planner.TestTravelPlanner) ... ok
test_itinerary_hour_cap (test_planner.TestTravelPlanner) ... ok
test_map_builder_creates_file (test_planner.TestTravelPlanner) ... ok
test_model_trains_and_evaluates (test_planner.TestTravelPlanner) ... ok
test_recommender_filters_over_budget (test_planner.TestTravelPlanner) ... ok
test_route_flight_pricing (test_planner.TestTravelPlanner) ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.65s

OK
```

---

## Contributing & Customization

- **Add Destinations:** Append new rows to `data/destinations.csv`, `data/hotels.csv`, `data/attractions.csv`, and `data/flights.csv`. Ensure foreign-key integrity matches `destination_id`.
- **Adjust Flight Quotes:** Edit `data/flights.csv` to fine-tune route-specific minimum and maximum airfares or add new origin cities.
- **Run Tests:** Always run `python -m unittest discover tests` after modifying CSV datasets to guarantee relational consistency.
