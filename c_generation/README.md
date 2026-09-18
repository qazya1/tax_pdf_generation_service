# Corporate Tax PDF Generator (`c_generation`)

A second, sibling FastAPI service (see the [root README](../README.md) for how it relates to the personal-return service) that fills out a **corporate** IRS return package — Form 1120 (C‑corp) or 1120‑S (S‑corp) — together with its supporting schedules, each owner's personal Form 1040, and multi‑year projections, then returns downloadable PDFs.

It reuses the same fill-a-blank-AcroForm-template pattern as the root project (`pdf_filling.py` + `pdf_fields.json` + `forms/<FormName>/<year>.pdf`), generalized to the corporate form set. See [How it works](../README.md#how-it-works) in the root README for the shared mechanics; this document covers what's specific to the corporate service.

## What it generates

For the requested filing year (and any additional years requested):

- **Form 1120** (C‑corp) or **Form 1120‑S** (S‑corp) — selected by `company_type`
- **Form 1125‑A** (Cost of Goods Sold) — only if the company sells `Products`
- **Form 1125‑E** (Officer Compensation) — only if gross income ≥ $500,000
- **Schedule G** — only if any owner holds more than 20% ownership
- **Schedule D** (C‑corp) or **Schedule D‑S** (S‑corp) — capital gains/losses
- **Form 8949** — sales/dispositions of capital assets (backed by the sample brokerage transactions in `configs/transactions.csv`)
- **Schedule K‑1** — one per owner, S‑corp only
- **Firm authorization** (e‑file authorization for the company)
- A synthetic **IRS tax transcript** for the corporate return (see [Known limitations](../README.md#known-limitations) — this step currently can't find its PDF template)

If an owner has `generate_personal_tax_return: true`, the service additionally produces that owner's **personal Form 1040 package** (1040, Schedule 1, Schedule B, e‑file authorization) using the same `Form_1040`/`Schedule1`/`ScheduleB` machinery as the root project — this is the concrete instance of "one project using the other's forms" mentioned in the root README. If `need_multiple_years` is set, it repeats the whole corporate + personal generation for each future year, either from explicit per-year figures (`future_years`) or by applying a percentage growth/decline to the current year (`future_years_percents_income`).

## API reference

### `GET /`

Serves `interface.html`, a minimal manual test form.

### `POST /generate-file`

Accepts a `TaxReturnRequest` JSON body (validated with Pydantic — see `fast_api_models.py`) and generates the full set of PDFs described above. Returns a dict of generated file paths (corporate returns/transcripts per year, personal returns per owner per year) — see `main_tax_return()` in `create_pdf.py`.

### `GET /file/{file_path}`

Downloads a previously generated file by its server-side path.

---

## Request body (JSON structure)

### 1. Company information

| Field | Type | Validation | Required |
|---|---|---|---|
| `filing_year` | integer | Must be a valid year (e.g. `2023`). The oldest year for which the tax return is needed. | ✅ Yes |
| `company_name` | string | – | ✅ Yes |
| `company_type` | string | One of: `C corp`, `S corp`. | ✅ Yes |
| `company_street_address` | string | – | ✅ Yes |
| `company_town` | string | – | ✅ Yes |
| `company_state` | string | Must be a valid US state (e.g. `NY`, `CA`). | ✅ Yes |
| `company_zip` | string | `XXXXX`, `XXXXX-XXXX`, or `XXXXXXXXX`. | ✅ Yes |
| `ein` | string | `XX-XXXXXXX` or `XXXXXXXXX`. | ✅ Yes |
| `date_inc` | string (ISO‑8601) | Year must be ≤ `filing_year`. | ✅ Yes |
| `business_activity_code` | string | `XXXXXX`. | ✅ Yes |
| `principal_product_service` | string | – | ✅ Yes |
| `business_activity` | string | – | ✅ Yes |
| `sells_products_or_services` | string | One of: `Products`, `Services`, `Both`. | ✅ Yes |
| `products_percentage` | integer | Required if `sells_products_or_services = Both`. 1–99. | ❌ No |
| `phone` | string | Valid US phone number. | ❌ No |
| `ceo_name` | string | – | ✅ Yes |
| `ceo_position` | string | – | ✅ Yes |
| `ceo_signature` | string (Base64) | Must be a `.PNG` image at a specified resolution. | ✅ Yes |
| `total_assets` | number | – | ❌ No |

### 2. Financial information

| Field | Type | Validation | Required |
|---|---|---|---|
| `gross_receipts_sales` | number | – | ✅ Yes |
| `returns_allowances` | number | Cannot be entered if `cost_of_goods_sold` is provided. | ❌ No |
| `cost_of_goods_sold` | number | Cannot be entered if `returns_allowances` is provided. | ❌ No |
| `gross_rents` | number | – | ❌ No |
| `has_capital_gain_income` | boolean | – | ✅ Yes |
| `compensation_of_officers` | number | – | ✅ Yes |
| `has_employees` | boolean | – | ✅ Yes |
| `salaries_wages` | number | Must be `0` if `has_employees = false`. | ❌ No |
| `compensation_of_officers_in_cost_of_labor` | number | – | ❌ No |
| `taxes_licenses` | number | – | ❌ No |
| `repairs_maintenance` | number | – | ❌ No |
| `refund_or_tax_due` | string | One of: `REFUND`, `TAX DUE`. | ✅ Yes |
| `refund_amount` | number | Required if `refund_or_tax_due = REFUND`. | ❌ No |
| `tax_due_amount` | number | Required if `refund_or_tax_due = TAX DUE`. | ❌ No |
| `account_number` | string | Numeric. | ✅ Yes |
| `routing_number` | string | Valid US routing number. | ✅ Yes |

### 3. Owners information

An array of owners (max 8 entries — enforced by the docs; the current Pydantic model caps it at 4, see [Known limitations](../README.md#known-limitations)).

| Field | Type | Validation | Required |
|---|---|---|---|
| `name` | string | – | ✅ Yes |
| `ssn` | string | `XXXXXXXXX`. | ✅ Yes |
| `ownership_percentage` | number | ≤ 100 (all owners must total exactly 100). Max 1 decimal place. | ✅ Yes |
| `generate_personal_tax_return` | boolean | – | ✅ Yes |

If `generate_personal_tax_return = true`, each owner also needs:

| Field | Type | Validation | Required |
|---|---|---|---|
| `generate_future_returns` | boolean | – | ❌ No |
| `years_of_future_returns` | integer | Required if `generate_future_returns = true`. | ❌ No |
| `signature` | string (Base64) | `.PNG` image at a specified resolution. | ✅ Yes |
| `position` | string | – | ✅ Yes |
| `marital_status` | string | One of: `Single`, `MarriedFilingJointly`. | ✅ Yes |
| `dependents` | array | Follows the 1040-style dependent structure (see the [root API's `dependents` field](../README.md#api-reference--personal-return-service-root)). | ❌ No |
| `personal_refund_or_tax_due` | string | One of: `TAX_REFUND`, `TAX_DUE`. | ✅ Yes |
| `personal_refund_amount` | number | Required if `personal_refund_or_tax_due = REFUND`. | ❌ No |
| `personal_tax_due_amount` | number | Required if `personal_refund_or_tax_due = TAX DUE`. | ❌ No |
| `personal_account_number` | string | Numeric. | ✅ Yes |
| `personal_routing_number` | string | Valid US routing number. | ✅ Yes |

### 4. 1125‑E table (officer compensation)

An array of officers (max 8 entries). Required if business rules require it, or at least one owner has `generate_personal_tax_return = true`.

| Field | Type | Validation | Required |
|---|---|---|---|
| `name` | string | Pulled from the owners table. | ✅ Yes |
| `ssn` | string | Matches SSN format. | ✅ Yes |
| `ownership_percentage` | number | ≤ 100. Max 1 decimal place. | ✅ Yes |
| `time_percentage` | number | All officers must total exactly 100. | ✅ Yes |
| `compensation_percentage` | number | All officers must total exactly 100. | ✅ Yes |

### 5. Preparer information

| Field | Type | Validation | Required |
|---|---|---|---|
| `prepared_by` | string | One of: `Bookkeeper`, `CPA/Paid Preparer`. | ✅ Yes |

If `prepared_by = CPA/Paid Preparer`:

| Field | Type | Validation | Required |
|---|---|---|---|
| `use_own_cpa` | boolean | – | ✅ Yes |

If `use_own_cpa = true`:

| Field | Type | Validation | Required |
|---|---|---|---|
| `preparer_name` | string | – | ✅ Yes |
| `preparer_signature` | string (Base64) | `.PNG` image at a specified resolution. | ✅ Yes |
| `firm_name` | string | – | ✅ Yes |
| `firm_address` | string | – | ✅ Yes |
| `firm_ein` | string | `XX-XXXXXXX` or `XXXXXXXXX`. | ✅ Yes |
| `ptin` | string | `PXXXXXXXX`, `P XXXXXXXX`, or `P-XXXXXXXX`. | ✅ Yes |
| `firm_phone` | string | Valid US phone number. | ✅ Yes |

### 6. Future tax returns

| Field | Type | Validation | Required |
|---|---|---|---|
| `need_multiple_years` | boolean | – | ✅ Yes |
| `years_needed` | integer | Required if `need_multiple_years = true`. | ❌ No |

For each additional year — use **either** `future_years` (explicit figures) **or** `future_years_percents_income` (percentage change), not both:

**`future_years[]`** (explicit figures per year):

| Field | Type | Validation | Required |
|---|---|---|---|
| `year` | integer | Must be sequential after `filing_year`. | ✅ Yes |
| `gross_receipts_sales` | number | – | ❌ No |
| `returns_allowances` | number | Cannot be entered if `cost_of_goods_sold` is provided. | ❌ No |
| `cost_of_goods_sold` | number | Cannot be entered if `returns_allowances` is provided. | ❌ No |
| `gross_rents` | number | – | ❌ No |
| `has_capital_gain_income` | boolean | – | ✅ Yes |
| `compensation_of_officers` | number | – | ✅ Yes |
| `has_employees` | boolean | – | ✅ Yes |
| `salaries_wages` | number | Must be `0` if `has_employees = false`. | ❌ No |
| `taxes_licenses` | number | – | ❌ No |
| `repairs_maintenance` | number | – | ❌ No |
| `refund_or_tax_due` | string | One of: `REFUND`, `TAX DUE`. | ✅ Yes |
| `refund_amount` | number | Required if `refund_or_tax_due = REFUND`. | ❌ No |
| `tax_due_amount` | number | Required if `refund_or_tax_due = TAX DUE`. | ❌ No |
| `total_assets` | number | – | ❌ No |
| `account_number` | string | Numeric. | ✅ Yes |
| `routing_number` | string | Valid US routing number. | ✅ Yes |

**`future_years_percents_income[]`** (percentage change per year):

| Field | Type | Validation | Required |
|---|---|---|---|
| `how_income_change_this_year` | string | One of: `HIGHER`, `LOWER`. | ✅ Yes |
| `percents_higher` | integer | 1–300. | ❌ No |
| `percents_lower` | integer | 1–95. | ❌ No |

---

## Running locally

```bash
pip install -r requirements.txt
python main.py            # serves on http://127.0.0.1:8000
```

Unlike the root service, this one does **not** need a database or `config.json` — generated files are written straight to `./generated_files/` (created automatically), split into `transcripts/` and `personal/` subfolders, and served back by path via `GET /file/{file_path}`.

See the [root README's Known limitations](../README.md#known-limitations) for caveats that apply here (synthetic supporting data, missing tax-transcript template, code duplicated from the root project).
