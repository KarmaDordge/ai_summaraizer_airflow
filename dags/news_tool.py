"""
Модуль для работы с новостями через tool для GigaChat API.

Реализует функцию get_news_titles и регистрацию tool "news" для использования
в GigaChat агенте. Использует стандартную библиотеку requests.
Обращается к локальному MCP серверу news_server.py.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests


# URL локального объединенного MCP сервера (новости)
# Для Docker используем host.docker.internal для доступа к хосту
# Для Linux Docker может потребоваться IP адрес хоста (например, 172.17.0.1)
# Можно переопределить через переменную окружения NEWS_SERVER_URL
NEWS_SERVER_URL = os.getenv(
    'NEWS_SERVER_URL',
    'http://host.docker.internal:8082/news'
)


def get_news_titles() -> Dict[str, Any]:
    """
    Получает заголовки новостей о Bitcoin.
    
    Делает GET запрос к объединенному MCP серверу (mcp_server.py)
    по эндпоинту /news и возвращает заголовки новостей. Сервер должен быть запущен на порту 8082.
    
    Примечание: Для работы в Docker используется host.docker.internal для доступа к хосту.
    Если mcp_server запущен на хосте, он должен быть доступен по этому адресу.
    
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

