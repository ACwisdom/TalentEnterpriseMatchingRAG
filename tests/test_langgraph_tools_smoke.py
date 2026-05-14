from pydantic import TypeAdapter

from langgraph_tools.models import CandidateDto, PagedResponse


def test_paged_response_parse_empty():
    raw = {
        "items": [],
        "page": {"number": 0, "size": 20, "totalElements": 0, "totalPages": 0},
    }
    page = TypeAdapter(PagedResponse[CandidateDto]).validate_python(raw)
    assert page.items == []
    assert page.page.totalElements == 0


def test_example_graph_importable():
    import langgraph_tools.example_graph as eg  # noqa: PLC0415

    assert callable(eg.build_example_graph)
