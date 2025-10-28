import requests
import json
import time

# 测试视频搜索功能
def test_video_search():
    print("开始测试视频搜索功能...")
    
    # 搜索API端点
    search_url = "http://localhost:8000/api/v1/videos/search"
    
    # 测试查询
    test_query = "测试搜索"
    
    try:
        # 发送POST请求
        response = requests.post(
            search_url,
            json={"query": test_query},
            headers={"Content-Type": "application/json"}
        )
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            print(f"搜索成功! 状态码: {response.status_code}")
            print(f"搜索类型: {result.get('search_type', 'unknown')}")
            print(f"返回结果数量: {result.get('total', 0)}")
            print("\n响应详情:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 检查是否是向量搜索结果
            if result.get('search_type') == 'vector':
                print("\n✓ 成功调用了MCP向量搜索工具!")
                
                # 检查每个结果是否包含最佳匹配信息
                for i, item in enumerate(result.get('results', [])[:3], 1):
                    print(f"\n结果 {i}:")
                    print(f"  视频ID: {item.get('video_id')}")
                    print(f"  文件名: {item.get('filename')}")
                    if 'best_match' in item:
                        print(f"  最佳匹配内容: {item['best_match'].get('content')[:100]}...")
                        print(f"  最佳匹配时间戳: {item['best_match'].get('start_time')} - {item['best_match'].get('end_time')}")
                        print(f"  匹配分数: {item['best_match'].get('score')}")
            else:
                print("\n⚠ 未使用向量搜索，可能回退到了简单搜索")
                print(f"原因可能是: {result.get('error') or '未知'}")
                
        else:
            print(f"搜索失败! 状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            
    except Exception as e:
        print(f"发送请求时出错: {str(e)}")

# 测试不同类型的查询
def test_different_queries():
    queries = [
        "人工智能",
        "技术讲解",
        "视频编辑",
        "123456789"  # 测试不存在的内容
    ]
    
    print("\n" + "="*60)
    print("测试不同类型的查询")
    print("="*60)
    
    for query in queries:
        print(f"\n测试查询: '{query}'")
        try:
            response = requests.post(
                "http://localhost:8000/api/v1/videos/search",
                json={"query": query}
            )
            result = response.json()
            print(f"  搜索类型: {result.get('search_type', 'unknown')}")
            print(f"  结果数量: {result.get('total', 0)}")
        except Exception as e:
            print(f"  出错: {str(e)}")
        time.sleep(1)  # 避免请求过快

if __name__ == "__main__":
    print("视频搜索功能测试脚本")
    print("="*40)
    
    # 运行主要测试
    test_video_search()
    
    # 测试不同查询
    test_different_queries()
    
    print("\n测试完成!")