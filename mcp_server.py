#!/usr/bin/env python3
"""
Объединенный MCP сервер для получения новостей о Bitcoin и погоды.
Содержит два инструмента:
1. get_news - получение новостей о Bitcoin через newsdata.io API
2. get_weather - получение погоды через API Яндекс.Погоды
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Порт сервера (8082 чтобы не конфликтовать с Airflow на 8080)
PORT = 8082

# URL API новостей
NEWS_API_URL = "https://newsdata.io/api/1/latest?apikey=pub_9e46781355424a7b98d14269cebceb8d&q=bitcoin"

# URL API Яндекс.Погоды
YANDEX_WEATHER_API_URL = "https://api.weather.yandex.ru/v2/forecast"


class MCPRequestHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для MCP сервера с инструментами новостей и погоды."""
    
    def do_GET(self):
        """Обработка GET запросов."""
        try:
            # Парсинг URL и параметров
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)
            
            logger.info(f"Входящий GET запрос: {self.path}")
            logger.info(f"Параметры запроса: {query_params}")
            
            # Маршрутизация по пути
            if path == '/news' or path == '/get_news':
                response_data = self._handle_news_request()
            elif path == '/weather' or path == '/get_weather':
                latitude = query_params.get('latitude', [None])[0]
                longitude = query_params.get('longitude', [None])[0]
                response_data = self._handle_weather_request(latitude, longitude)
            elif path == '/' or path == '/health':
                # Эндпоинт для проверки работоспособности
                response_data = {
                    "status": "ok",
                    "server": "MCP Server",
                    "tools": ["get_news", "get_weather"],
                    "endpoints": {
                        "news": "/news или /get_news",
                        "weather": "/weather или /get_weather (требует latitude и longitude)"
                    }
                }
            else:
                response_data = {
                    "error": "Неизвестный эндпоинт",
                    "available_endpoints": ["/news", "/get_news", "/weather", "/get_weather", "/health"]
                }
            
            # Отправка ответа
            status_code = 200 if 'error' not in response_data else 400
            if path not in ['/', '/health', '/news', '/get_news', '/weather', '/get_weather']:
                status_code = 404
            self._send_json_response(response_data, status_code)
            
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
            
            # Парсинг URL
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            logger.info(f"Входящий POST запрос: {self.path}")
            logger.info(f"Тело запроса: {body}")
            
            # Парсинг JSON
            request_data = {}
            if body:
                try:
                    request_data = json.loads(body)
                except json.JSONDecodeError as e:
                    error_response = {"error": f"Некорректный JSON: {str(e)}"}
                    self._send_json_response(error_response, 400)
                    return
            
            # Маршрутизация по пути
            if path == '/news' or path == '/get_news':
                response_data = self._handle_news_request()
            elif path == '/weather' or path == '/get_weather':
                latitude = request_data.get('latitude')
                longitude = request_data.get('longitude')
                response_data = self._handle_weather_request(latitude, longitude)
            else:
                response_data = {
                    "error": "Неизвестный эндпоинт",
                    "available_endpoints": ["/news", "/get_news", "/weather", "/get_weather"]
                }
            
            # Отправка ответа
            status_code = 200 if 'error' not in response_data else 400
            if path not in ['/news', '/get_news', '/weather', '/get_weather']:
                status_code = 404
            self._send_json_response(response_data, status_code)
            
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
    
    def _handle_weather_request(self, latitude, longitude):
        """
        Обрабатывает запрос на получение погоды.
        
        Args:
            latitude: Широта
            longitude: Долгота
            
        Returns:
            dict: JSON с данными о погоде или ошибкой
        """
        # Проверка наличия координат
        if latitude is None or longitude is None:
            logger.warning("Отсутствуют координаты в запросе")
            return {"error": "Необходимо указать latitude и longitude"}
        
        # Проверка и преобразование координат
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            logger.warning(f"Некорректные координаты: lat={latitude}, lon={longitude}")
            return {"error": "Координаты должны быть числами"}
        
        # Проверка диапазона координат
        if not (-90 <= latitude <= 90):
            logger.warning(f"Широта вне допустимого диапазона: {latitude}")
            return {"error": "Широта должна быть в диапазоне от -90 до 90"}
        
        if not (-180 <= longitude <= 180):
            logger.warning(f"Долгота вне допустимого диапазона: {longitude}")
            return {"error": "Долгота должна быть в диапазоне от -180 до 180"}
        
        # Получение API ключа
        api_key = os.getenv('YANDEX_WEATHER_API_KEY')
        if not api_key:
            logger.error("Переменная окружения YANDEX_WEATHER_API_KEY не установлена")
            return {"error": "API ключ не настроен. Установите переменную окружения YANDEX_WEATHER_API_KEY"}
        
        # Проверка, что ключ не пустой
        api_key = api_key.strip()
        if not api_key:
            logger.error("API ключ пустой")
            return {"error": "API ключ пустой. Проверьте переменную окружения YANDEX_WEATHER_API_KEY в .env файле"}
        
        # Запрос к API Яндекс.Погоды
        try:
            logger.info(f"Запрос к API Яндекс.Погоды для координат: lat={latitude}, lon={longitude}")
            
            headers = {
                'X-Yandex-Weather-Key': api_key
            }
            
            params = {
                'lat': latitude,
                'lon': longitude
            }
            
            response = requests.get(YANDEX_WEATHER_API_URL, headers=headers, params=params, timeout=10)
            
            logger.info(f"Ответ от API Яндекс.Погоды: статус {response.status_code}")
            
            # Проверка статуса ответа
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Ошибка API Яндекс.Погоды: статус {response.status_code}, ответ: {error_text}")
                
                # Более детальное сообщение об ошибке
                if response.status_code == 403:
                    return {
                        "error": "Ошибка доступа (403). Проверьте правильность API ключа YANDEX_WEATHER_API_KEY",
                        "details": error_text if error_text else "Forbidden"
                    }
                elif response.status_code == 401:
                    return {
                        "error": "Ошибка аутентификации (401). Неверный API ключ",
                        "details": error_text if error_text else "Unauthorized"
                    }
                else:
                    return {
                        "error": f"Ошибка API Яндекс.Погоды: статус {response.status_code}",
                        "details": error_text if error_text else "Unknown error"
                    }
            
            # Парсинг ответа
            weather_data = response.json()
            logger.info(f"Полный ответ от API: {json.dumps(weather_data, ensure_ascii=False, indent=2)}")
            
            # Извлечение нужных данных
            try:
                # Для /v2/forecast структура: weather_data['fact']
                fact = weather_data.get('fact', {})
                
                if not fact:
                    # Попробуем альтернативную структуру
                    logger.warning("Поле 'fact' не найдено, проверяю альтернативную структуру")
                    fact = weather_data.get('forecasts', [{}])[0].get('parts', {}).get('day', {}) if weather_data.get('forecasts') else {}
                
                result = {
                    "temperature": fact.get('temp'),
                    "condition": fact.get('condition'),
                    "wind_speed": fact.get('wind_speed'),
                    "humidity": fact.get('humidity')
                }
                
                # Проверка, что хотя бы некоторые данные получены
                if all(v is None for v in result.values()):
                    logger.error(f"Не удалось извлечь данные из ответа. Структура: {weather_data}")
                    return {"error": "Не удалось извлечь данные о погоде из ответа API", "raw_response": weather_data}
                
                logger.info(f"Успешный ответ: {result}")
                return result
                
            except (KeyError, AttributeError, IndexError) as e:
                logger.error(f"Ошибка при парсинге ответа API: {e}, данные: {weather_data}")
                return {"error": f"Неожиданный формат ответа от API: {str(e)}", "raw_response": weather_data}
            
        except requests.exceptions.Timeout:
            logger.error("Таймаут при запросе к API Яндекс.Погоды")
            return {"error": "Таймаут при запросе к API Яндекс.Погоды"}
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с API Яндекс.Погоды: {e}")
            return {"error": f"Ошибка соединения с API: {str(e)}"}
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к API Яндекс.Погоды: {e}")
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
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    logger.info(f"Запуск объединенного MCP сервера на порту {port}")
    logger.info(f"Сервер доступен по адресу: http://localhost:{port}")
    logger.info("Доступные инструменты:")
    logger.info("  - GET/POST /news или /get_news - получение новостей о Bitcoin")
    logger.info("  - GET/POST /weather или /get_weather - получение погоды (требует latitude и longitude)")
    logger.info("  - GET /health - проверка работоспособности сервера")
    logger.info("Для остановки нажмите Ctrl+C")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
        httpd.shutdown()
        logger.info("Сервер остановлен")


if __name__ == '__main__':
    run_server()

