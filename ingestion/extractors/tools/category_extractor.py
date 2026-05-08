from extractors.models.models import QueryCategoryMetadata
from llm_models.basic_models import BasicLocalModel


class CategoryExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_category(self, texts: list[str]) -> QueryCategoryMetadata:
        result: str = ""
        for text_range in texts:
            result = self.llm.extract_category(text_range)
            if result.category != "Other":
                return result
        return result
