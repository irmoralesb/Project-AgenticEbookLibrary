from fitz import Document


class PageCounterExtractor():

    def get_total_page_number(self, pdf_file: Document) -> str:
        return len(pdf_file)
