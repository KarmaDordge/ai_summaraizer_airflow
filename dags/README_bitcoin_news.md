# DAG: Bitcoin News Summary

Этот DAG автоматически получает новости о Bitcoin, создает саммари через GigaChat и отправляет результат на email каждый час.

## Требования

1. **Запущенный news_server.py** на порту 8081
2. **Установленная библиотека gigachat**: `pip install gigachat`
3. **Настроенные переменные окружения** для GigaChat и email

## Настройка

### 1. Настройка GigaChat

#### Формат credentials для GigaChat

**Важно:** GigaChat требует **Authorization Key** (ключ авторизации), полученный в личном кабинете!

**Как получить Authorization Key:**

1. Зайдите на [GigaChat Developers](https://developers.sber.ru/gigachat) (Studio)
2. Войдите в личный кабинет
3. Создайте проект GigaChat API (если еще не создан)
4. В разделе **"Настройки API"** вашего проекта нажмите **"Получить ключ"**
5. **ВАЖНО:** Сохраните значение поля **"Authorization Key"** - оно отображается только один раз!
6. Этот ключ уже является base64 строкой и готов к использованию

**Формат файла `config/gigachat_credentials.json`:**

Код автоматически обрабатывает несколько форматов:

1. **Простая строка (рекомендуется)** - просто Authorization Key в файле:
   ```
   ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg==
   ```
   (просто скопируйте Authorization Key в файл, без кавычек и JSON)

2. **JSON с `authorization`** - если хотите использовать JSON формат:
   ```json
   {
     "authorization": "ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg=="
   }
   ```

3. **JSON с `client_secret`** (устаревший формат, но поддерживается):
   ```json
   {
     "client_id": "ваш_client_id",
     "client_secret": "ZWRmN2JmOGItNT...",
     "scope": "GIGACHAT_API_PERS"
   }
   ```
   Код автоматически использует `client_secret` как credentials.

**ВАЖНО:** 
- Используйте **Authorization Key** из личного кабинета, а не client_id/client_secret!
- Authorization Key - это уже готовая base64 строка для авторизации
- Если потеряли ключ, нужно создать новый проект или получить новый ключ

#### Способ 1: Через файл с Authorization Key (Рекомендуется)

1. **Получите Authorization Key:**
   - Зайдите на [GigaChat Developers](https://developers.sber.ru/gigachat)
   - Войдите в личный кабинет Studio
   - Создайте проект GigaChat API (если еще не создан)
   - В разделе **"Настройки API"** нажмите **"Получить ключ"**
   - **ВАЖНО:** Скопируйте **Authorization Key** - он отображается только один раз!

2. **Создайте файл `config/gigachat_credentials.json`** в корне проекта:
   
   **Вариант A: Простая строка (рекомендуется)**
   ```
   ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg==
   ```
   (просто вставьте Authorization Key в файл, без кавычек и JSON)
   
   **Вариант B: JSON формат**
   ```json
   {
     "authorization": "ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg=="
   }
   ```

3. **Настройте в `docker-compose.yaml`** (уже настроено):
   ```yaml
   environment:
     GIGACHAT_CREDENTIALS: /opt/airflow/config/gigachat_credentials.json
     GIGACHAT_MODEL: GigaChat-Pro
   ```

4. **Перезапустите контейнеры:**
   ```bash
   docker compose down
   docker compose up -d
   ```

#### Способ 2: Через Airflow Variables

1. Откройте Airflow UI: `http://localhost:8080`
2. Перейдите в **Admin → Variables**
3. Добавьте переменную `GIGACHAT_CREDENTIALS` со значением:
   - **Просто Authorization Key** (base64 строка):
     ```
     ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg==
     ```
   - **Или JSON формат:**
     ```json
     {"authorization":"ZGVmN2JmOGItNWM1YS00NGIzLWI5MjAtZjkzZjgxNzAzYTJkOjkzODhhZDY3LWQ0NWYtNGMxZi1iMmZjLTVhMzQ3YzczNzcxMg=="}
     ```

4. Добавьте переменную `GIGACHAT_MODEL` со значением: `GigaChat-Pro`

**Важно:** 
- Файл `config/gigachat_credentials.json` должен существовать на хосте
- Файл монтируется в контейнер как read-only (`:ro`)
- Не коммитьте файл с реальными credentials в git! Добавьте в `.gitignore`:
  ```
  config/gigachat_credentials.json
  ```

### 2. Настройка Email

Установите email получателя:

```bash
NEWS_SUMMARY_EMAIL=your_email@example.com
```

Или через Airflow UI:
- Admin -> Variables
- Добавьте переменную `NEWS_SUMMARY_EMAIL` с вашим email

### 3. Настройка SMTP в Airflow (для Docker)

Для Airflow в Docker есть несколько способов настройки SMTP. Выберите наиболее удобный:

#### Способ 1: Через переменные окружения в docker-compose.yaml (Рекомендуется)

**Важно:** В этом DAG используется `SmtpHook` напрямую, поэтому `EMAIL_BACKEND` не нужен. Airflow автоматически использует SMTP настройки.

Откройте файл `docker-compose.yaml` и добавьте переменные окружения в секцию `&airflow-common-env`:

```yaml
environment:
  &airflow-common-env
  # ... существующие переменные ...
  
  # SMTP настройки для отправки email
  # EMAIL_BACKEND не нужен - Airflow автоматически использует SMTP настройки через SmtpHook
  # AIRFLOW__EMAIL__EMAIL_BACKEND: 'airflow.providers.smtp.hooks.smtp.SmtpHook'  # НЕ НУЖЕН!
  AIRFLOW__SMTP__SMTP_HOST: 'smtp.gmail.com'
  AIRFLOW__SMTP__SMTP_STARTTLS: 'True'
  AIRFLOW__SMTP__SMTP_SSL: 'False'
  AIRFLOW__SMTP__SMTP_USER: 'your_email@gmail.com'
  AIRFLOW__SMTP__SMTP_PASSWORD: 'your_app_password'
  AIRFLOW__SMTP__SMTP_PORT: '587'
  AIRFLOW__SMTP__SMTP_MAIL_FROM: 'your_email@gmail.com'
```

**Важно:** После изменения `docker-compose.yaml` перезапустите контейнеры:
```bash
docker-compose down
docker-compose up -d
```

#### Способ 2: Через файл airflow.cfg (если он монтируется)

Если у вас настроен volume для `airflow.cfg`, откройте файл `config/airflow.cfg` и добавьте:

```ini
# EMAIL_BACKEND не нужен - Airflow автоматически использует SMTP настройки
# [email]
# # email_backend = airflow.providers.smtp.hooks.smtp.SmtpHook  # НЕ НУЖЕН!  # НЕ НУЖЕН!

[smtp]
smtp_host = smtp.gmail.com
smtp_starttls = True
smtp_ssl = False
smtp_user = your_email@gmail.com
smtp_password = your_app_password
smtp_port = 587
smtp_mail_from = your_email@gmail.com
```

#### Способ 3: Через Airflow UI -> Connections (Альтернативный)

1. Откройте Airflow UI: `http://localhost:8080`
2. Перейдите в **Admin → Connections**
3. Нажмите **+** (Add a new record)
4. Заполните:
   - **Connection Id**: `smtp_default`
   - **Connection Type**: `Email`
   - **Host**: `smtp.gmail.com`
   - **Schema**: (оставьте пустым)
   - **Login**: `your_email@gmail.com`
   - **Password**: `your_app_password`
   - **Port**: `587`
   - **Extra**: 
     ```json
     {
       "smtp_starttls": true,
       "smtp_ssl": false
     }
     ```
5. Нажмите **Save**

#### Настройка для разных почтовых сервисов

**Gmail:**
- Host: `smtp.gmail.com`
- Port: `587`
- StartTLS: `True`
- SSL: `False`
- **Важно:** Используйте [App Password](https://support.google.com/accounts/answer/185833) вместо обычного пароля:
  1. Включите 2FA в Google аккаунте
  2. Перейдите в [App Passwords](https://myaccount.google.com/apppasswords)
  3. Создайте новый App Password для "Mail"
  4. Используйте этот пароль в настройках

**Yandex Mail:**
- Host: `smtp.yandex.ru`
- Port: `465` или `587`
- StartTLS: `True` (для 587) или `False` (для 465)
- SSL: `True` (для 465) или `False` (для 587)
- User: полный email адрес
- Password: пароль от почты или App Password

**Outlook/Hotmail:**
- Host: `smtp-mail.outlook.com`
- Port: `587`
- StartTLS: `True`
- SSL: `False`
- **КРИТИЧЕСКИ ВАЖНО:** Используйте **App Password** вместо обычного пароля!
  
  **Как получить App Password для Outlook/Hotmail:**
  1. Войдите в [Microsoft Account Security](https://account.microsoft.com/security)
  2. Включите **двухфакторную аутентификацию (2FA)** (если еще не включена)
  3. Перейдите в раздел **"Advanced security options"** или **"App passwords"**
  4. Нажмите **"Create a new app password"**
  5. Выберите приложение: **"Mail"** и устройство: **"Other"**
  6. Скопируйте сгенерированный App Password (16 символов, например: `abcd efgh ijkl mnop`)
  7. Используйте этот App Password в `AIRFLOW__SMTP__SMTP_PASSWORD` (без пробелов)
  
  **Важно:** 
  - Обычный пароль от аккаунта НЕ РАБОТАЕТ!
  - App Password показывается только один раз - сохраните его!
  - Если потеряли App Password, создайте новый

**Mail.ru:**
- Host: `smtp.mail.ru`
- Port: `465` или `587`
- StartTLS: `True` (для 587)
- SSL: `True` (для 465)

#### Проверка настройки SMTP

Для проверки можно создать тестовый DAG или выполнить в Python:

```python
from airflow.utils.email import send_email

send_email(
    to=['test@example.com'],
    subject='Test Email',
    html_content='<p>This is a test email from Airflow</p>'
)
```

#### Безопасность паролей

**Не храните пароли в открытом виде!** Используйте один из способов:

1. **Переменные окружения через .env файл** (не коммитьте в git):
   ```bash
   # .env файл (добавьте в .gitignore)
   AIRFLOW__SMTP__SMTP_PASSWORD=your_app_password
   ```
   В `docker-compose.yaml`:
   ```yaml
   env_file:
     - .env
   ```

2. **Airflow Secrets Backend** (для production):
   - Используйте HashiCorp Vault, AWS Secrets Manager и т.д.
   - Настройте через `AIRFLOW__SECRETS__BACKEND`

3. **Docker Secrets** (для Docker Swarm):
   ```yaml
   secrets:
     smtp_password:
       external: true
   ```

#### Пример полной конфигурации для docker-compose.yaml

Добавьте в секцию `environment: &airflow-common-env` вашего `docker-compose.yaml`:

```yaml
environment:
  &airflow-common-env
  # ... существующие переменные Airflow ...
  
  # SMTP настройки для отправки email
  # EMAIL_BACKEND не нужен - Airflow автоматически использует SMTP настройки через SmtpHook
  # AIRFLOW__EMAIL__EMAIL_BACKEND: 'airflow.providers.smtp.hooks.smtp.SmtpHook'  # НЕ НУЖЕН!
  AIRFLOW__SMTP__SMTP_HOST: 'smtp.gmail.com'
  AIRFLOW__SMTP__SMTP_STARTTLS: 'True'
  AIRFLOW__SMTP__SMTP_SSL: 'False'
  AIRFLOW__SMTP__SMTP_USER: 'your_email@gmail.com'
  AIRFLOW__SMTP__SMTP_PASSWORD: 'your_app_password_here'
  AIRFLOW__SMTP__SMTP_PORT: '587'
  AIRFLOW__SMTP__SMTP_MAIL_FROM: 'your_email@gmail.com'
```

**После изменений:**
```bash
# Остановите контейнеры
docker-compose down

# Запустите заново
docker-compose up -d

# Проверьте логи
docker-compose logs airflow-webserver | grep -i smtp
```

## Запуск

1. **Убедитесь, что `news_server.py` запущен на хосте:**
   ```bash
   python news_server.py
   ```
   Сервер должен быть доступен на `http://localhost:8081`

2. **Важно для Docker:** 
   - Если Airflow работает в Docker, а `news_server.py` на хосте, используется `host.docker.internal:8081`
   - Это уже настроено в `dags/news_tool.py`
   - Для Linux Docker может потребоваться изменить на IP адрес хоста (например, `172.17.0.1:8081`)

3. DAG автоматически появится в Airflow UI после перезагрузки scheduler

4. Включите DAG в Airflow UI (переключите тумблер)

5. DAG будет запускаться каждый час автоматически

## Структура DAG

1. **get_news** - Получает новости через news_tool
2. **summarize_news** - Создает саммари через GigaChat с использованием news tool
3. **prepare_email** - Формирует HTML содержимое email
4. **send_email** - Отправляет email с саммари

## Troubleshooting

### Ошибка "Библиотека gigachat не установлена"
```bash
pip install gigachat
```

### Ошибка "Не указаны учетные данные GigaChat"
Проверьте, что переменная `GIGACHAT_CREDENTIALS` установлена в Airflow Variables

### Ошибка "Ошибка при запросе новостей" или "Connection refused"

**Проблема:** Airflow в Docker не может подключиться к `news_server.py` на хосте.

**Решение:**

1. **Проверьте, что `news_server.py` запущен на хосте:**
   ```bash
   # На хосте
   curl http://localhost:8081
   ```

2. **Для Docker Desktop (Windows/Mac):**
   - Уже настроено: используется `host.docker.internal:8081`
   - Проверьте доступность из контейнера:
     ```bash
     docker compose exec airflow-webserver curl http://host.docker.internal:8081
     ```

3. **Для Linux Docker:**
   - Если `host.docker.internal` не работает, используйте IP адрес хоста
   - Найдите IP хоста: `ip addr show docker0 | grep inet`
   - Или используйте `172.17.0.1` (обычный IP Docker bridge)
   - Измените в `dags/news_tool.py`:
     ```python
     NEWS_SERVER_URL = "http://172.17.0.1:8081"  # или ваш IP
     ```

4. **Альтернатива:** Запустите `news_server.py` в той же Docker сети:
   - Добавьте `news_server` как сервис в `docker-compose.yaml`
   - Или используйте `network_mode: host` для news_server

### Email не отправляется или отклоняется как спам

1. **Проверьте переменную `NEWS_SUMMARY_EMAIL`:**
   - Убедитесь, что она установлена в Airflow Variables
   - Формат: `user@example.com` (без пробелов)

2. **Проблема "spam message rejected" от Mail.ru:**
   
   Mail.ru может блокировать письма из Docker контейнеров. Решения:
   
   **Вариант 1: Добавить в белый список**
   - Перейдите по ссылке из ошибки: `https://help.mail.ru/notspam-support/...`
   - Или отправьте запрос на `abuse@corp.mail.ru` с кодом ошибки
   
   **Вариант 2: Использовать другой SMTP сервис**
   - Gmail (требует App Password)
   - Yandex Mail
   - Outlook/Hotmail
   - Собственный SMTP сервер
   
   **Вариант 3: Настроить SPF/DKIM записи**
   - Если используете собственный домен, настройте SPF и DKIM записи
   - Это поможет избежать блокировки как спам
   
   **Вариант 4: Упростить содержимое письма**
   - Код уже обновлен для минимизации спам-триггеров
   - Убраны сложные HTML стили
   - Добавлена текстовая версия письма

2. **Проверьте настройки SMTP:**
   ```bash
   # Войдите в контейнер Airflow
   docker-compose exec airflow-webserver bash
   
   # Проверьте переменные окружения
   env | grep SMTP
   ```

3. **Проверьте логи:**
   ```bash
   # Просмотр логов webserver
   docker-compose logs airflow-webserver | grep -i smtp
   
   # Просмотр логов scheduler
   docker-compose logs airflow-scheduler | grep -i email
   ```

4. **Частые проблемы:**
   - **"Basic authentication is disabled" (Outlook/Hotmail):** 
     - Используйте **App Password** вместо обычного пароля
     - Включите 2FA в Microsoft аккаунте
     - Создайте App Password в настройках безопасности
   - **Gmail блокирует:** Используйте App Password, не обычный пароль
   - **Mail.ru блокирует:** Может требовать OAuth2 или специальные настройки
   - **Порт заблокирован:** Проверьте, что порт 587 или 465 открыт
   - **Неправильный формат переменных:** В docker-compose.yaml используйте формат `AIRFLOW__SECTION__KEY`
   - **Проблемы с DNS:** В Docker может не резолвиться SMTP хост, попробуйте использовать IP или настройте DNS

5. **Тест отправки email:**
   ```python
   # В Airflow UI -> Admin -> Connections -> smtp_default -> Test
   # Или через Python в контейнере:
   from airflow.utils.email import send_email
   send_email(['test@example.com'], 'Test', 'Test message')
   ```

### Проблемы с доступом к news_server из Docker контейнера

Если `news_server.py` запущен на хосте, а не в контейнере:

1. **Для Docker Desktop (Windows/Mac):**
   - Измените `NEWS_SERVER_URL` в `dags/news_tool.py`:
     ```python
     NEWS_SERVER_URL = "http://host.docker.internal:8081"
     ```

2. **Для Linux Docker:**
   - Используйте IP адрес хоста:
     ```python
     NEWS_SERVER_URL = "http://172.17.0.1:8081"  # или ваш IP
     ```
   - Или запустите `news_server.py` в той же Docker сети

3. **Проверка доступности:**
   ```bash
   # Из контейнера Airflow
   docker-compose exec airflow-webserver curl http://host.docker.internal:8081
   ```

