"""
企业检索模块（关键词匹配版 - 纯标准库实现，无外部依赖）
功能：基于关键词/全文匹配的语义检索（简化版RAG）
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Set
import re
import pandas as pd

from .config import ENTERPRISE_EXCEL, TOP_K, LAYER1_CANDIDATE_CAP, TECH_LEXICON_PATH
from .data_processor import load_enterprise_db, enterprise_to_document


def load_tech_lexicon_from_file(path: Optional[str] = None) -> Set[str]:
    """从可选词表加载术语（每行一词，# 行为注释）。文件不存在则返回空集。"""
    p = (path or TECH_LEXICON_PATH or "").strip()
    out: Set[str] = set()
    if not p or not os.path.isfile(p):
        return out
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.add(line)
    return out

# ============ 专业术语词典 ============
# 常见技术领域关键词（用于提升匹配质量）
TECH_KEYWORDS = {
    # 生物医药
    "生物医药", "药物研发", "化学制药", "生物制药", "中药", "天然药物", "药物制剂", "药理", "毒理", "临床试验",
    "小分子", "大分子", "蛋白质", "抗体", "疫苗", "基因治疗", "细胞治疗", "免疫疗法",
    # 半导体
    "半导体", "芯片", "集成电路", "IC", "晶圆", "光刻", "蚀刻", "CMP", "薄膜", "沉积",
    "SiC", "碳化硅", "GaN", "氮化镓", "MOSFET", "IGBT", "功率器件", "传感器", "MEMS",
    # 材料
    "材料", "纳米", "复合材料", "高分子", "陶瓷", "金属", "合金", "薄膜", "涂层", "功能材料",
    # 信息技术
    "人工智能", "机器学习", "深度学习", "NLP", "计算机视觉", "AI", "大数据", "云计算", "物联网", "IoT",
    "软件", "算法", "数据挖掘", "自然语言处理", "图像识别", "语音识别",
    # 能源
    "新能源", "电池", "储能", "太阳能", "光伏", "风能", "氢能", "燃料电池", "锂电池", "钠离子电池",
    # 化工
    "化工", "化学工程", "催化", "分离", "精制", "石化", "精细化工", "高分子化工",
    # 通用制造
    "制造", "自动化", "机器人", "数控", "CNC", "3D打印", "增材制造", "精密加工",
}

# 常见有意义的中文词组（2-4字）
MEANINGFUL_WORDS = {
    # 学历
    "博士", "硕士", "学士", "博士后", "研究员", "高级研究员", "教授", "副教授",
    # 工作经历
    "负责", "参与", "开发", "设计", "管理", "领导", "团队", "项目",
    # 技能
    "经验", "技能", "专业", "方向", "研究", "开发",
    # 企业相关
    "公司", "企业", "集团", "有限公司", "股份有限公司",
}


class KeywordSearch:
    """基于关键词匹配的企业检索类（纯标准库实现，无外部依赖）"""
    
    def __init__(self, excel_path: str = None):
        """
        初始化检索器
        
        Args:
            excel_path: Excel文件路径，默认使用config中的路径
        """
        self.excel_path = excel_path or ENTERPRISE_EXCEL
        self.df = None
        self.enterprises = None
        
        # 加载企业库
        self._load_data()
        self._tech_term_union: Set[str] = set(TECH_KEYWORDS) | load_tech_lexicon_from_file()
    
    def _load_data(self):
        """加载企业库数据"""
        print(f"正在加载企业库: {self.excel_path}")
        self.df = pd.read_excel(self.excel_path)
        self.enterprises = load_enterprise_db(self.excel_path)
        print(f"✅ 成功加载 {len(self.enterprises)} 家企业")
    
    def _extract_keywords(self, text: str, top_k: int = 20) -> List[str]:
        """
        从文本中提取关键词（纯标准库实现，保守策略）
        
        策略：
        1. 专业术语匹配（TECH_KEYWORDS）- 优先级最高
        2. 有意义词组匹配（MEANINGFUL_WORDS）
        3. 英文专业术语（大写缩写）
        4. 领域编号（如 "4.", "2.1"）
        
        Args:
            text: 输入文本（简历内容）
            top_k: 返回的关键词数量
            
        Returns:
            List[str]: 关键词列表
        """
        text_lower = text.lower()
        keywords = []
        keyword_set = set()  # 用于去重
        
        # 1. 专业术语匹配（最长匹配优先）
        for keyword in sorted(self._tech_term_union, key=len, reverse=True):
            if keyword.lower() in text_lower and keyword not in keyword_set:
                keywords.append(keyword)
                keyword_set.add(keyword)
        
        # 2. 有意义词组匹配
        for word in MEANINGFUL_WORDS:
            if word in text_lower and word not in keyword_set:
                keywords.append(word)
                keyword_set.add(word)
        
        # 3. 英文专业术语（如 "SAR", "CMP", "SiC"）
        english_terms = re.findall(r'\b[A-Z]{2,}\b', text)
        for term in english_terms:
            term_lower = term.lower()
            if term_lower not in keyword_set:
                keywords.append(term)
                keyword_set.add(term_lower)
        
        # 4. 提取领域编号（如 "4.", "2.1"）
        field_patterns = re.findall(r'\d+\.\d+|\d+\.', text)
        for pattern in field_patterns:
            if pattern not in keyword_set:
                keywords.append(pattern)
                keyword_set.add(pattern)
        
        # 5. 返回Top-K关键词
        return keywords[:top_k]
    
    def _calculate_match_score(self, enterprise: Dict, keywords: List[str]) -> tuple:
        """
        计算企业与关键词的匹配得分
        
        Args:
            enterprise: 企业信息字典
            keywords: 关键词列表
            
        Returns:
            tuple: (得分, 匹配关键词列表)
        """
        score = 0.0
        matched_keywords = []
        
        # 将企业信息拼接为文本
        enterprise_text = enterprise_to_document(enterprise).lower()
        
        # 1. 关键词匹配得分（权重：60%）
        keyword_score = 0
        for keyword in keywords:
            if keyword.lower() in enterprise_text:
                keyword_score += 1
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)
        
        if keywords:
            keyword_score = (keyword_score / len(keywords)) * 60
        
        # 2. 领域编号精确匹配得分（权重：40%）
        field_score = 0
        
        # 从关键词中识别领域编号（如 "4.", "2.1"）
        field_patterns = re.findall(r'\d+\.\d+|\d+\.', ' '.join(keywords))
        
        enterprise_fields = []
        if enterprise.get("一级领域"):
            enterprise_fields.append(enterprise["一级领域"])
        if enterprise.get("二级领域"):
            enterprise_fields.append(enterprise["二级领域"])
        
        for pattern in field_patterns:
            for field in enterprise_fields:
                if pattern in field or field.startswith(pattern.replace(".", "")):
                    field_score += 1
                    break
        
        if field_patterns:
            field_score = (field_score / len(field_patterns)) * 40
        
        # 总分
        total_score = keyword_score + field_score
        
        return min(total_score, 100.0), matched_keywords

    def _layer1_match_text(self, enterprise: Dict) -> str:
        """混合检索第一层：仅用二级领域 + 企业主要产品做字面相关。"""
        a = enterprise.get("二级领域") or ""
        b = enterprise.get("企业主要产品") or ""
        return f"{a} {b}".strip()

    def _calculate_layer1_match_score(self, enterprise: Dict, keywords: List[str]) -> tuple:
        matched_keywords: List[str] = []
        enterprise_text = self._layer1_match_text(enterprise).lower()
        if not enterprise_text.strip():
            return 0.0, matched_keywords

        keyword_score = 0
        for keyword in keywords:
            if keyword.lower() in enterprise_text:
                keyword_score += 1
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

        if keywords:
            keyword_score = (keyword_score / len(keywords)) * 60

        field_score = 0
        field_patterns = re.findall(r"\d+\.\d+|\d+\.", " ".join(keywords))
        enterprise_fields: List[str] = []
        if enterprise.get("二级领域"):
            enterprise_fields.append(enterprise["二级领域"])
        if enterprise.get("企业主要产品"):
            enterprise_fields.append(enterprise["企业主要产品"])

        for pattern in field_patterns:
            for field in enterprise_fields:
                low = field.lower()
                if pattern in low or low.startswith(pattern.replace(".", "")):
                    field_score += 1
                    break

        if field_patterns:
            field_score = (field_score / len(field_patterns)) * 40

        total_score = keyword_score + field_score
        return min(total_score, 100.0), matched_keywords

    def search_layer1_ranked(
        self, query: str, cap: int = None
    ) -> List[Dict]:
        """
        第一层关键词漏斗：仅在「二级领域 + 企业主要产品」上打分排序，
        取前 cap 条作为向量子集候选（得分全为 0 时仍保留全部企业顺序以兜底）。
        """
        cap = cap if cap is not None else LAYER1_CANDIDATE_CAP
        keywords = self._extract_keywords(query)
        scored: List[tuple] = []
        for enterprise in self.enterprises:
            s, mk = self._calculate_layer1_match_score(enterprise, keywords)
            scored.append((s, enterprise, mk))
        scored.sort(key=lambda x: (-x[0], x[1].get("id", 0)))

        positives = [t for t in scored if t[0] > 0]
        zeros = [t for t in scored if t[0] <= 0]
        ordered = positives + zeros

        seen_ids = set()
        merged: List[tuple] = []
        for t in ordered:
            eid = t[1].get("id")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)
            merged.append(t)
            if len(merged) >= cap:
                break

        # 若 cap 大于当前企业数，已全部收录；若不足 cap（理论上不会），不再重复

        out: List[Dict] = []
        for s, enterprise, mk in merged:
            meta = {k: enterprise.get(k, "") for k in ["企业名称", "省", "市", "区/县", "地区门槛", "一级领域", "二级领域", "企业主要产品"]}
            meta["enterprise_id"] = str(enterprise.get("id", ""))
            out.append(
                {
                    "content": enterprise_to_document(enterprise),
                    "metadata": meta,
                    "score": round(s, 2),
                    "matched_keywords": mk,
                }
            )
        return out

    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        关键词检索企业
        
        Args:
            query: 查询文本（通常是简历文本）
            top_k: 返回的企业数量，默认使用config中的TOP_K
            
        Returns:
            List[Dict]: 企业列表，每个企业包含：
                - content: 企业信息文档
                - metadata: 企业元数据
                - score: 匹配得分（0-100）
                - matched_keywords: 匹配的关键词
        """
        top_k = top_k or TOP_K
        
        # 1. 提取关键词
        keywords = self._extract_keywords(query)
        print(f"提取到关键词: {', '.join(keywords[:10])}...")
        
        # 2. 计算所有企业的匹配得分
        results = []
        for enterprise in self.enterprises:
            score, matched_keywords = self._calculate_match_score(enterprise, keywords)
            
            if score > 0:  # 只保留有匹配的企业
                meta = {k: enterprise.get(k, "") for k in ["企业名称", "省", "市", "区/县", "地区门槛", "一级领域", "二级领域", "企业主要产品"]}
                meta["enterprise_id"] = str(enterprise.get("id", ""))
                results.append({
                    "content": enterprise_to_document(enterprise),
                    "metadata": meta,
                    "score": round(score, 2),
                    "matched_keywords": matched_keywords
                })
        
        # 3. 按得分排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # 4. 返回Top-K
        return results[:top_k]
    
    def search_with_expansion(self, query: str, top_k: int = 15) -> List[Dict]:
        """
        检索并自动扩展（如果结果不足）
        
        Args:
            query: 查询文本
            top_k: 目标企业数量
            
        Returns:
            List[Dict]: 企业列表（可能大于top_k）
        """
        # 第一轮：精确检索
        results = self.search(query, top_k=top_k)
        
        # 如果结果不足，降低阈值重新检索
        if len(results) < 8:
            print(f"⚠️ 第一轮检索仅获得 {len(results)} 家企业，启动第二轮扩大检索...")
            
            # 使用更少的关键词重新检索
            keywords = self._extract_keywords(query, top_k=10)  # 只取前10个关键词
            print(f"使用更少关键词重试: {', '.join(keywords[:5])}...")
            
            results = self.search(query, top_k=top_k * 2)
        
        return results[:top_k]
    
    def get_enterprise_by_name(self, name: str) -> Optional[Dict]:
        """
        根据企业名称精确查询
        
        Args:
            name: 企业名称
            
        Returns:
            Optional[Dict]: 企业信息，未找到返回None
        """
        for enterprise in self.enterprises:
            if enterprise.get("企业名称") == name:
                meta = {k: enterprise.get(k, "") for k in ["企业名称", "省", "市", "区/县", "地区门槛", "一级领域", "二级领域", "企业主要产品"]}
                meta["enterprise_id"] = str(enterprise.get("id", ""))
                return {
                    "content": enterprise_to_document(enterprise),
                    "metadata": meta,
                }
        
        return None
    
    def get_info(self) -> Dict:
        """
        获取检索器信息
        
        Returns:
            Dict: 包含企业数量等信息
        """
        return {
            "企业数量": len(self.enterprises) if self.enterprises else 0,
            "检索方式": "keyword",
            "数据来源": self.excel_path
        }


def build_keyword_searcher(excel_path: Optional[str] = None) -> KeywordSearch:
    """
    快速构建关键词检索器的便捷函数
    
    Args:
        excel_path: Excel文件路径
        
    Returns:
        KeywordSearch: 已初始化的检索器对象
    """
    return KeywordSearch(excel_path=excel_path)


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    print("=" * 60)
    print("测试关键词检索模块（纯标准库版）")
    print("=" * 60)
    
    # 1. 构建检索器
    searcher = build_keyword_searcher()
    
    # 2. 测试检索
    test_query = "生物医药 药物研发 化学制药 博士"
    print(f"\n测试查询: {test_query}")
    results = searcher.search(test_query, top_k=5)
    
    print(f"\n检索到 {len(results)} 家企业：")
    print("-" * 60)
    for i, e in enumerate(results, 1):
        print(f"\n{i}. {e['metadata']['企业名称']}")
        print(f"   匹配得分: {e['score']}")
        print(f"   一级领域: {e['metadata']['一级领域']}")
        print(f"   二级领域: {e['metadata']['二级领域']}")
        print(f"   匹配关键词: {', '.join(e['matched_keywords'][:5])}")
    
    # 3. 显示检索器信息
    info = searcher.get_info()
    print("\n" + "=" * 60)
    print("检索器信息：")
    print("=" * 60)
    for k, v in info.items():
        print(f"{k}: {v}")
