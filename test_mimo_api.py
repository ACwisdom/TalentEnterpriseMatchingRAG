"""
测试MiMo API连接
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm_client import build_mimo_client


def test_mimo_connection():
    """测试MiMo API连接"""
    print("=" * 60)
    print("测试MiMo API连接")
    print("=" * 60)
    
    try:
        # 1. 初始化客户端
        print("\n[1/2] 正在初始化MiMo客户端...")
        client = build_mimo_client()
        
        # 2. 测试连接
        print("\n[2/2] 正在测试API连接...")
        if client.test_connection():
            print("\n" + "=" * 60)
            print("✅ MiMo API连接测试通过！")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ MiMo API连接测试失败")
            print("=" * 60)
            return False
            
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


def test_mimo_generation():
    """测试MiMo API生成功能"""
    print("\n" + "=" * 60)
    print("测试MiMo API文本生成")
    print("=" * 60)
    
    try:
        # 初始化客户端
        client = build_mimo_client()
        
        # 测试生成
        test_messages = [
            {"role": "system", "content": "你是一个专业的人才匹配顾问。"},
            {"role": "user", "content": "请用一句话介绍你自己。"}
        ]
        
        print("\n正在调用API生成文本...")
        response = client.chat(test_messages, max_tokens=100)
        
        print("\n" + "=" * 60)
        print("✅ 文本生成测试通过！")
        print("=" * 60)
        print(f"模型回复:\n{response}")
        return True
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 生成测试失败: {str(e)}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    # 测试连接
    if test_mimo_connection():
        # 连接成功，测试生成
        test_mimo_generation()
    else:
        print("\n⚠️ 请检查：")
        print("1. API Key是否正确")
        print("2. API URL是否正确")
        print("3. 网络连接是否正常")
        print("4. API账户是否有余额")
