"""
测试脚本：测试高级人才画像功能（结合简历+微信截图）
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import build_mimo_client, encode_image_to_base64
from src.pipeline import run_pipeline_and_generate_report, run_pipeline_and_export_word
from src.resume_processor import read_resume_file, process_resume_and_match
from src.word_exporter import WordExporter


def create_test_screenshot():
    """创建一个更真实的测试截图（使用Pillow）"""
    print("=" * 60)
    print("准备测试截图")
    print("=" * 60)
    
    test_image_path = "data/input/test_screenshot.png"
    os.makedirs(os.path.dirname(test_image_path), exist_ok=True)
    
    try:
        from PIL import Image  # 延迟导入，如果Pillow未安装则使用备选方案
        
        # 创建一个简单的截图（宽度750px，高度1334px，模拟手机截图）
        width, height = 750, 1334
        image = Image.new('RGB', (width, height), color='white')
        
        # 保存图片
        image.save(test_image_path)
        print(f"✅ 测试截图已创建: {test_image_path}")
        print(f"   大小: {os.path.getsize(test_image_path)} 字节")
        return test_image_path
    except ImportError:
        print("⚠️ Pillow未安装，无法创建真实截图")
        print("   使用最小的PNG文件代替")
        # 创建一个最小的合法PNG文件
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
            0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        with open(test_image_path, 'wb') as f:
            f.write(png_data)
        
        print(f"✅ 最小测试图片已创建: {test_image_path}")
        return test_image_path
    except Exception as e:
        print(f"❌ 创建测试截图失败: {str(e)}")
        return None


def test_encode_image():
    """测试图片Base64编码功能"""
    print("=" * 60)
    print("测试1: 图片Base64编码")
    print("=" * 60)
    
    test_image_path = create_test_screenshot()
    if not test_image_path or not os.path.exists(test_image_path):
        print("❌ 测试图片不存在，跳过测试")
        return None
    
    # 测试Base64编码
    try:
        encoded = encode_image_to_base64(test_image_path)
        print(f"✅ Base64编码成功，长度: {len(encoded)} 字符")
        print(f"   前50字符: {encoded[:50]}...")
        print(f"   后50字符: ...{encoded[-50:]}")
        return test_image_path
    except Exception as e:
        print(f"❌ Base64编码失败: {str(e)}")
        return None


def test_llm_client_init():
    """测试LLM客户端初始化"""
    print("\n" + "=" * 60)
    print("测试2: LLM客户端初始化")
    print("=" * 60)
    
    try:
        client = build_mimo_client()
        print(f"✅ LLM客户端初始化成功")
        print(f"   文本模型: {client.model}")
        print(f"   多模态模型: {client.multimodal_model}")
        print(f"   API URL: {client.api_url}")
        print(f"   多模态API URL: {client.multimodal_api_url}")
        return client
    except Exception as e:
        print(f"❌ LLM客户端初始化失败: {str(e)}")
        return None


def test_generate_talent_profile(client):
    """测试基础人才画像生成"""
    print("\n" + "=" * 60)
    print("测试3: 基础人才画像生成")
    print("=" * 60)
    
    if client is None:
        print("⚠️ 跳过测试（客户端未初始化）")
        return None
    
    test_resume = """
    王明华，男，1988年出生，博士学历，专业方向：人工智能、机器学习。
    
    教育背景：
    - 2007-2011：清华大学 计算机科学 学士
    - 2011-2014：清华大学 人工智能 硕士
    - 2014-2019：斯坦福大学 计算机科学 博士
    
    工作经历：
    - 2019-2021：Google Research 博士后研究员
      - 参与大规模语言模型训练与优化
      - 发表顶会论文10篇（NeurIPS、ICML、ICLR）
    
    - 2021-至今：Meta AI Research 高级研究员
      - 领导3人小团队进行多模态学习研究
      - 成功申请美国专利2项
      - 指导学生3名（博士生）
    
    专业技能：
    - 深度学习全流程（模型设计、训练、部署）
    - 自然语言处理（NLP）、计算机视觉（CV）
    - PyTorch、TensorFlow、Hugging Face Transformers
    - 分布式训练、模型压缩与加速
    
    求职意向：
    - 期望地区：北京市、上海市、深圳市
    - 期望领域：人工智能、大模型、AGI
    - 期望职位：首席科学家/技术副总裁/AI实验室主任
    """
    
    try:
        print("正在调用MiMo API生成基础人才画像...")
        profile = client.generate_talent_profile(test_resume)
        print(f"✅ 基础人才画像生成成功")
        print(f"   长度: {len(profile)} 字符")
        print(f"   前200字符: {profile[:200]}...")
        return profile
    except Exception as e:
        print(f"❌ 基础人才画像生成失败: {str(e)}")
        return None


def test_analyze_wechat_screenshots(client, screenshot_paths):
    """测试微信截图分析（多模态）"""
    print("\n" + "=" * 60)
    print("测试4: 微信截图分析（多模态）")
    print("=" * 60)
    
    if client is None:
        print("⚠️ 跳过测试（客户端未初始化）")
        return None
    
    if not screenshot_paths:
        print("⚠️ 跳过测试（无截图文件）")
        return None
    
    try:
        print(f"正在调用多模态MiMo API分析 {len(screenshot_paths)} 张截图...")
        
        # 打印第一张截图的大小
        if os.path.exists(screenshot_paths[0]):
            file_size = os.path.getsize(screenshot_paths[0])
            print(f"   第一张截图大小: {file_size} 字节")
        
        analysis = client.analyze_wechat_screenshots(screenshot_paths)
        print(f"✅ 微信截图分析成功")
        print(f"   长度: {len(analysis)} 字符")
        print(f"   前200字符: {analysis[:200]}...")
        return analysis
    except Exception as e:
        print(f"❌ 微信截图分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_generate_advanced_talent_profile(client, resume_text, wechat_analysis):
    """测试高级人才画像生成"""
    print("\n" + "=" * 60)
    print("测试5: 高级人才画像生成（结合简历+微信分析）")
    print("=" * 60)
    
    if client is None:
        print("⚠️ 跳过测试（客户端未初始化）")
        return None
    
    if wechat_analysis is None:
        print("⚠️ 跳过测试（无微信分析数据）")
        return None
    
    try:
        print("正在调用MiMo API生成高级人才画像...")
        profile = client.generate_advanced_talent_profile(resume_text, wechat_analysis)
        print(f"✅ 高级人才画像生成成功")
        print(f"   长度: {len(profile)} 字符")
        print(f"   前200字符: {profile[:200]}...")
        return profile
    except Exception as e:
        print(f"❌ 高级人才画像生成失败: {str(e)}")
        return None


def test_pipeline_with_advanced_profile(resume_file, wechat_screenshots=None):
    """测试完整Pipeline（含高级人才画像）"""
    print("\n" + "=" * 60)
    print("测试6: 完整Pipeline（含高级人才画像）")
    print("=" * 60)
    
    if not os.path.exists(resume_file):
        print(f"⚠️ 简历文件不存在: {resume_file}")
        print("   请修改 resume_file 变量为实际路径")
        return None
    
    try:
        print(f"正在处理简历: {resume_file}")
        output = process_resume_and_match(
            resume_file=resume_file,
            top_k=10,
            use_llm=False,  # 不使用LLM生成报告（节省API调用）
            use_llm_for_profile=False,  # 不使用基础人才画像
            wechat_screenshots=wechat_screenshots,
            use_advanced_profile=(wechat_screenshots is not None)
        )
        
        print(f"✅ Pipeline执行成功")
        print(f"   输出文件: {output}")
        return output
    except Exception as e:
        print(f"❌ Pipeline执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    print("=" * 60)
    print("高级人才画像功能测试")
    print("=" * 60)
    
    # 测试1: 图片Base64编码
    test_image_path = test_encode_image()
    
    # 测试2: LLM客户端初始化
    client = test_llm_client_init()
    
    # 测试3: 基础人才画像生成
    basic_profile = test_generate_talent_profile(client)
    
    # 测试4: 微信截图分析（多模态）
    screenshot_paths = [test_image_path] if test_image_path else None
    wechat_analysis = test_analyze_wechat_screenshots(client, screenshot_paths)
    
    # 测试5: 高级人才画像生成
    test_resume = """
    王明华，男，1988年出生，博士学历，专业方向：人工智能、机器学习。
    教育背景：- 2007-2011：清华大学 计算机科学 学士
    """
    advanced_profile = test_generate_advanced_talent_profile(client, test_resume, wechat_analysis)
    
    # 测试6: 完整Pipeline（需要真实的简历文件）
    # 请修改为实际的简历文件路径
    resume_file = "data/input/王明华博士简历.docx"  # 修改为实际路径
    
    if os.path.exists(resume_file):
        wechat_screenshots = [test_image_path] if test_image_path else None
        output = test_pipeline_with_advanced_profile(resume_file, wechat_screenshots)
    else:
        print("\n⚠️ 跳过完整Pipeline测试（简历文件不存在）")
        print(f"   请修改 resume_file 变量为实际路径: {resume_file}")
    
    # 打印测试摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"1. 图片Base64编码: {'✅ 通过' if test_image_path else '❌ 失败'}")
    print(f"2. LLM客户端初始化: {'✅ 通过' if client else '❌ 失败'}")
    print(f"3. 基础人才画像生成: {'✅ 通过' if basic_profile else '❌ 失败'}")
    print(f"4. 微信截图分析: {'✅ 通过' if wechat_analysis else '❌ 失败'}")
    print(f"5. 高级人才画像生成: {'✅ 通过' if advanced_profile else '❌ 失败'}")
    print(f"6. 完整Pipeline: {'✅ 通过' if 'output' in locals() and output else '❌ 失败'}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
