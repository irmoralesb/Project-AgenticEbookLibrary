from llm_models.basic_models import BasicLocalModel
from extractors.models.models import QueryEbookMetadata


class PdfMetadataExtractor():
    def __init__(self, llm: BasicLocalModel):
        self.llm = llm

    def get_metadata(self, pdf_content: str, file_name: str = "") -> QueryEbookMetadata:
        return self.llm.extract_metadata_from_text(pdf_content, file_name)
