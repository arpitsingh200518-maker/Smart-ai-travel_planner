"""
Generate an interactive HTML map with Folium.
Includes route polylines, destination/hotel markers, day-by-day stops,
and automatic bounding box fitting.
"""
from pathlib import Path
import os
import sys
import webbrowser
import folium

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def open_map(output_path):
    """Open an HTML map file in the user's default browser reliably across platforms."""
    p = Path(output_path).resolve()
    if not p.exists():
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
            return True
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", str(p)], check=True)
            return True
        else:
            import subprocess
            subprocess.run(["xdg-open", str(p)], check=True)
            return True
    except Exception:
        pass
    try:
        return webbrowser.open(p.as_uri())
    except Exception:
        return False

def build_map(destination, itinerary, output_path=None, hotel=None, open_browser=False):
    """
    Build an interactive Folium map for a destination and its day-by-day itinerary.

    Args:
        destination (dict or pd.Series): Destination info with name, country, lat, lon.
        itinerary (list): List of daily stop lists.
        output_path (str or Path, optional): Output path for the HTML file.
        hotel (dict, optional): Optional accommodation details to pin on map.
        open_browser (bool, optional): If True, open the generated map in browser immediately.

    Returns:
        Path: Resolved path to the generated HTML map.
    """
    if output_path is None:
        output_path = ROOT / "artifacts" / "travel_map.html"

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    dest_name = str(destination.get("name", "Destination"))
    dest_country = str(destination.get("country", ""))
    dest_desc = str(destination.get("description", ""))

    try:
        dest_lat = float(destination.get("latitude", 0.0))
        dest_lon = float(destination.get("longitude", 0.0))
    except (ValueError, TypeError):
        dest_lat, dest_lon = 0.0, 0.0

    center = [dest_lat, dest_lon]
    map_object = folium.Map(location=center, zoom_start=11, control_scale=True, tiles=None)

    # 1. Primary Street Map (Esri — completely free, reliable, no 403 tile blocking on local file://)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, TomTom",
        name="🗺️ Street Map",
        max_zoom=19,
        control=True,
    ).add_to(map_object)

    # 2. Topographic Map (terrain, mountains, contours)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; National Geographic, USGS",
        name="🏔️ Topographic",
        max_zoom=19,
        control=True,
    ).add_to(map_object)

    # 3. Satellite Imagery (aerial views)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, GeoEye, Earthstar Geographics",
        name="🛰️ Satellite",
        max_zoom=19,
        control=True,
    ).add_to(map_object)

    folium.LayerControl(position="topright", collapsed=True).add_to(map_object)

    # Destination central marker
    dest_popup = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 180px;">
        <h4 style="margin: 0 0 6px 0; color: #b71c1c;">📍 {dest_name}, {dest_country}</h4>
        <p style="margin: 0; font-size: 12px; color: #444;">{dest_desc}</p>
    </div>
    """
    folium.Marker(
        center,
        tooltip=f"<b>{dest_name}</b> ({dest_country})",
        popup=folium.Popup(dest_popup, max_width=300),
        icon=folium.Icon(color="red", icon="star", prefix="glyphicon"),
    ).add_to(map_object)

    points = [center]

    # Optional Hotel Marker
    if hotel:
        try:
            h_lat = float(hotel.get("latitude", dest_lat))
            h_lon = float(hotel.get("longitude", dest_lon))
            h_name = hotel.get("name", "Hotel")
            h_cost = hotel.get("cost_per_night", "")
            h_popup = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 160px;">
                <h4 style="margin: 0 0 4px 0; color: #1565c0;">🏨 {h_name}</h4>
                <p style="margin: 0; font-size: 12px; color: #555;">Accommodation · ₹{h_cost}/night</p>
            </div>
            """
            folium.Marker(
                [h_lat, h_lon],
                tooltip=f"🏨 {h_name}",
                popup=folium.Popup(h_popup, max_width=250),
                icon=folium.Icon(color="blue", icon="home", prefix="glyphicon"),
            ).add_to(map_object)
            points.append([h_lat, h_lon])
        except (ValueError, TypeError):
            pass

    # Day-by-day markers and connecting routes
    day_colors = ["darkred", "green", "purple", "orange", "cadetblue", "darkgreen", "blue"]
    cat_emojis = {
        "nature": "🌿", "food": "🍽️", "history": "🏛️",
        "adventure": "🧗", "culture": "🎭", "architecture": "🏗️",
        "shopping": "🛍️", "wildlife": "🦁"
    }

    for day_index, day in enumerate(itinerary or [], start=1):
        color = day_colors[(day_index - 1) % len(day_colors)]
        day_points = []

        for stop_index, stop in enumerate(day, start=1):
            try:
                s_lat = float(stop.get("latitude", dest_lat))
                s_lon = float(stop.get("longitude", dest_lon))
            except (ValueError, TypeError):
                continue

            pt = [s_lat, s_lon]
            points.append(pt)
            day_points.append(pt)

            s_name = str(stop.get("name", "Attraction"))
            s_cat = str(stop.get("category", "sight")).lower()
            s_dur = stop.get("duration_hours", 1.0)
            s_cost = stop.get("estimated_cost_per_person", 0)
            emoji = cat_emojis.get(s_cat, "📍")

            stop_popup = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif; min-width: 180px;">
                <div style="background: {color}; color: white; padding: 3px 8px; font-size: 11px; font-weight: bold; border-radius: 3px; display: inline-block; margin-bottom: 6px;">
                    DAY {day_index} · STOP {stop_index}
                </div>
                <h4 style="margin: 0 0 4px 0; color: #222;">{emoji} {s_name}</h4>
                <div style="font-size: 12px; color: #555; line-height: 1.5;">
                    <b>Category:</b> {s_cat.title()}<br>
                    <b>Duration:</b> {s_dur}h<br>
                    <b>Est. Cost:</b> ₹{s_cost:,} per person
                </div>
            </div>
            """

            folium.Marker(
                pt,
                tooltip=f"Day {day_index}: {emoji} {s_name}",
                popup=folium.Popup(stop_popup, max_width=280),
                icon=folium.Icon(color=color, icon="info-sign", prefix="glyphicon"),
            ).add_to(map_object)

        # Draw itinerary route line connecting the day's stops
        if len(day_points) >= 2:
            folium.PolyLine(
                day_points,
                color=color,
                weight=3,
                opacity=0.8,
                dash_array="6, 6",
                tooltip=f"Day {day_index} Route",
            ).add_to(map_object)

    # Automatically fit the map view to show all points
    if len(points) > 1:
        map_object.fit_bounds(points, padding=(30, 30))

    map_object.save(str(output))

    if open_browser:
        open_map(output)

    return output

if __name__ == "__main__":
    print("=" * 60)
    print("  SMART AI TRAVEL PLANNER -- MAP BUILDER DEMO")
    print("=" * 60)

    try:
        from travel.data_loader import load_data
        from travel.itinerary import build_itinerary

        frames = load_data()
        dest = frames["destinations"].iloc[0].to_dict()
        itinerary = build_itinerary(dest["destination_id"], frames["attractions"], days=3)

        out_file = ROOT / "artifacts" / "travel_map.html"
        print(f"\n[+] Building demo map for: {dest['name']}, {dest['country']}")
        print(f"[+] Total days: {len(itinerary)}")
        total_stops = sum(len(day) for day in itinerary)
        print(f"[+] Total stops: {total_stops}")

        saved_path = build_map(dest, itinerary, output_path=out_file, open_browser=True)
        print(f"\n[OK] Map successfully built and saved to:\n     {saved_path}")
        print("[OK] Opened in default web browser!")
    except Exception as exc:
        print(f"\n[ERROR] Error building map: {exc}")
        import traceback
        traceback.print_exc()
