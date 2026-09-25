import torch

from losses.cox_ph_loss import cox_ph_loss


def test_cox_loss_correct_order_lower():
    risk_good = torch.tensor([3.0, 2.0, 1.0])
    time = torch.tensor([5.0, 10.0, 15.0])
    event = torch.tensor([1.0, 1.0, 0.0])
    risk_bad = torch.tensor([1.0, 2.0, 3.0])
    loss_good = cox_ph_loss(risk_good, time, event)
    loss_bad = cox_ph_loss(risk_bad, time, event)
    assert loss_good < loss_bad


def test_cox_loss_finite_gradient():
    risk = torch.tensor([0.5, 1.2, -0.3], requires_grad=True)
    time = torch.tensor([10.0, 20.0, 30.0])
    event = torch.tensor([1.0, 0.0, 1.0])
    loss = cox_ph_loss(risk, time, event)
    loss.backward()
    assert torch.isfinite(loss)
    assert risk.grad is not None and torch.isfinite(risk.grad).all()
