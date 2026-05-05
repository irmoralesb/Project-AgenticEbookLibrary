from llm_models.basic_models import BasicLocalModel


class DescriptionExtractor:
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_description(self, texts: list[str]) -> str | None:
        for text_range in texts:
            description = self.llm.extract_description(text_range)
            if description is not None:
                return description
        return None

