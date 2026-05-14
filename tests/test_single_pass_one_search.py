"""单次检索：run_match_single_pass / Web 路径不得重复 search_with_expansion。"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def fake_enterprises():
    return [
        {
            "score": 72,
            "metadata": {"企业名称": "测A", "省": "浙", "市": "杭", "区/县": "", "地区门槛": "", "一级领域": "x", "二级领域": "y", "企业主要产品": "z"},
            "matched_keywords": ["k1"],
        }
    ]


def test_run_match_single_pass_search_called_once(tmp_path, fake_enterprises, monkeypatch):
    monkeypatch.setenv("RERANK_ENABLED", "0")
    out_docx = tmp_path / "out.docx"

    searcher = MagicMock()
    searcher.search_with_expansion.return_value = fake_enterprises

    with patch("src.pipeline.build_enterprise_searcher", return_value=searcher):
        with patch("src.pipeline._write_word_and_json", return_value=(str(out_docx), str(tmp_path / "out.json"))):
            from src.pipeline import run_match_single_pass

            run_match_single_pass(
                resume_text="测试简历内容",
                top_k=5,
                output_file=str(out_docx),
                use_llm=False,
                use_llm_for_profile=False,
            )

    assert searcher.search_with_expansion.call_count == 1


def test_iter_match_stream_events_search_called_once(tmp_path, fake_enterprises, monkeypatch):
    monkeypatch.setenv("RERANK_ENABLED", "0")
    out_docx = tmp_path / "stream.docx"
    searcher = MagicMock()
    searcher.search_with_expansion.return_value = fake_enterprises

    with patch("src.pipeline.build_enterprise_searcher", return_value=searcher):
        with patch("src.pipeline._write_word_and_json", return_value=(str(out_docx), str(tmp_path / "stream.json"))):
            from src.pipeline import iter_match_stream_events

            list(
                iter_match_stream_events(
                    resume_text="简历",
                    top_k=3,
                    output_file=str(out_docx),
                    use_llm=False,
                    use_llm_for_profile=False,
                )
            )

    assert searcher.search_with_expansion.call_count == 1
