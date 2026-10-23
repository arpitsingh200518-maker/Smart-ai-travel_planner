"""Generate an interactive HTML map with Folium."""
from pathlib import Path
import folium

def build_map(destination, itinerary, output_path):
    points = [(float(destination["latitude"]), float(destination["longitude"]))]
    for day in itinerary:
        for stop in day:
            points.append((stop["latitude"], stop["longitude"]))
    center = points[0]
    map_object = folium.Map(location=center, zoom_start=6, control_scale=True)
    folium.Marker(center, tooltip=str(destination["name"]), popup=str(destination["description"]), icon=folium.Icon(color="blue", icon="info-sign")).add_to(map_object)
    colors = ["red", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen"]
    for day_index, day in enumerate(itinerary, start=1):
        for stop in day:
            folium.Marker(
                [stop["latitude"], stop["longitude"]],
                tooltip=stop["name"],
                popup=f"Day {day_index}: {stop['name']}<br>{stop['duration_hours']} hours",
                icon=folium.Icon(color=colors[(day_index-1) % len(colors)], icon="map-marker"),
            ).add_to(map_object)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    map_object.save(str(output))
    return output
