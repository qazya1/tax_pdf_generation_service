# Tax PDF Generation Service

A FastAPI backend that fills out real IRS tax form templates (PDF/AcroForm) with data received via a JSON API and returns ready-to-download PDF tax returns.

The repository actually contains **two independent, sibling services** that share the same design pattern (see [Architecture](#architecture)):

| Service | Location | What it generates |
|---|---|---|
| **Personal return generator** | repository root | Individual **Form 1040** package (Schedule 1, Schedule 2, Schedule B, Schedule C, Schedule SE, e-file authorization) for a single taxpayer or a married couple |
| **Corporate return generator** | [`c_generation/`](./c_generation) | **Form 1120 / 1120‑S** corporate package (1125‑A, 1125‑E, 8949, Schedule D/D‑S/G, K‑1 per owner) plus the owners' personal 1040 returns, multi‑year projections, and a synthetic IRS tax‑transcript document |

Both were built as separate FastAPI apps rather than a single shared package — see [Two services, one pattern](#two-services-one-pattern) for why, and what it would take to merge them.

> **Note on the data.** Only the fields that matter for the filing (identity, income, refund/due amounts, etc.) come from the API request. Everything an IRS reviewer would also expect to see but that the API doesn't ask for — the preparing CPA firm, notarization dates, a matching brokerage statement of stock trades, dividend income from real public companies — is filled in with plausible randomized values from the CSV configs in [`configs/`](./configs). In other words, this service produces **realistic-looking, synthetic tax documents**, not a real e-filing pipeline: there is no IRS e-file/MeF integration, and it does not calculate a legally accurate tax liability. It's best understood as a document-generation engine for demos, QA fixtures, or synthetic training data.

---

## How it works

Both services follow the same three-step pipeline:

1. **Validate & normalize the request.** The personal service validates a raw JSON body by hand (regexes + field checks in `main.py`); the corporate service uses Pydantic models (`c_generation/fast_api_models.py`) for the same job.
2. **Compute derived figures and build one Python object per IRS form/schedule.** `forms_classes.py` (or `c_generation/forms_classes.py`) contains a class per form (e.g. `Form_1040`, `Schedule1`, `ScheduleC`, `Form_1120`, `Schedule_K1`, …). Each class:
   - pulls year-dependent constants from the CSVs in `configs/` (tax brackets, standard deduction, SE-tax rates, dividend-paying companies, a CPA firm directory, sample brokerage transactions);
   - computes the numbers for every line of that form;
   - stores them in a `{form_field_name: value}` dict.
3. **Fill the official PDF template and merge.** `pdf_filling.py`'s `Form.filling_pdf()` opens the blank IRS template for that form/year from `forms/<FormName>/<year>.pdf`, looks up each logical field name in `pdf_fields.json` to get the real AcroForm widget name, and writes the value into that widget with [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`). Signatures and typed dates are rendered as images (`courier_new.ttf`) and stamped onto the page. `create_pdf.py` then merges every filled form into one final PDF and (for the personal service) a matching IRS tax-transcript PDF.

The FastAPI app (`main.py`) exposes this as an HTTP API, stores generated files on disk, and serves them back for download.

### Two services, one pattern

`c_generation/` is a **parallel implementation**, not a library consumer of the root project — each has its own copy of `main.py`, `create_pdf.py`, `forms_classes.py`, `pdf_filling.py`, `pdf_fields.json`, `interface.html`, `courier_new.ttf` and `configs/`. The corporate service was evidently built by starting from the personal service's code and generalizing the same "compute → fill AcroForm → merge PDFs" pattern to a different set of forms (and, notably, the corporate service also calls back into a `Form_1040`-shaped flow to generate each owner's personal return). This makes the two feel like the same project at heart, filling out a different stack of IRS forms — hence "one uses the other" as a design pattern, even though there's no import between the two directories at runtime.

Because the copies have already diverged in small ways (the corporate `pdf_filling.py` has an extra `None`-image guard, logs to `./logs/`, etc.), merging them into a single shared package is a real refactor — worth doing for a production version, but out of scope for a quick cleanup (see [Known limitations](#known-limitations)).

---

## Project structure

```
.
├── main.py                 # FastAPI app: /generate-file, /download/*, /info/{id}
├── create_pdf.py            # Orchestrates one 1040 package (main_tax_return)
├── forms_classes.py         # One class per form/schedule; tax calculations
├── pdf_filling.py           # AcroForm filling engine (PyMuPDF) + title page
├── pdf_fields.json          # Maps logical field names -> PDF widget names, by form/year
├── interface.html           # Minimal manual test UI served at "/"
├── courier_new.ttf           # Font used to render signatures/typed text as images
├── configs/                  # CSV lookup tables (brackets, deductions, CPA firms, ...)
├── forms/                    # Blank IRS templates, one folder per form, one PDF per year
├── requirements.txt
│
└── c_generation/             # Corporate (1120 / 1120-S) sibling service — see its own README
    ├── main.py, create_pdf.py, forms_classes.py, pdf_filling.py, ...
    ├── fast_api_models.py     # Pydantic request schema (this service validates via models)
    └── forms/, configs/
```

`forms/` holds the actual **blank IRS PDF templates** used as fill targets (e.g. `forms/1040/2024.pdf`, `forms/ScheduleC/2023.pdf`). They are looked up by `forms/<FormName>/<year>.pdf`, matching the keys in `pdf_fields.json`.

---

## API reference — personal return service (root)

### `POST /generate-file`

Generates a Form 1040 package (+ IRS tax transcript) for one taxpayer and stores it server-side.

**Request body** (JSON):

| Parameter | Type | Required | Description | Constraints |
|---|---|---|---|---|
| `firstName` | String | Yes | Taxpayer's first name | – |
| `lastName` | String | Yes | Taxpayer's last name | – |
| `maritalStatus` | Enum | Yes | Marital status | `Single`, `MarriedFilingJointly` |
| `spouseFirstName` | String | No* | Spouse's first name | *required if `maritalStatus = MarriedFilingJointly`* |
| `spouseLastName` | String | No* | Spouse's last name | *required if `maritalStatus = MarriedFilingJointly`* |
| `residentialAddress` | String | Yes | Residential address | – |
| `town` | String | Yes | Town/City | – |
| `state` | Enum | Yes | State (affects notary data) | list of US states |
| `zipCode` | String | Yes | ZIP code | `XXXXX` or `XXXXX-XXXX` |
| `ssn` | String | Yes | Taxpayer's SSN | exactly 9 digits |
| `spouseSsn` | String | No* | Spouse's SSN | *required if married*; exactly 9 digits |
| `occupation` | String | Yes | Taxpayer's occupation | – |
| `spouseOccupation` | String | No* | Spouse's occupation | *required if married* |
| `employmentType` | Enum | Yes | Employment status | `Employed`, `Sole Prop. / Self-employed` |
| `principalBusiness` | String | No* | Business/profession | *required if self-employed* |
| `ein` | String | No* | EIN | *optional even if self-employed*; `XX-XXXXXXX` |
| `naicsCode` | String | No* | NAICS code | *required if self-employed*; exactly 6 digits |
| `businessName` | String | No | Business name, if different from personal name | defaults to `firstName + lastName` |
| `businessAddress` | String | No | Business address, if different | defaults to `residentialAddress` |
| `businessTown` | String | No | Business town, if different | defaults to `town` |
| `businessState` | Enum | No | Business state, if different | defaults to `state` |
| `businessZip` | String | No | Business ZIP, if different | `XXXXX` or `XXXXX-XXXX` |
| `year` | Number | Yes | Tax filing year | `2022`–`2025` (2025 reuses 2024's schedules) |
| `grossIncomeAmount` | Number | Yes | Gross income amount | must be positive |
| `refundOrPayment` | Enum | Yes | Refund or payment selection | `TAX_REFUND`, `TAX_DUE` |
| `refundAmount` | Number | No* | Refund amount | *required if `refundOrPayment = TAX_REFUND`* |
| `bankAccountNumber` | String | No* | Bank account number | *required if claiming refund*; max 17 digits |
| `bankRoutingNumber` | String | No* | Bank routing number | *required if claiming refund*; max 9 digits |
| `taxesDueAmount` | Number | No* | Taxes due amount | *required if `refundOrPayment = TAX_DUE`* |
| `preparationType` | Enum | Yes | Tax preparation type | `Self-prepared`, `CPA-prepared` |
| `dependents` | Array | No | List of dependents (max 4) | each: `{ name, ssn (9 digits), relation }` |
| `signature` | File | Yes | Taxpayer's signature (PNG) | base64-encoded image |
| `spouseSignature` | File | No* | Spouse's signature | *required if married*; base64-encoded image |

**Response body:**

| Field | Type | Description |
|---|---|---|
| `fileId` | String | UUID identifying the generated files |
| `downloadLink` | String | Link to download the tax return |
| `transcriptLink` | String | Link to download the tax transcript |
| `status` | String | `"success"` |

**Errors:** `400` — request JSON is malformed or fails validation · `500` — error during generation.

### `GET /download/{file_id}` / `GET /download/transcript/{file_id}`

Downloads the generated return / transcript PDF for a given `fileId`. `404` if the id or the underlying file doesn't exist.

### `GET /info/{file_id}`

Returns the metadata that was stored for a previously generated return.

| Field | Type | Description |
|---|---|---|
| `taxYear` | string | Tax year for the filing |
| `name` | string | Primary taxpayer's full name |
| `maritalStatus` | string | `"Single"` or `"Married, filling jointly"` |
| `spouseName` | string | Spouse's full name, if applicable |
| `SSN` / `spouseSSN` | string | Social Security Number(s) |
| `refundOrOwed` | string | `"I want to claim a refund"` or `"I want to pay taxes due"` |
| `refundAmount` / `owedAmount` | number | Amount, if applicable |
| `dependent1Name` … `dependent4Name` | string | Dependents' names |
| `preparerFirmName`, `preparerFirmAddress`, `preparerFirmEIN`, `preparerFirmPTIN` | string | Assigned CPA firm details |

**Errors:** `404` — no file with that id.

> This service persists metadata in **MySQL** (see [Configuration](#configuration)); the corporate service in `c_generation/` does not use a database — see [its README](./c_generation/README.md) for its API.

---

## Configuration

The root service reads DB credentials from a `config.json` file (not committed) at startup:

```json
{
  "databaseName": "...",
  "user": "...",
  "password": "..."
}
```

It expects a reachable local MySQL server and creates its `files` table automatically on boot (`init_db()` in `main.py`).

## Running locally

```bash
pip install -r requirements.txt
# create config.json with your MySQL credentials (see above)
python main.py            # serves on http://127.0.0.1:8000
```

A minimal manual test form is served at `/` (`interface.html`).

For the corporate service, see [`c_generation/README.md`](./c_generation/README.md).

---

## Known limitations

- **`config.json` isn't committed.** The root service won't start without it (MySQL credentials). This is expected for a project that shouldn't ship real credentials, but it means the service can't be run out of the box without first creating that file (or swapping storage for something else).
- **Not a real e-filing system.** No IRS MeF/e-file integration; several supporting figures (CPA firm, filing dates, sample brokerage trades, dividend income) are randomized from the CSVs in `configs/`, so the output is realistic but not a legally accurate return.
- **`c_generation` duplicates most of the root project's code** (`pdf_filling.py`, font, parts of `configs/`) instead of importing it as a shared package. Functionally fine since each is deployed as its own service, but a real refactor (shared `common/` package) would remove the duplication — left as-is here since the two copies have already diverged slightly in behavior.
- **`c_generation`'s owners/officers limit doesn't match its own docs.** The request docs describe up to 8 owners and 8 officers, but the current Pydantic model (`fast_api_models.py`) caps both lists at 4 (`max_items=4`).
- **`c_generation`'s tax-transcript form is currently unreachable.** `TaxTranscript1120.filling_pdf()` looks for a template at `forms/tax_transcript1120/<year>.pdf`, but only a single flat `forms/tax_transcript1120.pdf` is committed — the year-based template is missing. Generating a corporate return's tax transcript will fail until that template is added in the expected location.
