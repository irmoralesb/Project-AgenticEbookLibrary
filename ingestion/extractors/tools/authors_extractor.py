from llm_models.basic_models import BasicLocalModel


class AuthorsExtractor():
    def __init__(self, llm: BasicLocalModel) -> None:
        self.llm = llm

    def get_authors(self, texts: list[str]) -> list[str]:
        
        for text_range in texts:
            authors = self.llm.extract_authors(text_range).authors
            if len(authors) > 0:
                return authors
        return []
