from llm_models.basic_models import BasicLocalModel


class LanguageExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_language(self, texts: list[str]) -> str:
        for text_range in texts:
            text = self.llm.extract_language(texts)
            if text:
                return text
        return text

