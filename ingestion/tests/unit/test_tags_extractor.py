from extractors.models.models import QueryTags
from extractors.tools.tags_extractor import TagsExtractor
class _FakeLLM:
    def __init__(self, sequence: list[QueryTags]) -> None:
        self._sequence = list(sequence)
    def extract_tags(self, **_kwargs) -> QueryTags:
        return self._sequence.pop(0)
def test_returns_after_first_window_when_enough_tags():
    fake = _FakeLLM([QueryTags(tags=["FastAPI", "Pydantic", "Async IO", "Pytest"])])
    extractor = TagsExtractor(llm=fake)  # type: ignore[arg-type]
    tags = extractor.get_tags(
        ["window-1", "window-2"],
        title="X",
        description="Y",
        category="Programming",
        subcategory="Python",
    )
    assert tags == ["fastapi", "pydantic", "async-io", "pytest"]
def test_drops_tags_equal_to_category():
    fake = _FakeLLM([QueryTags(tags=["Programming", "Python", "Asyncio"])])
    extractor = TagsExtractor(llm=fake)  # type: ignore[arg-type]
    tags = extractor.get_tags(
        ["w"], title="X", description=None,
        category="Programming", subcategory="Python",
    )
    assert "programming" not in tags
    assert "python" not in tags
    assert tags == ["asyncio"]
def test_uses_second_window_when_first_is_insufficient():
    # First window yields only 2 tags — below TagsExtractor._MIN_TAGS_TO_ACCEPT (3).
    # The extractor must move on to the second window and merge results, not
    # short-circuit after the first window.
    fake = _FakeLLM([
        QueryTags(tags=["Python", "FastAPI"]),
        QueryTags(tags=["Pydantic", "Async IO", "Pytest"]),
    ])
    extractor = TagsExtractor(llm=fake)  # type: ignore[arg-type]
    tags = extractor.get_tags(
        ["window-1", "window-2"],
        title="X",
        description="Y",
        category=None,
        subcategory=None,
    )
    assert tags == ["python", "fastapi", "pydantic", "async-io", "pytest"]
    assert fake._sequence == []  # both windows were consumed