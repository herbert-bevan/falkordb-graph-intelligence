"""Cached entity candidate resolver for Company Brain (Track 3)."""

import time
from typing import Any, Dict, List, Optional
from graph_intelligence.common.falkordb_client import GraphStore
from graph_intelligence.common.text import squash
from graph_intelligence.company_brain.queries import ALL_COMPANY_ENTITIES_QUERY


class EntityResolver:
    """Resolves entity candidates against company graph nodes with a 60-second TTL cache."""

    def __init__(self, store: GraphStore, ttl_seconds: float = 60.0):
        self.store = store
        self.ttl_seconds = ttl_seconds
        self._cache: List[Dict[str, Any]] = []
        self._last_loaded_at: float = 0.0

    def _get_entities(self) -> List[Dict[str, Any]]:
        now = time.monotonic()
        if not self._cache or (now - self._last_loaded_at) > self.ttl_seconds:
            self._cache = self.store.query(ALL_COMPANY_ENTITIES_QUERY)
            self._last_loaded_at = now
        return self._cache

    def resolve(self, query: str) -> Optional[Dict[str, Any]]:
        """Resolve a single string to an entity node by ID, name, or alias."""
        target_squashed = squash(query)
        if not target_squashed:
            return None

        entities = self._get_entities()

        # 1. Exact ID or Name match
        for ent in entities:
            if squash(ent.get("id", "")) == target_squashed or squash(ent.get("name", "")) == target_squashed:
                return ent

        # 2. Alias match
        for ent in entities:
            aliases = ent.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            for a in aliases:
                if squash(a) == target_squashed:
                    return ent

        # 3. Substring match
        for ent in entities:
            ent_squashed = squash(ent.get("name", ""))
            if target_squashed in ent_squashed or ent_squashed in target_squashed:
                return ent

        return None

    def resolve_all(self, text: str) -> List[Dict[str, Any]]:
        """Scan text and return all distinct recognized company entities."""
        entities = self._get_entities()
        matched: List[Dict[str, Any]] = []
        seen_ids = set()

        text_squashed = squash(text)

        # Sort entities by length of squashed name descending (longest match first)
        sorted_entities = sorted(
            entities,
            key=lambda e: max(len(squash(e.get("name", ""))), len(squash(e.get("id", "")))),
            reverse=True,
        )

        for ent in sorted_entities:
            ent_id = ent["id"]
            if ent_id in seen_ids:
                continue

            names_to_check = [ent["name"], ent_id]
            aliases = ent.get("aliases") or []
            if isinstance(aliases, str):
                aliases = [aliases]
            names_to_check.extend(aliases)

            for cand in names_to_check:
                sq = squash(cand)
                if sq and len(sq) >= 3 and sq in text_squashed:
                    matched.append(ent)
                    seen_ids.add(ent_id)
                    break

        return matched
