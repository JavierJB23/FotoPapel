"""Miniaturas rápidas de la hoja activa: orientación y encaje reales.

No se abre el original a resolución completa cuando solo se necesita una
miniatura pequeña. El motor de exportación conserva toda la resolución.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageOps

from processor import (ExportOptions, PAPER_SIZES, printable_box,
                       _flatten_rgb, _trim_revelo_like_page_background,
                       _render_inside, _extended_background, paper_background_color)
from photo_edits import apply_edits


def render_photo_thumbnail(path: Path, opts: ExportOptions, *,
                           max_size: tuple[int, int] = (150, 108),
                           page_index: int = 0) -> Image.Image:
    """Hoja de impresión pequeña para una foto o una página PDF.

    Usa una copia previa de 900 px de lado, con las mismas instrucciones de
    edición y el mismo encaje que la exportación. No modifica nunca la fuente.
    """
    with Image.open(path) as raw:
        raw.draft('RGB', (900, 900))
        rotated = ImageOps.exif_transpose(raw)
        preview = _flatten_rgb(rotated)
    if max(preview.size) > 900:
        preview.thumbnail((900, 900), Image.Resampling.LANCZOS)
    try:
        pdf_page = path in opts.pdf_page_paths
        if pdf_page:
            prepared, trimmed = _trim_revelo_like_page_background(preview)
        else:
            prepared, trimmed = preview.copy(), False
        try:
            if path in opts.photo_edits:
                edited = apply_edits(prepared, opts.photo_edits[path])
            else:
                edited = prepared.copy()
        finally:
            prepared.close()
        try:
            w_mm, h_mm = PAPER_SIZES[opts.paper]
            if opts.orientation == 'Horizontal' or (opts.orientation == 'Automática'
                                                     and edited.width > edited.height):
                w_mm, h_mm = h_mm, w_mm
            out_ratio = min(max_size[0]/w_mm, max_size[1]/h_mm)
            out_w, out_h = max(1, round(w_mm*out_ratio)), max(1, round(h_mm*out_ratio))
            box = printable_box((out_w, out_h), (w_mm, h_mm),
                                binding=opts.binding, page_index=page_index)
            if pdf_page and not trimmed and path not in opts.photo_edits:
                whole = ImageOps.contain(edited, (out_w,out_h), Image.Resampling.LANCZOS)
                paper = Image.new('RGB',(out_w,out_h),'white')
                paper.paste(whole,((out_w-whole.width)//2,(out_h-whole.height)//2))
                whole.close()
                return paper
            print_scale=float(opts.photo_edits.get(path,{}).get('print_scale',1.0))
            if abs(print_scale-1)>0.002:
                use_size=(max(8,round((box[2]-box[0])*print_scale)),
                          max(8,round((box[3]-box[1])*print_scale)))
                blurred=(opts.fit=='Ajustar (sin recortar)' and opts.paper_background=='Difuminado')
                paper=(_extended_background(edited,(out_w,out_h)) if blurred or
                       opts.fit=='Ampliar fondo (sin recortar)' else
                       Image.new('RGB',(out_w,out_h),paper_background_color(opts)
                                 if opts.fit=='Ajustar (sin recortar)' else 'white'))
                tile=(ImageOps.contain(edited,use_size,Image.Resampling.LANCZOS) if blurred or
                      opts.fit=='Ampliar fondo (sin recortar)' else
                      _render_inside(edited,use_size,opts.fit,background=paper_background_color(opts)))
                try:
                    from processor import _paste_clipped_to_box
                    x=(box[0]+box[2]-tile.width)//2
                    y=(box[1]+box[3]-tile.height)//2
                    _paste_clipped_to_box(paper,tile,(x,y),box)
                finally:tile.close()
                return paper
            if opts.fit=='Ajustar (sin recortar)' and opts.paper_background=='Difuminado':
                paper=_extended_background(edited,(out_w,out_h))
                photo=ImageOps.contain(edited,(box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
                try:
                    paper.paste(photo,(box[0]+(box[2]-box[0]-photo.width)//2,
                                       box[1]+(box[3]-box[1]-photo.height)//2))
                finally:photo.close()
                return paper
            if opts.fit == 'Ampliar fondo (sin recortar)' and opts.binding:
                paper = _extended_background(edited, (out_w,out_h))
                safe_w, safe_h = box[2]-box[0],box[3]-box[1]
                inside = ImageOps.contain(edited,(safe_w,safe_h),Image.Resampling.LANCZOS)
                try:
                    paper.paste(inside,(box[0]+(safe_w-inside.width)//2,
                                        box[1]+(safe_h-inside.height)//2))
                finally:
                    inside.close()
                return paper
            inner = _render_inside(edited, (box[2]-box[0],box[3]-box[1]),opts.fit,
                                   background=paper_background_color(opts))
            if not opts.binding:
                return inner
            paper=Image.new('RGB',(out_w,out_h), paper_background_color(opts) if opts.fit=='Ajustar (sin recortar)' else 'white')
            paper.paste(inner, box[:2])
            inner.close()
            return paper
        finally:
            edited.close()
    finally:
        preview.close()
