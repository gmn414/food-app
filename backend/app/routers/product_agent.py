import asyncio
import json
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services import ai_engine

router = APIRouter(prefix="/api/v1/product-agent", tags=["product-agent"])

# ── Request Models ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    product_category: str = Field(..., description="产品品类名称，如'智能计数跳绳'")

class RegenerateStepRequest(BaseModel):
    product_category: str = Field(..., description="产品品类名称")
    step: int = Field(..., ge=1, le=7, description="要重新生成的步骤编号 1-7")
    current_results: dict = Field(default_factory=dict, description="当前所有步骤的结果 {step: content}")

# ── Step Definitions ────────────────────────────────────────────

STEPS = [
    {"step": 1, "name": "市场洞察", "icon": "📊", "max_tokens": 2048},
    {"step": 2, "name": "竞品拆解", "icon": "🔍", "max_tokens": 2048},
    {"step": 3, "name": "产品定义", "icon": "🎯", "max_tokens": 2048},
    {"step": 4, "name": "供应链辅助", "icon": "🏭", "max_tokens": 2048},
    {"step": 5, "name": "测试方案", "icon": "🧪", "max_tokens": 2048},
    {"step": 6, "name": "文案输出", "icon": "✍️", "max_tokens": 3072},
    {"step": 7, "name": "上市跟进", "icon": "🚀", "max_tokens": 2048},
]

# ── Prompt Templates ────────────────────────────────────────────

PROMPT_1 = """你是一位资深产品市场分析师。请针对产品品类「{product_category}」，输出一份结构化的市场洞察报告。

请严格按以下维度分析，每个维度用2-4句话，给出具体数据和趋势判断：

1. 市场规模与增长趋势
   - 全球市场规模（引用具体数字范围）
   - 年复合增长率（CAGR）
   - 主要增长驱动因素

2. 目标用户画像
   - 核心用户年龄、性别、收入水平
   - 主要使用场景（3-5个）
   - 购买动机与决策因素

3. 热门搜索关键词
   - Amazon站内搜索高频词（列出5-8个）
   - Google Trends趋势判断
   - 季节性搜索波动

4. 社交媒体热度
   - TikTok/Instagram/小红书/YouTube等平台话题量
   - 关键意见领袖（KOL）合作方向
   - 内容营销切入点

5. 市场机会与风险
   - 蓝海细分方向
   - 季节性窗口
   - 潜在风险与应对建议

请直接输出分析内容，不需要标题前缀。"""

PROMPT_2 = """你是一位资深竞品分析专家。请基于以下市场洞察，针对「{product_category}」品类，输出一份深度竞品拆解报告。

━━━ 市场洞察背景 ━━━
{market_insight}
━━━━━━━━━━━━━━━━━━━━

请严格按以下结构输出：

1. 头部竞品概览（表格形式，至少5个竞品）
   | 品牌/型号 | 价格带(USD) | 星级 | 评论数 | 核心卖点 |
   |-----------|-------------|------|--------|----------|

2. 核心卖点对比
   - 各竞品的主打卖点和差异化策略
   - 卖点的用户感知度分析

3. 用户评价关键词分析
   - 正面高频词TOP10及含义解读
   - 负面高频词TOP10及对应的用户不满点
   - 从中发现的改进机会

4. 价格带分布
   - 低端/中端/高端价格区间
   - 各价格带竞争强度
   - 建议定价区间

5. 市场空白点与机会
   - 竞品未满足的用户需求
   - 差异化的切入方向（至少3个）

请直接输出分析内容。"""

PROMPT_3 = """你是一位资深产品经理。请基于以下市场和竞品分析，为「{product_category}」输出完整的产品定义方案。

━━━ 市场洞察 ━━━
{market_insight}
━━━━━━━━━━━━━━━━

━━━ 竞品拆解 ━━━
{competitor_analysis}
━━━━━━━━━━━━━━━━

请严格按以下结构输出：

1. 产品定位
   - 一句话定位语
   - 目标用户画像（具体到使用场景）
   - 价格定位及理由

2. 5条核心卖点
   - 每条用一句话概括，需与竞品形成差异化
   - 每条标注是"功能创新"还是"体验升级"

3. 规格建议
   - 材质推荐及理由
   - 尺寸/重量建议
   - 颜色方案（3-5个颜色）
   - 包装方案建议

4. 竞品差异化对比表
   | 维度 | 本品 | 竞品A | 竞品B | 竞品C |
   |------|------|-------|-------|-------|
   （至少对比5个维度）

5. 产品路线图建议
   - V1.0 MVP功能
   - V2.0 迭代方向

请直接输出分析内容。"""

PROMPT_4 = """你是一位资深供应链管理专家。请基于以下产品定义，为「{product_category}」输出供应链辅助方案。

━━━ 产品定义 ━━━
{product_definition}
━━━━━━━━━━━━━━━━

请严格按以下结构输出：

1. 供应商沟通邮件模板
   - 主题行
   - 邮件正文（内容包括：公司简介、项目介绍、询价需求、合作意向、期望回复时间）
   - 中英文双语版本

2. 样品检验清单
   | 检验项目 | 检验标准 | 检验方法 | 判定标准 | 备注 |
   |----------|----------|----------|----------|------|
   （至少10个检验项目，涵盖外观、功能、安全、包装等方面）

3. 议价要点
   - 影响报价的核心因素（如材质、工艺、MOQ等）
   - 谈判策略建议（3-5条）
   - 常见价格陷阱及规避方法

4. 供应商评估维度
   - 资质审核要点
   - 生产能力评估
   - 交货周期参考

请直接输出分析内容。"""

PROMPT_5 = """你是一位资深产品测试与质量控制专家。请基于以下产品定义，为「{product_category}」输出测试方案。

━━━ 产品定义 ━━━
{product_definition}
━━━━━━━━━━━━━━━━

请严格按以下结构输出：

1. 小批量测试计划
   - 测试批次数量建议及理由
   - 每批次抽样比例
   - 测试周期安排（时间线）

2. 功能测试清单
   | 测试项目 | 测试方法 | 合格标准 | 优先级 |
   |----------|----------|----------|--------|
   （至少8个测试项目）

3. 用户测试方案
   - 测试用户招募条件（目标用户画像匹配）
   - 测试任务设计（3-5个核心使用场景）
   - 测试周期建议

4. 用户反馈收集模板
   | 评估维度 | 评分(1-5) | 具体意见 |
   |----------|-----------|----------|
   （至少8个评估维度，涵盖外观、功能、体验、包装、性价比等）

5. 问题分级与处理SOP
   - P0（致命缺陷）处理流程
   - P1（严重问题）处理流程
   - P2（一般问题）处理流程

请直接输出分析内容。"""

PROMPT_6 = """你是一位资深亚马逊Listing优化专家。请基于以下产品信息，为「{product_category}」输出完整的亚马逊文案方案。

━━━ 产品定义 ━━━
{product_definition}
━━━━━━━━━━━━━━━━

━━━ 市场洞察 ━━━
{market_insight}
━━━━━━━━━━━━━━━━

━━━ 竞品拆解 ━━━
{competitor_analysis}
━━━━━━━━━━━━━━━━

请严格按以下结构输出，不要遗漏任何部分：

【产品标题】
- 200字符以内
- 包含核心关键词
- 突出差异化卖点
- 符合亚马逊规范

【五点描述】
1. [要点1 — 聚焦核心功能和差异化优势，500字符内]
2. [要点2 — 聚焦材质/工艺/品质，500字符内]
3. [要点3 — 聚焦使用体验和便捷性，500字符内]
4. [要点4 — 聚焦适用场景和人群，500字符内]
5. [要点5 — 聚焦售后保障和品牌承诺，500字符内]

【产品描述】
- 300-500字
- 开头：场景化引入，激发用户共鸣
- 中段：产品功能与利益点展开
- 结尾：购买理由强化 + 行动号召
- 使用HTML标签格式化（<p>、<b>、<ul>、<li>）

【关键词列表】
- 核心关键词（5-8个）：搜索量最高的品类大词
- 长尾关键词（10-12个）：包含修饰属性的精准搜索词
- 场景关键词（5-8个）：用户使用场景相关搜索词

请确保所有内容质量达到可直接上架使用的标准。"""

PROMPT_7 = """你是一位资深电商运营与产品生命周期管理专家。请基于以下全部信息，为「{product_category}」输出上市跟进方案。

━━━ 市场洞察 ━━━
{market_insight}
━━━━━━━━━━━━━━━━

━━━ 竞品拆解 ━━━
{competitor_analysis}
━━━━━━━━━━━━━━━━

━━━ 产品定义 ━━━
{product_definition}
━━━━━━━━━━━━━━━━

请严格按以下结构输出：

1. 用户评价分析框架
   - 评价监控维度（至少6个）
   - 好评/差评分类标准
   - 差评预警机制与响应SOP
   - 好评率目标及提升策略

2. 产品优化方向建议
   - 基于竞品差评分析的产品改进优先级
   - 基于用户反馈的迭代路线图
   - 成本可控的快速优化项

3. 库存与生命周期管理
   - 新品期库存策略（安全库存建议）
   - 成熟期库存管理
   - 清仓/退市判断标准
   - 补货预警公式及参数建议

4. 运营节奏建议
   - 新品推广期（1-3个月）核心动作
   - 稳定增长期（4-12个月）核心动作
   - 成熟期（12个月+）竞争壁垒建设

5. 关键绩效指标（KPI）
   - 核心指标及目标值建议
   - 周报/月报监控维度

请直接输出分析内容。"""

# ── Prompt Builder ──────────────────────────────────────────────

def _build_prompt(step: int, product_category: str, results: dict) -> str:
    """Build the prompt for a given step, injecting context from completed steps."""
    ctx = results  # key: step number as str, value: result text

    def get(step_no: int) -> str:
        return ctx.get(str(step_no), "暂无数据")

    if step == 1:
        return PROMPT_1.format(product_category=product_category)

    elif step == 2:
        return PROMPT_2.format(
            product_category=product_category,
            market_insight=get(1),
        )

    elif step == 3:
        return PROMPT_3.format(
            product_category=product_category,
            market_insight=get(1),
            competitor_analysis=get(2),
        )

    elif step == 4:
        return PROMPT_4.format(
            product_category=product_category,
            product_definition=get(3),
        )

    elif step == 5:
        return PROMPT_5.format(
            product_category=product_category,
            product_definition=get(3),
        )

    elif step == 6:
        return PROMPT_6.format(
            product_category=product_category,
            product_definition=get(3),
            market_insight=get(1),
            competitor_analysis=get(2),
        )

    elif step == 7:
        return PROMPT_7.format(
            product_category=product_category,
            market_insight=get(1),
            competitor_analysis=get(2),
            product_definition=get(3),
        )

    raise ValueError(f"Unknown step: {step}")


# ── SSE Generator ───────────────────────────────────────────────

async def _generate_stream(product_category: str):
    all_results: dict[str, str] = {}

    for step_info in STEPS:
        step_num = step_info["step"]
        step_name = step_info["name"]
        max_tokens = step_info["max_tokens"]

        try:
            prompt = _build_prompt(step_num, product_category, all_results)
            messages = [{"role": "user", "content": prompt}]
            result = await ai_engine.chat(messages, temperature=0.7, max_tokens=max_tokens)
            all_results[str(step_num)] = result

            event = {
                "step": step_num,
                "total": 7,
                "name": step_name,
                "content": result,
                "status": "completed",
            }
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        except Exception as exc:
            error_event = {
                "step": step_num,
                "total": 7,
                "name": step_name,
                "status": "error",
                "content": f"生成失败: {str(exc)}",
            }
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'status': 'all_completed'}, ensure_ascii=False)}\n\n"


# ── Endpoints ───────────────────────────────────────────────────

@router.post("/generate")
async def generate(req: GenerateRequest):
    if not req.product_category.strip():
        raise HTTPException(status_code=400, detail="请输入产品品类名称")

    return StreamingResponse(
        _generate_stream(req.product_category.strip()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/regenerate-step")
async def regenerate_step(req: RegenerateStepRequest):
    if not req.product_category.strip():
        raise HTTPException(status_code=400, detail="请输入产品品类名称")

    step_num = req.step
    step_info = STEPS[step_num - 1]
    max_tokens = step_info["max_tokens"]

    prompt = _build_prompt(step_num, req.product_category.strip(), req.current_results)

    try:
        messages = [{"role": "user", "content": prompt}]
        result = await ai_engine.chat(messages, temperature=0.7, max_tokens=max_tokens)
        return {
            "step": step_num,
            "name": step_info["name"],
            "content": result,
            "status": "completed",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"步骤{step_num}重新生成失败: {str(exc)}")
