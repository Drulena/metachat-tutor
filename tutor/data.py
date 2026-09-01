"""Re-export scenario data from :mod:`tutor.scenarios`.

All data originally lived here. It has been moved to ``tutor.scenarios``
for better organization.  This module re-exports every name so that
existing ``from .data import ...`` statements keep working.
"""

from .scenarios import (  # noqa: F401
    LEVELS,
    SCENARIO,
    THEORETICAL_BASE,
    TASK_VARIANTS,
    randomize_scenario,
)
