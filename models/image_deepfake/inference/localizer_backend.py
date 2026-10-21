"""Swappable pixel-localization contract; no detector depends on TruFor internals."""
from typing import Protocol, Any


class PixelLocalizer(Protocol):
    def predict(self, data: bytes, time_budget: float | None = None) -> dict[str, Any]: ...


def create_localizer(backend: str = 'trufor') -> PixelLocalizer | None:
    if backend == 'none':
        return None
    if backend != 'trufor':
        raise ValueError('Unsupported localization backend: ' + backend)
    # Import lazily so disabling the research backend needs no vendor dependencies.
    from .bounded_localizer import BoundedLocalizer
    return BoundedLocalizer()
