import os
import asyncio
from typing import List, Dict, Any
from groq import Groq
from config import Config

class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.GROQ_MODEL
        self.temperature = Config.GROQ_TEMPERATURE

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=500
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Groq API error: {e}")
            return "Извините, произошла ошибка генерации ответа."

    async def analyze_conversation(self, dialogue: str, scenario: str) -> str:
        analysis_prompt = f"""
        Ты - старший медицинский консультант с 15-летним опытом.
        Проанализируй диалог между пациентом и консультантом по следующему сценарию:

        СЦЕНАРИЙ: {scenario}

        ДИАЛОГ:
        {dialogue}

        Проанализируй строго по критериям:

        🔬 **Профессиональная компетентность (1-10 баллов)**
        - Корректность медицинской информации
        - Соблюдение протоколов консультирования
        - Точность рекомендаций

        🗣️ **Коммуникативные навыки (1-10 баллов)**
        - Эмпатия и поддержка пациента
        - Ясность объяснений
        - Активное слушание
        - Управление диалогом

        ⚠️ **Основные ошибки (максимум 3):**
        1. ...
        2. ...
        3. ...

        💡 **Рекомендации по улучшению:**
        - Конкретные советы для следующей консультации
        - Фразы для улучшения
        - Техники, которые стоит применить

        🎯 **Общая оценка и вывод:**
        Краткое резюме с ключевыми моментами для развития.

        Форматируй ответ с эмодзи и четкой структурой.
        """

        messages = [
            {"role": "system", "content": "Ты эксперт в медицинской коммуникации и обучении консультантов."},
            {"role": "user", "content": analysis_prompt}
        ]

        return await self.generate_response(messages)

groq_client = GroqClient()
