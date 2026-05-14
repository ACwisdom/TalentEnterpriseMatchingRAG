"""
完整Pipeline脚本：简历 → 企业匹配 → Prompt生成
功能：1) 关键词检索企业 2) 组装Prompt 3) 保存结果到文件
"""

import os
import sys
from pathlib import Path
import json

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Any, Dict, Iterator, List, NamedTuple, Optional

from src.config import OUTPUT_DIR, SYSTEM_PROMPT_FILE
from src.enterprise_search import build_enterprise_searcher
from src.llm_client import build_mimo_client
from src.match_constraints import MatchConstraints
from src.match_rerank import compute_wide_recall_top_n, match_score_thresholds, rerank_enterprises
from src.prompt_builder import build_prompt, format_enterprise_info, load_system_prompt
from src.word_exporter import WordExporter


def retrieve_and_rerank(
    resume_text: str,
    top_k: int,
    constraints: Optional[MatchConstraints] = None,
    searcher: Any = None,
) -> tuple[List[dict], Dict[str, Any]]:
    """
    扩大召回后重排并截断为 top_k。返回 (enterprises, ranking_meta)。
    """
    c = constraints or MatchConstraints.empty()
    wide_n = compute_wide_recall_top_n(top_k)
    if searcher is None:
        searcher = build_enterprise_searcher()
    candidates = searcher.search_with_expansion(resume_text, top_k=wide_n)
    meta: Dict[str, Any] = {
        "recall_pool_size": len(candidates),
        "wide_recall_top_n": wide_n,
    }
    enterprises, rmeta = rerank_enterprises(resume_text, candidates, top_k, c)
    meta.update(rmeta)
    return enterprises, meta


def format_report_markdown(
    resume_text: str,
    enterprises: List[dict],
    talent_profile: Optional[str] = None,
) -> str:
    """
    基于已检索的 enterprises 生成本地 Markdown 风格报告（不再次检索）。
    与 run_pipeline_and_generate_report 中「检索之后」的拼装逻辑一致。
    """
    report_lines: List[str] = []
    report_lines.append("# 人才-企业匹配报告")
    report_lines.append("")
    report_lines.append("## 📋 人才画像摘要")
    report_lines.append("")
    if talent_profile:
        report_lines.append(talent_profile)
    else:
        report_lines.append(resume_text[:500] + "..." if len(resume_text) > 500 else resume_text)
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## 🏢 企业匹配结果")
    report_lines.append("")
    report_lines.append(f"**检索概况**：共匹配 **{len(enterprises)}** 家企业")
    report_lines.append("")
    report_lines.append("**数据来源**：附件《沃咨企业库.xlsx》")
    report_lines.append("")
    hi, mid = match_score_thresholds()
    report_lines.append(
        f"> 分档阈值（综合分，可由环境变量 MATCH_SCORE_HIGH / MATCH_SCORE_MID 调整）：高度 ≥{hi}；潜在 {mid}～{hi}；拓展 <{mid}。"
    )
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    high_match = [e for e in enterprises if e.get("score", 0) >= hi]
    potential_match = [e for e in enterprises if mid <= e.get("score", 0) < hi]
    related = [e for e in enterprises if e.get("score", 0) < mid]

    if high_match:
        report_lines.append("### ✅ 高度匹配企业（优先推荐）")
        report_lines.append("")
        for i, e in enumerate(high_match, 1):
            metadata = e.get("metadata", {})
            report_lines.append(f"{i}、{metadata.get('企业名称', '（未知）')}")
            report_lines.append("| 项目 | 内容 |")
            report_lines.append("|------|------|")
            report_lines.append(f"| 匹配度评分 | {e.get('score', 0)}/100 |")
            report_lines.append(
                f"| 所在地区 | {metadata.get('省', '')}{metadata.get('市', '')}{metadata.get('区/县', '')} |"
            )
            report_lines.append(f"| 地区门槛 | {metadata.get('地区门槛', '附件中未提供')} |")
            report_lines.append(f"| 一级领域 | {metadata.get('一级领域', '附件中未提供')} |")
            report_lines.append(f"| 二级领域 | {metadata.get('二级领域', '附件中未提供')} |")
            report_lines.append(f"| 企业主要产品 | {metadata.get('企业主要产品', '附件中未提供')} |")
            report_lines.append("")
            report_lines.append("**人才与企业匹配点**：")
            report_lines.append(f"1. 关键词匹配：{', '.join(e.get('matched_keywords', [])[:5])}")
            report_lines.append("2. 领域契合度高")
            report_lines.append("")
            report_lines.append("**信息来源**：✅ 附件《沃咨企业库.xlsx》")
            report_lines.append("")
            report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            report_lines.append("")

    if potential_match:
        report_lines.append("### ⚠️ 潜在匹配企业（可考虑）")
        report_lines.append("")
        for i, e in enumerate(potential_match, len(high_match) + 1):
            metadata = e.get("metadata", {})
            report_lines.append(f"{i}、{metadata.get('企业名称', '（未知）')}")
            report_lines.append("| 项目 | 内容 |")
            report_lines.append("|------|------|")
            report_lines.append(f"| 匹配度评分 | {e.get('score', 0)}/100 |")
            report_lines.append(f"| 所在地区 | {metadata.get('省', '')}{metadata.get('市', '')} |")
            report_lines.append(f"| 一级领域 | {metadata.get('一级领域', '附件中未提供')} |")
            report_lines.append(f"| 二级领域 | {metadata.get('二级领域', '附件中未提供')} |")
            report_lines.append(f"| 企业主要产品 | {metadata.get('企业主要产品', '附件中未提供')} |")
            report_lines.append("")
            report_lines.append("**协同空间说明**：领域相关，可进一步了解")
            report_lines.append("")
            report_lines.append("**信息来源**：✅ 附件《沃咨企业库.xlsx》")
            report_lines.append("")
            report_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            report_lines.append("")

    if related:
        report_lines.append("### 🔶 行业相关企业（拓展参考）")
        report_lines.append("")
        for i, e in enumerate(related, len(high_match) + len(potential_match) + 1):
            metadata = e.get("metadata", {})
            report_lines.append(f"{i}、{metadata.get('企业名称', '（未知）')}")
            report_lines.append("| 项目 | 内容 |")
            report_lines.append("|------|------|")
            report_lines.append(f"| 匹配度评分 | {e.get('score', 0)}/100 |")
            report_lines.append(f"| 一级领域 | {metadata.get('一级领域', '附件中未提供')} |")
            report_lines.append(f"| 企业主要产品 | {metadata.get('企业主要产品', '附件中未提供')} |")
            report_lines.append("")
            report_lines.append("**参考理由**：行业相关，可作为拓展选项")
            report_lines.append("")
            report_lines.append("**信息来源**：✅ 附件《沃咨企业库.xlsx》")
            report_lines.append("")

    report_lines.append("## 📊 匹配总结")
    report_lines.append("")
    report_lines.append("| 指标 | 数值 |")
    report_lines.append("|------|------|")
    report_lines.append(f"| 高度匹配 | {len(high_match)} 家 |")
    report_lines.append(f"| 潜在匹配 | {len(potential_match)} 家 |")
    report_lines.append(f"| 行业相关 | {len(related)} 家 |")
    report_lines.append(f"| **合计** | **{len(enterprises)} 家** |")
    report_lines.append("")
    report_lines.append(
        "> ⚠️ 以上企业信息均来源于附件《沃咨企业库.xlsx》，建议在正式接触前进一步核实最新情况。"
    )
    report_lines.append("> 注：附件中未提供的字段已标注'附件中未提供'，未编造任何信息。")

    return "\n".join(report_lines)


def _resolve_talent_profile(
    resume_text: str,
    use_llm_for_profile: bool,
    wechat_screenshots: Optional[List[str]],
    use_advanced_profile: bool,
) -> tuple[Optional[str], bool]:
    """
    高级 / 基础 LLM 人才画像（不检索）。返回 (talent_profile, is_advanced_profile)。
    """
    talent_profile: Optional[str] = None
    is_advanced = False

    if use_advanced_profile and wechat_screenshots:
        print("\n[1.5/3] 正在生成高级人才画像（结合简历+微信截图）...")
        try:
            client = build_mimo_client()
            print(f"   📸 正在分析 {len(wechat_screenshots)} 张微信截图...")
            wechat_analysis = client.analyze_wechat_screenshots(wechat_screenshots)
            print(f"   ✅ 微信截图分析完成（{len(wechat_analysis)} 字符）")
            print("   🧠 正在生成高级人才画像...")
            talent_profile = client.generate_advanced_talent_profile(
                resume_text=resume_text,
                wechat_analysis=wechat_analysis,
            )
            is_advanced = True
            print(f"   ✅ 高级人才画像生成完成（{len(talent_profile)} 字符）")
        except Exception as e:
            print(f"⚠️ 高级人才画像生成失败，降级为基础版: {str(e)}")

    if talent_profile is None and use_llm_for_profile:
        print("\n[1.5/3] 正在调用MiMo API生成人才画像摘要...")
        try:
            client = build_mimo_client()
            talent_profile = client.generate_talent_profile(resume_text)
            print(f"✅ 人才画像摘要生成完成（{len(talent_profile)} 字符）")
        except Exception as e:
            print(f"⚠️ 人才画像生成失败，使用默认方式: {str(e)}")

    return talent_profile, is_advanced


class MatchSinglePassResult(NamedTuple):
    word_path: str
    report_preview_text: str
    enterprises: List[dict]
    json_path: str
    report_content: str
    talent_profile: Optional[str]
    is_advanced_profile: bool
    use_llm: bool
    ranking_meta: Optional[Dict[str, Any]] = None


def run_pipeline(resume_text: str, 
                 top_k: int = 15,
                 output_file: str = None) -> dict:
    """
    运行完整Pipeline：简历 → 企业匹配 → Prompt生成
    
    Args:
        resume_text: 简历纯文本
        top_k: 返回企业数量
        output_file: 输出文件路径（可选）
        
    Returns:
        dict: 包含检索结果和Prompt的字典
    """
    print("=" * 60)
    print("开始运行匹配Pipeline")
    print("=" * 60)
    
    # ============ 第一步：关键词检索 ============
    print("\n[1/3] 正在检索匹配企业...")
    enterprises, _rank_meta = retrieve_and_rerank(resume_text, top_k, None)

    print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
    
    # ============ 第二步：加载系统提示词 ============
    print("\n[2/3] 正在加载系统提示词...")
    system_prompt = load_system_prompt()
    print(f"✅ 系统提示词已加载（{len(system_prompt)} 字符）")
    
    # ============ 第三步：组装Prompt ============
    print("\n[3/3] 正在组装Prompt...")
    messages = build_prompt(system_prompt, resume_text, enterprises)
    print(f"✅ Prompt已组装（{len(messages)} 条消息）")
    
    # ============ 第四步：保存结果 ============
    if output_file is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, "matching_result.json")
    
    result = {
        "resume_text": resume_text,
        "enterprises": enterprises,
        "messages": messages,
        "enterprise_count": len(enterprises)
    }
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 结果已保存: {output_file}")
    
    # ============ 打印摘要 ============
    print("\n" + "=" * 60)
    print("Pipeline执行完成")
    print("=" * 60)
    print(f"检索到企业数量: {len(enterprises)}")
    print(f"Prompt消息数: {len(messages)}")
    print(f"输出文件: {output_file}")
    
    # 打印企业列表
    print("\n匹配企业列表：")
    print("-" * 60)
    for i, e in enumerate(enterprises[:10], 1):  # 只显示前10家
        metadata = e.get("metadata", {})
        print(f"{i}. {metadata.get('企业名称', '（未知）')} (得分: {e.get('score', 0)})")
    
    if len(enterprises) > 10:
        print(f"... 还有 {len(enterprises) - 10} 家企业")
    
    return result


def run_pipeline_and_generate_report(resume_text: str,
                                    top_k: int = 15,
                                    output_file: str = None,
                                    use_llm_for_profile: bool = False,
                                    wechat_screenshots: Optional[List[str]] = None,
                                    use_advanced_profile: bool = False) -> str:
    """
    运行Pipeline并生成格式化的匹配报告（纯文本，可直接保存为Word）
    
    Args:
        resume_text: 简历纯文本
        top_k: 返回企业数量
        output_file: 输出文件路径（可选，支持.json或.txt）
        use_llm_for_profile: 是否使用LLM生成人才画像摘要
        wechat_screenshots: 微信聊天截图路径列表（PNG格式），用于高级人才画像
        use_advanced_profile: 是否使用高级人才画像（结合简历+微信截图）
        
    Returns:
        str: 格式化的匹配报告文本
    """
    print("=" * 60)
    print("开始生成匹配报告")
    print("=" * 60)
    
    # 1. 检索企业
    print("\n[1/3] 正在检索匹配企业...")
    enterprises, _ = retrieve_and_rerank(resume_text, top_k, None)
    print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
    
    talent_profile, _ = _resolve_talent_profile(
        resume_text,
        use_llm_for_profile,
        wechat_screenshots,
        use_advanced_profile,
    )
    
    # 2. 生成报告文本（模拟LLM输出格式）
    print("\n[2/3] 正在生成匹配报告...")
    report_text = format_report_markdown(resume_text, enterprises, talent_profile)
    
    # 保存报告
    if output_file is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, "matching_report.txt")
    
    # 根据文件扩展名决定格式
    if output_file.endswith(".json"):
        # 保存为JSON
        result = {
            "resume_text": resume_text,
            "enterprises": enterprises,
            "report_text": report_text
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        # 保存为文本文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
    
    print(f"✅ 报告已生成: {output_file}")
    print(f"   报告长度: {len(report_text)} 字符")
    
    return report_text


def run_pipeline_with_llm(resume_text: str,
                           top_k: int = 15,
                           output_file: str = None,
                           temperature: float = 0.7) -> str:
    """
    运行完整Pipeline并调用MiMo API生成匹配报告
    
    Args:
        resume_text: 简历纯文本
        top_k: 返回企业数量
        output_file: 输出文件路径（支持.json或.txt）
        temperature: LLM温度参数
        
    Returns:
        str: LLM生成的匹配报告文本
    """
    print("=" * 60)
    print("开始运行完整Pipeline（含LLM生成）")
    print("=" * 60)
    
    # ============ 第一步：检索企业 ============
    print("\n[1/4] 正在检索匹配企业...")
    enterprises, _ = retrieve_and_rerank(resume_text, top_k, None)
    print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
    
    # ============ 第二步：加载系统提示词 ============
    print("\n[2/4] 正在加载系统提示词...")
    system_prompt = load_system_prompt()
    print(f"✅ 系统提示词已加载（{len(system_prompt)} 字符）")
    
    # ============ 第三步：调用MiMo API生成报告 ============
    print("\n[3/4] 正在调用MiMo API生成匹配报告...")
    client = build_mimo_client()
    report_text = client.generate_matching_report(
        system_prompt=system_prompt,
        resume_text=resume_text,
        enterprises=enterprises,
        temperature=temperature
    )
    print(f"✅ 报告生成完成（{len(report_text)} 字符）")
    
    # ============ 第四步：保存结果 ============
    print("\n[4/4] 正在保存结果...")
    if output_file is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, "matching_report_llm.txt")
    
    # 根据文件扩展名决定格式
    if output_file.endswith(".json"):
        # 保存为JSON
        result = {
            "resume_text": resume_text,
            "enterprises": enterprises,
            "report_text": report_text,
            "model": "MiMo-V2.5-Pro"
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    else:
        # 保存为文本文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
    
    print(f"✅ 结果已保存: {output_file}")
    
    # ============ 打印摘要 ============
    print("\n" + "=" * 60)
    print("Pipeline执行完成（含LLM生成）")
    print("=" * 60)
    print(f"检索到企业数量: {len(enterprises)}")
    print(f"报告长度: {len(report_text)} 字符")
    print(f"输出文件: {output_file}")
    
    # 打印企业列表
    print("\n匹配企业列表：")
    print("-" * 60)
    for i, e in enumerate(enterprises[:10], 1):  # 只显示前10家
        metadata = e.get("metadata", {})
        print(f"{i}. {metadata.get('企业名称', '（未知）')} (得分: {e.get('score', 0)})")
    
    if len(enterprises) > 10:
        print(f"... 还有 {len(enterprises) - 10} 家企业")
    
    # 打印报告前500字符
    print("\n" + "=" * 60)
    print("生成的报告预览（前500字符）：")
    print("=" * 60)
    print(report_text[:500] + "..." if len(report_text) > 500 else report_text)
    
    return report_text


def _write_word_and_json(
    resume_text: str,
    enterprises: List[dict],
    report_content: str,
    talent_profile: Optional[str],
    is_advanced_profile: bool,
    output_file: Optional[str],
    use_llm: bool,
    ranking_meta: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """导出 Word 并写 JSON 侧车，返回 (Word 绝对路径, JSON 绝对路径)。"""
    print("\n[3/4] 正在导出Word文档...")
    exporter = WordExporter()
    if output_file is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"人才匹配报告_{timestamp}.docx")

    output_path = exporter.create_matching_report(
        resume_text=resume_text,
        enterprises=enterprises,
        output_path=output_file,
        report_title="人才-企业匹配报告",
        talent_profile=talent_profile,
        is_advanced_profile=is_advanced_profile,
    )
    print(f"✅ Word文档已保存: {output_path}")

    print("\n[4/4] 正在保存检索结果（JSON）...")
    json_file = output_file.replace(".docx", ".json")
    result = {
        "resume_text": resume_text,
        "enterprises": enterprises,
        "report_content": report_content,
        "word_output": output_path,
        "model_used": "MiMo-V2.5-Pro" if use_llm else "格式化数据",
    }
    if ranking_meta:
        result["ranking_meta"] = ranking_meta
    os.makedirs(os.path.dirname(json_file), exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON结果已保存: {json_file}")
    return output_path, json_file


def _mimo_stream_enabled() -> bool:
    return os.getenv("MIMO_USE_STREAM", "1").strip().lower() not in ("0", "false", "no")


def iter_match_stream_events(
    resume_text: str,
    top_k: int,
    output_file: str,
    use_llm: bool,
    use_llm_for_profile: bool,
    wechat_screenshots: Optional[List[str]] = None,
    use_advanced_profile: bool = False,
    constraints: Optional[MatchConstraints] = None,
) -> Iterator[Dict[str, Any]]:
    """
    单次检索 + 可选流式画像/主报告 + Word。yield dict 事件供 SSE。
    """
    yield {"type": "stage", "name": "search"}
    print("=" * 60)
    print("流式匹配 Pipeline")
    print("=" * 60)
    print("\n[1/4] 正在检索匹配企业...")
    enterprises, ranking_meta = retrieve_and_rerank(resume_text, top_k, constraints)
    print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
    preview = []
    for e in enterprises[:12]:
        md = e.get("metadata") or {}
        reasons = e.get("ranking_reasons") or []
        preview.append(
            {
                "name": md.get("企业名称", ""),
                "score": e.get("score"),
                "reasons": reasons[:2],
            }
        )
    yield {
        "type": "stage",
        "name": "search_done",
        "enterprise_count": len(enterprises),
        "recall_pool_size": ranking_meta.get("recall_pool_size"),
        "wide_recall_top_n": ranking_meta.get("wide_recall_top_n"),
        "rerank_applied": ranking_meta.get("rerank_applied"),
        "cross_encoder_model": ranking_meta.get("cross_encoder_model"),
        "blend_weights": ranking_meta.get("blend_weights"),
        "constraints": ranking_meta.get("constraints"),
        "ranking_meta": ranking_meta,
        "candidates_preview": preview,
    }

    report_content: Optional[str] = None
    talent_profile: Optional[str] = None
    is_advanced_profile = False

    if use_advanced_profile and wechat_screenshots:
        yield {"type": "stage", "name": "advanced_profile"}
        try:
            client = build_mimo_client()
            wechat_analysis = client.analyze_wechat_screenshots(wechat_screenshots)
            talent_profile = client.generate_advanced_talent_profile(
                resume_text=resume_text,
                wechat_analysis=wechat_analysis,
            )
            is_advanced_profile = True
        except Exception as e:
            yield {"type": "warning", "message": str(e)}

    if talent_profile is None and use_llm_for_profile:
        yield {"type": "stage", "name": "profile_start"}
        try:
            client = build_mimo_client()
            if _mimo_stream_enabled():
                parts: List[str] = []
                for piece in client.generate_talent_profile_stream(resume_text):
                    parts.append(piece)
                    yield {"type": "token", "section": "profile", "delta": piece}
                talent_profile = "".join(parts)
                talent_profile = talent_profile.strip()
                if talent_profile.startswith("```markdown"):
                    talent_profile = talent_profile[11:]
                if talent_profile.startswith("```"):
                    talent_profile = talent_profile[3:]
                if talent_profile.endswith("```"):
                    talent_profile = talent_profile[:-3]
                talent_profile = talent_profile.strip()
            else:
                talent_profile = client.generate_talent_profile(resume_text)
                yield {"type": "token", "section": "profile", "delta": talent_profile}
            yield {"type": "stage", "name": "profile_done"}
        except Exception as e:
            yield {"type": "warning", "message": f"profile: {e}"}

    use_llm_eff = use_llm
    if use_llm_eff:
        yield {"type": "stage", "name": "report_start"}
        try:
            client = build_mimo_client()
            system_prompt = load_system_prompt()
            if _mimo_stream_enabled():
                parts: List[str] = []
                for piece in client.generate_matching_report_stream(
                    system_prompt, resume_text, enterprises
                ):
                    parts.append(piece)
                    yield {"type": "token", "section": "report", "delta": piece}
                report_content = "".join(parts)
            else:
                report_content = client.generate_matching_report(
                    system_prompt=system_prompt,
                    resume_text=resume_text,
                    enterprises=enterprises,
                )
                yield {"type": "token", "section": "report", "delta": report_content}
            yield {"type": "stage", "name": "report_done"}
        except Exception as e:
            yield {"type": "warning", "message": f"report: {e}"}
            use_llm_eff = False

    if not use_llm_eff:
        print("\n[2/4] 正在生成 Markdown 报告预览...")
        report_content = format_report_markdown(resume_text, enterprises, talent_profile)
        yield {"type": "token", "section": "report", "delta": report_content}

    yield {"type": "stage", "name": "word_export"}
    output_path, json_path = _write_word_and_json(
        resume_text,
        enterprises,
        report_content,
        talent_profile,
        is_advanced_profile,
        output_file,
        use_llm_eff,
        ranking_meta=ranking_meta,
    )
    yield {
        "type": "done",
        "word_path": os.path.basename(output_path),
        "word_abs": output_path,
        "json_path": json_path,
        "report_text": report_content,
    }


def run_match_single_pass(
    resume_text: str,
    top_k: int = 10,
    output_file: str = None,
    use_llm: bool = False,
    use_llm_for_profile: bool = False,
    wechat_screenshots: Optional[List[str]] = None,
    use_advanced_profile: bool = False,
    constraints: Optional[MatchConstraints] = None,
) -> MatchSinglePassResult:
    """
    单次企业检索 + 可选 MiMo + Word 导出 + JSON 侧车。
    """
    print("=" * 60)
    print("开始运行完整Pipeline（含Word导出）")
    print("=" * 60)
    
    # ============ 第一步：检索企业 ============
    print("\n[1/4] 正在检索匹配企业...")
    enterprises, ranking_meta = retrieve_and_rerank(resume_text, top_k, constraints)
    print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
    
    # 显示检索到的企业
    print("\n匹配企业列表：")
    print("-" * 60)
    for i, e in enumerate(enterprises[:10], 1):
        metadata = e.get("metadata", {})
        print(f"{i}. {metadata.get('企业名称', '（未知）')} (得分: {e.get('score', 0):.2f})")
    
    if len(enterprises) > 10:
        print(f"... 还有 {len(enterprises) - 10} 家企业")
    
    # ============ 第二步：生成报告内容 ============
    report_content = None
    
    if use_llm:
        # 使用MiMo API生成报告
        print("\n[2/4] 正在调用MiMo API生成报告...")
        try:
            client = build_mimo_client()
            system_prompt = load_system_prompt()
            report_content = client.generate_matching_report(
                system_prompt=system_prompt,
                resume_text=resume_text,
                enterprises=enterprises
            )
            print(f"✅ LLM报告生成完成（{len(report_content)} 字符）")
        except Exception as e:
            print(f"⚠️ LLM调用失败，使用格式化数据代替: {str(e)}")
            use_llm = False
    
    if not use_llm:
        # 使用格式化数据作为报告内容
        print("\n[2/4] 正在生成格式化报告...")
        report_content = format_enterprise_info(enterprises)
        print(f"✅ 格式化报告生成完成（{len(report_content)} 字符）")
    
    talent_profile, is_advanced_profile = _resolve_talent_profile(
        resume_text,
        use_llm_for_profile,
        wechat_screenshots,
        use_advanced_profile,
    )

    if output_file is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"人才匹配报告_{timestamp}.docx")

    json_for_disk = (
        report_content
        if use_llm
        else format_report_markdown(resume_text, enterprises, talent_profile)
    )
    output_path, json_path = _write_word_and_json(
        resume_text,
        enterprises,
        json_for_disk,
        talent_profile,
        is_advanced_profile,
        output_file,
        use_llm,
        ranking_meta=ranking_meta,
    )

    # ============ 打印摘要 ============
    print("\n" + "=" * 60)
    print("✅ Pipeline执行完成（含Word导出）")
    print("=" * 60)
    print(f"检索到企业数量: {len(enterprises)}")
    print(f"Word报告: {output_path}")
    print(f"JSON结果: {json_path}")
    
    # 打印企业分类统计
    hi, mid = match_score_thresholds()
    high_match = len([e for e in enterprises if e.get("score", 0) >= hi])
    potential_match = len([e for e in enterprises if mid <= e.get("score", 0) < hi])
    related = len([e for e in enterprises if e.get("score", 0) < mid])
    
    print(f"\n企业分类统计：")
    print(f"  高度匹配（≥{hi}分）: {high_match} 家")
    print(f"  潜在匹配（{mid}～{hi}分）: {potential_match} 家")
    print(f"  行业相关（<{mid}分）: {related} 家")

    report_preview_text = (
        report_content
        if use_llm
        else format_report_markdown(resume_text, enterprises, talent_profile)
    )

    return MatchSinglePassResult(
        word_path=output_path,
        report_preview_text=report_preview_text,
        enterprises=enterprises,
        json_path=json_path,
        report_content=json_for_disk,
        talent_profile=talent_profile,
        is_advanced_profile=is_advanced_profile,
        use_llm=use_llm,
        ranking_meta=ranking_meta,
    )


def run_pipeline_and_export_word(resume_text: str,
                                  top_k: int = 10,
                                  output_file: str = None,
                                  use_llm: bool = False,
                                  use_llm_for_profile: bool = False,
                                  wechat_screenshots: Optional[List[str]] = None,
                                  use_advanced_profile: bool = False,
                                  constraints: Optional[MatchConstraints] = None) -> str:
    """
    运行完整Pipeline并导出为Word文档
    
    Args:
        resume_text: 简历纯文本
        top_k: 返回企业数量
        output_file: 输出Word文件路径
        use_llm: 是否使用MiMo API生成报告（需要网络）
        use_llm_for_profile: 是否使用LLM生成人才画像摘要（基础版）
        wechat_screenshots: 微信聊天截图路径列表（PNG格式），用于高级人才画像
        use_advanced_profile: 是否使用高级人才画像（结合简历+微信截图）
        
    Returns:
        str: 输出的Word文档路径
    """
    return run_match_single_pass(
        resume_text=resume_text,
        top_k=top_k,
        output_file=output_file,
        use_llm=use_llm,
        use_llm_for_profile=use_llm_for_profile,
        wechat_screenshots=wechat_screenshots,
        use_advanced_profile=use_advanced_profile,
        constraints=constraints,
    ).word_path


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("测试完整Pipeline")
    print("=" * 60)
    
    # 使用测试简历
    test_resume = """
    张三，男，1985年出生，博士学历，专业方向：生物医药、药物研发。
    教育背景：
    - 2008-2012：XX大学 药学 学士
    - 2012-2015：XX大学 药物化学 硕士
    - 2015-2019：XX大学 药学 博士
    
    工作经历：
    - 2019-至今：XX制药企业 高级研究员
      - 负责化学制药工艺开发
      - 参与多个药物研发项目
      - 发表SCI论文10篇
    
    专业技能：
    - 药物研发全流程经验
    - 化学制药工艺优化
    - 生物医药技术转化
    - 项目管理经验丰富
    """
    
    # 运行Pipeline
    result = run_pipeline(test_resume, top_k=10)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
