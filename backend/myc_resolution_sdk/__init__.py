"""SDK oficial para consumir exclusivamente la API institucional."""

from myc_resolution_sdk.client import ResolutionEngineClient
from myc_resolution_sdk.errors import ResolutionApiError

__all__ = ["ResolutionApiError", "ResolutionEngineClient"]
