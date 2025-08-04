#!/bin/bash

# 设置变量 - 请替换为你的实际信息
BASE_URL="http://localhost:8000"
USERNAME="Yang"  # 替换为你注册的用户名
PASSWORD="qwer1234."  # 替换为你的密码
POLL_INTERVAL=5  # 轮询间隔(秒)
MAX_WAIT=300     # 最大等待时间(秒)

echo "=== 开始 API 测试 ==="
echo "BASE_URL: $BASE_URL"
echo "USERNAME: $USERNAME"
echo ""

# 1. 登录获取 token
echo "1. 正在登录..."
RESPONSE=$(curl -s -X POST ${BASE_URL}/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"${USERNAME}\", \"password\": \"${PASSWORD}\"}")

echo "登录响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 检查登录是否成功 - 修改为检查 key 字段
if echo "$RESPONSE" | grep -q "key"; then
    echo "✅ 登录成功"
    
    # 提取 key (Token) - 修改为提取 key 字段
    AUTH_TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('key', ''))" 2>/dev/null)
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo "❌ 无法提取 token"
        exit 1
    fi
    
    echo "Auth Token (前50字符): ${AUTH_TOKEN:0:50}..."
    echo ""
else
    echo "❌ 登录失败"
    echo "请检查用户名和密码是否正确"
    exit 1
fi

# 2. 触发新闻简报生成
echo "2. 正在触发新闻简报生成..."
GENERATE_RESPONSE=$(curl -s -X POST ${BASE_URL}/api/ai/news-briefings/generate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token ${AUTH_TOKEN}" \
  -d '{"user_request": "请生成今日科技新闻简报"}')

echo "生成响应:"
echo "$GENERATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$GENERATE_RESPONSE"
echo ""

# 从生成响应中提取新创建的简报ID
NEW_REPORT_ID=$(echo "$GENERATE_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'id' in data:
        print(data['id'])
    elif 'report_id' in data:
        print(data['report_id'])
except:
    pass
" 2>/dev/null)

if [ -z "$NEW_REPORT_ID" ]; then
    echo "❌ 无法获取新简报ID，请检查响应格式"
    exit 1
fi

echo "🔄 新简报ID: $NEW_REPORT_ID"
echo ""

# 3. 等待简报生成完成
echo "3. 等待简报生成完成..."
echo "将每 $POLL_INTERVAL 秒检查一次，最多等待 $MAX_WAIT 秒"

wait_time=0
report_status="pending"

while [ "$report_status" != "completed" ] && [ $wait_time -lt $MAX_WAIT ]; do
    # 查询简报状态
    REPORT_DETAIL=$(curl -s -X GET ${BASE_URL}/api/ai/news-briefings/${NEW_REPORT_ID}/ \
      -H "Authorization: Token ${AUTH_TOKEN}")
    
    # 提取状态
    report_status=$(echo "$REPORT_DETAIL" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
    
    # 显示进度
    if [ "$report_status" = "completed" ]; then
        echo "✅ 简报生成完成!"
        break
    elif [ "$report_status" = "failed" ]; then
        echo "❌ 简报生成失败!"
        break
    else
        echo "⏳ 等待中... 已等待 $wait_time 秒，状态: $report_status"
        sleep $POLL_INTERVAL
        wait_time=$((wait_time + POLL_INTERVAL))
    fi
done

# 检查是否超时
if [ $wait_time -ge $MAX_WAIT ]; then
    echo "⚠️ 等待超时! 简报可能仍在生成中"
fi

# ... (前半部分代码保持不变) ...

# 4. 显示生成的简报详情
echo ""
echo "4. 显示新生成的简报详情 (ID: $NEW_REPORT_ID)..."
DETAIL_RESPONSE=$(curl -s -X GET ${BASE_URL}/api/ai/news-briefings/${NEW_REPORT_ID}/ \
  -H "Authorization: Token ${AUTH_TOKEN}")

echo "简报详情 (原始JSON):"
# 修改这里：使用新的python命令美化JSON并显示中文
echo "$DETAIL_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=4, ensure_ascii=False))" 2>/dev/null || echo "$DETAIL_RESPONSE"

# 提取并格式化显示关键内容
echo ""
echo "=== 简报内容摘要 ==="
# 修改这里：添加新闻文章列表的解析和显示
echo "$DETAIL_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"📅 生成时间: {data.get('generated_at', '未知')}\\n\")
    print(f\"📋 简报摘要:\\n{data.get('summary', '无摘要')}\\n\")
    print(f\"📊 市场情绪: {data.get('key_directions', {}).get('market_sentiment', '未提供')}\\n\")
    
    # 添加新闻文章列表的解析
    articles = data.get('news_articles', [])
    if articles:
        print(\"📰 相关新闻文章:\")
        for i, article in enumerate(articles, 1):
            title = article.get('title', '无标题')
            url = article.get('url', '#')
            print(f\"  {i}. {title}\")
            print(f\"     链接: {url}\")
        print(\"\") # 添加一个空行

    print(f\"🔍 完整简报:\\n{'-'*50}\\n{data.get('full_report_content', '无内容')}\\n{'-'*50}\")
except Exception as e:
    print(f\"解析简报内容出错: {e}\")
" 2>/dev/null

echo ""
echo "=== API 测试完成 ==="