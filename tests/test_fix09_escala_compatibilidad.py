"""Nuevos límites del deslizador 5 %-800 % con validación persistente."""
import pytest
from photo_edits import validate_edits


@pytest.mark.parametrize('value', [0.05, 0.65, 1.0, 1.5, 3.0, 8.0])
def test_master_print_scale_accepts_extended_range(value):
    assert validate_edits({'print_scale': value})['print_scale'] == value


@pytest.mark.parametrize('value', [0.0, 0.049, -1.0, 8.001, 12.0])
def test_master_print_scale_rejects_out_of_range(value):
    with pytest.raises(ValueError):
        validate_edits({'print_scale': value})
