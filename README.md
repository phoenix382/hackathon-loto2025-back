# Loto RNG Service

Сервис генерации тиражей лотереи и аудита случайных последовательностей на FastAPI. Поддерживает сбор энтропии из внешних источников (RSS‑новости, погодные данные) и локальных источников (OS RNG, временной джиттер), поэтапную визуализацию процесса (SSE), автоматические базовые статистические тесты и цифровой слепок результата для последующей верификации.

## Возможности
- Генерация тиражной комбинации с онлайн‑этапами (SSE): сбор энтропии, вайтинг, сид, результат, автотесты.
- Аудит внешнего генератора: загрузка последовательности (bits или файл), автоматический анализ и отчёт.
- Демонстрационный режим с пояснениями шагов.
- Swagger UI по адресу `/swagger` (OpenAPI JSON доступен по `/openapi.json`).

## Требования
- Python 3.10+
- Доступ в интернет для источников энтропии `news` и `weather` (при недоступности сервис продолжит работу на `os` и `time`).

## Установка и запуск
```
pip install -r requirements.txt
python run.py
# сервис поднимется на http://localhost:8000
```

Swagger UI: http://localhost:8000/swagger

## Сценарии использования

### 1) Проведение тиража (онлайн)
- POST `/draw/start` — старт генерации; возвращает `job_id`.
- GET `/draw/stream/{job_id}` — поток серверных событий (SSE) с этапами генерации.
- GET `/draw/result/{job_id}` — итог: комбинация, слепок, сводка автотестов.
- GET `/draw/bits/{job_id}` — белёные биты, использованные для генерации (для внешнего аудита).

Пример запуска:
```
curl -s -X POST http://localhost:8000/draw/start \
  -H "Content-Type: application/json" \
  -d '{
        "sources": ["news","weather","os","time"],
        "bits": 4096,
        "numbers": 6,
        "max_number": 49
      }'
# => {"job_id":"<uuid>"}
```

Просмотр этапов в реальном времени (в отдельном терминале/вкладке):
```
curl -N http://localhost:8000/draw/stream/<job_id>
```

Итог:
```
curl -s http://localhost:8000/draw/result/<job_id> | jq
```

Экспорт бит для внешнего тестирования:
```
curl -s http://localhost:8000/draw/bits/<job_id> | jq -r .bits > random_secure.txt
```

### 2) Аудит внешнего генератора
- POST `/audit/analyze` — принимает `sequence_bits` (строка из 0/1) или `numbers` (список int), запускает базовые тесты.
- POST `/audit/upload` — загрузка текстового файла, из которого извлекаются биты `0`/`1`.

Примеры:
```
# Битовая строка
curl -s -X POST http://localhost:8000/audit/analyze \
  -H "Content-Type: application/json" \
  -d '{"sequence_bits":"010011001101..."}' | jq

# Список чисел
curl -s -X POST http://localhost:8000/audit/analyze \
  -H "Content-Type: application/json" \
  -d '{"numbers":[12,7,33,45,3]}' | jq

# Файл с битами
curl -s -X POST http://localhost:8000/audit/upload \
  -H "Content-Type: multipart/form-data" \
  -F file=@random_secure.txt | jq
```

### 3) Демонстрация работы
- GET `/demo/stream` — SSE‑пояснения этапов (подходит для презентаций/объяснений):
```
curl -N "http://localhost:8000/demo/stream?scenario=default"
```

## Эндпоинты (сводка)
- Health
  - GET `/health` — проверка доступности
  - GET `/` — краткая сводка сервиса
- Draw
  - POST `/draw/start` — старт генерации тиража
  - GET `/draw/stream/{job_id}` — SSE‑этапы генерации
  - GET `/draw/result/{job_id}` — итог тиража
  - GET `/draw/bits/{job_id}` — белёные биты для аудита
- Audit
  - POST `/audit/analyze` — анализ последовательности
  - POST `/audit/upload` — анализ файла с битами
- Demo
  - GET `/demo/stream` — демонстрационный стрим

Подробные описания, теги и примеры доступны в Swagger UI (`/swagger`).

## Архитектура
```
app/
  main.py                 # FastAPI приложение и маршруты
  schemas.py              # Pydantic‑схемы запросов/ответов
  parsers/
    news_parser.py        # RSS‑новости (feedparser)
    weather_parser.py     # Погодные данные (Open‑Meteо)
  services/
    entropy.py            # Сбор энтропии, вайтинг, слепок
    generator.py          # Сценарий генерации тиража
    stat_tests.py         # Базовые статистические тесты (монобит, ран, блочный)
    logging.py            # Логгер этапов (для SSE)
  utils/
    sse.py                # Утилиты для Server‑Sent Events
run.py                    # Точка входа (Uvicorn)
requirements.txt          # Зависимости
```

## Источники энтропии
- `news` — RSS ленты (в конфиге источников по умолчанию соберём несколько последних новостей, текст хэшируется).
- `weather` — сводные данные по континентам из Open‑Meteo (агрегация, затем хэш).
- `os` — `os.urandom`.
- `time` — временной джиттер из `perf_counter_ns` (батчи хэшируются).

Далее применяется вайтинг (экстрактор фон Неймана), из результата строится криптографический `seed`, рассчитывается цифровой слепок (SHA‑256) и генерируется тираж без смещения (`random.Random(seed).sample`).

## Тестирование случайности
В API встроены быстрые базовые тесты:
- Монобит‑частоты (NIST‑подобный)
- Тест серий (runs)
- Блочный тест частот

Они удобны для онлайн‑индикации, но не заменяют полный набор NIST SP 800‑22. Для полноценного аудита воспользуйтесь библиотекой `nistrng` (уже в `requirements.txt`).

Пример запуска полного теста на сохранённых битах:
```
python - << 'PY'
from nistrng import check_eligibility_all_battery, run_all_battery, SP800_22R1A_BATTERY
import numpy as np

with open('random_secure.txt','r') as f:
    bits = ''.join(ch for ch in f.read() if ch in '01')
seq = np.array([int(b) for b in bits], dtype=int)
elig = check_eligibility_all_battery(seq, SP800_22R1A_BATTERY)
results = run_all_battery(seq, elig, SP800_22R1A_BATTERY)
print('Eligible:', sum(elig.values()), 'of', len(elig))
passed = 0
for (res, _), name in zip(results, elig):
    if elig[name]:
        print(name, 'PASS' if res.passed else 'FAIL', 'p=', res.score)
        passed += int(res.passed)
print('Summary:', passed, 'tests passed')
PY
```

> Примечание: для некоторых тестов требуется достаточно длинная последовательность (сотни тысяч и более бит).

## Настройки и примеры запросов
Тело для `/draw/start`:
```json
{
  "sources": ["news", "weather", "os", "time"],
  "bits": 4096,
  "numbers": 6,
  "max_number": 49
}
```
- `sources`: какие источники энтропии использовать.
- `bits`: целевой объём бит перед вайтингом (по необходимости расширяется детерминированным хэш‑каскадом).
- `numbers`: сколько чисел в тираже.
- `max_number`: верхняя граница диапазона (включительно).

## Замечания и ограничения
- SSE не воспроизводится в Swagger UI — используйте браузер/`curl -N`/клиент SSE.
- Сетевые источники могут быть недоступны — сервис всё равно завершит генерацию на `os`/`time`.
- Базовые статистические тесты — индикативны; для регуляторного аудита используйте NIST SP 800‑22.

## Лицензирование и права
Проект предназначен для демонстрационных/внутренних целей хакатона. Использование внешних источников данных подчиняется их условиям.

