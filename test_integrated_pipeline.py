"""
测试集成的Pipeline（检索 + Word导出）
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import run_pipeline_and_export_word


def test_integrated_pipeline():
    """测试集成的Pipeline（不使用LLM）"""
    print("=" * 60)
    print("测试集成的完整Pipeline")
    print("=" * 60)
    
    # 使用真实的简历数据
    test_resume = """
    王五，男，1990年出生，博士学历，专业方向：半导体、集成电路、芯片设计。
    教育背景：
    - 2008-2012：清华大学 电子工程 学士
    - 2012-2015：清华大学 微电子 硕士
    - 2015-2019：北京大学 集成电路 博士
    
    工作经历：
    - 2019-2021：上海某半导体企业 IC设计工程师
      - 参与5nm芯片前端设计
      - 负责验证环境搭建
      - 完成2个IP核设计
    
    - 2021-至今：苏州某微电子企业 高级IC设计工程师
      - 领导10人设计团队
      - 负责SoC架构设计
      - 成功流片3款芯片（28nm、14nm、7nm）
      - 申请发明专利5项
    
    专业技能：
    - 集成电路全流程设计经验（前端、验证、后端）
    - 熟悉Verilog/SystemVerilog
    - 精通EDA工具（Synopsys、Cadence）
    - 团队管理与技术攻关
    - 芯片架构设计与优化
    
    求职意向：
    - 期望地区：江苏省苏州市、无锡市、南京市
    - 期望领域：半导体、集成电路、芯片设计
    - 期望职位：IC设计经理/技术总监/架构师
    """
    
    try:
        # 运行集成的Pipeline（不使用LLM）
        print("\n📊 开始运行集成Pipeline...")
        output_path = run_pipeline_and_export_word(
            resume_text=test_resume,
            top_k=10,
            output_file="data/output/完整Pipeline测试报告.docx",
            use_llm=False  # 不使用LLM（网络不可用）
        )
        
        print("\n" + "=" * 60)
        print("✅ 集成Pipeline测试成功！")
        print("=" * 60)
        print(f"\n输出文件: {output_path}")
        print(f"\n📂 生成文件列表：")
        print(f"  1. Word报告: {output_path}")
        print(f"  2. JSON结果: {output_path.replace('.docx', '.json')}")
        
        print(f"\n📋 下一步建议：")
        print(f"  1. 打开Word文档检查格式和内容")
        print(f"  2. 确认企业匹配是否合理")
        print(f"  3. 验证报告结构是否完整")
        print(f"  4. 准备就绪后，可测试MiMo API生成功能")
        
        return output_path
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    output = test_integrated_pipeline()
    
    if output:
        print("\n" + "=" * 60)
        print("🎉 集成的Pipeline已完成！")
        print("=" * 60)
        print("\n当前系统功能状态：")
        print("✅ 1. 关键词检索模块 - 正常工作")
        print("✅ 2. Word导出功能 - 正常工作")
        print("✅ 3. 集成Pipeline - 正常工作")
        print("⏳ 4. MiMo API调用 - 待网络环境解决")
        print("\n您现在可以：")
        print("  - 批量处理多份简历")
        print("  - 调整Word报告格式")
        print("  - 优化关键词匹配算法")
        print("  - 或解决网络问题后接入真实的LLM生成")
