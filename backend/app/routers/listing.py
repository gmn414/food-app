import asyncio
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.ai_engine import chat

router = APIRouter(prefix="/api/v1", tags=["listing"])


class GenerateListingRequest(BaseModel):
    product_name: str = Field(..., description="产品名称")
    selling_points: str = Field(..., description="核心卖点")
    target_user: str = Field(..., description="目标用户")
    specifications: str = Field(..., description="产品规格")


class GenerateListingResponse(BaseModel):
    title: str
    bullet_points: str
    description: str
    keywords: str


TITLE_PROMPT = """你是一个亚马逊Listing优化专家。请根据以下产品信息生成一个亚马逊产品标题。

要求：
- 标题长度控制在200个字符以内
- 包含核心关键词，提高搜索可见性
- 突出产品核心卖点
- 符合亚马逊标题规范，不要使用促销性词语（如"Best Seller"、"Hot Sale"）

产品信息：
- 产品名称：{product_name}
- 核心卖点：{selling_points}
- 目标用户：{target_user}
- 产品规格：{specifications}

请只返回标题文本，不要包含任何解释或引号。"""

BULLET_POINTS_PROMPT = """你是一个亚马逊Listing优化专家。请根据以下产品信息生成5个产品要点描述(Bullet Points)。

要求：
- 每个要点长度控制在500个字符以内
- 突出产品核心卖点和差异化优势
- 解决目标用户的痛点和需求
- 使用简洁有力的语言，便于快速阅读
- 每个要点聚焦一个核心利益点

产品信息：
- 产品名称：{product_name}
- 核心卖点：{selling_points}
- 目标用户：{target_user}
- 产品规格：{specifications}

请返回5个要点，每行一个，格式为：
1. [要点1]
2. [要点2]
3. [要点3]
4. [要点4]
5. [要点5]

只返回要点列表，不要包含其他解释。"""

DESCRIPTION_PROMPT = """你是一个亚马逊Listing优化专家。请根据以下产品信息生成产品描述(Product Description)。

要求：
- 总字数在300-500字之间
- 使用HTML标签进行格式化（<p>、<b>、<ul>、<li>）
- 先描述产品解决的问题或满足的需求
- 再介绍产品的主要功能特性
- 最后描述为什么这款产品是最佳选择
- 语气专业且有说服力，但不夸张

产品信息：
- 产品名称：{product_name}
- 核心卖点：{selling_points}
- 目标用户：{target_user}
- 产品规格：{specifications}

请只返回产品描述内容（包含HTML标签），不要包含其他解释。"""

KEYWORDS_PROMPT = """你是一个亚马逊Listing优化专家。请根据以下产品信息生成搜索关键词。

要求：
- 总共15-20个关键词
- 分为"核心关键词"和"长尾关键词"两类
- 核心关键词：搜索量高、竞争大的核心词（5-8个）
- 长尾关键词：包含修饰词、搜索意图更精准的长尾词（10-12个）
- 关键词之间用逗号分隔
- 不要重复或高度相似的词

产品信息：
- 产品名称：{product_name}
- 核心卖点：{selling_points}
- 目标用户：{target_user}
- 产品规格：{specifications}

请按以下格式返回：
【核心关键词】
keyword1, keyword2, keyword3, ...

【长尾关键词】
longtail keyword 1, longtail keyword 2, longtail keyword 3, ...

只返回上述格式的关键词，不要包含其他解释。"""



def _parse_title(raw: str) -> str:
    raw = raw.strip().strip('"').strip("'").strip()
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    for line in lines:
        if not line.startswith("#") and not line.startswith("标题"):
            cleaned = line.strip('"').strip("'").strip()
            if len(cleaned) > 10:
                return cleaned
    return raw


def _parse_bullet_points(raw: str) -> str:
    raw = raw.strip()
    lines = raw.split("\n")
    bullets = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^[\d]+[\.\)、]\s*(.*)", stripped)
        if match:
            bullets.append(match.group(1).strip())
        elif stripped.startswith("- ") or stripped.startswith("• "):
            bullets.append(stripped[2:].strip())
    if bullets:
        return "\n".join(f"{i}. {b}" for i, b in enumerate(bullets, 1))
    return raw


def _parse_description(raw: str) -> str:
    return raw.strip()


def _parse_keywords(raw: str) -> str:
    return raw.strip()


@router.post("/generate-listing", response_model=GenerateListingResponse)
async def generate_listing(req: GenerateListingRequest):
    if not req.product_name.strip():
        raise HTTPException(status_code=400, detail="请输入产品名称")
    if not req.selling_points.strip():
        raise HTTPException(status_code=400, detail="请输入核心卖点")

    params = dict(
        product_name=req.product_name.strip(),
        selling_points=req.selling_points.strip(),
        target_user=req.target_user.strip() or "通用用户",
        specifications=req.specifications.strip() or "标准规格",
    )

    prompts = [
        ("title", TITLE_PROMPT.format(**params)),
        ("bullet_points", BULLET_POINTS_PROMPT.format(**params)),
        ("description", DESCRIPTION_PROMPT.format(**params)),
        ("keywords", KEYWORDS_PROMPT.format(**params)),
    ]

    parsers = {
        "title": _parse_title,
        "bullet_points": _parse_bullet_points,
        "description": _parse_description,
        "keywords": _parse_keywords,
    }

    async def call_one(field: str, prompt_text: str) -> tuple[str, str]:
        messages = [
            {"role": "user", "content": prompt_text},
        ]
        result = await chat(messages, temperature=0.7, max_tokens=2048)
        return field, parsers[field](result)

    tasks = [call_one(field, text) for field, text in prompts]
    results = dict(await asyncio.gather(*tasks))

    return GenerateListingResponse(
        title=results.get("title", ""),
        bullet_points=results.get("bullet_points", ""),
        description=results.get("description", ""),
        keywords=results.get("keywords", ""),
    )
