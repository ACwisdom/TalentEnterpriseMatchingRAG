"""
简单测试：验证高级人才画像Word导出功能
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.word_exporter import WordExporter
from src.llm_client import build_mimo_client


def test_word_export_with_advanced_profile():
    """测试Word导出（含高级人才画像）"""
    print("=" * 60)
    print("测试：Word导出（含高级人才画像）")
    print("=" * 60)
    
    # 模拟数据
    resume_text = """
    王明华，男，1988年出生，博士学历，专业方向：人工智能、机器学习。
    
    教育背景：
    - 2007-2011：清华大学 计算机科学 学士
    - 2011-2014：清华大学 人工智能 硕士
    - 2014-2019：斯坦福大学 计算机科学 博士
    
    工作经历：
    - 2019-2021：Google Research 博士后研究员
    - 2021-至今：Meta AI Research 高级研究员
    
    专业技能：
    - 深度学习全流程（模型设计、训练、部署）
    - 自然语言处理（NLP）、计算机视觉（CV）
    
    求职意向：
    - 期望地区：北京市、上海市、深圳市
    - 期望领域：人工智能、大模型、AGI
    """
    
    # 模拟高级人才画像（Markdown格式）
    advanced_profile = """## 一、博士人才画像

### 1. 基本信息
- **姓名**：王明华
- **性别**：男
- **年龄**：35岁（1988年出生）
- **学历**：博士（推断）
- **本科院校**：清华大学 计算机科学

### 2. 研究方向
- **专业领域**：人工智能、机器学习
- **重点与创新点**：简历中未提供博士及博士后阶段的具体研究课题、发表论文或项目细节。研究方向的大类指向明确，但缺乏细分方向描述，无法精准匹配细分领域岗位。

### 3. 核心技能
- **深度学习全流程**：模型设计、训练、部署
- **自然语言处理（NLP）**：顶会论文10篇（NeurIPS、ICML、ICLR）
- **计算机视觉（CV）**：多模态学习研究
- **工程能力**：PyTorch、TensorFlow、Hugging Face Transformers

### 4. 差异化优势（深度分析）
- **顶会论文产出能力**：在NeurIPS、ICML、ICLR等顶会发表10篇论文，说明其具备极强的算法创新能力和学术影响力，适合高校教职或企业研究院的"科学家"岗位，而非纯工程岗。
- **中美两边学术背景**：清华大学本科+硕士，斯坦福博士，兼具中国顶尖高校根基和美国顶尖科研训练，是"国际化人才"的典型画像，对国家人才引进项目（如海外高层次人才引进计划）极具吸引力。
- **工业界研究经验**：Google Research博士后 + Meta AI Research高级研究员，证明其研究能力已转化为工业级影响力，能承接"产学研"一体化岗位，直接对标"首席科学家""AI实验室主任"级别职位。
- **团队管理与指导能力**：在Meta领导3人小团队，并指导3名博士生，显示其已具备独立PI（Principal Investigator）潜质，适合"青年学者"或"团队负责人"角色。

### 5. 核心诉求

#### 显性诉求（从简历中得出）
- **期望地区**：北京市、上海市、深圳市
- **期望职位**：首席科学家/技术副总裁/AI实验室主任
- **期望领域**：人工智能、大模型、AGI

#### 隐性诉求（从聊天记录中推断）
- **家庭安置**：已婚，有子女且孩子还小，明确提出配偶工作安排和子女教育是重要考量因素
- **生活需求**：关注住房补贴、子女入学政策
- **职业发展**：希望在国内能继续顶会论文产出，同时实现研究成果转化
- **潜在顾虑**：担心国内高校/企业的科研自由度不如国外，担心"非升即走"压力

### 6. 潜在风险
- **家庭因素**：配偶工作安排和子女教育如果无法妥善解决，可能成为回国决策的"绊脚石"
- **科研环境适应**：从国外开放式科研环境到国内目标导向型科研环境，可能需要1-2年适应期
- **薪酬期望**：国外薪资水平较高，回国可能对薪酬有较高期望，需要提前沟通清楚
"""
    
    enterprises = [
        {
            "metadata": {
                "企业名称": "测试人工智能企业A",
                "省": "北京市",
                "市": "北京市",
                "区/县": "海淀区",
                "地区门槛": "博士可享安家补贴50万",
                "一级领域": "人工智能",
                "二级领域": "大模型",
                "企业主要产品": "大语言模型、多模态模型"
            },
            "score": 85.5,
            "matched_keywords": ["人工智能", "大模型", "博士"]
        },
        {
            "metadata": {
                "企业名称": "测试AI研究院B",
                "省": "上海市",
                "市": "上海市",
                "区/县": "浦东新区",
                "地区门槛": "附件中未提供",
                "一级领域": "人工智能",
                "二级领域": "AGI",
                "企业主要产品": "通用人工智能基础研究"
            },
            "score": 72.3,
            "matched_keywords": ["人工智能", "博士", "研究"]
        }
    ]
    
    try:
        # 初始化Word导出器
        exporter = WordExporter()
        
        # 导出Word文档（含高级人才画像）
        output_dir = "data/output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "测试_高级人才画像.docx")
        
        print(f"\n正在导出Word文档: {output_path}")
        
        result = exporter.create_matching_report(
            resume_text=resume_text,
            enterprises=enterprises,
            output_path=output_path,
            report_title="人才-企业匹配报告（高级人才画像测试）",
            talent_profile=advanced_profile,
            is_advanced_profile=True  # 关键：指定为高级人才画像
        )
        
        print(f"✅ Word文档导出成功！")
        print(f"   输出文件: {result}")
        print(f"   文件大小: {os.path.getsize(result)} 字节")
        
        # 验证文件是否存在
        if os.path.exists(result):
            print(f"\n✅ 验证通过：文件已成功创建")
            return result
        else:
            print(f"\n❌ 验证失败：文件不存在")
            return None
            
    except Exception as e:
        print(f"❌ Word导出失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_word_export_basic():
    """测试Word导出（基础版，无高级人才画像）"""
    print("\n" + "=" * 60)
    print("测试：Word导出（基础版）")
    print("=" * 60)
    
    # 模拟数据
    resume_text = "王明华，男，1988年出生，博士学历，专业方向：人工智能。"
    enterprises = []
    
    try:
        # 初始化Word导出器
        exporter = WordExporter()
        
        # 导出Word文档（基础版）
        output_dir = "data/output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "测试_基础版.docx")
        
        print(f"\n正在导出Word文档: {output_path}")
        
        result = exporter.create_matching_report(
            resume_text=resume_text,
            enterprises=enterprises,
            output_path=output_path,
            report_title="人才-企业匹配报告（基础版测试）",
            talent_profile=None,  # 无人才画像
            is_advanced_profile=False
        )
        
        print(f"✅ Word文档导出成功！")
        print(f"   输出文件: {result}")
        return result
            
    except Exception as e:
        print(f"❌ Word导出失败: {str(e)}")
        return None


def main():
    """主测试函数"""
    print("=" * 60)
    print("高级人才画像Word导出测试")
    print("=" * 60)
    
    # 测试1: Word导出（高级版）
    result_advanced = test_word_export_with_advanced_profile()
    
    # 测试2: Word导出（基础版）
    result_basic = test_word_export_basic()
    
    # 打印测试摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"1. Word导出（高级版）: {'✅ 通过' if result_advanced else '❌ 失败'}")
    print(f"2. Word导出（基础版）: {'✅ 通过' if result_basic else '❌ 失败'}")
    
    if result_advanced and result_basic:
        print("\n🎉 所有测试通过！")
        print(f"\n请打开以下文件查看效果：")
        print(f"1. 高级版: {result_advanced}")
        print(f"2. 基础版: {result_basic}")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
