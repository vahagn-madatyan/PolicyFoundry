"""AdapterRegistry: plugin discovery via entry_points."""

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any

from policyfoundry.exceptions import AdapterNotFoundError

if TYPE_CHECKING:
    from policyfoundry.adapters.base import FirewallAdapter

logger = logging.getLogger(__name__)

_ENTRY_POINT_GROUP = "policyfoundry.adapters"
_BUILTIN_ADAPTER_NAME = "aws_sg"
_BUILTIN_NULL_ADAPTER_NAME = "null"


class AdapterRegistry:
    """Discovers and loads firewall adapters via setuptools entry_points.

    Built-in aws_sg adapter has a direct-import fallback for development
    when entry points are not installed.
    """

    @staticmethod
    def get_adapter(name: str, **kwargs: Any) -> "FirewallAdapter":
        """Load an adapter by name and instantiate with kwargs.

        Raises AdapterNotFoundError if the adapter cannot be found.
        """
        eps = entry_points(group=_ENTRY_POINT_GROUP)
        for ep in eps:
            if ep.name == name:
                adapter_cls = ep.load()
                return adapter_cls(**kwargs)

        if name == _BUILTIN_ADAPTER_NAME:
            try:
                from policyfoundry.adapters.aws_sg import (
                    AwsSecurityGroupAdapter,
                )

                return AwsSecurityGroupAdapter(**kwargs)
            except ImportError:
                logger.warning("Failed to import adapter module", exc_info=True)
                pass

        if name == _BUILTIN_NULL_ADAPTER_NAME:
            from policyfoundry.adapters.null import NullAdapter

            return NullAdapter()

        msg = f"Adapter '{name}' not found in registry"
        raise AdapterNotFoundError(msg, error_code="ADAPTER_NOT_FOUND")

    @staticmethod
    def list_adapters() -> list[str]:
        """Return names of all registered adapters.

        Always includes aws_sg (built-in).
        """
        eps = entry_points(group=_ENTRY_POINT_GROUP)
        names = [ep.name for ep in eps]
        if _BUILTIN_ADAPTER_NAME not in names:
            names.append(_BUILTIN_ADAPTER_NAME)
        if _BUILTIN_NULL_ADAPTER_NAME not in names:
            names.append(_BUILTIN_NULL_ADAPTER_NAME)
        return names
