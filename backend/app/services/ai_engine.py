import asyncio
import json
import re
from typing import Optional

from openai import AsyncOpenAI

from ..config import (
    AI_MAX_RETRIES,
    AI_TIMEOUT_SECONDS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

_cached_kb: Optional[dict[str, dict]] = None
_cached_kb_list: Optional[list[dict]] = None


def _load_kb() -> tuple[dict[str, dict], list[dict]]:
    global _cached_kb, _cached_kb_list
    if _cached_kb is None:
        from pathlib import Path
        kb_path = Path(__file__).resolve().parent.parent.parent / "food_knowledge.json"
        with open(kb_path, "r", encoding="utf-8") as f:
            foods = json.load(f)
        _cached_kb = {item["food_name"]: item for item in foods}
        _cached_kb_list = foods
    return _cached_kb, _cached_kb_list


def _search_kb(keyword: str) -> list[dict]:
    _, kb_list = _load_kb()
    results = []
    kw = keyword.lower()
    for food in kb_list:
        if kw in food["food_name"].lower() or kw in food["category"].lower():
            results.append(food)
        elif any(kw in food["food_name"].lower()):
            results.append(food)
    return results[:10]


_client: Optional[AsyncOpenAI] = None
_api_available = True


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=AI_TIMEOUT_SECONDS,
        )
    return _client


def is_api_available() -> bool:
    return _api_available


async def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1024) -> str:
    global _api_available

    if not _api_available:
        return _local_fallback(messages)

    client = get_client()
    last_error = None
    for attempt in range(AI_MAX_RETRIES):
        try:
            response = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            _api_available = True
            return response.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < AI_MAX_RETRIES - 1:
                delay = 2**attempt
                await asyncio.sleep(delay)

    _api_available = False
    return _local_fallback(messages)


# ─── Local Fallback Engine ────────────────────────────

def _extract_user_message(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m["role"] == "user":
            return m["content"]
    return ""


def _extract_system_context(messages: list[dict]) -> str:
    for m in messages:
        if m["role"] == "system":
            return m["content"]
    return ""


def _local_fallback(messages: list[dict]) -> str:
    sys_ctx = _extract_system_context(messages)
    user_msg = _extract_user_message(messages)

    # Detect intent: analyze request
    if "今日饮食记录" in user_msg and "返回JSON格式" in user_msg:
        return _fallback_analyze(user_msg, messages)

    # Detect intent: score request
    if "评估这顿" in user_msg and "减脂友好程度" in user_msg:
        return _fallback_score(user_msg)

    # Detect intent: food recognition
    if "识别食物" in sys_ctx or "食物描述" in user_msg:
        return _fallback_recognize(user_msg)

    # General chat
    return _fallback_chat(user_msg, sys_ctx)


def _parse_nutrition_from_prompt(text: str) -> dict:
    total_cal = 0
    total_p = 0
    total_c = 0
    total_f = 0
    daily_target = 1800
    protein_target = 135
    records = []

    m = re.search(r"热量(\d+\.?\d*)千卡.*?目标(\d+\.?\d*)千卡", text)
    if m:
        total_cal = float(m.group(1))
        daily_target = float(m.group(2))

    m = re.search(r"蛋白质(\d+\.?\d*)g.*?目标(\d+\.?\d*)g", text)
    if m:
        total_p = float(m.group(1))
        protein_target = float(m.group(2))

    m = re.search(r"碳水(\d+\.?\d*)g", text)
    if m:
        total_c = float(m.group(1))

    m = re.search(r"脂肪(\d+\.?\d*)g", text)
    if m:
        total_f = float(m.group(1))

    # Parse individual records
    for line in text.split("\n"):
        meal_match = re.match(r"(早餐|午餐|晚餐|加餐): (.+?) (\d+)g \((\d+\.?\d*)千卡\)", line)
        if meal_match:
            records.append({
                "meal": meal_match.group(1),
                "food": meal_match.group(2),
                "grams": int(meal_match.group(3)),
                "cal": float(meal_match.group(4)),
            })

    return {
        "total_calories": total_cal,
        "total_protein_g": total_p,
        "total_carbs_g": total_c,
        "total_fat_g": total_f,
        "daily_target": daily_target,
        "protein_target": protein_target,
        "records": records,
    }


def _fallback_analyze(user_msg: str, messages: list[dict]) -> str:
    """Rule-based diet analysis when AI is unavailable."""
    data = _parse_nutrition_from_prompt(user_msg)
    cal = data["total_calories"]
    target = data["daily_target"]
    protein = data["total_protein_g"]
    protein_target = data["protein_target"]
    records = data["records"]

    issues = []
    suggestions = []

    # Calorie analysis
    cal_pct = cal / target * 100 if target > 0 else 100
    if cal > target * 1.2:
        issues.append(f"今日热量摄入严重超标，超出目标{(cal - target):.0f}千卡（{cal_pct - 100:.0f}%）")
        suggestions.append("明天适当控制总热量，建议摄入目标值减少200-300千卡来平衡")
    elif cal > target:
        issues.append(f"热量稍微超出目标{(cal - target):.0f}千卡")
        suggestions.append("明天减少约100千卡摄入，增加20分钟有氧运动")
    elif cal < target * 0.6:
        issues.append(f"热量摄入偏低，仅达目标的{cal_pct:.0f}%，可能影响基础代谢")
        suggestions.append(f"建议每餐至少保证{target * 0.3:.0f}千卡，避免过度节食")
    else:
        suggestions.append("热量控制不错，继续保持当前节奏")

    # Protein analysis
    pct_p = protein / protein_target * 100 if protein_target > 0 else 100
    if pct_p < 80:
        issues.append(f"蛋白质摄入不足（{protein:.0f}g/{protein_target:.0f}g，仅达{pct_p:.0f}%）")
        suggestions.append("增加优质蛋白来源：鸡胸肉、虾仁、鸡蛋、豆腐都是低卡高蛋白的好选择")
    elif pct_p > 120:
        issues.append(f"蛋白质摄入偏高（{protein:.0f}g/{protein_target:.0f}g）")

    # Meal pattern analysis
    dinner_cal = sum(r["cal"] for r in records if "晚" in r["meal"])
    total_cal = cal or 1
    if dinner_cal / total_cal > 0.4 and total_cal > 0:
        issues.append(f"晚餐热量占比过高（{dinner_cal / total_cal * 100:.0f}%），建议控制在30%以内")
        suggestions.append("晚餐以蔬菜和优质蛋白为主，主食减半")

    # Food category analysis
    _, kb_list = _load_kb()
    high_cal_foods = [f for f in kb_list if f["calories_per_100g"] > 250]
    high_cal_names = {f["food_name"] for f in high_cal_foods}
    for r in records:
        if r["food"] in high_cal_names:
            issues.append(f"{r['meal']}的{r['food']}热量较高（{r['cal']:.0f}千卡），建议适量控制")
            break

    # Veggie check
    veggie_keywords = ["菜", "蔬", "西兰花", "菠菜", "番茄", "黄瓜", "胡萝卜", "白菜", "生菜", "芹菜", "冬瓜", "青椒", "豆芽", "茄子"]
    has_veggie = any(any(v in r["food"] for v in veggie_keywords) for r in records)
    if not has_veggie:
        issues.append("今日蔬菜摄入偏少，建议每餐至少有一拳蔬菜")
        suggestions.append("每餐搭配一份蔬菜：西兰花、菠菜、番茄都是低卡营养佳品")

    if not issues:
        issues.append("整体饮食搭配较为均衡，没有明显问题")

    # Score
    score = 10
    if cal > target * 1.1:
        score -= 2
    elif cal > target:
        score -= 1
    if pct_p < 80:
        score -= 2
    if dinner_cal / (total_cal or 1) > 0.4:
        score -= 1
    if not has_veggie:
        score -= 1
    score = max(1, min(10, score))

    if cal == 0:
        score = 5

    summary_map = {
        range(9, 11): "今日表现优秀！热量和营养素都在理想范围内，继续保持！",
        range(7, 9): "今日表现不错，部分细节可以优化，整体方向正确。",
        range(5, 7): "今日饮食有改进空间，关注蛋白质摄入和蔬菜搭配。",
        range(1, 5): "今日饮食需要较大调整，建议重新审视食物选择。",
    }
    summary = f"您今日摄入{cal:.0f}千卡（目标{target:.0f}千卡）。" + next(
        (v for k, v in summary_map.items() if score in k),
        "请关注饮食结构优化。",
    )

    return json.dumps({
        "summary": summary,
        "issues": issues,
        "suggestions": suggestions[:3],
        "score": score,
    }, ensure_ascii=False)


def _fallback_score(user_msg: str) -> str:
    """Rule-based meal scoring when AI is unavailable."""
    # Parse foods from the message
    food_pattern = re.findall(r"-\s*(.+?):\s*(\d+)g", user_msg)
    meal_match = re.search(r"评估这顿(早餐|午餐|晚餐|加餐)", user_msg)
    meal_type = meal_match.group(1) if meal_match else "餐"

    _, kb_list = _load_kb()
    kb_map = _load_kb()[0]

    good_points = []
    bad_points = []
    total_cal = 0
    total_protein = 0
    has_veggie = False
    has_lean_protein = False
    has_high_fat = False
    veggie_categories = ["蔬菜", "水果"]
    high_fat_threshold = 200

    for food_name, grams in food_pattern:
        food_data = kb_map.get(food_name, {})
        if not food_data:
            for name, data in kb_map.items():
                if food_name in name or name in food_name:
                    food_data = data
                    break

        if food_data:
            ratio = float(grams) / 100
            cal = food_data["calories_per_100g"] * ratio
            protein = food_data["protein_per_100g"] * ratio
            total_cal += cal
            total_protein += protein

            if food_data["category"] in veggie_categories:
                has_veggie = True
            if food_data["calories_per_100g"] < 150 and food_data["protein_per_100g"] > 15:
                has_lean_protein = True
            if food_data["calories_per_100g"] > high_fat_threshold:
                has_high_fat = True

    if has_veggie:
        good_points.append("有蔬菜搭配，增加膳食纤维和饱腹感")
    if has_lean_protein:
        good_points.append("含有优质低脂蛋白，有助于维持肌肉量")
    if total_protein < 15:
        bad_points.append("蛋白质不足，建议增加鸡胸肉、鱼虾或豆腐")
    if has_high_fat:
        bad_points.append("含有高热量食物，建议减少或替换为低卡替代品")
    if total_cal > 600:
        bad_points.append(f"本餐热量约{total_cal:.0f}千卡偏高，建议控制在500千卡以内")
    if len(food_pattern) < 3:
        bad_points.append("食物种类偏少，建议增加蔬菜和蛋白质来源")

    if not good_points:
        good_points.append("记录了一餐，持续记录能更好地追踪进展")
    if not bad_points:
        bad_points.append("整体搭配合理")

    # Score
    score = 7
    if has_veggie: score += 1
    if has_lean_protein: score += 1
    if has_high_fat: score -= 2
    if total_cal > 600: score -= 1
    if len(food_pattern) < 2: score -= 1
    score = max(1, min(10, score))

    # Improvement
    if has_high_fat and not has_lean_protein:
        improvement = f"把高热量食物换成清蒸鱼或鸡胸肉，可减少约150-200千卡"
    elif not has_veggie:
        improvement = f"加一份蔬菜（如西兰花或菠菜），增加饱腹感且仅多30-40千卡"
    elif total_cal > 600:
        improvement = f"减少主食1/3份量，或把部分换成粗粮，可减少约100千卡"
    else:
        improvement = f"这顿{meal_type}整体不错，继续保持即可"

    return json.dumps({
        "score": score,
        "good_points": good_points,
        "bad_points": bad_points,
        "improvement": improvement,
    }, ensure_ascii=False)


def _fallback_recognize(user_msg: str) -> str:
    """Local food recognition when AI is unavailable."""
    # Try to extract food name
    _, kb_list = _load_kb()

    amount_match = re.search(r"(\d+)\s*克", user_msg)
    amount_g = float(amount_match.group(1)) if amount_match else 200.0

    for food in kb_list:
        if food["food_name"] in user_msg:
            cal = food["calories_per_100g"] * amount_g / 100
            return json.dumps({
                "food_name": food["food_name"],
                "category": food["category"],
                "amount_g": amount_g,
                "calories_per_100g": food["calories_per_100g"],
                "protein_per_100g": food["protein_per_100g"],
                "carbs_per_100g": food["carbs_per_100g"],
                "fat_per_100g": food["fat_per_100g"],
            }, ensure_ascii=False)

    return json.dumps({"error": "未识别到食物"}, ensure_ascii=False)


def _fallback_chat(user_msg: str, sys_ctx: str) -> str:
    """Local rule-based chat when DeepSeek API is unavailable."""
    msg = user_msg.strip()

    # Extract user context from system message
    height_match = re.search(r"身高(\d+)", sys_ctx)
    weight_match = re.search(r"体重(\d+)", sys_ctx)
    target_match = re.search(r"目标体重(\d+)", sys_ctx)
    cal_match = re.search(r"日目标(\d+)千卡", sys_ctx)
    today_cal_match = re.search(r"已摄入：热量(\d+\.?\d*)千卡", sys_ctx)
    today_p_match = re.search(r"蛋白质(\d+\.?\d*)g", sys_ctx)

    height = int(height_match.group(1)) if height_match else 170
    weight = int(weight_match.group(1)) if weight_match else 70
    target_wt = int(target_match.group(1)) if target_match else 65
    daily_target = int(cal_match.group(1)) if cal_match else 1800
    today_cal = float(today_cal_match.group(1)) if today_cal_match else 0
    today_p = float(today_p_match.group(1)) if today_p_match else 0

    protein_goal = int(daily_target * 0.3 / 4)

    # Intent: 吃超了/超标
    if any(kw in msg for kw in ["吃超", "超标", "超了", "吃多了", "暴食"]):
        return (
            f"理解你今天的感觉 😊 偶尔一天吃超不用太焦虑，不会让你之前努力白费的。\n\n"
            f"明天这样调整：\n"
            f"1️⃣ 早餐正常吃（约{daily_target * 0.22:.0f}千卡）：燕麦+鸡蛋+牛奶\n"
            f"2️⃣ 午餐控制碳水（约{daily_target * 0.3:.0f}千卡）：鸡胸肉+西兰花+半碗米饭\n"
            f"3️⃣ 晚餐轻食为主（约{daily_target * 0.25:.0f}千卡）：豆腐蔬菜汤+红薯\n"
            f"4️⃣ 增加30分钟快走或慢跑，额外消耗约200-300千卡\n\n"
            f"关键是把今天的超额在接下来2-3天逐步平衡，而非一天极端节食。"
            f"你的基础代谢约{10 * weight + 6.25 * height - 5 * 25 + 5:.0f}千卡，"
            f"即使躺着不动也会消耗热量，不用慌 💪"
        )

    # Intent: 低卡晚餐/推荐
    if any(kw in msg for kw in ["低卡", "推荐", "吃什么", "晚餐", "午餐", "早餐", "食谱"]):
        meal_type = ""
        for mt in ["晚餐", "午餐", "早餐", "加餐"]:
            if mt in msg:
                meal_type = mt
                break

        _, kb_list = _load_kb()
        # Find low-cal foods
        low_cal_proteins = [f for f in kb_list
                            if f["calories_per_100g"] < 150 and f["protein_per_100g"] > 10]
        low_cal_veggies = [f for f in kb_list
                           if f["calories_per_100g"] < 40 and f["category"] in ["蔬菜", "水产"]]

        proteins = low_cal_proteins[:3]
        veggies = low_cal_veggies[:3]

        cal_per_meal = daily_target * (0.25 if "晚" in msg else 0.3)

        return (
            f"以下是一份约{cal_per_meal:.0f}千卡的{meal_type or '推荐'}搭配 🥗\n\n"
            f"🥩 蛋白质（选1-2种）：\n"
            + "".join(f"  • {p['food_name']} 150g — {p['calories_per_100g'] * 1.5:.0f}千卡，"
                      f"蛋白质{p['protein_per_100g'] * 1.5:.0f}g\n" for p in proteins) +
            f"\n🥬 蔬菜（选2-3种）：\n"
            + "".join(f"  • {v['food_name']} 150g — {v['calories_per_100g'] * 1.5:.0f}千卡\n" for v in veggies) +
            f"\n🍚 主食：半碗糙米饭(75g)或一个小红薯(150g) — 约90千卡\n\n"
            f"这样搭配的{meal_type or '一餐'}蛋白质充足、热量可控、饱腹感强。"
            f"烹饪建议：优先清蒸/水煮/少油快炒，避免红烧和油炸。"
        )

    # Intent: 火锅
    if any(kw in msg for kw in ["火锅", "烧烤", "外卖", "聚餐"]):
        food_type = next((kw for kw in ["火锅", "烧烤", "外卖", "聚餐"] if kw in msg), "聚餐")
        return (
            f"减脂期当然可以吃{food_type}！关键是「怎么吃」而不是「不能吃」 🔥\n\n"
            f"吃{food_type}的减脂策略：\n"
            f"1️⃣ 汤底选清汤/菌菇/番茄锅，避开麻辣牛油锅（一勺牛油≈100千卡）\n"
            f"2️⃣ 涮菜优先：各种蔬菜、豆腐、菌菇类随便吃，热量极低\n"
            f"3️⃣ 蛋白质选择：虾滑、鱼片、鸡胸片、瘦牛肉片，避开肥牛/五花\n"
            f"4️⃣ 蘸料控制：香油碟换成醋+蒜泥+葱花+少量酱油，省下约80千卡\n"
            f"5️⃣ 不喝汤：火锅汤底含大量油脂和嘌呤\n\n"
            f"按这个策略，一顿{food_type}可以控制在500-600千卡，完全不耽误减脂！\n"
            f"第二天体重上涨通常是因为高钠导致的水肿，1-2天就会恢复，不用担心 ⚖️"
        )

    # Intent: 蛋白质
    if any(kw in msg for kw in ["蛋白质", "蛋白", "增肌"]):
        _, kb_list = _load_kb()
        high_protein = sorted(
            [f for f in kb_list if f["protein_per_100g"] > 8 and f["calories_per_100g"] < 300],
            key=lambda x: x["protein_per_100g"] / max(x["calories_per_100g"], 1), reverse=True,
        )[:8]

        return (
            f"你的每日蛋白质目标是{protein_goal}g，目前已摄入{today_p:.0f}g，" +
            (f"还差{max(0, protein_goal - today_p):.0f}g\n\n" if today_p < protein_goal else "已达到目标 👏\n\n") +
            f"以下是高蛋白低热量的优质来源（按蛋白质/热量比排序）：\n\n"
            + "".join(
                f"  • {f['food_name']} — 每100g含{f['protein_per_100g']}g蛋白质，"
                f"仅{f['calories_per_100g']}千卡\n"
                for f in high_protein
            ) +
            f"\n💡 小技巧：每餐先吃蛋白质和蔬菜，最后吃主食，"
            f"这样蛋白质吸收更好，饱腹感也更持久。"
        )

    # Intent: 分析/看今天的
    if any(kw in msg for kw in ["分析", "今天", "今日", "总结"]):
        if today_cal > 0:
            pct_cal = today_cal / daily_target * 100
            pct_p = today_p / protein_goal * 100
            return (
                f"📊 今日饮食概况（本地分析）：\n\n"
                f"🔥 热量：{today_cal:.0f}/{daily_target}千卡（{pct_cal:.0f}%）\n"
                f"🥩 蛋白质：{today_p:.0f}/{protein_goal}g（{pct_p:.0f}%）\n\n"
                + (f"⚡ 热量尚在目标范围内，不错！\n" if today_cal < daily_target else
                   f"⚠️ 热量已超出目标{(today_cal - daily_target):.0f}千卡，下午和晚上注意控制\n")
                + f"💪 蛋白质达标率{pct_p:.0f}%，"
                + (
                   ("继续补充蛋白质" if pct_p < 80 else
                    "还需努力" if pct_p < 100 else "已达标，很棒！")) +
                f"\n\n💡 建议：每餐保证一掌大小的蛋白质（鸡胸肉/鱼虾/豆腐）+ 一拳蔬菜 + 一拳主食，这是最简单好记的搭配法。"
            )
        else:
            return (
                f"今天还没有饮食记录哦 📝\n\n"
                f"先告诉我你吃了什么，我帮你分析。可以直接输入食物名"
                f"（如「鸡胸肉150克」）或描述（如「一个苹果」），"
                f"系统会自动计算热量和营养素。\n\n"
                f"你的每日目标是{daily_target}千卡，蛋白质目标{protein_goal}g。"
                f"现在开始记录吧 💪"
            )

    # Intent: 减肥/减脂
    if any(kw in msg for kw in ["减肥", "减脂", "瘦", "减重"]):
        bmr = 10 * weight + 6.25 * height - 5 * 25 + 5
        return (
            f"很高兴你想科学减脂！根据你的数据（{height}cm/{weight}kg）：\n\n"
            f"📐 BMI：{weight / ((height / 100) ** 2):.1f}\n"
            f"🔥 基础代谢约：{bmr:.0f}千卡/天\n"
            f"🎯 每日热量目标：{daily_target}千卡（已设500千卡缺口）\n"
            f"🏁 目标体重：{target_wt}kg（需减{weight - target_wt:.1f}kg）\n\n"
            f"减脂核心原则：\n"
            f"1️⃣ 制造热量缺口但不饿着自己 — 吃够蛋白质和蔬菜\n"
            f"2️⃣ 每周减0.5-1kg是健康速度，太快容易反弹\n"
            f"3️⃣ 力量训练+有氧结合，保住肌肉才能维持代谢\n"
            f"4️⃣ 记录每一餐，「数据驱动」比「靠意志力」有效10倍\n\n"
            f"预计{weight - target_wt:.0f}kg需要{(weight - target_wt) / 0.5:.0f}-{(weight - target_wt) / 0.25:.0f}周。"
            f"坚持记录，我会陪你每一步 💚"
        )

    # Intent: general food lookup
    foods = _search_kb(msg)
    if foods and len(msg) < 20:
        lines = [f"🔍 找到以下相关食物：\n"]
        for f in foods[:5]:
            lines.append(
                f"  • {f['food_name']}（{f['category']}）— "
                f"{f['calories_per_100g']}千卡/100g | "
                f"蛋白质{f['protein_per_100g']}g | 碳水{f['carbs_per_100g']}g | 脂肪{f['fat_per_100g']}g"
            )
        return "\n".join(lines)

    # Default: helpful reply
    return (
        f"你好！我是AI减脂营养师（当前为本地模式，DeepSeek API暂不可用，"
        f"但我可以基于84种食物知识库为你提供基础建议）。\n\n"
        f"你可以问我：\n"
        f"• 「今天吃超了怎么办」— 获取调整方案\n"
        f"• 「推荐一份低卡晚餐」— 获取具体食物搭配\n"
        f"• 「减脂期能吃火锅吗」— 获取聚餐策略\n"
        f"• 「如何补充蛋白质」— 获取高蛋白食物清单\n"
        f"• 「帮我分析今天的饮食」— 查看今日总结\n\n"
        f"你的身高{height}cm，体重{weight}kg，日目标{daily_target}千卡。"
        f"今天已摄入{today_cal:.0f}千卡，蛋白质{today_p:.0f}g。"
        f"告诉我你想了解什么？ 💚"
    )


# ─── Prompt builders (kept unchanged) ───────────────

def build_system_prompt(role: str) -> str:
    if role == "nutritionist":
        return (
            "你是一位专业、亲切的AI减脂营养师。你拥有营养学硕士学位，擅长：\n"
            "1. 分析食物营养构成，估算热量和三大营养素\n"
            "2. 根据用户饮食记录给出精准的减脂建议\n"
            "3. 用数据驱动的方式帮助用户达成减脂目标\n"
            "4. 使用积极鼓励的语气，但保持专业客观\n"
            "回复要求：\n"
            "- 具体可执行，避免泛泛而谈\n"
            "- 涉及数字时基于营养学计算\n"
            "- 使用中文回复，语气温暖但专业\n"
            "- 如果用户偏离减脂目标，善意提醒但不过度指责"
        )
    return "You are a helpful assistant."


def build_user_context(user_profile: Optional[dict] = None) -> str:
    if not user_profile:
        return "用户尚未设置个人资料。"
    return (
        f"用户信息：身高{user_profile['height_cm']}cm，体重{user_profile['weight_kg']}kg，"
        f"目标体重{user_profile['target_weight_kg']}kg，"
        f"每日热量目标{user_profile['daily_calorie_target']}千卡。"
    )
