"""断言单次匹配路径只触发一次企业检索。"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from src.pipeline import iter_match_stream_events, run_match_single_pass


def _fake_enterprises() -> list[dict]:
    return [{"metadata": {"企业名称": "测试企业"}, "score": 72.0}]


@patch.dict(os.environ, {"RERANK_ENABLED": "0"}, clear=False)
@patch("src.pipeline._write_word_and_json")
@patch("src.pipeline.build_enterprise_searcher")
def test_run_match_single_pass_search_once(mock_build: MagicMock, mock_write: MagicMock) -> None:
    search = MagicMock()
    search.search_with_expansion.return_value = _fake_enterprises()
    mock_build.return_value = search
    mock_write.return_value = (r"C:\tmp\out.docx", r"C:\tmp\out.json")

    run_match_single_pass(
        "简历文本示例",
        top_k=5,
        output_file=r"C:\tmp\out.docx",
        use_llm=False,
        use_llm_for_profile=False,
    )

    assert search.search_with_expansion.call_count == 1


@patch.dict(os.environ, {"RERANK_ENABLED": "0"}, clear=False)
@patch("src.pipeline._write_word_and_json")
@patch("src.pipeline.build_enterprise_searcher")
def test_iter_match_stream_events_search_once(mock_build: MagicMock, mock_write: MagicMock) -> None:
    search = MagicMock()
    search.search_with_expansion.return_value = _fake_enterprises()
    mock_build.return_value = search
    mock_write.return_value = (r"C:\tmp\stream.docx", r"C:\tmp\stream.json")

    list(
        iter_match_stream_events(
            resume_text="简历",
            top_k=3,
            output_file=r"C:\tmp\stream.docx",
            use_llm=False,
            use_llm_for_profile=False,
        )
    )

    assert search.search_with_expansion.call_count == 1
