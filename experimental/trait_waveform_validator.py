"""trait_waveform_validator.py

Replace scalar group-comparison ("A is stronger than B") with phase-space
comparison ("A(t, phase, load, duration, task) vs B(t, phase, load,
duration, task)").

This is not a bias offset. It is a structural reformulation that makes
scalar bias a TYPE ERROR rather than a value error.

Core property:
  A claim of form
       group_X {comparator} group_Y  on trait T
  is rejected unless ALL required axes are specified. At that point the
  claim either:
    (a) becomes narrow, testable, and useful, or
    (b) reveals itself as cherry-picked.

  No more hidden defaults. Bias must declare its coordinates.

Plugs into PhysicsGuard via PhysicsGuardAdapter (bottom of file).

STATUS: in progress.

CC0. Stdlib only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# exceptions
# ---------------------------------------------------------------------------

class WaveformError(Exception):
    """Base class for waveform validator errors."""


class UnderspecifiedComparisonError(WaveformError):
    """A comparison was attempted without specifying all required
    phase/load/duration/task axes.

    This is the core anti-bias mechanism: scalar comparison is not a bug
    to be filtered, it is a malformed query.
    """


class ScalarCollapseError(WaveformError):
    """A query attempted to reduce a phase-space surface to a single
    number without specifying coordinates."""


class IncompatibleSurfaceError(WaveformError):
    """Two surfaces being compared have axes that do not align."""


# ---------------------------------------------------------------------------
# axis primitives
# ---------------------------------------------------------------------------

class AxisKind(Enum):
    PHASE = "phase"          # endocrine cycle, circadian, etc.
    LOAD = "load"            # external demand
    DURATION = "duration"    # time scale of the task
    TASK = "task"            # task type / class
    SUBSTRATE = "substrate"  # individual-level state (sleep, age, etc.)


@dataclass(frozen=True)
class Axis:
    name: str
    kind: AxisKind
    unit: str
    domain: tuple                        # (min, max) range or tuple of categoricals
    required_for_comparison: bool = True
    notes: str = ""

    def validate(self, value: Any) -> None:
        if (isinstance(self.domain, tuple) and len(self.domain) == 2
                and all(isinstance(x, (int, float)) for x in self.domain)):
            lo, hi = self.domain
            if not (lo <= value <= hi):
                raise WaveformError(
                    f"axis '{self.name}' value {value} outside "
                    f"domain [{lo}, {hi}]"
                )
        else:
            if value not in self.domain:
                raise WaveformError(
                    f"axis '{self.name}' value {value!r} not in {self.domain}"
                )


# ---------------------------------------------------------------------------
# trait waveform: a trait expressed as a function over phase-space
# ---------------------------------------------------------------------------

@dataclass
class TraitWaveform:
    """A trait expressed as a function over phase-space, not a scalar.

    `evaluator` receives a dict of axis_name -> value and returns
    (mean, stddev) at that point in phase space. stddev is required.
    A waveform without uncertainty is a lie.
    """
    name: str
    group: str
    axes: Tuple[Axis, ...]
    measurement_unit: str
    evaluator: Callable[[Dict[str, Any]], Tuple[float, float]]
    citations: Tuple[str, ...] = ()
    confidence: float = 0.5
    notes: str = ""

    def required_axes(self) -> set:
        return {a.name for a in self.axes if a.required_for_comparison}

    def evaluate(self, **state) -> Tuple[float, float]:
        missing = self.required_axes() - set(state.keys())
        if missing:
            raise UnderspecifiedComparisonError(
                f"trait '{self.name}' for group '{self.group}' "
                f"requires axes {sorted(missing)} to evaluate. "
                f"scalar evaluation is not permitted."
            )
        for ax in self.axes:
            if ax.name in state:
                ax.validate(state[ax.name])
        return self.evaluator(state)

    def __repr__(self):
        axnames = ",".join(a.name for a in self.axes)
        return f"TraitWaveform({self.name}@{self.group} | axes=[{axnames}])"


# ---------------------------------------------------------------------------
# trait surface: multi-group, comparison-aware
# ---------------------------------------------------------------------------

@dataclass
class TraitSurface:
    """A trait sampled across multiple groups. Comparisons are only
    permitted with all required axes pinned."""
    trait: str
    waveforms: Dict[str, TraitWaveform]
    description: str = ""

    def __post_init__(self):
        if len(self.waveforms) < 2:
            return
        ref = next(iter(self.waveforms.values()))
        ref_axes = ref.required_axes()
        for g, wf in self.waveforms.items():
            if wf.required_axes() != ref_axes:
                raise IncompatibleSurfaceError(
                    f"group '{g}' axes {wf.required_axes()} do not match "
                    f"reference axes {ref_axes}. surfaces must share axes."
                )

    def required_axes(self) -> set:
        return next(iter(self.waveforms.values())).required_axes()

    def evaluate_all(self, **state) -> Dict[str, Tuple[float, float]]:
        return {g: wf.evaluate(**state) for g, wf in self.waveforms.items()}

    def compare(self, group_a: str, group_b: str, **state) -> Dict[str, Any]:
        """Structured comparison at a fully-specified phase point. Includes
        overlap detection (1-sigma) so 'difference' is not claimed when the
        distributions overlap."""
        missing = self.required_axes() - set(state.keys())
        if missing:
            raise UnderspecifiedComparisonError(
                f"comparison of '{group_a}' vs '{group_b}' on trait "
                f"'{self.trait}' requires axes {sorted(missing)}. "
                f"refusing scalar collapse."
            )
        if group_a not in self.waveforms or group_b not in self.waveforms:
            raise WaveformError(f"unknown group(s): {group_a}, {group_b}")

        ma, sa = self.waveforms[group_a].evaluate(**state)
        mb, sb = self.waveforms[group_b].evaluate(**state)

        # 1-sigma overlap test
        overlap = not (ma + sa < mb - sb or mb + sb < ma - sa)
        # Cohen's d (pooled stddev)
        pooled = math.sqrt((sa * sa + sb * sb) / 2) if (sa or sb) else 0.0
        if pooled > 0:
            d = (ma - mb) / pooled
        else:
            d = float("inf") if ma != mb else 0.0

        if overlap and abs(d) < 0.2:
            verdict = "indistinguishable_at_this_phase"
        elif abs(d) < 0.5:
            verdict = "small_difference"
        elif abs(d) < 0.8:
            verdict = "moderate_difference"
        else:
            verdict = "large_difference"

        return {
            "trait": self.trait,
            "phase_point": dict(state),
            "group_a": {"name": group_a, "mean": ma, "stddev": sa},
            "group_b": {"name": group_b, "mean": mb, "stddev": sb},
            "delta_mean": ma - mb,
            "cohens_d": d,
            "one_sigma_overlap": overlap,
            "verdict": verdict,
            "axis_specification": "complete",
            "scalar_claim_permitted": False,
            "narrow_claim_permitted": True,
        }

    def map_overlap_region(
        self,
        sample_grid: Dict[str, list],
        group_a: str,
        group_b: str,
    ) -> Dict[str, Any]:
        """Sample the phase space and report:
            - fraction of points where groups are indistinguishable
            - fraction where group_a > group_b
            - fraction where group_b > group_a
        The anti-bias diagnostic: if the answer flips sign across the
        phase space, no scalar claim is defensible."""
        from itertools import product

        keys = list(sample_grid.keys())
        vals = [sample_grid[k] for k in keys]

        n = 0
        n_overlap = 0
        n_a_greater = 0
        n_b_greater = 0

        for combo in product(*vals):
            state = dict(zip(keys, combo))
            try:
                result = self.compare(group_a, group_b, **state)
            except WaveformError:
                continue
            n += 1
            if result["one_sigma_overlap"]:
                n_overlap += 1
            elif result["delta_mean"] > 0:
                n_a_greater += 1
            else:
                n_b_greater += 1

        if n == 0:
            return {"error": "no valid phase points sampled"}

        sign_flip = (n_a_greater > 0 and n_b_greater > 0)
        if sign_flip:
            advisory = ("scalar comparison is INVALID -- direction reverses "
                        "across phase space")
        elif (n_overlap / n) >= 0.2:
            advisory = ("scalar comparison is INVALID -- distributions "
                        "overlap on most of phase space")
        else:
            advisory = ("narrow claim may be defensible if all axes "
                        "are specified")

        return {
            "trait": self.trait,
            "n_phase_points": n,
            "fraction_indistinguishable": n_overlap / n,
            "fraction_a_greater": n_a_greater / n,
            "fraction_b_greater": n_b_greater / n,
            "sign_flips_across_phase_space": sign_flip,
            "scalar_claim_defensible": (
                not sign_flip and (n_overlap / n) < 0.2
            ),
            "advisory": advisory,
        }
