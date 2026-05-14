"""
MiMo API客户端模块
功能：调用MiMo-V2.5-Pro API生成匹配报告
"""
import os
import sys
from pathlib import Path
import requests
import json
import base64
from typing import List, Dict, Optional, Iterator

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MIMO_API_KEY, MIMO_API_URL, MIMO_MODEL, MIMO_API_KEY_HEADER, MIMO_MULTIMODAL_MODEL, MIMO_MULTIMODAL_API_URL, REFERENCE_DATE


def encode_image_to_base64(image_path: str) -> str:
    """
    将图片文件编码为Base64字符串
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        str: Base64编码的字符串
    """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string


class MiMoClient:
    """MiMo API客户端（OpenAI兼容格式）"""
    
    def __init__(self, 
                 api_key: str = None, 
                 api_url: str = None, 
                 model: str = None,
                 multimodal_model: str = None,
                 multimodal_api_url: str = None):
        """
        初始化MiMo客户端
        
        Args:
            api_key: API密钥，默认使用config中的配置
            api_url: API地址，默认使用config中的配置
            model: 文本模型名称，默认使用config中的配置
            multimodal_model: 多模态模型名称，默认使用config中的配置
            multimodal_api_url: 多模态API地址，默认使用config中的配置
        """
        self.api_key = api_key or MIMO_API_KEY
        self.api_url = api_url or MIMO_API_URL
        self.model = model or MIMO_MODEL
        self.multimodal_model = multimodal_model or MIMO_MULTIMODAL_MODEL
        self.multimodal_api_url = multimodal_api_url or MIMO_MULTIMODAL_API_URL
        self.api_key_header = MIMO_API_KEY_HEADER  # 使用自定义认证头
        
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError("❌ MiMo API Key未配置，请在config.py中设置MIMO_API_KEY")
        
        print(f"✅ MiMo客户端初始化成功")
        print(f"   文本模型: {self.model}")
        print(f"   多模态模型: {self.multimodal_model}")
        print(f"   API URL: {self.api_url}")
    
    def _build_headers(self) -> Dict:
        """构建请求头（官方 OpenAI 兼容：Authorization: Bearer）"""
        if (self.api_key_header or "").lower() == "authorization":
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
        # 兼容少数使用自定义头的网关
        return {
            "Content-Type": "application/json",
            self.api_key_header: self.api_key,
        }
    
    def chat(self, 
             messages: List[Dict],
             temperature: float = 0.7,
             max_tokens: int = 4000,
             stream: bool = False) -> str:
        """
        调用MiMo API进行对话
        
        Args:
            messages: OpenAI格式的messages列表
            temperature: 温度参数（0-1）
            max_tokens: 最大生成token数
            stream: 是否流式返回
            
        Returns:
            str: 模型生成的回复文本
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        print(f"\n🌐 正在调用MiMo API...")
        print(f"   URL: {self.api_url}")
        print(f"   Model: {self.model}")
        print(f"   Messages数量: {len(messages)}")
        
        try:
            response = requests.post(
                self.api_url,
                headers=self._build_headers(),
                json=payload,
                timeout=120  # 2分钟超时
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise ValueError(f"❌ API返回格式错误: {result}")
            
            # 提取生成的文本
            generated_text = result["choices"][0]["message"]["content"]
            
            print(f"✅ API调用成功")
            print(f"   生成文本长度: {len(generated_text)} 字符")
            
            return generated_text
            
        except requests.exceptions.Timeout:
            raise TimeoutError("❌ API调用超时（120秒），请检查网络连接或稍后重试")
        
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"❌ API调用失败: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"❌ 解析API响应失败: {str(e)}，响应内容: {response.text[:500]}")
    
    def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Iterator[str]:
        """OpenAI 兼容 SSE：逐段 yield 文本增量。"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            with requests.post(
                self.api_url,
                headers=self._build_headers(),
                json=payload,
                timeout=300,
                stream=True,
            ) as response:
                response.raise_for_status()
                for raw in response.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    line = raw.strip()
                    if line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        yield piece
        except requests.exceptions.Timeout:
            raise TimeoutError("❌ API 流式调用超时") from None
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"❌ API 流式调用失败: {e}") from e
    
    def generate_matching_report_stream(
        self,
        system_prompt: str,
        resume_text: str,
        enterprises: List[Dict],
        temperature: float = 0.7,
    ) -> Iterator[str]:
        from src.prompt_builder import build_matching_user_content
        
        user_content = build_matching_user_content(resume_text, enterprises)
        ref = REFERENCE_DATE.isoformat()
        system_effective = (
            system_prompt.rstrip()
            + f"\n（系统已给定参考日期：{ref}，输出中的时间表述须与此一致。）\n"
        )
        messages = [
            {"role": "system", "content": system_effective},
            {"role": "user", "content": user_content},
        ]
        yield from self.chat_stream(messages, temperature=temperature, max_tokens=4000)
    
    def generate_talent_profile_stream(
        self,
        resume_text: str,
        temperature: float = 0.7,
    ) -> Iterator[str]:
        system_prompt = """你是一个专业的人才分析师，擅长从简历中提取关键信息并生成简洁、结构化的人才画像摘要。

要求：
1. 从简历中提取关键信息
2. 生成结构化的人才画像摘要
3. 包括：基本信息、教育背景、工作经历、专业技能、求职意向
4. 语言简洁、专业
5. 不要编造信息，只基于简历内容
6. 输出格式为Markdown"""

        user_content = f"""请根据以下简历文本，生成人才画像摘要。

=== 简历文本 ===
{resume_text}

=== 要求 ===
请生成结构化的人才画像摘要，包括：
1. **基本信息**：姓名、性别、年龄、学历等
2. **教育背景**：学校、专业、学历、时间
3. **工作经历**：公司、职位、时间、主要职责
4. **专业技能**：核心技能、专长领域
5. **求职意向**：期望地区、领域、职位

注意：
- 语言简洁、专业
- 不要编造信息
- 输出格式为Markdown"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        yield from self.chat_stream(messages, temperature=temperature, max_tokens=2000)
    
    def generate_matching_report(self,
                                system_prompt: str,
                                resume_text: str,
                                enterprises: List[Dict],
                                temperature: float = 0.7) -> str:
        """
        生成人才-企业匹配报告（高级封装）
        
        Args:
            system_prompt: 系统提示词
            resume_text: 简历文本
            enterprises: 检索到的企业列表
            temperature: 温度参数
            
        Returns:
            str: 生成的匹配报告
        """
        from src.prompt_builder import build_matching_user_content
        
        user_content = build_matching_user_content(resume_text, enterprises)
        
        ref = REFERENCE_DATE.isoformat()
        system_effective = (
            system_prompt.rstrip()
            + f"\n（系统已给定参考日期：{ref}，输出中的时间表述须与此一致。）\n"
        )
        
        messages = [
            {"role": "system", "content": system_effective},
            {"role": "user", "content": user_content},
        ]
        
        # 4. 调用API
        report = self.chat(messages, temperature=temperature, max_tokens=4000)
        
        return report
    
    def generate_talent_profile(self,
                                resume_text: str,
                                temperature: float = 0.7) -> str:
        """
        生成人才画像摘要（使用LLM）
        
        Args:
            resume_text: 简历文本
            temperature: 温度参数
            
        Returns:
            str: 生成的人才画像摘要
        """
        system_prompt = """你是一个专业的人才分析师，擅长从简历中提取关键信息并生成简洁、结构化的人才画像摘要。

要求：
1. 从简历中提取关键信息
2. 生成结构化的人才画像摘要
3. 包括：基本信息、教育背景、工作经历、专业技能、求职意向
4. 语言简洁、专业
5. 不要编造信息，只基于简历内容
6. 输出格式为Markdown"""

        user_content = f"""请根据以下简历文本，生成人才画像摘要。

=== 简历文本 ===
{resume_text}

=== 要求 ===
请生成结构化的人才画像摘要，包括：
1. **基本信息**：姓名、性别、年龄、学历等
2. **教育背景**：学校、专业、学历、时间
3. **工作经历**：公司、职位、时间、主要职责
4. **专业技能**：核心技能、专长领域
5. **求职意向**：期望地区、领域、职位

注意：
- 语言简洁、专业
- 不要编造信息
- 输出格式为Markdown"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # 调用API
        profile = self.chat(messages, temperature=temperature, max_tokens=2000)
        
        # 清理输出（去除可能的markdown代码块标记）
        profile = profile.strip()
        if profile.startswith("```markdown"):
            profile = profile[11:]
        if profile.startswith("```"):
            profile = profile[3:]
        if profile.endswith("```"):
            profile = profile[:-3]
        profile = profile.strip()
        
        return profile

    def chat_multimodal(self, 
                        messages: List[Dict],
                        temperature: float = 0.7,
                        max_tokens: int = 4000,
                        stream: bool = False) -> str:
        """
        调用多模态MiMo API（支持图像输入）
        
        Args:
            messages: OpenAI格式的messages列表（可包含image_url）
            temperature: 温度参数（0-1）
            max_tokens: 最大生成token数
            stream: 是否流式返回
            
        Returns:
            str: 模型生成的回复文本
        """
        payload = {
            "model": self.multimodal_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        print(f"\n🌐 正在调用多模态MiMo API...")
        print(f"   URL: {self.multimodal_api_url}")
        print(f"   Model: {self.multimodal_model}")
        print(f"   Messages数量: {len(messages)}")
        
        try:
            response = requests.post(
                self.multimodal_api_url,
                headers=self._build_headers(),
                json=payload,
                timeout=120  # 2分钟超时
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise ValueError(f"❌ API返回格式错误: {result}")
            
            # 提取生成的文本
            generated_text = result["choices"][0]["message"]["content"]
            
            print(f"✅ 多模态API调用成功")
            print(f"   生成文本长度: {len(generated_text)} 字符")
            
            return generated_text
            
        except requests.exceptions.Timeout:
            raise TimeoutError("❌ 多模态API调用超时（120秒），请检查网络连接或稍后重试")
        
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"❌ 多模态API调用失败: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"❌ 解析多模态API响应失败: {str(e)}，响应内容: {response.text[:500]}")

    def analyze_wechat_screenshots(self,
                                   screenshot_paths: List[str],
                                   temperature: float = 0.7) -> str:
        """
        使用多模态模型分析微信聊天截图，提取深层信息
        
        Args:
            screenshot_paths: 截图文件路径列表（PNG格式）
            temperature: 温度参数
            
        Returns:
            str: 提取的深层信息（JSON格式或结构化文本）
        """
        # 1. 构建系统提示词
        system_prompt = """你是一个专业的人才分析师，擅长从微信聊天记录中提取人才的深层信息和真实诉求。

重要提示：
1. 请仔细分析聊天截图中的对话内容
2. 提取以下关键信息：
   - 家庭情况（婚姻状况、配偶工作、子女情况）
   - 回国计划（时间、原因、顾虑）
   - 真实诉求（薪资期望、职业发展、生活需求）
   - 性格特点（沟通风格、决策倾向）
   - 潜在风险（顾虑、担忧、未明说的需求）
3. 如果某些信息无法从截图中获取，请标注"截图中未体现"
4. 输出格式为JSON，便于后续处理"""
        
        # 2. 构建用户消息（包含多张截图）
        user_content = [
            {"type": "text", "text": """请分析以下微信聊天截图，提取人才的深层信息和真实诉求。

需要提取的信息：
1. **家庭情况**：婚姻状况、配偶工作地点、子女情况、是否需要安置家人
2. **回国计划**：计划回国时间、回国原因、有哪些顾虑或担忧
3. **真实诉求**：薪资期望、职业发展需求、生活方面的需求（住房、子女教育等）
4. **性格特点**：从沟通风格中分析其性格特点、决策倾向
5. **潜在风险**：有哪些未明说的担忧、可能的影响因素

请注意：
- 只基于截图内容进行分析，不要编造信息
- 如果某些信息截图未体现，标注"截图中未体现"
- 输出格式为JSON"""}
        ]
        
        # 3. 添加所有截图（Base64编码）
        for screenshot_path in screenshot_paths:
            try:
                base64_image = encode_image_to_base64(screenshot_path)
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
                print(f"   ✅ 已加载截图: {screenshot_path}")
            except Exception as e:
                print(f"   ⚠️ 截图加载失败: {screenshot_path}, 错误: {str(e)}")
        
        # 4. 构造messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # 5. 调用多模态API
        result = self.chat_multimodal(messages, temperature=temperature, max_tokens=2000)
        
        return result

    def generate_advanced_talent_profile(self,
                                         resume_text: str,
                                         wechat_analysis: str,
                                         temperature: float = 0.7) -> str:
        """
        生成高级人才画像（结合简历+微信截图分析）
        
        Args:
            resume_text: 简历文本
            wechat_analysis: 微信截图分析结果（JSON或结构化文本）
            temperature: 温度参数
            
        Returns:
            str: 生成的高级人才画像（Markdown格式）
        """
        system_prompt = """你是一个顶级的人才分析师，擅长结合简历和聊天记录，生成深度人才画像。

你的任务：
1. 综合简历文本和微信聊天分析，生成完整的人才画像
2. 重点关注：差异化优势、核心诉求、潜在风险
3. 差异化优势需要深度分析（不只是罗列技能，要结合背景、经验、成果进行深度解读）
4. 核心诉求要区分：显性诉求（明说的）和隐性诉求（从聊天中推断的）
5. 输出格式要专业、简洁、有洞察力

输出格式（Markdown）：
## 一、博士人才画像
### 1. 基本信息
（姓名、性别、年龄、学历等）

### 2. 研究方向
（博士/博士后研究方向，重点、创新点）

### 3. 核心技能
（列出3-5个核心技能，每个技能用1-2句话解释）

### 4. 差异化优势（深度分析）
（这是重点，需要3-5段深度分析，每段讲一个差异化优势，要结合其背景、经验、成果进行解读，不要只是罗列）

### 5. 核心诉求
#### 显性诉求（从简历中得出）
- 期望地区：
- 期望职位：
- 期望薪资：

#### 隐性诉求（从聊天记录中推断）
- 家庭安置：
- 生活需求：
- 职业发展：
- 潜在顾虑：

### 6. 潜在风险
（可能影响回国决策的因素、需要重点沟通的问题）

---
注意：
- 差异化优势是重点，需要深度分析
- 隐性诉求要从聊天记录中细心挖掘
- 输出语言要专业、简洁、有洞察力"""

        user_content = f"""请根据以下简历文本和微信聊天分析结果，生成高级人才画像。

=== 简历文本 ===
{resume_text}

=== 微信聊天分析 ===
{wechat_analysis}

=== 要求 ===
请按照系统提示词中的格式，生成完整、专业、有洞察力的人才画像。
重点：差异化优势部分需要深度分析，不要只是罗列技能。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # 调用API（使用文本模型，因为已经是分析后的信息）
        profile = self.chat(messages, temperature=temperature, max_tokens=3000)
        
        # 清理输出（去除可能的markdown代码块标记）
        profile = profile.strip()
        if profile.startswith("```markdown"):
            profile = profile[11:]
        if profile.startswith("```"):
            profile = profile[3:]
        if profile.endswith("```"):
            profile = profile[:-3]
        profile = profile.strip()
        
        return profile

    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            bool: 连接成功返回True
        """
        print("\n🧪 测试MiMo API连接...")
        
        test_messages = [
            {"role": "system", "content": "你是一个有帮助的助手。"},
            {"role": "user", "content": "请回复'连接成功'三个字。"}
        ]
        
        try:
            response = self.chat(test_messages, max_tokens=50)
            print(f"✅ 连接测试成功！模型回复: {response[:100]}")
            return True
        
        except Exception as e:
            print(f"❌ 连接测试失败: {str(e)}")
            return False


def build_mimo_client(api_key: str = None, api_url: str = None, model: str = None) -> MiMoClient:
    """
    快速构建MiMo客户端的便捷函数
    
    Args:
        api_key: API密钥
        api_url: API地址
        model: 模型名称
        
    Returns:
        MiMoClient: 已初始化的客户端对象
    """
    return MiMoClient(api_key=api_key, api_url=api_url, model=model)


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("测试MiMo API客户端")
    print("=" * 60)
    
    try:
        # 1. 初始化客户端
        client = build_mimo_client()
        
        # 2. 测试连接
        if client.test_connection():
            print("\n✅ MiMo API客户端工作正常")
        else:
            print("\n❌ MiMo API连接测试失败")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
