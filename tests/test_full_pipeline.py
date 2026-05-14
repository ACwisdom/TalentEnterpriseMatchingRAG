"""
完整Pipeline测试脚本（模拟LLM版）
功能：用模拟LLM生成匹配报告，验证完整流程
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline import run_pipeline_and_generate_report


def run_pipeline_sample(resume_text: str, resume_name: str = "测试简历"):
    """
    用给定简历跑完整 Pipeline（供脚本 __main__ 调用；勿以 test_ 前缀命名，避免被 pytest 当作用例）。
    """
    print("=" * 60)
    print(f"测试简历：{resume_name}")
    print("=" * 60)
    
    # 生成输出文件名
    output_file = os.path.join(PROJECT_ROOT, "data", "output", f"report_{resume_name}.txt")
    
    # 运行Pipeline
    report_text = run_pipeline_and_generate_report(
        resume_text=resume_text,
        top_k=15,
        output_file=output_file
    )
    
    print("\n" + "=" * 60)
    print("Pipeline测试完成！")
    print("=" * 60)
    print(f"报告已保存：{output_file}")
    print(f"报告长度：{len(report_text)} 字符")
    
    # 显示报告前1000字符
    print("\n" + "=" * 60)
    print("报告预览（前1000字符）：")
    print("=" * 60)
    print(report_text[:1000] + "...")
    
    return report_text


# ============ 测试用例 ============

# 测试用例1：生物医药博士
BIO_MEDICINE_RESUME = """
李明，男，1988年出生，博士学位，专业方向：生物医药、化学制药。

教育背景：
- 2006-2010：北京大学 药学 学士
- 2010-2013：北京大学 药物化学 硕士
- 2013-2017：清华大学 药学 博士

工作经历：
- 2017-2020：上海某制药企业 研究员
  - 参与抗肿瘤药物研发项目
  - 负责药物合成工艺优化
  - 发表SCI论文5篇

- 2020-至今：苏州生物医药企业 高级研究员
  - 负责小分子药物研发
  - 领导5人研发团队
  - 申请发明专利3项
  - 发表SCI论文8篇

专业技能：
- 药物研发全流程经验（10年+）
- 化学制药工艺开发与优化
- 小分子药物设计
- 生物医药技术转化
- 团队管理与项目协调
- 精通HPLC、LC-MS等分析仪器

获奖情况：
- 2022年 江苏省"双创人才"
- 2021年 苏州市"姑苏领军人才"
"""

# 测试用例2：半导体材料博士
SEMICONDUCTOR_RESUME = """
王强，男，1985年出生，博士学位，专业方向：半导体材料、薄膜技术。

教育背景：
- 2003-2007：浙江大学 材料科学 学士
- 2007-2010：中科院半导体所 微电子 硕士
- 2010-2014：美国加州大学 材料科学 博士

工作经历：
- 2014-2017：美国Intel公司 研发工程师
  - 参与7nm工艺开发
  - 负责薄膜沉积工艺优化
  - 发表专利2项

- 2017-至今：无锡某半导体企业 技术总监
  - 负责SiC功率器件研发
  - 领导15人技术团队
  - 成功开发GaN HEMT器件
  - 申请发明专利10项

专业技能：
- 半导体工艺全流程（10年+）
- SiC/GaN功率器件设计与制造
- 薄膜沉积技术（CVD、PVD）
- 半导体器件表征与分析
- 精通TCAD仿真、半导体物理
"""

# 测试用例3：AI算法博士
AI_RESUME = """
张薇，女，1990年出生，博士学位，专业方向：人工智能、计算机视觉。

教育背景：
- 2008-2012：清华大学 计算机科学 学士
- 2012-2015：清华大学 人工智能 硕士
- 2015-2019：美国斯坦福大学 计算机科学 博士

工作经历：
- 2019-2021：美国Google公司 研究科学家
  - 参与大规模图像识别项目
  - 发表顶会论文（CVPR、ICCV）5篇

- 2021-至今：杭州某AI企业 算法总监
  - 负责计算机视觉算法研发
  - 领导20人算法团队
  - 成功落地多个AI产品（人脸识别、目标检测）
  - 发表顶会论文10篇

专业技能：
- 深度学习全流程（8年+）
- 计算机视觉（CNN、Transformer、目标检测）
- 自然语言处理（BERT、GPT）
- 精通PyTorch、TensorFlow
- 大数据处理（Spark、Hadoop）
"""


if __name__ == "__main__":
    print("=" * 60)
    print("完整Pipeline测试（模拟LLM版）")
    print("=" * 60)
    
    # 让用户选择测试用例
    print("\n请选择测试用例：")
    print("1. 生物医药博士（药物研发方向）")
    print("2. 半导体材料博士（SiC/GaN方向）")
    print("3. AI算法博士（计算机视觉方向）")
    print("4. 运行所有测试用例")
    
    # 这里为了方便，直接运行所有测试用例
    print("\n开始运行所有测试用例...\n")
    
    # 测试用例1：生物医药
    run_pipeline_sample(BIO_MEDICINE_RESUME, "生物医药博士")
    
    print("\n" + "=" * 60 + "\n")
    
    # 测试用例2：半导体
    run_pipeline_sample(SEMICONDUCTOR_RESUME, "半导体博士")
    
    print("\n" + "=" * 60 + "\n")
    
    # 测试用例3：AI
    run_pipeline_sample(AI_RESUME, "AI算法博士")
    
    print("\n" + "=" * 60)
    print("所有测试用例完成！")
    print("=" * 60)
    print("\n生成的报告文件：")
    print("- data/output/report_生物医药博士.txt")
    print("- data/output/report_半导体博士.txt")
    print("- data/output/report_AI算法博士.txt")
