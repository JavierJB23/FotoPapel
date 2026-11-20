"""Presentación estética de libro abierto para Revelo.

Se usa únicamente en la previsualización, nunca altera páginas exportadas.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

DESK = (19, 30, 42)


def _gradient_background(size: tuple[int, int]) -> Image.Image:
    w, h = size
    # Poca memoria: un gradiente de 1 píxel de ancho escalado al lienzo.
    stripe = Image.new('RGB', (1, h))
    for y in range(h):
        t = abs(y / max(h - 1, 1) - .46) * 1.35
        stripe.putpixel((0, y), tuple(max(0, round(c - t * 22)) for c in (37, 53, 65)))
    result = stripe.resize(size, Image.Resampling.NEAREST)
    stripe.close()
    return result


def _paste_shadow(target: Image.Image, rect: tuple[int, int, int, int], blur: int, alpha: int) -> None:
    x0,y0,x1,y1 = rect
    mask = Image.new('L', target.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((x0+8,y0+12,x1+8,y1+12), radius=10, fill=alpha)
    smooth = mask.filter(ImageFilter.GaussianBlur(blur))
    shade = Image.new('RGB', target.size, (0, 0, 0))
    target.paste(shade, (0, 0), smooth)
    shade.close();smooth.close();mask.close()


def _paper_shade(page: Image.Image, *, side: str, size: int = 14) -> Image.Image:
    """Pequeña curvatura del papel junto al lomo, sin ocultar contenido."""
    result=page.convert('RGB').copy()
    w,h=result.size
    layer=Image.new('RGBA',(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    edge=min(size,w//9)
    for i in range(edge):
        opacity=int(54 * ((edge-i)/max(edge,1))**1.5)
        x=(i if side=='right' else w-i-1)
        d.line((x,0,x,h),fill=(7,14,18,opacity))
    result=Image.alpha_composite(result.convert('RGBA'),layer).convert('RGB')
    layer.close()
    return result


def render_book(pages: tuple[Image.Image | None, Image.Image | None],
                *, cover: bool = False) -> Image.Image:
    """Dibuja un álbum con lomo, páginas y sombras. No inventa página izquierda.

    Primera página (portada) siempre aparece a la derecha. El área vacía a
    su izquierda es la superficie de apoyo, no otra página simulada.
    """
    if len(pages) != 2 or all(p is None for p in pages):
        raise ValueError('La vista de libro necesita al menos una hoja')
    active=[p for p in pages if p is not None]
    max_w=max(p.width for p in active)
    max_h=max(p.height for p in active)
    # Reservamos espacio para la encuadernación y las sombras, sin forzar que
    # imágenes con diferentes proporciones tengan una geometría inventada.
    slot_w=max_w
    slot_h=max_h
    padding=max(24, min(slot_w,slot_h)//18)
    spine=max(10,slot_w//46)
    gap=0 if not cover else 9
    width=slot_w*2+spine+padding*2+gap
    height=slot_h+padding*2
    result=_gradient_background((width,height))
    left_x=padding
    right_x=padding+slot_w+spine+gap
    top=padding
    d=ImageDraw.Draw(result)
    if cover:
        # Portada como una cubierta cerrada a la derecha: la izquierda queda
        # vacía, sin dibujar un falso folio crema.
        x,y=right_x,top
        page=pages[1] if pages[1] is not None else pages[0]
        _paste_shadow(result,(x-10,y-4,x+slot_w+10,y+slot_h+7),18,125)
        d=ImageDraw.Draw(result)
        for offset,color in ((10,(91,108,113)),(7,(193,199,192)),(4,(218,221,216))):
            d.rounded_rectangle((x+offset,y+offset//2,x+slot_w+offset,y+slot_h+offset//2),
                                 radius=4,fill=color)
        scaled=ImageOps_contain(page,(slot_w,slot_h))
        try:
            result.paste(scaled,(x+(slot_w-scaled.width)//2,y+(slot_h-scaled.height)//2))
        finally:
            scaled.close()
        d=ImageDraw.Draw(result)
        d.rectangle((x-7,y,x-1,y+slot_h),fill=(8,17,28))
        d.line((x+1,y+2,x+1,y+slot_h-2), fill=(255,255,255),width=2)
        # Color aguamarina de Revelo como discreto detalle del canto.
        d.line((x+slot_w-2,y+3,x+slot_w-2,y+slot_h-3),fill=(62,165,147),width=2)
    else:
        for side,page in enumerate(pages):
            if page is None:
                continue
            x=left_x if side==0 else right_x
            _paste_shadow(result,(x-3,top-2,x+slot_w+4,top+slot_h+7),16,110)
            d=ImageDraw.Draw(result)
            # Cantos de papel en el extremo exterior, ligeramente escalonados.
            for layer in range(4,0,-1):
                xoff=-layer if side==0 else layer
                d.rectangle((x+xoff,top+layer//2,x+slot_w+xoff,top+slot_h+layer//2),
                            fill=(207+layer*5,206+layer*5,194+layer*4))
            scaled=ImageOps_contain(page,(slot_w,slot_h))
            try:
                shade=_paper_shade(scaled,side='left' if side==0 else 'right')
                try:
                    result.paste(shade,(x+(slot_w-shade.width)//2,top+(slot_h-shade.height)//2))
                finally:
                    shade.close()
            finally:
                scaled.close()
        # Pliegue realista central: sombra estrecha, ligero brillo y doble
        # página que se curva suavemente hacia el lomo.
        middle=padding+slot_w+spine//2
        overlay=Image.new('RGBA',result.size,(0,0,0,0))
        dob=ImageDraw.Draw(overlay)
        for dx in range(-spine//2-8,spine//2+9):
            strength=max(0,1-abs(dx)/(spine//2+9))
            if dx<=0:
                a=int(112*strength)
                col=(2,10,16,a)
            else:
                a=int(102*strength)
                col=(3,11,18,a)
            dob.line((middle+dx,top,middle+dx,top+slot_h),fill=col)
        dob.line((middle+spine//2+7,top+4,middle+spine//2+7,top+slot_h-5),fill=(255,255,255,45),width=2)
        composite=Image.alpha_composite(result.convert('RGBA'),overlay)
        result.close();overlay.close()
        result=composite.convert('RGB');composite.close()
    return result


def ImageOps_contain(image: Image.Image, bounds: tuple[int,int]) -> Image.Image:
    from PIL import ImageOps
    return ImageOps.contain(image.convert('RGB'), bounds, method=Image.Resampling.LANCZOS)
