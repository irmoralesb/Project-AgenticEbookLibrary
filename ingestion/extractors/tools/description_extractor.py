from llm_models.basic_models import BasicLocalModel


class DescriptionExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_description(self, text: str) -> str | None:
        return self.llm.extract_description(text)
