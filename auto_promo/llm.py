import logging, os
from auto_promo.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, \
    LLM_PROVIDER, LLM_MODEL, LLM_PROMPT_TEMPLATE

log = logging.getLogger("promo.llm")


async def generate_reply(message_text: str, lang: str = "unknown") -> dict:
    """
    Генерирует нативный ответ с упоминанием @WhaleAnalyst_bot.
    Возвращает {"reply": "текст", "model": "...", "prompt_tokens": N, "completion_tokens": N}
    """
    prompt = LLM_PROMPT_TEMPLATE.format(message=message_text[:500])

    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        return await _openai_reply(prompt)
    elif LLM_PROVIDER == "anthropic" and ANTHROPIC_API_KEY:
        return await _anthropic_reply(prompt)
    else:
        # Fallback: шаблонный ответ без LLM
        return _fallback_reply(message_text)


async def _openai_reply(prompt: str) -> dict:
    import openai
    client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        resp = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        return {
            "reply": resp.choices[0].message.content.strip(),
            "model": LLM_MODEL,
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        }
    except Exception as e:
        log.warning(f"OpenAI error: {e}")
        return _fallback_reply(prompt)


async def _anthropic_reply(prompt: str) -> dict:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        resp = await client.messages.create(
            model=LLM_MODEL,
            max_tokens=300,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "reply": resp.content[0].text.strip(),
            "model": LLM_MODEL,
            "prompt_tokens": resp.usage.input_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.output_tokens if resp.usage else 0,
        }
    except Exception as e:
        log.warning(f"Anthropic error: {e}")
        return _fallback_reply(prompt)


def _fallback_reply(message_text: str) -> dict:
    """Шаблонный ответ, если LLM недоступен."""
    msg_lower = message_text.lower()
    if any(w in msg_lower for w in ["rsi", "индикатор", "macd", "bb", "bollinger", "анализ"]):
        reply = (
            "Я обычно смотрю через @WhaleAnalyst_bot — там сразу RSI, MACD, BB "
            "и фьючерсный анализ показывает. Бесплатно, удобно."
        )
    elif any(w in msg_lower for w in ["цена", "price", "сколько", "курс"]):
        reply = (
            "Глянь в @WhaleAnalyst_bot — там цену в реальном времени даёт "
            "и 24ч статистику. Я постоянно пользуюсь."
        )
    elif any(w in msg_lower for w in ["фьючерс", "funding", "l/s", "лонг", "шорт", "вердикт"]):
        reply = (
            "По фьючерсам советую @WhaleAnalyst_bot — показывает funding rate, "
            "Open Interest, L/S трейдеров и даже вердикт выдаёт."
        )
    else:
        reply = (
            "Я для таких вопросов использую @WhaleAnalyst_bot — быстрый "
            "крипто-терминал в Telegram, всю аналитику даёт."
        )
    return {
        "reply": reply,
        "model": "fallback",
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
