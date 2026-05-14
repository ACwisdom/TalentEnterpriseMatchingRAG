"""
完整测试：使用真实数据测试Word导出功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.vector_store import build_keyword_searcher
from src.word_exporter import WordExporter


def test_word_export_with_real_data():
    """使用真实企业数据测试Word导出"""
    print("=" * 60)
    print("测试Word导出功能（真实数据）")
    print("=" * 60)
    
    try:
        # ============ 第一步：检索企业 ============
        print("\n[1/3] 正在检索匹配企业...")
        searcher = build_keyword_searcher()
        
        # 使用真实的生物医药简历
        test_resume = """
        李四，男，1988年出生，博士学历，专业方向：生物医药、化学制药。
        教育背景：
        - 2006-2010：中国药科大学 药学 学士
        - 2010-2013：中国药科大学 药物化学 硕士
        - 2013-2017：北京大学 药学 博士
        
        工作经历：
        - 2017-2020：上海某生物医药企业 研究员
          - 参与小分子药物研发项目
          - 负责药物合成工艺优化
          - 发表SCI论文3篇
        
        - 2020-至今：苏州某制药企业 高级研究员
          - 领导化学制药工艺开发团队（5人）
          - 负责创新药研发项目管理
          - 申请发明专利2项
          - 发表SCI论文7篇
        
        专业技能：
        - 药物研发全流程经验（小分子药物、化学制药）
        - 化学制药工艺开发与优化
        - 生物医药技术转化与产业化
        - 团队管理与项目协调
        - 精通药物分析、制剂开发
        
        求职意向：
        - 期望地区：江苏省苏州市、南京市、无锡市
        - 期望领域：生物医药、化学制药、创新药研发
        - 期望职位：高级研究员/技术总监/研发经理
        """
        
        enterprises = searcher.search_with_expansion(test_resume, top_k=10)
        print(f"✅ 检索完成，找到 {len(enterprises)} 家匹配企业")
        
        # 显示检索到的企业
        print("\n检索到的企业：")
        print("-" * 60)
        for i, e in enumerate(enterprises, 1):
            metadata = e.get("metadata", {})
            print(f"{i}. {metadata.get('企业名称', '（未知）')} (得分: {e.get('score', 0):.2f})")
        
        # ============ 第二步：初始化Word导出器 ============
        print("\n[2/3] 正在初始化Word导出器...")
        exporter = WordExporter()
        
        # ============ 第三步：导出Word文档 ============
        print("\n[3/3] 正在导出Word文档...")
        output_file = "data/output/匹配报告_生物医药博士.docx"
        output_path = exporter.create_matching_report(
            resume_text=test_resume,
            enterprises=enterprises,
            output_path=output_file,
            report_title="人才-企业匹配报告（生物医药博士）"
        )
        
        print("\n" + "=" * 60)
        print("✅ Word导出测试成功！")
        print("=" * 60)
        print(f"\n输出文件: {output_path}")
        print(f"文件大小: {Path(output_path).stat().st_size} 字节")
        print(f"\n请打开Word文档检查：")
        print("1. 报告格式是否美观")
        print("2. 企业信息是否完整")
        print("3. 表格排版是否正确")
        print("4. 中文字体是否正常显示")
        
        return output_path
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    output = test_word_export_with_real_data()
    
    if output:
        print("\n" + "=" * 60)
        print("📝 后续建议：")
        print("=" * 60)
        print("1. 打开生成的Word文档，检查格式和内容")
        print("2. 如果格式不满意，我可以调整：")
        print("   - 字体、字号")
        print("   - 表格样式")
        print("   - 标题层级")
        print("   - 颜色搭配")
        print("3. 如果内容不完整，我可以添加更多字段")
        print("4. 准备好后可以集成到完整Pipeline中")
