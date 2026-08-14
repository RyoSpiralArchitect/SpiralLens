"""Private framework-neutral structural contracts for model observations."""

from __future__ import annotations

from typing import Protocol

import numpy as np

__all__: tuple[str, ...] = ()

LOGIT_SUMMARY_COLUMNS: tuple[str, ...] = (
    "max_logit",
    "mean_logit",
    "std_logit",
    "logsumexp_logit",
    "entropy_nats",
    "input_token_logit",
)


class _NumpyConvertibleArray(Protocol):
    """Array value that exposes a NumPy representation to the capture store."""

    @property
    def shape(self) -> tuple[int, ...]: ...

    def numpy(self) -> np.ndarray: ...


class BatchObservationProtocol(Protocol):
    """Structural observation boundary consumed by the capture store."""

    @property
    def resid_pre(self) -> _NumpyConvertibleArray: ...

    @property
    def resid_post(self) -> _NumpyConvertibleArray: ...

    @property
    def norm_summary(self) -> _NumpyConvertibleArray: ...

    @property
    def logit_summary(self) -> _NumpyConvertibleArray: ...

    @property
    def prediction_ids(self) -> _NumpyConvertibleArray: ...
