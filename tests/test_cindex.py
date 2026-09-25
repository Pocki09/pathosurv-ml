import numpy as np

from evaluation.concordance import harrell_c_index


def test_c_index_perfect_ranking():
    time = np.array([1.0, 2.0, 3.0, 4.0])
    event = np.array([1, 1, 0, 0])
    risk = np.array([3.0, 2.0, 1.0, 0.5])
    ci = harrell_c_index(event, time, risk)
    assert ci == 1.0
