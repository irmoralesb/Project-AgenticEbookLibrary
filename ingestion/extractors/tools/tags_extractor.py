from extractors.models.models import QueryTags
from extractors.tools.tag_normalization import canonicalize_tags
from llm_models.basic_models import BasicLocalModel


class TagsExtractor:
    _MIN_TAGS_TO_ACCEPT: int = 3
    _MAX_TAGS: int = 15

    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_tags(self, texts: list[str], *, title: str | None, description: str | None,
                 category: str | None, subcategory: str | None) -> list[str]:

        accumulated: list[str] = []

        for text_range in texts:
            if not text_range:
                continue

            try:
                result: QueryTags = self.llm.extract_tags(
                    text=text_range,
                    title=title,
                    description=description,
                    category=category,
                    subcategory=subcategory
                )
            except Exception:
                continue

            accumulated.extend(result.tags)
            normalized = canonicalize_tags(
                accumulated, drop_equal_to=[category, subcategory],
                max_count=self._MAX_TAGS
            )

            if len(normalized) >= self._MIN_TAGS_TO_ACCEPT:
                return normalized

        return canonicalize_tags(
            accumulated,
            drop_equal_to=[category, subcategory],
            max_count=self._MAX_TAGS
        )
