"""FotoPapel: prepara y ordena fotografías para imprimir sin conocimientos técnicos."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from PIL import Image, ImageTk, ImageOps, ImageDraw

from processor import (
    ExportOptions, PAPER_SIZES, SUPPORTED_EXTENSIONS, export,
    pixel_size, source_dimensions,
)

APP_NAME = "FotoPapel"
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


class FotoPapelApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FotoPapel · Fotos listas para imprimir")
        self.root.geometry("1270x845")
        self.root.minsize(940, 650)
        self.root.configure(bg=BG)
        self.paths: list[Path] = []
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

        self.paper = tk.StringVar(value="A4")
        self.orientation = tk.StringVar(value="Automática")
        self.fit = tk.StringVar(value="Ajustar (sin recortar)")
        self.dpi = tk.StringVar(value="300")
        self.output_format = tk.StringVar(value="PDF")
        self.overview = tk.StringVar(value="A4 · 210 × 297 mm · 2480 × 3508 px a 300 PPP")
        self.feedback = tk.StringVar(value="Carga tus fotos para empezar. Los archivos originales no se modifican.")
        self.count_var = tk.StringVar(value="0 fotos")
        self.page_count_var = tk.StringVar(value="0 páginas")

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
        tk.Label(left, text="F", font=("Segoe UI", 25, "bold"), fg=BG, bg=ACCENT,
                 width=2, height=1).pack(side="left", padx=(0, 14))
        htext = tk.Frame(left, bg=BG)
        htext.pack(side="left")
        self._label(htext, "FotoPapel", size=23, weight="bold").pack(anchor="w")
        self._label(htext, "Tus fotos, al tamaño exacto para imprimir", color=MUTED, size=10).pack(anchor="w")
        self._label(header, "100 % LOCAL  ·  SIN SUBIR FOTOS A INTERNET", color=ACCENT, size=9,
                    weight="bold").pack(side="right")

        setting_outer = tk.Frame(self.root, bg=BG, padx=24)
        setting_outer.pack(fill="x")
        settings = tk.Frame(setting_outer, bg=SURFACE, padx=17, pady=14,
                            highlightbackground=BORDER, highlightthickness=1)
        settings.pack(fill="x")
        row = tk.Frame(settings, bg=SURFACE)
        row.pack(fill="x")
        self._field(row, "TAMAÑO DE IMPRESIÓN", self.paper, list(PAPER_SIZES), width=17, grow=2)
        self._field(row, "ORIENTACIÓN", self.orientation,
                    ["Automática", "Vertical", "Horizontal"], width=16, grow=2)
        self._field(row, "ENCAJE EN EL PAPEL", self.fit,
                    ["Ajustar (sin recortar)", "Rellenar (recortar)"], width=24, grow=3)
        self._field(row, "CALIDAD", self.dpi, ["150", "300", "600"], width=8, grow=1)
        self._field(row, "EXPORTAR COMO", self.output_format,
                    ["PDF", "Word", "Imágenes (mismo formato)"], width=25, grow=3)
        info = tk.Frame(settings, bg=SURFACE)
        info.pack(fill="x", pady=(12, 0))
        self._label(info, "●", color=ACCENT, size=10).pack(side="left")
        self._label(info, "  ", color=MUTED).pack(side="left")
        self._label(info, "", size=10, color=MUTED, textvariable=self.overview).pack(side="left")
        self._label(info, "  ·  Una fotografía por página en Word y PDF", color=MUTED).pack(side="left")
        for var in (self.paper, self.orientation, self.dpi, self.fit, self.output_format):
            var.trace_add("write", self._update_overview)

        content = tk.Frame(self.root, bg=BG, padx=24, pady=16)
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
        self._label(title, "01  FOTOS CARGADAS", size=12, weight="bold").pack(anchor="w")
        self._label(title, "0 fotos", textvariable=self.count_var, size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        buttons = tk.Frame(library_top, bg=SURFACE)
        buttons.pack(side="right")
        self._button(buttons, "+ Añadir fotos", self.add_photos, accent=True, small=True).pack(side="left", padx=(0, 7))
        self._button(buttons, "Vaciar", self.clear, small=True).pack(side="left")
        tk.Frame(left_panel, height=1, bg=BORDER).pack(fill="x")
        self.library_area = ScrollingArea(left_panel)
        self.library_area.pack(fill="both", expand=True, padx=9, pady=9)
        self.library_area.canvas.bind("<Configure>", self._on_library_resize, add="+")
        self.library_placeholder = self._label(
            self.library_area.inner, "Tus fotos aparecerán aquí.\n\nPulsa «Añadir fotos» para elegir una o varias.\nAdmite JPG, PNG, WEBP, TIFF y BMP.",
            color=MUTED, size=12, justify="center",
        )
        self.library_placeholder.pack(pady=115)

        ordering_top = tk.Frame(right_panel, bg=SURFACE, padx=16, pady=14)
        ordering_top.pack(fill="x")
        rt = tk.Frame(ordering_top, bg=SURFACE)
        rt.pack(side="left")
        self._label(rt, "02  ORDEN DE LAS PÁGINAS", size=12, weight="bold").pack(anchor="w")
        self._label(rt, "0 páginas", textvariable=self.page_count_var,
                    size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        self._button(ordering_top, "Orden inicial", self.reset_order, small=True).pack(side="right")
        tk.Frame(right_panel, height=1, bg=BORDER).pack(fill="x")
        hint = tk.Frame(right_panel, bg=ACCENT_DARK, padx=12, pady=9)
        hint.pack(fill="x", padx=12, pady=(12, 2))
        self._label(hint, "Arrastra a un número, usa las flechas o selecciona foto y posición.",
                    size=10, color="#C1F3E5").pack(anchor="w")
        self.order_area = ScrollingArea(right_panel)
        self.order_area.pack(fill="both", expand=True, padx=9, pady=9)
        self._show_empty_order()

        footer = tk.Frame(self.root, bg=BG, padx=25, pady=14)
        footer.pack(fill="x")
        status_area = tk.Frame(footer, bg=BG)
        status_area.pack(side="left", fill="both", expand=True)
        self._label(status_area, "Listo", textvariable=self.feedback,
                    color=MUTED, size=10, anchor="w").pack(fill="x")
        self.progress = ttk.Progressbar(status_area, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(8, 0), padx=(0, 30))
        self.open_btn = self._button(footer, "Abrir resultado", self.open_result, small=True)
        self.open_btn.pack(side="right", padx=(8, 0))
        self.open_btn.configure(state="disabled")
        self.export_btn = self._button(footer, "Exportar fotos   →", self.start_export, accent=True)
        self.export_btn.pack(side="right")

    def _field(self, row, caption, var, choices, *, width=18, grow=1):
        holder = tk.Frame(row, bg=SURFACE)
        holder.pack(side="left", fill="x", expand=True, padx=(0, 13))
        self._label(holder, caption, color=MUTED, size=8, weight="bold").pack(anchor="w", pady=(0, 7))
        combo = ttk.Combobox(holder, values=choices, textvariable=var,
                             width=width, state="readonly", style="Custom.TCombobox")
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
        names = filedialog.askopenfilenames(
            title="Selecciona una o varias fotos", filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if names:
            self.import_paths([Path(f) for f in names])

    def import_paths(self, incoming):
        new_count = 0
        errors = []
        for path in incoming:
            path = Path(path).expanduser().resolve()
            if path in self.paths:
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                errors.append(f"{path.name}: formato no admitido")
                continue
            try:
                dims = source_dimensions(path)
                self._thumbnail(path)
            except (OSError, ValueError, SyntaxError) as e:
                errors.append(f"{path.name}: no se pudo leer ({e})")
                continue
            self.details[path] = dims
            self.paths.append(path)
            self.pages.append(path)
            new_count += 1
        if new_count:
            self.render_library()
            self.render_order()
            self.feedback.set(f"{len(self.paths)} foto(s) listas. Ordénalas si lo necesitas y pulsa Exportar fotos.")
        if errors:
            messagebox.showwarning("Algunas fotos no se han añadido", "\n".join(errors[:10]))

    def remove_photo(self, path: Path):
        if path not in self.paths or self.is_busy:
            return
        self.paths.remove(path)
        self.pages.remove(path)
        self.thumbnails.pop(path, None)
        self.thumbnails_small.pop(path, None)
        self.details.pop(path, None)
        if self.selected == path:
            self.selected = None
        self.render_library()
        self.render_order()
        self.feedback.set(f"Quitada de la lista: {path.name}. El archivo original se conserva.")

    def clear(self):
        if not self.paths:
            return
        if messagebox.askyesno("Vaciar fotos", "¿Quitar todas las fotos de la lista?\nLos originales no se borrarán."):
            self.paths.clear()
            self.pages.clear()
            self.thumbnails.clear()
            self.thumbnails_small.clear()
            self.details.clear()
            self.selected = None
            self.render_library()
            self.render_order()
            self.feedback.set("Lista vacía. Los originales no se han modificado.")

    def reset_order(self):
        if self.paths:
            self.pages = self.paths.copy()
            self.render_order()
            self.feedback.set("Restaurado el orden en que cargaste las fotos.")

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
        self.count_var.set(f"{len(self.paths)} foto{'s' if len(self.paths) != 1 else ''}")
        if not self.paths:
            self._label(self.library_area.inner,
                        "Tus fotos aparecerán aquí.\n\nPulsa «Añadir fotos» para elegir una o varias.\nAdmite JPG, PNG, WEBP, TIFF y BMP.",
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
            name = path.name if len(path.name) <= 28 else path.stem[:20] + "…" + path.suffix
            lbl = self._label(card, name, size=10, weight="bold", bg=SURFACE_2, anchor="w")
            lbl.pack(fill="x", pady=(6, 0))
            w, h = self.details[path]
            meta = self._label(card, f"{w} × {h} px  ·  {path.suffix[1:].upper()}",
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
                    "Aquí aparecerán las posiciones 1, 2, 3…\n\nCada posición será una página de tu PDF o Word.",
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
            short = path.name if len(path.name) <= 35 else path.name[:31] + "…"
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
            self.feedback.set(f"«{path.name}» pasa a la posición {index + 1}.")

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
            tk.Label(self.drag_ghost, text=f"  ↕  {self.drag_source.name[:31]}  ",
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
        )

    def start_export(self):
        if self.is_busy:
            return
        if not self.pages:
            messagebox.showinfo("Faltan fotos", "Añade una o varias fotos antes de exportar.")
            return
        opts = self._options()
        suggested = f"FotoPapel_{opts.paper.replace(' × ', 'x').replace(' ', '')}"
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
        if opts.fmt != "Imagenes" and dest.exists():
            if not messagebox.askyesno("Sobrescribir documento", "Ese archivo ya existe. ¿Quieres sustituirlo?"):
                return
        self.is_busy = True
        self.export_btn.configure(state="disabled", text="Exportando…")
        self.progress["value"] = 0
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
                if event[0] == "progress":
                    _, current, total, name = event
                    self.progress["value"] = round(100 * current / total)
                    self.feedback.set(f"Procesando {current}/{total}: {name}")
                elif event[0] == "success":
                    _, result, warning_count, count = event
                    self.is_busy = False
                    self.export_btn.configure(state="normal", text="Exportar fotos   →")
                    self.progress["value"] = 100
                    self.output_path = Path(result)
                    self.open_btn.configure(state="normal")
                    self.feedback.set(f"✓ {count} foto(s) exportadas. Resultado: {self.output_path.name}")
                    note = (f"\n\nAtención: {warning_count} foto(s) se han ampliado bastante. "
                            "Puede que se vean borrosas al imprimir." if warning_count else "")
                    messagebox.showinfo("Exportación completada",
                                        f"Se han preparado {count} foto(s).\n\nGuardado en:\n{result}{note}")
                elif event[0] == "error":
                    self.is_busy = False
                    self.export_btn.configure(state="normal", text="Exportar fotos   →")
                    self.progress["value"] = 0
                    self.feedback.set("No se pudo completar la exportación.")
                    messagebox.showerror("Error al exportar", event[1])
        except queue.Empty:
            pass
        self.root.after(120, self._poll)

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
    FotoPapelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
