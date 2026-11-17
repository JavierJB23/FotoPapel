"""Revelo: organiza fotografías y páginas PDF para imprimir sin complicaciones."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tempfile
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from PIL import Image, ImageTk, ImageOps, ImageDraw

from processor import (
    ExportOptions, PAPER_SIZES, SUPPORTED_EXTENSIONS, FIT_MODES, export, render_print_image,
    pixel_size, source_dimensions,
)
from pdf_import import import_pdf_pages, matched_paper
from mobile_import import PhoneTransferServer
import qrcode

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
        self.root.title("Revelo · Fotos y PDF listos para imprimir")
        self.root.geometry("1270x845")
        self.root.minsize(940, 650)
        self.root.configure(bg=BG)
        self.paths: list[Path] = []
        self.path_labels: dict[Path, str] = {}
        self.pdf_origins: dict[Path, Path] = {}
        self.pdf_temp = tempfile.TemporaryDirectory(prefix="Revelo_PDF_")
        self.mobile_temp = tempfile.TemporaryDirectory(prefix="Revelo_Movil_")
        self.mobile_server: PhoneTransferServer | None = None
        self.mobile_window: tk.Toplevel | None = None
        self.mobile_qr: ImageTk.PhotoImage | None = None
        self.mobile_status = tk.StringVar(value="Esperando fotografías…")
        self.mobile_received_count = 0
        self.pending_mobile: list[Path] = []
        self.pages: list[Path] = []
        self.thumbnails: dict[Path, ImageTk.PhotoImage] = {}
        self.thumbnails_small: dict[Path, ImageTk.PhotoImage] = {}
        self.details: dict[Path, tuple[int, int]] = {}
        self.selected: Path | None = None
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
        self.dpi = tk.StringVar(value="300")
        self.output_format = tk.StringVar(value="PDF")
        self.binding = tk.StringVar(value="No")
        self.overview = tk.StringVar(value="A4 · 210 × 297 mm · 2480 × 3508 px a 300 PPP")
        self.feedback = tk.StringVar(value="Carga fotos o PDF para empezar. Los archivos originales no se modifican.")
        self.count_var = tk.StringVar(value="0 elementos")
        self.page_count_var = tk.StringVar(value="0 páginas")
        self.percent_text = tk.StringVar(value="(0 %)")
        self.preview_page_text = tk.StringVar(value="")
        self.preview_detail_text = tk.StringVar(value="")

        self._style()
        self._layout()
        self._update_overview()
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
            "Custom.Vertical.TScrollbar", background=SURFACE_2,
            troughcolor=SURFACE, bordercolor=SURFACE, arrowcolor=MUTED,
        )
        style.configure(
            "Revelo.Horizontal.TProgressbar", troughcolor=SURFACE_2,
            background=ACCENT, darkcolor=ACCENT, lightcolor=ACCENT,
            bordercolor=BORDER, thickness=15, relief="flat",
        )

    def _label(self, parent, text, *, size=10, color=TEXT, weight="normal", bg=None, **kw):
        return tk.Label(parent, text=text, font=("Segoe UI", size, weight), fg=color,
                        bg=bg or parent.cget("bg"), **kw)

    def _button(self, parent, text, command, *, accent=False, small=False, **kwargs):
        return tk.Button(
            parent, text=text, command=command,
            bg=ACCENT if accent else SURFACE_2,
            fg=BG if accent else TEXT,
            activebackground="#83EBD2" if accent else "#2C435D",
            activeforeground=BG if accent else TEXT,
            font=("Segoe UI", 10 if small else 11, "bold"),
            bd=0, relief="flat", cursor="hand2", highlightthickness=0,
            padx=12 if small else 17, pady=6 if small else 10, **kwargs,
        )

    def _layout(self):
        header = tk.Frame(self.root, bg=BG, padx=28, pady=18)
        header.pack(fill="x")
        left = tk.Frame(header, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        with Image.open(app_asset("logo_cabecera.png")) as logo:
            self.header_icon = ImageTk.PhotoImage(logo.convert("RGBA").resize((59, 59), Image.Resampling.LANCZOS))
        tk.Label(left, image=self.header_icon, bg=BG, borderwidth=0).pack(side="left", padx=(0, 14))
        htext = tk.Frame(left, bg=BG)
        htext.pack(side="left")
        self._label(htext, "Revelo", size=23, weight="bold").pack(anchor="w")
        self._label(htext, "Tus fotos y documentos, listos para imprimir", color=MUTED, size=10).pack(anchor="w")

        setting_outer = tk.Frame(self.root, bg=BG, padx=24)
        setting_outer.pack(fill="x")
        settings = tk.Frame(setting_outer, bg=SURFACE, padx=17, pady=14,
                            highlightbackground=BORDER, highlightthickness=1)
        settings.pack(fill="x")
        # Una sola línea, con anchuras proporcionadas al contenido.
        # grid evita que los cinco primeros controles absorban todo el ancho
        # dejando el selector de encuadernación en una segunda fila.
        row = tk.Frame(settings, bg=SURFACE)
        row.pack(fill="x")
        fields = [
            ("TAMAÑO DE IMPRESIÓN", self.paper, list(PAPER_SIZES), 112, 3),
            ("ORIENTACIÓN", self.orientation, ["Automática", "Vertical", "Horizontal"], 100, 2),
            ("ENCAJE EN EL PAPEL", self.fit, list(FIT_MODES), 180, 5),
            ("CALIDAD", self.dpi, ["150", "300", "600"], 72, 1),
            ("EXPORTAR COMO", self.output_format, ["PDF", "Word", "Imágenes (mismo formato)"], 140, 3),
            ("MÁRGENES DE ENCUADERNACIÓN", self.binding, ["No", "Sí"], 204, 3),
        ]
        for column, (caption, variable, choices, minwidth, weight) in enumerate(fields):
            row.grid_columnconfigure(column, weight=weight, minsize=minwidth)
            self._field(row, caption, variable, choices, column=column,
                        compact=(column == 5), last=(column == 5))
        info = tk.Frame(settings, bg=SURFACE)
        info.pack(fill="x", pady=(12, 0))
        self._label(info, "●", color=ACCENT, size=10).pack(side="left")
        self._label(info, "  ", color=MUTED).pack(side="left")
        self._label(info, "", size=10, color=MUTED, textvariable=self.overview).pack(side="left")
        self._label(info, "  ·  Una página por hoja en Word y PDF", color=MUTED).pack(side="left")
        for var in (self.paper, self.orientation, self.dpi, self.fit, self.output_format, self.binding):
            var.trace_add("write", self._update_overview)

        # Reservar el pie ANTES de distribuir el espacio restante a los paneles;
        # así los botones nunca quedan debajo de la barra de tareas de Windows.
        footer = tk.Frame(self.root, bg=BG, padx=25, pady=10)
        footer.pack(side="bottom", fill="x")
        self.open_btn = self._button(footer, "Abrir resultado", self.open_result, small=True)
        self.open_btn.pack(side="right", padx=(8, 0))
        self.open_btn.configure(state="disabled")
        self.export_btn = self._button(footer, "Exportar fotos   →", self.start_export, accent=True)
        self.export_btn.pack(side="right")
        self.preview_btn = self._button(footer, "◉  Previsualización", self.open_preview)
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

        content = tk.Frame(self.root, bg=BG, padx=24, pady=10)
        content.pack(fill="both", expand=True)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=6, uniform="grid")
        content.grid_columnconfigure(1, weight=5, uniform="grid")
        left_panel = self._panel(content)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_panel = self._panel(content)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        library_top = tk.Frame(left_panel, bg=SURFACE, padx=16, pady=14)
        library_top.pack(fill="x")
        title = tk.Frame(library_top, bg=SURFACE)
        title.pack(side="left")
        self._label(title, "FOTOS Y PDF CARGADOS", size=12, weight="bold").pack(anchor="w")
        self._label(title, "0 fotos", textvariable=self.count_var, size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        buttons = tk.Frame(library_top, bg=SURFACE)
        buttons.pack(side="right")
        files_row = tk.Frame(buttons, bg=SURFACE)
        files_row.pack(fill="x")
        self.add_btn = self._button(files_row, "+ Añadir fotos / PDF", self.add_photos, accent=True, small=True)
        self.add_btn.pack(side="left", padx=(0, 7))
        self.clear_btn = self._button(files_row, "Vaciar", self.clear, small=True)
        self.clear_btn.pack(side="left")
        self.mobile_btn = self._button(buttons, "Importar desde móvil  ·  QR", self.open_mobile_import, small=True)
        self.mobile_btn.pack(fill="x", pady=(7, 0))
        tk.Frame(left_panel, height=1, bg=BORDER).pack(fill="x")
        self.library_area = ScrollingArea(left_panel)
        self.library_area.pack(fill="both", expand=True, padx=9, pady=9)
        self.library_area.canvas.bind("<Configure>", self._on_library_resize, add="+")
        self.library_placeholder = self._label(
            self.library_area.inner, "Tus fotos y páginas PDF aparecerán aquí.\n\nPulsa «Añadir fotos / PDF» para elegir archivos.\nAdmite JPG, PNG, HEIC, WEBP, TIFF y PDF.",
            color=MUTED, size=12, justify="center",
        )
        self.library_placeholder.pack(pady=115)

        ordering_top = tk.Frame(right_panel, bg=SURFACE, padx=16, pady=14)
        ordering_top.pack(fill="x")
        rt = tk.Frame(ordering_top, bg=SURFACE)
        rt.pack(side="left")
        self._label(rt, "ORDEN DE LAS PÁGINAS", size=12, weight="bold").pack(anchor="w")
        self._label(rt, "0 páginas", textvariable=self.page_count_var,
                    size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        self.reset_btn = self._button(ordering_top, "Orden inicial", self.reset_order, small=True)
        self.reset_btn.pack(side="right")
        tk.Frame(right_panel, height=1, bg=BORDER).pack(fill="x")
        hint = tk.Frame(right_panel, bg=ACCENT_DARK, padx=12, pady=9)
        hint.pack(fill="x", padx=12, pady=(12, 2))
        self._label(hint, "Arrastra a un número, usa las flechas o selecciona un elemento y su posición.",
                    size=10, color="#C1F3E5").pack(anchor="w")
        self.order_area = ScrollingArea(right_panel)
        self.order_area.pack(fill="both", expand=True, padx=9, pady=9)
        self._show_empty_order()

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
        return tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)

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
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self._show_preview_page()

    def _thumbnail(self, path: Path) -> ImageTk.PhotoImage:
        if path not in self.thumbnails:
            with Image.open(path) as original:
                im = ImageOps.exif_transpose(original)
                im.thumbnail((150, 108), Image.Resampling.LANCZOS)
                rgba = im.convert("RGBA")
                background = Image.new("RGBA", (150, 108), (29, 45, 67, 255))
                x = (background.width - rgba.width) // 2
                y = (background.height - rgba.height) // 2
                background.alpha_composite(rgba, (x, y))
                self.thumbnails[path] = ImageTk.PhotoImage(background.convert("RGB"))
                self.thumbnails_small[path] = ImageTk.PhotoImage(background.convert("RGB").resize((50, 36), Image.Resampling.LANCZOS))
        return self.thumbnails[path]

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
        for button in (self.add_btn, self.clear_btn, self.reset_btn,
                       self.preview_btn, self.export_btn):
            button.configure(state=state)

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
        imported_pdfs = set(self.pdf_origins.values())
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
                        images, sizes = import_pdf_pages(
                            source, temp_dir,
                            progress=lambda i, n, name: self.updates.put(("import_progress", i, n, name)),
                        )
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
            self.updates.put(("import_done", items, detected_paper, mixed_pdf, errors))

        threading.Thread(target=do_import, daemon=True).start()

    def _finish_import(self, items, detected_paper, mixed_pdf, errors):
        was_empty = not self.paths
        count = 0
        for path, dims, label, origin in items:
            try:
                self._thumbnail(path)
            except (OSError, ValueError, SyntaxError) as error:
                errors.append(f"{label}: no se pudo mostrar ({error})")
                continue
            self.details[path] = dims
            self.path_labels[path] = label
            if origin is not None:
                self.pdf_origins[path] = origin
            self.paths.append(path)
            self.pages.append(path)
            count += 1
        if count and was_empty and detected_paper:
            self.paper.set(detected_paper)
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
        if self.selected == path:
            self.selected = None
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
            self.selected = None
            self.render_library()
            self.render_order()
            self.feedback.set("Lista vacía. Los originales no se han modificado.")
            self._close_preview()

    def reset_order(self):
        if self.paths:
            self.pages = self.paths.copy()
            self.render_order()
            self.feedback.set("Restaurado el orden en que cargaste las fotos y los PDF.")

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
        self._clear_children(self.library_area.inner)
        self.count_var.set(f"{len(self.paths)} elemento{'s' if len(self.paths) != 1 else ''}")
        if not self.paths:
            self._label(self.library_area.inner,
                        "Tus fotos y páginas PDF aparecerán aquí.\n\nPulsa «Añadir fotos / PDF» para elegir archivos.\nAdmite JPG, PNG, HEIC, WEBP, TIFF y PDF.",
                        color=MUTED, size=12, justify="center").pack(pady=115)
            return
        for column in range(self.library_cols):
            self.library_area.inner.grid_columnconfigure(column, weight=1)
        for index, path in enumerate(self.paths):
            selected = self.selected == path
            card = tk.Frame(self.library_area.inner, bg=SURFACE_2,
                            highlightbackground=ACCENT if selected else BORDER,
                            highlightthickness=2 if selected else 1,
                            cursor="hand2", padx=8, pady=8)
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
            kind = "PDF" if path in self.pdf_origins else path.suffix[1:].upper()
            meta = self._label(card, f"{w} × {h} px  ·  {kind}",
                               size=9, color=MUTED, bg=SURFACE_2, anchor="w")
            meta.pack(fill="x", pady=(2, 0))
            remove = tk.Button(card, text="×", command=lambda p=path: self.remove_photo(p),
                               font=("Segoe UI", 12, "bold"), bg="#33455D", fg=TEXT,
                               activebackground="#5B3444", activeforeground=TEXT,
                               borderwidth=0, padx=5, pady=0, cursor="hand2")
            remove.place(relx=1, x=-3, y=3, anchor="ne")
            for part in (card, thumb, lbl, meta):
                self._make_draggable(part, path)
            self.library_area.bind_wheel_recursive(card)
        self.library_area._update_scrollregion()

    def _show_empty_order(self):
        self._clear_children(self.order_area.inner)
        self._label(self.order_area.inner,
                    "Aquí aparecerán las posiciones 1, 2, 3…\n\nCada posición será una página del documento exportado.",
                    color=MUTED, size=11, justify="center").pack(pady=100)

    def render_order(self):
        self.page_count_var.set(f"{len(self.pages)} página{'s' if len(self.pages) != 1 else ''}")
        if not self.pages:
            self._show_empty_order()
            return
        offset = self.order_area.canvas.yview()[0]
        self._clear_children(self.order_area.inner)
        for idx, path in enumerate(self.pages):
            slot = tk.Frame(self.order_area.inner, bg=SURFACE_2,
                            highlightbackground=BORDER, highlightthickness=1,
                            padx=10, pady=9, cursor="hand2")
            slot.foto_slot_index = idx
            slot.pack(fill="x", padx=4, pady=4)
            number = tk.Label(slot, text=f"{idx + 1:02d}", bg=ACCENT_DARK, fg=ACCENT,
                              width=3, font=("Segoe UI", 12, "bold"), pady=12)
            number.pack(side="left", padx=(0, 10))
            thumb = tk.Label(slot, image=self.thumbnails_small[path], bg=SURFACE_2,
                             borderwidth=0, cursor="hand2")
            thumb.pack(side="left", padx=(0, 10))
            text_box = tk.Frame(slot, bg=SURFACE_2)
            text_box.pack(side="left", fill="x", expand=True)
            display_name = self.path_labels.get(path, path.name)
            short = display_name if len(display_name) <= 35 else display_name[:31] + "…"
            name = self._label(text_box, short, weight="bold", size=10, bg=SURFACE_2, anchor="w")
            name.pack(fill="x")
            dim = self.details.get(path, (0, 0))
            sub = self._label(text_box, f"Página {idx + 1}  ·  {dim[0]} × {dim[1]} px",
                              color=MUTED, size=9, bg=SURFACE_2, anchor="w")
            sub.pack(fill="x", pady=(3, 0))
            arrows = tk.Frame(slot, bg=SURFACE_2)
            arrows.pack(side="right", padx=(8, 0))
            b_up = self._button(arrows, "↑", lambda n=idx: self._shift(n, -1), small=True)
            b_down = self._button(arrows, "↓", lambda n=idx: self._shift(n, +1), small=True)
            b_up.pack(side="left", padx=(0, 3))
            b_down.pack(side="left")
            if idx == 0:
                b_up.configure(state="disabled")
            if idx == len(self.pages) - 1:
                b_down.configure(state="disabled")
            for part in (slot, number, thumb, text_box, name, sub):
                self._make_draggable(part, path)
            self.order_area.bind_wheel_recursive(slot)
        self.order_area._update_scrollregion()
        self.order_area.canvas.yview_moveto(offset)
        if self.preview_window is not None and self.preview_window.winfo_exists():
            self._show_preview_page()

    def _shift(self, index, delta):
        j = index + delta
        if j < 0 or j >= len(self.pages):
            return
        self.pages[index], self.pages[j] = self.pages[j], self.pages[index]
        self.render_order()

    def _reposition(self, path, index):
        if path not in self.pages or index < 0 or index >= len(self.pages):
            return
        old = self.pages.index(path)
        if old != index:
            self.pages.pop(old)
            self.pages.insert(index, path)
            self.render_order()
            self.feedback.set(f"«{self.path_labels.get(path, path.name)}» pasa a la posición {index + 1}.")

    def _make_draggable(self, widget, path):
        widget.bind("<ButtonPress-1>", lambda e, p=path: self._drag_press(e, p))
        widget.bind("<B1-Motion>", self._drag_motion)
        widget.bind("<ButtonRelease-1>", self._drag_release)

    def _drag_press(self, event, path):
        if self.is_busy:
            return
        self.drag_source = path
        self.drag_begin = (event.x_root, event.y_root)
        self.is_dragging = False

    def _drag_motion(self, event):
        if not self.drag_source or self.drag_begin is None:
            return
        dx = abs(event.x_root - self.drag_begin[0])
        dy = abs(event.y_root - self.drag_begin[1])
        if dx + dy < 9 and not self.is_dragging:
            return
        if not self.is_dragging:
            self.is_dragging = True
            self.drag_ghost = tk.Toplevel(self.root)
            self.drag_ghost.overrideredirect(True)
            self.drag_ghost.attributes("-topmost", True)
            try:
                self.drag_ghost.attributes("-alpha", 0.9)
            except tk.TclError:
                pass
            tk.Label(self.drag_ghost, text=f"  ↕  {self.path_labels.get(self.drag_source, self.drag_source.name)[:31]}  ",
                     bg=ACCENT, fg=BG, padx=9, pady=7,
                     font=("Segoe UI", 10, "bold")).pack()
        if self.drag_ghost:
            self.drag_ghost.geometry(f"+{event.x_root + 14}+{event.y_root + 14}")

    def _drag_release(self, event):
        path = self.drag_source
        moving = self.is_dragging
        self.drag_source = None
        self.drag_begin = None
        self.is_dragging = False
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        if path is None:
            return
        if moving:
            target = self.root.winfo_containing(event.x_root, event.y_root)
            index = None
            while target is not None:
                if hasattr(target, "foto_slot_index"):
                    index = target.foto_slot_index
                    break
                target = getattr(target, "master", None)
            if index is not None:
                self._reposition(path, index)
        else:
            target = event.widget
            index = None
            while target is not None:
                if hasattr(target, "foto_slot_index"):
                    index = target.foto_slot_index
                    break
                target = getattr(target, "master", None)
            if index is not None and self.selected is not None and self.selected != path:
                self._reposition(self.selected, index)
                return
            self.selected = path
            self.render_library()

    def _options(self):
        format_name = self.output_format.get()
        fmt = "Imagenes" if format_name.startswith("Imágenes") else format_name
        return ExportOptions(
            paper=self.paper.get(), orientation=self.orientation.get(),
            fit=self.fit.get(), dpi=int(self.dpi.get()), fmt=fmt,
            binding=self.binding.get() == "Sí",
            pdf_page_paths=frozenset(self.pdf_origins),
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
        self.preview_index = self.pages.index(self.selected) if self.selected in self.pages else 0
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

    def _preview_move(self, step: int):
        if not self.pages:
            self._close_preview()
            return
        new_index = max(0, min(len(self.pages) - 1, self.preview_index + step))
        if new_index != self.preview_index:
            self.preview_index = new_index
            self._show_preview_page()

    def _show_preview_page(self):
        if self.preview_window is None or not self.preview_window.winfo_exists():
            return
        if not self.pages:
            self._close_preview()
            return
        self.preview_index = min(self.preview_index, len(self.pages) - 1)
        path = self.pages[self.preview_index]
        self.preview_page_text.set(
            f"Página {self.preview_index + 1} de {len(self.pages)}  ·  {self.path_labels.get(path, path.name)}")
        self.preview_prev_btn.configure(state="normal" if self.preview_index > 0 else "disabled")
        self.preview_next_btn.configure(state="normal" if self.preview_index < len(self.pages) - 1 else "disabled")
        try:
            rendered, (w_mm, h_mm), lowres = render_print_image(
                path, self._options(), preview_max_size=(1100, 850),
                page_index=self.preview_index,
            )
            old = self.preview_image
            self.preview_image = rendered
            if old is not None:
                old.close()
            notice = " · Atención: elemento de poca resolución" if lowres else ""
            imported_pdf = path in self.pdf_origins
            bind_note = ((" · Página PDF importada" if imported_pdf else "") +
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
        if opts.fmt != "Imagenes" and dest.resolve() in set(self.pdf_origins.values()):
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
                elif event[0] == "import_done":
                    _, items, detected_paper, mixed_pdf, errors = event
                    self._finish_import(items, detected_paper, mixed_pdf, errors)
                    self.progress["value"] = 0
                    self.percent_text.set("(0 %)")
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
                    self.feedback.set(f"✓ {count} página(s) exportadas. Resultado: {self.output_path.name}")
                    note = (f"\n\nAtención: {warning_count} foto(s) se han ampliado bastante. "
                            "Puede que se vean borrosas al imprimir." if warning_count else "")
                    messagebox.showinfo("Exportación completada",
                                        f"Se han preparado {count} página(s).\n\nGuardado en:\n{result}{note}")
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
