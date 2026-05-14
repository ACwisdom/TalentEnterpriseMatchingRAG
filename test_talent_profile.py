"""
测试人才画像LLM生成功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_talent_profile_generation():
    """测试人才画像生成功能"""
    print("=" * 60)
    print("测试人才画像LLM生成功能")
    print("=" * 60)
    
    # 测试简历文本
    test_resume = """
    王明华，男，1985年出生，博士学历，专业方向：半导体、集成电路。
    
    教育背景：
    - 2008-2012：复旦大学 微电子 学士
    - 2012-2015：复旦大学 集成电路 硕士
    - 2015-2019：清华大学 电子工程 博士
    
    工作经历：
    - 2019-2022：上海华虹集团 IC设计工程师
      - 参与28nm工艺芯片前端设计
      - 负责验证环境搭建与调试
      - 完成3个IP核设计项目
    
    - 2022-至今：苏州纳芯微电子 高级IC设计工程师
      - 领导8人设计团队
      - 负责SoC架构设计与优化
      - 成功流片2款芯片（14nm、7nm）
      - 申请发明专利3项
      - 发表EI论文5篇
    
    专业技能：
    - 集成电路全流程设计（前端设计、验证、后端实现）
    - 熟悉Verilog/SystemVerilog HDL
    - 精通Synopsys EDA工具（VCS、DC、ICC2）
    - 芯片架构设计与功耗优化
    - 团队管理与技术攻关
    
    求职意向：
    - 期望地区：江苏省苏州市、无锡市、南京市
    - 期望领域：半导体、集成电路、芯片设计
    - 期望职位：IC设计经理/技术总监/首席架构师
    """
    
    # 测试1: 测试 generate_talent_profile 方法
    print("\n[测试1] 测试 llm_client.generate_talent_profile()...")
    try:
        from src.llm_client import build_mimo_client
        
        client = build_mimo_client()
        
        print("  正在调用LLM生成人才画像...")
        talent_profile = client.generate_talent_profile(test_resume)
        
        print(f"  ✅ 人才画像生成成功（{len(talent_profile)} 字符）")
        print(f"\n  生成的人才画像预览（前500字符）:")
        print("-" * 60)
        print(talent_profile[:500] + "..." if len(talent_profile) > 500 else talent_profile)
        print("-" * 60)
        
    except Exception as e:
        print(f"  ⚠️ LLM调用失败: {str(e)}")
        print("  （这可能是因为API密钥未配置或网络不可用）")
        talent_profile = None
    
    # 测试2: 测试 run_pipeline_and_generate_report  with use_llm_for_profile
    print("\n[测试2] 测试 pipeline.run_pipeline_and_generate_report()...")
    try:
        from src.pipeline import run_pipeline_and_generate_report
        
        print("  正在生成报告（使用LLM生成人才画像）...")
        report = run_pipeline_and_generate_report(
            resume_text=test_resume,
            top_k=5,
            use_llm_for_profile=True
        )
        
        print(f"  ✅ 报告生成成功（{len(report)} 字符）")
        print(f"\n  报告预览（前500字符）:")
        print("-" * 60)
        print(report[:500] + "..." if len(report) > 500 else report)
        print("-" * 60)
        
    except Exception as e:
        print(f"  ⚠️ 报告生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 测试3: 测试 Word 导出 with talent_profile
    print("\n[测试3] 测试 word_exporter.create_matching_report()...")
    try:
        from src.word_exporter import WordExporter
        
        # 先检索企业
        from src.vector_store import build_keyword_searcher
        searcher = build_keyword_searcher()
        enterprises = searcher.search_with_expansion(test_resume, top_k=5)
        
        print(f"  检索到 {len(enterprises)} 家企业")
        
        # 导出Word（传入LLM生成的人才画像）
        exporter = WordExporter()
        output_path = exporter.create_matching_report(
            resume_text=test_resume,
            enterprises=enterprises,
            output_path="data/output/test_talent_profile.docx",
            talent_profile=talent_profile
        )
        
        print(f"  ✅ Word文档已保存: {output_path}")
        
    except Exception as e:
        print(f"  ⚠️ Word导出失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_talent_profile_generation()
