"""
Smart AI Travel Planner — Desktop GUI
Tkinter-based graphical interface that connects to the full recommendation
engine, budget estimator, itinerary builder and Folium map generator.
Features an immersive, translucent frosted-glass theme revealing travel, food,
nature, and country scenes directly behind the text and controls.
"""
import math
import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from pathlib import Path

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageDraw, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── project imports ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from travel.data_loader import load_data
from travel.features import validate_request
from travel.model import train_model
from travel.recommender import recommend_destinations
from travel.itinerary import build_itinerary
from travel.map_builder import build_map

# ── colour palette ── Translucent glass over scenic travel imagery ───────────
BG_DEEP       = "#141216"       # fallback dark
BG_SURFACE    = "#18161c"       # header/status bar
BG_CARD       = "#5a4c3c"       # matches average glass-composite pixel
BG_CARD_SOLID = "#5a4c3c"       # alias
BG_ELEVATED   = "#44392e"       # hover / elevated
BG_INPUT      = "#201c1a"       # entry fields
GLASS_BG      = "#5a4c3c"       # frosted glass card widget bg
GLASS_INNER   = "#4a3e31"       # inner sections
GLASS_HOVER   = "#6e5d4a"       # hover state inside glass
ACCENT_RED    = "#e53935"       # primary red
ACCENT_CRIM   = "#ff1744"       # bright crimson
ACCENT_DARK   = "#b71c1c"       # deep red
ACCENT_CYAN   = "#ff5252"
ACCENT_PURPLE = "#ff8a80"
ACCENT_ROSE   = "#ff6b8a"
ACCENT_AMBER  = "#ff9100"
ACCENT_EMERALD= "#10b981"
ACCENT_GOLD   = "#ffd54f"       # warm gold accent
TEXT_PRIMARY  = "#ffffff"       # pure white for crisp readability
TEXT_SECONDARY= "#f2e8dc"       # warm light text
TEXT_MUTED    = "#c8b8a8"       # warm muted text
BORDER        = "#685745"       # subtle warm glass border
BORDER_LIGHT  = "#e53935"       # crimson accent border
HOVER         = "#4a3a2e"
ACCENT_LIME   = ACCENT_RED


# ── helpers ──────────────────────────────────────────────────────────────────
def money(n):
    """Format a number as Indian Rupee string."""
    n = int(round(n))
    s = str(abs(n))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        formatted = ",".join(groups) + "," + last3
    return f"₹{formatted}" if n >= 0 else f"-₹{formatted}"


class TravelPlannerApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Smart AI Travel Planner")
        self.geometry("1180x820")
        self.minsize(940, 680)
        self.configure(bg=BG_DEEP)
        self.iconname("Smart Travel")

        # ── state ────────────────────────────────────────────────────────────
        self.frames = None
        self.model = None
        self.metrics = None
        self.results = []
        self.selected_index = None

        # ── fonts ────────────────────────────────────────────────────────────
        self.heading_font   = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.subheading_font= tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.label_font     = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.body_font      = tkfont.Font(family="Segoe UI", size=10)
        self.small_font     = tkfont.Font(family="Segoe UI", size=9)
        self.card_title_font= tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.card_body_font = tkfont.Font(family="Segoe UI", size=9)
        self.score_font     = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.money_font     = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.btn_font       = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.menu_font      = tkfont.Font(family="Segoe UI", size=10)

        # ── travel / nature / food background assets ─────────────────────────
        self._bg_orig = None
        bg_path = ROOT / "artifacts" / "travel_bg.jpg"
        if not bg_path.exists():
            bg_path = ROOT / "artifacts" / "travel_banner.jpg"
        if HAS_PIL and bg_path.exists():
            try:
                self._bg_orig = Image.open(bg_path).convert("RGB")
            except Exception:
                self._bg_orig = None

        # Background resize caches
        self._planner_photo = None
        self._planner_last_w = 0
        self._planner_last_h = 0
        self._planner_resize_job = None

        self._results_photo = None
        self._results_last_w = 0
        self._results_last_h = 0
        self._results_resize_job = None

        self._itin_photo = None
        self._itin_last_w = 0
        self._itin_last_h = 0
        self._itin_resize_job = None

        # ── style ttk ───────────────────────────────────────────────────────
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self._configure_styles()

        # ── menu bar ─────────────────────────────────────────────────────────
        self._build_menu()

        # ── layout ───────────────────────────────────────────────────────────
        self._build_ui()

        # ── load data + train model in background ────────────────────────────
        self._show_status("Loading data and training model…")
        threading.Thread(target=self._init_engine, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════
    #  IMAGE COVER GENERATOR  (translucent frosted-glass compositing)
    # ═══════════════════════════════════════════════════════════════════════
    def _create_cover_image(self, width, height, brightness=0.96,
                            panels=None, blur_radius=8):
        """
        Scale and center-crop the background image to cover (width, height).
        Composites translucent frosted-glass panels directly onto the scenic image.
        """
        if not HAS_PIL or self._bg_orig is None or width <= 20 or height <= 20:
            return None
        try:
            img = self._bg_orig
            img_w, img_h = img.size
            scale = max(width / img_w, height / img_h)
            new_w = max(width, int(img_w * scale))
            new_h = max(height, int(img_h * scale))
            resized = img.resize((new_w, new_h), Image.BICUBIC)

            x_offset = max(0, (new_w - width) // 2)
            y_offset = max(0, (new_h - height) // 2)
            cropped = resized.crop((x_offset, y_offset, x_offset + width, y_offset + height))

            if brightness < 0.99:
                enhancer = ImageEnhance.Brightness(cropped)
                cropped = enhancer.enhance(brightness)

            # ── frosted-glass panel compositing ──────────────────────────
            if panels:
                base = cropped.convert("RGBA")
                for p in panels:
                    px, py = max(0, p["x"]), max(0, p["y"])
                    pw = min(p["w"], width - px)
                    ph = min(p["h"], height - py)
                    if pw <= 0 or ph <= 0:
                        continue

                    # 1. Soft blur for frosted glass texture
                    region = base.crop((px, py, px + pw, py + ph))
                    blurred = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))

                    # 2. Gentle darken to keep the scene luminous and vivid
                    blurred_rgb = blurred.convert("RGB")
                    darkener = ImageEnhance.Brightness(blurred_rgb)
                    blurred_rgb = darkener.enhance(0.88)

                    # 3. Translucent dark overlay with fine outline
                    panel_rgba = blurred_rgb.convert("RGBA")
                    alpha = p.get("alpha", 85)
                    glass_fill = (18, 16, 20, alpha)
                    overlay = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
                    draw = ImageDraw.Draw(overlay)
                    radius = p.get("radius", 14)
                    if radius > 0:
                        draw.rounded_rectangle([0, 0, pw, ph], radius=radius,
                                               fill=glass_fill, outline=(255, 255, 255, 45), width=1)
                        # Glowing crimson accent stripe on top
                        draw.rounded_rectangle([0, 0, pw, 3], radius=radius,
                                               fill=(229, 57, 53, 230))
                    else:
                        draw.rectangle([0, 0, pw, ph], fill=glass_fill)

                    # 4. Optional vibe sub-cards drawn into the panel
                    vibe_cards = p.get("vibe_cards", [])
                    for vc in vibe_cards:
                        vx, vy, vw, vh = vc["x"] - px, vc["y"] - py, vc["w"], vc["h"]
                        if 0 <= vx < pw and 0 <= vy < ph:
                            draw.rounded_rectangle(
                                [vx, vy, min(vx + vw, pw), min(vy + vh, ph)],
                                radius=vc.get("radius", 8),
                                fill=(25, 22, 28, 100),
                                outline=(255, 255, 255, 30),
                                width=1
                            )

                    panel_final = Image.alpha_composite(panel_rgba, overlay)
                    base.paste(panel_final, (px, py))

                cropped = base.convert("RGB")

            return ImageTk.PhotoImage(cropped)
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════════════════
    #  STYLES
    # ═══════════════════════════════════════════════════════════════════════
    def _configure_styles(self):
        s = self.style
        s.configure(".", background=BG_DEEP, foreground=TEXT_PRIMARY, font=self.body_font)
        s.configure("TFrame", background=BG_DEEP)
        s.configure("Card.TFrame", background=GLASS_BG)
        s.configure("Surface.TFrame", background=BG_SURFACE)
        s.configure("TLabel", background=BG_DEEP, foreground=TEXT_PRIMARY, font=self.body_font)
        s.configure("Card.TLabel", background=GLASS_BG, foreground=TEXT_PRIMARY)
        s.configure("Heading.TLabel", font=self.heading_font, foreground=ACCENT_CRIM, background=BG_SURFACE)
        s.configure("Sub.TLabel", font=self.subheading_font, foreground=TEXT_PRIMARY, background=GLASS_BG)
        s.configure("Muted.TLabel", foreground=TEXT_SECONDARY, font=self.small_font, background=GLASS_BG)
        s.configure("MutedCard.TLabel", foreground=TEXT_SECONDARY, font=self.small_font, background=GLASS_BG)
        s.configure("Score.TLabel", font=self.score_font, foreground=ACCENT_RED, background=GLASS_BG)
        s.configure("Money.TLabel", font=self.money_font, foreground=ACCENT_RED, background=GLASS_BG)
        s.configure("CardTitle.TLabel", font=self.card_title_font, foreground=TEXT_PRIMARY, background=GLASS_BG)
        s.configure("CardBody.TLabel", font=self.card_body_font, foreground=TEXT_SECONDARY, background=GLASS_BG)
        s.configure("StatusBar.TLabel", background=BG_SURFACE, foreground=TEXT_MUTED, font=self.small_font)
        s.configure("InputLabel.TLabel", font=self.label_font, foreground=TEXT_SECONDARY, background=BG_SURFACE)

        # Combobox — sleek dark translucent fields
        s.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_ELEVATED,
                     foreground=TEXT_PRIMARY, arrowcolor=TEXT_SECONDARY, borderwidth=1,
                     relief="flat", padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", TEXT_PRIMARY)],
              selectbackground=[("readonly", BG_INPUT)],
              selectforeground=[("readonly", TEXT_PRIMARY)])
        self.option_add("*TCombobox*Listbox*Background", BG_INPUT)
        self.option_add("*TCombobox*Listbox*Foreground", TEXT_PRIMARY)
        self.option_add("*TCombobox*Listbox*selectBackground", ACCENT_RED)
        self.option_add("*TCombobox*Listbox*selectForeground", "#ffffff")

        # Entry
        s.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT_PRIMARY,
                     insertcolor=TEXT_PRIMARY, borderwidth=1, relief="flat", padding=6)

        # Notebook
        s.configure("TNotebook", background=BG_SURFACE, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_SURFACE, foreground=TEXT_SECONDARY,
                     padding=[20, 9], font=self.label_font)
        s.map("TNotebook.Tab",
              background=[("selected", BG_ELEVATED)],
              foreground=[("selected", ACCENT_CRIM)])

        # Scrollbar
        s.configure("Vertical.TScrollbar", background=GLASS_BG, troughcolor=BG_SURFACE,
                     arrowcolor=TEXT_MUTED, borderwidth=0)

    # ═══════════════════════════════════════════════════════════════════════
    #  MENU BAR
    # ═══════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        menubar = tk.Menu(self, bg=BG_SURFACE, fg=TEXT_PRIMARY, activebackground=ACCENT_RED,
                          activeforeground="#ffffff", font=self.menu_font, relief="flat", bd=0)

        # File
        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_SURFACE, fg=TEXT_PRIMARY,
                            activebackground=ACCENT_RED, activeforeground="#ffffff",
                            font=self.menu_font)
        file_menu.add_command(label="🔄  Reload Data", command=self._reload_data)
        file_menu.add_command(label="🗺️  Open Last Map", command=self._open_last_map)
        file_menu.add_separator()
        file_menu.add_command(label="❌  Exit", command=self.destroy)
        menubar.add_cascade(label="  File  ", menu=file_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=0, bg=BG_SURFACE, fg=TEXT_PRIMARY,
                            activebackground=ACCENT_RED, activeforeground="#ffffff",
                            font=self.menu_font)
        view_menu.add_command(label="📋  Show Planner", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="📊  Show Results", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="🗓️  Show Itinerary", command=lambda: self.notebook.select(2))
        menubar.add_cascade(label="  View  ", menu=view_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0, bg=BG_SURFACE, fg=TEXT_PRIMARY,
                            activebackground=ACCENT_RED, activeforeground="#ffffff",
                            font=self.menu_font)
        help_menu.add_command(label="📖  About", command=self._show_about)
        help_menu.add_command(label="🌐  GitHub", command=lambda: webbrowser.open(
            "https://github.com/arpitsingh200518-maker/Smart-ai-travel_planner"))
        menubar.add_cascade(label="  Help  ", menu=help_menu)

        self.config(menu=menubar)

    # ═══════════════════════════════════════════════════════════════════════
    #  UI LAYOUT
    # ═══════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        # ── top header ───────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG_SURFACE, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x", padx=0, pady=0)
        header_inner = tk.Frame(header, bg=BG_SURFACE)
        header_inner.pack(fill="x", padx=24, pady=12)

        brand_box = tk.Frame(header_inner, bg=BG_SURFACE)
        brand_box.pack(side="left")
        tk.Label(brand_box, text="✦ Smart AI Travel Planner",
                 font=self.heading_font, fg=ACCENT_CRIM, bg=BG_SURFACE).pack(side="left")
        tk.Label(brand_box, text="  ·  Travel · Food · Nature · Adventure",
                 font=self.small_font, fg=TEXT_MUTED, bg=BG_SURFACE).pack(side="left", padx=(8, 0), pady=(3, 0))

        self.model_label = tk.Label(header_inner, text="Engine: initialising…",
                                    font=self.small_font, fg=TEXT_MUTED, bg=BG_SURFACE)
        self.model_label.pack(side="right")

        # ── notebook (tabs) ──────────────────────────────────────────────────
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(6, 0))

        # Tab 1: Planner
        self.planner_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.planner_tab, text="  🧭  Plan a Trip  ")
        self._build_planner_tab()

        # Tab 2: Results
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="  📊  Results  ")
        self._build_results_tab()

        # Tab 3: Itinerary & Map
        self.itinerary_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.itinerary_tab, text="  🗓️  Itinerary & Map  ")
        self._build_itinerary_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ── status bar ───────────────────────────────────────────────────────
        status_frame = tk.Frame(self, bg=BG_SURFACE, highlightbackground=BORDER, highlightthickness=1)
        status_frame.pack(fill="x", padx=0, pady=0)
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(status_frame, textvariable=self.status_var, font=self.small_font,
                 fg=TEXT_MUTED, bg=BG_SURFACE).pack(side="left", padx=16, pady=6)

    def _on_tab_changed(self, event=None):
        try:
            idx = self.notebook.index("current")
            w = max(self.winfo_width(), 1180)
            h = max(self.winfo_height(), 820)
            if idx == 0:
                self._update_planner_bg(w, h)
            elif idx == 1:
                self._update_results_bg(w, h)
            elif idx == 2:
                self._update_itin_bg(w, h)
        except Exception:
            pass

    # ─── PLANNER TAB (Transparent Canvas Text & Sleek Translucent Overlays)
    def _build_planner_tab(self):
        self.planner_canvas = tk.Canvas(self.planner_tab, bg=BG_DEEP, highlightthickness=0, bd=0)
        self.planner_scrollbar = ttk.Scrollbar(self.planner_tab, orient="vertical",
                                               command=self.planner_canvas.yview)
        self.planner_canvas.configure(yscrollcommand=self.planner_scrollbar.set)
        self.planner_canvas.pack(side="left", fill="both", expand=True)
        self.planner_scrollbar.pack(side="right", fill="y")

        # Background image item on canvas
        self._planner_bg_id = self.planner_canvas.create_image(0, 0, anchor="nw")

        # Mousewheel & configure bindings
        self.planner_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.planner_canvas))
        self.planner_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel(self.planner_canvas))
        self.planner_canvas.bind("<Configure>", self._on_planner_canvas_configure)

        # ── Text items rendered directly on canvas (100% transparent backgrounds) ──
        self._t_title = self.planner_canvas.create_text(
            0, 0, text="✦ Where should we go?", font=self.subheading_font, fill=TEXT_PRIMARY, anchor="w"
        )
        self._t_sub = self.planner_canvas.create_text(
            0, 0, text="Discover tailored trips across nature, food, culture & beaches",
            font=self.small_font, fill=TEXT_SECONDARY, anchor="w"
        )
        self._t_badge = self.planner_canvas.create_text(
            0, 0, text="Full dataset · 20 destinations",
            font=self.small_font, fill=ACCENT_RED, anchor="e"
        )

        # Field Labels
        self._t_lbl_scope = self.planner_canvas.create_text(0, 0, text="TRIP SCOPE", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_people = self.planner_canvas.create_text(0, 0, text="TRAVELLERS", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_days = self.planner_canvas.create_text(0, 0, text="DURATION (DAYS)", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_budget = self.planner_canvas.create_text(0, 0, text="GROUP BUDGET (₹)", font=self.label_font, fill=ACCENT_GOLD, anchor="w")

        self._t_lbl_climate = self.planner_canvas.create_text(0, 0, text="CLIMATE", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_group = self.planner_canvas.create_text(0, 0, text="GROUP TYPE", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_interests = self.planner_canvas.create_text(0, 0, text="INTERESTS (COMMA-SEP)", font=self.label_font, fill=ACCENT_GOLD, anchor="w")
        self._t_lbl_start = self.planner_canvas.create_text(0, 0, text="STARTING CITY", font=self.label_font, fill=ACCENT_GOLD, anchor="w")

        # ── Form Inputs (placed cleanly with create_window) ──
        self.scope_var = tk.StringVar(value="Either")
        self.scope_cb = ttk.Combobox(self.planner_canvas, textvariable=self.scope_var,
                                     values=["Either", "Domestic", "International"], state="readonly")
        self._win_scope = self.planner_canvas.create_window(0, 0, window=self.scope_cb, anchor="nw")

        self.people_var = tk.StringVar(value="2")
        self.people_frame, self.people_entry = self._create_canvas_entry(self.people_var)
        self._win_people = self.planner_canvas.create_window(0, 0, window=self.people_frame, anchor="nw")

        self.days_var = tk.StringVar(value="4")
        self.days_frame, self.days_entry = self._create_canvas_entry(self.days_var)
        self._win_days = self.planner_canvas.create_window(0, 0, window=self.days_frame, anchor="nw")

        self.budget_var = tk.StringVar(value="50000")
        self.budget_frame, self.budget_entry = self._create_canvas_entry(self.budget_var)
        self._win_budget = self.planner_canvas.create_window(0, 0, window=self.budget_frame, anchor="nw")

        self.climate_var = tk.StringVar(value="Any")
        self.climate_cb = ttk.Combobox(self.planner_canvas, textvariable=self.climate_var,
                                       values=["Any", "Cold", "Mild", "Hot", "Dry", "Tropical"], state="readonly")
        self._win_climate = self.planner_canvas.create_window(0, 0, window=self.climate_cb, anchor="nw")

        self.group_var = tk.StringVar(value="Friends")
        self.group_cb = ttk.Combobox(self.planner_canvas, textvariable=self.group_var,
                                     values=["Solo", "Couple", "Family", "Friends"], state="readonly")
        self._win_group = self.planner_canvas.create_window(0, 0, window=self.group_cb, anchor="nw")

        self.interests_var = tk.StringVar(value="nature, food")
        self.interests_frame, self.interests_entry = self._create_canvas_entry(self.interests_var)
        self._win_interests = self.planner_canvas.create_window(0, 0, window=self.interests_frame, anchor="nw")

        self.start_var = tk.StringVar(value="")
        self.start_frame, self.start_entry = self._create_canvas_entry(self.start_var)
        self._win_start = self.planner_canvas.create_window(0, 0, window=self.start_frame, anchor="nw")

        # Disclaimer & Find Destinations Button
        self._t_disclaimer = self.planner_canvas.create_text(
            0, 0, text="All costs are illustrative estimates — not live fares.",
            font=self.small_font, fill=TEXT_MUTED, anchor="w"
        )
        self.find_btn = tk.Button(
            self.planner_canvas, text="  🔍  Find Destinations  ", font=self.btn_font,
            bg=ACCENT_RED, fg="#ffffff", activebackground=ACCENT_DARK,
            activeforeground="#ffffff", relief="flat", bd=0, padx=22, pady=9,
            cursor="hand2", command=self._on_find
        )
        self._bind_hover(self.find_btn, ACCENT_DARK, ACCENT_RED)
        self._win_find_btn = self.planner_canvas.create_window(0, 0, window=self.find_btn, anchor="ne")

        # Separator line 1
        self._sep1_id = self.planner_canvas.create_line(0, 0, 0, 0, fill="#55483a", width=1)

        # Quick presets
        self._t_presets_lbl = self.planner_canvas.create_text(
            0, 0, text="Quick presets:", font=self.small_font, fill=TEXT_MUTED, anchor="w"
        )
        self.preset_btns = []
        self._win_presets = []
        presets = [
            ("🏔️ Mountain Trip", {"scope": "Domestic", "climate": "Cold", "interests": "mountains, adventure, nature", "days": "5", "budget": "40000"}),
            ("🏖️ Beach Getaway", {"scope": "Either", "climate": "Tropical", "interests": "beach, food, nature", "days": "4", "budget": "50000"}),
            ("🏛️ Heritage Tour", {"scope": "Domestic", "climate": "Any", "interests": "history, architecture, culture", "days": "3", "budget": "30000"}),
            ("✈️ International", {"scope": "International", "climate": "Any", "interests": "food, culture, shopping", "days": "5", "budget": "80000"}),
            ("💰 Budget Trip", {"scope": "Either", "climate": "Any", "interests": "nature, food", "days": "3", "budget": "20000"}),
        ]
        for label, vals in presets:
            btn = tk.Button(self.planner_canvas, text=label, font=self.small_font,
                            bg=BG_ELEVATED, fg=TEXT_PRIMARY, activebackground=ACCENT_RED,
                            activeforeground="#ffffff", relief="flat", bd=0,
                            padx=11, pady=5, cursor="hand2",
                            command=lambda v=vals: self._apply_preset(v))
            self._bind_hover(btn, ACCENT_RED, BG_ELEVATED)
            win_id = self.planner_canvas.create_window(0, 0, window=btn, anchor="w")
            self.preset_btns.append(btn)
            self._win_presets.append(win_id)

        # Separator line 2
        self._sep2_id = self.planner_canvas.create_line(0, 0, 0, 0, fill="#55483a", width=1)

        # Explore by Vibe section
        self._t_vibe_title = self.planner_canvas.create_text(
            0, 0, text="✦ EXPLORE BY VIBE", font=("Segoe UI", 9, "bold"), fill=ACCENT_CRIM, anchor="w"
        )
        self._t_vibe_sub = self.planner_canvas.create_text(
            0, 0, text="Click any card to load curated travel filters",
            font=self.small_font, fill=TEXT_MUTED, anchor="w"
        )

        self.vibe_cards_data = [
            ("🌿 Nature & Mountains", "Misty peaks, waterfalls, emerald trails",
             {"scope": "Domestic", "climate": "Cold", "interests": "nature, mountains, waterfalls", "days": "5", "budget": "45000"}),
            ("🍜 Food & Street Delights", "Authentic flavours, night markets & cafes",
             {"scope": "Either", "climate": "Any", "interests": "food, markets, culture", "days": "4", "budget": "50000"}),
            ("✈️ Global Wonders & Sights", "Iconic landmarks, balloon flights & world heritage",
             {"scope": "International", "climate": "Any", "interests": "culture, architecture, sightseeing", "days": "5", "budget": "80000"}),
            ("🏖️ Coastal & Island Escapes", "Turquoise ocean waters, beaches & palm breeze",
             {"scope": "Either", "climate": "Tropical", "interests": "beach, relaxation, nature", "days": "4", "budget": "55000"}),
        ]
        self._vibe_items = []
        for i, (v_title, v_desc, v_preset) in enumerate(self.vibe_cards_data):
            tag = f"vibe_card_{i}"
            t_id = self.planner_canvas.create_text(0, 0, text=v_title, font=("Segoe UI", 10, "bold"), fill=TEXT_PRIMARY, anchor="w", tags=tag)
            d_id = self.planner_canvas.create_text(0, 0, text=v_desc, font=("Segoe UI", 8), fill=TEXT_MUTED, anchor="w", tags=tag)
            a_id = self.planner_canvas.create_text(0, 0, text="Apply vibe →", font=("Segoe UI", 8, "bold"), fill=ACCENT_RED, anchor="w", tags=tag)
            r_id = self.planner_canvas.create_rectangle(0, 0, 0, 0, fill="", outline="", tags=(tag, "clickable"))

            for item_id in (t_id, d_id, a_id, r_id):
                self.planner_canvas.tag_bind(item_id, "<Button-1>", lambda e, p=v_preset: self._apply_preset(p))
                self.planner_canvas.tag_bind(item_id, "<Enter>", lambda e: self.planner_canvas.config(cursor="hand2"))
                self.planner_canvas.tag_bind(item_id, "<Leave>", lambda e: self.planner_canvas.config(cursor=""))

            self._vibe_items.append((t_id, d_id, a_id, r_id))

        # Initial background render
        self.after(10, lambda: self._update_planner_bg(self.winfo_width() or 1180, self.winfo_height() or 820))

    def _create_canvas_entry(self, var):
        """Create a sleek border-highlighted entry frame for canvas window."""
        frame = tk.Frame(self.planner_canvas, bg=BG_INPUT, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        entry = tk.Entry(frame, textvariable=var, font=self.body_font,
                         bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
                         relief="flat", bd=0)
        entry.pack(fill="x", padx=8, pady=6)

        def on_focus_in(e): frame.configure(highlightbackground=ACCENT_RED)
        def on_focus_out(e): frame.configure(highlightbackground=BORDER)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        return frame, entry

    def _reposition_planner_canvas(self, w, h):
        """Reposition all transparent text and input windows relative to window width."""
        panel_w = min(max(w - 60, 600), 1080)
        px0 = max(10, (w - panel_w) // 2)
        py0 = 20

        # Title row
        self.planner_canvas.coords(self._t_title, px0 + 24, py0 + 26)
        self.planner_canvas.coords(self._t_sub, px0 + 245, py0 + 28)
        self.planner_canvas.coords(self._t_badge, px0 + panel_w - 24, py0 + 26)

        # Form grid coordinates
        col_gap = 18
        col_w = max(110, (panel_w - 48 - 3 * col_gap) // 4)

        # Row 0
        c0 = px0 + 24
        c1 = c0 + col_w + col_gap
        c2 = c1 + col_w + col_gap
        c3 = c2 + col_w + col_gap

        y_lbl1 = py0 + 64
        y_inp1 = py0 + 82
        self.planner_canvas.coords(self._t_lbl_scope, c0, y_lbl1)
        self.planner_canvas.coords(self._win_scope, c0, y_inp1)
        self.planner_canvas.itemconfigure(self._win_scope, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_people, c1, y_lbl1)
        self.planner_canvas.coords(self._win_people, c1, y_inp1)
        self.planner_canvas.itemconfigure(self._win_people, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_days, c2, y_lbl1)
        self.planner_canvas.coords(self._win_days, c2, y_inp1)
        self.planner_canvas.itemconfigure(self._win_days, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_budget, c3, y_lbl1)
        self.planner_canvas.coords(self._win_budget, c3, y_inp1)
        self.planner_canvas.itemconfigure(self._win_budget, width=col_w, height=32)

        # Row 1
        y_lbl2 = py0 + 130
        y_inp2 = py0 + 148
        self.planner_canvas.coords(self._t_lbl_climate, c0, y_lbl2)
        self.planner_canvas.coords(self._win_climate, c0, y_inp2)
        self.planner_canvas.itemconfigure(self._win_climate, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_group, c1, y_lbl2)
        self.planner_canvas.coords(self._win_group, c1, y_inp2)
        self.planner_canvas.itemconfigure(self._win_group, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_interests, c2, y_lbl2)
        self.planner_canvas.coords(self._win_interests, c2, y_inp2)
        self.planner_canvas.itemconfigure(self._win_interests, width=col_w, height=32)

        self.planner_canvas.coords(self._t_lbl_start, c3, y_lbl2)
        self.planner_canvas.coords(self._win_start, c3, y_inp2)
        self.planner_canvas.itemconfigure(self._win_start, width=col_w, height=32)

        # Action row
        y_act = py0 + 196
        self.planner_canvas.coords(self._t_disclaimer, c0, y_act + 18)
        self.planner_canvas.coords(self._win_find_btn, px0 + panel_w - 24, y_act)

        # Separator line 1
        y_sep1 = py0 + 252
        self.planner_canvas.coords(self._sep1_id, px0 + 20, y_sep1, px0 + panel_w - 20, y_sep1)

        # Presets row
        y_pres = py0 + 276
        self.planner_canvas.coords(self._t_presets_lbl, c0, y_pres)
        curr_x = c0 + 105
        for win_id in self._win_presets:
            self.planner_canvas.coords(win_id, curr_x, y_pres)
            curr_x += 135

        # Separator line 2
        y_sep2 = py0 + 304
        self.planner_canvas.coords(self._sep2_id, px0 + 20, y_sep2, px0 + panel_w - 20, y_sep2)

        # Vibe row
        y_vibe_title = py0 + 322
        self.planner_canvas.coords(self._t_vibe_title, c0, y_vibe_title)
        self.planner_canvas.coords(self._t_vibe_sub, c0 + 155, y_vibe_title)

        # 4 vibe cards
        vy = py0 + 342
        for i, (t_id, d_id, a_id, r_id) in enumerate(self._vibe_items):
            vx = px0 + 24 + i * (col_w + col_gap)
            self.planner_canvas.coords(t_id, vx + 12, vy + 22)
            self.planner_canvas.coords(d_id, vx + 12, vy + 50)
            self.planner_canvas.coords(a_id, vx + 12, vy + 82)
            self.planner_canvas.coords(r_id, vx, vy, vx + col_w, vy + 100)

        # Set scroll region
        self.planner_canvas.configure(scrollregion=(0, 0, w, max(h, py0 + 475)))

    def _on_planner_canvas_configure(self, event):
        w, h = event.width, event.height
        if w <= 50 or h <= 50:
            return

        self._reposition_planner_canvas(w, h)

        if abs(w - self._planner_last_w) < 15 and abs(h - self._planner_last_h) < 15:
            return

        if self._planner_resize_job:
            self.after_cancel(self._planner_resize_job)
        self._planner_resize_job = self.after(35, lambda: self._update_planner_bg(w, h))

    def _update_planner_bg(self, w, h):
        self._planner_resize_job = None
        self._planner_last_w = w
        self._planner_last_h = h

        panel_w = min(max(w - 60, 600), 1080)
        px0 = max(10, (w - panel_w) // 2)
        py0 = 20
        total_h = max(h, py0 + 480)

        col_gap = 18
        col_w = max(110, (panel_w - 48 - 3 * col_gap) // 4)
        vy = py0 + 342

        vibe_cards = [
            {"x": px0 + 24 + i * (col_w + col_gap), "y": vy, "w": col_w, "h": 100, "radius": 8}
            for i in range(4)
        ]

        glass_panels = [
            {"x": px0, "y": py0, "w": panel_w, "h": 465,
             "radius": 14, "alpha": 85, "vibe_cards": vibe_cards},
        ]

        photo = self._create_cover_image(w, total_h, brightness=0.96,
                                         panels=glass_panels, blur_radius=8)
        if photo:
            self._planner_photo = photo
            self.planner_canvas.itemconfig(self._planner_bg_id, image=self._planner_photo)

        self._reposition_planner_canvas(w, h)

    # ─── RESULTS TAB ─────────────────────────────────────────────────────
    def _build_results_tab(self):
        self.results_container = ttk.Frame(self.results_tab)
        self.results_container.pack(fill="both", expand=True)

        self.results_canvas = tk.Canvas(self.results_container, bg=BG_DEEP,
                                         highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.results_container, orient="vertical",
                                   command=self.results_canvas.yview)

        self._results_bg_id = self.results_canvas.create_image(0, 0, anchor="nw")

        self.results_scroll_frame = tk.Frame(self.results_canvas, bg=GLASS_BG)
        self.results_scroll_frame.bind("<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        self._results_win_id = self.results_canvas.create_window((0, 0), window=self.results_scroll_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        self.results_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.results_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.results_canvas))
        self.results_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel(self.results_canvas))
        self.results_canvas.bind("<Configure>", self._on_results_canvas_configure)

        self._render_results_placeholder()
        self.after(10, lambda: self._update_results_bg(self.winfo_width() or 1180, self.winfo_height() or 820))

    def _render_results_placeholder(self):
        for widget in self.results_scroll_frame.winfo_children():
            widget.destroy()

        card = tk.Frame(self.results_scroll_frame, bg=GLASS_BG,
                        highlightbackground=BORDER_LIGHT, highlightthickness=1)
        card.pack(fill="x", padx=48, pady=60)

        tk.Frame(card, bg=ACCENT_RED, height=3).pack(fill="x")
        inner = tk.Frame(card, bg=GLASS_BG)
        inner.pack(fill="x", padx=32, pady=36)

        tk.Label(inner, text="🔍  Ready to Discover Destinations?",
                 font=self.subheading_font, fg=TEXT_PRIMARY, bg=GLASS_BG).pack(pady=(0, 8))
        tk.Label(inner,
                 text="Enter your travel scope, duration, budget and interests in the Planner tab,\n"
                      "then click 'Find Destinations' to generate top AI-ranked recommendations with full cost breakdowns.",
                 font=self.body_font, fg=TEXT_SECONDARY, bg=GLASS_BG, justify="center").pack(pady=(0, 20))

        go_btn = tk.Button(inner, text="  ← Go to Trip Planner  ", font=self.btn_font,
                           bg=ACCENT_RED, fg="#ffffff", activebackground=ACCENT_DARK,
                           activeforeground="#ffffff", relief="flat", bd=0, padx=20, pady=9,
                           cursor="hand2", command=lambda: self.notebook.select(0))
        go_btn.pack()
        self._bind_hover(go_btn, ACCENT_DARK, ACCENT_RED)

    def _on_results_canvas_configure(self, event):
        w, h = event.width, event.height
        if w <= 50 or h <= 50:
            return
        if hasattr(self, "_results_win_id"):
            self.results_canvas.itemconfigure(self._results_win_id, width=w)

        if abs(w - self._results_last_w) < 20 and abs(h - self._results_last_h) < 20:
            return
        if self._results_resize_job:
            self.after_cancel(self._results_resize_job)
        self._results_resize_job = self.after(50, lambda: self._update_results_bg(w, h))

    def _update_results_bg(self, w, h):
        self._results_resize_job = None
        self._results_last_w = w
        self._results_last_h = h
        req_h = self.results_scroll_frame.winfo_reqheight() if hasattr(self, "results_scroll_frame") else h
        total_h = max(h, req_h + 80)
        glass_panels = [
            {"x": 20, "y": 0, "w": max(w - 40, 200), "h": total_h,
             "radius": 0, "alpha": 85},
        ]
        photo = self._create_cover_image(w, total_h, brightness=0.96,
                                         panels=glass_panels, blur_radius=8)
        if photo:
            self._results_photo = photo
            self.results_canvas.itemconfig(self._results_bg_id, image=self._results_photo)

    # ─── ITINERARY TAB ───────────────────────────────────────────────────
    def _build_itinerary_tab(self):
        self.itin_container = ttk.Frame(self.itinerary_tab)
        self.itin_container.pack(fill="both", expand=True)

        self.itin_canvas = tk.Canvas(self.itin_container, bg=BG_DEEP,
                                      highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.itin_container, orient="vertical",
                                   command=self.itin_canvas.yview)

        self._itin_bg_id = self.itin_canvas.create_image(0, 0, anchor="nw")

        self.itin_scroll_frame = tk.Frame(self.itin_canvas, bg=GLASS_BG)
        self.itin_scroll_frame.bind("<Configure>",
            lambda e: self.itin_canvas.configure(scrollregion=self.itin_canvas.bbox("all")))
        self._itin_win_id = self.itin_canvas.create_window((0, 0), window=self.itin_scroll_frame, anchor="nw")
        self.itin_canvas.configure(yscrollcommand=scrollbar.set)
        self.itin_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.itin_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.itin_canvas))
        self.itin_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel(self.itin_canvas))
        self.itin_canvas.bind("<Configure>", self._on_itin_canvas_configure)

        self._render_itin_placeholder()
        self.after(10, lambda: self._update_itin_bg(self.winfo_width() or 1180, self.winfo_height() or 820))

    def _render_itin_placeholder(self):
        for widget in self.itin_scroll_frame.winfo_children():
            widget.destroy()

        card = tk.Frame(self.itin_scroll_frame, bg=GLASS_BG,
                        highlightbackground=BORDER_LIGHT, highlightthickness=1)
        card.pack(fill="x", padx=48, pady=60)

        tk.Frame(card, bg=ACCENT_RED, height=3).pack(fill="x")
        inner = tk.Frame(card, bg=GLASS_BG)
        inner.pack(fill="x", padx=32, pady=36)

        tk.Label(inner, text="🗓️  Day-by-Day Itinerary & Interactive Map",
                 font=self.subheading_font, fg=TEXT_PRIMARY, bg=GLASS_BG).pack(pady=(0, 8))
        tk.Label(inner,
                 text="Select any destination shortlist card in the Results tab to build\n"
                      "a customized day-by-day travel schedule, activity budgets, and an interactive Folium map.",
                 font=self.body_font, fg=TEXT_SECONDARY, bg=GLASS_BG, justify="center").pack(pady=(0, 20))

        go_btn = tk.Button(inner, text="  ← View Results  ", font=self.btn_font,
                           bg=ACCENT_RED, fg="#ffffff", activebackground=ACCENT_DARK,
                           activeforeground="#ffffff", relief="flat", bd=0, padx=20, pady=9,
                           cursor="hand2", command=lambda: self.notebook.select(1))
        go_btn.pack()
        self._bind_hover(go_btn, ACCENT_DARK, ACCENT_RED)

    def _on_itin_canvas_configure(self, event):
        w, h = event.width, event.height
        if w <= 50 or h <= 50:
            return
        if hasattr(self, "_itin_win_id"):
            self.itin_canvas.itemconfigure(self._itin_win_id, width=w)

        if abs(w - self._itin_last_w) < 20 and abs(h - self._itin_last_h) < 20:
            return
        if self._itin_resize_job:
            self.after_cancel(self._itin_resize_job)
        self._itin_resize_job = self.after(50, lambda: self._update_itin_bg(w, h))

    def _update_itin_bg(self, w, h):
        self._itin_resize_job = None
        self._itin_last_w = w
        self._itin_last_h = h
        req_h = self.itin_scroll_frame.winfo_reqheight() if hasattr(self, "itin_scroll_frame") else h
        total_h = max(h, req_h + 80)
        glass_panels = [
            {"x": 20, "y": 0, "w": max(w - 40, 200), "h": total_h,
             "radius": 0, "alpha": 85},
        ]
        photo = self._create_cover_image(w, total_h, brightness=0.96,
                                         panels=glass_panels, blur_radius=8)
        if photo:
            self._itin_photo = photo
            self.itin_canvas.itemconfig(self._itin_bg_id, image=self._itin_photo)

    # ═══════════════════════════════════════════════════════════════════════
    #  INTERACTION HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    def _bind_hover(self, widget, hover_bg, normal_bg):
        widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal_bg))

    def _bind_mousewheel(self, canvas):
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-int(e.delta/120), "units"))

    def _unbind_mousewheel(self, canvas):
        canvas.unbind_all("<MouseWheel>")

    # ═══════════════════════════════════════════════════════════════════════
    #  ENGINE INIT
    # ═══════════════════════════════════════════════════════════════════════
    def _init_engine(self):
        try:
            self.frames = load_data()
            self.model, self.metrics = train_model()
            acc = self.metrics["synthetic_holdout_accuracy"]
            try:
                self.after(0, lambda: self.model_label.configure(
                    text=f"Engine ready · Classifier accuracy: {acc:.1%}"))
                self.after(0, lambda: self._show_status(
                    f"Ready — {len(self.frames['destinations'])} destinations loaded, model trained"))
            except (tk.TclError, RuntimeError):
                pass
        except Exception as exc:
            try:
                self.after(0, lambda: messagebox.showerror("Initialisation Error", str(exc)))
                self.after(0, lambda: self._show_status(f"Error: {exc}"))
            except (tk.TclError, RuntimeError):
                pass

    def _reload_data(self):
        self._show_status("Reloading data…")
        threading.Thread(target=self._init_engine, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════
    #  FIND DESTINATIONS
    # ═══════════════════════════════════════════════════════════════════════
    def _on_find(self):
        if self.frames is None or self.model is None:
            messagebox.showwarning("Not Ready", "The engine is still loading. Please wait.")
            return

        # Validate inputs
        try:
            people = int(self.people_var.get())
            days = int(self.days_var.get())
            budget = float(self.budget_var.get())
            assert people >= 1 and days >= 1 and budget > 0
        except (ValueError, AssertionError):
            messagebox.showwarning("Invalid Input",
                "Please enter valid numbers:\n• Travellers ≥ 1\n• Days ≥ 1\n• Budget > 0")
            return

        request = {
            "scope": self.scope_var.get().lower(),
            "people": people,
            "days": days,
            "budget": budget,
            "climate": self.climate_var.get().lower(),
            "group_type": self.group_var.get().lower(),
            "interests": self.interests_var.get(),
            "start_city": self.start_var.get() or "Not specified",
        }

        self.find_btn.configure(state="disabled", text="  ⏳  Searching…  ")
        self._show_status("Scoring destinations…")

        def run():
            try:
                results = recommend_destinations(self.frames, request, self.model, limit=5)
                try:
                    self.after(0, lambda: self._display_results(results, request))
                except (tk.TclError, RuntimeError):
                    pass
            except Exception as exc:
                try:
                    self.after(0, lambda: messagebox.showerror("Error", str(exc)))
                except (tk.TclError, RuntimeError):
                    pass
            finally:
                try:
                    self.after(0, lambda: self.find_btn.configure(
                        state="normal", text="  🔍  Find Destinations  "))
                except (tk.TclError, RuntimeError):
                    pass

        threading.Thread(target=run, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════
    #  DISPLAY RESULTS
    # ═══════════════════════════════════════════════════════════════════════
    def _display_results(self, results, request):
        self.results = results
        self.selected_index = None
        self._current_request = request

        # Clear previous results
        for widget in self.results_scroll_frame.winfo_children():
            widget.destroy()

        if not results:
            self._show_status("No destinations match the criteria.")
            card = tk.Frame(self.results_scroll_frame, bg=GLASS_BG,
                            highlightbackground=BORDER_LIGHT, highlightthickness=1)
            card.pack(fill="x", padx=48, pady=60)
            inner = tk.Frame(card, bg=GLASS_BG)
            inner.pack(fill="x", padx=32, pady=36)
            tk.Label(inner, text="🔍  No destinations fit these filters.",
                     font=self.subheading_font, fg=TEXT_PRIMARY, bg=GLASS_BG).pack(pady=(0, 8))
            tk.Label(inner, text="Try adjusting your budget, longer duration, or choosing 'Either' trip scope.",
                     font=self.body_font, fg=TEXT_SECONDARY, bg=GLASS_BG).pack()
            self.notebook.select(1)
            return

        self._show_status(f"Found {len(results)} destination(s) within budget")

        # Header
        header = tk.Frame(self.results_scroll_frame, bg=GLASS_BG)
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(header, text="Your Destination Shortlist", bg=GLASS_BG,
                 fg=TEXT_PRIMARY, font=self.subheading_font, anchor="w").pack(side="left")
        start = request.get("start_city", "")
        meta_text = f"{request['people']} traveller(s) · {request['days']} day(s) · Budget {money(request['budget'])}"
        if start and start != "Not specified":
            meta_text = f"From {start} · " + meta_text
        tk.Label(header, text=meta_text, bg=GLASS_BG, fg=TEXT_MUTED,
                 font=self.small_font).pack(side="right")

        # Destination cards
        rank_labels = ["🏆 Best Match", "🥈 Runner Up", "🥉 Great Option", "✨ Worth a Look", "📌 Also Fits"]
        accent_colors = [ACCENT_RED, ACCENT_CRIM, ACCENT_PURPLE, ACCENT_ROSE, ACCENT_AMBER]

        for i, result in enumerate(results):
            d = result["destination"]
            c = result["costs"]
            color = accent_colors[i % len(accent_colors)]

            card = tk.Frame(self.results_scroll_frame, bg=GLASS_BG,
                            highlightbackground=BORDER, highlightthickness=1, bd=0)
            card.pack(fill="x", padx=24, pady=6)

            # Top bar with accent
            top_bar = tk.Frame(card, bg=color, height=3)
            top_bar.pack(fill="x")
            top_bar.pack_propagate(False)

            # Card content
            content = tk.Frame(card, bg=GLASS_BG)
            content.pack(fill="x", padx=20, pady=16)

            # Row 1: Rank + Name + Score
            row1 = tk.Frame(content, bg=GLASS_BG)
            row1.pack(fill="x")

            rank_lbl = tk.Label(row1, text=rank_labels[i] if i < len(rank_labels) else "📌 Match",
                                bg=GLASS_HOVER, fg=color, font=self.small_font, padx=10, pady=3)
            rank_lbl.pack(side="left")

            tk.Label(row1, text=f"  {d['name']}, {d['country']}",
                     bg=GLASS_BG, fg=TEXT_PRIMARY, font=self.card_title_font).pack(side="left", padx=(8, 0))

            score_frame = tk.Frame(row1, bg=GLASS_BG)
            score_frame.pack(side="right")
            tk.Label(score_frame, text="SCORE", bg=GLASS_BG, fg=TEXT_MUTED,
                     font=("Segoe UI", 8, "bold")).pack()
            tk.Label(score_frame, text=f"{result['score']}",
                     bg=GLASS_BG, fg=color, font=self.score_font).pack()

            # Row 2: Description + Reasons
            row2 = tk.Frame(content, bg=GLASS_BG)
            row2.pack(fill="x", pady=(8, 0))

            tk.Label(row2, text=d.get("description", ""), bg=GLASS_BG,
                     fg=TEXT_SECONDARY, font=self.card_body_font, anchor="w",
                     wraplength=520).pack(side="left", anchor="w")

            reasons_frame = tk.Frame(row2, bg=GLASS_BG)
            reasons_frame.pack(side="right")
            for reason in result["reasons"]:
                r_lbl = tk.Label(reasons_frame, text=f" {reason} ", bg=GLASS_INNER,
                                 fg=ACCENT_RED, font=("Segoe UI", 8, "bold"), padx=6, pady=2)
                r_lbl.pack(side="left", padx=2)

            # Row 3: Cost breakdown
            cost_frame = tk.Frame(content, bg=GLASS_BG)
            cost_frame.pack(fill="x", pady=(12, 0))
            separator = tk.Frame(cost_frame, bg=BORDER, height=1)
            separator.pack(fill="x", pady=(0, 10))

            costs_inner = tk.Frame(cost_frame, bg=GLASS_BG)
            costs_inner.pack(fill="x")
            for col_idx in range(5):
                costs_inner.columnconfigure(col_idx, weight=1)

            cost_items = [
                ("Transport By Flight", money(c["transport"])),
                (f"Stay ({c['rooms']}rm × {c['nights']}nt)", money(c["accommodation"])),
                ("Food", money(c["food"])),
                ("Activities", money(c["activities"])),
            ]
            for ci, (lbl_text, val_text) in enumerate(cost_items):
                tk.Label(costs_inner, text=lbl_text, bg=GLASS_BG, fg=TEXT_MUTED,
                         font=("Segoe UI", 8)).grid(row=0, column=ci, sticky="w", padx=4)
                tk.Label(costs_inner, text=val_text, bg=GLASS_BG, fg=TEXT_PRIMARY,
                         font=("Segoe UI", 10, "bold")).grid(row=1, column=ci, sticky="w", padx=4)

            # Total
            tk.Label(costs_inner, text="TOTAL", bg=GLASS_BG, fg=TEXT_MUTED,
                     font=("Segoe UI", 8)).grid(row=0, column=4, sticky="e", padx=4)
            tk.Label(costs_inner, text=money(c["total"]), bg=GLASS_BG, fg=color,
                     font=self.money_font).grid(row=1, column=4, sticky="e", padx=4)

            # Row 4: Hotel info + Select button
            row4 = tk.Frame(content, bg=GLASS_BG)
            row4.pack(fill="x", pady=(10, 0))

            tk.Label(row4, text=f"🏨 {c['hotel_name']}", bg=GLASS_BG,
                     fg=TEXT_MUTED, font=self.small_font).pack(side="left")

            select_btn = tk.Button(
                row4, text="  Select → Itinerary & Map  ", font=("Segoe UI", 10, "bold"),
                bg=GLASS_HOVER, fg=color, activebackground=color,
                activeforeground=TEXT_PRIMARY, relief="flat", bd=0, padx=16, pady=6,
                cursor="hand2",
                command=lambda idx=i: self._on_select_destination(idx)
            )
            select_btn.pack(side="right")
            self._bind_hover(select_btn, color, GLASS_HOVER)

        # Switch to results tab
        self.notebook.select(1)

    # ═══════════════════════════════════════════════════════════════════════
    #  SELECT DESTINATION → ITINERARY + MAP
    # ═══════════════════════════════════════════════════════════════════════
    def _on_select_destination(self, index):
        if index >= len(self.results):
            return

        self.selected_index = index
        result = self.results[index]
        d = result["destination"]
        request = self._current_request

        self._show_status(f"Building itinerary for {d['name']}…")

        # Build itinerary
        itinerary = build_itinerary(
            d["destination_id"], self.frames["attractions"], request["days"]
        )

        # Build map
        map_path = ROOT / "artifacts" / "travel_map.html"
        build_map(d, itinerary, map_path)

        # Clear itinerary tab
        for widget in self.itin_scroll_frame.winfo_children():
            widget.destroy()

        # Header
        header = tk.Frame(self.itin_scroll_frame, bg=GLASS_BG)
        header.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(header, text=f"📋  Itinerary: {d['name']}, {d['country']}",
                 bg=GLASS_BG, fg=TEXT_PRIMARY, font=self.subheading_font).pack(side="left")

        tk.Label(self.itin_scroll_frame,
                 text=f"{request['days']} day(s) · 7h daily cap · {d.get('description', '')}",
                 bg=GLASS_BG, fg=TEXT_MUTED, font=self.small_font, anchor="w"
                 ).pack(fill="x", padx=24, pady=(0, 16))

        # Day blocks
        category_emojis = {"nature": "🌿", "food": "🍽️", "history": "🏛️",
                           "adventure": "🧗", "culture": "🎭", "architecture": "🏗️",
                           "shopping": "🛍️", "wildlife": "🦁"}
        day_colors = [ACCENT_RED, ACCENT_CRIM, ACCENT_PURPLE, ACCENT_ROSE,
                      ACCENT_AMBER, "#ff5722", "#e91e63"]

        for day_idx, stops in enumerate(itinerary):
            day_color = day_colors[day_idx % len(day_colors)]

            # Day header
            day_header = tk.Frame(self.itin_scroll_frame, bg=GLASS_BG)
            day_header.pack(fill="x", padx=24, pady=(12, 6))
            day_badge = tk.Label(day_header, text=f"  DAY {day_idx + 1}  ",
                                 bg=GLASS_HOVER, fg=day_color,
                                 font=("Segoe UI", 9, "bold"), padx=8, pady=3)
            day_badge.pack(side="left")
            tk.Frame(day_header, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=12, pady=8)

            if not stops:
                free = tk.Label(self.itin_scroll_frame,
                                text="   Free time / travel buffer",
                                bg=GLASS_BG, fg=TEXT_MUTED, font=self.body_font)
                free.pack(fill="x", padx=36, pady=4)
                continue

            for stop in stops:
                stop_frame = tk.Frame(self.itin_scroll_frame, bg=GLASS_BG,
                                      highlightbackground=BORDER, highlightthickness=1)
                stop_frame.pack(fill="x", padx=36, pady=3)
                inner = tk.Frame(stop_frame, bg=GLASS_BG)
                inner.pack(fill="x", padx=16, pady=10)

                cat = stop.get("category", "other")
                emoji = category_emojis.get(cat, "📍")
                tk.Label(inner, text=emoji, bg=GLASS_BG, font=("Segoe UI", 16)).pack(side="left", padx=(0, 12))

                info = tk.Frame(inner, bg=GLASS_BG)
                info.pack(side="left", fill="x", expand=True)
                tk.Label(info, text=stop["name"], bg=GLASS_BG, fg=TEXT_PRIMARY,
                         font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w")
                tk.Label(info, text=f"{cat.title()} · {stop['duration_hours']}h",
                         bg=GLASS_BG, fg=TEXT_MUTED, font=self.small_font, anchor="w").pack(anchor="w")

                tk.Label(inner, text=f"{money(stop['estimated_cost_per_person'])}/pp",
                         bg=GLASS_BG, fg=ACCENT_RED, font=("Segoe UI", 11, "bold")).pack(side="right")

        # Open Map button
        btn_frame = tk.Frame(self.itin_scroll_frame, bg=GLASS_BG)
        btn_frame.pack(fill="x", padx=24, pady=(20, 8))

        map_btn = tk.Button(
            btn_frame, text="  🗺️  Open Interactive Map in Browser  ", font=self.btn_font,
            bg=ACCENT_RED, fg="#ffffff", activebackground=ACCENT_DARK,
            activeforeground="#ffffff", relief="flat", bd=0, padx=20, pady=12,
            cursor="hand2", command=lambda: webbrowser.open(str(map_path))
        )
        map_btn.pack(side="left")
        self._bind_hover(map_btn, ACCENT_DARK, ACCENT_RED)

        new_search_btn = tk.Button(
            btn_frame, text="  🔄  New Search  ", font=self.btn_font,
            bg=GLASS_HOVER, fg=TEXT_PRIMARY, activebackground=BG_ELEVATED,
            activeforeground="#ffffff", relief="flat", bd=0, padx=20, pady=12,
            cursor="hand2", command=lambda: self.notebook.select(0)
        )
        new_search_btn.pack(side="left", padx=(12, 0))
        self._bind_hover(new_search_btn, BG_ELEVATED, GLASS_HOVER)

        # Disclaimer
        tk.Label(self.itin_scroll_frame, bg=GLASS_BG, fg=ACCENT_AMBER, font=self.small_font,
                 text="⚠️  Estimates are illustrative. Verify prices, safety and availability independently.",
                 anchor="w").pack(fill="x", padx=24, pady=(12, 24))

        # Map path info
        tk.Label(self.itin_scroll_frame, bg=GLASS_BG, fg=TEXT_MUTED, font=self.small_font,
                 text=f"Map saved: {map_path}", anchor="w").pack(fill="x", padx=24, pady=(0, 20))

        self._show_status(f"Itinerary built for {d['name']} — map saved to artifacts/travel_map.html")
        self.notebook.select(2)

    # ═══════════════════════════════════════════════════════════════════════
    #  PRESETS
    # ═══════════════════════════════════════════════════════════════════════
    def _apply_preset(self, vals):
        if "scope" in vals: self.scope_var.set(vals["scope"])
        if "climate" in vals: self.climate_var.set(vals["climate"])
        if "interests" in vals: self.interests_var.set(vals["interests"])
        if "days" in vals: self.days_var.set(vals["days"])
        if "budget" in vals: self.budget_var.set(vals["budget"])
        self._show_status("Preset applied — click 'Find Destinations' to search")

    # ═══════════════════════════════════════════════════════════════════════
    #  MISC
    # ═══════════════════════════════════════════════════════════════════════
    def _show_status(self, text):
        self.status_var.set(text)

    def _open_last_map(self):
        path = ROOT / "artifacts" / "travel_map.html"
        if path.exists():
            webbrowser.open(str(path))
        else:
            messagebox.showinfo("No Map", "No map has been generated yet.\nSearch and select a destination first.")

    def _show_about(self):
        messagebox.showinfo("About Smart AI Travel Planner",
            "Smart AI Travel Planner\n\n"
            "A modular Python application that recommends\n"
            "domestic and international trips using local\n"
            "datasets, preference matching, budget constraints,\n"
            "itinerary generation and interactive maps.\n\n"
            "20 destinations · 60 hotels · 120 attractions\n\n"
            "Prices are illustrative estimates.\n"
            "Verify all travel details independently.")


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = TravelPlannerApp()
    app.mainloop()
