from textwrap import dedent
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import content
from extractors.models.models import QueryEbookMetadata, QueryTitleWithEdition


class BasicLocalModel():
    def __init__(self, url: str, model_name: str, temperature: float = 0) -> None:
        self.url = url
        self.model_name = model_name
        self.temperature = temperature
        self.llm = ChatOllama(
            model=model_name,
            base_url=url,
            temperature=temperature,
            reasoning=False,
        )

    def extract_title_and_edition(self, file_name: str) -> QueryTitleWithEdition:

        system_message = dedent("""
            Goal: Extract title and edition from a PDF file name.

            Rules:
            1) Output must be a single valid JSON object with exactly two fields:
               - "title": string
               - "edition": string
            2) Do not include markdown fences, comments, or extra text.
            3) Use only the file name, not directories.
            4) Normalize separators (_,-,.) into readable spaces when appropriate.
            5) Keep connectors like "and", "or", "for" as words when part of the title.
            6) If no edition exists, set "edition" to "Not Specified".
            7) If you cannot infer a meaningful title, set "title" to "N/A".

            Examples:

            Input: this_is_a_book.pdf
            Output: {{"title":"This Is a Book","edition":"Not Specified"}}

            Input: thisisabook2nded.pdf
            Output: {{"title":"This Is a Book","edition":"2nd Edition"}}

            Input: thisisabookforaithird_ed.pdf
            Output: {{"title":"This Is a Book for AI","edition":"3rd Edition"}}
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", "{text_to_parse}")
        ])

        structured_output = self.llm.with_structured_output(
            QueryTitleWithEdition, method="json_schema")

        chain = prompt | structured_output

        ai_message = chain.invoke({"text_to_parse": file_name})
        return ai_message

    def extract_metadata_from_text(self, pdf_document: str, file_name: str = "") -> QueryEbookMetadata:
        system_message = dedent("""
            You extract bibliographic metadata from the first pages of a technical
            ebook PDF. The input is the raw text concatenation of pages 1..N and may
            contain headers, footers, page numbers, and OCR artefacts - ignore them.

            Extract exactly these fields:
            - isbn:        ISBN-10 with format 'X-XXX-XXXXX-X' or ISBN-13 with format 'XXX-X-XXX-XXXXX-X' as printed (keep hyphens). If not present, return null.
            - authors:     list of author names in printed order. They must be in the fist page (cover) on in the first 5 pages If none, return [].
            - year:        integer publication or copyright year. If not present, return null.
            - description: Many books have a summary about the book in the first pages,
                           your task is to find and store the description in this field, <=2000 chars. If the
                           book contains no summary, synthesize one from the available
                           text. Never return "N/A" here.
            - category:    one of {{Programming, Cloud Services, Architecture, Networking, Databases, AI/ML, Project Management}}.
                           If none applies, return "Other".
            - subcategory: a narrower topic matching the chosen category (see pairs below).
                           If none applies, return "Other".
            - publisher:   e.g. "O'Reilly", "Apress", "Microsoft Press". If unknown, return "Unknown".
            - language:    ISO-639-1 code ("en", "es", ...). Default to "en" if unclear.

            Example of Allowed (category, subcategory) pairs:
            - AI/ML          -> LLM, Machine Learning, Data Science, Agents, ML Models
            - Programming    -> C#, Python, JavaScript, TypeScript, Go, Rust, Java
            - Cloud Services -> Azure, AWS, GCP
            - Architecture   -> Azure Architecture, Domain Driven Design, Microservices
            - Networking     -> Firewall, Routing
            - Databases      -> MS SQL, PostgreSQL, MongoDB

            Rules:
            - Output ONLY the JSON object that matches the schema.
            - Do not invent data. Prefer null/[] over guessing for isbn, authors, year.
            - Use exactly the spelling of the allowed category/subcategory values.
            """).strip()

        human_message = dedent("""
            File name: {file_name}
            Below is the raw text extracted from the first pages of the PDF.
            Extract the metadata as instructed.

            -----BEGIN PDF TEXT-----
            {ebook}
            -----END PDF TEXT-----
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])

        structured_output = self.llm.with_structured_output(
            QueryEbookMetadata,
            method="json_schema",
        )
        chain = prompt | structured_output

        ai_message = chain.invoke({
            "ebook": pdf_document,
            "file_name": file_name,
        })
        return ai_message
