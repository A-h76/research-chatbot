"""Known production flag names and fail-open defaults.

Missing DB rows use these defaults so shipping the service does not kill
live Discover / Writing Intelligence. Admin can still flip ``enabled=false``
as a kill switch, or set ``rollout_pct`` for gradual enable.
"""

from __future__ import annotations

# Discover / OpenAlex scholarly search + import
FLAG_DISCOVER_SEARCH = "discover_search"

# POST /api/evidence/writing (Writing Intelligence)
FLAG_WRITING_INTELLIGENCE = "writing_intelligence"

KNOWN_FLAGS: dict[str, dict] = {
    FLAG_DISCOVER_SEARCH: {
        "default": True,
        "description": "OpenAlex Discover search and import (/api/discover*)",
    },
    FLAG_WRITING_INTELLIGENCE: {
        "default": True,
        "description": "Writing Intelligence grounded generation (/api/evidence/writing)",
    },
}
