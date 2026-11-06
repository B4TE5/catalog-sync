"""Plan de búsqueda por afinidad de filtros y rotación persistente."""

from collections import defaultdict
from dataclasses import dataclass, field

from vinted_hunter.config import Config, Profile


@dataclass
class Search:
    profiles: list[Profile]
    params: dict[str, str] = field(default_factory=dict)
    expects_items: bool = False

    def query(self, page: int) -> dict[str, str]:
        return {"order": "newest_first", "page": str(page), **self.params}


def plan_searches(
    config: Config,
    cursor: int = 0,
    selftest: bool = False,
) -> tuple[list[Search], int]:
    if selftest:
        return [Search([p], {"search_text": p.text_queries[0].q}) for p in config.profiles], cursor
    grouped: dict[tuple[str, int], list[Profile]] = defaultdict(list)
    high = []
    normal = []
    ids = config.ids
    for profile in config.profiles:
        category = ids.catalog_ids.get(profile.hood) or ids.catalog_ids.get("sweatshirts")
        if profile.brand in ids.brand_ids and category:
            grouped[profile.size, category].append(profile)
        for query in profile.text_queries:
            search = Search([profile], {"search_text": query.q}, query.priority == "high")
            (high if query.priority == "high" else normal).append(search)
    combined = [
        Search(
            profiles,
            {
                "catalog[]": str(category),
                "brand_ids[]": ",".join(
                    str(brand_id) for p in profiles for brand_id in ids.brand_ids[p.brand]
                ),
                **({"size_ids[]": str(ids.size_ids[size])} if size in ids.size_ids else {}),
            },
        )
        for (size, category), profiles in grouped.items()
    ]
    cap = config.scoring.capture.catalog_limit
    required = (combined + high)[:cap]
    count = min(len(normal), cap - len(required))
    chosen = [normal[(cursor + i) % len(normal)] for i in range(count)]
    return required + chosen, (cursor + count) % len(normal) if normal else 0
