"""
Smart AI Travel Planner — Desktop GUI
Tkinter-based graphical interface that connects to the full recommendation
engine, budget estimator, itinerary builder and Folium map generator.
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
    from PIL import Image, ImageTk
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

# ── colour palette ── Black & Red theme ──────────────────────────────────────
BG_DEEP      = "#0a0a0a"       # near-black base
BG_SURFACE   = "#121212"       # dark surface
BG_CARD      = "#1a1a1a"       # card background
BG_ELEVATED  = "#252525"       # elevated panels
BG_INPUT     = "#0e0e0e"       # input fields
ACCENT_RED   = "#e53935"       # primary red accent
ACCENT_CRIM  = "#ff1744"       # bright crimson highlight
ACCENT_DARK  = "#b71c1c"       # deep red
ACCENT_CYAN  = "#ff5252"       # light red (replacing cyan)
ACCENT_PURPLE= "#ff8a80"       # salmon pink
ACCENT_ROSE  = "#ff6b8a"       # rose
ACCENT_AMBER = "#ff9100"       # amber/orange for warnings
TEXT_PRIMARY  = "#f5f5f5"      # near-white text
TEXT_SECONDARY= "#9e9e9e"     # muted grey text
TEXT_MUTED    = "#616161"      # very muted text
BORDER       = "#2a2a2a"       # subtle dark border
HOVER        = "#2d1515"       # hover with red tint

# ── backward compat alias ────────────────────────────────────────────────────
ACCENT_LIME  = ACCENT_RED      # all old ACCENT_LIME refs now use red

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
        self.minsize(900, 650)
        self.configure(bg=BG_DEEP)
        self.iconname("Smart Travel")

        # ── state ────────────────────────────────────────────────────────────
        self.frames = None
        self.model = None
        self.metrics = None
        self.results = []
        self.selected_index = None

        # ── fonts ────────────────────────────────────────────────────────────
        self.heading_font   = tkfont.Font(family="Segoe UI", size=22, weight="bold")
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

        # ── banner image ──────────────────────────────────────────────────────
        self._banner_photo = None
        banner_path = ROOT / "artifacts" / "travel_banner.jpg"
        if HAS_PIL and banner_path.exists():
            try:
                img = Image.open(banner_path)
                img = img.resize((1180, 160), Image.LANCZOS)
                self._banner_photo = ImageTk.PhotoImage(img)
            except Exception:
                pass  # fall back gracefully

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
    #  STYLES
    # ═══════════════════════════════════════════════════════════════════════
    def _configure_styles(self):
        s = self.style
        s.configure(".", background=BG_DEEP, foreground=TEXT_PRIMARY, font=self.body_font)
        s.configure("TFrame", background=BG_DEEP)
        s.configure("Card.TFrame", background=BG_CARD)
        s.configure("Surface.TFrame", background=BG_SURFACE)
        s.configure("TLabel", background=BG_DEEP, foreground=TEXT_PRIMARY, font=self.body_font)
        s.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_PRIMARY)
        s.configure("Heading.TLabel", font=self.heading_font, foreground=ACCENT_CRIM, background=BG_SURFACE)
        s.configure("Sub.TLabel", font=self.subheading_font, foreground=TEXT_PRIMARY, background=BG_DEEP)
        s.configure("Muted.TLabel", foreground=TEXT_SECONDARY, font=self.small_font, background=BG_DEEP)
        s.configure("MutedCard.TLabel", foreground=TEXT_SECONDARY, font=self.small_font, background=BG_CARD)
        s.configure("Score.TLabel", font=self.score_font, foreground=ACCENT_RED, background=BG_CARD)
        s.configure("Money.TLabel", font=self.money_font, foreground=ACCENT_RED, background=BG_CARD)
        s.configure("CardTitle.TLabel", font=self.card_title_font, foreground=TEXT_PRIMARY, background=BG_CARD)
        s.configure("CardBody.TLabel", font=self.card_body_font, foreground=TEXT_SECONDARY, background=BG_CARD)
        s.configure("StatusBar.TLabel", background=BG_SURFACE, foreground=TEXT_MUTED, font=self.small_font)
        s.configure("InputLabel.TLabel", font=self.label_font, foreground=TEXT_SECONDARY, background=BG_SURFACE)

        # Combobox
        s.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_ELEVATED,
                     foreground=TEXT_PRIMARY, arrowcolor=TEXT_SECONDARY, borderwidth=1,
                     relief="flat", padding=6)
        s.map("TCombobox", fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", TEXT_PRIMARY)],
              selectbackground=[("readonly", BG_INPUT)],
              selectforeground=[("readonly", TEXT_PRIMARY)])
        self.option_add("*TCombobox*Listbox*Background", BG_CARD)
        self.option_add("*TCombobox*Listbox*Foreground", TEXT_PRIMARY)
        self.option_add("*TCombobox*Listbox*selectBackground", ACCENT_RED)
        self.option_add("*TCombobox*Listbox*selectForeground", BG_DEEP)

        # Entry
        s.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT_PRIMARY,
                     insertcolor=TEXT_PRIMARY, borderwidth=1, relief="flat", padding=6)

        # Notebook
        s.configure("TNotebook", background=BG_DEEP, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT_SECONDARY,
                     padding=[16, 8], font=self.label_font)
        s.map("TNotebook.Tab",
              background=[("selected", BG_ELEVATED)],
              foreground=[("selected", ACCENT_CRIM)])

        # Scrollbar
        s.configure("Vertical.TScrollbar", background=BG_CARD, troughcolor=BG_SURFACE,
                     arrowcolor=TEXT_MUTED, borderwidth=0)

    # ═══════════════════════════════════════════════════════════════════════
    #  MENU BAR
    # ═══════════════════════════════════════════════════════════════════════
    def _build_menu(self):
        menubar = tk.Menu(self, bg=BG_CARD, fg=TEXT_PRIMARY, activebackground=ACCENT_RED,
                          activeforeground="#ffffff", font=self.menu_font, relief="flat", bd=0)

        # File
        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_CARD, fg=TEXT_PRIMARY,
                            activebackground=ACCENT_RED, activeforeground="#ffffff",
                            font=self.menu_font)
        file_menu.add_command(label="🔄  Reload Data", command=self._reload_data)
        file_menu.add_command(label="🗺️  Open Last Map", command=self._open_last_map)
        file_menu.add_separator()
        file_menu.add_command(label="❌  Exit", command=self.destroy)
        menubar.add_cascade(label="  File  ", menu=file_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=0, bg=BG_CARD, fg=TEXT_PRIMARY,
                            activebackground=ACCENT_RED, activeforeground="#ffffff",
                            font=self.menu_font)
        view_menu.add_command(label="📋  Show Planner", command=lambda: self.notebook.select(0))
        view_menu.add_command(label="📊  Show Results", command=lambda: self.notebook.select(1))
        view_menu.add_command(label="🗓️  Show Itinerary", command=lambda: self.notebook.select(2))
        menubar.add_cascade(label="  View  ", menu=view_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0, bg=BG_CARD, fg=TEXT_PRIMARY,
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
        # ── banner image ─────────────────────────────────────────────────────
        if self._banner_photo:
            banner_label = tk.Label(self, image=self._banner_photo, bg=BG_DEEP, bd=0)
            banner_label.pack(fill="x", padx=0, pady=0)

        # ── top header ───────────────────────────────────────────────────────
        header = ttk.Frame(self, style="Surface.TFrame")
        header.pack(fill="x", padx=0, pady=0)
        header_inner = ttk.Frame(header, style="Surface.TFrame")
        header_inner.pack(fill="x", padx=24, pady=14)
        ttk.Label(header_inner, text="✦ Smart AI Travel Planner",
                  style="Heading.TLabel").pack(side="left")
        self.model_label = ttk.Label(header_inner, text="Engine: initialising…",
                                     style="StatusBar.TLabel")
        self.model_label.pack(side="right")

        # ── notebook (tabs) ──────────────────────────────────────────────────
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(8, 0))

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

        # ── status bar ───────────────────────────────────────────────────────
        status_frame = ttk.Frame(self, style="Surface.TFrame")
        status_frame.pack(fill="x", padx=0, pady=0)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var,
                  style="StatusBar.TLabel").pack(side="left", padx=16, pady=6)

    # ─── PLANNER TAB ─────────────────────────────────────────────────────
    def _build_planner_tab(self):
        container = ttk.Frame(self.planner_tab)
        container.pack(fill="both", expand=True, padx=24, pady=20)

        # Title row
        title_frame = ttk.Frame(container)
        title_frame.pack(fill="x", pady=(0, 18))
        ttk.Label(title_frame, text="Where should we go?",
                  font=self.subheading_font, foreground=TEXT_PRIMARY).pack(side="left")
        ttk.Label(title_frame, text="Full dataset · 20 destinations",
                  font=self.small_font, foreground=ACCENT_RED).pack(side="right")

        # Form frame with Surface bg
        form_outer = tk.Frame(container, bg=BG_SURFACE, highlightbackground=BORDER,
                              highlightthickness=1, bd=0)
        form_outer.pack(fill="x", pady=(0, 16))
        form = tk.Frame(form_outer, bg=BG_SURFACE)
        form.pack(fill="x", padx=24, pady=20)

        # Configure 4-column grid
        for c in range(4):
            form.columnconfigure(c, weight=1, uniform="col")

        # ── Row 0 ──
        self._add_label(form, "TRIP SCOPE", 0, 0)
        self.scope_var = tk.StringVar(value="Either")
        self.scope_cb = self._add_combo(form, self.scope_var,
                                        ["Either", "Domestic", "International"], 1, 0)

        self._add_label(form, "TRAVELLERS", 0, 1)
        self.people_var = tk.StringVar(value="2")
        self.people_entry = self._add_entry(form, self.people_var, 1, 1)

        self._add_label(form, "DURATION (DAYS)", 0, 2)
        self.days_var = tk.StringVar(value="4")
        self.days_entry = self._add_entry(form, self.days_var, 1, 2)

        self._add_label(form, "GROUP BUDGET (₹)", 0, 3)
        self.budget_var = tk.StringVar(value="50000")
        self.budget_entry = self._add_entry(form, self.budget_var, 1, 3)

        # ── Row 2 ──
        self._add_label(form, "CLIMATE", 2, 0)
        self.climate_var = tk.StringVar(value="Any")
        self._add_combo(form, self.climate_var,
                        ["Any", "Cold", "Mild", "Hot", "Dry", "Tropical"], 3, 0)

        self._add_label(form, "GROUP TYPE", 2, 1)
        self.group_var = tk.StringVar(value="Friends")
        self._add_combo(form, self.group_var,
                        ["Solo", "Couple", "Family", "Friends"], 3, 1)

        self._add_label(form, "INTERESTS (COMMA-SEP)", 2, 2)
        self.interests_var = tk.StringVar(value="nature, food")
        self.interests_entry = self._add_entry(form, self.interests_var, 3, 2, span=1)

        self._add_label(form, "STARTING CITY", 2, 3)
        self.start_var = tk.StringVar(value="")
        self._add_entry(form, self.start_var, 3, 3)

        # ── Buttons row ──
        btn_frame = tk.Frame(form, bg=BG_SURFACE)
        btn_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(18, 0))

        disclaimer = tk.Label(btn_frame, text="All costs are illustrative estimates — not live fares.",
                              bg=BG_SURFACE, fg=TEXT_MUTED, font=self.small_font, anchor="w")
        disclaimer.pack(side="left")

        self.find_btn = tk.Button(
            btn_frame, text="  🔍  Find Destinations  ", font=self.btn_font,
            bg=ACCENT_RED, fg="#ffffff", activebackground=ACCENT_DARK,
            activeforeground="#ffffff", relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2", command=self._on_find
        )
        self.find_btn.pack(side="right")
        self._bind_hover(self.find_btn, ACCENT_DARK, ACCENT_RED)

        # ── Quick-actions row ──
        quick_frame = tk.Frame(container, bg=BG_DEEP)
        quick_frame.pack(fill="x", pady=(4, 0))

        presets = [
            ("🏔️ Mountain Trip", {"scope": "Domestic", "climate": "Cold", "interests": "mountains, adventure, nature", "days": "5", "budget": "40000"}),
            ("🏖️ Beach Getaway", {"scope": "Either", "climate": "Tropical", "interests": "beach, food, nature", "days": "4", "budget": "50000"}),
            ("🏛️ Heritage Tour", {"scope": "Domestic", "climate": "Any", "interests": "history, architecture, culture", "days": "3", "budget": "30000"}),
            ("✈️ International", {"scope": "International", "climate": "Any", "interests": "food, culture, shopping", "days": "5", "budget": "80000"}),
            ("💰 Budget Trip", {"scope": "Either", "climate": "Any", "interests": "nature, food", "days": "3", "budget": "20000"}),
        ]
        tk.Label(quick_frame, text="Quick presets:", bg=BG_DEEP, fg=TEXT_MUTED,
                 font=self.small_font).pack(side="left", padx=(0, 8))
        for label, vals in presets:
            btn = tk.Button(quick_frame, text=label, font=self.small_font,
                            bg=BG_CARD, fg=TEXT_SECONDARY, relief="flat", bd=0,
                            padx=12, pady=5, cursor="hand2",
                            command=lambda v=vals: self._apply_preset(v))
            btn.pack(side="left", padx=3)
            self._bind_hover(btn, BG_ELEVATED, BG_CARD)

    # ─── RESULTS TAB ─────────────────────────────────────────────────────
    def _build_results_tab(self):
        self.results_container = ttk.Frame(self.results_tab)
        self.results_container.pack(fill="both", expand=True)

        # Scrollable canvas
        self.results_canvas = tk.Canvas(self.results_container, bg=BG_DEEP,
                                         highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.results_container, orient="vertical",
                                   command=self.results_canvas.yview)
        self.results_scroll_frame = ttk.Frame(self.results_canvas)
        self.results_scroll_frame.bind("<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all")))
        self.results_canvas.create_window((0, 0), window=self.results_scroll_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        self.results_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        self.results_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.results_canvas))
        self.results_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel(self.results_canvas))

        # Placeholder
        self.results_placeholder = ttk.Label(self.results_scroll_frame,
            text="\n\n\n\n🔍  Enter your trip details in the Planner tab\n      and click 'Find Destinations' to see results here.",
            font=self.body_font, foreground=TEXT_MUTED, justify="center")
        self.results_placeholder.pack(pady=80)

    # ─── ITINERARY TAB ───────────────────────────────────────────────────
    def _build_itinerary_tab(self):
        self.itin_container = ttk.Frame(self.itinerary_tab)
        self.itin_container.pack(fill="both", expand=True)

        self.itin_canvas = tk.Canvas(self.itin_container, bg=BG_DEEP,
                                      highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.itin_container, orient="vertical",
                                   command=self.itin_canvas.yview)
        self.itin_scroll_frame = ttk.Frame(self.itin_canvas)
        self.itin_scroll_frame.bind("<Configure>",
            lambda e: self.itin_canvas.configure(scrollregion=self.itin_canvas.bbox("all")))
        self.itin_canvas.create_window((0, 0), window=self.itin_scroll_frame, anchor="nw")
        self.itin_canvas.configure(yscrollcommand=scrollbar.set)
        self.itin_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.itin_canvas.bind("<Enter>", lambda e: self._bind_mousewheel(self.itin_canvas))
        self.itin_canvas.bind("<Leave>", lambda e: self._unbind_mousewheel(self.itin_canvas))

        self.itin_placeholder = ttk.Label(self.itin_scroll_frame,
            text="\n\n\n\n🗓️  Select a destination from the Results tab\n      to generate an itinerary and interactive map.",
            font=self.body_font, foreground=TEXT_MUTED, justify="center")
        self.itin_placeholder.pack(pady=80)

    # ═══════════════════════════════════════════════════════════════════════
    #  FORM HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    def _add_label(self, parent, text, row, col):
        lbl = tk.Label(parent, text=text, bg=BG_SURFACE, fg=TEXT_SECONDARY,
                       font=self.label_font, anchor="w")
        lbl.grid(row=row, column=col, sticky="sw", padx=6, pady=(12, 2))

    def _add_combo(self, parent, var, values, row, col, span=1):
        cb = ttk.Combobox(parent, textvariable=var, values=values, state="readonly",
                          font=self.body_font, width=14)
        cb.grid(row=row, column=col, columnspan=span, sticky="ew", padx=6, pady=2)
        return cb

    def _add_entry(self, parent, var, row, col, span=1):
        frame = tk.Frame(parent, bg=BG_INPUT, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        entry_inner = tk.Entry(frame, textvariable=var, font=self.body_font,
                               bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
                               relief="flat", bd=0)
        entry_inner.pack(fill="x", padx=8, pady=6)
        frame.grid(row=row, column=col, columnspan=span, sticky="ew", padx=6, pady=2)

        def on_focus_in(e): frame.configure(highlightbackground=ACCENT_RED)
        def on_focus_out(e): frame.configure(highlightbackground=BORDER)
        entry_inner.bind("<FocusIn>", on_focus_in)
        entry_inner.bind("<FocusOut>", on_focus_out)
        return entry_inner

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
            self.after(0, lambda: self.model_label.configure(
                text=f"Engine ready · Classifier accuracy: {acc:.1%}"))
            self.after(0, lambda: self._show_status(
                f"Ready — {len(self.frames['destinations'])} destinations loaded, model trained"))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Initialisation Error", str(exc)))
            self.after(0, lambda: self._show_status(f"Error: {exc}"))

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
                self.after(0, lambda: self._display_results(results, request))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Error", str(exc)))
            finally:
                self.after(0, lambda: self.find_btn.configure(
                    state="normal", text="  🔍  Find Destinations  "))

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
            lbl = tk.Label(self.results_scroll_frame, bg=BG_DEEP, fg=TEXT_MUTED,
                           font=self.body_font, justify="center",
                           text="\n\n🔍  No destinations fit these filters.\n\n"
                                "Try a higher budget, longer trip, 'Any' climate,\n"
                                "or 'Either' trip scope.")
            lbl.pack(pady=80)
            self.notebook.select(1)
            return

        self._show_status(f"Found {len(results)} destination(s) within budget")

        # Header
        header = tk.Frame(self.results_scroll_frame, bg=BG_DEEP)
        header.pack(fill="x", padx=24, pady=(20, 12))
        tk.Label(header, text=f"Your Destination Shortlist", bg=BG_DEEP,
                 fg=TEXT_PRIMARY, font=self.subheading_font, anchor="w").pack(side="left")
        start = request.get("start_city", "")
        meta_text = f"{request['people']} traveller(s) · {request['days']} day(s) · Budget {money(request['budget'])}"
        if start and start != "Not specified":
            meta_text = f"From {start} · " + meta_text
        tk.Label(header, text=meta_text, bg=BG_DEEP, fg=TEXT_MUTED,
                 font=self.small_font).pack(side="right")

        # Destination cards
        rank_labels = ["🏆 Best Match", "🥈 Runner Up", "🥉 Great Option", "✨ Worth a Look", "📌 Also Fits"]
        accent_colors = [ACCENT_RED, ACCENT_CRIM, ACCENT_PURPLE, ACCENT_ROSE, ACCENT_AMBER]

        for i, result in enumerate(results):
            d = result["destination"]
            c = result["costs"]
            color = accent_colors[i % len(accent_colors)]

            card = tk.Frame(self.results_scroll_frame, bg=BG_CARD,
                            highlightbackground=BORDER, highlightthickness=1, bd=0)
            card.pack(fill="x", padx=24, pady=6)

            # Top bar with accent
            top_bar = tk.Frame(card, bg=color, height=3)
            top_bar.pack(fill="x")
            top_bar.pack_propagate(False)

            # Card content
            content = tk.Frame(card, bg=BG_CARD)
            content.pack(fill="x", padx=20, pady=16)

            # Row 1: Rank + Name + Score
            row1 = tk.Frame(content, bg=BG_CARD)
            row1.pack(fill="x")

            rank_lbl = tk.Label(row1, text=rank_labels[i] if i < len(rank_labels) else "📌 Match",
                                bg=BG_ELEVATED, fg=color, font=self.small_font, padx=10, pady=3)
            rank_lbl.pack(side="left")

            tk.Label(row1, text=f"  {d['name']}, {d['country']}",
                     bg=BG_CARD, fg=TEXT_PRIMARY, font=self.card_title_font).pack(side="left", padx=(8, 0))

            score_frame = tk.Frame(row1, bg=BG_CARD)
            score_frame.pack(side="right")
            tk.Label(score_frame, text="SCORE", bg=BG_CARD, fg=TEXT_MUTED,
                     font=("Segoe UI", 8, "bold")).pack()
            tk.Label(score_frame, text=f"{result['score']}",
                     bg=BG_CARD, fg=color, font=self.score_font).pack()

            # Row 2: Description + Reasons
            row2 = tk.Frame(content, bg=BG_CARD)
            row2.pack(fill="x", pady=(8, 0))

            tk.Label(row2, text=d.get("description", ""), bg=BG_CARD,
                     fg=TEXT_SECONDARY, font=self.card_body_font, anchor="w",
                     wraplength=500).pack(side="left", anchor="w")

            reasons_frame = tk.Frame(row2, bg=BG_CARD)
            reasons_frame.pack(side="right")
            for reason in result["reasons"]:
                r_lbl = tk.Label(reasons_frame, text=f" {reason} ", bg=BG_DEEP,
                                 fg=ACCENT_RED, font=("Segoe UI", 8, "bold"), padx=6, pady=2)
                r_lbl.pack(side="left", padx=2)

            # Row 3: Cost breakdown
            cost_frame = tk.Frame(content, bg=BG_CARD)
            cost_frame.pack(fill="x", pady=(12, 0))
            separator = tk.Frame(cost_frame, bg=BORDER, height=1)
            separator.pack(fill="x", pady=(0, 10))

            costs_inner = tk.Frame(cost_frame, bg=BG_CARD)
            costs_inner.pack(fill="x")
            for col_idx in range(5):
                costs_inner.columnconfigure(col_idx, weight=1)

            cost_items = [
                ("Transport", money(c["transport"])),
                (f"Stay ({c['rooms']}rm × {c['nights']}nt)", money(c["accommodation"])),
                ("Food", money(c["food"])),
                ("Activities", money(c["activities"])),
            ]
            for ci, (lbl_text, val_text) in enumerate(cost_items):
                tk.Label(costs_inner, text=lbl_text, bg=BG_CARD, fg=TEXT_MUTED,
                         font=("Segoe UI", 8)).grid(row=0, column=ci, sticky="w", padx=4)
                tk.Label(costs_inner, text=val_text, bg=BG_CARD, fg=TEXT_PRIMARY,
                         font=("Segoe UI", 10, "bold")).grid(row=1, column=ci, sticky="w", padx=4)

            # Total
            tk.Label(costs_inner, text="TOTAL", bg=BG_CARD, fg=TEXT_MUTED,
                     font=("Segoe UI", 8)).grid(row=0, column=4, sticky="e", padx=4)
            tk.Label(costs_inner, text=money(c["total"]), bg=BG_CARD, fg=color,
                     font=self.money_font).grid(row=1, column=4, sticky="e", padx=4)

            # Row 4: Hotel info + Select button
            row4 = tk.Frame(content, bg=BG_CARD)
            row4.pack(fill="x", pady=(10, 0))

            tk.Label(row4, text=f"🏨 {c['hotel_name']}", bg=BG_CARD,
                     fg=TEXT_MUTED, font=self.small_font).pack(side="left")

            select_btn = tk.Button(
                row4, text="  Select → Itinerary & Map  ", font=("Segoe UI", 10, "bold"),
                bg=BG_ELEVATED, fg=color, activebackground=color,
                activeforeground=BG_DEEP, relief="flat", bd=0, padx=16, pady=6,
                cursor="hand2",
                command=lambda idx=i: self._on_select_destination(idx)
            )
            select_btn.pack(side="right")
            self._bind_hover(select_btn, color, BG_ELEVATED)

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
        header = tk.Frame(self.itin_scroll_frame, bg=BG_DEEP)
        header.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(header, text=f"📋  Itinerary: {d['name']}, {d['country']}",
                 bg=BG_DEEP, fg=TEXT_PRIMARY, font=self.subheading_font).pack(side="left")

        tk.Label(self.itin_scroll_frame,
                 text=f"{request['days']} day(s) · 7h daily cap · {d.get('description', '')}",
                 bg=BG_DEEP, fg=TEXT_MUTED, font=self.small_font, anchor="w"
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
            day_header = tk.Frame(self.itin_scroll_frame, bg=BG_DEEP)
            day_header.pack(fill="x", padx=24, pady=(12, 6))
            day_badge = tk.Label(day_header, text=f"  DAY {day_idx + 1}  ",
                                 bg=BG_ELEVATED, fg=day_color,
                                 font=("Segoe UI", 9, "bold"), padx=8, pady=3)
            day_badge.pack(side="left")
            tk.Frame(day_header, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=12, pady=8)

            if not stops:
                free = tk.Label(self.itin_scroll_frame,
                                text="   Free time / travel buffer",
                                bg=BG_DEEP, fg=TEXT_MUTED, font=self.body_font)
                free.pack(fill="x", padx=36, pady=4)
                continue

            for stop in stops:
                stop_frame = tk.Frame(self.itin_scroll_frame, bg=BG_CARD,
                                      highlightbackground=BORDER, highlightthickness=1)
                stop_frame.pack(fill="x", padx=36, pady=3)
                inner = tk.Frame(stop_frame, bg=BG_CARD)
                inner.pack(fill="x", padx=16, pady=10)

                cat = stop.get("category", "other")
                emoji = category_emojis.get(cat, "📍")
                tk.Label(inner, text=emoji, bg=BG_CARD, font=("Segoe UI", 16)).pack(side="left", padx=(0, 12))

                info = tk.Frame(inner, bg=BG_CARD)
                info.pack(side="left", fill="x", expand=True)
                tk.Label(info, text=stop["name"], bg=BG_CARD, fg=TEXT_PRIMARY,
                         font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w")
                tk.Label(info, text=f"{cat.title()} · {stop['duration_hours']}h",
                         bg=BG_CARD, fg=TEXT_MUTED, font=self.small_font, anchor="w").pack(anchor="w")

                tk.Label(inner, text=f"{money(stop['estimated_cost_per_person'])}/pp",
                         bg=BG_CARD, fg=ACCENT_RED, font=("Segoe UI", 11, "bold")).pack(side="right")

        # Open Map button
        btn_frame = tk.Frame(self.itin_scroll_frame, bg=BG_DEEP)
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
            bg=BG_CARD, fg=TEXT_SECONDARY, activebackground=BG_ELEVATED,
            activeforeground=TEXT_PRIMARY, relief="flat", bd=0, padx=20, pady=12,
            cursor="hand2", command=lambda: self.notebook.select(0)
        )
        new_search_btn.pack(side="left", padx=(12, 0))
        self._bind_hover(new_search_btn, BG_ELEVATED, BG_CARD)

        # Disclaimer
        tk.Label(self.itin_scroll_frame, bg=BG_DEEP, fg=ACCENT_AMBER, font=self.small_font,
                 text="⚠️  Estimates are illustrative. Verify prices, safety and availability independently.",
                 anchor="w").pack(fill="x", padx=24, pady=(12, 24))

        # Map path info
        tk.Label(self.itin_scroll_frame, bg=BG_DEEP, fg=TEXT_MUTED, font=self.small_font,
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
