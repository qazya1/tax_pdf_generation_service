from typing import List, Optional, Union
from datetime import date
from pydantic import BaseModel, Field, validator, constr
from enum import Enum
import copy

# Enums для выбора значений
class CompanyType(str, Enum):
    C_CORP = "C corp"
    S_CORP = "S corp"

class SellsProductsOrServices(str, Enum):
    PRODUCTS = "Products"
    SERVICES = "Services"
    BOTH = "Both"

class MaritalStatus(str, Enum):
    SINGLE = "Single"
    MARRIED_FILLING_JOINTLY = "MarriedFilingJointly"

class RefundOrTaxDue(str, Enum):
    REFUND = "TAX_REFUND"
    TAX_DUE = "TAX_DUE"

class PreparedBy(str, Enum):
    BOOKKEEPER = "Bookkeeper"
    CPA_PAID_PREPARER = "CPA/Paid Preparer"

class UseOwnCPA(str, Enum):
    OWN_DETAILS = "My own details"
    YOUR_CPA = "Your CPA"

class IncomeChangeThisYear(str, Enum):
    HIGHER = "HIGHER"
    LOWER = "LOWER"

# Вложенные модели
class Dependent(BaseModel):
    name: str
    ssn: str
    relationship: str

class Owner(BaseModel):
    name: str
    ssn: str
    ownership_percentage: float = Field(..., ge=0.1, le=100)
    generate_personal_tax_return: bool
    generate_future_returns: Optional[bool] = None
    years_of_future_returns: Optional[int] = Field(None, ge=1)
    signature: Optional[str] = None  # Base64 PNG
    position: Optional[str] = None
    marital_status: Optional[MaritalStatus] = None
    dependents: Optional[List[Dependent]] = None
    personal_refund_or_tax_due: Optional[RefundOrTaxDue] = None
    personal_refund_amount: Optional[float] = None
    personal_tax_due_amount: Optional[float] = None
    personal_account_number: Optional[str] = None
    personal_routing_number: Optional[str] = None

class Officer(BaseModel):
    name: str
    ssn: str
    time_percentage: float = Field(..., ge=0.1, le=100)
    ownership_percentage: float = Field(..., ge=0.1, le=100)
    compensation_percentage: float = Field(..., ge=0.1, le=100)

class FutureYear(BaseModel):
    year: int
    gross_receipts_sales: Optional[float] = None
    returns_allowances: Optional[float] = None
    cost_of_goods_sold: Optional[float] = None
    gross_income: float
    gross_rents: Optional[float] = None
    has_capital_gain_income: bool
    compensation_of_officers: float
    has_employees: bool
    salaries_wages: Optional[float] = None
    taxes_licenses: Optional[float] = None
    repairs_maintenance: Optional[float] = None
    refund_or_tax_due: RefundOrTaxDue
    refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    account_number: str
    routing_number: str
    total_assets: Optional[float] = None

class FutureYearPercents(BaseModel):
    year: int
    how_income_change_this_year: IncomeChangeThisYear
    percents_higher: Optional[int] = Field(None, ge=1, le=300)
    percents_lower: Optional[int] = Field(None, ge=1, le=95)

class CPAInfo(BaseModel):
    preparer_name: str
    preparer_signature: str  # Base64 PNG
    firm_name: str
    firm_address: str
    firm_ein: str
    ptin: str
    firm_phone: str

# Основная модель запроса
class TaxReturnRequest(BaseModel):
    # 1. Company Information
    filing_year: int
    company_name: str
    company_type: CompanyType
    company_street_address: str
    company_town: str
    company_state: str
    company_zip: str
    ein: str
    date_inc: date
    business_activity_code: str
    business_activity: str
    principal_product_service: str
    sells_products_or_services: SellsProductsOrServices
    products_percentage: Optional[int] = Field(None, ge=1, le=99)
    phone: Optional[str] = None
    ceo_name: str
    ceo_position: str
    ceo_signature: str  # Base64 PNG
    total_assets: Optional[float] = None

    # 2. Financial Information
    gross_receipts_sales: float
    returns_allowances: Optional[float] = None
    cost_of_goods_sold: Optional[float] = None
    gross_rents: Optional[float] = None
    has_capital_gain_income: bool
    compensation_of_officers: float
    has_employees: bool
    salaries_wages: Optional[float] = None
    taxes_licenses: Optional[float] = None
    repairs_maintenance: Optional[float] = None
    refund_or_tax_due: RefundOrTaxDue
    refund_amount: Optional[float] = None
    tax_due_amount: Optional[float] = None
    compensation_of_officers_in_cost_of_labor: Optional[float] = None
    account_number: str
    routing_number: str

    # 3. Owners Information
    owners: List[Owner] = Field(..., max_items=4)

    # 4. 1125-E Table (Officers Compensation)
    officers: Optional[List[Officer]] = Field(default=[], max_items=4)

    # 5. Preparer Information
    prepared_by: PreparedBy
    use_own_cpa: Optional[bool] = None
    cpa_info: Optional[CPAInfo] = None

    # 6. Future Tax Returns
    need_multiple_years: bool
    years_needed: Optional[int] = Field(None, ge=1)
    future_years: Optional[List[FutureYear]] = None
    future_years_percents_income: Optional[List[FutureYearPercents]] = None

    # Валидаторы
    @validator('date_inc')
    def validate_date_inc(cls, v, values):
        if 'filing_year' in values and v.year > values['filing_year']:
            raise ValueError("Incorporation year cannot be after filing year")
        return v

    @validator('owners')
    def validate_owners_percentage(cls, v):
        total = sum(owner.ownership_percentage for owner in v)
        if not (99.9 <= total <= 100.1):  # Учитываем погрешность float
            raise ValueError("Total ownership percentage must be exactly 100%")
        return v

    @validator('officers')
    def validate_officers_percentages(cls, v):
        if v:
            time_total = sum(officer.time_percentage for officer in v)
            comp_total = sum(officer.compensation_percentage for officer in v)
            total = sum(officer.ownership_percentage for officer in v)
            if not (99.9 <= time_total <= 100.1) or not (99.9 <= comp_total <= 100.1) or not (total <= 100.1):
                raise ValueError("Time and compensation percentages must each total 100%")
        return v

    @validator('products_percentage')
    def validate_products_percentage(cls, v, values):
        if values.get('sells_products_or_services') == SellsProductsOrServices.BOTH and v is None:
            raise ValueError("Products percentage is required when selling both products and services")
        return v

def create_info_next_year(tax_return_last_year: TaxReturnRequest, future_year_info: FutureYear):
    new_tax_return = copy.deepcopy(tax_return_last_year)
    new_tax_return.filing_year = future_year_info.year
    if not(future_year_info.gross_receipts_sales is None):
        new_tax_return.gross_receipts_sales = future_year_info.gross_receipts_sales
    new_tax_return.returns_allowances = future_year_info.returns_allowances
    new_tax_return.cost_of_goods_sold = future_year_info.cost_of_goods_sold
    new_tax_return.gross_rents = future_year_info.gross_rents
    new_tax_return.has_capital_gain_income = future_year_info.has_capital_gain_income
    new_tax_return.compensation_of_officers = future_year_info.compensation_of_officers
    new_tax_return.has_employees = future_year_info.has_employees
    new_tax_return.salaries_wages = future_year_info.salaries_wages
    new_tax_return.taxes_licenses = future_year_info.taxes_licenses
    new_tax_return.repairs_maintenance = future_year_info.repairs_maintenance
    new_tax_return.refund_or_tax_due = future_year_info.refund_or_tax_due
    new_tax_return.refund_amount = future_year_info.refund_amount
    new_tax_return.tax_due_amount = future_year_info.tax_due_amount
    new_tax_return.account_number = future_year_info.account_number
    new_tax_return.routing_number = future_year_info.routing_number
    new_tax_return.total_assets = future_year_info.total_assets
    return new_tax_return

def create_info_next_year_with_percents(tax_return_last_year: TaxReturnRequest, future_year_info: FutureYearPercents):
    new_tax_return = copy.deepcopy(tax_return_last_year)
    if future_year_info.how_income_change_this_year == "HIGHER":
        multiplier = future_year_info.percents_higher / 100
    else:
        multiplier = -future_year_info.percents_lower / 100
    new_tax_return.gross_receipts_sales += new_tax_return.gross_receipts_sales * multiplier
    new_tax_return.filing_year = future_year_info.year
    return new_tax_return