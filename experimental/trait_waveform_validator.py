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
