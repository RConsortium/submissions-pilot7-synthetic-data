"""CATH EDC generator package.

``build_all.build_edc(GenConfig(...))`` runs the g-formula causal-DAG simulator
(vendored under ``sim/``) and writes the CRF forms. The simulator package is the
upstream truth: there is no canonical SDTM to sample from.
"""
from .config import GenConfig          # noqa: F401
from .build_all import build_edc       # noqa: F401

__all__ = ["GenConfig", "build_edc"]
