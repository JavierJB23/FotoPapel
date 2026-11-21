"""Revelo: organiza fotografías y páginas PDF para imprimir sin complicaciones."""
from __future__ import annotations

import os
import queue
import math
import subprocess
import sys
import threading
import tempfile
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
from pathlib import Path

import revelo_dialogs as messagebox

from PIL import Image, ImageTk, ImageOps, ImageDraw
from editorial_art import header_art

from processor import (
    ExportOptions, PAPER_SIZES, SUPPORTED_EXTENSIONS, FIT_MODES, export, render_print_image,
    pixel_size, source_dimensions, page_groups, render_layout_page,
)
from pdf_import import import_pdf_pages, matched_paper
from pdf_sources import recover_sources
from mobile_import import PhoneTransferServer
from project_io import save_project, load_project, ProjectError
from special_pages import KINDS, THEMES, CUSTOM_THEME, validate_special_spec, save_special_thumbnail
from ordering_rules import cover_path, anchored_order, move_item, click_move
from custom_editor import edit_custom_page
from photo_editor_ui import edit_photo
from thumbnail_preview import render_photo_thumbnail
from photo_edits import validate_edits, has_edits, apply_edits
import qrcode
from advanced_layout import (TEMPLATES, NUMBER_POSITIONS, NUMBER_FORMATS, CAPTION_PLACEMENTS,
                             validate_caption, has_caption, numbers_for_groups, book_spreads)
from caption_editor import edit_caption
from layout_editor import edit_sheet, validate_layout_item
from book_renderer import render_book
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # El código también puede probarse sin TkDND.
    DND_FILES = None
    TkinterDnD = None

APP_NAME = "Revelo"
BG = "#0B1422"
SURFACE = "#142236"
SURFACE_2 = "#1B2D43"
BORDER = "#2C415A"
ACCENT = "#4CD9B5"
ACCENT_DARK = "#123B3D"
TEXT = "#F1F6FB"
MUTED = "#9CB1C7"
WARNING = "#F8CB82"


def app_asset(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return root / name


class ScrollingArea(tk.Frame):
    def __init__(self, parent: tk.Widget, *, background: str = SURFACE):
        super().__init__(parent, bg=background)
        self.canvas = tk.Canvas(self, bg=background, borderwidth=0, highlightthickness=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=background)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._update_scrollregion)
        self.canvas.bind("<Configure>", self._update_inner_width)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.inner.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"))

    def _update_scrollregion(self, _evt=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_inner_width(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def bind_wheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._wheel, add="+")
        for child in widget.winfo_children():
            self.bind_wheel_recursive(child)


class ReveloApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Revelo · Estudio Editorial · Fotos y PDF listos para imprimir")
        self.root.geometry("1270x845")
        self.root.minsize(1100, 690)
        self.root.configure(bg=BG)
        self.paths: list[Path] = []
        self.path_labels: dict[Path, str] = {}
        self.pdf_origins: dict[Path, Path] = {}
        self.recovered_pdf_sources: set[Path] = set()
        self.pdf_temp = tempfile.TemporaryDirectory(prefix="Revelo_PDF_")
        self.special_temp = tempfile.TemporaryDirectory(prefix="Revelo_Paginas_")
        self.special_pages: dict[Path, dict] = {}
        self.photo_edits: dict[Path, dict] = {}  # instrucciones no destructivas
        self.captions: dict[Path, dict] = {}
        self.layout_items: dict[Path,dict] = {}
        self.preview_book = False
        self.photo_editor_window = None
        self.mobile_temp = tempfile.TemporaryDirectory(prefix="Revelo_Movil_")
        self.project_temp = tempfile.TemporaryDirectory(prefix="Revelo_Proyecto_")
        self.project_path: Path | None = None
        self.mobile_server: PhoneTransferServer | None = None
        self.mobile_window: tk.Toplevel | None = None
        self.mobile_qr: ImageTk.PhotoImage | None = None
        self.mobile_status = tk.StringVar(value="Esperando fotografías…")
        self.mobile_received_count = 0
        self.pending_mobile: list[Path] = []
        self.pages: list[Path] = []
        self.thumbnails: dict[Path, ImageTk.PhotoImage] = {}
        self.thumbnails_small: dict[Path, ImageTk.PhotoImage] = {}
        self._thumbnail_settings_job = None
        self._restoring_project = False
        self.sheet_thumbnails: dict[tuple, ImageTk.PhotoImage] = {}
        self.details: dict[Path, tuple[int, int]] = {}
        self.selected: Path | None = None  # selección de biblioteca
        self.order_selected: Path | None = None  # independiente, selección en lista ordenada
        self.drag_origin: str | None = None
        self.drag_source: Path | None = None
        self.drag_begin: tuple[int, int] | None = None
        self.drag_ghost: tk.Toplevel | None = None
        self.is_dragging = False
        self.is_busy = False
        self.output_path: Path | None = None
        self.updates: queue.Queue[tuple] = queue.Queue()
        self.library_cols = 3
        self.preview_window: tk.Toplevel | None = None
        self.preview_canvas: tk.Canvas | None = None
        self.preview_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_index = 0
        self.preview_resize_job: str | None = None

        self.paper = tk.StringVar(value="A4")
        self.orientation = tk.StringVar(value="Automática")
        self.fit = tk.StringVar(value="Ajustar (sin recortar)")
        self.paper_background = tk.StringVar(value="Blanco")
        self.paper_background_color = tk.StringVar(value="#FFFFFF")
        self.dpi = tk.StringVar(value="300")
        self.output_format = tk.StringVar(value="PDF")
        self.binding = tk.StringVar(value="No")
        self.per_sheet = tk.StringVar(value="1")
        self.layout_template = tk.StringVar(value="Cuadrícula")
        self.numbering_enabled = tk.BooleanVar(value=False)
        self.numbering_position = tk.StringVar(value="Exterior")
        self.numbering_skip_special = tk.BooleanVar(value=True)
        self.numbering_start = tk.IntVar(value=1)
        self.numbering_format = tk.StringVar(value="1")
        self.layout_info = tk.StringVar(value="Una fotografía por hoja en Word y PDF")
        self.overview = tk.StringVar(value="A4 · 210 × 297 mm · 2480 × 3508 px a 300 PPP")
        self.feedback = tk.StringVar(value="Listo para cargar fotos y PDF.")
        self.count_var = tk.StringVar(value="0 elementos")
        self.page_count_var = tk.StringVar(value="0 páginas")
        self.percent_text = tk.StringVar(value="(0 %)")
        self.preview_page_text = tk.StringVar(value="")
        self.preview_detail_text = tk.StringVar(value="")

        self._style()
        self._layout()
        self._configure_file_drop()
        self._update_overview()
        self.per_sheet.trace_add("write", self._on_per_sheet_changed)
        self.layout_template.trace_add("write", self._on_template_changed)
        # Las tarjetas muestran siempre el papel y la orientación actuales.
        for var in (self.paper, self.orientation, self.fit, self.binding,
                    self.paper_background, self.paper_background_color):
            var.trace_add("write", self._on_thumbnail_settings_changed)
        # Cambiar el fondo general sustituye los ajustes locales anteriores,
        # para que el mismo color se vea en todas las ventanas.
        self.paper_background.trace_add("write", self._sync_free_background_from_main)
        self.paper_background_color.trace_add("write", self._sync_free_background_from_main)
        self.root.after(120, self._poll)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Custom.TCombobox", fieldbackground=SURFACE_2, background=SURFACE_2,
            foreground=TEXT, bordercolor=BORDER, arrowcolor=ACCENT,
            padding=8, borderwidth=1,
        )
        style.map(
            "Custom.TCombobox", fieldbackground=[("readonly", SURFACE_2)],
            foreground=[("readonly", TEXT)], selectbackground=[("readonly", SURFACE_2)],
            selectforeground=[("readonly", TEXT)],
        )
        style.configure(
            "Compact.TCombobox", fieldbackground=SURFACE_2, background=SURFACE_2,
            foreground=TEXT, bordercolor=BORDER, arrowcolor=ACCENT,
            font=("Segoe UI", 9), padding=3, borderwidth=1,
        )
        style.map(
            "Compact.TCombobox", fieldbackground=[("disabled", "#101B2A"), ("readonly", SURFACE_2)],
            background=[("disabled", "#101B2A"), ("readonly", SURFACE_2)],
            foreground=[("disabled", "#65788B"), ("readonly", TEXT)],
            arrowcolor=[("disabled", "#566778"), ("readonly", ACCENT)],
            selectbackground=[("readonly", SURFACE_2)],
            selectforeground=[("readonly", TEXT)],
        )
        style.configure(
            "Custom.Vertical.TScrollbar", background=SURFACE_2,
            troughcolor=SURFACE, bordercolor=SURFACE, arrowcolor=MUTED,
        )
        style.configure(
            "Revelo.Horizontal.TProgressbar", troughcolor=SURFACE_2,
            background=ACCENT, darkcolor=ACCENT, lightcolor=ACCENT,
            bordercolor=BORDER, thickness=15, relief="flat",
        )

    def _label(self, parent, text, *, size=10, color=TEXT, weight="normal", bg=None,
               family="Segoe UI", **kw):
        return tk.Label(parent, text=text, font=(family, size, weight), fg=color,
                        bg=bg or parent.cget("bg"), **kw)

    def _button(self, parent, text, command, *, accent=False, small=False, **kwargs):
        """Botón de escritorio con respuesta al pasar el puntero.

        Conserva tk.Button para no romper el estado, el teclado ni los
        callbacks existentes de Revelo.
        """
        normal_bg = ACCENT if accent else SURFACE_2
        hover_bg = "#75EAD5" if accent else "#29465A"
        button = tk.Button(
            parent, text=text, command=command,
            bg=normal_bg, fg=BG if accent else TEXT,
            activebackground=hover_bg,
            activeforeground=BG if accent else TEXT,
            font=("Segoe UI", 9 if small else 10, "bold"),
            bd=0, relief="flat", cursor="hand2",
            highlightbackground="#42657A" if not accent else ACCENT,
            highlightcolor=ACCENT, highlightthickness=1,
            padx=11 if small else 16, pady=5 if small else 9, **kwargs,
        )
        def hover(_event):
            if button.cget("state") != "disabled":
                button.configure(bg=hover_bg)
        def normal(_event):
            button.configure(bg=normal_bg)
        button.bind("<Enter>", hover, add="+")
        button.bind("<Leave>", normal, add="+")
        return button

    def _layout(self):
        # Cabecera editorial contenida: mantiene el área de trabajo central.
        header = tk.Frame(self.root, bg=BG, padx=25, pady=10)
        header.pack(fill="x")
        left = tk.Frame(header, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        with Image.open(app_asset("logo_cabecera.png")) as logo:
            self.header_icon = ImageTk.PhotoImage(logo.convert("RGBA").resize((55, 55), Image.Resampling.LANCZOS))
        tk.Label(left, image=self.header_icon, bg=BG, borderwidth=0).pack(side="left", padx=(0, 14))
        htext = tk.Frame(left, bg=BG)
        htext.pack(side="left")
        self._label(htext, "Revelo", size=25, weight="bold", family="Georgia").pack(anchor="w")
        self._label(htext, "Tus fotos y documentos, listos para imprimir", color="#B3C6D2",
                    size=10, family="Georgia", weight="normal").pack(anchor="w")
        # Arte del concepto B aprobado: decoración que no bloquea controles.
        # Integrado en Python: la compilación en carpeta no necesita assets extra.
        self.editorial_header_image = ImageTk.PhotoImage(header_art(290, 66))
        tk.Label(left, image=self.editorial_header_image, bg=BG,
                 borderwidth=0).pack(side="right", padx=(6, 8))
        project_buttons = tk.Frame(header, bg=BG)
        project_buttons.pack(side="right", padx=(10, 0))
        self.save_project_btn = self._button(project_buttons, "Guardar proyecto", self.save_project_dialog, small=True)
        self.save_project_btn.pack(side="right")
        self.open_project_btn = self._button(project_buttons, "Abrir proyecto", self.open_project_dialog, small=True)
        self.open_project_btn.pack(side="right", padx=(0, 8))

        setting_outer = tk.Frame(self.root, bg=BG, padx=24)
        setting_outer.pack(fill="x")
        settings = tk.Frame(setting_outer, bg=SURFACE, padx=17, pady=6,
                            highlightbackground="#3E6679", highlightthickness=1)
        settings.pack(fill="x")
        editorial_heading = tk.Frame(settings, bg=SURFACE)
        editorial_heading.pack(fill="x", pady=(0, 3))
        self._label(editorial_heading, "▤", size=14, color=ACCENT).pack(side="left", padx=(0, 8))
        self._label(editorial_heading, "Configuración de impresión", size=14,
                    family="Georgia", weight="bold").pack(side="left")
        self._label(editorial_heading, "  │  FORMATO · ENCAJE · CALIDAD · PAPEL",
                    color=MUTED, size=8).pack(side="left", padx=(6, 0))
        # Los selectores ocupan solo el espacio necesario para su opción más larga.
        # Los siete grupos permanecen en una única fila, incluso en ventanas compactas.
        # Se conservan las variables y callbacks anteriores; es solo maquetación.
        row = tk.Frame(settings, bg=SURFACE)
        row.pack(fill="x")
        self.settings_controls_row = row
        fields = [
            ("TAMAÑO DE IMPRESIÓN", self.paper, list(PAPER_SIZES), 136),
            ("ORIENTACIÓN", self.orientation, ["Automática", "Vertical", "Horizontal"], 94),
            ("ENCAJE EN EL PAPEL", self.fit, list(FIT_MODES), 190),
            ("CALIDAD", self.dpi, ["150", "300", "600"], 54),
            ("EXPORTAR COMO", self.output_format, ["PDF", "Word", "Imágenes (mismo formato)"], 183),
            ("MÁRGENES DE ENCUADERNACIÓN", self.binding, ["No", "Sí"], 190),
            ("FONDO DEL PAPEL", self.paper_background,
             ["Blanco", "Crema", "Aguamarina", "Azul noche", "Difuminado", "Personalizado"], 140),
        ]
        settings_holders = []
        for column, (caption, variable, choices, width) in enumerate(fields):
            row.grid_columnconfigure(column, minsize=width)
            holder = tk.Frame(row, bg=SURFACE, width=width, height=41)
            settings_holders.append(holder)
            holder.grid_propagate(False)  # Evita desplegables desmesurados.
            holder.grid(row=0, column=column, sticky="new", padx=(0, 0 if column == 6 else 6))
            heading = self._label(holder, caption, color=MUTED, size=8, weight="bold")
            heading.pack(anchor="w", pady=(0, 4))
            if column == 6:
                self.paper_background_label = heading
            if column == 6:
                fondo_row = tk.Frame(holder, bg=SURFACE)
                fondo_row.pack(fill="x")
                self.paper_background_combo = ttk.Combobox(
                    fondo_row, textvariable=variable, values=choices,
                    state="readonly", style="Compact.TCombobox", width=1,
                    font=("Segoe UI", 9))
                self.paper_background_combo.pack(side="left", fill="x", expand=True)
                # El selector personalizado sigue accesible sin crear otra fila.
                self.paper_background_button = tk.Button(
                    fondo_row, text="…", command=self.choose_paper_background_color,
                    bg=SURFACE_2, fg=ACCENT, font=("Segoe UI", 10, "bold"),
                    bd=0, relief="flat", cursor="hand2", width=2,
                    padx=1, pady=4, highlightthickness=0)
            else:
                ttk.Combobox(holder, values=choices, textvariable=variable,
                             state="readonly", style="Compact.TCombobox", width=1,
                             font=("Segoe UI", 9)).pack(fill="x")

        # Aprovechar espacio en monitores grandes sin que ninguno de los textos
        # largos se corte; al estrechar la ventana se recuperan los mínimos.
        # Reserva de seguridad para los tamaños reales de Segoe UI en Windows.
        # En los runners de GitHub una etiqueta puede necesitar varios píxeles más
        # que en Linux; sin holgura el último campo sobresalía del panel.
        compact_widths = (136, 94, 190, 54, 183, 190, 140)
        spacious_widths = (153, 119, 228, 70, 225, 205, 175)
        last_widths = [None]

        def resize_settings(event):
            # No emplear hasta el último píxel: Windows añade anchura a
            # ciertas etiquetas y controles nativos. Reservar 32 px.
            spare = max(0, event.width - sum(compact_widths) - 32)
            budget = sum(spacious_widths) - sum(compact_widths)
            progress = min(1.0, spare / budget) if budget else 0
            widths = tuple(round(lo + (hi - lo) * progress)
                           for lo, hi in zip(compact_widths, spacious_widths))
            if widths == last_widths[0]:
                return
            last_widths[0] = widths
            for column, width in enumerate(widths):
                row.grid_columnconfigure(column, minsize=width)
                settings_holders[column].configure(width=width - (6 if column < 6 else 0))

        row.bind("<Configure>", resize_settings, add="+")

        info = tk.Frame(settings, bg=SURFACE)
        info.pack(fill="x", pady=(2, 0))
        self._label(info, "●", color=ACCENT, size=10).pack(side="left")
        self._label(info, "  ", color=MUTED).pack(side="left")
        self._label(info, "", size=10, color=MUTED, textvariable=self.overview).pack(side="left")
        self._label(info, "  ·  ", color=MUTED).pack(side="left")
        self._label(info, "", textvariable=self.layout_info, color=MUTED).pack(side="left")
        self.background_hint = tk.StringVar(value="")
        self._label(info, "", textvariable=self.background_hint, color="#E7BD8D", size=9).pack(side="left")
        self.fit.trace_add("write", lambda *_: self._update_paper_background_controls())
        self.paper_background.trace_add("write", lambda *_: self._update_paper_background_controls())
        self._update_paper_background_controls()
        for var in (self.paper, self.orientation, self.dpi, self.fit, self.output_format, self.binding, self.per_sheet):
            var.trace_add("write", self._update_overview)

        # Reservar el pie ANTES de distribuir el espacio restante a los paneles;
        # así los botones nunca quedan debajo de la barra de tareas de Windows.
        footer = tk.Frame(self.root, bg=BG, padx=24, pady=8)
        footer.pack(side="bottom", fill="x")
        self.open_btn = self._button(footer, "▱  Abrir resultado", self.open_result, small=True)
        self.open_btn.pack(side="right", padx=(8, 0))
        self.open_btn.configure(state="disabled")
        self.export_btn = self._button(footer, "Exportar fotos   →", self.start_export, accent=True)
        self.export_btn.pack(side="right")
        self.preview_btn = self._button(footer, "◎  Previsualización", self.open_preview)
        self.preview_btn.pack(side="right", padx=(0, 8))


        status_area = tk.Frame(footer, bg=BG)
        status_area.pack(side="left", fill="both", expand=True)
        self._label(status_area, "Listo", textvariable=self.feedback,
                    color=MUTED, size=10, anchor="w").pack(fill="x")
        progress_row = tk.Frame(status_area, bg=BG)
        progress_row.pack(fill="x", pady=(8, 0), padx=(0, 22))
        self.progress = ttk.Progressbar(progress_row, mode="determinate", maximum=100,
                                         style="Revelo.Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True)
        self._label(progress_row, "", textvariable=self.percent_text, color=ACCENT,
                    weight="bold", size=10, width=7, anchor="e").pack(side="right", padx=(8, 0))

        content = tk.Frame(self.root, bg=BG, padx=23, pady=9)
        content.pack(fill="both", expand=True)
        content.grid_rowconfigure(0, weight=1)
        # Prioridad al orden del contenido, especialmente en portátiles.
        content.grid_columnconfigure(0, weight=5, uniform="grid")
        content.grid_columnconfigure(1, weight=6, uniform="grid")
        left_panel = self._panel(content)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_panel = self._panel(content)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        library_top = tk.Frame(left_panel, bg=SURFACE, padx=15, pady=10)
        library_top.pack(fill="x")
        title = tk.Frame(library_top, bg=SURFACE)
        title.pack(side="left")
        library_heading = tk.Frame(title, bg=SURFACE)
        library_heading.pack(anchor="w")
        self._label(library_heading, "▧", size=15, color=ACCENT).pack(side="left", padx=(0, 7))
        self.library_heading_label = self._label(
            library_heading, "Fotos y PDF cargados", size=12,
            family="Georgia", weight="bold")
        self.library_heading_label.pack(side="left")
        # El título se abrevia únicamente en ventanas estrechas para evitar
        # solapamientos con Añadir, Página, QR y Vaciar en Windows.
        library_top.bind("<Configure>", self._on_library_header_resize, add="+")
        self._label(title, "0 fotos", textvariable=self.count_var, size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        buttons = tk.Frame(library_top, bg=SURFACE)
        buttons.pack(side="right")
        files_row = tk.Frame(buttons, bg=SURFACE)
        files_row.pack(fill="x")
        self.add_btn = self._button(files_row, "+ Añadir fotos / PDF", self.add_photos, accent=True, small=True)
        self.add_btn.pack(side="left", padx=(0, 7))
        self.special_btn = self._button(files_row, "+ Página", self.special_page_dialog, small=True)
        self.special_btn.pack(side="left", padx=(0, 7))
        lower_buttons = tk.Frame(buttons, bg=SURFACE)
        lower_buttons.pack(fill="x", pady=(7,0))
        self.mobile_btn = self._button(lower_buttons, "Móvil · QR", self.open_mobile_import, small=True)
        self.mobile_btn.pack(side="left", fill="x", expand=True, padx=(0,7))
        self.clear_btn = self._button(lower_buttons, "Vaciar", self.clear, small=True)
        self.clear_btn.pack(side="left")
        tk.Frame(left_panel, height=1, bg=BORDER).pack(fill="x")
        self.library_area = ScrollingArea(left_panel)
        self.library_area.pack(fill="both", expand=True, padx=9, pady=9)
        self.library_area.canvas.bind("<Configure>", self._on_library_resize, add="+")
        self.library_placeholder = self._label(
            self.library_area.inner, "Tus fotos y páginas PDF aparecerán aquí.\n\nPulsa «Añadir fotos / PDF» para elegir archivos.\nAdmite JPG, PNG, HEIC, WEBP, TIFF y PDF.",
            color=MUTED, size=12, justify="center",
        )
        self.library_placeholder.pack(pady=115)
        self._register_drop(self.library_placeholder)

        ordering_top = tk.Frame(right_panel, bg=SURFACE, padx=15, pady=10)
        ordering_top.pack(fill="x")
        rt = tk.Frame(ordering_top, bg=SURFACE)
        rt.pack(side="left")
        order_heading = tk.Frame(rt, bg=SURFACE)
        order_heading.pack(anchor="w")
        self._label(order_heading, "≋", size=17, color=ACCENT).pack(side="left", padx=(0, 7))
        self._label(order_heading, "Orden del contenido", size=14,
                    family="Georgia", weight="bold").pack(side="left")
        self._label(rt, "0 hojas", textvariable=self.page_count_var,
                    size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        self.reset_btn = self._button(ordering_top, "Orden inicial", self.reset_order, small=True)
        self.reset_btn.pack(side="right")
        self.numbers_btn = self._button(ordering_top, "Numeración…", self.numbering_dialog, small=True)
        self.numbers_btn.pack(side="right", padx=(0, 8))
        tk.Frame(right_panel, height=1, bg=BORDER).pack(fill="x")
        hint = tk.Frame(right_panel, bg="#123D43", padx=12, pady=6,
                        highlightbackground="#26636A", highlightthickness=1)
        hint.pack(fill="x", padx=12, pady=(10, 2))
        self._label(hint, "FOTOS / HOJA", size=9, weight="bold",
                    color="#C1F3E5").pack(side="left", padx=(0, 8))
        self.per_sheet_combo = ttk.Combobox(hint, values=["1", "2", "3", "4", "6", "9"],
                                           textvariable=self.per_sheet, width=3,
                                           state="readonly", style="Custom.TCombobox")
        self.per_sheet_combo.pack(side="left")
        self._label(hint, "DISEÑO", size=9, weight="bold",
                    color="#C1F3E5").pack(side="left", padx=(12, 6))
        self.layout_combo = ttk.Combobox(hint, values=list(TEMPLATES),
                                          textvariable=self.layout_template, width=20,
                                          state="readonly", style="Custom.TCombobox")
        self.layout_combo.pack(side="left")
        self.layout_edit_btn=self._button(hint,'Tamaño de fotos',self.edit_page_layout,small=True)
        self.layout_edit_btn.pack(side='left',padx=(9,0))
        self._refresh_layout_button()
        # En equipos de menor anchura, el botón del editor conserva su función
        # con un rótulo corto en lugar de invadir el panel de orden.
        hint.bind("<Configure>", self._on_layout_hint_resize, add="+")
        self.order_area = ScrollingArea(right_panel)
        self.order_area.pack(fill="both", expand=True, padx=9, pady=9)
        self._show_empty_order()

    def _update_paper_background_controls(self):
        if not hasattr(self, 'paper_background_combo'):
            return
        enabled = self.fit.get() == 'Ajustar (sin recortar)'
        self.paper_background_combo.configure(state='readonly' if enabled else 'disabled')
        if hasattr(self, 'paper_background_label'):
            self.paper_background_label.configure(fg=MUTED if enabled else '#65788B')
        if hasattr(self, 'background_hint'):
            self.background_hint.set('  ·  Fondo desactivado con este encaje' if not enabled else '')
        custom = enabled and self.paper_background.get() == 'Personalizado'
        if custom and not self.paper_background_button.winfo_manager():
            self.paper_background_button.pack(side="right", padx=(3, 0))
        if not custom and self.paper_background_button.winfo_manager():
            self.paper_background_button.pack_forget()

    def _sync_free_background_from_main(self, *_):
        """Un fondo general seleccionado sustituye antiguos fondos por hoja.

        Los proyectos heredados no se alteran mientras se están restaurando.
        Una elección posterior en la cabecera sí sincroniza todas las hojas.
        """
        if getattr(self, '_restoring_project', False):
            return
        if not hasattr(self, 'layout_items'):
            return
        changed = False
        for spec in self.layout_items.values():
            if 'background' in spec or 'background_color' in spec:
                spec.pop('background', None)
                spec.pop('background_color', None)
                changed = True
        if changed and self.paths and not self.is_busy:
            self.sheet_thumbnails.clear()
            self._on_thumbnail_settings_changed()

    def choose_paper_background_color(self):
        chosen = colorchooser.askcolor(color=self.paper_background_color.get(),
                                       parent=self.root, title='Revelo · Color del papel')[1]
        if chosen:
            self.paper_background_color.set(chosen.upper())
            self.paper_background.set('Personalizado')

    def _field(self, row, caption, var, choices, *, column=0, compact=False, last=False):
        holder = tk.Frame(row, bg=SURFACE)
        holder.grid(row=0, column=column, sticky="ew", padx=(0, 0 if last else 9))
        self._label(holder, caption, color=MUTED, size=8, weight="bold").pack(anchor="w", pady=(0, 7))
        combo = ttk.Combobox(holder, values=choices, textvariable=var,
                             width=8 if compact else 1, state="readonly", style="Custom.TCombobox")
        if compact:
            # Para un Sí/No no hace falta un desplegable de 200 píxeles.
            combo.pack(anchor="w")
        else:
            combo.pack(fill="x")
        return combo

    def _panel(self, parent):
        return tk.Frame(parent, bg=SURFACE, highlightbackground="#3B6074", highlightthickness=1)

    def _update_overview(self, *_):
        try:
            w, h = PAPER_SIZES[self.paper.get()]
            if self.orientation.get() == "Horizontal":
                w, h = h, w
            dw, dh = pixel_size(w, h, int(self.dpi.get()))
            suffix = " (en vertical; horizontal automático por foto)" if self.orientation.get() == "Automática" else ""
            self.overview.set(f"{self.paper.get()} · {w:g} × {h:g} mm · {dw} × {dh} píxeles · {self.dpi.get()} PPP{suffix}")
        except Exception:
            pass
        try:
            per_sheet = int(self.per_sheet.get())
            self.layout_info.set("Una fotografía por hoja" if per_sheet == 1
                                 else f"{per_sheet} fotos por hoja · PDF/Word/PNG")
            self.page_count_var.set(f"{len(self.pages)} elementos · {len(page_groups(self.pages, per_sheet, self.special_pages))} hojas")
        except (ValueError, ZeroDivisionError):
            pass
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_index = min(self.preview_index, max(0, len(self._groups()) - 1))
            self._show_preview_page()

    def _on_thumbnail_settings_changed(self, *_):
        """Sincroniza miniaturas de ambos paneles con los ajustes de impresión.

        Agrupa los cambios rápidos del desplegable para no reconstruir las
        tarjetas varias veces durante un mismo gesto.
        """
        job = getattr(self, '_thumbnail_settings_job', None)
        if job is not None:
            self.root.after_cancel(job)
        self._thumbnail_settings_job = self.root.after(110, self._refresh_page_thumbnails)

    def _refresh_page_thumbnails(self):
        self._thumbnail_settings_job = None
        if not self.paths or self.is_busy:
            return
        self.thumbnails.clear()
        self.thumbnails_small.clear()
        self.sheet_thumbnails.clear()
        self.render_library()
        self.render_order()

    def _on_per_sheet_changed(self, *_):
        if self.per_sheet.get() != "3" and self.layout_template.get() not in ("Cuadrícula", "Diseño libre"):
            self.layout_template.set("Cuadrícula")
        self._refresh_layout_button()
        self.render_order()

    def _on_template_changed(self, *_):
        if self.layout_template.get() not in ("Cuadrícula", "Diseño libre") and self.per_sheet.get() != "3":
            self.per_sheet.set("3")
        self._refresh_layout_button()
        self.render_order()

    def _on_layout_hint_resize(self, event):
        compact = event.width < 610
        if compact != getattr(self, "_compact_layout_button", False):
            self._compact_layout_button = compact
            self._refresh_layout_button()

    def _refresh_layout_button(self):
        button=getattr(self,'layout_edit_btn',None)
        if button is None:return
        template=self.layout_template.get()
        enabled=template!='Cuadrícula' and (template=='Diseño libre' or self.per_sheet.get()=='3')
        full_label = 'Editar diseño libre' if template=='Diseño libre' else 'Tamaño de fotos'
        short_label = 'Editar' if template=='Diseño libre' else 'Tamaño'
        button.configure(text=short_label if getattr(self, '_compact_layout_button', False) else full_label,
                         state='normal' if enabled else 'disabled')

    def edit_page_layout(self):
        """Edita solamente la hoja seleccionada, no todas las hojas del álbum."""
        if self.is_busy or not self.pages:return
        template=self.layout_template.get()
        if template=='Cuadrícula':return
        groups=[g for g in self._groups() if not (len(g)==1 and g[0] in self.special_pages)]
        if not groups:return
        group=next((g for g in groups if self.order_selected in g),groups[0])
        selected_group=list(group)
        # Migración del antiguo fondo específico de hoja: al abrir su editor
        # pasa a ser un fondo del papel visible en el menú principal.
        old_sheet=self.layout_items.get(group[0], {})
        old_background=old_sheet.get('background')
        if (self.fit.get()=='Ajustar (sin recortar)' and
                old_background not in (None,'Según encaje')):
            if old_background=='Personalizado':
                self.paper_background_color.set(old_sheet.get('background_color','#FFFFFF'))
            self.paper_background.set(old_background)
        def save(result, *, photo_scales=None, background_choice=None):
            # En diseño libre el tamaño proporcional es print_scale, la misma
            # variable que usa «Editar foto» (sin multiplicadores ocultos).
            if photo_scales:
                for path, scale in photo_scales.items():
                    current = validate_edits(self.photo_edits.get(path))
                    current['print_scale'] = round(float(scale), 4)
                    if path in self.captions and 'photo_scale' in self.captions[path]:
                        self.captions[path]['photo_scale'] = 1.0
                    if has_edits(current):
                        self.photo_edits[path] = current
                    else:
                        self.photo_edits.pop(path, None)
            for path,spec in result.items():
                clean=validate_layout_item(spec)
                # Un único fondo general manda también en el diseño libre.
                clean.pop('background',None)
                clean.pop('background_color',None)
                if clean:self.layout_items[path]=clean
                else:self.layout_items.pop(path,None)
            if background_choice is not None and self.fit.get() == 'Ajustar (sin recortar)':
                bg, color = background_choice
                if bg != 'Según encaje':
                    self.paper_background_color.set(color)
                    self.paper_background.set(bg)
            self.thumbnails.clear();self.thumbnails_small.clear();self.sheet_thumbnails.clear()
            self.render_library();self.render_order()
            if self.preview_window is not None and self.preview_window.winfo_exists():self._show_preview_page()
            self.feedback.set(f'Composición guardada para {len(selected_group)} fotos de esta hoja.')
        shared = {}
        def save_shared(scales, background):
            shared['photo_scales'] = scales
            shared['background_choice'] = background
        def commit_layout(result):
            save(result, **shared)
        page_number=next((i for i,g in enumerate(self._groups()) if tuple(g)==tuple(group)),0)
        edit_sheet(self.root,selected_group,template,self.layout_items,self._options(),commit_layout,
                   page_index=page_number, on_shared_save=save_shared)

    def _groups(self) -> list[tuple[Path, ...]]:
        return page_groups(self.pages, int(self.per_sheet.get()), self.special_pages)

    def _special_landscape(self, path: Path | None = None) -> bool:
        """Resuelve la orientación de portadas en la configuración ACTUAL.

        Vertical y Horizontal tienen prioridad sobre la miniatura existente.
        Solo en Automática se reutiliza su orientación (o la primera hoja).
        """
        selection = self.orientation.get()
        if selection == "Horizontal":
            return True
        if selection == "Vertical":
            return False
        if path is not None and path in self.details:
            w, h = self.details[path]
            return w > h
        if self.pages:
            w, h = self.details.get(self.pages[0], (1, 2))
            return w > h
        return False

    def _commit_special_page(self, spec: dict, path: Path | None) -> None:
        """Guarda portada/separador desde el modo clásico o personalizar."""
        spec = validate_special_spec(spec)
        if spec['kind'] == 'Portada' and cover_path(self.special_pages, path) is not None:
            raise ValueError('Ya tienes una portada. Edítala o elimínala antes de crear otra.')
        new = path is None
        candidate = (Path(self.special_temp.name) / f'pagina_{uuid.uuid4().hex}.png') if new else path
        landscape = self._special_landscape(path)
        save_special_thumbnail(candidate, spec, landscape=landscape)
        self.special_pages[candidate] = spec
        self.thumbnails.pop(candidate, None)
        self.thumbnails_small.pop(candidate, None)
        self._thumbnail(candidate)
        self.path_labels[candidate] = ('Página en blanco' if spec['kind'] == 'Página en blanco'
                                       else f"{spec['kind']}: {spec['title'] or 'Sin título'}")
        self.details[candidate] = source_dimensions(candidate)
        if new:
            self.paths.append(candidate)
            self.pages.append(candidate)
        self.pages = anchored_order(self.pages, self.special_pages)
        self.selected = candidate
        self.render_library()
        self.render_order()
        self.feedback.set('Página guardada. La portada siempre ocupa la primera posición.')

    def _custom_page_dialog(self, path: Path | None = None, *, initial: dict | None = None) -> None:
        if self.is_busy:
            return
        spec = dict(initial or self.special_pages.get(path) or {})
        landscape = self._special_landscape(path)
        paper_w_mm, paper_h_mm = PAPER_SIZES[self.paper.get()]
        if landscape:
            paper_w_mm, paper_h_mm = paper_h_mm, paper_w_mm
        def commit(custom_spec):
            self._commit_special_page(custom_spec, path)
        def current_page_settings():
            width_mm, height_mm = PAPER_SIZES[self.paper.get()]
            if self._special_landscape(path):
                width_mm, height_mm = height_mm, width_mm
            return ((width_mm, height_mm), self.binding.get() == 'Sí')

        edit_custom_page(self.root, initial=spec, image_dir=Path(self.special_temp.name),
                         landscape=landscape, binding=self.binding.get() == 'Sí',
                         paper_dimensions_mm=(paper_w_mm, paper_h_mm),
                         page_settings=current_page_settings,
                         settings_vars=(self.paper, self.orientation, self.binding),
                         orientation_var=self.orientation,
                         on_save=commit)

    def special_page_dialog(self, path: Path | None = None):
        """Los temas prediseñados no cambian posición/tamaño; Personalizar abre editor."""
        if self.is_busy:
            return
        old = self.special_pages.get(path) if path is not None else None
        if old is not None and old.get('theme') == CUSTOM_THEME:
            self._custom_page_dialog(path)
            return
        kind = tk.StringVar(value=old['kind'] if old else 'Separador')
        title = tk.StringVar(value=old['title'] if old else '')
        subtitle = tk.StringVar(value=old['subtitle'] if old else '')
        theme = tk.StringVar(value=old['theme'] if old else 'Crema')
        window = tk.Toplevel(self.root)
        window.title('Revelo · ' + ('Editar página' if old else 'Añadir página'))
        self.root.update_idletasks()
        win_w, win_h = 520, 550
        x = max(0, self.root.winfo_rootx() + (self.root.winfo_width() - win_w)//2)
        y = max(0, self.root.winfo_rooty() + (self.root.winfo_height() - win_h)//2)
        window.geometry(f'{win_w}x{win_h}+{x}+{y}')
        window.resizable(False, False)
        window.configure(bg=BG)
        window.transient(self.root)
        window.grab_set()
        content = tk.Frame(window, bg=BG, padx=28, pady=23)
        content.pack(fill='both', expand=True)
        self._label(content, 'EDITAR PÁGINA' if old else 'CREAR PÁGINA',
                    weight='bold', size=17).pack(anchor='w')
        self._label(content, 'Elige un diseño o personaliza una foto, colores y textos.',
                    color=MUTED, size=9).pack(anchor='w', pady=(6, 15))
        def select(caption, var, choices):
            self._label(content, caption, weight='bold', color=MUTED, size=9).pack(anchor='w', pady=(7,4))
            combo = ttk.Combobox(content, textvariable=var, values=choices,
                                 state='readonly', style='Custom.TCombobox')
            combo.pack(fill='x')
            return combo
        select('TIPO DE PÁGINA', kind, list(KINDS))
        self._label(content, 'TÍTULO', weight='bold', color=MUTED, size=9).pack(anchor='w', pady=(10,4))
        title_input = tk.Entry(content, textvariable=title, bg=SURFACE_2, fg=TEXT,
                               font=('Segoe UI', 11), insertbackground=ACCENT, relief='flat')
        title_input.pack(fill='x', ipady=7)
        self._label(content, 'SUBTÍTULO (OPCIONAL)', weight='bold', color=MUTED, size=9).pack(anchor='w', pady=(10,4))
        subtitle_input = tk.Entry(content, textvariable=subtitle, bg=SURFACE_2, fg=TEXT,
                                  font=('Segoe UI', 11), insertbackground=ACCENT, relief='flat')
        subtitle_input.pack(fill='x', ipady=7)
        select('COLOR / DISEÑO', theme, [*THEMES, CUSTOM_THEME])
        self._label(content, 'Con «Personalizar» podrás escoger cualquier color o foto de fondo,\n'
                    'mover el título y subtítulo y cambiar sus tamaños.',
                    color=MUTED, size=9, justify='left').pack(anchor='w', pady=(11,0))
        controls = tk.Frame(content, bg=BG)
        controls.pack(side='bottom', fill='x', pady=(16,0))
        self._button(controls, 'Cancelar', window.destroy, small=True).pack(side='right')
        def update_kind(*_):
            state = 'disabled' if kind.get() == 'Página en blanco' else 'normal'
            title_input.configure(state=state)
            subtitle_input.configure(state=state)
        kind.trace_add('write', update_kind)
        update_kind()
        def create():
            if theme.get() == CUSTOM_THEME:
                initial = {'kind':kind.get(), 'title':title.get(), 'subtitle':subtitle.get(),
                           'theme':CUSTOM_THEME}
                window.destroy()
                self._custom_page_dialog(path, initial=initial)
                return
            try:
                self._commit_special_page({'kind':kind.get(),'title':title.get(),
                                           'subtitle':subtitle.get(),'theme':theme.get()}, path)
            except (ValueError, OSError) as exc:
                messagebox.showwarning('Página especial', str(exc), parent=window)
                return
            window.destroy()
        self._button(controls, 'Guardar página', create, small=True, accent=True).pack(side='right', padx=(0,9))
        title_input.focus_set()

    def _thumbnail(self, path: Path) -> ImageTk.PhotoImage:
        """Miniatura de la hoja REAL, no de la orientación de la foto fuente.

        Renderiza en tamaño diminuto: no exporta ni modifica el archivo de
        origen y aplica también los recortes y las portadas personalizadas.
        """
        if path not in self.thumbnails:
            opts = self._options()
            index = self.pages.index(path) if path in self.pages else 0
            try:
                # Las portadas necesitan más píxeles al dibujar tipografías;
                # después se reducen para que sus letras no desaparezcan.
                if path in self.special_pages:
                    picture, _, _ = render_layout_page((path,), opts,
                                       preview_max_size=(360,255), page_index=index)
                    picture.thumbnail((150,108),Image.Resampling.LANCZOS)
                elif has_caption(self.captions.get(path)):
                    from dataclasses import replace
                    preview_opts = replace(opts, photos_per_page=1, layout_template="Cuadrícula")
                    picture, _, _ = render_layout_page((path,), preview_opts,
                                       preview_max_size=(420, 310), page_index=index)
                    picture.thumbnail((150,108),Image.Resampling.LANCZOS)
                else:
                    picture = render_photo_thumbnail(path, opts, page_index=index)
            except (OSError, ValueError, RuntimeError):
                # Un archivo inaccesible no debe impedir mostrar las tarjetas.
                with Image.open(path) as source:
                    picture=ImageOps.contain(ImageOps.exif_transpose(source).convert('RGB'),
                                             (150,108), Image.Resampling.LANCZOS)
            try:
                background=Image.new('RGB',(150,108), (29,45,67))
                background.paste(picture,((150-picture.width)//2,(108-picture.height)//2))
                self.thumbnails[path]=ImageTk.PhotoImage(background)
                self.thumbnails_small[path]=ImageTk.PhotoImage(
                     background.resize((124,92), Image.Resampling.LANCZOS))
            finally:
                picture.close()
                background.close()
        return self.thumbnails[path]

    def _sheet_thumbnail(self, group, sheet_index):
        """Hoja ya compuesta para la lista de orden, no la foto fuente aislada."""
        key = (tuple(group), sheet_index, self.paper.get(), self.orientation.get(),
               self.fit.get(), self.paper_background.get(), self.paper_background_color.get(),
               repr([self.layout_items.get(p, {}) for p in group]),
               repr([self.photo_edits.get(p, {}) for p in group]),
               repr([self.captions.get(p, {}) for p in group]))
        if key not in self.sheet_thumbnails:
            if len(self.sheet_thumbnails) >= 128:
                self.sheet_thumbnails.clear()
            opts = self._options()
            try:
                sheet, _, _ = render_layout_page(group, opts,
                          preview_max_size=(248, 184), page_index=sheet_index)
                try:
                    sheet.thumbnail((124, 92), Image.Resampling.LANCZOS)
                    frame = Image.new('RGB', (124, 92), (29, 45, 67))
                    try:
                        frame.paste(sheet, ((124-sheet.width)//2, (92-sheet.height)//2))
                        self.sheet_thumbnails[key] = ImageTk.PhotoImage(frame)
                    finally:
                        frame.close()
                finally:
                    sheet.close()
            except (OSError, ValueError, RuntimeError):
                return self.thumbnails_small[group[0]]
        return self.sheet_thumbnails[key]

    def edit_photo_dialog(self, path: Path):
        """Editor separado por fotografía; no modifica archivos originales."""
        if self.is_busy or path not in self.paths or path in self.special_pages:
            return
        if self.photo_editor_window is not None and self.photo_editor_window.winfo_exists():
            self.photo_editor_window.lift()
            return
        def save_edits(spec):
            old_master_scale = float(self.photo_edits.get(path, {}).get('print_scale', 1.0))
            spec = validate_edits(spec)
            if has_edits(spec):
                self.photo_edits[path] = spec
            else:
                self.photo_edits.pop(path, None)
            # El tamaño guardado desde Editar foto es el tamaño real: un viejo
            # pie de foto no debe volver a multiplicarlo por su propia escala.
            if (abs(old_master_scale-spec['print_scale'])>0.002 and
                    path in self.captions and self.captions[path].get('photo_scale',1.0)!=1.0):
                self.captions[path]['photo_scale']=1.0
            self.thumbnails.pop(path, None)
            self.thumbnails_small.pop(path, None)
            self.sheet_thumbnails.clear()
            self._thumbnail(path)
            self.render_library()
            self.render_order()
            if self.preview_window is not None and self.preview_window.winfo_exists():
                self._show_preview_page()
            self.feedback.set(f"Edición guardada para «{self.path_labels.get(path, path.name)}». Original intacto.")
        self.photo_editor_window = edit_photo(self.root, path, self.photo_edits.get(path), save_edits,
                                              pdf_flattened=path in self.pdf_origins,
                                              paper_options=self._options())

    def add_photos(self):
        if self.is_busy:
            return
        names = filedialog.askopenfilenames(
            title="Selecciona fotos o documentos PDF", filetypes=[
                ("Fotos y PDF", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp *.heic *.heif *.pdf"),
                ("Documentos PDF", "*.pdf"),
                ("Imágenes", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp *.heic *.heif"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if names:
            self.import_paths([Path(f) for f in names])

    def caption_dialog(self, path: Path):
        """Editor reversible de texto sin bandas opacas, con posición libre."""
        if self.is_busy or path not in self.paths or path in self.special_pages:
            return
        original = validate_caption(self.captions.get(path))

        def save(clean):
            if has_caption(clean):
                self.captions[path] = clean
            else:
                self.captions.pop(path, None)
            self.thumbnails.clear()
            self.thumbnails_small.clear()
            self.sheet_thumbnails.clear()
            self.render_library()
            self.render_order()
            if self.preview_window is not None and self.preview_window.winfo_exists():
                self._show_preview_page()
            self.feedback.set('Pie de foto actualizado. La fotografía original no se modifica.')

        groups=self._groups()
        group=next((g for g in groups if path in g),(path,))
        group_idx=next((i for i,g in enumerate(groups) if path in g),0)
        def save_scale(scale):
            updated=validate_edits(self.photo_edits.get(path))
            updated['print_scale']=float(scale)
            if has_edits(updated):self.photo_edits[path]=updated
            else:self.photo_edits.pop(path,None)
        edit_caption(self.root, path, original, self._options(), save,
                     page_paths=group, page_index=group_idx,
                     on_master_scale=save_scale)

    def numbering_dialog(self):
        """Numeración opcional, independiente del orden físico de encuadernación."""
        window = tk.Toplevel(self.root)
        window.title("Revelo · Numeración de páginas")
        window.configure(bg=BG)
        window.geometry("575x400")
        window.minsize(495, 350)
        panel = tk.Frame(window, bg=BG, padx=24, pady=19)
        panel.pack(fill="both", expand=True)
        self._label(panel, "NUMERACIÓN DE PÁGINAS", size=16, weight="bold").pack(anchor="w")
        self._label(panel, "Se aplicará a previsualización, PDF, Word e imágenes.", color=MUTED,
                    size=9).pack(anchor="w", pady=(7, 15))
        enabled = tk.BooleanVar(value=self.numbering_enabled.get())
        skip = tk.BooleanVar(value=self.numbering_skip_special.get())
        where = tk.StringVar(value=self.numbering_position.get())
        number_style = tk.StringVar(value=self.numbering_format.get())
        start = tk.StringVar(value=str(self.numbering_start.get()))
        for caption, variable in (("Numerar páginas", enabled),
                                  ("Omitir portada y separadores", skip)):
            tk.Checkbutton(panel, text=caption, variable=variable, bg=BG, fg=TEXT,
                           selectcolor=SURFACE_2, activebackground=BG,
                           activeforeground=TEXT).pack(anchor="w", pady=(4, 6))
        number_row=tk.Frame(panel,bg=BG)
        number_row.pack(fill='x',pady=(10,4))
        position_box=tk.Frame(number_row,bg=BG)
        position_box.pack(side='left',fill='x',expand=True,padx=(0,14))
        self._label(position_box,"POSICIÓN",color=MUTED,weight='bold',size=9).pack(anchor='w',pady=(0,5))
        ttk.Combobox(position_box,textvariable=where,values=list(NUMBER_POSITIONS),
                     width=15,state='readonly',style='Custom.TCombobox').pack(fill='x')
        format_box=tk.Frame(number_row,bg=BG)
        format_box.pack(side='left',fill='x',expand=True)
        self._label(format_box,"FORMATO",color=MUTED,weight='bold',size=9).pack(anchor='w',pady=(0,5))
        ttk.Combobox(format_box,textvariable=number_style,values=list(NUMBER_FORMATS),
                     width=14,state='readonly',style='Custom.TCombobox').pack(fill='x')
        self._label(panel, "EMPEZAR EN", color=MUTED, size=9,
                    weight="bold").pack(anchor="w", pady=(10, 5))
        tk.Entry(panel, textvariable=start, bg=SURFACE_2, fg=TEXT,
                 insertbackground=ACCENT, relief="flat", width=12).pack(anchor="w", ipady=6)
        buttons = tk.Frame(panel, bg=BG)
        buttons.pack(side="bottom", fill="x", pady=(12,0))
        self._button(buttons, "Cancelar", window.destroy, small=True).pack(side="right")
        def save():
            try:
                value = int(start.get())
                if not 1 <= value <= 999999:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showwarning("Numeración", "Introduce un número de inicio entre 1 y 999999.")
                return
            self.numbering_enabled.set(enabled.get())
            self.numbering_position.set(where.get())
            self.numbering_format.set(number_style.get())
            self.numbering_skip_special.set(skip.get())
            self.numbering_start.set(value)
            window.destroy()
            self.thumbnails.clear()
            self.thumbnails_small.clear()
            self.render_library()
            self.render_order()
            self.feedback.set("Numeración actualizada para todas las hojas.")
        self._button(buttons, "Aplicar", save, accent=True, small=True).pack(side="right", padx=(0, 8))
        window.bind("<Escape>",lambda event: window.destroy())

    def _register_drop(self, widget):
        """Permite soltar imágenes/PDF del Explorador usando el TkDND empaquetado."""
        if DND_FILES is None:
            return
        try:
            if hasattr(widget, "drop_target_register"):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_file_drop)
            else:
                # TkinterDnD permite registrar también widgets Tk normales.
                self.root.tk.call("tkdnd::drop_target", "register", widget._w, DND_FILES)
                # El bind nativo de Tk no construye el campo event.data.
                # Utilizamos el sustituidor de eventos de TkinterDnD2 también
                # cuando el widget destino es un Frame/Label de Tk estándar.
                if hasattr(self.root, "_substitute_dnd"):
                    self.root._bind(("bind", widget._w), "<<Drop>>",
                                    self._on_file_drop, "+", self.root._substitute_dnd)
        except (tk.TclError, RuntimeError):
            pass

    def _configure_file_drop(self):
        for target in (self.root, self.library_area, self.library_area.canvas,
                       self.library_area.inner, self.order_area, self.order_area.canvas):
            self._register_drop(target)

    def _on_file_drop(self, event):
        if self.is_busy:
            return "break"
        try:
            candidates = [Path(s).expanduser() for s in self.root.tk.splitlist(event.data)]
            selected = []
            for path in candidates:
                if path.is_dir():
                    selected.extend(sorted((p for p in path.iterdir()
                                            if p.is_file() and (p.suffix.lower() in SUPPORTED_EXTENSIONS
                                                                or p.suffix.lower() == '.pdf')),
                                           key=lambda p: p.name.casefold()))
                elif path.is_file() and (path.suffix.lower() in SUPPORTED_EXTENSIONS
                                         or path.suffix.lower() == '.pdf'):
                    selected.append(path)
            if len(selected) > 250:
                if not messagebox.askyesno("Importar fotografías",
                                           f"Has arrastrado {len(selected)} archivos. ¿Quieres importarlos todos?"):
                    return "break"
            if selected:
                self.import_paths(selected)
            else:
                messagebox.showwarning("Arrastrar archivos", "Arrastra fotografías o documentos PDF compatibles.")
        except OSError as exc:
            messagebox.showerror("Importación por arrastre", str(exc))
        return "break"

    def open_mobile_import(self):
        """Muestra el QR para seleccionar y enviar fotos desde un móvil en la LAN."""
        if self.mobile_window is not None and self.mobile_window.winfo_exists():
            self.mobile_window.lift()
            self.mobile_window.focus_force()
            return
        try:
            self.mobile_server = PhoneTransferServer(
                Path(self.mobile_temp.name),
                lambda path: self.updates.put(("mobile_received", path)),
            )
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Importar desde móvil", str(exc))
            return
        window = tk.Toplevel(self.root)
        self.mobile_window = window
        window.title("Revelo · Importar desde móvil")
        window.geometry("510x690")
        window.minsize(455, 605)
        window.configure(bg=BG)
        try:
            ico = app_asset("icono.ico")
            if sys.platform == "win32" and ico.exists():
                window.iconbitmap(str(ico))
        except tk.TclError:
            pass
        self.mobile_received_count = 0
        self.mobile_status.set("Esperando fotografías desde el móvil…")
        outer = tk.Frame(window, bg=BG, padx=25, pady=20)
        outer.pack(fill="both", expand=True)
        self._label(outer, "IMPORTAR DESDE MÓVIL", size=17, weight="bold").pack(anchor="w")
        self._label(outer, "1. Conecta el iPhone y el ordenador a la misma red doméstica.",
                    size=10, color=MUTED).pack(anchor="w", pady=(10, 5))
        self._label(outer, "2. Escanea este código con la cámara del móvil.",
                    size=10, color=MUTED).pack(anchor="w", pady=(0, 14))

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=4)
        qr.add_data(self.mobile_server.url)
        qr.make(fit=True)
        raw = qr.make_image(fill_color="#102234", back_color="white").convert("RGB")
        raw = raw.resize((330, 330), Image.Resampling.NEAREST)
        self.mobile_qr = ImageTk.PhotoImage(raw)
        tk.Label(outer, image=self.mobile_qr, bg="white", padx=8, pady=8,
                 borderwidth=0).pack(anchor="center")
        self._label(outer, "3. Selecciona varias fotos y pulsa «Enviar fotos».",
                    color=MUTED, size=10).pack(anchor="w", pady=(14, 7))
        self._label(outer, "", textvariable=self.mobile_status, color=ACCENT,
                    size=11, weight="bold", anchor="w").pack(fill="x")
        self._label(outer, "Sin nube ni instalación en el móvil. Las fotos originales se conservan.",
                    size=9, color=MUTED, wraplength=440, justify="left").pack(anchor="w", pady=(12, 0))
        self._label(outer, "Si Windows solicita permiso, permite Revelo solo en redes privadas.",
                    size=9, color=WARNING, wraplength=440, justify="left").pack(anchor="w", pady=(4, 0))
        bottom = tk.Frame(outer, bg=BG)
        bottom.pack(side="bottom", fill="x", pady=(12, 0))
        self._button(bottom, "Cerrar QR", self._close_mobile_import, small=True).pack(side="right")
        self._button(bottom, "Copiar enlace", self._copy_mobile_url, small=True).pack(side="left")
        window.protocol("WM_DELETE_WINDOW", self._close_mobile_import)

    def _copy_mobile_url(self):
        if self.mobile_server is None:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.mobile_server.url)
        self.root.update_idletasks()
        self.mobile_status.set("Enlace copiado. Ábrelo desde el móvil conectado a la misma red.")

    def _close_mobile_import(self):
        if self.mobile_server is not None:
            server = self.mobile_server
            self.mobile_server = None
            server.stop()
        if self.mobile_window is not None and self.mobile_window.winfo_exists():
            self.mobile_window.destroy()
        self.mobile_window = None
        self.mobile_qr = None

    def _set_busy(self, active: bool):
        self.is_busy = active
        state = "disabled" if active else "normal"
        for button in (self.add_btn, self.special_btn, self.mobile_btn,
                       self.clear_btn, self.reset_btn,
                       self.preview_btn, self.export_btn, self.open_project_btn,
                       self.save_project_btn):
            button.configure(state=state)
        self.per_sheet_combo.configure(state="disabled" if active else "readonly")

    def import_paths(self, incoming):
        """Carga fotos y convierte páginas PDF en segundo plano para no bloquear la ventana."""
        if self.is_busy:
            return
        selected = []
        for file in incoming:
            file = Path(file).expanduser().resolve()
            if file not in selected:
                selected.append(file)
        if not selected:
            return
        existing = set(self.paths)
        imported_pdfs = set(self.pdf_origins.values()) | set(self.recovered_pdf_sources)
        self._set_busy(True)
        self.feedback.set("Importando archivos… No se modificará ninguno de los originales.")
        self.progress["value"] = 0
        self.percent_text.set("(0 %)")
        self._close_preview()

        def do_import():
            items = []   # (imagen, dimensiones, nombre visible, pdf_origen)
            errors = []
            detected_paper = None
            mixed_pdf = False
            recovered_specials = {}
            recovered_edits = {}
            recovered_captions = {}
            recovered_layout_items = {}
            seen = set()
            for source in selected:
                if source in seen:
                    continue
                seen.add(source)
                if source.suffix.lower() == ".pdf":
                    if source in imported_pdfs:
                        continue
                    temp_dir = Path(self.pdf_temp.name) / uuid.uuid4().hex
                    try:
                        progress = lambda i, n, name: self.updates.put(("import_progress", i, n, name))
                        try:
                            originals = recover_sources(source, temp_dir, progress=progress,
                                                        include_specials=True, include_edits=True,
                                                        include_captions=True,include_layout=True)
                        except Exception:
                            # Si un lector elimina o altera el adjunto interno,
                            # el PDF debe seguir pudiendo abrirse como páginas.
                            originals = None
                            errors.append(f"{source.name}: no se recuperaron originales adjuntos; se leerán sus páginas como imágenes")
                        if originals is not None:
                            images, sizes, per_sheet, recovered_specs, source_edits, source_captions, source_layout_items, source_template = originals
                            recovered_specials.update(recovered_specs)
                            recovered_edits.update(source_edits)
                            recovered_captions.update(source_captions)
                            recovered_layout_items.update(source_layout_items)
                            # Las fotos recuperadas son originales: NO se deben
                            # marcar como página PDF ni intentar quitarles un fondo.
                            paper, has_mixed = matched_paper(sizes)
                            if detected_paper is None:
                                detected_paper = paper
                            mixed_pdf = mixed_pdf or has_mixed
                            for number, image in enumerate(images, 1):
                                dims = source_dimensions(image)
                                spec = recovered_specs.get(image)
                                label = (f"{spec['kind']}: {spec['title']}" if spec and spec['title']
                                         else "Página en blanco" if spec else f"{source.name} · foto original {number}")
                                items.append((image, dims, label, None))
                            self.updates.put(("pdf_recovered", source, len(images), per_sheet, source_template))
                        else:
                            images, sizes = import_pdf_pages(source, temp_dir, progress=progress)
                            paper, has_mixed = matched_paper(sizes)
                            if detected_paper is None:
                                detected_paper = paper
                            mixed_pdf = mixed_pdf or has_mixed
                            for number, image in enumerate(images, 1):
                                dims = source_dimensions(image)
                                items.append((image, dims, f"{source.name} · pág. {number}", source))
                    except Exception as error:
                        errors.append(f"{source.name}: {error}")
                elif source.suffix.lower() in SUPPORTED_EXTENSIONS:
                    if source in existing:
                        continue
                    try:
                        items.append((source, source_dimensions(source), source.name, None))
                    except (OSError, ValueError, SyntaxError) as error:
                        errors.append(f"{source.name}: no se pudo leer ({error})")
                else:
                    errors.append(f"{source.name}: formato no admitido")
            self.updates.put(("import_done", items, detected_paper, mixed_pdf, errors,
                              recovered_specials, recovered_edits, recovered_captions, recovered_layout_items))

        threading.Thread(target=do_import, daemon=True).start()

    def _finish_import(self, items, detected_paper, mixed_pdf, errors, specials=None, edits=None, captions=None, layout_items=None):
        was_empty = not self.paths
        count = 0
        for path, dims, label, origin in items:
            # Registrar primero los metadatos: la miniatura debe interpretar
            # la portada, las ediciones y la procedencia del PDF desde el
            # momento de su creación. Antes se generaba demasiado pronto.
            self.details[path] = dims
            self.path_labels[path] = label
            if path in (specials or {}):
                self.special_pages[path] = specials[path]
            if path in (edits or {}):
                self.photo_edits[path] = edits[path]
            if path in (captions or {}):
                self.captions[path] = captions[path]
            if path in (layout_items or {}):
                self.layout_items[path] = layout_items[path]
            if origin is not None:
                self.pdf_origins[path] = origin
            self.paths.append(path)
            self.pages.append(path)
            try:
                self._thumbnail(path)
            except (OSError, ValueError, SyntaxError) as error:
                self.paths.remove(path)
                self.pages.remove(path)
                self.details.pop(path, None)
                self.path_labels.pop(path, None)
                self.pdf_origins.pop(path, None)
                self.special_pages.pop(path, None)
                self.photo_edits.pop(path, None)
                self.layout_items.pop(path, None)
                self.captions.pop(path, None)
                self.thumbnails.pop(path, None)
                self.thumbnails_small.pop(path, None)
                errors.append(f"{label}: no se pudo mostrar ({error})")
                continue
            count += 1
        if count and was_empty and detected_paper:
            self.paper.set(detected_paper)
        self.pages = anchored_order(self.pages, self.special_pages)
        self.render_library()
        self.render_order()
        self._set_busy(False)
        if count:
            self.feedback.set(f"{len(self.paths)} elementos listos. Ordena y previsualiza antes de exportar.")
        else:
            self.feedback.set("No se añadieron nuevos elementos.")
        if mixed_pdf:
            errors.append("El PDF incluye tamaños de página distintos: el tamaño de exportación será el seleccionado arriba.")
        if errors:
            messagebox.showwarning("Avisos de importación", "\n".join(errors[:10]))

    def remove_photo(self, path: Path):
        if path not in self.paths or self.is_busy:
            return
        self.paths.remove(path)
        self.pages.remove(path)
        self.thumbnails.pop(path, None)
        self.thumbnails_small.pop(path, None)
        self.details.pop(path, None)
        self.path_labels.pop(path, None)
        self.pdf_origins.pop(path, None)
        self.special_pages.pop(path, None)
        self.photo_edits.pop(path, None)
        self.layout_items.pop(path, None)
        if self.selected == path:
            self.selected = None
        if self.order_selected == path:
            self.order_selected = None
        self.render_library()
        self.render_order()
        self.feedback.set(f"Quitada de la lista: {path.name}. El archivo original se conserva.")

    def clear(self):
        if not self.paths:
            return
        if messagebox.askyesno("Vaciar lista", "¿Quitar todas las fotos y páginas PDF de la lista?\nLos originales no se borrarán."):
            self.paths.clear()
            self.pages.clear()
            self.thumbnails.clear()
            self.thumbnails_small.clear()
            self.details.clear()
            self.path_labels.clear()
            self.pdf_origins.clear()
            self.special_pages.clear()
            self.photo_edits.clear()
            self.captions.clear()
            self.layout_items.clear()
            self.selected = None
            self.order_selected = None
            self.render_library()
            self.render_order()
            self.feedback.set("Lista vacía. Los originales no se han modificado.")
            self._close_preview()

    def reset_order(self):
        if self.paths:
            self.pages = anchored_order(self.paths.copy(), self.special_pages)
            self.render_order()
            self.feedback.set("Restaurado el orden en que cargaste las fotos y los PDF.")

    def _on_library_header_resize(self, event):
        if hasattr(self, 'library_heading_label'):
            self.library_heading_label.configure(
                text='Fotos y PDF' if event.width < 520 else 'Fotos y PDF cargados')

    def _on_library_resize(self, event):
        cols = 3 if event.width >= 560 else 2 if event.width >= 345 else 1
        if cols != self.library_cols:
            self.library_cols = cols
            if self.paths:
                self.render_library()

    def _clear_children(self, parent):
        for child in parent.winfo_children():
            child.destroy()

    def render_library(self):
        offset = self.library_area.canvas.yview()[0]
        self._clear_children(self.library_area.inner)
        self.count_var.set(f"{len(self.paths)} elemento{'s' if len(self.paths) != 1 else ''}")
        if not self.paths:
            empty_hint = self._label(self.library_area.inner,
                        "Tus fotos y páginas PDF aparecerán aquí.\n\nArrastra imágenes o PDF desde Windows, o pulsa «Añadir fotos / PDF».",
                        color=MUTED, size=12, justify="center")
            empty_hint.pack(pady=115)
            self._register_drop(empty_hint)
            return
        for column in range(self.library_cols):
            self.library_area.inner.grid_columnconfigure(column, weight=1)
        for index, path in enumerate(self.paths):
            selected = self.selected == path
            card = tk.Frame(self.library_area.inner, bg=SURFACE_2,
                            highlightbackground=ACCENT if selected else "#3A6074",
                            highlightthickness=2 if selected else 1,
                            cursor="hand2", padx=10, pady=9)
            card.grid(row=index // self.library_cols, column=index % self.library_cols,
                      padx=5, pady=5, sticky="nsew")
            thumb = tk.Label(card, image=self._thumbnail(path), bg=SURFACE_2,
                             borderwidth=0, cursor="hand2")
            thumb.pack(fill="x")
            display_name = self.path_labels.get(path, path.name)
            name = display_name if len(display_name) <= 30 else display_name[:27] + "…"
            lbl = self._label(card, name, size=10, weight="bold", bg=SURFACE_2, anchor="w")
            lbl.pack(fill="x", pady=(6, 0))
            w, h = self.details[path]
            kind = "PÁGINA" if path in self.special_pages else ("PDF" if path in self.pdf_origins else path.suffix[1:].upper())
            meta = self._label(card, f"{w} × {h} px  ·  {kind}",
                               size=9, color=MUTED, bg=SURFACE_2, anchor="w")
            meta.pack(fill="x", pady=(2, 4))
            remove = tk.Button(card, text="×", command=lambda p=path: self.remove_photo(p),
                               font=("Segoe UI", 12, "bold"), bg="#33455D", fg=TEXT,
                               activebackground="#5B3444", activeforeground=TEXT,
                               borderwidth=0, padx=5, pady=0, cursor="hand2")
            remove.place(relx=1, x=-3, y=3, anchor="ne")
            if path in self.special_pages:
                self._button(card, "Editar página", lambda p=path: self.special_page_dialog(p),
                             small=True).pack(fill="x", pady=(6,0))
            else:
                button_name = "Editar foto ✎" if path not in self.photo_edits else "Editar foto ✓"
                self._button(card, button_name, lambda p=path: self.edit_photo_dialog(p),
                             small=True).pack(fill="x", pady=(6,0))
                self._button(card, "Texto / pie de foto" + (" ✓" if has_caption(self.captions.get(path)) else ""),
                             lambda p=path: self.caption_dialog(p), small=True).pack(fill="x", pady=(4,0))
            for part in (card, thumb, lbl, meta):
                self._make_draggable(part, path, 'library')
            self.library_area.bind_wheel_recursive(card)
            for drop_target in (card, thumb, lbl, meta):
                self._register_drop(drop_target)
        self.library_area._update_scrollregion()
        self.library_area.canvas.yview_moveto(offset)

    def _show_empty_order(self):
        self._clear_children(self.order_area.inner)
        self._label(self.order_area.inner,
                    "Aquí aparecerá el orden de tus imágenes.\n\nRevelo las agrupará según las fotos por hoja elegidas.",
                    color=MUTED, size=11, justify="center").pack(pady=100)

    def render_order(self):
        # Un cambio de plantilla puede llegar mientras se reconstruyen las
        # tarjetas: no asumir que el thumbnail ya está precalculado.
        for path in self.pages:
            if path not in self.thumbnails_small and path in self.details:
                self._thumbnail(path)
        groups = self._groups()
        sheet_number = {path: i + 1 for i, group in enumerate(groups) for path in group}
        self.page_count_var.set(f'{len(self.pages)} elementos · {len(groups)} hojas')
        if not self.pages:
            self._show_empty_order()
            return
        offset = self.order_area.canvas.yview()[0]
        self._clear_children(self.order_area.inner)
        pinned = cover_path(self.special_pages)
        for idx, path in enumerate(self.pages):
            selected = self.order_selected == path
            is_cover = path == pinned
            slot = tk.Frame(self.order_area.inner, bg=SURFACE_2,
                            highlightbackground=ACCENT if selected else "#3A6074",
                            highlightthickness=2 if selected else 1,
                            padx=10, pady=6, cursor='hand2')
            slot.foto_slot_index = idx
            slot.pack(fill='x', padx=4, pady=5)
            number = tk.Label(slot, text=f'{idx + 1:02d}',
                              bg=ACCENT if selected else ACCENT_DARK,
                              fg=BG if selected else ACCENT,
                              width=3, font=('Segoe UI', 14, 'bold'), pady=18)
            number.pack(side='left', padx=(0, 11))
            group = groups[sheet_number[path]-1]
            image = (self._sheet_thumbnail(group, sheet_number[path]-1)
                     if (len(group) == 1 or (self.layout_template.get() == 'Diseño libre'
                           and any(p in self.layout_items for p in group)))
                     else self.thumbnails_small[path])
            thumb = tk.Label(slot, image=image, bg=SURFACE_2,
                             borderwidth=0, cursor='hand2')
            thumb.pack(side='left', padx=(0, 12))
            text_box = tk.Frame(slot, bg=SURFACE_2)
            text_box.pack(side='left', fill='x', expand=True)
            display_name = self.path_labels.get(path, path.name)
            short = display_name if len(display_name) <= 48 else display_name[:45] + '…'
            name = self._label(text_box, short, weight='bold', size=10, bg=SURFACE_2,
                               anchor='w', wraplength=285, justify='left')
            name.pack(fill='x')
            dim = self.details.get(path, (0, 0))
            subtext = ('Portada fija · inicio del documento' if is_cover else
                       f'Hoja {sheet_number[path]} · página independiente' if path in self.special_pages else
                       f'Hoja {sheet_number[path]} · diseño libre (vista de hoja)'
                       if self.layout_template.get() == 'Diseño libre' and
                          any(p in self.layout_items for p in group)
                       else f'Hoja {sheet_number[path]} · {dim[0]} × {dim[1]} px')
            sub = self._label(text_box, subtext, color=ACCENT if is_cover else MUTED,
                              size=9, bg=SURFACE_2, anchor='w')
            sub.pack(fill='x', pady=(5,0))
            arrows = tk.Frame(slot, bg=SURFACE_2)
            arrows.pack(side='right', padx=(7,0))
            b_up = self._button(arrows, '↑', lambda n=idx: self._shift(n,-1), small=True)
            b_down = self._button(arrows, '↓', lambda n=idx: self._shift(n,+1), small=True)
            b_up.pack(side='top', pady=(0,6))
            b_down.pack(side='top')
            if idx == 0 or (idx == 1 and pinned in self.pages):
                b_up.configure(state='disabled')
            if idx == len(self.pages) - 1 or is_cover:
                b_down.configure(state='disabled')
            for part in (slot, number, thumb, text_box, name, sub):
                part.bind('<ButtonRelease-1>', lambda event, p=path: self._order_click(p))
            self.order_area.bind_wheel_recursive(slot)
            for drop_target in (slot, number, thumb, text_box, name, sub):
                self._register_drop(drop_target)
        self.order_area._update_scrollregion()
        self.order_area.canvas.yview_moveto(offset)
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self._show_preview_page()

    def _order_click(self, path):
        """Origen con primer clic, destino con segundo; sin arrastrar ni hacer scroll pulsado."""
        if self.is_busy:
            return
        previously_selected = self.order_selected
        updated, selected, changed = click_move(self.pages, previously_selected, path, self.special_pages)
        self.pages = updated
        self.order_selected = selected
        if changed:
            name = self.path_labels.get(previously_selected, previously_selected.name)
            self.feedback.set(f'«{name}» ahora está en la posición {updated.index(previously_selected) + 1}.')
        elif selected is not None:
            self.feedback.set('Elemento señalado. Haz clic en la posición de destino para moverlo; vuelve a pulsarlo para cancelar.')
        elif path == cover_path(self.special_pages) and previously_selected is None:
            self.feedback.set('La portada está anclada en la primera posición.')
        else:
            self.feedback.set('Selección de ordenación cancelada.')
        self.render_order()

    def _shift(self, index, delta):
        j=index+delta
        if not 0 <= j < len(self.pages):
            return
        path=self.pages[index]
        if path == cover_path(self.special_pages) or (j == 0 and cover_path(self.special_pages) in self.pages):
            return
        self.pages[index],self.pages[j]=self.pages[j],self.pages[index]
        self.order_selected=path
        self.render_order()

    def _reposition(self, path, index):
        if path not in self.pages or not 0 <= index < len(self.pages):
            return
        old=self.pages.index(path)
        updated=move_item(self.pages,path,index,self.special_pages)
        if self.pages != updated:
            self.pages=updated
            self.order_selected=path
            self.render_order()
            self.feedback.set(f'«{self.path_labels.get(path,path.name)}» pasa a la posición {self.pages.index(path)+1}.')
        else:
            self.order_selected=path
            self.render_order()

    def _make_draggable(self,widget,path,panel):
        widget.bind('<ButtonPress-1>',lambda e,p=path,origin=panel:self._drag_press(e,p,origin))
        widget.bind('<B1-Motion>',self._drag_motion)
        widget.bind('<ButtonRelease-1>',self._drag_release)

    def _drag_press(self,event,path,panel):
        if self.is_busy:
            return
        self.drag_source=path
        self.drag_origin=panel
        self.drag_begin=(event.x_root,event.y_root)
        self.is_dragging=False

    def _drag_motion(self,event):
        if self.drag_source is None or self.drag_begin is None:
            return
        dx=abs(event.x_root-self.drag_begin[0])
        dy=abs(event.y_root-self.drag_begin[1])
        if dx+dy<9 and not self.is_dragging:
            return
        if not self.is_dragging:
            self.is_dragging=True
            self.drag_ghost=tk.Toplevel(self.root)
            self.drag_ghost.overrideredirect(True)
            self.drag_ghost.attributes('-topmost',True)
            try:self.drag_ghost.attributes('-alpha',0.9)
            except tk.TclError:pass
            tk.Label(self.drag_ghost,text='  ↕  '+self.path_labels.get(self.drag_source,self.drag_source.name)[:31]+'  ',
                     bg=ACCENT,fg=BG,padx=9,pady=7,font=('Segoe UI',10,'bold')).pack()
        if self.drag_ghost:
            self.drag_ghost.geometry(f'+{event.x_root+14}+{event.y_root+14}')

    def _drag_release(self,event):
        path=self.drag_source
        moving=self.is_dragging
        origin=self.drag_origin
        self.drag_source=None
        self.drag_origin=None
        self.drag_begin=None
        self.is_dragging=False
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost=None
        if path is None:
            return
        if moving:
            target=self.root.winfo_containing(event.x_root,event.y_root)
            while target is not None and not hasattr(target,'foto_slot_index'):
                target=getattr(target,'master',None)
            if target is not None:
                self._reposition(path,target.foto_slot_index)
        elif origin == 'order':
            # Un simple clic solo selecciona: NO recoloca la foto de la biblioteca.
            self.order_selected=path
            self.render_order()
        else:
            self.selected=path
            self.render_library()

    def _options(self):
        format_name = self.output_format.get()
        fmt = "Imagenes" if format_name.startswith("Imágenes") else format_name
        return ExportOptions(
            paper=self.paper.get(), orientation=self.orientation.get(),
            fit=self.fit.get(), dpi=int(self.dpi.get()), fmt=fmt,
            paper_background=self.paper_background.get(),
            paper_background_color=self.paper_background_color.get(),
            binding=self.binding.get() == "Sí",
            pdf_page_paths=frozenset(self.pdf_origins),
            photos_per_page=int(self.per_sheet.get()),
            special_pages=dict(self.special_pages),
            photo_edits={path: dict(spec) for path, spec in self.photo_edits.items()},
            layout_template=self.layout_template.get(),
            captions={path: dict(spec) for path, spec in self.captions.items()},
            numbering_enabled=self.numbering_enabled.get(),
            numbering_position=self.numbering_position.get(),
            numbering_skip_special=self.numbering_skip_special.get(),
            numbering_start=int(self.numbering_start.get()),
            numbering_format=self.numbering_format.get(),
            layout_items={path:dict(spec) for path,spec in self.layout_items.items()},
        )

    def open_preview(self):
        """Abre un visor de páginas con los mismos encajes de la exportación."""
        if not self.pages:
            messagebox.showinfo("Faltan fotos", "Añade al menos una foto para previsualizar.")
            return
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.lift()
            self.preview_window.focus_set()
            self._show_preview_page()
            return
        window = tk.Toplevel(self.root)
        window.title("Revelo · Previsualización de impresión")
        window.geometry("990x770")
        window.minsize(520, 480)
        window.configure(bg=BG)
        try:
            ico = app_asset("icono.ico")
            if sys.platform == "win32" and ico.exists():
                window.iconbitmap(str(ico))
        except tk.TclError:
            pass
        self.preview_window = window
        self.preview_book = False
        groups_open = self._groups()
        self.preview_index = next((i for i, group in enumerate(groups_open)
                                   if self.selected in group), 0)
        top = tk.Frame(window, bg=BG, padx=22, pady=15)
        top.pack(fill="x")
        self._label(top, "VISTA PREVIA DE IMPRESIÓN", size=15,
                    weight="bold").pack(anchor="w")
        self._label(top, "Comprueba cada página. No se exportará nada hasta que pulses Exportar fotos.",
                    color=MUTED, size=10).pack(anchor="w", pady=(5, 0))

        canvas_shell = tk.Frame(window, bg=SURFACE, padx=10, pady=10,
                                highlightbackground=BORDER, highlightthickness=1)
        canvas_shell.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        self.preview_canvas = tk.Canvas(canvas_shell, bg=SURFACE, borderwidth=0,
                                        highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._preview_resized)

        controls = tk.Frame(window, bg=BG, padx=22, pady=5)
        controls.pack(fill="x")
        self.preview_prev_btn = self._button(controls, "← Anterior", lambda: self._preview_move(-1), small=True)
        self.preview_prev_btn.pack(side="left")
        self.preview_next_btn = self._button(controls, "Siguiente →", lambda: self._preview_move(1), small=True)
        self.preview_next_btn.pack(side="right")
        self.preview_book_btn = self._button(controls, "Libro abierto", self._toggle_preview_book, small=True)
        self.preview_book_btn.pack(side="left", padx=(10,0))
        self._label(controls, "", textvariable=self.preview_page_text, size=11,
                    weight="bold").pack(fill="x", pady=(7, 0))
        self._label(window, "", textvariable=self.preview_detail_text, color=MUTED,
                    size=10).pack(padx=22, pady=(4, 16))
        window.bind("<Left>", lambda _event: self._preview_move(-1))
        window.bind("<Right>", lambda _event: self._preview_move(1))
        window.protocol("WM_DELETE_WINDOW", self._close_preview)
        self._show_preview_page()

    def _close_preview(self):
        if self.preview_resize_job is not None:
            self.root.after_cancel(self.preview_resize_job)
            self.preview_resize_job = None
        if self.preview_image is not None:
            self.preview_image.close()
            self.preview_image = None
        self.preview_photo = None
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None
        self.preview_canvas = None
        self.preview_book = False

    def _toggle_preview_book(self):
        groups = self._groups()
        spreads = book_spreads(len(groups))
        if not self.preview_book:
            page = self.preview_index
            self.preview_index = next((i for i, pair in enumerate(spreads) if page in pair), 0)
            self.preview_book = True
            self.preview_book_btn.configure(text="Página única")
        else:
            spread = spreads[min(self.preview_index, len(spreads)-1)]
            self.preview_index = spread[0] if spread[0] is not None else spread[1]
            self.preview_book = False
            self.preview_book_btn.configure(text="Libro abierto")
        self._show_preview_page()

    def _render_open_book(self, groups, spread):
        """Vista de álbum físico: tapa aislada y páginas con lomo, sin afectar PDF."""
        pages = []
        numbers = numbers_for_groups(groups, self.special_pages,
                                     enabled=self.numbering_enabled.get(),
                                     start=self.numbering_start.get(),
                                     skip_special=self.numbering_skip_special.get())
        for index in spread:
            if index is None:
                pages.append(None)
            else:
                im, _, _ = render_layout_page(groups[index], self._options(),
                                               preview_max_size=(620, 670), page_index=index,
                                               printed_number=numbers[index])
                pages.append(im)
        try:
            return render_book(tuple(pages), cover=(spread[0] is None))
        finally:
            for im in pages:
                if im is not None:
                    im.close()

    def _preview_move(self, step: int):
        if not self.pages:
            self._close_preview()
            return
        total = len(book_spreads(len(self._groups()))) if self.preview_book else len(self._groups())
        new_index = max(0, min(total - 1, self.preview_index + step))
        if new_index != self.preview_index:
            self.preview_index = new_index
            self._show_preview_page()

    def _show_preview_page(self):
        if self.preview_window is None or not self.preview_window.winfo_exists():
            return
        if not self.pages:
            self._close_preview()
            return
        groups = self._groups()
        if self.preview_book:
            spreads = book_spreads(len(groups))
            self.preview_index = min(self.preview_index, len(spreads)-1)
            spread = spreads[self.preview_index]
            label = ("Portada · página derecha" if spread[0] is None else
                     "Páginas " + " y ".join(str(j+1) for j in spread if j is not None))
            self.preview_page_text.set(f"Vista de libro · {label} · {self.preview_index+1}/{len(spreads)}")
            self.preview_prev_btn.configure(state="normal" if self.preview_index > 0 else "disabled")
            self.preview_next_btn.configure(state="normal" if self.preview_index < len(spreads)-1 else "disabled")
            try:
                rendered = self._render_open_book(groups, spread)
                old = self.preview_image
                self.preview_image = rendered
                if old is not None:
                    old.close()
                self.preview_detail_text.set("Vista de lectura simulada · El documento exportado conserva sus hojas individuales.")
                self._paint_preview()
            except Exception as exc:
                self.preview_detail_text.set(f"Error en la vista de libro: {exc}")
            return
        self.preview_index = min(self.preview_index, len(groups) - 1)
        group = groups[self.preview_index]
        path = group[0]
        short_label = self.path_labels.get(path, path.name)
        if len(group) > 1:
            short_label = f"{len(group)} imágenes · {short_label}…"
        self.preview_page_text.set(
            f"Hoja {self.preview_index + 1} de {len(groups)}  ·  {short_label}")
        self.preview_prev_btn.configure(state="normal" if self.preview_index > 0 else "disabled")
        self.preview_next_btn.configure(state="normal" if self.preview_index < len(groups) - 1 else "disabled")
        try:
            nums = numbers_for_groups(groups, self.special_pages,
                                      enabled=self.numbering_enabled.get(),
                                      start=self.numbering_start.get(),
                                      skip_special=self.numbering_skip_special.get())
            rendered, (w_mm, h_mm), lowres = render_layout_page(
                group, self._options(), preview_max_size=(1100, 850),
                page_index=self.preview_index, printed_number=nums[self.preview_index],
            )
            old = self.preview_image
            self.preview_image = rendered
            if old is not None:
                old.close()
            notice = " · Atención: elemento de poca resolución" if lowres else ""
            imported_pdf = any(item in self.pdf_origins for item in group)
            bind_note = ((" · Contiene páginas PDF" if imported_pdf and len(group) > 1 else
                          " · Página PDF importada" if imported_pdf else "") +
                         ((" · Encuadernación: " + ("izquierda" if self.preview_index % 2 == 0 else "derecha")) if self.binding.get() == "Sí" else ""))
            self.preview_detail_text.set(
                f"{self.paper.get()}  ·  {w_mm:g} × {h_mm:g} mm  ·  {self.fit.get()}"
                f"  ·  Salida: {self.dpi.get()} PPP{bind_note}{notice}"
            )
            self._paint_preview()
        except Exception as exc:
            self.preview_detail_text.set("No se pudo abrir esta imagen")
            if self.preview_canvas is not None:
                self.preview_canvas.delete("all")
                self.preview_canvas.create_text(240, 160, text=str(exc), fill=WARNING, width=400)

    def _preview_resized(self, _event=None):
        if self.preview_resize_job is not None:
            self.root.after_cancel(self.preview_resize_job)
        self.preview_resize_job = self.root.after(110, self._paint_preview)

    def _paint_preview(self):
        self.preview_resize_job = None
        canvas, picture = self.preview_canvas, self.preview_image
        if canvas is None or picture is None or not canvas.winfo_exists():
            return
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 50 or height < 50:
            return
        room_w, room_h = max(1, width - 56), max(1, height - 54)
        scale = min(room_w / picture.width, room_h / picture.height)
        draw_w, draw_h = max(1, round(picture.width * scale)), max(1, round(picture.height * scale))
        if (draw_w, draw_h) != picture.size:
            display = picture.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
        else:
            display = picture
        self.preview_photo = ImageTk.PhotoImage(display)
        if display is not picture:
            display.close()
        x, y = (width - draw_w) // 2, (height - draw_h) // 2
        canvas.delete("all")
        canvas.create_rectangle(x + 7, y + 8, x + draw_w + 7, y + draw_h + 8,
                                fill=BG, outline="")
        canvas.create_rectangle(x - 2, y - 2, x + draw_w + 2, y + draw_h + 2,
                                outline=ACCENT, width=2)
        canvas.create_image(x, y, image=self.preview_photo, anchor="nw")

    def start_export(self):
        if self.is_busy:
            return
        if not self.pages:
            messagebox.showinfo("Faltan páginas", "Añade fotos o PDF antes de exportar.")
            return
        opts = self._options()
        suggested = f"Revelo_{opts.paper.replace(' × ', 'x').replace(' ', '')}"
        if opts.fmt == "Imagenes":
            dest_name = filedialog.askdirectory(title="¿Dónde guardar las fotos redimensionadas?")
        else:
            ext = ".pdf" if opts.fmt == "PDF" else ".docx"
            dest_name = filedialog.asksaveasfilename(
                title="Guardar archivo de fotos", defaultextension=ext,
                initialfile=suggested + ext,
                filetypes=[("Documento PDF", "*.pdf")] if opts.fmt == "PDF" else [("Word", "*.docx")],
            )
        if not dest_name:
            return
        dest = Path(dest_name)
        # Nunca se permite reemplazar por accidente un PDF que se haya importado.
        if opts.fmt != "Imagenes" and dest.resolve() in (set(self.pdf_origins.values()) | self.recovered_pdf_sources):
            messagebox.showwarning("Conserva el PDF original",
                "Has elegido el mismo PDF que has importado.\nGuarda el nuevo documento con otro nombre para conservar el recetario original.")
            return
        if opts.fmt != "Imagenes" and dest.exists():
            if not messagebox.askyesno("Sobrescribir documento", "Ese archivo ya existe. ¿Quieres sustituirlo?"):
                return
        self._set_busy(True)
        self.export_btn.configure(text="Exportando…")
        self.progress["value"] = 0
        self.percent_text.set("(0 %)")
        self.feedback.set("Preparando las fotografías…")
        pages = self.pages.copy()

        def do_work():
            try:
                def notify(current, total, name):
                    self.updates.put(("progress", current, total, name))
                result, warnings = export(pages, opts, dest, notify)
                self.updates.put(("success", result, warnings, len(pages)))
            except Exception as e:
                self.updates.put(("error", str(e)))

        threading.Thread(target=do_work, daemon=True).start()

    def _project_settings(self) -> dict:
        return {
            "paper": self.paper.get(), "orientation": self.orientation.get(),
            "fit": self.fit.get(), "dpi": int(self.dpi.get()),
            "paper_background": self.paper_background.get(),
            "paper_background_color": self.paper_background_color.get(),
            "fmt": self._options().fmt, "binding": self.binding.get() == "Sí",
            "photos_per_page": int(self.per_sheet.get()),
            "layout_template": self.layout_template.get(),
            "numbering_enabled": self.numbering_enabled.get(),
            "numbering_position": self.numbering_position.get(),
            "numbering_skip_special": self.numbering_skip_special.get(),
            "numbering_start": int(self.numbering_start.get()),
            "numbering_format": self.numbering_format.get(),
        }

    def save_project_dialog(self):
        if self.is_busy:
            return
        if not self.paths:
            messagebox.showinfo("Guardar proyecto", "Añade al menos una foto o PDF para guardar.")
            return
        proposed = self.project_path.stem if self.project_path else "Mi proyecto Revelo"
        chosen = filedialog.asksaveasfilename(
            title="Guardar proyecto portable de Revelo",
            defaultextension=".revelo", initialfile=proposed + ".revelo",
            filetypes=[("Proyecto de Revelo", "*.revelo")],
        )
        if not chosen:
            return
        target = Path(chosen)
        if target.exists() and not messagebox.askyesno(
            "Sustituir proyecto", f"¿Quieres reemplazar {target.name}?"):
            return
        self._set_busy(True)
        self.feedback.set("Guardando imágenes y orden dentro del proyecto…")
        self.progress["value"] = 0
        self.percent_text.set("(0 %)")
        paths, pages = self.paths.copy(), self.pages.copy()
        labels, origins, settings = dict(self.path_labels), dict(self.pdf_origins), self._project_settings()
        special = dict(self.special_pages)
        photos_changed = dict(self.photo_edits)
        captions_changed = dict(self.captions)
        layout_changed = dict(self.layout_items)

        def worker():
            try:
                save_project(target, paths, pages, labels, origins, settings,
                             progress=lambda n, total: self.updates.put(("project_progress", n, total, "Guardando")),
                             special_pages=special, photo_edits=photos_changed,
                             captions=captions_changed, layout_items=layout_changed)
                self.updates.put(("project_saved", target))
            except Exception as exc:
                self.updates.put(("project_error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def open_project_dialog(self):
        if self.is_busy:
            return
        chosen = filedialog.askopenfilename(
            title="Abrir proyecto de Revelo", filetypes=[("Proyecto de Revelo", "*.revelo")],
        )
        if not chosen:
            return
        if self.paths and not messagebox.askyesno(
            "Abrir proyecto", "Se reemplazará la composición actual. ¿Has guardado los cambios que quieras conservar?"):
            return
        self._set_busy(True)
        self._close_preview()
        self.progress["value"] = 0
        self.percent_text.set("(0 %)")
        self.feedback.set("Abriendo proyecto y recuperando sus imágenes…")
        source = Path(chosen)

        def worker():
            temporary = tempfile.TemporaryDirectory(prefix="Revelo_Proyecto_")
            try:
                loaded = load_project(source, Path(temporary.name),
                                      progress=lambda n, total: self.updates.put(("project_progress", n, total, "Abriendo")))
                self.updates.put(("project_loaded", source, temporary, loaded))
            except Exception as exc:
                temporary.cleanup()
                self.updates.put(("project_error", str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_project_open(self, source, temporary, loaded):
        old = self.project_temp
        self.project_temp = temporary
        self.paths = loaded["paths"]
        self.pages = anchored_order(loaded['pages'], loaded.get('special_pages', {}))
        self.path_labels = loaded["labels"]
        self.pdf_origins = loaded["pdf_origins"]
        self.special_pages = loaded.get("special_pages", {})
        self.photo_edits = loaded.get("photo_edits", {})
        self.captions = loaded.get("captions", {})
        self.layout_items = loaded.get("layout_items", {})
        self.recovered_pdf_sources.clear()
        self.thumbnails.clear()
        self.thumbnails_small.clear()
        self.details.clear()
        self.selected = None
        self.order_selected = None
        self.output_path = None
        self.open_btn.configure(state="disabled")
        for path in self.paths:
            self.details[path] = source_dimensions(path)
            self._thumbnail(path)
        settings = loaded["settings"]
        self._restoring_project = True
        self.paper.set(settings["paper"])
        self.orientation.set(settings["orientation"])
        self.fit.set(settings["fit"])
        self.paper_background.set(settings.get("paper_background", "Blanco"))
        self.paper_background_color.set(settings.get("paper_background_color", "#FFFFFF"))
        self.dpi.set(str(settings["dpi"]))
        self.output_format.set("Imágenes (mismo formato)" if settings["fmt"] == "Imagenes" else settings["fmt"])
        self.binding.set("Sí" if settings["binding"] else "No")
        self.per_sheet.set(str(settings["photos_per_page"]))
        self.layout_template.set(settings.get("layout_template", "Cuadrícula"))
        self.sheet_thumbnails.clear()
        self.numbering_enabled.set(settings.get("numbering_enabled", False))
        self.numbering_position.set(settings.get("numbering_position", "Exterior"))
        self.numbering_skip_special.set(settings.get("numbering_skip_special", True))
        self.numbering_start.set(settings.get("numbering_start", 1))
        self.numbering_format.set(settings.get("numbering_format", "1"))
        self._restoring_project = False
        self.project_path = source
        self.render_library()
        self.render_order()
        self._set_busy(False)
        self.progress["value"] = 100
        self.percent_text.set("(100 %)")
        self.feedback.set(f"✓ Proyecto abierto: {source.name} · {len(self.paths)} elementos · orden recuperado")
        old.cleanup()

    def _show_export_completed(self, result: Path, sheet_count: int,
                               element_count: int, warning_count: int) -> None:
        """Ventana propia de Revelo, sin cuadros genéricos de Windows."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Revelo · Exportación completada")
        dialog.configure(bg=BG)
        dialog.geometry("630x375" if warning_count else "630x335")
        dialog.minsize(480, 260)
        dialog.resizable(True, True)
        dialog.transient(self.root)
        try:
            ico = app_asset("icono.ico")
            if sys.platform == "win32" and ico.exists():
                dialog.iconbitmap(str(ico))
        except tk.TclError:
            pass
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")
        container = tk.Frame(dialog, bg=BG, padx=26, pady=22)
        container.pack(fill="both", expand=True)
        headline = tk.Frame(container, bg=BG)
        headline.pack(fill="x")
        icon = tk.Label(headline, text="✓", bg=ACCENT, fg=BG,
                        font=("Segoe UI", 19, "bold"), width=2, height=1)
        icon.pack(side="left", padx=(0, 15))
        heading = tk.Frame(headline, bg=BG)
        heading.pack(side="left")
        self._label(heading, "Exportación completada", size=18, weight="bold").pack(anchor="w")
        self._label(heading, "El documento ya está listo para imprimir.",
                    size=10, color=MUTED).pack(anchor="w", pady=(2, 0))

        panel = tk.Frame(container, bg=SURFACE, padx=15, pady=13,
                         highlightbackground=BORDER, highlightthickness=1)
        panel.pack(fill="x", pady=(21, 12))
        self._label(panel, f"{sheet_count} hoja(s) · {element_count} elemento(s)",
                    size=12, weight="bold", bg=SURFACE).pack(anchor="w")
        self._label(panel, str(result), size=10, color=MUTED, bg=SURFACE,
                    wraplength=520, justify="left").pack(anchor="w", pady=(6, 0))
        if result.suffix.lower() == ".pdf":
            self._label(container,
                        "Este PDF incluye las imágenes originales para poder reeditarlas en Revelo. "
                        "Si lo compartes, también podrán extraerse esas imágenes.",
                        size=9, color=MUTED, wraplength=540,
                        justify="left").pack(anchor="w", pady=(0, 8))
        if warning_count:
            self._label(container,
                        f"Atención: {warning_count} elemento(s) podrían verse borrosos al imprimir.",
                        size=10, color=WARNING, wraplength=555,
                        justify="left").pack(anchor="w", pady=(2, 8))
        footer = tk.Frame(container, bg=BG)
        footer.pack(side="bottom", fill="x")
        self._button(footer, "Aceptar", dialog.destroy, small=True, accent=True).pack(side="right")
        def open_folder():
            dialog.destroy()
            self.open_result()
        self._button(footer, "Abrir carpeta", open_folder, small=True).pack(side="right", padx=(0, 8))
        dialog.bind("<Escape>", lambda _evt: dialog.destroy())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.grab_set()
        dialog.focus_set()

    def _poll(self):
        try:
            while True:
                event = self.updates.get_nowait()
                if event[0] == "mobile_received":
                    self.pending_mobile.append(event[1])
                    self.mobile_received_count += 1
                    self.mobile_status.set(f"✓ {self.mobile_received_count} foto(s) recibidas del móvil")
                    self.feedback.set(f"Recibidas {self.mobile_received_count} foto(s) del móvil. Añadiendo a Revelo…")
                elif event[0] == "import_progress":
                    _, current, total, name = event
                    percent = round(100 * current / total)
                    self.progress["value"] = percent
                    self.percent_text.set(f"({percent} %)")
                    self.feedback.set(f"Leyendo {name}: página {current}/{total}  ({percent} %)")
                elif event[0] == "pdf_recovered":
                    _, source, count, per_sheet, source_template = event
                    self.recovered_pdf_sources.add(source.resolve())
                    if not self.paths:
                        self.per_sheet.set(str(per_sheet))
                        self.layout_template.set(source_template)
                    self.feedback.set(f"PDF reversible: recuperadas {count} fotografías originales de {source.name}")
                elif event[0] == "import_done":
                    _, items, detected_paper, mixed_pdf, errors, special, edits, captions, layout_items = event
                    self._finish_import(items, detected_paper, mixed_pdf, errors, special, edits, captions, layout_items)
                    self.progress["value"] = 0
                    self.percent_text.set("(0 %)")
                elif event[0] == "project_progress":
                    _, current, total, operation = event
                    percent = round(100 * current / total)
                    self.progress["value"] = percent
                    self.percent_text.set(f"({percent} %)")
                    self.feedback.set(f"{operation} proyecto: {current}/{total} archivos")
                elif event[0] == "project_saved":
                    _, target = event
                    self.project_path = target
                    self._set_busy(False)
                    self.progress["value"] = 100
                    self.percent_text.set("(100 %)")
                    self.feedback.set(f"✓ Proyecto guardado: {target.name} · portable con fotos incluidas")
                    messagebox.showinfo("Proyecto guardado", f"El proyecto está listo en:\n{target}")
                elif event[0] == "project_loaded":
                    _, source, temporary, loaded = event
                    try:
                        self._finish_project_open(source, temporary, loaded)
                    except Exception as exc:
                        self._set_busy(False)
                        messagebox.showerror("Abrir proyecto", str(exc))
                elif event[0] == "project_error":
                    self._set_busy(False)
                    self.progress["value"] = 0
                    self.percent_text.set("(0 %)")
                    self.feedback.set("No se ha podido abrir o guardar el proyecto.")
                    messagebox.showerror("Proyecto de Revelo", event[1])
                elif event[0] == "progress":
                    _, current, total, name = event
                    percent = round(100 * current / total)
                    self.progress["value"] = percent
                    self.percent_text.set(f"({percent} %)")
                    self.feedback.set(f"Procesando {current}/{total}: {name}  ({percent} %)")
                elif event[0] == "success":
                    _, result, warning_count, count = event
                    self._set_busy(False)
                    self.export_btn.configure(text="Exportar fotos   →")
                    self.progress["value"] = 100
                    self.percent_text.set("(100 %)")
                    self.output_path = Path(result)
                    self.open_btn.configure(state="normal")
                    sheet_count = len(self._groups())
                    self.feedback.set(f"✓ {sheet_count} hoja(s) exportadas. Resultado: {self.output_path.name}")
                    self._show_export_completed(Path(result), sheet_count, count, warning_count)
                elif event[0] == "error":
                    self._set_busy(False)
                    self.export_btn.configure(text="Exportar fotos   →")
                    self.progress["value"] = 0
                    self.percent_text.set("(0 %)")
                    self.feedback.set("No se pudo completar la exportación.")
                    messagebox.showerror("Error al exportar", event[1])
        except queue.Empty:
            pass
        if self.pending_mobile and not self.is_busy:
            batch = self.pending_mobile[:]
            self.pending_mobile.clear()
            self.import_paths(batch)
        self.root.after(120, self._poll)

    def _on_close(self):
        if self.is_busy:
            messagebox.showinfo("Operación en curso", "Termina de importar o exportar antes de cerrar Revelo.")
            return
        self._close_preview()
        self._close_mobile_import()
        self.mobile_temp.cleanup()
        self.pdf_temp.cleanup()
        self.project_temp.cleanup()
        self.special_temp.cleanup()
        self.root.destroy()

    def open_result(self):
        if not self.output_path:
            return
        destination = self.output_path if self.output_path.is_dir() else self.output_path.parent
        try:
            if sys.platform == "win32":
                os.startfile(str(destination))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(destination)])
            else:
                subprocess.Popen(["xdg-open", str(destination)])
        except OSError as e:
            messagebox.showerror("No se pudo abrir", str(e))


def main():
    try:
        root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
    except (tk.TclError, RuntimeError):
        root = tk.Tk()
    try:
        ico = app_asset("icono.ico")
        if ico.exists() and sys.platform == "win32":
            root.iconbitmap(str(ico))
    except tk.TclError:
        pass
    application = ReveloApp(root)
    root.protocol("WM_DELETE_WINDOW", application._on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
