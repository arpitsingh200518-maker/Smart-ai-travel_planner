"""
REST API Server for Smart AI Travel Planner.
Exposes live endpoints for destinations, hotels, attractions, live weather,
live currency rates, and the AI recommendation engine.
Uses Python's built-in http.server (no extra dependencies required).
"""
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from travel.data_loader import load_data
from travel.features import validate_request
from travel.model import train_model
from travel.recommender import recommend_destinations
from travel.itinerary import build_itinerary
from travel.live_api import (
    get_live_weather,
    get_live_wiki_summary,
    get_live_currency_rate,
    get_live_flight_search_url,
    get_live_hotel_search_url,
    get_live_attraction_map_url,
    get_destination_live_feed,
)

# Global cache for data & model
FRAMES = None
MODEL = None
METRICS = None

def init_app_state():
    global FRAMES, MODEL, METRICS
    if FRAMES is None or MODEL is None:
        print("[API] Loading dataset and training AI model...")
        FRAMES = load_data()
        MODEL, METRICS = train_model()
        print(f"[API] Ready! Synthetic accuracy: {METRICS['synthetic_holdout_accuracy']:.1%}")

class TravelAPIRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API requests with full CORS support."""

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[API] {self.address_string()} - {args[0]} {args[1]}\n")

    def do_GET(self):
        init_app_state()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        # ── Documentation / Landing Page ──
        if path == "" or path == "/api":
            self._set_headers(200, content_type="text/html")
            doc_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Smart AI Travel Planner — Live REST API</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f1117; color: #e6edf3; padding: 30px; margin: 0; }}
                    .container {{ max-width: 900px; margin: 0 auto; }}
                    h1 {{ color: #ff5252; margin-bottom: 6px; }}
                    .subtitle {{ color: #8b949e; margin-top: 0; margin-bottom: 24px; }}
                    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
                    .method {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 8px; }}
                    .get {{ background: #238636; color: white; }}
                    .post {{ background: #1f6feb; color: white; }}
                    code {{ background: #0d1117; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 13px; }}
                    a {{ color: #58a6ff; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✦ Smart AI Travel Planner — Live REST API</h1>
                    <p class="subtitle">Real-time live details, weather, currency, and AI recommendations for all CSV dataset entries.</p>
                    
                    <div class="card">
                        <h3>Available API Endpoints:</h3>
                        <ul>
                            <li><span class="method get">GET</span> <a href="/api/destinations"><code>/api/destinations</code></a> — All 20 destinations with live weather & flight links</li>
                            <li><span class="method get">GET</span> <a href="/api/destinations/IN01"><code>/api/destinations/{id}</code></a> — Single destination with hotels, attractions & live facts</li>
                            <li><span class="method get">GET</span> <a href="/api/destinations/IN01/live"><code>/api/destinations/{id}/live</code></a> — Real-time live weather, currency & flight booking URLs</li>
                            <li><span class="method get">GET</span> <a href="/api/hotels?destination_id=IN01"><code>/api/hotels?destination_id={id}</code></a> — Hotels with booking links</li>
                            <li><span class="method get">GET</span> <a href="/api/attractions?destination_id=IN01"><code>/api/attractions?destination_id={id}</code></a> — Attractions with Google Maps links</li>
                            <li><span class="method get">GET</span> <a href="/api/weather?lat=15.2993&lon=74.1240"><code>/api/weather?lat={lat}&lon={lon}</code></a> — Live Open-Meteo weather</li>
                            <li><span class="method post">POST</span> <code>/api/recommend</code> — AI trip scoring with live pricing & flight estimates</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(doc_html.encode("utf-8"))
            return

        # ── GET /api/destinations ──
        if path == "/api/destinations":
            dest_list = []
            for _, row in FRAMES["destinations"].iterrows():
                d = row.to_dict()
                lat = float(d.get("latitude", 0.0))
                lon = float(d.get("longitude", 0.0))
                d["live_flight_url"] = get_live_flight_search_url(d["name"])
                d["live_hotel_url"] = get_live_hotel_search_url(d["name"])
                d["coordinates"] = {"latitude": lat, "longitude": lon}
                dest_list.append(d)
            self._set_headers(200)
            self.wfile.write(json.dumps({"count": len(dest_list), "destinations": dest_list}, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # ── GET /api/destinations/<id>/live ──
        if path.startswith("/api/destinations/") and path.endswith("/live"):
            dest_id = path.split("/")[3].upper()
            match = FRAMES["destinations"][FRAMES["destinations"]["destination_id"] == dest_id]
            if match.empty:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Destination ID '{dest_id}' not found."}).encode("utf-8"))
                return
            d = match.iloc[0].to_dict()
            live_data = get_destination_live_feed(d, start_city=params.get("start_city", [""])[0])
            self._set_headers(200)
            self.wfile.write(json.dumps(live_data, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # ── GET /api/destinations/<id> ──
        if path.startswith("/api/destinations/"):
            dest_id = path.split("/")[3].upper()
            match = FRAMES["destinations"][FRAMES["destinations"]["destination_id"] == dest_id]
            if match.empty:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Destination ID '{dest_id}' not found."}).encode("utf-8"))
                return
            d = match.iloc[0].to_dict()
            lat = float(d.get("latitude", 0.0))
            lon = float(d.get("longitude", 0.0))
            
            # Related hotels and attractions
            hotels = FRAMES["hotels"][FRAMES["hotels"]["destination_id"] == dest_id].to_dict(orient="records")
            for h in hotels:
                h["live_booking_url"] = get_live_hotel_search_url(d["name"], h["hotel_name"])
            
            attractions = FRAMES["attractions"][FRAMES["attractions"]["destination_id"] == dest_id].to_dict(orient="records")
            for a in attractions:
                a["live_map_url"] = get_live_attraction_map_url(a["attraction_name"], d["name"])

            payload = {
                "destination": d,
                "coordinates": {"latitude": lat, "longitude": lon},
                "live_weather": get_live_weather(lat, lon),
                "live_currency": get_live_currency_rate(d.get("country", "")),
                "live_wikipedia": get_live_wiki_summary(d.get("name", "")),
                "live_flight_url": get_live_flight_search_url(d.get("name", "")),
                "hotels": hotels,
                "attractions": attractions,
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        # ── GET /api/hotels ──
        if path == "/api/hotels":
            dest_id = params.get("destination_id", [""])[0].upper()
            df = FRAMES["hotels"]
            if dest_id:
                df = df[df["destination_id"] == dest_id]
            hotels_list = df.to_dict(orient="records")
            for h in hotels_list:
                h["live_booking_url"] = get_live_hotel_search_url("", h["hotel_name"])
            self._set_headers(200)
            self.wfile.write(json.dumps({"count": len(hotels_list), "hotels": hotels_list}, indent=2).encode("utf-8"))
            return

        # ── GET /api/attractions ──
        if path == "/api/attractions":
            dest_id = params.get("destination_id", [""])[0].upper()
            df = FRAMES["attractions"]
            if dest_id:
                df = df[df["destination_id"] == dest_id]
            attrs_list = df.to_dict(orient="records")
            for a in attrs_list:
                a["live_map_url"] = get_live_attraction_map_url(a["attraction_name"], "")
            self._set_headers(200)
            self.wfile.write(json.dumps({"count": len(attrs_list), "attractions": attrs_list}, indent=2).encode("utf-8"))
            return

        # ── GET /api/weather ──
        if path == "/api/weather":
            try:
                lat = float(params.get("lat", [0])[0])
                lon = float(params.get("lon", [0])[0])
                w_data = get_live_weather(lat, lon)
                self._set_headers(200)
                self.wfile.write(json.dumps(w_data, indent=2).encode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": f"Invalid coordinates: {e}"}).encode("utf-8"))
            return

        # Not found
        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Endpoint not found", "available_docs": "/api"}).encode("utf-8"))

    def do_POST(self):
        init_app_state()
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/recommend":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8")
                raw_request = json.loads(body) if body else {}

                request = validate_request({
                    "scope": raw_request.get("scope", "either"),
                    "people": int(raw_request.get("people", 2)),
                    "days": int(raw_request.get("days", 4)),
                    "budget": float(raw_request.get("budget", 50000)),
                    "climate": raw_request.get("climate", "any"),
                    "group_type": raw_request.get("group_type", "friends"),
                    "interests": raw_request.get("interests", "nature, food"),
                    "start_city": raw_request.get("start_city", "Anywhere"),
                })

                results = recommend_destinations(FRAMES, request, MODEL, limit=int(raw_request.get("limit", 5)))
                
                # Enrich each result with live weather and live flight search links
                for res in results:
                    d = res["destination"]
                    lat = float(d.get("latitude", 0.0))
                    lon = float(d.get("longitude", 0.0))
                    res["live_weather"] = get_live_weather(lat, lon)
                    res["live_currency"] = get_live_currency_rate(d.get("country", ""))
                    res["live_flight_url"] = get_live_flight_search_url(d["name"], request.get("start_city"))
                    res["live_hotel_url"] = get_live_hotel_search_url(d["name"], res["costs"].get("hotel_name", ""))

                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "request": request,
                    "results_count": len(results),
                    "recommendations": results
                }, ensure_ascii=False, indent=2).encode("utf-8"))
            except Exception as exc:
                self._set_headers(400)
                self.wfile.write(json.dumps({"success": False, "error": str(exc)}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "POST endpoint not found"}).encode("utf-8"))

def run_server(port=5000):
    init_app_state()
    server_address = ("", port)
    httpd = HTTPServer(server_address, TravelAPIRequestHandler)
    print("=" * 60)
    print(f"  ✦ SMART AI TRAVEL PLANNER — REST API SERVER")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print(f"  API Docs / Playground: http://127.0.0.1:{port}/api")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[API] Server stopped.")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    run_server(port)

