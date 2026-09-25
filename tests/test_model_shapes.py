import torch

from models.attention_mil import AttentionMILCox
from models.mean_pooling_cox import MeanPoolingCox


def test_mean_pooling_output_shape():
    model = MeanPoolingCox(64)
    x = torch.randn(50, 64)
    risk, attn = model(x)
    assert risk.shape == ()
    assert attn is None


def test_attention_mil_weights_sum_to_one():
    model = AttentionMILCox(64, hidden_dim=32)
    x = torch.randn(40, 64)
    risk, weights = model(x)
    assert risk.shape == ()
    assert weights.shape == (40,)
    assert torch.allclose(weights.sum(), torch.tensor(1.0), atol=1e-5)
