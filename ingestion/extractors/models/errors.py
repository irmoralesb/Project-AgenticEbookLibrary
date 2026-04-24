class PdfExtractionError(Exception):
    def __init__(self, message: str, *, file_name: str, stage: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.file_name = file_name
        self.stage = stage
        self.__cause__ = cause


class PfdOpenError(PdfExtractionError):
    pass


class PdfReadError(PdfExtractionError):
    pass


class MetadataEnrichmentError(PdfExtractionError):
    pass
