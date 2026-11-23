"""FIX14: las fotos libres mantienen fondo y el menú pide confirmación.

Se prueban efectos reales, sin saltar validaciones ni desactivar pruebas previas.
"""
from dataclasses import dataclass, field
from pathlib import Path
import sys
import types

import pytest
from PIL import Image, ImageDraw

from revelo_background_control import (
    on_choice, cancel_custom_choice, commit_custom_editor, CUSTOM, ALL_IMAGE,
)
from revelo_background_free import _clip_polygon, free_background_area
from revelo_backgrounds import compose_backgrounds


class Var:
    def __init__(self, value):
        self.value = value
    def set(self, value):
        self.value=value
    def get(self):
        return self.value


class Frame:
    def __init__(self):
        self.actions=[]
    def after_idle(self, f):
        self.actions.append(f)
    def run_idle(self):
        while self.actions:
            self.actions.pop(0)()


class FakeApp:
    def __init__(self, initial='Personalizado'):
        self.paper_background=Var(initial)
        self.paper_background_color=Var('#FFFFFF')
        self._background_choice_previous=initial
        self._background_choice_guard=False
        self._background_pending_custom_from=None
        self._restoring_project=False
        self.background_window=None
        self.background_global={'mode':'Imagen', 'image':'e.png','opacity':90}
        self.background_overrides={'foto':{'mode':'Color','color':'#AABBCC','opacity':40}}
        self.root=Frame()
        self.thumbnails={'a':1}
        self.thumbnails_small={'a':1}
        self.sheet_thumbnails={'a':1}
        self.paths=[]
        self.preview_window=None
        self.is_busy=False
        self.synced=0
        self.opened=0
    def _sync_free_background_from_main(self):
        self.synced+=1
    def open_backgrounds(self):
        self.opened+=1


@pytest.mark.parametrize('color',['Blanco','Crema','Aguamarina','Azul noche','Difuminado'])
def test_declining_global_replacement_preserves_individuals(monkeypatch,color):
    import revelo_background_control as control
    app=FakeApp()
    old_overrides=app.background_overrides.copy()
    old_global=app.background_global.copy()
    monkeypatch.setattr(control,'_confirm_override',lambda _app,_choice:False)
    app.paper_background.set(color)
    on_choice(app)
    assert app.paper_background.get()=='Personalizado'
    assert app.background_global==old_global
    assert app.background_overrides==old_overrides
    assert app.synced==0


def test_accept_global_color_removes_overrides(monkeypatch):
    import revelo_background_control as control
    app=FakeApp()
    monkeypatch.setattr(control,'_confirm_override',lambda _app,_choice:True)
    app.paper_background.set('Crema')
    on_choice(app)
    assert app.background_global=={}
    assert app.background_overrides=={}
    assert app.paper_background.get()=='Crema'
    assert app.synced==1
    assert app.sheet_thumbnails=={}


def test_personalized_opens_editor_and_cancel_reverts():
    app=FakeApp('Blanco')
    app.background_global={}
    app.background_overrides={}
    app.paper_background.set('Personalizado')
    on_choice(app)
    app.root.run_idle()
    assert app.opened==1
    assert app.background_overrides=={}
    cancel_custom_choice(app)
    assert app.paper_background.get()=='Blanco'
    assert app._background_pending_custom_from is None


def test_commit_custom_preserves_legacy_base_color():
    app=FakeApp('Azul noche')
    app.background_global={}
    app.background_overrides={}
    overrides={'foto':{'mode':'Color','color':'#FF0000','opacity':20}}
    commit_custom_editor(app,{},overrides)
    assert app.paper_background.get()==CUSTOM
    assert app.paper_background_color.get()=='#0B1928'


def test_general_image_replaces_only_after_confirmation(monkeypatch,tmp_path):
    import revelo_background_control as control
    app=FakeApp('Crema')
    bg=tmp_path/'fondo.png'
    Image.new('RGB',(30,20),'navy').save(bg)
    monkeypatch.setattr(control,'_choose_image',lambda _app:str(bg))
    monkeypatch.setattr(control,'_confirm_override',lambda _app,_choice:False)
    app.paper_background.set(ALL_IMAGE)
    on_choice(app)
    assert app.paper_background.get()=='Crema'
    assert app.background_overrides
    monkeypatch.setattr(control,'_confirm_override',lambda _app,_choice:True)
    app.paper_background.set(ALL_IMAGE)
    on_choice(app)
    assert app.paper_background.get()=='Personalizado'
    assert app.background_global['mode']=='Imagen'
    assert app.background_global['image']==str(bg)
    assert app.background_overrides=={}
    assert app.synced==1


def test_voronoi_zones_cover_free_paper_even_when_photos_fill_rectangles(monkeypatch):
    layout=types.ModuleType('layout_editor')
    layout.validate_layout_item=lambda spec:spec or {}
    layout.free_default=lambda idx,count:{'rect':[.25+idx*.5,.5,.26,.40]}
    processor=types.ModuleType('processor')
    processor.printable_box=lambda *_args,**_kwargs:(15,15,285,185)
    monkeypatch.setitem(sys.modules,'layout_editor',layout)
    monkeypatch.setitem(sys.modules,'processor',processor)
    a=Path('left.png');b=Path('right.png')
    opts=types.SimpleNamespace(binding=False,layout_items={
        a:{'rect':[.25,.5,.22,.25]},b:{'rect':[.75,.5,.22,.25]}})
    left=free_background_area([a,b],a,opts,(300,200),(148,210))
    right=free_background_area([a,b],b,opts,(300,200),(148,210))
    assert left and right
    lbox,lmask=left;rbox,rmask=right
    try:
        assert lbox[0]==0 and lbox[2]>130
        assert rbox[2]==300 and rbox[0]<170
        assert lmask.getpixel((20,20))==255
        assert rmask.getpixel((rbox[2]-rbox[0]-20,20))==255
    finally:lmask.close();rmask.close()


@dataclass(frozen=True)
class FakeOptions:
    paper_background:str='Blanco'
    paper_background_color:str='#FFFFFF'
    background_global:dict=field(default_factory=dict)
    background_overrides:dict=field(default_factory=dict)
    special_pages:dict=field(default_factory=dict)
    layout_template:str='Diseño libre'
    fit:str='Ajustar (sin recortar)'
    layout_items:dict=field(default_factory=dict)
    binding:bool=False


def test_free_layout_multiple_photo_backgrounds_recolor_whole_paper(monkeypatch,tmp_path):
    """Simula un render estable: fotografía encima, papel debajo."""
    layout=types.ModuleType('layout_editor')
    layout.validate_layout_item=lambda spec:spec or {}
    layout.free_default=lambda idx,count:{'rect':[.25+idx*.5,.5,.28,.28]}
    processor=types.ModuleType('processor')
    processor.printable_box=lambda *_args,**_kwargs:(10,10,290,190)
    monkeypatch.setitem(sys.modules,'layout_editor',layout)
    monkeypatch.setitem(sys.modules,'processor',processor)
    a=tmp_path/'a.png';b=tmp_path/'b.png'
    Image.new('RGB',(60,40),(240,40,40)).save(a)
    Image.new('RGB',(60,40),(40,200,40)).save(b)
    wallpaper=tmp_path/'fondo.png'
    Image.new('RGB',(20,20),(23,63,193)).save(wallpaper)
    opts=FakeOptions(
        background_global={'mode':'Imagen','image':str(wallpaper),'opacity':100},
        background_overrides={a:{'mode':'Color','color':'#D0A000','opacity':100}},
        layout_items={a:{'rect':[.25,.5,.28,.28]},b:{'rect':[.75,.5,.28,.28]}})
    def old_render(options):
        colors={'Blanco':'#FFFFFF','Personalizado':options.paper_background_color}
        paper=Image.new('RGB',(300,200),colors[options.paper_background])
        draw=ImageDraw.Draw(paper)
        draw.rectangle((54,80,94,120),fill=(240,40,40))
        draw.rectangle((206,80,246,120),fill=(40,200,40))
        return paper,(148,210),False
    result,_,_=compose_backgrounds((a,b),opts,old_render)
    try:
        assert result.getpixel((10,20))==(208,160,0)
        assert result.getpixel((290,20))==(23,63,193)
        assert result.getpixel((75,100))==(240,40,40)
        assert result.getpixel((225,100))==(40,200,40)
    finally:result.close()


def test_app_menu_provides_image_option_and_valid_custom_mode():
    """Prueba de integración en CI Windows; preserva siete selectores."""
    import tkinter as tk
    from main import ReveloApp
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('Entorno sin escritorio Tk')
    try:
        app=ReveloApp(root)
        assert len(app.settings_controls_row.winfo_children())==7
        assert 'Imagen para todas' in app.paper_background_combo.cget('values')
        assert app._background_choice_previous=='Blanco'
        assert callable(app._background_choice_changed)
        assert app._options().background_overrides=={}
        # «Personalizado» debe abrir REALMENTE un editor, no solo dejar
        # seleccionado un elemento del desplegable sin hacer nada.
        app.paper_background.set('Personalizado')
        root.update()
        assert app.background_window is not None
        assert app.background_window.winfo_exists()
    finally:root.destroy()


def test_free_layout_two_different_photo_wallpapers_visible(monkeypatch,tmp_path):
    """Una imagen de fondo por foto ocupa su área de página aun en libre."""
    layout=types.ModuleType('layout_editor')
    layout.validate_layout_item=lambda spec:spec or {}
    layout.free_default=lambda idx,count:{'rect':[.25+idx*.5,.5,.26,.25]}
    processor=types.ModuleType('processor')
    processor.printable_box=lambda *_args,**_kwargs:(8,8,292,192)
    monkeypatch.setitem(sys.modules,'layout_editor',layout)
    monkeypatch.setitem(sys.modules,'processor',processor)
    a,b=tmp_path/'a.png',tmp_path/'b.png'
    bg_a,bg_b=tmp_path/'wall_a.png',tmp_path/'wall_b.png'
    Image.new('RGB',(30,15),(200,12,65)).save(bg_a)
    Image.new('RGB',(35,20),(22,85,225)).save(bg_b)
    opts=FakeOptions(
        background_overrides={
            a:{'mode':'Imagen','image':str(bg_a),'opacity':100},
            b:{'mode':'Imagen','image':str(bg_b),'opacity':50},
        },
        layout_items={a:{'rect':[.25,.5,.25,.24]},b:{'rect':[.75,.5,.25,.24]}})
    def stable(source):
        col=(255,255,255) if source.paper_background=='Blanco' else (
            (0,0,0) if source.paper_background_color=='#000000' else (255,255,255))
        paper=Image.new('RGB',(300,200),col)
        ImageDraw.Draw(paper).rectangle((65,85,85,110), fill=(10,235,40))
        ImageDraw.Draw(paper).rectangle((210,85,235,110), fill=(230,135,20))
        return paper,(148,210),False
    im,_,_=compose_backgrounds((a,b),opts,stable)
    try:
        assert im.getpixel((20,35))==(200,12,65)
        # Fondo blanco + imagen azul 50 %: conserva el rango interpolado.
        assert im.getpixel((280,35)) in ((138,170,240),(139,170,240))
        assert im.getpixel((73,95))==(10,235,40)
        assert im.getpixel((215,95))==(230,135,20)
    finally:im.close()


def test_real_free_design_preserves_photos_and_shows_two_backgrounds(tmp_path):
    """Integración con el motor verdadero, solo en GitHub/instalación completa."""
    from processor import ExportOptions, render_layout_page
    a=tmp_path/'a.png';b=tmp_path/'b.png'
    Image.new('RGB',(300,180),(210,30,25)).save(a)
    Image.new('RGB',(300,180),(35,175,75)).save(b)
    image_bg=tmp_path/'papel.png'
    Image.new('RGB',(50,80),(45,95,205)).save(image_bg)
    opts=ExportOptions(paper='A5',dpi=90,orientation='Vertical',photos_per_page=2,
        layout_template='Diseño libre',fit='Ajustar (sin recortar)',
        layout_items={a:{'rect':[.26,.5,.22,.19]}, b:{'rect':[.75,.5,.22,.19]}},
        background_global={'mode':'Color','color':'#EFEBD5','opacity':100},
        background_overrides={a:{'mode':'Imagen','image':str(image_bg),'opacity':100}})
    page,_,_=render_layout_page((a,b),opts,preview_max_size=(300,390))
    try:
        assert page.getpixel((5,10))==(45,95,205)
        assert page.getpixel((page.width-5,10))==(239,235,213)
        from collections import Counter
        present=Counter(page.getdata())
        assert present[(210,30,25)]>100
        assert present[(35,175,75)]>100
    finally:page.close()


def test_custom_color_picker_also_requires_confirmation(monkeypatch):
    from tkinter import colorchooser
    import revelo_background_control as control
    app=FakeApp('Personalizado')
    old_overrides=app.background_overrides.copy()
    monkeypatch.setattr(colorchooser,'askcolor',lambda **_kw:((210,100,10),'#D2640A'))
    monkeypatch.setattr(control,'_confirm_override',lambda *_args:False)
    control.choose_custom_color(app)
    assert app.background_overrides==old_overrides
    assert app.paper_background_color.get()=='#FFFFFF'
    monkeypatch.setattr(control,'_confirm_override',lambda *_args:True)
    control.choose_custom_color(app)
    assert app.background_overrides=={}
    assert app.background_global=={}
    assert app.paper_background_color.get()=='#D2640A'
    assert app.paper_background.get()=='Personalizado'
