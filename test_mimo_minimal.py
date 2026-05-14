"""
最小化MiMo API测试（仅依赖requests）
"""
import json
import sys

import requests

from src.config import MIMO_API_KEY

# MiMo API配置（密钥来自 .env / 环境变量 MIMO_API_KEY）
API_KEY = MIMO_API_KEY
API_URL = "https://api.mimo-v2.com/v1/chat/completions"
MODEL = "MiMo-V2.5-Pro"


def test_mimo_api():
    """测试MiMo API连接和生成"""
    if not API_KEY:
        print("❌ 未配置 MIMO_API_KEY（请在项目根目录 .env 或环境变量中设置）")
        sys.exit(1)
    print("=" * 60)
    print("测试MiMo API（最小化版本）")
    print("=" * 60)
    
    # 构建请求
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY  # MiMo使用api-key认证头
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "请用一句话介绍你自己，并说明你可以如何帮助人才匹配。"}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    print(f"\n🌐 正在调用MiMo API...")
    print(f"   URL: {API_URL}")
    print(f"   Model: {MODEL}")
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        # 检查响应
        print(f"\n📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if "choices" in result and result["choices"]:
                generated_text = result["choices"][0]["message"]["content"]
                
                print("\n" + "=" * 60)
                print("✅ API调用成功！")
                print("=" * 60)
                print(f"\n模型回复:\n{generated_text}")
                
                # 保存结果
                output_file = "data/mimo_test_result.txt"
                import os
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(generated_text)
                
                print(f"\n✅ 结果已保存: {output_file}")
                return True
            else:
                print("\n❌ API返回格式错误:")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return False
        else:
            print("\n❌ API调用失败:")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时（60秒）")
        print("   请检查网络连接")
        return False
    
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_mimo_api()
