"""
Prompt组装模块
功能：将系统提示词、检索到的企业信息、简历文本组装为LLM可识别的Prompt
"""
import os
import sys
from pathlib import Path
from typing import List, Dict

from .config import REFERENCE_DATE, SYSTEM_PROMPT_FILE


def reference_date_iso() -> str:
    """配置中的参考日期，ISO 字符串（用于 Prompt）。"""
    if hasattr(REFERENCE_DATE, "isoformat"):
        return REFERENCE_DATE.isoformat()
    return str(REFERENCE_DATE)


def inject_reference_into_prompt_text(text: str) -> str:
    """替换系统提示中的 {{REFERENCE_DATE}} 占位符。"""
    return text.replace("{{REFERENCE_DATE}}", reference_date_iso())


def temporal_context_block() -> str:
    """写入用户消息：参考日期、时效与在职/全职适配约束。"""
    d = reference_date_iso()
    return (
        "=== 时效性与参考日期 ===\n"
        f"本次分析的**参考日期（视为「当前」）**：{d}\n"
        "请在该日期下自洽地表述经历年限、时效性判断；不得编造附件与简历未给出的动态事实。\n"
        "请结合简历文字判断候选人当前工作状态（在职、离职、自由职业、创业、待业等）。"
        "若有企业明确要求全职到岗或全职高管稳定性，请明确标注候选人是否可能适配该类需求；"
        "若信息不足请说明「附件中未提供」。\n"
    )


def build_matching_user_content(resume_text: str, enterprises: List[Dict]) -> str:
    """
    匹配报告用户消息正文（与 MiMo chat 共用，避免 llm_client 与 prompt_builder 分叉）。
    """
    enterprise_info = format_enterprise_info(enterprises)
    return f"""
请根据以下人才简历和候选企业信息，进行精准匹配分析。

{temporal_context_block()}

=== 人才简历 ===
{resume_text}

=== 候选企业信息 ===
{enterprise_info}

=== 要求 ===
请严格按照系统提示词中的Constraints和Output Format要求输出匹配报告。
注意：
1. 企业信息来源于附件《沃咨企业库.xlsx》
2. 若某字段为空，标注"附件中未提供"
3. 输出8-15家企业（高度匹配优先，不足时用潜在匹配/行业相关补齐）
""".strip()


def load_system_prompt(file_path: str = None) -> str:
    """
    读取系统提示词模板
    
    Args:
        file_path: 系统提示词文件路径，默认使用config中的路径
        
    Returns:
        str: 系统提示词完整文本
    """
    file_path = file_path or SYSTEM_PROMPT_FILE
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"系统提示词文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = inject_reference_into_prompt_text(content)
    print(f"✅ 已加载系统提示词: {file_path}")
    return content


def format_enterprise_info(enterprises: List[Dict]) -> str:
    """
    将检索到的企业信息格式化为文本（用于填入Prompt）
    
    Args:
        enterprises: 企业列表（来自检索模块）
        
    Returns:
        str: 格式化后的企业信息文本
    """
    if not enterprises:
        return "（未检索到相关企业）"
    
    lines = []
    lines.append(f"共检索到 {len(enterprises)} 家企业：\n")
    
    for i, e in enumerate(enterprises, 1):
        metadata = e.get("metadata", {})
        
        # 企业基本信息
        lines.append(f"{i}. {metadata.get('企业名称', '（未知）')}")
        lines.append(f"   - 所在地区：{metadata.get('省', '')}{metadata.get('市', '')}{metadata.get('区/县', '')}")
        lines.append(f"   - 一级领域：{metadata.get('一级领域', '附件中未提供')}")
        lines.append(f"   - 二级领域：{metadata.get('二级领域', '附件中未提供')}")
        lines.append(f"   - 企业主要产品：{metadata.get('企业主要产品', '附件中未提供')}")
        
        # 如果有匹配得分，也显示
        if "score" in e:
            lines.append(f"   - 匹配得分：{e['score']}/100（综合分，含重排与规则）")
        rs = e.get("ranking_reasons") or []
        if rs:
            lines.append(f"   - 排序要点：{'；'.join(str(x) for x in rs[:4])}")
        
        lines.append("")  # 空行分隔
    
    return "\n".join(lines)


def build_prompt(system_prompt: str, 
                 resume_text: str, 
                 enterprises: List[Dict]) -> List[Dict]:
    """
    组装完整的Prompt（适用于OpenAI API格式）
    
    Args:
        system_prompt: 系统提示词
        resume_text: 简历纯文本
        enterprises: 检索到的企业列表
        
    Returns:
        List[Dict]: OpenAI API格式的messages列表
    """
    ref_note = f"\n（系统已给定参考日期：{reference_date_iso()}，输出中的时间表述须与此一致。）\n"
    system_effective = system_prompt.rstrip() + ref_note

    user_content = build_matching_user_content(resume_text, enterprises)
    
    messages = [
        {"role": "system", "content": system_effective},
        {"role": "user", "content": user_content},
    ]
    
    return messages


def build_prompt_for_mimo(system_prompt: str,
                          resume_text: str,
                          enterprises: List[Dict]) -> List[Dict]:
    """
    为MiMo-V2.5-Pro API组装Prompt（格式可能与OpenAI略有不同）
    
    Args:
        system_prompt: 系统提示词
        resume_text: 简历纯文本
        enterprises: 检索到的企业列表
        
    Returns:
        List[Dict]: MiMo API格式的messages列表
    """
    # MiMo API通常与OpenAI格式兼容，但可能需要调整
    # 这里假设与OpenAI格式一致
    return build_prompt(system_prompt, resume_text, enterprises)


def save_prompt_example(messages: List[Dict], output_path: str = "data/prompt_example.json"):
    """
    保存Prompt示例（用于调试）
    
    Args:
        messages: Prompt消息列表
        output_path: 输出文件路径
    """
    import json
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Prompt示例已保存: {output_path}")


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("=" * 60)
    print("测试Prompt组装模块")
    print("=" * 60)
    
    # 1. 加载系统提示词
    system_prompt = load_system_prompt()
    print(f"\n系统提示词长度: {len(system_prompt)} 字符")
    print(f"前200字符: {system_prompt[:200]}...")
    
    # 2. 测试企业信息格式化
    test_enterprises = [
        {
            "metadata": {
                "企业名称": "测试企业A",
                "省": "江苏省",
                "市": "苏州市",
                "区/县": "太仓市",
                "一级领域": "4. 生物医药技术",
                "二级领域": "4.1 现代医药 - 化学",
                "企业主要产品": "化学原料药、制剂"
            },
            "score": 85.5
        },
        {
            "metadata": {
                "企业名称": "测试企业B",
                "省": "江苏省",
                "市": "苏州市",
                "区/县": "",
                "一级领域": "3. 半导体技术",
                "二级领域": "3.2 半导体制造",
                "企业主要产品": "SiC MOSFET芯片"
            },
            "score": 72.3
        }
    ]
    
    print("\n=== 测试企业信息格式化 ===")
    formatted = format_enterprise_info(test_enterprises)
    print(formatted)
    
    # 3. 测试完整Prompt组装
    test_resume = "张三，博士，研究方向：生物医药，化学制药..."
    messages = build_prompt(system_prompt, test_resume, test_enterprises)
    
    print("\n=== 测试Prompt组装 ===")
    print(f"Messages数量: {len(messages)}")
    print(f"System Prompt长度: {len(messages[0]['content'])}")
    print(f"User Prompt长度: {len(messages[1]['content'])}")
    
    # 4. 保存示例
    save_prompt_example(messages)
    
    print("\n✅ Prompt组装模块测试完成")
