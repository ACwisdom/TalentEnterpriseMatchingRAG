"""
测试关键词检索模块（不依赖网络和LLM）
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.vector_store import build_keyword_searcher
from src.prompt_builder import load_system_prompt, format_enterprise_info


def test_keyword_search():
    """测试关键词检索功能"""
    print("=" * 60)
    print("测试关键词检索模块")
    print("=" * 60)
    
    try:
        # 1. 构建检索器
        print("\n[1/3] 正在加载企业库...")
        searcher = build_keyword_searcher()
        info = searcher.get_info()
        print(f"✅ 检索器初始化成功")
        print(f"   企业数量: {info['企业数量']}")
        print(f"   检索方式: {info['检索方式']}")
        
        # 2. 测试检索功能
        print("\n[2/3] 正在测试检索功能...")
        test_resume = """
        张三，博士，专业方向：生物医药、药物研发。
        教育背景：北京大学药学博士，专注于化学制药工艺开发。
        工作经历：某制药企业高级研究员，负责小分子药物研发。
        """
        
        results = searcher.search(test_resume, top_k=5)
        print(f"✅ 检索成功，找到 {len(results)} 家企业")
        
        # 3. 显示检索结果
        print("\n[3/3] 检索结果：")
        print("-" * 60)
        for i, e in enumerate(results, 1):
            metadata = e.get("metadata", {})
            print(f"\n{i}. {metadata.get('企业名称', '（未知）')}")
            print(f"   匹配得分: {e.get('score', 0)}")
            print(f"   一级领域: {metadata.get('一级领域', 'N/A')}")
            print(f"   二级领域: {metadata.get('二级领域', 'N/A')}")
            print(f"   匹配关键词: {', '.join(e.get('matched_keywords', [])[:5])}")
        
        # 4. 测试企业信息格式化
        print("\n" + "=" * 60)
        print("测试企业信息格式化")
        print("=" * 60)
        formatted = format_enterprise_info(results)
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if test_keyword_search():
        print("\n" + "=" * 60)
        print("✅ 关键词检索模块测试通过！")
        print("=" * 60)
        print("\n下一步：")
        print("1. 检索模块正常工作")
        print("2. 需要解决MiMo API网络访问问题")
        print("3. 或者先使用模拟数据测试完整Pipeline")
    else:
        print("\n❌ 检索模块存在问题，请检查企业库文件路径")
