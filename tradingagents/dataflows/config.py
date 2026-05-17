from copy import deepcopy
from typing import Dict, Optional

import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config: Optional[Dict] = None


def initialize_config():
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = deepcopy(default_config.DEFAULT_CONFIG)


def set_config(config: Dict):
    """Replace the configuration with the given dict.

    The incoming dict fully replaces the current config — keys not present in
    the incoming dict are removed.  Dict-valued keys (e.g. ``data_vendors``)
    are merged one level deep relative to the *incoming* dict's own values, so
    nested keys are still respected; but stale top-level keys from a previous
    config are cleared.

    This behaviour lets callers use ``set_config(deepcopy(DEFAULT_CONFIG))``
    as a reliable full reset (e.g. in test fixtures) while preserving the
    convenience of partial nested-dict updates in production callers that
    always pass a full config object.

    Callers must always pass a complete config dict. Multiple sequential partial-key
    calls will lose all keys not present in the most recent call.
    """
    global _config
    initialize_config()
    incoming = deepcopy(config)
    # Full replacement: start from a fresh dict built from the incoming keys only.
    new_config: Dict = {}
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(_config.get(key), dict):
            merged = deepcopy(_config[key])
            merged.update(value)
            new_config[key] = merged
        else:
            new_config[key] = value
    _config = new_config


def get_config() -> Dict:
    """Get the current configuration."""
    if _config is None:
        initialize_config()
    return deepcopy(_config)


# Initialize with default config
initialize_config()
