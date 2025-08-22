# pylint: disable=C0114,C0116

import warnings
from pypicosdk import ps6000a, OverrangeWarning


def test_adc_to_mv():
    warnings.simplefilter("ignore", OverrangeWarning)
    scope = ps6000a("pytest")
    scope.over_range = 255
    assert scope.is_over_range() == ["A", "B", "C", "D", "E", "F", "G", "H"]
