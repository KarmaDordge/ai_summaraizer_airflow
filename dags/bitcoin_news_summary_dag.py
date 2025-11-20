"""
DAG для получения новостей о Bitcoin, создания саммари через GigaChat
и отправки результата на email каждый час.
"""

from datetime import datetime, timedelta
import json
import os
import uuid
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.email import send_email
from airflow.models import Variable
import requests

# Импорт news_tool из той же папки dags
from news_tool import get_news_titles, register_news_tool, execute_news_tool

# Настройки по умолчанию для DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def get_config_value(key: str, default: str = '') -> str:
    """
    Получает значение конфигурации из Airflow Variables или переменных окружения.
    
    Args:
        key: Ключ конфигурации
        default: Значение по умолчанию
        
    Returns:
        str: Значение конфигурации
    """
    try:
        return Variable.get(key, default_var=default)
    except Exception:
        return os.getenv(key, default)


# Email получателя (настраивается через Airflow Variable: NEWS_SUMMARY_EMAIL)
RECIPIENT_EMAIL = get_config_value('NEWS_SUMMARY_EMAIL', 'your_email@example.com')

# Настройки GigaChat (настраиваются через Airflow Variables)
GIGACHAT_CREDENTIALS = get_config_value('GIGACHAT_CREDENTIALS', '')
GIGACHAT_MODEL = get_config_value('GIGACHAT_MODEL', 'GigaChat-Pro')


def get_news_task(**context) -> Dict[str, Any]:
    """
    Получает новости через news_tool.
    
    Returns:
        dict: Словарь с новостями
    """
    try:
        news_data = get_news_titles()
        
        if 'error' in news_data:
            raise Exception(f"Ошибка при получении новостей: {news_data['error']}")
        
        context['ti'].xcom_push(key='news_data', value=news_data)
        return news_data
        
    except Exception as e:
        raise Exception(f"Ошибка в задаче получения новостей: {str(e)}")


def summarize_news_with_gigachat(**context) -> str:
    """
    Создает саммари новостей через GigaChat API.
    
    Returns:
        str: Текст саммари
    """
    # Переменные для управления временным файлом credentials
    credentials_path = None
    temp_file_created = False
    
    try:
        # Получаем данные новостей из предыдущей задачи
        news_data = context['ti'].xcom_pull(key='news_data', task_ids='get_news')
        
        if not news_data or 'titles' not in news_data:
            raise Exception("Не удалось получить данные новостей")
        
        titles = news_data.get('titles', [])
        total_count = news_data.get('total_count', 0)
        
        if not titles:
            return "Новостей не найдено."
        
        # Формируем промпт для GigaChat
        news_text = "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
        
        prompt = f"""Проанализируй следующие новости о Bitcoin и создай краткое саммари на русском языке.

Новости:
{news_text}

Создай структурированное саммари, которое включает:
1. Общую оценку ситуации на рынке Bitcoin
2. Ключевые события и тренды
3. Важные детали из новостей

Саммари должно быть информативным, но кратким (не более 500 слов)."""

        # Импортируем GigaChat только при необходимости
        try:
            from gigachat import GigaChat
            from gigachat.models import Chat, Messages, MessagesRole
        except ImportError:
            raise ImportError(
                "Библиотека gigachat не установлена. "
                "Установите её: pip install gigachat"
            )
        
        # Инициализация GigaChat клиента
        if not GIGACHAT_CREDENTIALS:
            raise Exception(
                "Не указаны учетные данные GigaChat. "
                "Установите Airflow Variable GIGACHAT_CREDENTIALS "
                "(Admin -> Variables) - путь к файлу с credentials или JSON строка"
            )
        
        # Получаем Authorization Key из Airflow Variables GIGACHAT_CREDENTIALS
        # Очищаем от всех пробелов, переносов строк и невидимых символов
        credentials_value = GIGACHAT_CREDENTIALS.strip()
        credentials_value = credentials_value.replace('\r', '').replace('\n', '').replace('\t', '')
        credentials_value = ''.join(credentials_value.split())
        
        if not credentials_value:
            raise Exception("Authorization Key пустой. Установите Airflow Variable GIGACHAT_CREDENTIALS с Authorization Key (base64 строка)")
        
        # Создаем клиент GigaChat напрямую, передавая credentials из переменной
        # Библиотека сама получит токен из Authorization Key
        client = GigaChat(credentials=credentials_value, verify_ssl_certs=False)
        
        # Регистрируем news tool
        tools = register_news_tool()
        
        # Создаем сообщения для чата
        messages = [
            Messages(role=MessagesRole.USER, content=prompt)
        ]
        
        # Создаем объект Chat
        chat = Chat(
            messages=messages,
            model=GIGACHAT_MODEL,
            tools=tools,
            temperature=0.7,
        )
        
        # Отправляем запрос в GigaChat
        response = client.chat(chat)
        
        # Извлекаем ответ
        summary = ""
        if hasattr(response, 'choices') and response.choices:
            message = response.choices[0].message
            
            # Проверяем, есть ли tool_calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Если есть tool_calls, выполняем их
                for tool_call in message.tool_calls:
                    if hasattr(tool_call, 'function'):
                        function = tool_call.function
                        tool_call_dict = {
                            "name": function.name if hasattr(function, 'name') else getattr(function, 'name', ''),
                            "arguments": function.arguments if hasattr(function, 'arguments') else getattr(function, 'arguments', '{}')
                        }
                        tool_result = execute_news_tool(tool_call_dict)
                        
                        # Добавляем результат обратно в сообщения
                        messages.append(Messages(role=MessagesRole.ASSISTANT, content=str(getattr(message, 'content', ''))))
                        messages.append(Messages(
                            role=MessagesRole.TOOL,
                            content=json.dumps(tool_result),
                            name=tool_call_dict["name"]
                        ))
                
                # Повторяем запрос с результатами tool
                chat = Chat(
                    messages=messages,
                    model=GIGACHAT_MODEL,
                    tools=tools,
                    temperature=0.7,
                )
                response = client.chat(chat)
                if hasattr(response, 'choices') and response.choices:
                    message = response.choices[0].message
            
            summary = getattr(message, 'content', str(message)) if hasattr(message, 'content') else str(message)
        else:
            summary = str(response)
        
        # Проверяем, что саммари успешно создано
        if not summary or not summary.strip():
            raise Exception("Саммари не было создано - получен пустой ответ от GigaChat")
        
        # Проверяем, что саммари не содержит ошибок
        error_indicators = [
            "ошибка",
            "error",
            "не удалось",
            "failed",
            "Can't decode",
            "Authorization",
            "400",
            "401",
            "403",
            "500"
        ]
        summary_lower = summary.lower()
        if any(indicator in summary_lower for indicator in error_indicators):
            # Проверяем, что это действительно ошибка, а не часть саммари
            if "ошибка при" in summary_lower or "error" in summary_lower or "400" in summary or "401" in summary:
                raise Exception(f"Ошибка при создании саммари: {summary[:200]}")
        
        # Сохраняем саммари в XCom
        context['ti'].xcom_push(key='summary', value=summary)
        
        return summary
        
    except ImportError as e:
        error_msg = f"Ошибка импорта: {str(e)}"
        # Не сохраняем ошибку в XCom - задача должна упасть
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Ошибка при создании саммари: {str(e)}"
        # Не сохраняем ошибку в XCom - задача должна упасть
        # Это гарантирует, что email не будет отправлен при ошибке
        raise Exception(error_msg)


def prepare_email_content(**context) -> Dict[str, str]:
    """
    Подготавливает содержимое email (текстовую и HTML версии).
    
    Returns:
        dict: Словарь с subject, text_content и html_content
    """
    try:
        # Получаем саммари из предыдущей задачи
        summary = context['ti'].xcom_pull(key='summary', task_ids='summarize_news')
        news_data = context['ti'].xcom_pull(key='news_data', task_ids='get_news')
        
        # Проверяем, что саммари успешно создано
        if not summary or not summary.strip():
            raise Exception("Саммари не было создано - получен пустой ответ")
        
        # Проверяем, что саммари не содержит ошибок
        error_indicators = ["ошибка при", "error", "не удалось создать", "failed", "Can't decode", "Authorization", "400", "401"]
        summary_lower = summary.lower()
        if any(indicator in summary_lower for indicator in error_indicators):
            raise Exception(f"Саммари содержит ошибку: {summary[:200]}")
        
        # Формируем данные
        titles = news_data.get('titles', []) if news_data else []
        total_count = news_data.get('total_count', 0) if news_data else 0
        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Текстовая версия (для избежания спам-фильтров)
        text_content = f"""Саммари новостей о Bitcoin

Дата: {date_str}
Всего новостей: {total_count}

САММАРИ:
{summary}

СПИСОК НОВОСТЕЙ:
"""
        for i, title in enumerate(titles[:20], 1):
            text_content += f"{i}. {title}\n"
        
        if total_count > 20:
            text_content += f"\n... и еще {total_count - 20} новостей\n"
        
        # HTML версия (упрощенная, без сложных стилей)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Саммари новостей о Bitcoin</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #333; border-bottom: 2px solid #333; padding-bottom: 10px;">Саммари новостей о Bitcoin</h1>
    <p><strong>Дата:</strong> {date_str}</p>
    <p><strong>Всего новостей:</strong> {total_count}</p>
    
    <div style="background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-left: 4px solid #333;">
        <h2 style="margin-top: 0;">Саммари:</h2>
        <p style="white-space: pre-wrap;">{summary.replace('<', '&lt;').replace('>', '&gt;')}</p>
    </div>
    
    <div style="margin: 20px 0;">
        <h2>Список новостей:</h2>
"""
        
        for i, title in enumerate(titles[:20], 1):
            # Экранируем HTML символы в заголовках
            safe_title = title.replace('<', '&lt;').replace('>', '&gt;')
            html_content += f'        <p style="padding: 5px 0; border-bottom: 1px solid #eee;">{i}. {safe_title}</p>\n'
        
        if total_count > 20:
            html_content += f'        <p style="font-style: italic; color: #666;">... и еще {total_count - 20} новостей</p>\n'
        
        html_content += """    </div>
</body>
</html>"""
        
        subject = f"Саммари новостей о Bitcoin - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        context['ti'].xcom_push(key='email_subject', value=subject)
        context['ti'].xcom_push(key='email_text', value=text_content)
        context['ti'].xcom_push(key='email_html', value=html_content)
        
        return {
            'subject': subject,
            'text_content': text_content,
            'html_content': html_content
        }
        
    except Exception as e:
        error_msg = f"Ошибка при подготовке email: {str(e)}"
        context['ti'].xcom_push(key='email_subject', value='Ошибка при подготовке саммари новостей')
        context['ti'].xcom_push(key='email_text', value=error_msg)
        context['ti'].xcom_push(key='email_html', value=f'<html><body><p>{error_msg}</p></body></html>')
        return {
            'subject': 'Ошибка при подготовке саммари новостей',
            'text_content': error_msg,
            'html_content': f'<html><body><p>{error_msg}</p></body></html>'
        }


def send_summary_email(**context):
    """
    Отправляет email с саммари новостей через SMTP.
    Использует стандартный способ отправки email с текстовой и HTML версиями.
    """
    try:
        subject = context['ti'].xcom_pull(key='email_subject', task_ids='prepare_email')
        text_content = context['ti'].xcom_pull(key='email_text', task_ids='prepare_email')
        html_content = context['ti'].xcom_pull(key='email_html', task_ids='prepare_email')
        
        if not subject or not html_content:
            raise Exception("Не удалось получить данные для email")
        
        # Используем стандартный способ отправки email
        # Добавляем текстовую версию для избежания спам-фильтров
        send_email(
            to=[RECIPIENT_EMAIL],
            subject=subject,
            html_content=html_content,
            files=None,  # Без вложений
        )
        
        return f"Email успешно отправлен на {RECIPIENT_EMAIL}"
        
    except Exception as e:
        error_msg = str(e)
        # Логируем ошибку для отладки
        print(f"Ошибка отправки email: {error_msg}")
        
        # Если это ошибка спама от Mail.ru, даем более понятное сообщение
        if "spam message rejected" in error_msg.lower() or "550" in error_msg:
            raise Exception(
                f"Письмо отклонено как спам Mail.ru. "
                f"Попробуйте: 1) Проверить содержимое письма, 2) Добавить отправителя в белый список, "
                f"3) Использовать другой email сервис. "
                f"Детали: {error_msg}"
            )
        else:
            raise Exception(f"Ошибка при отправке email: {error_msg}")


# Создание DAG
dag = DAG(
    'bitcoin_news_summary',
    default_args=default_args,
    description='Получение новостей о Bitcoin, создание саммари через GigaChat и отправка на email',
    schedule_interval=timedelta(hours=1),  # Каждый час
    start_date=datetime(2025, 11, 19),
    catchup=False,
    tags=['bitcoin', 'news', 'gigachat', 'email'],
)

# Определение задач
get_news_task = PythonOperator(
    task_id='get_news',
    python_callable=get_news_task,
    dag=dag,
)

summarize_news_task = PythonOperator(
    task_id='summarize_news',
    python_callable=summarize_news_with_gigachat,
    dag=dag,
)

prepare_email_task = PythonOperator(
    task_id='prepare_email',
    python_callable=prepare_email_content,
    dag=dag,
)

send_email_task = PythonOperator(
    task_id='send_email',
    python_callable=send_summary_email,
    dag=dag,
)

# Определение последовательности выполнения задач
get_news_task >> summarize_news_task >> prepare_email_task >> send_email_task

