from llm_models.basic_models import BasicLocalModel


class AuthorsExtractor():
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_authors(self, text: str) -> list[str]:
        return self.llm.extract_authors(text).authors