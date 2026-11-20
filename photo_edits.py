"""Edición fotográfica reversible de Revelo.

Solo se guardan parámetros inocuos (nunca rutas ni código). El archivo fuente
permanece intacto; la misma composición se aplica para miniaturas, PDF y Word.
"""
from __future__ import annotations

import math
from PIL import Image, ImageOps, ImageEnhance, ImageChops

DEFAULT = {
    'turns': 0, 'flip_h': False, 'flip_v': False, 'straighten': 0.0,
    'crop': None, 'brightness': 1.0, 'contrast': 1.0,
    'saturation': 1.0, 'sharpness': 1.0, 'auto_correct': False,
    'print_scale': 1.0,
}
LIMITS = {'brightness': (0.2, 2.5), 'contrast': (0.2, 2.5),
          'saturation': (0.0, 2.5), 'sharpness': (0.0, 3.0),
          'print_scale': (0.25, 1.5)}


def validate_edits(value: dict | None) -> dict:
    """Valida datos de proyectos/PDF de terceros y devuelve una copia normalizada."""
    if value is None:
        return dict(DEFAULT)
    if not isinstance(value, dict) or any(k not in DEFAULT for k in value):
        raise ValueError('Ediciones de fotografía no reconocidas')
    result = dict(DEFAULT)
    if 'turns' in value:
        if type(value['turns']) is not int or not 0 <= value['turns'] <= 3:
            raise ValueError('Giro no válido')
        result['turns'] = value['turns']
    for key in ('flip_h', 'flip_v', 'auto_correct'):
        if key in value:
            if type(value[key]) is not bool:
                raise ValueError('Volteo no válido')
            result[key] = value[key]
    if 'straighten' in value:
        angle = value['straighten']
        if type(angle) not in (int, float) or not math.isfinite(angle) or abs(angle) > 15:
            raise ValueError('Enderezado fuera de rango')
        result['straighten'] = float(angle)
    if value.get('crop') is not None:
        box = value['crop']
        if not isinstance(box, (list, tuple)) or len(box) != 4 or any(type(x) not in (int, float) or not math.isfinite(x) for x in box):
            raise ValueError('Recorte no válido')
        x0,y0,x1,y1 = box
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1 and x1-x0 >= .005 and y1-y0 >= .005):
            raise ValueError('El área de recorte es demasiado pequeña')
        result['crop'] = [float(x0),float(y0),float(x1),float(y1)]
    for key,(low, high) in LIMITS.items():
        if key in value:
            number = value[key]
            if type(number) not in (float,int) or not math.isfinite(number) or not low <= number <= high:
                raise ValueError('Ajuste fotográfico fuera de rango')
            result[key] = float(number)
    return result


def has_edits(spec: dict | None) -> bool:
    if spec is None:
        return False
    obj = validate_edits(spec)
    return obj != DEFAULT


def _rotate90(im: Image.Image, turns: int) -> Image.Image:
    return im.transpose({1:Image.Transpose.ROTATE_270, 2:Image.Transpose.ROTATE_180,
                         3:Image.Transpose.ROTATE_90}[turns])


def geometry_image(source: Image.Image, edits: dict | None) -> Image.Image:
    """Giro, espejo y enderezado antes de definir el recorte proporcional."""
    spec = validate_edits(edits)
    image = source.copy()
    if spec['turns']:
        nxt = _rotate90(image, spec['turns']); image.close(); image = nxt
    if spec['flip_h']:
        nxt = ImageOps.mirror(image); image.close(); image = nxt
    if spec['flip_v']:
        nxt = ImageOps.flip(image); image.close(); image = nxt
    if abs(spec['straighten']) >= 0.01:
        nxt = image.rotate(-spec['straighten'], expand=True, resample=Image.Resampling.BICUBIC,
                           fillcolor=(255,255,255) if image.mode == 'RGB' else 255)
        image.close(); image = nxt
    return image


def automatic_photo_correction(source: Image.Image) -> Image.Image:
    """Mejora fotográfica moderada y determinista, sin IA ni servicios externos.

    Ajusta únicamente la luminancia (el color no se estira canal a canal),
    y añade una corrección leve de saturación y nitidez. No modifica `source`.
    No pretende replicar el algoritmo propietario de Fotos de Apple.
    """
    base = source.convert('RGB')
    ycbcr = base.convert('YCbCr')
    y, cb, cr = ycbcr.split()
    balanced = ImageOps.autocontrast(y, cutoff=1)
    # Corregimos parcialmente para evitar blancos quemados y sombras empastadas.
    softer = Image.blend(y, balanced, .48)
    balanced.close()
    corrected = Image.merge('YCbCr', (softer, cb, cr)).convert('RGB')
    y.close(); cb.close(); cr.close(); softer.close(); ycbcr.close(); base.close()
    colored = ImageEnhance.Color(corrected).enhance(1.035)
    corrected.close()
    sharp = ImageEnhance.Sharpness(colored).enhance(1.09)
    colored.close()
    return sharp


def apply_edits(source: Image.Image, edits: dict | None) -> Image.Image:
    """Genera la vista editada. El llamador conserva la propiedad de source."""
    spec = validate_edits(edits)
    image = geometry_image(source, spec)
    try:
        if spec['crop']:
            w,h = image.size
            x0,y0,x1,y1 = spec['crop']
            box = (round(x0*w),round(y0*h), round(x1*w),round(y1*h))
            box = (max(0,box[0]),max(0,box[1]),min(w,max(box[0]+1,box[2])),min(h,max(box[1]+1,box[3])))
            nxt = image.crop(box); image.close(); image=nxt
        if spec['auto_correct']:
            nxt = automatic_photo_correction(image); image.close(); image = nxt
        for key, cls in (('brightness',ImageEnhance.Brightness),('contrast',ImageEnhance.Contrast),
                         ('saturation',ImageEnhance.Color),('sharpness',ImageEnhance.Sharpness)):
            if abs(spec[key]-1.0)>0.001:
                nxt = cls(image).enhance(spec[key]); image.close(); image=nxt
        return image
    except Exception:
        image.close()
        raise


def transformed_dimensions(size: tuple[int,int], edits: dict | None) -> tuple[float,float]:
    spec = validate_edits(edits)
    w,h = size
    if spec['turns']%2:
        w,h=h,w
    angle=math.radians(spec['straighten'])
    c,s=abs(math.cos(angle)),abs(math.sin(angle))
    w,h=w*c+h*s,w*s+h*c
    if spec['crop']:
        x0,y0,x1,y1=spec['crop']
        w*=x1-x0; h*=y1-y0
    return w,h


def auto_white_crop(image: Image.Image, *, tolerance: int=24, pad: float=0.004) -> list[float] | None:
    """Detecta borde blanco/clarísimo periférico; no altera la fuente."""
    rgb=image.convert('RGB')
    rgb.thumbnail((700,700), Image.Resampling.LANCZOS)
    w,h=rgb.size
    if min(w,h)<25:
        return None
    # Comparación por canal máximo: amarillos claros no se consideran papel blanco.
    difference=ImageChops.difference(rgb,Image.new('RGB',(w,h),'white'))
    r,g,b=difference.split()
    import PIL.ImageChops as chops
    mask=chops.lighter(chops.lighter(r,g),b).point(lambda v: 255 if v>tolerance else 0)
    box=mask.getbbox()
    if box is None:
        return None
    x0,y0,x1,y1=box
    if x0<3 and y0<3 and x1>w-3 and y1>h-3:
        return None
    padding=max(1,round(min(w,h)*pad))
    x0=max(0,x0-padding);y0=max(0,y0-padding);x1=min(w,x1+padding);y1=min(h,y1+padding)
    if (x1-x0)<w*.1 or (y1-y0)<h*.1:
        return None
    return [x0/w,y0/h,x1/w,y1/h]
