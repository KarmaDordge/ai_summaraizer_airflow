# Инструкция по настройке GigaChat Authorization Key

## Где получить Authorization Key

1. **Откройте сайт:** https://developers.sber.ru/gigachat
2. **Войдите в личный кабинет** (Studio)
3. **Создайте проект GigaChat API** (если еще не создан)
4. **Перейдите в раздел "Настройки API"** вашего проекта
5. **Нажмите кнопку "Получить ключ"**
6. **ВАЖНО:** Скопируйте **Authorization Key** - он отображается только один раз!
   - Это длинная base64 строка, например: `ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg==`

## Как установить

### Вариант 1: Через файл (Рекомендуется)

1. Создайте файл `config/gigachat_credentials.json` в корне проекта
2. Вставьте Authorization Key в файл (просто строку, без кавычек):
   ```
   ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg==
   ```
3. Файл уже настроен в `docker-compose.yaml`
4. Перезапустите контейнеры:
   ```bash
   docker compose down
   docker compose up -d
   ```

### Вариант 2: Через Airflow Variables

1. Откройте Airflow UI: http://localhost:8080
2. Перейдите в **Admin → Variables**
3. Добавьте переменную:
   - **Key:** `GIGACHAT_CREDENTIALS`
   - **Value:** ваш Authorization Key (base64 строка)
4. Добавьте переменную:
   - **Key:** `GIGACHAT_MODEL`
   - **Value:** `GigaChat-Pro`

## Проверка

После настройки DAG должен работать. Если возникают ошибки авторизации, проверьте:
- Правильность скопированного Authorization Key
- Что файл `config/gigachat_credentials.json` существует и доступен
- Что переменные окружения установлены в контейнере

