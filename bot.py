#!/usr/bin/env python3
"""
🤖 ASORT PM Bot v2
Bot de Project Management que:
- Envía reportes diarios de ClickUp a Telegram
- Tagea a las personas con sus pendientes
- Usa IA (Groq) para sugerir qué estudiar basado en TODA la info de la tarea
- Gamifica el cumplimiento de tareas

Autor: AIT Team - Grupo Salinas
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
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

# Contexto del equipo para la IA
TEAM_CONTEXT = """
Equipo AIT (Arquitectura e Innovación Tecnológica) de Banco Azteca / Grupo Salinas.
Stack tecnológico: React, AWS (ECS Fargate, Lambda, Bedrock, AppSync, DynamoDB, QuickSight, Glue, Redshift), 
Micro-frontends (MFE), Module Federation, GitLab CI/CD, Jenkins, SonarQube, Docker.
Proyectos actuales: Sistema de cobranza, agentes de IA en Bedrock, dashboards en QuickSight, 
steering files con Kiro, gobernanza DevSecOps.
"""

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
    "moon": "🌙",
    "sunrise": "🌅",
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
    "morning_calm": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "https://media.giphy.com/media/3o7TKSjRrfIPjeiVyM/giphy.gif",
        "https://media.giphy.com/media/xT9IgG50Lg7russbDa/giphy.gif",
    ],
    "morning_urgent": [
        "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
        "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif",
        "https://media.giphy.com/media/xT9IgDECMFBzMsuDnW/giphy.gif",
    ],
    "morning_monday": [
        "https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif",
        "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",
        "https://media.giphy.com/media/xT9IgG50Lg7russbDa/giphy.gif",
    ],
    "evening_calm": [
        "https://media.giphy.com/media/l0HlNQ03J5JxX6lva/giphy.gif",
        "https://media.giphy.com/media/3o7TKMt1VVNkHV2PaE/giphy.gif",
        "https://media.giphy.com/media/xT9IgDECMFBzMsuDnW/giphy.gif",
    ],
    "evening_pending": [
        "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
        "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif",
        "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
    ],
}

def get_gif(context: str) -> str:
    return random.choice(GIFS.get(context, GIFS["morning_calm"]))


# ============== CLICKUP API ==============
class ClickUpClient:
    BASE_URL = "https://api.clickup.com/api/v2"
    
    def __init__(self, token: str):
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
    
    def get_task_details(self, task_id: str) -> Optional[Dict]:
        """Obtiene TODOS los detalles de una tarea: descripción, subtareas, checklists"""
        url = f"{self.BASE_URL}/task/{task_id}"
        params = {
            "include_subtasks": "true",
            "include_markdown_description": "true"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching task details for {task_id}: {e}")
            return None
    
    def get_task_checklists(self, task_id: str) -> List[Dict]:
        """Obtiene los checklists de una tarea"""
        # Los checklists vienen en el task detail, pero por si acaso
        task = self.get_task_details(task_id)
        if task:
            return task.get("checklists", [])
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
    
    def build_task_context(self, task: Dict, full_details: Optional[Dict] = None) -> str:
        """Construye el contexto completo de una tarea para la IA"""
        context_parts = []
        
        # Nombre de la tarea
        name = task.get("name", "Sin nombre")
        context_parts.append(f"TAREA: {name}")
        
        # Usar detalles completos si están disponibles
        details = full_details or task
        
        # Descripción
        description = details.get("description") or details.get("text_content") or ""
        if description and description.strip():
            context_parts.append(f"\nDESCRIPCIÓN:\n{description[:1000]}")  # Limitar a 1000 chars
        
        # Subtareas
        subtasks = details.get("subtasks", [])
        if subtasks:
            context_parts.append("\nSUBTAREAS:")
            for st in subtasks[:10]:  # Max 10 subtareas
                st_name = st.get("name", "")
                st_status = st.get("status", {}).get("status", "")
                status_icon = "✓" if st_status.lower() in ["complete", "done", "closed"] else "○"
                context_parts.append(f"  {status_icon} {st_name}")
        
        # Checklists
        checklists = details.get("checklists", [])
        if checklists:
            context_parts.append("\nCHECKLISTS:")
            for checklist in checklists[:3]:  # Max 3 checklists
                cl_name = checklist.get("name", "Checklist")
                context_parts.append(f"  📋 {cl_name}:")
                items = checklist.get("items", [])
                for item in items[:10]:  # Max 10 items por checklist
                    item_name = item.get("name", "")
                    resolved = item.get("resolved", False)
                    status_icon = "✓" if resolved else "○"
                    context_parts.append(f"    {status_icon} {item_name}")
        
        # Tags
        tags = details.get("tags", [])
        if tags:
            tag_names = [t.get("name", "") for t in tags]
            context_parts.append(f"\nTAGS: {', '.join(tag_names)}")
        
        # Folder/List para contexto
        folder = details.get("folder", {})
        if folder:
            context_parts.append(f"\nCARPETA: {folder.get('name', 'N/A')}")
        
        return "\n".join(context_parts)
    
    def suggest_study_topics(self, task: Dict, full_details: Optional[Dict] = None) -> str:
        """Genera sugerencias de qué estudiar basado en TODA la info de la tarea"""
        
        task_context = self.build_task_context(task, full_details)
        
        prompt = f"""Eres un coach técnico del equipo AIT de Banco Azteca.

{TEAM_CONTEXT}

Analiza esta tarea y sugiere qué deberían estudiar o investigar para completarla exitosamente.

{task_context}

INSTRUCCIONES:
- Responde en máximo 2-3 oraciones cortas en español casual
- Sé MUY específico: menciona documentación oficial, tecnologías exactas, o patrones relevantes
- Si la tarea menciona algo del stack (MFE, AWS, React, QuickSight, etc.), enfócate en eso
- Si no entiendes bien la tarea, sugiere que revisen la documentación interna o pregunten al equipo
- NO uses emojis
- Sé directo y útil, como un compañero senior"""

        try:
            response = requests.post(
                self.BASE_URL,
                headers=self.headers,
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.7
                },
                timeout=15
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

    def send_gif(self, chat_id: str, gif_url: str) -> bool:
        """Envía un GIF animado a Telegram"""
        url = f"{self.BASE_URL}{self.token}/sendAnimation"
        try:
            response = requests.post(url, json={"chat_id": chat_id, "animation": gif_url})
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending GIF: {e}")
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
            "overdue": [],
            "today": [],
            "next_48h": [],
            "this_week": [],
            "upcoming": [],
            "no_date": []
        }
        
        for task in tasks:
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
        DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        lists = self.clickup.get_space_lists(SPACE_ID)
        all_tasks = []
        for lst in lists:
            all_tasks.extend(self.clickup.get_tasks_by_list(lst["id"]))

        if not all_tasks:
            return None

        categories = self.categorize_tasks(all_tasks)

        # Resumen por persona
        person_summary = {}
        for uid, info in USER_MAP.items():
            person_tasks = [t for t in all_tasks if any(
                str(a.get("id")) == uid for a in t.get("assignees", [])
            )]
            overdue = [t for t in person_tasks if t in categories["overdue"]]
            today = [t for t in person_tasks if t in categories["today"]]
            next48 = [t for t in person_tasks if t in categories["next_48h"]]
            person_summary[info["name"]] = {
                "telegram": info["telegram"],
                "overdue": len(overdue),
                "today": len(today),
                "next48": len(next48),
                "total": len(person_tasks),
            }

        # Gamificación: estrellitas por persona sin vencidas
        stars_earned = [name for name, s in person_summary.items() if s["overdue"] == 0 and s["total"] > 0]

        # Contexto GIF
        if self.today.weekday() == 0:
            gif_context = "morning_monday"
        elif categories["overdue"] or categories["today"]:
            gif_context = "morning_urgent"
        else:
            gif_context = "morning_calm"

        morning_greetings = [
            "🌟 <b>¡Buenos días, estrellitas!</b> ✨",
            "⭐ <b>¡Despierten, mis pequeñas estrellitas!</b> 🌟",
            "✨ <b>¡Buenos días a las estrellitas más brillantes del universo!</b> 🚀",
            "🌠 <b>¡Ah, mis queridas estrellitas han llegado!</b> ⭐",
        ]

        dia = DIAS_ES[self.today.weekday()]
        mes = MESES_ES[self.today.month - 1]
        fecha = f"{dia} {self.today.day} de {mes}, {self.today.year}"

        lines = [random.choice(morning_greetings)]
        lines.append(f"📅 {fecha}\n")

        # Tareas vencidas
        if categories["overdue"]:
            lines.append(f"{EMOJIS['warning']} <b>VENCIDAS — ¡atención! ({len(categories['overdue'])})</b>")
            for task in categories["overdue"][:5]:
                lines.append(self.format_task(task))
            if len(categories["overdue"]) > 5:
                lines.append(f"   ... y {len(categories['overdue']) - 5} más")
            lines.append("")

        # Vencen hoy
        if categories["today"]:
            lines.append(f"{EMOJIS['fire']} <b>Entregan HOY ({len(categories['today'])})</b>")
            for task in categories["today"]:
                lines.append(self.format_task(task, include_date=False))
            lines.append("")

        # Próximas 48 horas
        if categories["next_48h"]:
            lines.append(f"{EMOJIS['clock']} <b>Vencen en las próximas 48 hrs ({len(categories['next_48h'])})</b>")
            for task in categories["next_48h"]:
                lines.append(self.format_task(task))
            lines.append("")

        # Esta semana (solo lunes)
        if self.today.weekday() == 0 and categories["this_week"]:
            lines.append(f"{EMOJIS['eyes']} <b>En la agenda esta semana ({len(categories['this_week'])})</b>")
            for task in categories["this_week"][:5]:
                lines.append(self.format_task(task))
            if len(categories["this_week"]) > 5:
                lines.append(f"   ... y {len(categories['this_week']) - 5} más")
            lines.append("")

        # Resumen por persona
        lines.append("👥 <b>¿Cómo va cada estrellita?</b>")
        for name, s in person_summary.items():
            if s["total"] == 0:
                continue
            status = []
            if s["overdue"]: status.append(f"⚠️ {s['overdue']} vencida(s)")
            if s["today"]: status.append(f"🔥 {s['today']} para hoy")
            if s["next48"]: status.append(f"⏰ {s['next48']} en 48hrs")
            if not status: status.append("✅ al día")
            lines.append(f"  {s['telegram']}: {' · '.join(status)}")
        lines.append("")

        # Gamificación
        if stars_earned:
            lines.append(f"🏆 <b>Sin vencidas hoy:</b> {', '.join(stars_earned)} — ¡siguen brillando! ⭐")
        if not categories["overdue"] and not categories["today"]:
            msg = random.choice(MOTIVATIONAL_MESSAGES)
            for key, emoji in EMOJIS.items():
                msg = msg.replace("{" + key + "}", emoji)
            lines.append(f"\n{EMOJIS['check']} <b>¡Sin urgencias hoy!</b> {msg}")

        return "\n".join(lines), get_gif(gif_context)
    
    def generate_evening_report(self) -> str:
        """Genera el check-in de la tarde (6:00 PM)"""
        DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        lists = self.clickup.get_space_lists(SPACE_ID)
        all_tasks = []
        for lst in lists:
            all_tasks.extend(self.clickup.get_tasks_by_list(lst["id"]))

        categories = self.categorize_tasks(all_tasks)

        gif_context = "evening_pending" if (categories["overdue"] or categories["today"]) else "evening_calm"

        evening_greetings = [
            "🌙 <b>¡Ya casí terminamos, estrellitas!</b> ✨",
            "⭐ <b>¡Casi es hora de cerrar, mis brillantes estrellitas!</b> 🌟",
            "🌠 <b>¡El día casi llega a su fin, queridas estrellitas!</b> 💫",
        ]

        dia = DIAS_ES[self.today.weekday()]
        mes = MESES_ES[self.today.month - 1]

        lines = [random.choice(evening_greetings)]
        lines.append(f"🌅 {dia} {self.today.day} de {mes}\n")

        # Recordatorio de pendientes del día
        if categories["overdue"]:
            lines.append(f"{EMOJIS['warning']} <b>Aún hay {len(categories['overdue'])} tarea(s) vencida(s) sin cerrar:</b>")
            for task in categories["overdue"][:3]:
                lines.append(self.format_task(task))
            lines.append("")

        # Sugerencia de estudio con IA
        next_tasks = categories["next_48h"] + categories["this_week"][:2]
        if next_tasks and self.ai:
            target_task = next(
                (t for t in next_tasks if self.parse_due_date(t.get("due_date")) and
                 self.parse_due_date(t.get("due_date")).date() > self.today),
                next_tasks[0] if next_tasks else None
            )
            if target_task:
                task_id = target_task.get("id")
                full_details = self.clickup.get_task_details(task_id) if task_id else None
                suggestion = self.ai.suggest_study_topics(target_task, full_details)
                if suggestion:
                    telegrams = self.get_assignee_telegram(target_task)
                    telegram_str = " ".join(telegrams) if telegrams else ""
                    lines.append(f"{EMOJIS['brain']} <b>Para mañana, estrellitas:</b>")
                    lines.append(f"📌 <i>{target_task.get('name', '')}</i> — {telegram_str}")
                    lines.append(f"💡 {suggestion}")
                    lines.append("")

        # Check de progreso
        if categories["next_48h"]:
            task = categories["next_48h"][0]
            telegrams = self.get_assignee_telegram(task)
            if telegrams:
                lines.append(f"{EMOJIS['eyes']} {' '.join(telegrams)} ¿Cómo van con <i>{task.get('name', '')}</i>?")
                lines.append("")

        # Gamificación: quién cerró todo hoy
        if not categories["overdue"] and not categories["today"]:
            lines.append(f"{EMOJIS['trophy']} <b>¡Día limpio, estrellitas!</b> Sin pendientes del día. ¡Eso se celebra! 🎉")
        
        closings = [
            "¡Descansen y recarguen su brillo, estrellitas! 🌙✨",
            "Mañana volvemos a brillar juntas 💪⭐",
            "¡Buen descanso, mis pequeñas estrellitas! 🌠",
            "¡Hasta mañana, equipo de estrellas! 🚀🌟",
        ]
        lines.append(f"\n{random.choice(closings)}")

        return "\n".join(lines), get_gif(gif_context)
    
    def send_morning_report(self):
        """Envía el reporte de la mañana"""
        result = self.generate_morning_report()
        if result:
            text, gif_url = result
            self.telegram.send_gif(TELEGRAM_CHAT_ID, gif_url)
            self.telegram.send_message(TELEGRAM_CHAT_ID, text)
            print("✅ Morning report sent!")
        else:
            print("⚠️ No tasks found or error generating report")

    def send_evening_report(self):
        """Envía el check-in de la tarde"""
        result = self.generate_evening_report()
        if result:
            text, gif_url = result
            self.telegram.send_gif(TELEGRAM_CHAT_ID, gif_url)
            self.telegram.send_message(TELEGRAM_CHAT_ID, text)
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
        import re
        print("=" * 50)
        print("=== MORNING REPORT ===")
        print("=" * 50)
        morning = reporter.generate_morning_report()
        if morning:
            text, gif = morning
            print(f"GIF: {gif}")
            print(re.sub(r'<[^>]+>', '', text))
        else:
            print("No se pudo generar el reporte")

        print("\n" + "=" * 50)
        print("=== EVENING REPORT ===")
        print("=" * 50)
        evening = reporter.generate_evening_report()
        if evening:
            text, gif = evening
            print(f"GIF: {gif}")
            print(re.sub(r'<[^>]+>', '', text))
        else:
            print("No se pudo generar el reporte")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
