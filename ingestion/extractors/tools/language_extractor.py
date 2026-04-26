from llm_models.basic_models import BasicLocalModel


class LanguageExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_language(self, text: str) -> str:
        return self.llm.extract_language(text)
