"""Capa visual Estudio Editorial de Revelo (Tkinter + Pillow, sin servicios externos).

No cambia los callbacks, el modelo de datos ni el motor de exportación.
Los botones son tk.Button reales para conservar foco, accesibilidad y las pruebas.
Las ventanas auxiliares reciben una imagen panorámica SIN segunda marca Revelo.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from functools import lru_cache
from PIL import Image, ImageTk, ImageDraw

NAVY = '#071625'
BG = '#081928'
SURFACE = '#103044'
SURFACE_2 = '#193A4E'
OUTLINE = '#3F7486'
AQUA = '#4CE8D4'
TEXT = '#F4F8FA'
MUTED = '#B5CBD5'


def _rgb(h):
    return tuple(bytes.fromhex(h.lstrip('#')))


@lru_cache(maxsize=100)
def banner_raster(width: int, height: int, *, primary: bool = False):
    """Fondo fotográfico continuo y oscuro. No contiene textos ni logos."""
    from editorial_art import header_art
    width, height = max(250, int(width)), max(36, int(height))
    base = Image.new('RGB', (width, height), BG)
    # La fotografía original tiene formato panorámico 5:1. Respetar
    # esta proporción evita estirar y pixelar la ilustración en monitores anchos.
    image = header_art(max(490, int(height * 5)), max(98, height)).convert('RGB')
    image = image.resize((int(height * 5), height), Image.Resampling.LANCZOS)
    ix = width - image.width
    mask = Image.new('L', (image.width, height))
    px = mask.load()
    fade = max(80, min(image.width//2, 300))
    for x in range(image.width):
        alpha = int(250 * (x/fade)**1.8) if x < fade else 250
        for y in range(height):
            px[x,y] = max(0, alpha)
    base.paste(image, (ix,0),mask)
    # Sin subrayado ni divisores horizontales bajo la panorámica.
    return base


class PhotoBanner(tk.Frame):
    def __init__(self, parent, *, compact=False, heading=None):
        super().__init__(parent, bg=BG, height=78 if compact and heading else 62 if compact else 97)
        self.pack_propagate(False)
        self._image=None
        self.bg_label=tk.Label(self,bg=BG,borderwidth=0)
        self.bg_label.place(relwidth=1,relheight=1)
        self.heading=heading
        if heading:
            # Una sola cabecera textual, DENTRO de la fotografía panorámica.
            self.heading_label=tk.Label(self,text=heading,bg=BG,fg=TEXT,
                              font=('Georgia',20,'bold'),anchor='w',bd=0)
            self.heading_label.place(x=23,rely=.52,anchor='w')
        self.bind('<Configure>',self._draw,add='+')
        self._prev_size=(0,0)
    def _draw(self,e):
        w,h=max(250,e.width),max(40,e.height)
        if (w,h)==self._prev_size:return
        self._prev_size=(w,h)
        self._image=ImageTk.PhotoImage(banner_raster(w,h))
        self.bg_label.configure(image=self._image)


# Título único de cada herramienta, integrado en el encabezado fotográfico.
# En particular NO mostrar un segundo «Revelo» ni repetir el rótulo abajo.
EDITORIAL_HEADINGS = {
    'Texto y pie de foto': 'Texto y pie de foto',
    'Posición personalizada del texto': 'Posición personalizada del texto',
    'Editar fotografía': 'Editar fotografía',
    'Personalizar portada o separador': 'Personalizar página',
    'Añadir página': 'Crear página',
    'Editar página': 'Editar página',
    'Numeración de páginas': 'Numeración de páginas',
    'Previsualización de impresión': 'Vista previa de impresión',
    'Importar desde móvil': 'Importar desde móvil',
    'Diseño libre': 'Composición libre',
    'Tamaño de fotos': 'Tamaño de fotografías',
}

# Solo frases secundarias de cabeceras; no se eliminan mensajes ni instrucciones
# presentes dentro de los editores, para conservar la ayuda importante.
HEADLINE_NOTES = (
    'Texto transparente · Ajusta cada elemento a tu gusto.',
    'Cambios reversibles · Los originales no se modifican',
    'Elige un fondo, activa los textos que quieras',
    'Elige un diseño o personaliza una foto',
    'Comprueba cada página. No se exportará nada',
    'Se aplicará a previsualización, PDF',
    'Arrastra la foto para moverla · Tira de esquinas',
    'Haz clic en una fotografía para seleccionarla. Usa la barra',
    'Selecciona el texto que deseas mover. Las líneas',
)


def _normalize_heading(value):
    return ' '.join(str(value).split()).casefold()


def _integrate_existing_headings(window, heading):
    """Eliminar la fila redundante tras trasladar su texto al banner.

    Las llamadas antiguas mantienen intactos sus argumentos, los callbacks y
    las referencias al modelo: únicamente se retiran widgets ornamentales.
    """
    to_remove=[]
    requested=_normalize_heading(heading)
    subtitles=[]
    def visit(node, depth=0):
        if depth>7:return
        for widget in node.winfo_children():
            if isinstance(widget,tk.Label):
                try: content=widget.cget('text').strip()
                except tk.TclError:content=''
                norm=_normalize_heading(content)
                if norm==requested:
                    to_remove.append(widget)
                elif depth<=4 and any(content.startswith(note) for note in HEADLINE_NOTES):
                    subtitles.append(widget)
            elif isinstance(widget,(tk.Frame,ttk.Frame)):
                visit(widget, depth+1)
    visit(window)
    for w in to_remove+subtitles:
        parent=w.master
        if w.winfo_exists():w.destroy()
        # Si su contenedor era exclusivamente decorativo, eliminarlo también.
        if parent is not window and isinstance(parent,tk.Frame):
            try:
                if not parent.winfo_children() and parent.winfo_manager()=='pack':
                    parent.destroy()
            except tk.TclError:pass
    # Cabeceras de algunos editores tenían además un icono decorativo.
    # Tras mover el título al banner ya no necesitan reservar una fila vacía.
    for top in list(window.winfo_children()):
        if not isinstance(top,tk.Frame):continue
        try:
            remaining=top.winfo_children()
            if len(remaining)==1 and isinstance(remaining[0],tk.Label) and not remaining[0].cget('text').strip():
                top.destroy()
        except tk.TclError:pass
    # Los grandes editores ganan la altura completa que ocupaban las dos filas.
    for widget in window.winfo_children():
        if not isinstance(widget,tk.Frame):continue
        try:
            if widget.cget('pady') and int(widget.cget('pady'))>=13:
                widget.configure(pady=min(8,int(widget.cget('pady'))))
        except (tk.TclError,ValueError):pass
    return len(to_remove)


def add_secondary_banner(window, *, compact=True, before=None):
    """La fotografía Y el título forman UNA sola cabecera.

    Inserción compatible con las ventanas existentes creadas por pack.
    """
    if getattr(window, '_editorial_banner', None) is not None:
        return window._editorial_banner
    name=window.title().split(' · ',1)[-1]
    heading=EDITORIAL_HEADINGS.get(name,name)
    # El encabezado es la nueva referencia visual de los títulos.
    _integrate_existing_headings(window,heading)
    banner=PhotoBanner(window,compact=compact,heading=heading)
    if before is None:
        siblings=[c for c in window.winfo_children() if c is not banner and c.winfo_manager()=='pack']
        before=siblings[0] if siblings else None
    if before is not None:banner.pack(fill='x',before=before)
    else:banner.pack(fill='x')
    window._editorial_banner=banner
    return banner


@lru_cache(maxsize=400)
def button_art(width, height, *, accent=False, hover=False, disabled=False):
    """Fondo suave con esquinas redondas y contorno tipo Estudio Editorial."""
    w,h=int(width),int(height)
    s=3
    W,H=w*s,h*s
    im=Image.new('RGBA',(W,H),(0,0,0,0))
    draw=ImageDraw.Draw(im)
    if disabled:
        hi='#203244';lo='#1A2B38';stroke='#334B5A'
    elif accent:
        hi='#74F5E2' if hover else '#53F0DC'
        lo='#20C9B3' if hover else '#1BC9B4'
        stroke='#9FFCF0' if hover else '#3EE7D0'
    else:
        hi='#274E63' if hover else '#1B4054'
        lo='#1A3548' if hover else '#102D42'
        stroke='#7AB3C3' if hover else '#4F7F91'
    radius=min(H//3,12*s)
    draw.rounded_rectangle((1*s,1*s,W-2*s,H-2*s),radius=radius,fill=lo,outline=stroke,width=1*s)
    # Tira superior de luz suave: no ocupa texto.
    if not disabled:
        draw.rounded_rectangle((3*s,3*s,W-4*s,min(H//2,H-4*s)),radius=max(2,radius-2*s),fill=hi)
        draw.rectangle((3*s,min(H//2,H-4*s)-radius, W-4*s,H//2+2*s),fill=hi)
    return im.resize((w,h),Image.Resampling.LANCZOS)


def style_button(button: tk.Button, *, accent=None):
    """Transforma un tk.Button existente en botón redondeado SIN cambiar su clase.

    La geometría se determina por el texto actual; el cambio de texto en caliente
    actualiza los assets al pasar el ratón, sin interferir con sus comandos.
    """
    if not isinstance(button,tk.Button):return button
    if getattr(button, '_editorial_skinned', False):return button
    try:
        text=button.cget('text')
        fg=button.cget('fg').lower()
        bg=button.cget('bg').lower()
    except tk.TclError:return button
    accent=bool(accent) if accent is not None else bg in ('#4cd9b5','#53f0dc','#4ce8d4','#32dfc6')
    # Longitudes calculadas con Tk, sin necesidad de tipografías privadas.
    try:
        measured=button.tk.call('font','measure',button.cget('font'),text)
        measured=int(measured)
    except tk.TclError:
        measured=len(text)*8
    width=max(31,min(290,measured+30))
    height=39 if ('Exportar fotos' in text or 'Guardar' in text) else (32 if measured<160 else 36)
    if text in ('×','↑','↓','…'):width=31;height=29
    try:
        imgs=[ImageTk.PhotoImage(button_art(width,height,accent=accent,hover=hover,disabled=disabled),master=button)
              for hover,disabled in ((False,False),(True,False),(False,True))]
        button._editorial_assets=imgs
        button._editorial_accent=accent
        button._editorial_text=text
        parent_bg=button.master.cget('bg')
        button.configure(image=imgs[0],compound='center',bg=parent_bg,
                         activebackground=parent_bg,foreground=BG if accent else TEXT,
                         activeforeground=BG if accent else TEXT,
                         bd=0,relief='flat',highlightthickness=0,padx=0,pady=0,
                         cursor='hand2')
    except tk.TclError:return button
    button._editorial_skinned=True
    def refresh(event=None, hover=False):
        if not button.winfo_exists():return
        try:
            if button.cget('text')!=button._editorial_text:
                button._editorial_skinned=False
                style_button(button,accent=accent)
                return
            idx=2 if str(button.cget('state'))=='disabled' else 1 if hover else 0
            button.configure(image=button._editorial_assets[idx])
        except tk.TclError:pass
    button.bind('<Enter>', lambda e:refresh(e,True),add='+')
    button.bind('<Leave>', lambda e:refresh(e,False),add='+')
    return button


def skin_tree(parent, *, root=False):
    """Estilo común de ventanas antiguas sin reescribir su lógica."""
    if not parent.winfo_exists():return
    try:
        widgets=parent.winfo_children()
    except tk.TclError:return
    for widget in widgets:
        if isinstance(widget,tk.Button):
            style_button(widget)
        elif isinstance(widget,ttk.Combobox):
            try:
                sty=widget.cget('style')
                if not sty or sty in ('TCombobox','Custom.TCombobox'):
                    widget.configure(style='Editorial.TCombobox')
            except tk.TclError:pass
        elif isinstance(widget,(tk.Entry,tk.Text,tk.Spinbox)):
            try:
                # No alterar los fondos de las cajas de texto editoriales.
                widget.configure(relief='flat',bd=0,highlightthickness=1,
                                 highlightbackground='#46778B',highlightcolor=AQUA,
                                 insertbackground=AQUA)
            except tk.TclError:pass
        elif isinstance(widget,tk.Label):
            # Solo títulos visibles: NUNCA las etiquetas de los siete selectores,
            # que necesitan Segoe UI pequeña para caber en una sola fila.
            try:
                label=widget.cget('text')
                if label in ('TEXTO Y PIE DE FOTO', 'EDITAR FOTOGRAFÍA',
                             'COMPOSICIÓN LIBRE', 'PERSONALIZAR PÁGINA',
                             'VISTA PREVIA DE IMPRESIÓN',
                             'VISTA PREVIA DE LA HOJA · EN DIRECTO'):
                    widget.configure(font=('Georgia',17,'bold'))
            except tk.TclError:pass
        skin_tree(widget)


def apply_window_skin(window, *, banner=True, compact=True):
    """Ajustes comunes para todos los editores auxiliares y mensajes."""
    window.configure(bg=BG)
    setup_combo_style(window.winfo_toplevel())
    style=ttk.Style(window)
    style.configure('Editorial.TCombobox',fieldbackground=SURFACE_2,
                    background=SURFACE_2,foreground=TEXT,
                    arrowcolor=AQUA,bordercolor=OUTLINE,
                    padding=6,borderwidth=1)
    style.map('Editorial.TCombobox',
              fieldbackground=[('readonly',SURFACE_2),('disabled','#172637')],
              foreground=[('readonly',TEXT),('disabled','#718693')],
              selectbackground=[('readonly',SURFACE_2)],
              selectforeground=[('readonly',TEXT)])
    if banner:add_secondary_banner(window,compact=compact)
    skin_tree(window)
    return window


def style_main_window(app):
    """Aplicar al inicio y después de redibujos de tarjetas de la biblioteca."""
    skin_tree(app.root)


@lru_cache(maxsize=320)
def rounded_panel_art(width,height,fill=SURFACE,stroke=OUTLINE, radius=16):
    w,h=max(12,int(width)),max(12,int(height))
    im=Image.new('RGB',(w,h),BG)
    d=ImageDraw.Draw(im)
    rad=min(radius,w//3,h//3)
    # Pequeña iluminación editorial superior sin volver opacas las esquinas.
    d.rounded_rectangle((0,0,w-1,h-1),radius=rad,
                        fill=fill,outline=stroke,width=1)
    if h>24:
        d.arc((2,1,w-3,max(16,min(36,h//5))),180,360,fill='#477B8C',width=1)
    return im


class RoundedCard(tk.Frame):
    """Superficie decorativa redondeada; el contenido conserva Tk nativo.

    No hace uso de canvas.create_window para los controles: los callbacks y
    las pruebas de geometría siguen funcionando como antes.
    """
    def __init__(self,parent,*,fill=SURFACE,outline=OUTLINE,pad=2,**kwargs):
        super().__init__(parent,bg=fill,padx=pad,pady=pad,**kwargs)
        self._card_fill=fill
        self._card_outline=outline
        self._card_image=None
        self._card_label=tk.Label(self,bg=fill,bd=0)
        self._card_label.place(x=0,y=0,relwidth=1,relheight=1)
        self._card_prev=(0,0)
        self.bind('<Configure>',self._redraw,add='+')
    def _redraw(self,evt):
        wh=(evt.width,evt.height)
        if wh==self._card_prev or min(wh)<16:return
        self._card_prev=wh
        self._card_image=ImageTk.PhotoImage(rounded_panel_art(*wh,self._card_fill,self._card_outline),master=self)
        self._card_label.configure(image=self._card_image)


def icon_bitmap(kind, size=24):
    s=3;w=h=size*s
    im=Image.new('RGBA',(w,h),(0,0,0,0))
    d=ImageDraw.Draw(im)
    q=lambda x:int(x*s)
    line={'fill':AQUA,'width':q(1.7),'joint':'curve'}
    def L(points):d.line([tuple(q(t) for t in p) for p in points],**line)
    if kind=='pictures':
        d.rounded_rectangle((q(2),q(4),q(size-2),q(size-3)),radius=q(2),outline=AQUA,width=q(2))
        d.ellipse((q(5),q(7),q(9),q(11)),outline=AQUA,width=q(1.5))
        L([(4,size-6),(10,size-12),(14,size-9),(18,size-15),(size-4,size-7)])
    elif kind=='layers':
        L([(2,size*.43),(size/2,3),(size-2,size*.43),(size/2,size-4),(2,size*.43)])
        L([(2,size*.62),(size/2,size-1),(size-2,size*.62)])
        L([(2,size*.80),(size/2,size+1),(size-2,size*.80)])
    elif kind=='print':
        d.rounded_rectangle((q(2),q(7),q(size-2),q(size-7)),radius=q(2),outline=AQUA,width=q(2))
        d.rectangle((q(6),q(2),q(size-6),q(9)),outline=AQUA,width=q(2))
        d.rectangle((q(6),q(size-10),q(size-6),q(size-3)),outline=AQUA,width=q(2))
    elif kind=='text':
        d.rounded_rectangle((q(2),q(2),q(size-2),q(size-2)),radius=q(3),outline=AQUA,width=q(2))
        L([(6,7),(size-6,7)]);L([(size/2,7),(size/2,size-5)])
    else:
        d.ellipse((q(2),q(2),q(size-2),q(size-2)),outline=AQUA,width=q(2))
    return im.resize((size,size),Image.Resampling.LANCZOS)


def icon_label(parent,kind,size=25):
    label=tk.Label(parent,bg=parent.cget('bg'),bd=0)
    label._icon_image=ImageTk.PhotoImage(icon_bitmap(kind,size),master=label)
    label.configure(image=label._icon_image)
    return label


def _combobox_asset(width=20,height=29,*,arrow=False,disabled=False):
    """Flecha sin falso subrayado en todos los combobox de Revelo."""
    w,h=width,height
    im=Image.new('RGBA',(w*3,h*3),(0,0,0,0))
    d=ImageDraw.Draw(im)
    bg='#152637' if disabled else '#193A4E'
    outline='#345567' if disabled else '#6C9DB0'
    if arrow:
        # Antes se dibujaba un segundo rectángulo redondeado en la flecha.
        # El borde inferior superpuesto parecía una barra o un subrayado.
        d.rectangle((0,0,w*3,h*3),fill=bg)
        cy=h*3//2
        d.line([(w*3//2-13,cy-6),(w*3//2,cy+7),(w*3//2+13,cy-6)],
               fill='#738897' if disabled else AQUA,width=5,joint='curve')
    else:
        # Los extremos de un campo de 20 px son estirados por ttk; dibujar un
        # contorno inferior crea dos puntos sueltos bajo la zona de flecha.
        d.rounded_rectangle((3,3,w*3-4,h*3-4),radius=14,fill=bg)
        d.line((8,3,w*3-8,3),fill=outline,width=2)
        d.line((3,10,3,h*3-12),fill=outline,width=2)
    return im.resize((w,h),Image.Resampling.LANCZOS)


def setup_combo_style(root):
    """Combobox redondeados, sin cambiar ttk.Combobox ni su comportamiento."""
    if getattr(root,'_editorial_combo_ready',False):return
    try:
        style=ttk.Style(root)
        photos=[ImageTk.PhotoImage(_combobox_asset(20,29),master=root),
                ImageTk.PhotoImage(_combobox_asset(20,29,disabled=True),master=root),
                ImageTk.PhotoImage(_combobox_asset(20,29,arrow=True),master=root),
                ImageTk.PhotoImage(_combobox_asset(20,29,arrow=True,disabled=True),master=root)]
        # Elementos visuales exclusivos de Revelo; no sustituyen los del sistema.
        style.element_create('Revelo.roundfield','image',photos[0],
                             ('disabled',photos[1]),border=(5,5,5,5),sticky='nswe')
        style.element_create('Revelo.downarrow','image',photos[2],
                             ('disabled',photos[3]),sticky='ns')
        layout=[('Revelo.downarrow',{'side':'right','sticky':'ns'}),
                ('Revelo.roundfield',{'sticky':'nswe','children':[
                    ('Combobox.padding',{'sticky':'nswe','children':[
                        ('Combobox.textarea',{'sticky':'nswe'})]})]})]
        for name in ('Editorial.TCombobox','Custom.TCombobox','Compact.TCombobox'):
            style.layout(name,layout)
            style.configure(name,fieldbackground=SURFACE_2,background=SURFACE_2,
                            foreground=TEXT,arrowcolor=AQUA,selectforeground=TEXT,
                            selectbackground=SURFACE_2,padding=(3,3,1,3),borderwidth=0)
            style.map(name,
                    fieldbackground=[('disabled','#152637'),('readonly',SURFACE_2)],
                    foreground=[('disabled','#718693'),('readonly',TEXT)],
                    selectbackground=[('readonly',SURFACE_2)],
                    selectforeground=[('readonly',TEXT)])
        root._editorial_combo_photos=photos
        root._editorial_combo_ready=True
    except tk.TclError:
        # Un Tk muy antiguo puede carecer de las extensiones de imagen de ttk.
        # En ese caso se mantiene el estilo clam anterior sin afectar la app.
        return
