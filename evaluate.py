#!/usr/bin/env python3
"""
评测脚本 - 用于评估视频AI问答系统的性能
"""

import json
import time
import requests
import re
from typing import Dict, List, Any
import os
import sys


# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
AGENT_CHAT_URL = f"{API_BASE_URL}/api/v1/agent/chat"


def load_test_cases() -> List[Dict[str, Any]]:
    """加载测试用例数据"""
    try:
        with open('data/test_cases.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('test_cases', [])
    except FileNotFoundError:
        print("错误: 找不到测试数据文件 data/test_cases.json")
        return []
    except json.JSONDecodeError:
        print("错误: 测试数据文件格式错误")
        return []


def check_keywords(answer: str, expected_keywords: List[str]) -> float:
    """
    检查答案中关键词的覆盖率

    Args:
        answer: 系统生成的答案
        expected_keywords: 期望包含的关键词列表

    Returns:
        关键词覆盖率 (0.0 - 1.0)
    """
    if not expected_keywords:
        return 1.0

    found_count = 0
    for keyword in expected_keywords:
        if keyword.lower() in answer.lower():
            found_count += 1

    return found_count / len(expected_keywords)


def extract_citations(answer: str) -> int:
    """
    从答案中提取引用数量

    查找答案中的引用标记，如 [1], (来源:xxx) 等
    """
    # 匹配各种引用格式
    patterns = [
        r'\[\d+\]',  # [1], [2] 等
        r'\(来源:.*?\)',  # (来源:xxx)
        r'引用自.*?[\n\.]',  # 引用自xxx
        r'参考.*?[\n\.]',  # 参考xxx
    ]

    citations = 0
    for pattern in patterns:
        citations += len(re.findall(pattern, answer))

    return citations


def call_agent_api(question: str, use_mock: bool = False) -> Dict[str, Any]:
    """
    调用Agent API进行问答

    Args:
        question: 用户问题
        use_mock: 是否使用模拟数据（用于测试）

    Returns:
        包含答案和元数据的字典
    """
    if use_mock:
        # 使用模拟数据进行快速测试
        import random
        latency = random.uniform(500, 3000)
        time.sleep(latency / 1000)

        mock_answers = {
            "系统支持哪些视频文件格式?": "系统支持MP4、MOV、AVI、WebM和MKV等常见视频格式。",
            "如何上传视频文件进行处理?": "您可以通过上传接口上传视频文件，系统会自动将其加入处理队列进行转码。",
            "语音识别支持哪些语言?": "系统支持中文等多种语言，使用阿里FunASR引擎进行高精度语音识别。",
        }

        answer = mock_answers.get(question, f"关于'{question}'，系统使用RAG技术和向量检索进行智能问答。")
        tokens = random.randint(100, 800)

        return {
            "answer": answer,
            "metadata": {
                "latency_ms": latency,
                "total_tokens": tokens,
                "has_citations": random.choice([True, False])
            }
        }

    # 真实API调用
    start_time = time.time()

    try:
        response = requests.post(
            AGENT_CHAT_URL,
            json={"message": question},
            timeout=60
        )

        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            data = response.json()
            answer = data.get("response", "")

            # 尝试从metadata中获取token信息
            metadata = data.get("metadata", {})
            tokens = metadata.get("response_length", len(answer.split()))

            return {
                "answer": answer,
                "metadata": {
                    "latency_ms": latency_ms,
                    "total_tokens": tokens,
                    "processing_time": data.get("processing_time", 0),
                    "has_citations": extract_citations(answer) > 0
                }
            }
        else:
            print(f"API调用失败: {response.status_code} - {response.text}")
            return {
                "answer": "",
                "metadata": {
                    "latency_ms": latency_ms,
                    "total_tokens": 0,
                    "error": response.text
                }
            }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        print(f"API调用异常: {str(e)}")
        return {
            "answer": "",
            "metadata": {
                "latency_ms": latency_ms,
                "total_tokens": 0,
                "error": str(e)
            }
        }


def calculate_cost(avg_tokens: float, model_type: str = "doubao") -> float:
    """
    计算每个查询的平均成本

    Args:
        avg_tokens: 平均token数量
        model_type: 模型类型 (doubao/gpt4)
    """
    # 不同模型的定价（每1000 tokens的价格，单位：美元）
    pricing = {
        "doubao": 0.008,  # 火山引擎豆包模型
        "gpt4": 0.03,     # GPT-4
        "gpt35": 0.002    # GPT-3.5
    }

    cost_per_1k_tokens = pricing.get(model_type, 0.01)
    return (avg_tokens / 1000) * cost_per_1k_tokens


def evaluate_system(
    use_mock: bool = False,
    max_cases: int = None,
    difficulty_filter: str = None
) -> Dict[str, Any]:
    """
    执行系统评测

    Args:
        use_mock: 是否使用模拟数据（用于快速测试）
        max_cases: 最大测试用例数量（None表示全部）
        difficulty_filter: 难度过滤器 ("easy", "medium", "hard")

    Returns:
        包含评测指标的字典
    """
    test_cases = load_test_cases()
    if not test_cases:
        return {"error": "没有可用的测试用例"}

    # 应用难度过滤
    if difficulty_filter:
        test_cases = [c for c in test_cases if c.get("difficulty") == difficulty_filter]
        print(f"过滤到 {len(test_cases)} 个 '{difficulty_filter}' 难度的测试用例")

    # 限制测试用例数量
    if max_cases:
        test_cases = test_cases[:max_cases]

    results = []
    total_cases = len(test_cases)

    print(f"\n开始评测，共 {total_cases} 个测试用例...")
    print(f"API地址: {AGENT_CHAT_URL}")
    print(f"模式: {'模拟数据' if use_mock else '真实API调用'}\n")

    # 用于统计
    successful_cases = 0
    failed_cases = 0
    citations_found = 0

    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        print(f"[{i}/{total_cases}] 问题: {question[:60]}...")

        try:
            # 调用问答系统
            response = call_agent_api(question, use_mock=use_mock)

            # 检查是否有答案
            if not response["answer"]:
                print(f"  ⚠️  未获取到答案")
                failed_cases += 1
                continue

            # 检查关键词覆盖率
            accuracy = check_keywords(response["answer"], case["expected_keywords"])

            # 获取延迟和token信息
            latency = response["metadata"]["latency_ms"]
            tokens = response["metadata"]["total_tokens"]
            has_citations = response["metadata"].get("has_citations", False)

            if has_citations:
                citations_found += 1

            results.append({
                "id": case["id"],
                "question": question,
                "answer": response["answer"][:100] + "...",  # 只保存前100字符
                "accuracy": accuracy,
                "latency": latency,
                "tokens": tokens,
                "difficulty": case.get("difficulty", "unknown"),
                "has_citations": has_citations
            })

            successful_cases += 1
            print(f"  ✓ 准确率: {accuracy:.2%}, 延迟: {latency:.0f}ms, Tokens: {tokens}")

        except Exception as e:
            print(f"  ✗ 处理失败: {str(e)}")
            failed_cases += 1
            continue

    if not results:
        return {"error": "所有测试用例都失败了"}

    # 计算平均指标
    avg_accuracy = sum(r["accuracy"] for r in results) / len(results)
    avg_latency = sum(r["latency"] for r in results) / len(results)
    avg_tokens = sum(r["tokens"] for r in results) / len(results)
    cost_per_query = calculate_cost(avg_tokens)

    # 计算引用准确率（有引用的比例）
    citation_accuracy = citations_found / len(results) if results else 0

    # 按难度分组统计
    difficulty_stats = {}
    for difficulty in ["easy", "medium", "hard"]:
        difficulty_results = [r for r in results if r.get("difficulty") == difficulty]
        if difficulty_results:
            difficulty_stats[difficulty] = {
                "count": len(difficulty_results),
                "avg_accuracy": sum(r["accuracy"] for r in difficulty_results) / len(difficulty_results),
                "avg_latency_ms": sum(r["latency"] for r in difficulty_results) / len(difficulty_results)
            }

    # 构建评测结果
    evaluation_result = {
        "accuracy": round(avg_accuracy, 2),
        "avg_latency_ms": round(avg_latency),
        "avg_tokens": round(avg_tokens),
        "cost_per_query": round(cost_per_query, 4),
        "citation_accuracy": round(citation_accuracy, 2),
        "total_cases": total_cases,
        "successful_cases": successful_cases,
        "failed_cases": failed_cases,
        "difficulty_breakdown": difficulty_stats
    }

    return evaluation_result


def main():
    """主函数"""
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='视频AI问答系统评测工具')
    parser.add_argument('--mock', action='store_true', help='使用模拟数据进行快速测试')
    parser.add_argument('--max-cases', type=int, help='最大测试用例数量')
    parser.add_argument('--difficulty', choices=['easy', 'medium', 'hard'], help='只测试指定难度')
    parser.add_argument('--output', default='evaluation_result.json', help='结果输出文件')

    args = parser.parse_args()

    print("=" * 60)
    print("       视频AI问答系统评测工具 - QuickRewind")
    print("=" * 60)

    # 执行评测
    result = evaluate_system(
        use_mock=args.mock,
        max_cases=args.max_cases,
        difficulty_filter=args.difficulty
    )

    # 输出结果
    print("\n" + "=" * 60)
    print("                    评测结果")
    print("=" * 60)

    if "error" in result:
        print(f"❌ 评测失败: {result['error']}")
        sys.exit(1)

    # 格式化输出关键指标
    print(f"\n📊 核心指标:")
    print(f"  准确率 (Accuracy):           {result['accuracy']:.2%}")
    print(f"  平均延迟 (Avg Latency):      {result['avg_latency_ms']:.0f} ms")
    print(f"  平均Token (Avg Tokens):      {result['avg_tokens']:.0f}")
    print(f"  单次成本 (Cost per Query):   ${result['cost_per_query']:.4f}")
    print(f"  引用准确率 (Citation Acc):   {result['citation_accuracy']:.2%}")

    print(f"\n📈 测试统计:")
    print(f"  总用例数:   {result['total_cases']}")
    print(f"  成功数:     {result['successful_cases']}")
    print(f"  失败数:     {result['failed_cases']}")

    if result.get('difficulty_breakdown'):
        print(f"\n📊 难度分析:")
        for difficulty, stats in result['difficulty_breakdown'].items():
            print(f"  {difficulty.capitalize():8s}: 准确率 {stats['avg_accuracy']:.2%}, "
                  f"延迟 {stats['avg_latency_ms']:.0f}ms ({stats['count']}个用例)")

    # 保存完整结果到文件
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完整评测结果已保存到: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()