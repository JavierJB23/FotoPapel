"""Regresiones FIX02: navegación libre y contraste de muestras claras.

El único botón nuevo dentro del editor libre guarda antes de avanzar o
retroceder; «Cancelar» conserva exactamente su antigua semántica.
"""
from pathlib import Path
import tkinter as tk
import pytest
from PIL import Image


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip('Sin escritorio Tk')


def _walk(widget):
    yield widget
    for item in widget.winfo_children():
        yield from _walk(item)


def _button(widget, label):
    found=[w for w in _walk(widget) if isinstance(w, tk.Button)
           and str(w.cget('text'))==label]
    assert len(found)==1, (label, [str(w.cget('text')) for w in _walk(widget)
                            if isinstance(w, tk.Button)])
    return found[0]


def _photos(tmp_path, n):
    paths=[]
    for i in range(n):
        p=tmp_path/f'foto{i+1}.png'
        Image.new('RGB',(280,170),(30+i*40,90+i*13,100)).save(p)
        paths.append(p)
    return paths


def test_chip_contraste_sobre_color_blanco_y_oscuro():
    from revelo_background_ui import _contrast_fg
    assert _contrast_fg('#FFFFFF')=='#10202D'
    assert _contrast_fg('#F6EBDC')=='#10202D'
    assert _contrast_fg('#FFF7EA')=='#10202D'
    assert _contrast_fg('#081928')=='#FFFFFF'
    assert _contrast_fg('#000000')=='#FFFFFF'


def test_editor_libre_guarda_antes_de_navegar_y_no_habilita_fuera_de_rango(tmp_path):
    from layout_editor import edit_sheet
    from processor import ExportOptions
    root=_root()
    dialog=None
    try:
        paths=_photos(tmp_path,2)
        saved=[]; navigations=[]; shared=[]; sequence=[]
        def on_save(layout):
            saved.append(layout);sequence.append("guardar")
        def on_navigate(direction, geometry):
            navigations.append(direction);sequence.append("navegar")
            assert "x" in geometry
        opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',
                           photos_per_page=2,layout_template='Diseño libre')
        dialog=edit_sheet(root,paths,'Diseño libre',{},opts,on_save,
                          on_shared_save=lambda *args:shared.append(args),
                          on_navigate=on_navigate,has_previous=True,has_next=True)
        root.update()
        assert _button(dialog,'Anterior').cget('state')=='normal'
        assert _button(dialog,'Siguiente').cget('state')=='normal'
        _button(dialog,'Siguiente').invoke()
        root.update()
        assert navigations==[1]
        assert sequence==["guardar", "navegar"]
        assert len(saved)==1 and set(saved[0])==set(paths)
        assert len(shared)==1
        assert not dialog.winfo_exists()
    finally:
        if dialog is not None and dialog.winfo_exists(): dialog.destroy()
        root.destroy()


def test_editor_libre_cancelar_no_guarda_ni_navega(tmp_path):
    from layout_editor import edit_sheet
    from processor import ExportOptions
    root=_root();dialog=None
    try:
        photos=_photos(tmp_path,1)
        saved=[];navigations=[]
        dialog=edit_sheet(root,photos,'Diseño libre',{},
                          ExportOptions(paper='A5',dpi=100,photos_per_page=1,
                                        layout_template='Diseño libre'),
                          saved.append,on_navigate=navigations.append,
                          has_previous=False,has_next=False)
        root.update()
        assert _button(dialog,'Anterior').cget('state')=='disabled'
        assert _button(dialog,'Siguiente').cget('state')=='disabled'
        _button(dialog,'Cancelar').invoke();root.update()
        assert not saved and not navigations
    finally:
        if dialog is not None and dialog.winfo_exists():dialog.destroy()
        root.destroy()


def test_app_cambia_de_grupo_y_respeta_limites(monkeypatch,tmp_path):
    import main
    from processor import source_dimensions
    root=_root()
    try:
        app=main.ReveloApp(root)
        paths=_photos(tmp_path,5)
        app.paths=list(paths)
        app.pages=list(paths)
        app.path_labels={p:p.name for p in paths}
        app.details={p:source_dimensions(p) for p in paths}
        # Se prueba el controlador, no el coste de dibujar la biblioteca.
        monkeypatch.setattr(app,'render_order',lambda:None)
        monkeypatch.setattr(app,'render_library',lambda:None)
        app.per_sheet.set('2')
        app.layout_template.set('Diseño libre')
        visits=[]
        def fake_editor(parent, group, template, initial, opts, on_save, **kw):
            visits.append((list(group),kw))
        monkeypatch.setattr(main,'edit_sheet',fake_editor)
        app.edit_page_layout()
        assert visits[-1][0]==paths[:2]
        assert visits[-1][1]['has_previous'] is False
        assert visits[-1][1]['has_next'] is True
        visits[-1][1]['on_navigate'](1,'910x620+45+77')
        root.update()
        assert visits[-1][0]==paths[2:4]
        assert visits[-1][1]['editor_geometry']=='910x620+45+77'
        assert visits[-1][1]['has_previous'] is True
        assert visits[-1][1]['has_next'] is True
        visits[-1][1]['on_navigate'](1,'910x620+45+77')
        root.update()
        assert visits[-1][0]==paths[4:]
        assert visits[-1][1]['has_previous'] is True
        assert visits[-1][1]['has_next'] is False
        visits[-1][1]['on_navigate'](-1,'910x620+45+77')
        root.update()
        assert visits[-1][0]==paths[2:4]
        assert app.order_selected==paths[2]
    finally:
        root.destroy()
