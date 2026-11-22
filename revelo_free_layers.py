"""Render de capas libres: recortes grandes sin memoria gigante y giros transparentes.

La fotografía fuente sigue intacta. Sólo calculamos la porción de la foto
que realmente cae DENTRO del papel; el color visible fuera de ella pertenece
al fondo real de la hoja. No se generan lienzos intermedios gigantes.
"""
from __future__ import annotations

from math import cos, sin, radians, ceil, floor
from pathlib import Path
from PIL import Image, ImageOps


def editing_alpha(path: Path, edits: dict | None, final_size: tuple[int, int]) -> Image.Image | None:
    """Máscara de huecos transparentes producidos al enderezar la fotografía.

    El motor fotográfico conserva deliberadamente RGB para el resto de modos.
    Aquí reconstruimos en L sólo la geometría, sin alterar los colores de origen.
    """
    if edits:
        from photo_edits import validate_edits
        spec = validate_edits(edits)
    else:
        spec = {'ops': [], 'turns': 0, 'flip_h': False, 'flip_v': False,
                'straighten': 0.0, 'crop': None}
    actions = list(spec.get('ops', []))
    for kind, value in (('turn',spec['turns']), ('flip_h',spec['flip_h']),
                        ('flip_v',spec['flip_v']), ('straighten',spec['straighten'])):
        if value:
            actions.append({'kind':kind,'value':value})
    has_rotation = any(op['kind']=='straighten' and
                       abs(float(op['value']))>0.01 for op in actions)
    with Image.open(path) as original:
        oriented = ImageOps.exif_transpose(original)
        try:
            has_native_alpha=('A' in oriented.getbands() or
                              'transparency' in oriented.info)
            if not has_rotation and not has_native_alpha:
                return None
            if has_native_alpha:
                rgba=oriented.convert('RGBA')
                try:alpha=rgba.getchannel('A')
                finally:rgba.close()
            else:
                alpha = Image.new('L', oriented.size, 255)
        finally:oriented.close()
    try:
        for op in actions:
            kind, value = op['kind'], op['value']
            if kind == 'turn':
                turn=int(value)%4
                new = alpha.transpose({1:Image.Transpose.ROTATE_270,
                     2:Image.Transpose.ROTATE_180,3:Image.Transpose.ROTATE_90}[turn]) if turn else alpha.copy()
            elif kind == 'flip_h':
                new = ImageOps.mirror(alpha)
            elif kind == 'flip_v':
                new = ImageOps.flip(alpha)
            elif kind == 'straighten':
                new = alpha.rotate(-float(value),resample=Image.Resampling.BICUBIC,
                                   expand=True,fillcolor=0)
            elif kind == 'crop':
                w,h=alpha.size;x0,y0,x1,y1=value
                new = alpha.crop((max(0,round(x0*w)),max(0,round(y0*h)),
                                  min(w,max(round(x0*w)+1,round(x1*w))),
                                  min(h,max(round(y0*h)+1,round(y1*h)))))
            else:
                continue
            alpha.close();alpha=new
        if spec.get('crop'):
            w,h=alpha.size;x0,y0,x1,y1=spec['crop']
            new=alpha.crop((max(0,round(x0*w)),max(0,round(y0*h)),
                           min(w,max(round(x0*w)+1,round(x1*w))),
                           min(h,max(round(y0*h)+1,round(y1*h)))))
            alpha.close();alpha=new
        if alpha.size != final_size:
            new=alpha.resize(final_size,Image.Resampling.BILINEAR)
            alpha.close();alpha=new
        return alpha
    except Exception:
        alpha.close()
        raise


def visible_photo_patch(source: Image.Image, alpha: Image.Image | None,
                        paper_box: tuple[int,int,int,int], center: tuple[float,float],
                        fit_size: tuple[float,float], angle: float=0.0, *,
                        stretch: bool=False) -> tuple[Image.Image, tuple[int,int]] | None:
    """Sólo los píxeles visibles de una capa escalada/rotada dentro del papel.

    «fit_size» es la caja virtual sin rotar. La salida está recortada al papel,
    evitando crear una foto 800 % en memoria a resolución de imprenta.
    """
    sw,sh=source.size
    bw,bh=max(1.0,float(fit_size[0])),max(1.0,float(fit_size[1]))
    factor=min(bw/max(1,sw),bh/max(1,sh))
    dw,dh=(bw,bh) if stretch else (max(1.0,sw*factor),max(1.0,sh*factor))
    theta=radians(angle)
    co,si=cos(theta),sin(theta)
    ext_w=abs(dw*co)+abs(dh*si)
    ext_h=abs(dw*si)+abs(dh*co)
    cx,cy=center
    l=max(paper_box[0],floor(cx-ext_w/2)-2)
    t=max(paper_box[1],floor(cy-ext_h/2)-2)
    r=min(paper_box[2],ceil(cx+ext_w/2)+2)
    b=min(paper_box[3],ceil(cy+ext_h/2)+2)
    if r<=l or b<=t:
        return None
    rgba=source.convert('RGBA')
    try:
        if alpha is not None:
            rgba.putalpha(alpha.resize(source.size,Image.Resampling.BILINEAR)
                          if alpha.size!=source.size else alpha)
        sx=sw/dw;sy=sh/dh
        a=co*sx;c=sw/2 + a*(l-cx)+si*sx*(t-cy)
        bxy=si*sx
        d=-si*sy;e=co*sy;f=sh/2 + d*(l-cx)+e*(t-cy)
        patch=rgba.transform((r-l,b-t),Image.Transform.AFFINE,
                             (a,bxy,c,d,e,f),resample=Image.Resampling.BICUBIC,
                             fillcolor=(0,0,0,0))
        return patch,(l,t)
    finally:
        rgba.close()
