# AI减脂营养师 (AI Fat Loss Nutritionist)

## 项目定位

面向减脂人群的AI饮食记录与营养分析工具。核心价值：用户拍照或输入吃了什么，AI自动识别食物、计算热量、分析营养、给出饮食评分和个性化建议，让减脂饮食管理从"靠意志力"变成"靠数据驱动"。

对标产品：Yazio / Lifesum / MyFitnessPal / 薄荷健康

## 用户画像

- **主要用户**：有减脂需求的20-40岁人群
- **核心痛点**：不知道吃了多少热量、营养素不均衡、缺乏个性化饮食建议
- **使用场景**：日常饮食记录、营养分析、减脂饮食咨询

## 功能架构

```
AI减脂营养师
├── 启动引导
│   ├── 身高体重输入 → 目标选择 → AI热量计算
│   └── 动画过渡 → 主页
├── 饮食记录（Tab1）
│   ├── 食物搜索（知识库 + AI识别）
│   ├── 食物添加（份量调节 + 餐次选择）
│   ├── 今日饮食列表（按餐次分组）
│   ├── 右滑删除
│   └── 底部汇总条（热量/蛋白质/碳水/脂肪）
├── 分析看板（Tab2）
│   ├── 营养素环形图（蛋白质/碳水/脂肪 三环）
│   ├── 本周热量趋势柱状图
│   ├── AI饮食评分
│   ├── AI改进建议列表
│   └── 近7天评分趋势折线图
├── AI营养师（Tab3）
│   ├── 多轮对话（上下文感知）
│   ├── 打字机效果
│   └── 快捷问题胶囊
├── 设置页
│   ├── 用户信息展示与编辑
│   ├── 热量目标调整
│   ├── 饮食偏好设置
│   └── 数据管理（清除/导出）
└── 底部导航栏（首页/分析/AI/我的）
```

## 技术栈

### 后端
- **Python 3.11+** / **FastAPI** — 异步Web框架，自动生成OpenAPI文档
- **SQLAlchemy 2.0** — ORM，SQLite数据库
- **DeepSeek API** (via openai SDK) — AI食物识别、饮食分析、多轮对话
- **Pydantic v2** — 数据验证与序列化

### 前端
- **原生 HTML/CSS/JS** — 无框架依赖，零构建步骤
- **Canvas API** — 营养素环形图、热量柱状图、评分趋势图
- **CSS 玻璃拟态 + 深色模式** — 对标顶级健康App设计

### 设计系统
- 375px宽度手机App风格居中展示
- 深色背景 `#0D1B0E` + 翠绿渐变主色调 `#1B5E20 → #4CAF50`
- 玻璃拟态卡片 `rgba(255,255,255,0.06)` + 毛玻璃效果
- 完整动画系统（呼吸、飞入、弹跳、打字机、涟漪）

## 项目结构

```
food-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI入口，CORS，路由注册
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # SQLAlchemy引擎
│   │   ├── models.py            # 数据模型（DietRecord, UserProfile, FoodKnowledge）
│   │   ├── schemas.py           # Pydantic请求/响应模型
│   │   ├── routers/
│   │   │   ├── food.py          # 食物识别 & 搜索
│   │   │   ├── diet.py          # 饮食记录CRUD
│   │   │   └── ai.py            # AI分析/评分/对话
│   │   └── services/
│   │       ├── ai_engine.py     # DeepSeek API封装（重试+超时）
│   │       ├── food_kb.py       # 食物知识库服务
│   │       └── nutrition.py     # 营养计算
│   ├── food_knowledge.json      # 84种中国常见食物预置数据
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 单页应用（3页面）
│   ├── css/
│   │   └── app.css              # 设计系统（~600行）
│   └── js/
│       ├── api-client.js        # API调用封装
│       ├── chart-utils.js       # Canvas图表绘制
│       └── app.js               # 应用逻辑（~850行）
└── docs/
    └── README.md                # 本文档
```

## 启动步骤

### 1. 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 配置DeepSeek API Key（可选，无Key时使用本地知识库）
# Windows PowerShell: $env:DEEPSEEK_API_KEY="your-key"
# Linux/Mac: export DEEPSEEK_API_KEY="your-key"

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 前端

直接用浏览器打开 `frontend/index.html`，或：

```bash
cd frontend
python -m http.server 3000
# 访问 http://127.0.0.1:3000
```

### 3. API文档

启动后端后访问：http://127.0.0.1:8000/docs

## 接口文档

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/food/recognize` | AI食物识别 |
| GET | `/api/v1/food/search?keyword=xxx` | 搜索食物库 |
| POST | `/api/v1/diet/record` | 记录饮食 |
| GET | `/api/v1/diet/today` | 今日汇总 |
| GET | `/api/v1/diet/weekly` | 本周每日热量 |
| DELETE | `/api/v1/diet/record/{id}` | 删除记录 |
| POST | `/api/v1/ai/analyze` | AI分析今日饮食 |
| POST | `/api/v1/ai/score` | AI单餐评分 |
| POST | `/api/v1/ai/chat` | AI多轮对话 |
| GET | `/api/v1/user/profile` | 获取用户资料 |
| POST | `/api/v1/user/profile` | 保存用户资料 |
| GET | `/api/v1/health` | 健康检查 |

## 食物知识库

预置84种中国常见食物，分8大类：

- **主食类**（12种）：米饭、馒头、面条、全麦面包、燕麦片、红薯等
- **肉类**（12种）：鸡胸肉、去皮鸡腿、猪瘦肉、红烧肉、牛肉瘦等
- **水产类**（8种）：三文鱼、虾仁、带鱼、鲈鱼等
- **蛋奶豆类**（8种）：鸡蛋、牛奶、无糖酸奶、豆腐等
- **蔬菜类**（12种）：西兰花、菠菜、番茄、黄瓜等
- **水果类**（10种）：苹果、香蕉、橙子、草莓等
- **零食饮料**（10种）：巧克力、薯片、奶茶等
- **中式菜肴**（12种）：宫保鸡丁、麻婆豆腐、西红柿炒蛋等

## 设计理念

### 数据驱动减脂
不只是记录，更是用AI分析数据、给出可执行的建议。用户知道每餐的热量与营养素构成，不再凭感觉吃饭。

### 渐进式体验
从启动引导的步骤式输入，到主页的饮食记录，再到AI分析和对话，体验层次递进，让用户逐步深入。

### 视觉激励
- 热量进度环颜色变化（绿→橙→红）
- AI评分大数字醒目展示
- 营养素达标率清晰可读
- 超标时红色抖动提醒

## License

MIT
