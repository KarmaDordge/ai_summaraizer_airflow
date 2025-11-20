# Скрипт для пуша проекта в GitHub репозиторий
# https://github.com/KarmaDordge/ai_summaraizer_airflow

Write-Host "Инициализация Git репозитория..." -ForegroundColor Green

# Инициализация репозитория
git init

# Добавление remote репозитория
git remote add origin https://github.com/KarmaDordge/ai_summaraizer_airflow.git

# Добавление всех файлов (с учетом .gitignore)
Write-Host "Добавление файлов..." -ForegroundColor Green
git add .

# Создание коммита
Write-Host "Создание коммита..." -ForegroundColor Green
git commit -m "Initial commit: AI Summarizer Airflow project"

# Переименование ветки в main (если нужно)
git branch -M main

# Push в репозиторий
Write-Host "Отправка в GitHub..." -ForegroundColor Green
Write-Host "ВНИМАНИЕ: Вам может потребоваться ввести учетные данные GitHub!" -ForegroundColor Yellow
git push -u origin main

Write-Host "Готово! Проект успешно отправлен в GitHub." -ForegroundColor Green

