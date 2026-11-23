"""Fondos opcionales por fotografía o para el documento; nunca edita los originales.

La composición se hace sobre las regiones del papel que realmente están detrás
las fotos. Esto evita tapar la fotografía, el texto y otras capas al usar marcas
de agua, incluso con giros o rectángulos superpuestos.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import math
import re
from typing import Callable, Sequence

from PIL import Image, ImageChops, ImageOps

MODES = ('Heredar', 'Color', 'Imagen', 'Difuminado', 'Sin fondo adicional')
FITS = ('Cubrir', 'Ajustar')
PRESETS = {'Blanco': '#FFFFFF', 'Crema': '#F6EBDC',
           'Aguamarina': '#DDF8EF', 'Azul noche': '#0B1928'}


def validate_background_spec(spec: dict | None) -> dict:
    """Copia inmutable por convención, apta para guardar en JSON."""
    if spec is None or spec == {}:
        return {}
    if not isinstance(spec, dict) or set(spec) - {'mode', 'opacity', 'color', 'image', 'fit'}:
        raise ValueError('Configuración de fondo desconocida')
    mode = spec.get('mode', 'Heredar')
    if mode not in MODES:
        raise ValueError('Tipo de fondo desconocido')
    opacity = spec.get('opacity', 100)
    if type(opacity) not in (int, float) or not math.isfinite(opacity) or not 0 <= opacity <= 100:
        raise ValueError('Opacidad fuera de rango (0–100 %)')
    color = spec.get('color', '#FFFFFF')
    if not isinstance(color, str) or re.fullmatch('#[0-9A-Fa-f]{6}', color) is None:
        raise ValueError('Color hexadecimal inválido')
    image = spec.get('image', '')
    if not isinstance(image, str) or len(image) > 2048:
        raise ValueError('Ruta de imagen de fondo inválida')
    fit = spec.get('fit', 'Cubrir')
    if fit not in FITS:
        raise ValueError('Encaje de fondo desconocido')
    if mode == 'Imagen' and not image:
        raise ValueError('Selecciona una imagen de fondo')
    if mode == 'Heredar':
        return {}
    return {'mode': mode, 'opacity': int(round(opacity)),
            'color': color.upper(), 'image': image, 'fit': fit}


def active_backgrounds(paths, opts) -> bool:
    if any(p in opts.special_pages for p in paths):
        return False  # Las portadas mantienen su editor de fondos propio.
    if validate_background_spec(getattr(opts, 'background_global', {})):
        return True
    return any(validate_background_spec(getattr(opts, 'background_overrides', {}).get(p))
               for p in paths)


def _image_background(spec: dict, size: tuple[int, int], photo: Path, opts) -> Image.Image:
    mode = spec['mode']
    if mode == 'Color':
        return Image.new('RGB', size, spec['color'])
    if mode == 'Difuminado':
        from processor import _prepared_photo, _extended_background
        src, _ = _prepared_photo(photo, opts)
        try:
            return _extended_background(src, size)
        finally:
            src.close()
    if mode != 'Imagen':
        raise ValueError('No hay imagen de fondo que generar')
    path = Path(spec['image'])
    if not path.is_file():
        raise ValueError(f'No se encuentra la imagen de fondo: {path.name}')
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        if source.mode != 'RGBA':
            source = source.convert('RGBA')
        else:
            source = source.copy()
    try:
        if spec['fit'] == 'Cubrir':
            resized = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
            base = Image.new('RGBA', size, spec['color'] + 'FF')
            try:
                base.alpha_composite(resized)
                return base.convert('RGB')
            finally:
                resized.close()
                base.close()
        resized = ImageOps.contain(source, size, Image.Resampling.LANCZOS)
        base = Image.new('RGBA', size, spec['color'] + 'FF')
        try:
            base.alpha_composite(resized, ((size[0]-resized.width)//2,
                                           (size[1]-resized.height)//2))
            return base.convert('RGB')
        finally:
            resized.close()
            base.close()
    finally:
        source.close()


def _regions(paths, opts, size, physical, page_index=0):
    """Regiones de la misma plantilla que usa el motor de impresión."""
    from processor import printable_box, _grid_shape
    from advanced_layout import template_rects
    from layout_editor import editable_template_rects, free_default, validate_layout_item
    w,h=size
    w_mm,h_mm=physical
    if len(paths) == 1 and opts.layout_template != 'Diseño libre':
        return {paths[0]: (0,0,w,h)}
    if opts.binding:
        safe = printable_box(size, physical, binding=True, page_index=page_index)
    else:
        mx=max(1,round(w*3/w_mm));my=max(1,round(h*3/h_mm))
        safe=(mx,my,w-mx,h-my)
    x0,y0,x1,y1=safe
    if opts.layout_template=='Diseño libre':
        zw,zh=x1-x0,y1-y0
        result={}
        for idx,path in enumerate(paths):
            spec=validate_layout_item(opts.layout_items.get(path))
            cx,cy,rw,rh=spec.get('rect',free_default(idx,len(paths))['rect'])
            # Un fondo de foto sigue su caja de composición; ampliar la caja
            # para cubrir también el área alcanzada por una fotografía girada.
            angle=math.radians(float(spec.get('angle',0.0)))
            ew=abs(rw*math.cos(angle))+abs(rh*math.sin(angle))
            eh=abs(rh*math.cos(angle))+abs(rw*math.sin(angle))
            result[path]=(round(x0+zw*(cx-ew/2)),round(y0+zh*(cy-eh/2)),
                          round(x0+zw*(cx+ew/2)),round(y0+zh*(cy+eh/2)))
        return result
    template=(opts.layout_template if opts.photos_per_page==3 else 'Cuadrícula')
    gapx=max(1,round(w*3/w_mm));gapy=max(1,round(h*3/h_mm))
    if template !='Cuadrícula' and len(paths)==3:
        rects=editable_template_rects(safe,gapx,gapy,template,opts.layout_items.get(paths[0],{}))
    else:
        rects=template_rects(safe,gapx,gapy,template='Cuadrícula',
                             count=opts.photos_per_page,landscape=w_mm>h_mm)
    return dict(zip(paths,rects))


def _clamp_rect(rect, size):
    x0,y0,x1,y1=rect
    return (max(0,min(size[0],x0)),max(0,min(size[1],y0)),
            max(0,min(size[0],x1)),max(0,min(size[1],y1)))


def compose_backgrounds(paths: Sequence[Path], opts, base_render: Callable,
                        *, page_index: int = 0):
    """Un solo motor para miniaturas, editor, vista previa, PNG/PDF/Word.

    Ejecuta el motor existente con fondos negro/blanco testigo, permitiendo
    calcular matemáticamente la porción visible del *papel* sin adivinar píxeles
    blancos en la fotografía. Las capas nuevas nunca tapan fotos ni textos.
    """
    paths=tuple(paths)
    neutral=replace(opts, background_global={}, background_overrides={})
    original, physical, lowres=base_render(neutral)
    if not active_backgrounds(paths,opts):
        return original,physical,lowres
    if opts.fit != 'Ajustar (sin recortar)':
        # Con relleno / fondo ampliado no existen zonas de papel reemplazables.
        return original,physical,lowres
    bg_global=validate_background_spec(opts.background_global)
    individual={p:validate_background_spec(opts.background_overrides.get(p)) for p in paths}
    if not bg_global and not any(individual.values()):
        return original,physical,lowres
    visible=[spec for spec in [bg_global,*individual.values()] if spec and
             (spec['mode']=='Sin fondo adicional' or spec['opacity']>0)]
    if not visible:
        return original,physical,lowres
    stripped={p:{k:v for k,v in spec.items()
                 if k not in ('background','background_color')}
              for p,spec in neutral.layout_items.items()}
    neutral=replace(neutral,layout_items=stripped)
    black_opts=replace(neutral,paper_background='Personalizado',paper_background_color='#000000')
    white_opts=replace(neutral,paper_background='Personalizado',paper_background_color='#FFFFFF')
    black,_,_=base_render(black_opts)
    white,_,_=base_render(white_opts)
    try:
        if black.size!=original.size or white.size!=original.size:
            raise ValueError('Las capas del fondo no coinciden con el papel')
        # Solo la diferencia es papel: en la foto (y textos) el valor es 0.
        strength=ImageChops.difference(white,black).convert('L')
        try:
            if strength.getbbox() is None:
                return original,physical,lowres
            sheet=original
            legacy=(original.copy() if any(
                x.get('mode')=='Sin fondo adicional' for x in individual.values()) else None)
            def apply(spec,rect,photo,region_mask=None):
                nonlocal sheet
                if not spec:
                    return
                box=_clamp_rect(rect,sheet.size)
                if box[2]<=box[0] or box[3]<=box[1]:
                    return
                w,h=box[2]-box[0],box[3]-box[1]
                if spec['mode']=='Sin fondo adicional':
                    if legacy is None:return
                    patch=legacy.crop(box)
                    try:sheet.paste(patch,box[:2],region_mask)
                    finally:patch.close()
                    return
                if spec['opacity']==0:
                    return
                layer=_image_background(spec,(w,h),photo,neutral)
                black_patch=black.crop(box)
                strength_patch=strength.crop(box)
                mask_rgb=strength_patch.convert('RGB')
                current=sheet.crop(box)
                try:
                    contribution=ImageChops.multiply(mask_rgb,layer)
                    recolored=ImageChops.add(black_patch,contribution)
                    try:
                        mixed=Image.blend(current,recolored,spec['opacity']/100.0)
                        try:sheet.paste(mixed,box[:2],region_mask)
                        finally:mixed.close()
                    finally:contribution.close();recolored.close()
                finally:
                    current.close();mask_rgb.close();strength_patch.close();black_patch.close();layer.close()
            if bg_global:
                apply(bg_global,(0,0,*sheet.size),paths[0])
            if any(individual.values()) and opts.layout_template=='Diseño libre':
                # En libre los fondos no pueden quedar ocultos bajo la propia
                # foto; cada imagen define una zona de página, sin alterar
                # fotos ni textos ya compuestos. El fondo general permanece
                # visible detrás de las zonas sin excepción particular.
                from revelo_background_free import free_background_area
                for p in paths:
                    if not individual[p]:
                        continue
                    region=free_background_area(paths,p,opts,sheet.size,physical,page_index)
                    if region is None:
                        continue
                    box,mask=region
                    try:apply(individual[p],box,p,mask)
                    finally:mask.close()
            elif any(individual.values()):
                regions=_regions(paths,opts,sheet.size,physical,page_index)
                for p in paths:
                    if individual[p]:
                        apply(individual[p],regions[p],p)
            return sheet,physical,lowres
        finally:
            strength.close()
            if "legacy" in locals() and legacy is not None: legacy.close()
    finally:
        black.close();white.close()
