"""Una sola fuente de composición para el editor y la salida impresa.

Los controles de la vista son únicamente asas superpuestas sobre una reproducción
reducida de ``processor.render_layout_page``. El fondo, escala, giro y colocación
no tienen implementaciones de dibujo alternativas dentro del editor.
"""
from dataclasses import replace
from pathlib import Path
from photo_edits import validate_edits


def editor_options(opts, paths, template, state, ratios, scales, background, color):
    paths = tuple(paths)
    if not paths:
        raise ValueError('La hoja no contiene fotografías')
    layouts = {p: dict(v) for p, v in opts.layout_items.items()}
    layouts.update({p: dict(state[p]) for p in paths})
    if template == 'Diseño libre':
        # Una ventana antigua puede tener un fondo específico en el primer
        # elemento; la selección actual del usuario manda en la vista previa.
        layouts[paths[0]].update(background=background,
                                 background_color=color)
    else:
        layouts[paths[0]].update(ratios)
    photo_edits = {p: dict(v) for p, v in opts.photo_edits.items()}
    captions = {p: dict(v) for p, v in opts.captions.items()}
    for p in paths:
        ed = validate_edits(photo_edits.get(p))
        ed['print_scale'] = float(scales[p])
        photo_edits[p] = ed
        # Escala antigua de pie de foto absorbida ya en ``scales``; de otro
        # modo sería multiplicada dos veces por el motor de impresión.
        if p in captions and captions[p].get('photo_scale', 1.0) != 1.0:
            captions[p]['photo_scale'] = 1.0
    paper_background = (background if background not in ('Según encaje','Personalizado')
                        else opts.paper_background)
    return replace(opts, layout_template=template, layout_items=layouts,
                   photo_edits=photo_edits, captions=captions,
                   paper_background=paper_background,
                   paper_background_color=color if background=='Personalizado'
                   else opts.paper_background_color)


def render_editor_sheet(paths, opts, template, state, ratios, scales, background,
                        color, size, *, page_index=0):
    from processor import render_layout_page
    current = editor_options(opts, paths, template, state, ratios, scales,
                             background, color)
    return render_layout_page(tuple(paths), current, preview_max_size=size,
                              page_index=page_index)
