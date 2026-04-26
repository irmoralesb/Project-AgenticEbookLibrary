from extractors.models.models import QueryCategoryMetadata
from llm_models.basic_models import BasicLocalModel


class CategoryExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_category(self, text: str) -> QueryCategoryMetadata:
        return self.llm.extract_category(text)
