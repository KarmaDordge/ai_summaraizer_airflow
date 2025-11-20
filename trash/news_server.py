#!/usr/bin/env python3
"""
Локальный MCP сервер для получения новостей о Bitcoin через newsdata.io API.
Запускается на порту 8081 и принимает запросы, возвращает только заголовки новостей.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Порт сервера
PORT = 8081

# URL API новостей
NEWS_API_URL = "https://newsdata.io/api/1/latest?apikey=pub_9e46781355424a7b98d14269cebceb8d&q=bitcoin"


class NewsRequestHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для получения новостей."""
    
    def do_GET(self):
        """Обработка GET запросов."""
        try:
            logger.info(f"Входящий GET запрос: {self.path}")
            
            # Обработка запроса
            response_data = self._handle_news_request()
            
            # Отправка ответа
            self._send_json_response(response_data, 200 if 'error' not in response_data else 400)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке GET запроса: {e}", exc_info=True)
            error_response = {"error": f"Внутренняя ошибка сервера: {str(e)}"}
            self._send_json_response(error_response, 500)
    
    def do_POST(self):
        """Обработка POST запросов."""
        try:
            # Чтение тела запроса
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            logger.info(f"Входящий POST запрос: {self.path}")
            logger.info(f"Тело запроса: {body}")
            
            # Обработка запроса (параметры не требуются, но можно использовать для будущих расширений)
            response_data = self._handle_news_request()
            
            # Отправка ответа
            self._send_json_response(response_data, 200 if 'error' not in response_data else 400)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке POST запроса: {e}", exc_info=True)
            error_response = {"error": f"Внутренняя ошибка сервера: {str(e)}"}
            self._send_json_response(error_response, 500)
    
    def _handle_news_request(self):
        """
        Обрабатывает запрос на получение новостей.
        
        Returns:
            dict: JSON с заголовками новостей или ошибкой
        """
        # Запрос к API новостей
        try:
            logger.info("Запрос к newsdata.io API")
            
            response = requests.get(NEWS_API_URL, timeout=10)
            
            logger.info(f"Ответ от API новостей: статус {response.status_code}")
            
            # Проверка статуса ответа
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Ошибка API новостей: статус {response.status_code}, ответ: {error_text}")
                
                return {
                    "error": f"Ошибка API новостей: статус {response.status_code}",
                    "details": error_text if error_text else "Unknown error"
                }
            
            # Парсинг ответа
            news_data = response.json()
            logger.info(f"Получен ответ от API, всего результатов: {news_data.get('totalResults', 0)}")
            
            # Извлечение только заголовков (title) из results
            try:
                titles = []
                if "results" in news_data and isinstance(news_data["results"], list):
                    for article in news_data["results"]:
                        if "title" in article:
                            titles.append(article["title"])
                
                result = {
                    "titles": titles,
                    "total_count": len(titles)
                }
                
                logger.info(f"Успешно извлечено заголовков: {len(titles)}")
                return result
                
            except (KeyError, AttributeError, TypeError) as e:
                logger.error(f"Ошибка при парсинге ответа API: {e}, данные: {news_data}")
                return {
                    "error": f"Неожиданный формат ответа от API: {str(e)}",
                    "raw_response": news_data
                }
            
        except requests.exceptions.Timeout:
            logger.error("Таймаут при запросе к API новостей")
            return {"error": "Таймаут при запросе к API новостей"}
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с API новостей: {e}")
            return {"error": f"Ошибка соединения с API: {str(e)}"}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к API новостей: {e}")
            return {"error": f"Ошибка сети: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
            return {"error": f"Неожиданная ошибка: {str(e)}"}
    
    def _send_json_response(self, data, status_code=200):
        """
        Отправляет JSON ответ клиенту.
        
        Args:
            data: Данные для отправки (будут преобразованы в JSON)
            status_code: HTTP статус код
        """
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json_data.encode('utf-8'))
        
        logger.info(f"Отправлен ответ со статусом {status_code}")
    
    def log_message(self, format, *args):
        """Переопределение метода логирования для использования нашего logger."""
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(port=PORT):
    """Запускает HTTP сервер."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, NewsRequestHandler)
    
    logger.info(f"Запуск MCP сервера новостей на порту {port}")
    logger.info(f"Сервер доступен по адресу: http://localhost:{port}")
    logger.info("Для остановки нажмите Ctrl+C")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
        httpd.shutdown()
        logger.info("Сервер остановлен")


if __name__ == '__main__':
    run_server()

