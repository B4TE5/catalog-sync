"""Plan de búsqueda por afinidad de filtros y rotación persistente."""

from collections import defaultdict
from dataclasses import dataclass, field

from vinted_hunter.config import Config, Profile
from vinted_hunter.sources.base import QueryParams


@dataclass
class Search:
    profiles: list[Profile]
    params: QueryParams = field(default_factory=dict)
    expects_items: bool = False

    def query(self, page: int) -> QueryParams:
        return {"order": "newest_first", "page": str(page), **self.params}


def category_params(profile: Profile) -> QueryParams:
    categories = [str(value) for value in profile.categories.search]
    if not categories:
        return {}
    return {"catalog[]": categories[0] if len(categories) == 1 else categories}


def search_groups(config: Config) -> tuple[list[Search], list[Search], list[Search]]:
    grouped: dict[tuple[str | None, tuple[int, ...]], list[Profile]] = defaultdict(list)
    high = []
    normal = []
    ids = config.ids
    for profile in config.profiles:
        if profile.brand in ids.brand_ids:
            grouped[profile.size, tuple(profile.categories.search)].append(profile)
        for query in profile.text_queries:
            search = Search(
                [profile], {**category_params(profile), "search_text": query.q},
                query.q == "stone island",
            )
            (high if query.priority == "high" else normal).append(search)
    combined = [
        Search(
            profiles,
            {
                **category_params(profiles[0]),
                "brand_ids[]": [
                    str(brand_id) for p in profiles for brand_id in ids.brand_ids[p.brand]
                ],
                **({"size_ids[]": str(ids.size_ids[size])} if size in ids.size_ids else {}),
            },
        )
        for (size, _), profiles in grouped.items()
    ]
    return combined, high, normal


def all_searches(config: Config) -> list[Search]:
    """Todas las búsquedas activas, sin perder consultas de la rotación."""
    return [search for group in search_groups(config) for search in group]


def plan_searches(
    config: Config,
    cursor: int = 0,
    selftest: bool = False,
    catalog_limit: int | None = None,
) -> tuple[list[Search], int]:
    if selftest:
        return [
            Search([p], {**category_params(p), "search_text": p.text_queries[0].q})
            for p in config.profiles
        ], cursor
    combined, high, normal = search_groups(config)
    cap = min(config.scoring.capture.catalog_limit,
              catalog_limit if catalog_limit is not None else config.scoring.capture.catalog_limit)
    required = (combined + high)[:cap]
    count = min(len(normal), cap - len(required))
    chosen = [normal[(cursor + i) % len(normal)] for i in range(count)]
    return required + chosen, (cursor + count) % len(normal) if normal else 0
