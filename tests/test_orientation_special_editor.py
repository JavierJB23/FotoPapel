"""Regresiones FIX02: portada orientada como el papel activo, no como la miniatura vieja."""
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from main import ReveloApp
from processor import ExportOptions, render_layout_page


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def make_fake_app(tmp_path, existing_size=(600, 840)):
    cover = tmp_path / "cover.png"
    Image.new("RGB", existing_size, "#F6EBDC").save(cover)
    app = ReveloApp.__new__(ReveloApp)
    app.root = object()
    app.is_busy = False
    app.orientation = Variable("Horizontal")
    app.paper = Variable("A4")
    app.binding = Variable("Sí")
    app.special_temp = SimpleNamespace(name=str(tmp_path))
    app.details = {cover: existing_size}
    app.pages = [cover]
    app.paths = [cover]
    app.special_pages = {cover: {"kind": "Portada", "theme": "Crema", "title": "Mi recetario", "subtitle": ""}}
    app.thumbnails = {}
    app.thumbnails_small = {}
    app.path_labels = {}
    app.feedback = Variable("")
    app._thumbnail = lambda path: None
    app.render_library = lambda: None
    app.render_order = lambda: None
    return app, cover


def test_existing_portrait_cover_editor_uses_explicit_horizontal(tmp_path, monkeypatch):
    app, cover = make_fake_app(tmp_path)
    calls = []
    monkeypatch.setattr('main.edit_custom_page', lambda *args, **kwargs: calls.append(kwargs))

    app._custom_page_dialog(cover)
    assert len(calls) == 1
    assert calls[0]['landscape'] is True
    assert calls[0]['paper_dimensions_mm'] == (297, 210)
    assert calls[0]['binding'] is True

    # Guardar tras editar debe regenerar también la miniatura apaisada.
    app._commit_special_page(app.special_pages[cover], cover)
    with Image.open(cover) as im:
        assert im.width > im.height
    opts = ExportOptions(paper='A4', orientation='Horizontal', dpi=100,
                         special_pages=app.special_pages)
    rendered, (w, h), _ = render_layout_page((cover,), opts, preview_max_size=(900, 900))
    try:
        assert (w, h) == (297, 210)
        assert rendered.width > rendered.height
    finally:
        rendered.close()


def test_vertical_selection_overrides_old_landscape_and_auto_preserves_old(tmp_path, monkeypatch):
    app, cover = make_fake_app(tmp_path, existing_size=(840, 600))
    calls = []
    monkeypatch.setattr('main.edit_custom_page', lambda *args, **kwargs: calls.append(kwargs))

    app.orientation.set('Vertical')
    app._custom_page_dialog(cover)
    assert calls[-1]['landscape'] is False
    assert calls[-1]['paper_dimensions_mm'] == (210, 297)
    app._commit_special_page(app.special_pages[cover], cover)
    with Image.open(cover) as im:
        assert im.width < im.height

    app.orientation.set('Automática')
    app._custom_page_dialog(cover)
    assert calls[-1]['landscape'] is False
    assert calls[-1]['paper_dimensions_mm'] == (210, 297)


def test_custom_editor_uses_real_selected_paper_ratio(tmp_path, monkeypatch):
    app, cover = make_fake_app(tmp_path)
    app.paper.set('10 × 15 cm')
    calls = []
    monkeypatch.setattr('main.edit_custom_page', lambda *args, **kwargs: calls.append(kwargs))
    app._custom_page_dialog(cover)
    assert calls[-1]['landscape'] is True
    assert calls[-1]['paper_dimensions_mm'] == (150, 100)
