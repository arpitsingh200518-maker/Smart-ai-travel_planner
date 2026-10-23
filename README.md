# Smart AI Travel Planner

A modular Python console application that recommends domestic and international trips using a local dataset, preference matching, budget constraints, itinerary generation, and an interactive HTML map.

> **Project status:** Educational prototype. Prices are illustrative estimates, and recommendations are based on local data rather than live travel services.

## Overview

Smart AI Travel Planner takes a travel request and ranks destinations that fit the traveller's preferences and total group budget. It is designed to run locally on Windows using Python and does not require an API key for its core workflow.

The project combines a small machine-learning component with explicit recommendation and cost-estimation logic. The model is trained on synthetic traveller profiles generated from preference-matching rules, so its evaluation measures agreement with those generated labels—not actual traveller satisfaction.

## Features

- **Local destination data:** CSV files describe 20 destinations, hotels, and attractions.
- **Preference-based recommendations:** Ranks destinations using trip duration, climate, interests, group type, and domestic/international scope.
- **Budget filtering:** Excludes destinations that exceed the specified group budget.
- **Machine-learning prototype:** Trains a scikit-learn Random Forest suitability classifier on synthetic profiles.
- **Recommendation explanations:** Provides reasons associated with destination ranking.
- **Cost estimates:** Breaks down estimated transport, accommodation, food, and activities.
- **Itinerary generation:** Builds a day-by-day attraction plan with a seven-hour daily activity cap.
- **Interactive map:** Generates an HTML map using Folium.
- **Tests and setup check:** Includes unit tests and a setup diagnostic script.

## How it works

1. The console collects the travel requirements.
2. The data loader reads and validates the local CSV datasets.
3. The model component prepares synthetic training examples and trains the suitability classifier.
4. The recommender scores destinations and applies the strict budget constraint.
5. The budget and itinerary modules estimate trip costs and arrange activities.
6. The map builder creates an interactive HTML map for the planned trip.

This is a local-data prototype. The classifier is one part of the workflow; recommendation scoring, cost estimation, and itinerary construction are handled by separate modules.

## Project structure

```text
smart_ai_travel_planner/
├── artifacts/
│   └── (generated travel_map.html appears here after running)
├── data/
│   ├── attractions.csv
│   ├── destinations.csv
│   └── hotels.csv
├── tests/
│   └── test_planner.py
├── travel/
│   ├── __init__.py
│   ├── budget.py
│   ├── data_loader.py
│   ├── features.py
│   ├── itinerary.py
│   ├── map_builder.py
│   ├── model.py
│   └── recommender.py
├── .gitignore
├── check_setup.py
├── main.py
├── README.md
└── requirements.txt
```

- `main.py` — console entry point.
- `travel/data_loader.py` — loads and validates CSV data.
- `travel/features.py` — request validation and feature helpers.
- `travel/model.py` — generates training examples and trains/evaluates the classifier.
- `travel/recommender.py` — destination scoring, explanations, and budget filtering.
- `travel/budget.py` — trip-cost estimates.
- `travel/itinerary.py` — day-by-day activity scheduling.
- `travel/map_builder.py` — creates the HTML map.
- `data/` — local destination, hotel, and attraction data.
- `tests/` — automated tests.

## Requirements

- Windows, macOS, or Linux with Python 3.10 or later
- Dependencies listed in `requirements.txt`

The commands below are written for Windows PowerShell in VS Code.

## Setup on Windows / VS Code

### 1. Open the project

Extract the ZIP file, then open the extracted `smart_ai_travel_planner` folder in VS Code.

### 2. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install dependencies

With the environment activated:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Check the setup and run tests

```powershell
python check_setup.py
python -m unittest discover -s tests -v
```

### 5. Start the planner

```powershell
python main.py
```

The model trains from synthetic local examples at startup. When map generation is used, the HTML map is saved to `artifacts/travel_map.html`.

## Data and cost estimates

The project uses three CSV files:

- `data/destinations.csv`
- `data/hotels.csv`
- `data/attractions.csv`

You can add destinations by editing the CSV files. Keep the existing column names and data formats unchanged, or update the data loader and tests accordingly.

The current cost estimate uses this general formula:

```text
Estimated total =
    transport per person × travellers
  + (cheapest listed room rate × rooms × nights)
  + (food per person per day × travellers × days)
  + (activities per person × travellers)
```

The application assumes one room per two travellers, rounded up. Transport estimates are generic placeholders and are not route-specific fares or live quotes. The total should not be treated as a booking price. The starting city is collected for context but does not currently alter transport estimates.

## Limitations

- Destination, hotel, and attraction information comes from the bundled local CSV files.
- Prices are illustrative estimates and may not reflect current market prices.
- The application does not query live flights, hotel availability, visa rules, weather, or safety conditions.
- The machine-learning training profiles are synthetic and labelled using explicit preference-matching rules.
- Holdout accuracy measures agreement with those generated labels; it does not establish real-world travel quality.
- Users should independently verify travel requirements, costs, opening hours, and safety information before booking.

These commands let you check the local environment and the tests included in the repository. They do not guarantee that live travel information is accurate, because the current project does not fetch live travel data.

## Possible future improvements

- Integrate verified APIs for live transport, accommodation, weather, and points of interest.
- Add data-source references and timestamps to destination and price records.
- Expand test coverage for invalid input, budget edge cases, and itinerary constraints.
- Compare the current synthetic-label model with simple non-ML baselines.
- Add a graphical interface after the console workflow is stable.

These are potential improvements, not features currently claimed by this repository.

## Contributing

Contributions can improve the dataset, validation, tests, recommendation logic, and documentation. For data changes, preserve the CSV schema and run the test suite before submitting a change.
