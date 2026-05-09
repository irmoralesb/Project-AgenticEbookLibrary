from textwrap import dedent
from langchain_core.tools import structured
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import content
from extractors.models.models import (
    QueryAuthors,
    QueryCategoryMetadata,
    QueryPublisher,
    QueryTitleWithEdition,
)


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

    def extract_authors(self, book_extract: str) -> QueryAuthors:
        system_message = dedent(
            """
            You are expert finding book data, you work the author or author list of a book in the given text.

            Rules:
            1) The book can have 1 or more authors
            2) They must be stored as they are listed in the text
               2.1) If there is only one author, the name will be next to the book title
            3) Don't invent data, if no authors are found respond with empty list
            """
        )

        human_message = dedent(
            """ 
            Below is the raw text extracted from the first pages of the book.
            Extract the author or author list as instructed.

            -----BEGIN PDF TEXT-----
            {book_extract}
            -----END PDF TEXT-----
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ]
        )

        structured_output = self.llm.with_structured_output(
            QueryAuthors, method="json_schema"
        )

        chain = prompt | structured_output

        ai_message = chain.invoke({"book_extract": book_extract})
        return ai_message

    def extract_publisher(self, book_extract: str) -> QueryPublisher:
        system_message = dedent(
            """
            You extract the publisher (publishing imprint or publishing house) for a book from raw
            text taken from its early pages — copyright pages, title verso, colophon, or similar.

            Rules:
            1) Output must be a single valid JSON object with exactly one field:
               - "publisher": string or null
            2) Do not include markdown fences, comments, or extra text.
            3) Prefer the exact imprint wording as printed in the excerpt when there is clear evidence:
               phrases like "Published by …", copyright lines naming the publisher, or "… Press"
               on the imprint line count. Do not paraphrase when a literal name is visible.
            4) The publisher is the entity that publishes the book, not the author, not only a
               printer, and typically not an ebook retailer or file host unless it is explicitly
               named as the publisher of this edition.
            5) Do not confuse a book series title, slogan, or software product name with the
               publisher. If ambiguous, use null.
            6) "publisher" must be at most 60 characters; truncate only if necessary to stay within
               the limit while keeping the imprint recognizable.
            7) If no publisher is clearly stated in the text, or you would be guessing, set
               "publisher" to null. Do not invent names.
            """
        ).strip()

        human_message = dedent(
            """
            Below is raw text from the early part of the book. Extract the publisher as instructed.

            -----BEGIN PDF TEXT-----
            {book_extract}
            -----END PDF TEXT-----
            """
        ).strip()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                ("human", human_message),
            ]
        )

        structured_output = self.llm.with_structured_output(
            QueryPublisher, method="json_schema"
        )
        chain = prompt | structured_output
        return chain.invoke({"book_extract": book_extract})

    def extract_description(self, text: str) -> str | None:
        system_message = dedent("""
            You are a bibliographic assistant. Your only task is to extract or synthesize
            a description of the book from the raw text of its first pages.

            Rules:
            - Many books include a back-cover blurb or preface summary in the first pages.
              Return it verbatim (truncated to 2000 chars) if found.
            - If no explicit summary exists, synthesize a concise description from the
              available text. Never return "N/A" or an empty string.
            - Output ONLY the description text, no JSON, no labels.
            """).strip()

        human_message = dedent("""
            -----BEGIN PDF TEXT-----
            {text}
            -----END PDF TEXT-----
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"text": text})
        raw = result.content if hasattr(result, "content") else str(result)
        return raw.strip()[:2000] if raw else None

    def extract_category(self, text: str) -> QueryCategoryMetadata:
        system_message = dedent("""
            You assign a category and subcategory for any ebook based on its early content.

            Pick short, library-style labels the reader would recognize: category is the broad shelf;
            subcategory refines it (e.g. category "Programming", subcategory "Rust"; or "Cooking",
            "Italian"). These examples are hints only — invent fitting labels for any topic.

            Rules:
            - Output ONLY the JSON object that matches the schema.
            - Category at most 60 characters; subcategory at most 40.
            - Return "Other" for both fields when you cannot classify confidently.
            """).strip()

        human_message = dedent("""
            -----BEGIN PDF TEXT-----
            {text}
            -----END PDF TEXT-----
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])
        structured_output = self.llm.with_structured_output(
            QueryCategoryMetadata, method="json_schema"
        )
        chain = prompt | structured_output
        return chain.invoke({"text": text})

    def extract_language(self, text: str) -> str:
        system_message = dedent("""
            You detect the written language of a book from a raw text sample.

            Rules:
            - Return ONLY the ISO-639-1 two-letter language code (e.g. "en", "es", "de").
            - Default to "en" when the language is unclear or mixed.
            - Output nothing else — no JSON, no explanation, just the code.
            """).strip()

        human_message = dedent("""
            -----BEGIN PDF TEXT-----
            {text}
            -----END PDF TEXT-----
            """).strip()

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message),
        ])
        chain = prompt | self.llm
        result = chain.invoke({"text": text[:3000]})
        raw = result.content if hasattr(result, "content") else str(result)
        code = raw.strip().lower()[:10]
        return code if code else "en"
