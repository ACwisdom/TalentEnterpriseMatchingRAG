"""
企业库数据处理模块
功能：读取Excel、结构化、准备向量化
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from typing import List, Dict
from src.config import ENTERPRISE_EXCEL, ENTERPRISE_FIELDS, USE_WEIGHTED_INDEX_DOC


def load_enterprise_db(excel_path: str = None) -> List[Dict]:
    """
    读取企业库Excel，返回结构化数据
    
    Args:
        excel_path: Excel文件路径，默认使用config中的路径
        
    Returns:
        List[Dict]: 企业列表，每个企业是一个字典
    """
    if excel_path is None:
        excel_path = ENTERPRISE_EXCEL
    
    print(f"正在读取企业库: {excel_path}")
    
    # 读取Excel
    df = pd.read_excel(excel_path)
    
    # 验证字段
    missing_fields = [f for f in ENTERPRISE_FIELDS if f not in df.columns]
    if missing_fields:
        raise ValueError(f"Excel缺少字段: {missing_fields}")
    
    # 转换为字典列表
    enterprises = []
    for idx, row in df.iterrows():
        enterprise = {}
        for field in ENTERPRISE_FIELDS:
            value = row[field]
            # 处理NaN值
            enterprise[field] = str(value) if pd.notna(value) else ""
        
        # 添加唯一ID
        enterprise["id"] = idx
        enterprises.append(enterprise)
    
    print(f"成功读取 {len(enterprises)} 家企业")
    return enterprises


def enterprise_to_document(enterprise: Dict) -> str:
    """
    将企业信息拼接为一个文档（用于向量化）
    
    Args:
        enterprise: 企业字典
        
    Returns:
        str: 拼接后的文档文本
    """
    parts = []
    
    # 按优先级拼接字段
    if enterprise.get("企业名称"):
        parts.append(f"企业名称: {enterprise['企业名称']}")
    
    if enterprise.get("一级领域"):
        parts.append(f"一级领域: {enterprise['一级领域']}")
    
    if enterprise.get("二级领域"):
        parts.append(f"二级领域: {enterprise['二级领域']}")
    
    if enterprise.get("企业主要产品"):
        parts.append(f"主要产品: {enterprise['企业主要产品']}")
    
    if enterprise.get("省") or enterprise.get("市"):
        location = f"{enterprise.get('省', '')}{enterprise.get('市', '')}{enterprise.get('区/县', '')}"
        parts.append(f"所在地: {location}")
    
    if enterprise.get("地区门槛"):
        parts.append(f"地区门槛: {enterprise['地区门槛']}")
    
    if enterprise.get("政府给介绍"):
        parts.append(f"政府介绍: {enterprise['政府给介绍']}")
    
    if enterprise.get("企业官方/第三方/新闻介绍"):
        parts.append(f"企业介绍: {enterprise['企业官方/第三方/新闻介绍']}")
    
    return "\n".join(parts)


def enterprise_to_index_document(enterprise: Dict) -> str:
    """
    面向向量索引的加权叙事正文：核心领域与产品重复加权，其余字段单次叙述。
    用于 Chroma documents 与嵌入；展示与 Prompt 列表仍可用 enterprise_to_document。
    """
    chunks: List[str] = []
    name = (enterprise.get("企业名称") or "").strip()
    if name:
        chunks.append(f"【企业名称】{name}")

    l1 = (enterprise.get("一级领域") or "").strip()
    l2 = (enterprise.get("二级领域") or "").strip()
    core_line = f"一级领域：{l1}；二级领域：{l2}。" if (l1 or l2) else ""
    if core_line:
        chunks.append(f"【核心领域】{core_line}")
        chunks.append(f"【核心领域】{core_line}")

    main_prod = (enterprise.get("企业主要产品") or "").strip()
    if main_prod:
        chunks.append(f"【主要产品】{main_prod}")
        chunks.append(f"【主要产品】{main_prod}")

    loc = f"{enterprise.get('省', '')}{enterprise.get('市', '')}{enterprise.get('区/县', '')}".strip()
    if loc:
        chunks.append(f"【所在地】{loc}")
    th = (enterprise.get("地区门槛") or "").strip()
    if th:
        chunks.append(f"【地区门槛】{th}")
    gov = (enterprise.get("政府给介绍") or "").strip()
    if gov:
        chunks.append(f"【政府介绍】{gov}")
    intro = (enterprise.get("企业官方/第三方/新闻介绍") or "").strip()
    if intro:
        chunks.append(f"【企业介绍】{intro}")

    return "\n".join(chunks)


def _document_for_vector_index(enterprise: Dict) -> str:
    if USE_WEIGHTED_INDEX_DOC:
        return enterprise_to_index_document(enterprise)
    return enterprise_to_document(enterprise)


def prepare_documents(enterprises: List[Dict]) -> tuple:
    """
    准备向量化数据
    
    Args:
        enterprises: 企业列表
        
    Returns:
        tuple: (documents, metadatas, ids)
            - documents: 文档文本列表
            - metadatas: 元数据列表（用于检索后展示）
            - ids: 唯一ID列表
    """
    documents = []
    metadatas = []
    ids = []
    
    for enterprise in enterprises:
        # 向量索引用文档（加权叙事或扁平）
        doc = _document_for_vector_index(enterprise)
        documents.append(doc)
        
        # 元数据（用于检索后展示）
        metadata = {
            "企业名称": enterprise.get("企业名称", ""),
            "省": enterprise.get("省", ""),
            "市": enterprise.get("市", ""),
            "区/县": enterprise.get("区/县", ""),
            "地区门槛": enterprise.get("地区门槛", ""),
            "一级领域": enterprise.get("一级领域", ""),
            "二级领域": enterprise.get("二级领域", ""),
            "企业主要产品": enterprise.get("企业主要产品", ""),
            "政府给介绍": enterprise.get("政府给介绍", ""),
            "企业官方/第三方/新闻介绍": enterprise.get("企业官方/第三方/新闻介绍", "")
        }
        metadatas.append(metadata)
        
        # 唯一ID
        ids.append(str(enterprise["id"]))
    
    return documents, metadatas, ids


if __name__ == "__main__":
    # 测试代码
    enterprises = load_enterprise_db()
    
    print("\n=== 第一条记录 ===")
    print(enterprises[0])
    
    print("\n=== 向量化文档样例 ===")
    doc = enterprise_to_document(enterprises[0])
    print(doc)
    
    print("\n=== 准备向量化数据 ===")
    documents, metadatas, ids = prepare_documents(enterprises[:5])
    print(f"文档数量: {len(documents)}")
    print(f"第一个文档:\n{documents[0][:200]}...")
