# Генератор корпоративной налоговой декларации (`c_generation`)

Второй, родственный FastAPI-сервис (см. [корневой README](../README.md), где описано, как он связан с первым), который заполняет **корпоративный** пакет деклараций IRS — Form 1120 (C‑corp) или 1120‑S (S‑corp) — вместе с сопутствующими приложениями, личной декларацией Form 1040 каждого владельца и прогнозом на несколько лет вперёд, а затем возвращает готовые к скачиванию PDF.

Использует тот же паттерн «заполнить пустой шаблон AcroForm» (`pdf_filling.py` + `pdf_fields.json` + `forms/<ИмяФормы>/<год>.pdf`), что и корневой проект, но обобщённый под другой набор форм. Общий механизм описан в разделе [«Как это работает»](../README.md#как-это-работает) корневого README; здесь — только то, что специфично для корпоративного сервиса.

## Что генерируется

Для запрошенного года подачи (и любых дополнительных лет, если запрошены):

- **Form 1120** (C‑corp) или **Form 1120‑S** (S‑corp) — выбирается по `company_type`
- **Form 1125‑A** (себестоимость реализованной продукции) — только если компания продаёт `Products`
- **Form 1125‑E** (вознаграждение офицеров) — только если валовой доход ≥ 500 000 $
- **Schedule G** — только если у кого-то из владельцев доля больше 20%
- **Schedule D** (C‑corp) или **Schedule D‑S** (S‑corp) — прирост/убыток капитала
- **Form 8949** — операции с капитальными активами (на основе образцов брокерских сделок из `configs/transactions.csv`)
- **Schedule K‑1** — по одной на каждого владельца, только для S‑corp
- **Авторизация фирмы** (авторизация e-file для компании)
- Синтетическая **налоговая транскрипция IRS** для корпоративной декларации (см. [Известные ограничения](../README.md#известные-ограничения) — на этом шаге сейчас не находится PDF-шаблон)

Если у владельца `generate_personal_tax_return: true`, сервис дополнительно генерирует его **личный пакет Form 1040** (1040, Schedule 1, Schedule B, авторизация для e-file), используя тот же механизм `Form_1040`/`Schedule1`/`ScheduleB`, что и корневой проект — это и есть конкретный пример «использования одного проекта другим», упомянутый в корневом README. Если установлен `need_multiple_years`, вся генерация (корпоративная + личная) повторяется для каждого будущего года — либо по явным показателям за год (`future_years`), либо применением процента роста/падения к текущему году (`future_years_percents_income`).

## API

### `GET /`

Отдаёт `interface.html` — минимальную форму для ручного тестирования.

### `POST /generate-file`

Принимает тело запроса `TaxReturnRequest` в формате JSON (валидируется через Pydantic — см. `fast_api_models.py`) и генерирует весь описанный выше набор PDF. Возвращает словарь путей к сгенерированным файлам (корпоративные декларации/транскрипции по годам, личные декларации по владельцам и годам) — см. `main_tax_return()` в `create_pdf.py`.

### `GET /file/{file_path}`

Скачивание ранее сгенерированного файла по его пути на сервере.

---

## Тело запроса (структура JSON)

### 1. Информация о компании

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `filing_year` | integer | Должен быть корректным годом (например, `2023`). Самый ранний год, за который нужна декларация. | ✅ Да |
| `company_name` | string | – | ✅ Да |
| `company_type` | string | Одно из: `C corp`, `S corp`. | ✅ Да |
| `company_street_address` | string | – | ✅ Да |
| `company_town` | string | – | ✅ Да |
| `company_state` | string | Должен быть корректным штатом США (например, `NY`, `CA`). | ✅ Да |
| `company_zip` | string | `XXXXX`, `XXXXX-XXXX` или `XXXXXXXXX`. | ✅ Да |
| `ein` | string | `XX-XXXXXXX` или `XXXXXXXXX`. | ✅ Да |
| `date_inc` | string (ISO‑8601) | Год должен быть ≤ `filing_year`. | ✅ Да |
| `business_activity_code` | string | `XXXXXX`. | ✅ Да |
| `principal_product_service` | string | – | ✅ Да |
| `business_activity` | string | – | ✅ Да |
| `sells_products_or_services` | string | Одно из: `Products`, `Services`, `Both`. | ✅ Да |
| `products_percentage` | integer | Обязательно, если `sells_products_or_services = Both`. От 1 до 99. | ❌ Нет |
| `phone` | string | Корректный телефонный номер США. | ❌ Нет |
| `ceo_name` | string | – | ✅ Да |
| `ceo_position` | string | – | ✅ Да |
| `ceo_signature` | string (Base64) | Изображение `.PNG` заданного разрешения. | ✅ Да |
| `total_assets` | number | – | ❌ Нет |

### 2. Финансовая информация

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `gross_receipts_sales` | number | – | ✅ Да |
| `returns_allowances` | number | Нельзя указывать, если указан `cost_of_goods_sold`. | ❌ Нет |
| `cost_of_goods_sold` | number | Нельзя указывать, если указан `returns_allowances`. | ❌ Нет |
| `gross_rents` | number | – | ❌ Нет |
| `has_capital_gain_income` | boolean | – | ✅ Да |
| `compensation_of_officers` | number | – | ✅ Да |
| `has_employees` | boolean | – | ✅ Да |
| `salaries_wages` | number | Должно быть `0`, если `has_employees = false`. | ❌ Нет |
| `compensation_of_officers_in_cost_of_labor` | number | – | ❌ Нет |
| `taxes_licenses` | number | – | ❌ Нет |
| `repairs_maintenance` | number | – | ❌ Нет |
| `refund_or_tax_due` | string | Одно из: `REFUND`, `TAX DUE`. | ✅ Да |
| `refund_amount` | number | Обязательно, если `refund_or_tax_due = REFUND`. | ❌ Нет |
| `tax_due_amount` | number | Обязательно, если `refund_or_tax_due = TAX DUE`. | ❌ Нет |
| `account_number` | string | Числовое значение. | ✅ Да |
| `routing_number` | string | Корректный routing-номер банка США. | ✅ Да |

### 3. Информация о владельцах

Массив владельцев (максимум 8 записей — согласно документации; в текущей Pydantic-модели ограничение — 4, см. [Известные ограничения](../README.md#известные-ограничения)).

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `name` | string | – | ✅ Да |
| `ssn` | string | `XXXXXXXXX`. | ✅ Да |
| `ownership_percentage` | number | ≤ 100 (сумма по всем владельцам должна быть ровно 100). Максимум 1 знак после запятой. | ✅ Да |
| `generate_personal_tax_return` | boolean | – | ✅ Да |

Если `generate_personal_tax_return = true`, для владельца также требуется:

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `generate_future_returns` | boolean | – | ❌ Нет |
| `years_of_future_returns` | integer | Обязательно, если `generate_future_returns = true`. | ❌ Нет |
| `signature` | string (Base64) | Изображение `.PNG` заданного разрешения. | ✅ Да |
| `position` | string | – | ✅ Да |
| `marital_status` | string | Одно из: `Single`, `MarriedFilingJointly`. | ✅ Да |
| `dependents` | array | По структуре как иждивенцы в декларации 1040 (см. [поле `dependents` в корневом API](../README.md#api--сервис-личной-декларации-корень-репозитория)). | ❌ Нет |
| `personal_refund_or_tax_due` | string | Одно из: `TAX_REFUND`, `TAX_DUE`. | ✅ Да |
| `personal_refund_amount` | number | Обязательно, если `personal_refund_or_tax_due = REFUND`. | ❌ Нет |
| `personal_tax_due_amount` | number | Обязательно, если `personal_refund_or_tax_due = TAX DUE`. | ❌ Нет |
| `personal_account_number` | string | Числовое значение. | ✅ Да |
| `personal_routing_number` | string | Корректный routing-номер банка США. | ✅ Да |

### 4. Таблица 1125‑E (вознаграждение офицеров)

Массив офицеров (максимум 8 записей). Требуется, если этого требуют бизнес-правила, либо если хотя бы у одного владельца `generate_personal_tax_return = true`.

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `name` | string | Берётся из таблицы владельцев. | ✅ Да |
| `ssn` | string | Соответствует формату SSN. | ✅ Да |
| `ownership_percentage` | number | ≤ 100. Максимум 1 знак после запятой. | ✅ Да |
| `time_percentage` | number | Сумма по всем офицерам должна быть ровно 100. | ✅ Да |
| `compensation_percentage` | number | Сумма по всем офицерам должна быть ровно 100. | ✅ Да |

### 5. Информация о составителе декларации

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `prepared_by` | string | Одно из: `Bookkeeper`, `CPA/Paid Preparer`. | ✅ Да |

Если `prepared_by = CPA/Paid Preparer`:

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `use_own_cpa` | boolean | – | ✅ Да |

Если `use_own_cpa = true`:

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `preparer_name` | string | – | ✅ Да |
| `preparer_signature` | string (Base64) | Изображение `.PNG` заданного разрешения. | ✅ Да |
| `firm_name` | string | – | ✅ Да |
| `firm_address` | string | – | ✅ Да |
| `firm_ein` | string | `XX-XXXXXXX` или `XXXXXXXXX`. | ✅ Да |
| `ptin` | string | `PXXXXXXXX`, `P XXXXXXXX` или `P-XXXXXXXX`. | ✅ Да |
| `firm_phone` | string | Корректный телефонный номер США. | ✅ Да |

### 6. Будущие налоговые декларации

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `need_multiple_years` | boolean | – | ✅ Да |
| `years_needed` | integer | Обязательно, если `need_multiple_years = true`. | ❌ Нет |

Для каждого дополнительного года используйте **либо** `future_years` (явные показатели), **либо** `future_years_percents_income` (процентное изменение), но не оба сразу:

**`future_years[]`** (явные показатели по годам):

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `year` | integer | Должен идти последовательно после `filing_year`. | ✅ Да |
| `gross_receipts_sales` | number | – | ❌ Нет |
| `returns_allowances` | number | Нельзя указывать, если указан `cost_of_goods_sold`. | ❌ Нет |
| `cost_of_goods_sold` | number | Нельзя указывать, если указан `returns_allowances`. | ❌ Нет |
| `gross_rents` | number | – | ❌ Нет |
| `has_capital_gain_income` | boolean | – | ✅ Да |
| `compensation_of_officers` | number | – | ✅ Да |
| `has_employees` | boolean | – | ✅ Да |
| `salaries_wages` | number | Должно быть `0`, если `has_employees = false`. | ❌ Нет |
| `taxes_licenses` | number | – | ❌ Нет |
| `repairs_maintenance` | number | – | ❌ Нет |
| `refund_or_tax_due` | string | Одно из: `REFUND`, `TAX DUE`. | ✅ Да |
| `refund_amount` | number | Обязательно, если `refund_or_tax_due = REFUND`. | ❌ Нет |
| `tax_due_amount` | number | Обязательно, если `refund_or_tax_due = TAX DUE`. | ❌ Нет |
| `total_assets` | number | – | ❌ Нет |
| `account_number` | string | Числовое значение. | ✅ Да |
| `routing_number` | string | Корректный routing-номер банка США. | ✅ Да |

**`future_years_percents_income[]`** (процентное изменение по годам):

| Поле | Тип | Валидация | Обязательное |
|---|---|---|---|
| `how_income_change_this_year` | string | Одно из: `HIGHER`, `LOWER`. | ✅ Да |
| `percents_higher` | integer | От 1 до 300. | ❌ Нет |
| `percents_lower` | integer | От 1 до 95. | ❌ Нет |

---

## Запуск локально

```bash
pip install -r requirements.txt
python main.py            # доступен на http://127.0.0.1:8000
```

В отличие от корневого сервиса, этому **не нужна** база данных или `config.json` — сгенерированные файлы записываются прямо в `./generated_files/` (создаётся автоматически), с разбивкой по подпапкам `transcripts/` и `personal/`, и отдаются обратно по пути через `GET /file/{file_path}`.

Оговорки из [раздела «Известные ограничения» корневого README](../README.md#известные-ограничения) применимы и здесь (синтетические вспомогательные данные, отсутствующий шаблон налоговой транскрипции, код, дублированный из корневого проекта).
