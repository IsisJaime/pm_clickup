#!/usr/bin/env python3
"""
🤖 ASORT PM Bot
Bot de Project Management que:
- Envía reportes diarios de ClickUp a Telegram
- Tagea a las personas con sus pendientes
- Usa IA (Groq) para sugerir qué estudiar
- Gamifica el cumplimiento de tareas

Autor: AIT Team - Grupo Salinas
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional
import random

# ============== CONFIGURACIÓN ==============
CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")  # Opcional para IA

# Space FrontEnd en ClickUp
SPACE_ID = "901313702490"
WORKSPACE_ID = "9013739855"

# Mapeo ClickUp ID -> Telegram Username
USER_MAP = {
    "176560828": {"name": "Isis", "telegram": "@isisjaimev"},
    "75556718": {"name": "Salma", "telegram": "@salmareli"},
    "138138459": {"name": "Sergio", "telegram": "@DanielUnda"},
    "138142839": {"name": "Maguie", "telegram": "@MaguieCalderon"},
}

# Emojis y mensajes
EMOJIS = {
    "fire": "🔥",
    "warning": "⚠️",
    "check": "✅",
    "clock": "⏰",
    "star": "⭐",
    "rocket": "🚀",
    "brain": "🧠",
    "trophy": "🏆",
    "party": "🎉",
    "eyes": "👀",
    "muscle": "💪",
}

MOTIVATIONAL_MESSAGES = [
    "¡Están haciendo un trabajo increíble! {rocket}",
    "Sin presión hoy, ¡pero no bajen la guardia! {muscle}",
    "Día tranquilo, perfecto para adelantar trabajo {brain}",
    "¡El equipo AIT no para! {fire}",
    "Aprovechen para estudiar algo nuevo hoy {star}",
]

# GIFs por contexto
GIFS = {
    # Mañana tranquila, sin urgentes
    "morning_calm": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",   # Willy Wonka welcome
        "https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif",   # Good morning sparkles
        "https://media.giphy.com/media/xT9IgG50Lg7russbDa/giphy.gif",   # Stars shining
    ],
    # Mañana con tareas urgentes / vencidas
    "morning_urgent": [
        "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",    # Wake up!
        "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif",   # Alarm fire
        "https://media.giphy.com/media/xT9IgDECMFBzMsuDnW/giphy.gif",   # Urgente
    ],
    # Lunes (inicio de semana)
    "morning_monday": [
        "https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif",    # Monday motivation
        "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",   # Let's go!
        "https://media.giphy.com/media/xT9IgG50Lg7russbDa/giphy.gif",   # New week stars
    ],
    # Cierre tranquilo
    "evening_calm": [
        "https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif",    # Good night stars
        "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",   # Evening sparkles
        "https://media.giphy.com/media/xT9IgDECMFBzMsuDnW/giphy.gif",   # Night sky
    ],
    # Cierre con pendientes
    "evening_pending": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",    # Reminder
        "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif",   # Don't forget
        "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",    # Heads up
    ],
}

def get_gif(context: str) -> str:
    """Retorna un GIF aleatorio según el contexto"""
    return random.choice(GIFS.get(context, GIFS["morning_calm"]))

STUDY_PROMPTS = [
    "¿Ya revisaron documentación sobre {topic}?",
    "Tip: Este es buen momento para explorar {topic}",
    "¿Alguien ha investigado sobre {topic}? Compártannos",
    "Para la tarea que viene, valdría la pena leer sobre {topic}",
]


# ============== CLICKUP API ==============
class ClickUpClient:
    BASE_URL = "https://api.clickup.com/api/v2"
    
    def __init__(self, token: str):
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
    
    def get_tasks(self, space_id: str, include_closed: bool = False) -> list:
        """Obtiene todas las tareas del Space"""
        url = f"{self.BASE_URL}/space/{space_id}/task"
        params = {
            "include_closed": str(include_closed).lower(),
            "subtasks": "true"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("tasks", [])
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []
    
    def get_tasks_by_list(self, list_id: str) -> list:
        """Obtiene tareas de una lista específica"""
        url = f"{self.BASE_URL}/list/{list_id}/task"
        params = {"subtasks": "true"}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("tasks", [])
        except Exception as e:
            print(f"Error fetching tasks from list {list_id}: {e}")
            return []
    
    def get_space_lists(self, space_id: str) -> list:
        """Obtiene todas las listas de un Space (incluyendo folders)"""
        lists = []
        
        # Listas directas del space
        url = f"{self.BASE_URL}/space/{space_id}/list"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            lists.extend(response.json().get("lists", []))
        except Exception as e:
            print(f"Error fetching lists: {e}")
        
        # Folders y sus listas
        url = f"{self.BASE_URL}/space/{space_id}/folder"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            folders = response.json().get("folders", [])
            for folder in folders:
                lists.extend(folder.get("lists", []))
        except Exception as e:
            print(f"Error fetching folders: {e}")
        
        return lists


# ============== GROQ AI ==============
class GroqAI:
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def suggest_study_topics(self, task_name: str, task_description: str = "") -> str:
        """Genera sugerencias de qué estudiar basado en la tarea"""
        prompt = f"""Eres un coach técnico de un equipo de desarrollo Frontend/AWS.
        
Tarea próxima: {task_name}
Descripción: {task_description or 'No especificada'}

En máximo 2 oraciones cortas y en español casual, sugiere qué deberían estudiar o investigar para prepararse para esta tarea. 
Sé específico con tecnologías, documentación oficial, o conceptos clave.
No uses emojis. Sé directo y útil."""

        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error with Groq AI: {e}")
            return None
    
    def generate_motivation(self, completed_count: int, team_member: str) -> str:
        """Genera mensaje motivacional personalizado"""
        prompt = f"""Genera un mensaje corto (máximo 1 oración) en español casual y motivador para {team_member} 
que ha completado {completed_count} tareas a tiempo. Sé genuino, no cursi. Sin emojis."""

        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.8
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error with Groq AI: {e}")
            return f"¡Buen trabajo {team_member}!"


# ============== TELEGRAM ==============
class TelegramBot:
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, token: str):
        self.token = token
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Envía mensaje a Telegram"""
        url = f"{self.BASE_URL}{self.token}/sendMessage"
        
        try:
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            })
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False


# ============== REPORTES ==============
class PMReporter:
    def __init__(self):
        self.clickup = ClickUpClient(CLICKUP_API_TOKEN)
        self.telegram = TelegramBot(TELEGRAM_BOT_TOKEN)
        self.ai = GroqAI(GROQ_API_KEY) if GROQ_API_KEY else None
        self.today = datetime.now().date()
    
    def parse_due_date(self, due_date_str: str) -> Optional[datetime]:
        """Convierte timestamp de ClickUp a datetime"""
        if not due_date_str:
            return None
        try:
            # ClickUp usa timestamps en milisegundos
            timestamp = int(due_date_str) / 1000
            return datetime.fromtimestamp(timestamp)
        except:
            return None
    
    def get_assignee_telegram(self, task: dict) -> list:
        """Obtiene los usernames de Telegram de los asignados"""
        telegrams = []
        assignees = task.get("assignees", [])
        for assignee in assignees:
            user_id = str(assignee.get("id", ""))
            if user_id in USER_MAP:
                telegrams.append(USER_MAP[user_id]["telegram"])
        return telegrams
    
    def get_assignee_name(self, task: dict) -> str:
        """Obtiene el nombre del asignado"""
        assignees = task.get("assignees", [])
        if assignees:
            user_id = str(assignees[0].get("id", ""))
            if user_id in USER_MAP:
                return USER_MAP[user_id]["name"]
            return assignees[0].get("username", "Sin asignar")
        return "Sin asignar"
    
    def categorize_tasks(self, tasks: list) -> dict:
        """Categoriza tareas por urgencia"""
        categories = {
            "overdue": [],      # Vencidas
            "today": [],        # Vencen hoy
            "next_48h": [],     # Próximas 48 horas
            "this_week": [],    # Esta semana
            "upcoming": [],     # Próximas
            "no_date": []       # Sin fecha
        }
        
        for task in tasks:
            # Ignorar tareas completadas
            status = task.get("status", {}).get("status", "").lower()
            if status in ["complete", "closed", "done", "completado"]:
                continue
            
            due_date = self.parse_due_date(task.get("due_date"))
            
            if not due_date:
                categories["no_date"].append(task)
                continue
            
            due_date_only = due_date.date()
            days_until = (due_date_only - self.today).days
            
            if days_until < 0:
                categories["overdue"].append(task)
            elif days_until == 0:
                categories["today"].append(task)
            elif days_until <= 2:
                categories["next_48h"].append(task)
            elif days_until <= 7:
                categories["this_week"].append(task)
            else:
                categories["upcoming"].append(task)
        
        return categories
    
    def format_task(self, task: dict, include_date: bool = True) -> str:
        """Formatea una tarea para el mensaje"""
        name = task.get("name", "Sin nombre")
        url = task.get("url", "")
        telegrams = self.get_assignee_telegram(task)
        telegram_str = " ".join(telegrams) if telegrams else ""
        
        due_date = self.parse_due_date(task.get("due_date"))
        date_str = ""
        if include_date and due_date:
            date_str = f" ({due_date.strftime('%d/%m')})"
        
        link = f'<a href="{url}">{name}</a>' if url else name
        
        return f"• {link}{date_str} {telegram_str}"
    
    def generate_morning_report(self) -> str:
        """Genera el reporte de la mañana (9:30 AM)"""
        # Obtener todas las listas y sus tareas
        lists = self.clickup.get_space_lists(SPACE_ID)
        all_tasks = []
        
        for lst in lists:
            tasks = self.clickup.get_tasks_by_list(lst["id"])
            all_tasks.extend(tasks)
        
        if not all_tasks:
            return None
        
        categories = self.categorize_tasks(all_tasks)
        
        # Saludos estilo Willy Wonka
        morning_greetings = [
            f"🌟 <b>¡Buenos días, estrellitas!</b> ✨",
            f"⭐ <b>¡Despierten, mis pequeñas estrellitas!</b> 🌟",
            f"✨ <b>¡Buenos días a las estrellitas más brillantes del universo!</b> 🚀",
            f"🌠 <b>¡Ah, mis queridas estrellitas han llegado!</b> ⭐",
        ]

        # Construir mensaje
        lines = [random.choice(morning_greetings)]

        # GIF según contexto
        if self.today.weekday() == 0:
            gif_context = "morning_monday"
        elif categories["overdue"] or categories["today"]:
            gif_context = "morning_urgent"
        else:
            gif_context = "morning_calm"
        lines.append(f'<a href="{get_gif(gif_context)}">​</a>')
        lines.append(f"📅 {self.today.strftime('%A %d de %B, %Y')}\n")
        
        has_urgent = False
        
        # Tareas vencidas
        if categories["overdue"]:
            has_urgent = True
            lines.append(f"{EMOJIS['warning']} <b>VENCIDAS ({len(categories['overdue'])})</b>")
            for task in categories["overdue"][:5]:  # Max 5
                lines.append(self.format_task(task))
            if len(categories["overdue"]) > 5:
                lines.append(f"   ... y {len(categories['overdue']) - 5} más")
            lines.append("")
        
        # Vencen hoy
        if categories["today"]:
            has_urgent = True
            lines.append(f"{EMOJIS['fire']} <b>VENCEN HOY ({len(categories['today'])})</b>")
            for task in categories["today"]:
                lines.append(self.format_task(task, include_date=False))
            lines.append("")
        
        # Próximas 48 horas
        if categories["next_48h"]:
            lines.append(f"{EMOJIS['clock']} <b>Próximas 48 hrs ({len(categories['next_48h'])})</b>")
            for task in categories["next_48h"]:
                lines.append(self.format_task(task))
            lines.append("")
        
        # Esta semana (solo lunes)
        if self.today.weekday() == 0 and categories["this_week"]:
            lines.append(f"{EMOJIS['eyes']} <b>Esta semana ({len(categories['this_week'])})</b>")
            for task in categories["this_week"][:5]:
                lines.append(self.format_task(task))
            if len(categories["this_week"]) > 5:
                lines.append(f"   ... y {len(categories['this_week']) - 5} más")
            lines.append("")
        
        # Si no hay nada urgente
        if not has_urgent and not categories["next_48h"]:
            msg = random.choice(MOTIVATIONAL_MESSAGES)
            for key, emoji in EMOJIS.items():
                msg = msg.replace("{" + key + "}", emoji)
            lines.append(f"\n{EMOJIS['check']} <b>¡Sin entregas urgentes hoy!</b>")
            lines.append(msg)
        
        # Resumen
        total_pending = sum(len(v) for v in categories.values())
        lines.append(f"\n📊 <i>Total pendientes: {total_pending}</i>")
        
        return "\n".join(lines)
    
    def generate_evening_report(self) -> str:
        """Genera el check-in de la tarde (6:00 PM)"""
        lists = self.clickup.get_space_lists(SPACE_ID)
        all_tasks = []
        
        for lst in lists:
            tasks = self.clickup.get_tasks_by_list(lst["id"])
            all_tasks.extend(tasks)
        
        categories = self.categorize_tasks(all_tasks)
        
        # Saludos de cierre estilo Willy Wonka
        evening_greetings = [
            f"🌙 <b>¡Y así termina otro día mágico, estrellitas!</b> ✨",
            f"⭐ <b>¡Hora de cerrar, mis brillantes estrellitas!</b> 🌟",
            f"🌠 <b>¡El día llega a su fin, queridas estrellitas!</b> 💫",
        ]

        lines = [random.choice(evening_greetings)]

        # GIF según si hay pendientes o no
        if categories["overdue"] or categories["today"]:
            gif_context = "evening_pending"
        else:
            gif_context = "evening_calm"
        lines.append(f'<a href="{get_gif(gif_context)}">​</a>')
        lines.append(f"🌅 {self.today.strftime('%A %d/%m')}\n")
        
        # Si hay tareas para mañana o próximas
        next_tasks = categories["next_48h"] + categories["this_week"][:3]
        
        if next_tasks and self.ai:
            # Usar IA para sugerir qué estudiar
            next_task = next_tasks[0]
            suggestion = self.ai.suggest_study_topics(
                next_task.get("name", ""),
                next_task.get("description", "")
            )
            
            if suggestion:
                assignee = self.get_assignee_name(next_task)
                telegrams = self.get_assignee_telegram(next_task)
                telegram_str = " ".join(telegrams) if telegrams else ""
                
                lines.append(f"{EMOJIS['brain']} <b>Preparación para lo que viene:</b>")
                lines.append(f"Tarea: <i>{next_task.get('name', '')}</i>")
                lines.append(f"Para: {telegram_str}")
                lines.append(f"\n💡 <b>Sugerencia:</b> {suggestion}")
                lines.append("")
        
        # Si no hay entregas cercanas
        if not categories["today"] and not categories["overdue"]:
            lines.append(f"\n{EMOJIS['check']} <b>¡Buen día!</b> Sin entregas pendientes para hoy.")
            
            # Preguntar sobre progreso en tareas próximas
            if categories["next_48h"]:
                task = categories["next_48h"][0]
                telegrams = self.get_assignee_telegram(task)
                if telegrams:
                    lines.append(f"\n{EMOJIS['eyes']} {' '.join(telegrams)} ¿Cómo van con <i>{task.get('name', '')}?</i>")
        else:
            # Recordatorio de pendientes
            if categories["overdue"]:
                lines.append(f"\n{EMOJIS['warning']} Recuerden que hay {len(categories['overdue'])} tarea(s) vencida(s)")
        
        # Mensaje de cierre aleatorio
        closings = [
            "¡Descansen y recarguen su brillo, estrellitas! 🌙✨",
            "Mañana volvemos a brillar juntas 💪⭐",
            "¡Buen descanso, mis pequeñas estrellitas! 🌠",
            "¡Hasta mañana, equipo de estrellas! 🚀🌟",
        ]
        lines.append(f"\n{random.choice(closings)}")
        
        return "\n".join(lines)
    
    def send_morning_report(self):
        """Envía el reporte de la mañana"""
        report = self.generate_morning_report()
        if report:
            self.telegram.send_message(TELEGRAM_CHAT_ID, report)
            print("✅ Morning report sent!")
        else:
            print("⚠️ No tasks found or error generating report")
    
    def send_evening_report(self):
        """Envía el check-in de la tarde"""
        report = self.generate_evening_report()
        if report:
            self.telegram.send_message(TELEGRAM_CHAT_ID, report)
            print("✅ Evening report sent!")
        else:
            print("⚠️ Error generating evening report")


# ============== MAIN ==============
def main():
    """Punto de entrada principal"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python bot.py [morning|evening|test]")
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    reporter = PMReporter()
    
    if mode == "morning":
        reporter.send_morning_report()
    elif mode == "evening":
        reporter.send_evening_report()
    elif mode == "test":
        # Modo de prueba - imprime en consola
        print("=== MORNING REPORT ===")
        print(reporter.generate_morning_report())
        print("\n=== EVENING REPORT ===")
        print(reporter.generate_evening_report())
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
