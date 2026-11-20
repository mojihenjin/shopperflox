# Shopperflox

<div align="center">

**Современная маркетплейс-платформа для брендов, независимых мастеров и покупателей**

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 📖 О проекте

**Shopperflox** — это масштабируемая e-commerce экосистема, ориентированная на бренды, независимых авторов (artisans / self-worked creators) и розничных покупателей. Платформа решает полный цикл задач маркетплейса: от публикации товаров с премодерацией до управления очередью сборки заказов, мультивалютных расчетов (RUB / CNY), логистики с сетью почтовых отделений и интеграции с платёжными шлюзами.

### Ключевые возможности

- 🛍️ **Каталог товаров и вариативность**: поддержка размеров, цветов, остатков на складах, группировки по коллекциям и брендам, загрузки галереи с сортировкой и индикаторов ограниченных тиражей (`is_limited`).
- 🎨 **Кабинет брендов и авторов**: возможность создания брендов, управления участниками с разграничением прав (`creator:brand`), загрузки брендинга и логотипов.
- ⚖️ **Система премодерации**: жизненный цикл товаров (черновик -> на модерации -> одобрен / отклонен с причиной), защита витрины от некорректного контента.
- 📦 **Оформление заказов и логистика**:
  - Гибкие варианты доставки (Почта России / ПВЗ, курьер, самовывоз).
  - Справочник почтовых отделений с разделением доступа для операторов доставки (`mod:mail-manager`).
  - Управление паспортами для таможенного декларирования и международных отправлений.
  - Конвейер исполнения заказов (очередь производства, статусы: `pending`, `paid`, `in_production`, `dispatched`, `in_transit`, `ready_for_pickup`, `delivered`, `returning`, `returned`, `cancelled`).
- 💳 **Мультивалютность и платежи**: расчет цен в рублях и юанях (CNY) с динамической конвертацией; режим отладочной оплаты (`debug_pay`) для локальной разработки и интеграция с платежным шлюзом (`BILLING_ENABLED`).
- 🔐 **Безопасность корпоративного уровня**:
  - Асимметричная аутентификация по алгоритму **EdDSA (Ed25519)** с открытым ключом.
  - Хеширование паролей **Argon2id** с дополнительной солью-перцем (PEPPER).
  - Моментальный отзыв токенов (Token Blacklist & Revocation) в Redis при изменении прав пользователя или смене пароля.
  - Иерархический RBAC: суперпользователь (`*`), администраторы (`admin:access`), модераторы каталога (`mod:approve_manager`), менеджеры доставки (`mod:mail-manager`).
- ⚡ **Фоновые задачи и SMTPless-режим**: асинхронный брокер **Taskiq + Redis** для отправки писем, верификационных кодов и сброса паролей. В dev-режиме не требует внешнего SMTP — все коды направляются прямо в логи воркера.
- 📊 **Наблюдаемость (Observability)**: встроенные эндпоинты Prometheus (`/metrics`), готовые дашборды в Grafana, Healthchecks (`/health/live`, `/health/ready`).

---

## 🏛️ Архитектура системы

```mermaid
flowchart TD
    Client(["Клиент (Браузер / API)"]) -->|HTTP:80| NGINX["Nginx Reverse Proxy\n(Rate Limiting & Static/Media)"]
    
    subgraph Frontend["Frontend SPA"]
        NGINX -->|/| SPA["React 19 + TypeScript + Vite\n(Tailwind CSS, Zustand, React Query)"]
    end

    subgraph Backend["Backend Services"]
        NGINX -->|/api/v1| API["FastAPI Application\n(Clean Architecture & UoW)"]
        NGINX -->|/metrics| PromExp["Prometheus Metrics"]
        
        API --> DB[(PostgreSQL 17\npg_trgm indexes)]
        API --> Redis[(Redis 7\nCache & Taskiq Broker)]
        
        API -.->|Enqueue Tasks| Worker["Taskiq Worker\n(Email & Background jobs)"]
        Worker --> Redis
        Worker -.->|Console / SMTP| MailTransport["Email Transport"]
    end

    subgraph Monitoring["Observability Stack"]
        Prometheus["Prometheus TSDB"] -->|Scrape :8000/metrics| API
        Grafana["Grafana 11"] -->|Query| Prometheus
    end
```

---

## 🛠️ Стек технологий

| Область | Технологии |
|---|---|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy 2.0 (asyncio), Asyncpg, Alembic, Pydantic v2 |
| **Очереди & Фоновые задачи** | Taskiq, Taskiq-Redis, Redis 7 |
| **База данных** | PostgreSQL 17 (с расширением `pg_trgm` для быстрого нечеткого поиска) |
| **Безопасность** | Ed25519 (EdDSA JWT via PyJWT & Cryptography), Argon2id (pwdlib) |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, TanStack React Query v5, Zustand |
| **Инфраструктура** | Docker, Docker Compose, Nginx 1.27 Alpine |
| **Мониторинг** | Prometheus 2.54, Grafana 11.2, Loguru |
| **Пакетные менеджеры** | `uv` (Python), `npm` (Node.js) |

---

## 🚀 Быстрый старт

### Требования

- **Docker** и **Docker Compose** (версии v2 / Compose CLI)
- **Python >= 3.13** и пакетный менеджер **[uv](https://docs.astral.sh/uv/)**

---

### Пошаговая инструкция запуска

#### 1. Синхронизация зависимостей и генерация конфигурации (.env)

Перейдите в директорию `backend`, выполните синхронизацию окружения и генерацию ключей шифрования, пользователей и базы данных:

```bash
cd backend
uv sync
uv run get_env.py
```

> [!TIP]
> Утилита `get_env.py` автоматически сгенерирует приватный/публичный ключ Ed25519 для JWT, стойкий pepper для Argon2, пароли для PostgreSQL и Grafana, а также скопирует готовый файл конфигурации в корневой `.env`.
> Для полностью автоматического режима без интерактивных запросов можно вызвать:
> ```bash
> uv run get_env.py --auto
> ```

Вернитесь в корень проекта:
```bash
cd ..
```

---

#### 2. Сборка и запуск контейнеров в Docker

Запустите все сервисы платформы (Nginx, Frontend, Backend, Taskiq Worker, PostgreSQL, Redis, Prometheus, Grafana) в фоновом режиме:

```bash
docker-compose up -d --build
```

---

#### 3. Применение миграций базы данных

После успешного старта контейнеров накатите схему базы данных с помощью Alembic:

```bash
docker-compose exec backend alembic upgrade head
```

*(или через прямое обращение к контейнеру)*:
```bash
docker exec shopperflox-backend alembic upgrade head
```

---

#### 4. Работа в режиме SMTPless (получение паролей и кодов подтверждения)

По умолчанию проект настроен в режиме `EMAIL_BACKEND=console`. Все отправляемые системой электронные письма (верификационные коды, ссылки активации, сгенерированные пароли) выводятся в стандартный поток вывода воркера Taskiq.

Чтобы посмотреть последние события или получить сгенерированный пароль / код:

```bash
# Просмотр последнего сообщения:
docker-compose logs worker --tail 1

# Просмотр последних 5 строк (или по имени контейнера):
docker logs shopperflox-worker --tail 5
```

---

#### 5. Полная остановка и очистка проекта в Docker

Для полной очистки всех запущенных сервисов, пользовательских томов данных (volumes) и собранных docker-образов:

```bash
docker-compose down -v --rmi all
```

---

## 🌐 Сетевые порты и доступ к сервисам

После запуска контейнеров доступны следующие эндпоинты:

| Сервис | URL | Назначение |
|---|---|---|
| **Веб-интерфейс (Frontend)** | [http://localhost](http://localhost) | Витрина магазина, каталог, корзина, чекаут, админка |
| **REST API & Swagger UI** | [http://localhost/docs](http://localhost/docs) | Интерактивная документация OpenAPI / Swagger |
| **ReDoc API Документация** | [http://localhost/redoc](http://localhost/redoc) | Альтернативная спецификация API |
| **Healthcheck (Live)** | [http://localhost/health/live](http://localhost/health/live) | Проверка работоспособности сервиса |
| **Prometheus Metrics** | [http://localhost/metrics](http://localhost/metrics) | Сырые метрики бэкенда для сбора |
| **Grafana Dashboard** | [http://localhost:3000](http://localhost:3000) | Дашборды мониторинга (логин/пароль из `.env`) |
| **Prometheus UI** | [http://localhost:9090](http://localhost:9090) | Прямой интерфейс метрик Prometheus |

---

## ⚙️ Переменные окружения

Файл `.env` формируется скриптом `backend/get_env.py` (шаблоны доступны в [`.env.example`](.env.example) и [`backend/.env.example`](backend/.env.example)):

| Переменная | Описание | Значение по умолчанию |
|---|---|---|
| `APP_ENV` | Окружение приложения (`dev`, `test`, `production`) | `dev` |
| `DEBUG` | Режим отладки (в `production` строго запрещен) | `True` |
| `DATABASE_URL` / `DB_URL` | Строка подключения к PostgreSQL через asyncpg | Автогенерация |
| `REDIS_URL` | Строка подключения к Redis | `redis://localhost:6379/0` |
| `JWT_ALGORITHM` | Алгоритм подписи JWT-токенов | `EdDSA` |
| `JWT_PRIVATE_KEY` | Hex-представление приватного ключа Ed25519 (32 байта) | Автогенерация |
| `JWT_PUBLIC_KEY` | Hex-представление публичного ключа Ed25519 | Автодеривация |
| `PEPPER` | Секретная соль для Argon2id | Автогенерация |
| `EMAIL_BACKEND` | Режим почты: `console` (SMTPless в логи) или `smtp` | `console` |
| `STORAGE_BACKEND` | Хранилище медиа: `local` или `s3` | `local` |
| `BILLING_ENABLED` | Включение внешнего биллинга (платежного шлюза) | `False` |

---

## 🧪 Тестирование и локальная разработка

### Тесты бэкенда

Тестовый набор бэкенда включает более 220 интеграционных и модульных тестов с использованием in-memory SQLite и мок-брокеров:

```bash
cd backend
uv run pytest
```

### Проверка типов и сборка фронтенда

```bash
cd frontend
npm run typecheck
npm run build
```

---

## 📄 Лицензия

Проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).
