import asyncio
from typing import List, Dict, Any
from datetime import datetime
from groq_client import groq_client
from scenarios import MEDICAL_SCENARIOS, get_scenario_by_id

class MedicalTrainer:
    def __init__(self):
        self.scenarios = MEDICAL_SCENARIOS
        self.active_sessions = {}

    def get_scenario_by_id(self, scenario_id: int):
        return get_scenario_by_id(scenario_id)

    def create_session(self, user_id: int, scenario_id: int):
        scenario = get_scenario_by_id(scenario_id)
        if not scenario:
            return None

        session = {
            "user_id": user_id,
            "scenario": scenario,
            "messages": [
                {"role": "system", "content": scenario["prompt"] + "\n\nОтвечай только от лица пациента. Будь естественным, не помогай консультанту."}
            ],
            "start_time": datetime.now(),
            "message_count": 0,
            "patient_messages": []
        }

        self.active_sessions[user_id] = session

        initial_messages = [
            {"role": "system", "content": "Начни разговор как пациент с первой проблемой. Будь естественным."},
            {"role": "user", "content": "Начни диалог как пациент"}
        ]

        return session

    def add_consultant_message(self, user_id: int, message: str):
        if user_id not in self.active_sessions:
            return False

        session = self.active_sessions[user_id]
        session["messages"].append({"role": "user", "content": message})
        session["message_count"] += 1

        return True

    async def generate_patient_response(self, user_id: int) -> str:
        if user_id not in self.active_sessions:
            return "Сессия завершена. Начните новую тренировку."

        session = self.active_sessions[user_id]

        response = await groq_client.generate_response(session["messages"])

        session["messages"].append({"role": "assistant", "content": response})
        session["patient_messages"].append(response)

        return response

    def get_dialogue_text(self, user_id: int) -> str:
        if user_id not in self.active_sessions:
            return ""

        session = self.active_sessions[user_id]
        dialogue_lines = []

        for msg in session["messages"]:
            if msg["role"] == "system":
                continue

            speaker = "👨‍⚕️ Консультант" if msg["role"] == "user" else "👤 Пациент"
            dialogue_lines.append(f"{speaker}: {msg['content']}")

        return "\n\n".join(dialogue_lines)

    async def analyze_session(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self.active_sessions:
            return {"error": "Сессия не найдена"}

        session = self.active_sessions[user_id]
        dialogue = self.get_dialogue_text(user_id)

        if not dialogue or session["message_count"] < 3:
            return {"error": "Недостаточно сообщений для анализа"}

        analysis = await groq_client.analyze_conversation(
            dialogue=dialogue,
            scenario=session["scenario"]["name"]
        )

        stats = {
            "total_messages": session["message_count"],
            "scenario": session["scenario"]["name"],
            "duration": (datetime.now() - session["start_time"]).seconds // 60,
            "analysis": analysis
        }

        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

        return stats

    def end_session(self, user_id: int):
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            return True
        return False

    def is_session_active(self, user_id: int) -> bool:
        return user_id in self.active_sessions

    def get_active_scenario(self, user_id: int):
        if user_id in self.active_sessions:
            return self.active_sessions[user_id]["scenario"]
        return None

medical_trainer = MedicalTrainer()
