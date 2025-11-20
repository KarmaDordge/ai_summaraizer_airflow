"""
Модуль для работы с новостями через tool для GigaChat API.

Реализует функцию get_news_titles и регистрацию tool "news" для использования
в GigaChat агенте. Использует стандартную библиотеку requests.
Обращается к локальному MCP серверу news_server.py.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


# URL локального сервера новостей
NEWS_SERVER_URL = "http://localhost:8081"


def get_news_titles() -> Dict[str, Any]:
    """
    Получает заголовки новостей о Bitcoin.
    
    Делает GET запрос к локальному MCP серверу новостей (news_server.py)
    и возвращает заголовки новостей. Сервер должен быть запущен на порту 8081.
    
    Returns:
        dict: JSON с массивом заголовков новостей или словарь с ошибкой,
              если запрос не удался
              
    Example:
        >>> result = get_news_titles()
        >>> print(result)
        {'titles': ['Bitcoin Price Plummets...', 'New Hampshire Launches...', ...], 'total_count': 10}
    """
    try:
        # Выполняем GET запрос к локальному серверу
        response = requests.get(NEWS_SERVER_URL, timeout=10)
        response.raise_for_status()
        
        # Возвращаем JSON ответ от сервера
        return response.json()
        
    except requests.exceptions.RequestException as e:
        # В случае ошибки возвращаем словарь с описанием ошибки
        return {
            "error": f"Ошибка при запросе новостей: {str(e)}",
        }


# Определение tool для GigaChat API (формат OpenAI-style function calling)
NEWS_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "news",
        "description": (
            "Получает актуальные заголовки новостей о Bitcoin. "
            "Возвращает список заголовков из последних новостей."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def get_news_tool() -> Dict[str, Any]:
    """
    Возвращает определение tool "news" для регистрации в GigaChat агенте.
    
    Returns:
        dict: Определение tool в формате GigaChat/OpenAI function calling
        
    Example:
        >>> tool = get_news_tool()
        >>> # Использование в GigaChat:
        >>> # chat = Chat(messages=messages, tools=[tool])
    """
    return NEWS_TOOL_DEFINITION


def execute_news_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполняет вызов tool "news" на основе данных из tool_call.
    
    Args:
        tool_call: Словарь с данными вызова tool от GigaChat API.
                  Ожидается структура: {"name": "news", "arguments": {...}}
                  
    Returns:
        dict: Результат выполнения функции get_news_titles
        
    Example:
        >>> tool_call = {
        ...     "name": "news",
        ...     "arguments": "{}"
        ... }
        >>> result = execute_news_tool(tool_call)
        >>> print(result)
        {'titles': ['Bitcoin Price Plummets...', ...], 'total_count': 10}
    """
    # Извлекаем имя функции
    function_name = tool_call.get("name", "")
    
    if function_name != "news":
        return {
            "error": f"Неизвестная функция: {function_name}",
        }
    
    # Парсим аргументы (могут быть строкой JSON или уже словарем)
    arguments = tool_call.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as e:
            return {
                "error": f"Ошибка парсинга аргументов: {str(e)}",
            }
    
    # Вызываем функцию получения новостей
    return get_news_titles()


def register_news_tool(tools_list: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Регистрирует tool "news" в списке tools для GigaChat.
    
    Если передан существующий список tools, добавляет news tool к нему.
    Если список не передан, создает новый список с одним news tool.
    
    Args:
        tools_list: Опциональный список существующих tools
        
    Returns:
        list: Список tools с добавленным news tool
        
    Example:
        >>> # Создание нового списка tools
        >>> tools = register_news_tool()
        >>> 
        >>> # Добавление к существующему списку
        >>> existing_tools = [other_tool]
        >>> all_tools = register_news_tool(existing_tools)
    """
    if tools_list is None:
        tools_list = []
    
    # Проверяем, не добавлен ли уже news tool
    news_tool = get_news_tool()
    for tool in tools_list:
        if tool.get("function", {}).get("name") == "news":
            # Tool уже есть, возвращаем список без изменений
            return tools_list
    
    # Добавляем news tool
    tools_list.append(news_tool)
    return tools_list


# ---------------------------------------------------------------------------
# Пример использования
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import io
    # Устанавливаем UTF-8 кодировку для вывода в Windows
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 60)
    print("Пример использования news tool")
    print("=" * 60)
    
    # 1. Пример прямого вызова функции get_news_titles
    print("\n1. Прямой вызов get_news_titles:")
    print("-" * 60)
    result = get_news_titles()
    print(f"Результат: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 2. Пример получения определения tool
    print("\n2. Определение tool для GigaChat:")
    print("-" * 60)
    tool_def = get_news_tool()
    print(json.dumps(tool_def, ensure_ascii=False, indent=2))
    
    # 3. Пример регистрации tool
    print("\n3. Регистрация tool:")
    print("-" * 60)
    tools = register_news_tool()
    print(f"Зарегистрировано tools: {len(tools)}")
    print(f"Имя tool: {tools[0]['function']['name']}")
    
    # 4. Пример выполнения tool_call (симуляция вызова от GigaChat)
    print("\n4. Симуляция вызова tool от GigaChat:")
    print("-" * 60)
    simulated_tool_call = {
        "name": "news",
        "arguments": json.dumps({}),
    }
    tool_result = execute_news_tool(simulated_tool_call)
    print(f"Tool call: {json.dumps(simulated_tool_call, ensure_ascii=False, indent=2)}")
    print(f"Результат выполнения: {json.dumps(tool_result, ensure_ascii=False, indent=2)}")
    
    print("\n" + "=" * 60)
    print("Пример завершен")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Пример интеграции в gigachat_client.py:
# ---------------------------------------------------------------------------
#
# from news_tool import get_news_tool, execute_news_tool, register_news_tool
# from gigachat.models import Chat, Messages, MessagesRole
#
# # При создании Chat объекта добавить tools:
# tools = register_news_tool()  # или register_news_tool(existing_tools)
# chat = Chat(
#     messages=messages,
#     model=model,
#     temperature=temperature,
#     tools=tools,  # Добавить tools параметр
#     flags=["no_cache"],
# )
#
# # При обработке ответа от GigaChat, если есть tool_calls:
# response = client.chat(chat)
# if hasattr(response, 'choices') and response.choices:
#     message = response.choices[0].message
#     if hasattr(message, 'tool_calls') and message.tool_calls:
#         # Выполнить вызовы tools
#         for tool_call in message.tool_calls:
#             if tool_call.get('function', {}).get('name') == 'news':
#                 result = execute_news_tool(tool_call)
#                 # Добавить результат обратно в историю сообщений
#
# ---------------------------------------------------------------------------

