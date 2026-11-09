"""No credibility: every territory is rated by the GLM alone.

Z = 0 everywhere, so θ is the overall ratio of actual to expected claims, the same for all.
A territory's rate then differs from another's only by what the GLM knows of it: its
terrain and, with the wind offset, its distance inland. Its own claims count for nothing.

The option to beat: credibility earns its place only where it comes closer than this.
"""
import numpy as np

from blocks import ui
from territories import blend, experience, pictures

METRICS = {"mostly_own": "territories with Z ≥ 0.9", "mostly_glm": "territories with Z < 0.1"}


def credibility(join, glm):
    m, A, X, mean, seen = experience(join, glm)
    return blend(join, m, A, X, mean, np.zeros_like(m))


def view(out):
    return [ui.metrics(), *pictures(out)]
