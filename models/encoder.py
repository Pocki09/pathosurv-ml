"""Frozen patch encoders (TITAN hook + ResNet50 fallback for smoke / Colab)."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torchvision import models, transforms

from pathosurv.config import load_yaml


@dataclass
class EncoderInfo:
    encoder_id: str
    encoder_version: str
    embedding_dim: int
    transform: transforms.Compose


def _resnet50_backbone() -> tuple[nn.Module, int]:
    weights = models.ResNet50_Weights.IMAGENET1K_V2
    net = models.resnet50(weights=weights)
    dim = net.fc.in_features
    net.fc = nn.Identity()
    for p in net.parameters():
        p.requires_grad = False
    net.eval()
    return net, dim


def load_encoder(encoder_id: str | None = None) -> tuple[nn.Module, EncoderInfo]:
    cfg = load_yaml("encoder.yaml")
    eid = encoder_id or cfg.get("fallback_encoder_id") or "resnet50_imagenet"
    if eid == "TITAN":
        raise NotImplementedError(
            "TITAN encoder not wired in this repo yet. "
            "Set fallback_encoder_id: resnet50_imagenet in configs/encoder.yaml "
            "or load TITAN in Colab and match embedding_dim in configs/model.yaml."
        )
    if eid not in ("resnet50_imagenet", "resnet50_imagenet_baseline"):
        raise ValueError(f"Unsupported encoder_id: {eid}")

    model, dim = _resnet50_backbone()
    tfm = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=weights_mean(), std=weights_std()),
        ]
    )
    info = EncoderInfo(
        encoder_id="resnet50_imagenet",
        encoder_version="torchvision_imagenet1k_v2",
        embedding_dim=dim,
        transform=tfm,
    )
    return model, info


def weights_mean():
    return (0.485, 0.456, 0.406)


def weights_std():
    return (0.229, 0.224, 0.225)


@torch.inference_mode()
def encode_patches(model: nn.Module, info: EncoderInfo, patch_tensors: torch.Tensor) -> torch.Tensor:
    """``patch_tensors``: (B, 3, H, W) float tensor already normalized."""
    device = next(model.parameters()).device
    patch_tensors = patch_tensors.to(device)
    return model(patch_tensors)
