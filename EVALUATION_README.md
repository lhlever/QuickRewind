# QuickRewind 评测系统使用指南

## 概述

QuickRewind评测系统用于评估视频AI问答系统的性能，支持自动化测试和多维度指标统计。

## 核心指标

评测系统会生成以下核心指标：

```json
{
  "accuracy": 0.78,              // 准确率：关键词覆盖率的平均值
  "avg_latency_ms": 1250,        // 平均延迟：API响应时间（毫秒）
  "avg_tokens": 450,             // 平均Token：每次查询的token消耗
  "cost_per_query": 0.02,        // 单次成本：每次查询的费用（美元）
  "citation_accuracy": 0.95      // 引用准确率：答案包含引用的比例
}
```

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 运行评测

#### 方式一：使用Shell脚本（推荐）

```bash
# 完整评测（需要后端服务运行）
bash evaluate.sh

# 快速测试（使用模拟数据）
bash evaluate.sh --mock

# 只测试简单难度
bash evaluate.sh --easy

# 只测试前10个用例
bash evaluate.sh --max 10

# 组合使用
bash evaluate.sh --mock --medium --max 5
```

#### 方式二：直接运行Python脚本

```bash
# 完整评测
python3 evaluate.py

# 使用模拟数据
python3 evaluate.py --mock

# 指定难度
python3 evaluate.py --difficulty easy

# 限制用例数量
python3 evaluate.py --max-cases 10

# 自定义输出文件
python3 evaluate.py --output my_result.json
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--mock` | 使用模拟数据进行快速测试 | `--mock` |
| `--max-cases N` | 限制测试用例数量 | `--max-cases 10` |
| `--difficulty D` | 只测试指定难度（easy/medium/hard） | `--difficulty medium` |
| `--output FILE` | 指定结果输出文件 | `--output result.json` |
| `--help` | 显示帮助信息 | `--help` |

## 测试用例结构

测试用例存储在 `data/test_cases.json` 文件中：

```json
{
  "test_cases": [
    {
      "id": "Q001",
      "question": "系统支持哪些视频文件格式?",
      "expected_keywords": ["MP4", "MOV", "AVI", "WebM", "MKV"],
      "difficulty": "easy"
    }
  ]
}
```

### 字段说明

- `id`: 测试用例唯一标识
- `question`: 测试问题
- `expected_keywords`: 期望答案包含的关键词列表
- `difficulty`: 难度等级（easy/medium/hard）

## 评测流程

1. **加载测试用例**：从 `data/test_cases.json` 读取测试用例
2. **应用过滤**：根据参数过滤难度和数量
3. **调用API**：逐个调用Agent API获取答案
4. **计算准确率**：检查关键词覆盖率
5. **统计指标**：计算延迟、token、成本等
6. **生成报告**：输出评测结果并保存到JSON文件

## 准确率计算方法

准确率基于关键词覆盖率计算：

```python
accuracy = 匹配的关键词数量 / 期望关键词总数
```

例如：
- 期望关键词：["MP4", "MOV", "AVI", "WebM", "MKV"]（5个）
- 答案中包含：["MP4", "MOV", "AVI"]（3个）
- 准确率：3 / 5 = 0.60 (60%)

最终准确率是所有测试用例准确率的平均值。

## 引用准确率

系统会检测答案中是否包含引用标记，支持以下格式：

- `[1]`, `[2]` 等数字引用
- `(来源:xxx)` 格式
- `引用自xxx` 格式
- `参考xxx` 格式

引用准确率 = 包含引用的答案数 / 总答案数

## 成本计算

成本根据不同模型的定价计算：

| 模型 | 价格（每1000 tokens） |
|------|---------------------|
| 火山引擎豆包 (doubao) | $0.008 |
| GPT-4 | $0.03 |
| GPT-3.5 | $0.002 |

计算公式：`成本 = (平均token数 / 1000) × 单价`

## 输出结果示例

```json
{
  "accuracy": 0.78,
  "avg_latency_ms": 1250,
  "avg_tokens": 450,
  "cost_per_query": 0.0033,
  "citation_accuracy": 0.95,
  "total_cases": 50,
  "successful_cases": 48,
  "failed_cases": 2,
  "difficulty_breakdown": {
    "easy": {
      "count": 15,
      "avg_accuracy": 0.85,
      "avg_latency_ms": 1100
    },
    "medium": {
      "count": 20,
      "avg_accuracy": 0.75,
      "avg_latency_ms": 1250
    },
    "hard": {
      "count": 13,
      "avg_accuracy": 0.68,
      "avg_latency_ms": 1450
    }
  }
}
```

## 环境变量

可以通过环境变量配置API地址：

```bash
# 设置自定义API地址
export API_BASE_URL=http://your-server:8000

# 运行评测
bash evaluate.sh
```

## 故障排查

### 1. 无法连接到后端服务

**问题**：`API调用失败: Connection refused`

**解决**：
- 确保后端服务已启动：`cd backend && python -m uvicorn app.main:app --reload`
- 检查端口是否正确（默认8000）
- 或使用 `--mock` 参数进行模拟测试

### 2. 测试数据文件不存在

**问题**：`找不到测试数据文件 data/test_cases.json`

**解决**：
- 确保在项目根目录运行脚本
- 检查 `data/` 目录是否存在
- 确认 `test_cases.json` 文件存在

### 3. 依赖缺失

**问题**：`ModuleNotFoundError: No module named 'requests'`

**解决**：
```bash
pip install requests
```

## 高级用法

### 1. 批量测试不同配置

```bash
# 测试不同难度
for difficulty in easy medium hard; do
    echo "Testing $difficulty..."
    python3 evaluate.py --difficulty $difficulty --output "result_${difficulty}.json"
done
```

### 2. 性能基准测试

```bash
# 快速性能测试（前20个用例）
python3 evaluate.py --max-cases 20 --output benchmark.json
```

### 3. 持续集成

在CI/CD流程中使用：

```yaml
# .github/workflows/evaluation.yml
- name: Run Evaluation
  run: |
    python3 evaluate.py --max-cases 30
    # 检查准确率是否达标
    python3 -c "import json; result = json.load(open('evaluation_result.json')); exit(0 if result['accuracy'] >= 0.75 else 1)"
```

## 扩展测试用例

要添加新的测试用例，编辑 `data/test_cases.json`：

```json
{
  "id": "Q051",
  "question": "你的问题",
  "expected_keywords": ["关键词1", "关键词2", "关键词3"],
  "difficulty": "medium"
}
```

建议：
- 简单（easy）：基础概念、直接回答的问题（10-20个用例）
- 中等（medium）：需要一定技术理解的问题（20-30个用例）
- 困难（hard）：复杂技术、架构设计问题（10-20个用例）

## 贡献指南

欢迎贡献更多测试用例和改进建议！

1. Fork项目
2. 添加测试用例到 `data/test_cases.json`
3. 运行评测验证：`bash evaluate.sh --mock`
4. 提交Pull Request

## 许可证

MIT License
