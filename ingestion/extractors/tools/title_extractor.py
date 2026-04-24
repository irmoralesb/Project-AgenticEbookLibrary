from extractors.models.models import QueryTitleWithEdition
from llm_models.basic_models import BasicLocalModel


class TitleExtractor():
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_title_and_edition(self, file_name: str) -> QueryTitleWithEdition:
        return self.llm.extract_title_and_edition(file_name)
