import telebot
from telebot import TeleBot, types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import DATABASE, TOKEN
from logic import DB_Manager

# Инициализация бота и менеджера базы данных
bot = TeleBot(TOKEN)
manager = DB_Manager(DATABASE)

# Кнопка скрытия клавиатуры и стандартная кнопка отмены
hideBoard = types.ReplyKeyboardRemove()
cancel_button = "Отмена 🚫"


def cancel(message):
    """Отменяет текущее действие и скрывает клавиатуру."""
    bot.send_message(
        message.chat.id,
        "🚫 Действие отменено.\nЧтобы посмотреть список команд, используй /info",
        reply_markup=hideBoard
    )


def no_projects(message):
    """Отправляет сообщение, если у пользователя еще нет проектов."""
    bot.send_message(
        message.chat.id,
        '📂 У тебя пока нет сохранённых проектов!\n'
        'Ты можешь добавить новый проект с помощью команды /new_project ✨'
    )


def gen_inline_markup(rows):
    """Генерирует Инлайн-клавиатуру с кнопками."""
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    for row in rows:
        markup.add(InlineKeyboardButton(row, callback_data=row))
    return markup


def gen_markup(rows):
    """
    Генерирует Reply-клавиатуру.
    Задание 1: one_time_keyboard=True обеспечивает сокрытие клавиатуры после нажатия.
    """
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.row_width = 1
    for row in rows:
        markup.add(KeyboardButton(row))
    markup.add(KeyboardButton(cancel_button))
    return markup


# Словарь соответствия атрибутов проекта для команды редактирования
attributes_of_projects = {
    '✏️ Имя проекта': ["Введите новое имя проекта:", "project_name"],
    '📝 Описание': ["Введите новое описание проекта:", "description"],
    '🔗 Ссылка': ["Введите новую ссылку на проект:", "url"],
    '📊 Статус': ["Выберите новый статус задачи:", "status_id"]
}


def info_project(message, user_id, project_name):
    """Выводит детальную информацию о конкретном проекте."""
    info = manager.get_project_info(user_id, project_name)[0]
    skills = manager.get_project_skills(project_name)
    
    if not skills:
        skills = 'Навыки пока не добавлены 🔍'

    # Красивый вывод с визуальными разделителями и смайликами
    text = (
        f"📌 *Проект:* {info[0]}\n"
        f"📝 *Описание:* {info[1] if info[1] else 'Отсутствует'}\n"
        f"🔗 *Ссылка:* {info[2]}\n"
        f"📊 *Статус:* {info[3]}\n"
        f"🛠 *Навыки:* {skills}\n"
        f"──────────────────"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ==========================================
#              ХЭНДЛЕРЫ КОМАНД
# ==========================================

@bot.message_handler(commands=['start'])
def start_command(message):
    """Хэндлер команды /start: Приветствует пользователя и выводит справку."""
    greeting = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я твой личный *Бот-портфолио* 💼\n"
        "Помогу систематизировать твои проекты, отслеживать их статус и привязанные навыки."
    )
    bot.send_message(message.chat.id, greeting, parse_mode='Markdown')
    info(message)


@bot.message_handler(commands=['info'])
def info(message):
    """
    Хэндлер команды /info: Отображает полный список доступных команд.
    Задание 2: Расписана каждая команда бота.
    """
    help_text = (
        "📖 *Доступные команды бота:*\n\n"
        "➕ /new\_project — Добавить новый проект в портфолио\n"
        "📁 /projects — Посмотреть список всех твоих проектов\n"
        "⚙️ /update\_projects — Изменить данные существующего проекта\n"
        "🛠 /skills — Привязать ключевой навык/технологию к проекту\n"
        "🗑 /delete — Удалить проект из базы данных\n"
        "ℹ️ /info — Показать это справочное сообщение\n\n"
        "💡 *Совет:* Просто напиши название проекта в чат, чтобы быстро узнать подробности о нём!"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


@bot.message_handler(commands=['new_project'])
def addtask_command(message):
    """Хэндлер команды /new_project: Начинает пошаговый процесс создания нового проекта."""
    bot.send_message(message.chat.id, "🚀 *Шаг 1/3:* Введите название нового проекта:", parse_mode='Markdown')
    bot.register_next_step_handler(message, name_project)


def name_project(message):
    """Шаг 2: Получает имя проекта и запрашивает ссылку."""
    name = message.text
    user_id = message.from_user.id
    data = [user_id, name]
    
    bot.send_message(message.chat.id, "🔗 *Шаг 2/3:* Введите ссылку на проект (GitHub, Figma, сайт и т.д.):", parse_mode='Markdown')
    bot.register_next_step_handler(message, link_project, data=data)


def link_project(message, data):
    """Шаг 3: Получает ссылку и запрашивает выбор статуса."""
    data.append(message.text)
    statuses = [x[0] for x in manager.get_statuses()] 
    
    bot.send_message(
        message.chat.id, 
        "📊 *Шаг 3/3:* Выберите текущий статус проекта из списка ниже:", 
        reply_markup=gen_markup(statuses),
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)


def callback_project(message, data, statuses):
    """Завершение создания: Валидирует статус и сохраняет проект в БД."""
    status = message.text
    if status == cancel_button:
        cancel(message)
        return
        
    if status not in statuses:
        bot.send_message(
            message.chat.id, 
            "⚠️ Вы выбрали статус не из списка, попробуйте ещё раз! 👇", 
            reply_markup=gen_markup(statuses)
        )
        bot.register_next_step_handler(message, callback_project, data=data, statuses=statuses)
        return
        
    status_id = manager.get_status_id(status)
    data.append(status_id)
    manager.insert_project([tuple(data)])
    
    bot.send_message(
        message.chat.id, 
        "🎉 *Ура! Проект успешно сохранён в портфолио!*", 
        reply_markup=hideBoard,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['skills'])
def skill_handler(message):
    """Хэндлер команды /skills: Позволяет привязать навык к проекту."""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        projects_names = [x[2] for x in projects]
        bot.send_message(
            message.chat.id, 
            '🛠 Выбери проект, к которому хочешь добавить навык:', 
            reply_markup=gen_markup(projects_names)
        )
        bot.register_next_step_handler(message, skill_project, projects=projects_names)
    else:
        no_projects(message)


def skill_project(message, projects):
    """Получает выбранный проект и предлагает список доступных навыков."""
    project_name = message.text
    if project_name == cancel_button:
        cancel(message)
        return
        
    if project_name not in projects:
        bot.send_message(
            message.chat.id, 
            '⚠️ У тебя нет такого проекта. Выбери из списка ниже:', 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, skill_project, projects=projects)
    else:
        skills = [x[1] for x in manager.get_skills()]
        bot.send_message(
            message.chat.id, 
            '💡 Выбери навык/технологию для привязки:', 
            reply_markup=gen_markup(skills)
        )
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)


def set_skill(message, project_name, skills):
    """Сохраняет связь между выбранным навыком и проектом."""
    skill = message.text
    user_id = message.from_user.id
    
    if skill == cancel_button:
        cancel(message)
        return
        
    if skill not in skills:
        bot.send_message(
            message.chat.id, 
            '⚠️ Кажется, выбранного навыка нет в списке. Попробуй ещё раз:', 
            reply_markup=gen_markup(skills)
        )
        bot.register_next_step_handler(message, set_skill, project_name=project_name, skills=skills)
        return
        
    manager.insert_skill(user_id, project_name, skill)
    bot.send_message(
        message.chat.id, 
        f'✅ Навык *"{skill}"* успешно добавлен к проекту *"{project_name}"*!',
        reply_markup=hideBoard,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['projects'])
def get_projects(message):
    """Хэндлер команды /projects: Отображает список всех проектов пользователя с инлайн-кнопками."""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "📁 *Твои текущие проекты:*\n\n"
        text += "\n".join([f"🔹 *{x[2]}*\n🔗 {x[4]}\n" for x in projects])
        text += "\n_Нажми на кнопку ниже, чтобы узнать детали!_"
        
        bot.send_message(
            message.chat.id, 
            text, 
            reply_markup=gen_inline_markup([x[2] for x in projects]),
            parse_mode='Markdown'
        )
    else:
        no_projects(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    """Обработчик нажатий на инлайн-кнопки под списком проектов."""
    project_name = call.data
    info_project(call.message, call.from_user.id, project_name)


@bot.message_handler(commands=['delete'])
def delete_handler(message):
    """Хэндлер команды /delete: Запускает процедуру удаления проекта."""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        text = "🗑 *Выбери проект, который хочешь удалить:*\n\n"
        text += "\n".join([f"🔹 *{x[2]}*" for x in projects])
        projects_names = [x[2] for x in projects]
        
        bot.send_message(
            message.chat.id, 
            text, 
            reply_markup=gen_markup(projects_names),
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, delete_project, projects=projects_names)
    else:
        no_projects(message)


def delete_project(message, projects):
    """Удаляет проект из базы данных после подтверждения."""
    project = message.text
    user_id = message.from_user.id

    if project == cancel_button:
        cancel(message)
        return
        
    if project not in projects:
        bot.send_message(
            message.chat.id, 
            '⚠️ У тебя нет такого проекта. Попробуй выбрать снова:', 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, delete_project, projects=projects)
        return
        
    project_id = manager.get_project_id(project, user_id)
    manager.delete_project(user_id, project_id)
    bot.send_message(
        message.chat.id, 
        f'🗑 Проект *"{project}"* успешно удалён!', 
        reply_markup=hideBoard,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['update_projects'])
def update_project(message):
    """Хэндлер команды /update_projects: Начинает процесс редактирования проекта."""
    user_id = message.from_user.id
    projects = manager.get_projects(user_id)
    if projects:
        projects_names = [x[2] for x in projects]
        bot.send_message(
            message.chat.id, 
            "⚙️ Выбери проект, данные которого хочешь изменить:", 
            reply_markup=gen_markup(projects_names)
        )
        bot.register_next_step_handler(message, update_project_step_2, projects=projects_names)
    else:
        no_projects(message)


def update_project_step_2(message, projects):
    """Выбор редактируемого поля проекта."""
    project_name = message.text
    if project_name == cancel_button:
        cancel(message)
        return
        
    if project_name not in projects:
        bot.send_message(
            message.chat.id, 
            "⚠️ Выбран несуществующий проект. Выбери из списка:", 
            reply_markup=gen_markup(projects)
        )
        bot.register_next_step_handler(message, update_project_step_2, projects=projects)
        return
        
    bot.send_message(
        message.chat.id, 
        "📝 Что именно ты хочешь изменить в проекте?", 
        reply_markup=gen_markup(list(attributes_of_projects.keys()))
    )
    bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)


def update_project_step_3(message, project_name):
    """Запрос нового значения для выбранного атрибута."""
    attribute = message.text
    reply_markup = None 
    
    if attribute == cancel_button:
        cancel(message)
        return
        
    if attribute not in attributes_of_projects.keys():
        bot.send_message(
            message.chat.id, 
            "⚠️ Пожалуйста, выбери вариант из предложенной клавиатуры:", 
            reply_markup=gen_markup(list(attributes_of_projects.keys()))
        )
        bot.register_next_step_handler(message, update_project_step_3, project_name=project_name)
        return
        
    elif attribute == "📊 Статус":
        rows = manager.get_statuses()
        reply_markup = gen_markup([x[0] for x in rows])
        
    bot.send_message(
        message.chat.id, 
        attributes_of_projects[attribute][0], 
        reply_markup=reply_markup
    )
    bot.register_next_step_handler(
        message, 
        update_project_step_4, 
        project_name=project_name, 
        attribute=attributes_of_projects[attribute][1]
    )


def update_project_step_4(message, project_name, attribute): 
    """Сохранение обновлённых данных проекта в базе."""
    update_info = message.text
    
    if update_info == cancel_button:
        cancel(message)
        return
        
    if attribute == "status_id":
        rows = manager.get_statuses()
        status_names = [x[0] for x in rows]
        if update_info in status_names:
            update_info = manager.get_status_id(update_info)
        else:
            bot.send_message(
                message.chat.id, 
                "⚠️ Выбран неверный статус, попробуй ещё раз:", 
                reply_markup=gen_markup(status_names)
            )
            bot.register_next_step_handler(
                message, 
                update_project_step_4, 
                project_name=project_name, 
                attribute=attribute
            )
            return

    user_id = message.from_user.id
    data = (update_info, project_name, user_id)
    manager.update_projects(attribute, data)
    
    bot.send_message(
        message.chat.id, 
        "✅ *Готово! Данные проекта обновлены!*", 
        reply_markup=hideBoard,
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda message: True)
def text_handler(message):
    """
    Универсальный хэндлер текстовых сообщений.
    Если пользователь введёт имя существующего проекта — выведет карточку проекта.
    В противном случае предложит справку.
    """
    user_id = message.from_user.id
    user_projects = manager.get_projects(user_id)
    
    if user_projects:
        projects = [x[2] for x in user_projects]
        project = message.text
        if project in projects:
            info_project(message, user_id, project)
            return
            
    bot.reply_to(message, "🤔 Не совсем понял тебя. Тебе нужна помощь?")
    info(message)


# Точка входа в программу
if __name__ == '__main__':
    bot.infinity_polling()