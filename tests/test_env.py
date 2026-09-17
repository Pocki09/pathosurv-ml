import sys

import pandas as pd
import pytest

from pathosurv import __version__
from pathosurv.seed import set_seed

torch = pytest.importorskip("torch")
sksurv = pytest.importorskip("sksurv")


def test_package_import():
    assert __version__


def test_environment_versions():
    assert sys.version_info >= (3, 10)
    assert torch.__version__
    assert pd.__version__
    assert sksurv.__version__


def test_set_seed():
    set_seed(42)
