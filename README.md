# 🤖 ASORT PM Bot

Bot de Project Management para el equipo AIT de Grupo Salinas.

## ✨ Funcionalidades

### 📅 Reporte Mañanero (9:30 AM Lun-Vie)
- 🔴 **VENCIDAS**: Tareas pasadas de fecha con tag directo a la persona
- 🔥 **HOY**: Tareas que vencen hoy
- ⏰ **Próximas 48hrs**: Aviso preventivo
- 📊 **Resumen semanal** (solo lunes)

### 🌅 Check-in de Cierre (6:00 PM Lun-Vie)
- 🧠 **Sugerencias de estudio** con IA (Groq/Llama)
- ❓ Preguntas sobre progreso en tareas próximas
- 💬 Mensajes motivacionales cuando no hay entregas

### 🎮 Gamificación (próximamente)
- 🔥 Streaks de cumplimiento
- 🏆 Rankings semanales
- 🎉 Celebraciones automáticas

---

## 🚀 Configuración

### 1. Crear Bot de Telegram

1. Abre Telegram y busca `@BotFather`
2. Envía `/newbot`
3. Sigue las instrucciones y guarda el **TOKEN**
4. Agrega el bot a tu grupo "Procesos y transformación digital 🧑‍💻"
5. Para obtener el **CHAT_ID** del grupo:
   - Agrega `@userinfobot` al grupo temporalmente
   - Te dará el ID del grupo (número negativo)
   - Remueve el bot después

### 2. Obtener API Token de ClickUp

1. Ve a ClickUp → Settings → API de ClickUp
2. Genera un nuevo token personal
3. Guárdalo de forma segura

### 3. Obtener API Key de Groq (Gratis)

1. Ve a https://console.groq.com/
2. Crea una cuenta
3. Ve a API Keys → Create API Key
4. Guárdala

### 4. Configurar GitHub Repository

1. Crea un repo nuevo (puede ser privado)
2. Sube los archivos:
   ```
   asort-pm-bot/
   ├── bot.py
   ├── .github/
   │   └── workflows/
   │       └── pm-bot.yml
   └── README.md
   ```

3. Ve a **Settings → Secrets and variables → Actions**

4. Agrega estos secrets:
   | Secret Name | Valor |
   |-------------|-------|
   | `CLICKUP_API_TOKEN` | Tu token de ClickUp |
   | `TELEGRAM_BOT_TOKEN` | Token de BotFather |
   | `TELEGRAM_CHAT_ID` | ID del grupo (ej: -1001234567890) |
   | `GROQ_API_KEY` | Tu API key de Groq |

### 5. Probar Manualmente

1. Ve a **Actions** en tu repo
2. Selecciona "ASORT PM Bot"
3. Click en "Run workflow"
4. Selecciona `morning` o `evening`
5. ¡Verifica que llegue el mensaje a Telegram!

---

## 👥 Equipo Configurado

| ClickUp ID | Nombre | Telegram |
|------------|--------|----------|
| 176560828 | Isis | @isisjaimev |
| 75556718 | Salma | @salmareli |
| 138138459 | Sergio | @DanielUnda |
| 138142839 | Maguie | @MaguieCalderon |

---

## ⚙️ Personalización

### Cambiar horarios
Edita `.github/workflows/pm-bot.yml`:
```yaml
schedule:
  # Formato: minuto hora * * días
  # Recuerda: GitHub usa UTC
  - cron: '30 15 * * 1-5'  # 9:30 AM CDMX
```

### Agregar usuarios
Edita `bot.py` → `USER_MAP`:
```python
USER_MAP = {
    "USER_ID": {"name": "Nombre", "telegram": "@username"},
}
```

### Cambiar Space de ClickUp
Edita `bot.py`:
```python
SPACE_ID = "tu_space_id"
WORKSPACE_ID = "tu_workspace_id"
```

---

## 🐛 Troubleshooting

### El bot no envía mensajes
1. Verifica que el bot esté en el grupo
2. Confirma que el CHAT_ID sea correcto (debe ser negativo para grupos)
3. Revisa los logs en GitHub Actions

### No llegan las sugerencias de IA
1. Verifica que `GROQ_API_KEY` esté configurado
2. El bot funciona sin IA, solo omite las sugerencias

### Las tareas no aparecen
1. Verifica el `SPACE_ID` en el código
2. Confirma que el token de ClickUp tenga permisos

---

## 📄 Licencia

Uso interno - AIT Team, Grupo Salinas

---

Made with 🧡 by the AIT Team
