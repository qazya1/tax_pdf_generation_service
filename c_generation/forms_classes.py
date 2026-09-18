from pdf_filling import *
from fast_api_models import *
import pandas as pd
import random
from datetime import datetime, timedelta

transactions_df = pd.read_csv("configs/transactions.csv")

#функция для генерации дат
def get_random_day(year, min_date_day=None):
    if min_date_day:
        dt = datetime(year=year+1, day=min_date_day, month=4) + timedelta(days=random.randint(3,6))
        while dt.weekday() == 6:
            dt = datetime(year=year+1, day=min_date_day, month=4) + timedelta(days=random.randint(3,6))
    else:
        dt = datetime(year=year+1, day=random.randint(1,15), month=4)
        while dt.weekday() == 6:
            dt = datetime(year=year+1, day=random.randint(1,15), month=4)
    return dt
    #return dt.strftime("%m/%d/%Y")


#аналогичен классу Person
class Firm:
    def __init__(self):
        self.cost_of_goods_sold = None
        self.receipts_returns_balance = None
        self.inventory_end_year = None
        self.inventory_start_year = None
        self.officers_compensation = None
        self.short_term_capitals = None
        self.long_term_capitals = None
        self.gross_income = None
        self.total_income = None
        self.date = None
        self.k_info = None
        
        #это будет использоваться для связи последующих генераций
        self.balance_begin_year = None
        self.NOL = None
        self.assets_begin_year = None

class Form_1125A(Form):
    def __init__(self, req_body, firm):
        super().__init__("f1125a")
        if not(req_body.returns_allowances is None):
            firm.receipts_returns_balance = req_body.gross_receipts_sales - req_body.returns_allowances
        else:
            firm.receipts_returns_balance = req_body.gross_receipts_sales
        if not(req_body.cost_of_goods_sold is None):
            firm.cost_of_goods_sold = req_body.cost_of_goods_sold
        else:
            firm.cost_of_goods_sold = firm.receipts_returns_balance*random.uniform(0.4,0.55)
        self.rows["8"] = firm.cost_of_goods_sold
        if firm.inventory_end_year is None:
            self.rows["1"] = self.rows["8"]*random.uniform(0.9,0.95)
        else:
            self.rows["1"] = firm.inventory_end_year
        self.rows["2"] = (self.rows["8"] - self.rows["1"]) * random.uniform(0.55,0.7)
        self.rows["3"] = (self.rows["8"] - self.rows["1"]) * random.uniform(0.45,0.75)
        self.rows["4"] = 0
        self.rows["5"] = 0
        self.rows["6"] = sum([self.rows[str(i)] for i in range(1,6)])
        self.rows["7"] = self.rows["6"] - self.rows["8"]
        firm.inventory_start_year = self.rows["1"]
        firm.inventory_end_year = self.rows["7"]
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

class Form_1120(Form):
    #form1120 + schedules C, J, K, L, M-1, M-2
    def __init__(self, req_body, firm):
        super().__init__("f1120")
        
        #form1120 main
        self.rows["1a"] = req_body.gross_receipts_sales
        if not(req_body.returns_allowances is None):
            self.rows["1b"] = req_body.returns_allowances
        else:
            self.rows["1b"] = 0
        self.rows["1c"] = self.rows["1a"] - self.rows["1b"]
        if req_body.sells_products_or_services == "Services":
            self.rows["2"] = 0
        else:
            if firm.cost_of_goods_sold:
                self.rows["2"] = firm.cost_of_goods_sold
            else:
                self.rows["2"] = req_body.products_percentage/100 * req_body.gross_receipts_sales
        # elif req_body.sells_products_or_services == "Both":
            # self.rows["2"] = req_body.products_percentage/100 * req_body.gross_receipts_sales
        # else:
            # self.rows["2"] = firm.cost_of_goods_sold
        self.rows["3"] = self.rows["1c"] - self.rows["2"]
        firm.gross_income = self.rows["3"]
        self.rows["4"] = self.rows["3"]*random.uniform(0.05,0.1)
        self.rows["5"] = 0
        if not(req_body.gross_rents is None):
            self.rows["6"] = req_body.gross_rents
        else:
            self.rows["6"] = 0
        self.rows["7"] = 0
        self.rows["8"] = firm.short_term_capitals
        self.rows["9"] = 0
        self.rows["10"] = 0
        self.rows["11"] = sum([self.rows[i] for i in ("3", "4", "5", "6", "7", "8", "9", "10")])
        firm.total_income = self.rows["11"]
        
        self.rows["12"] = min(req_body.compensation_of_officers, 0.5*self.rows["11"])
        firm.officers_compensation = self.rows["12"]
        if req_body.has_employees:
            if not(req_body.salaries_wages is None):
                self.rows["13"] = req_body.salaries_wages   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["11"]*0.205
            else:
                self.rows["13"] = self.rows["11"]*random.uniform(0.15,0.2)
        else:
            self.rows["13"] = 0
        if not(req_body.repairs_maintenance is None):
            self.rows["14"] = req_body.repairs_maintenance
        else:
            self.rows["14"] = 0
        self.rows["15"] = self.rows["11"]*random.uniform(0.02,0.03)
        if not(req_body.gross_rents is None):
            self.rows["16"] = req_body.gross_rents   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["11"]*0.045
        else:
            self.rows["16"] = 0
        if not(req_body.taxes_licenses is None):
            self.rows["17"] = req_body.taxes_licenses   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["11"]*0.065
        else:
            self.rows["17"] = 0
        self.rows["18"] = 0
        self.rows["19"] = 0
        self.rows["20"] = 0
        self.rows["21"] = 0
        self.rows["22"] = self.rows["11"]*random.uniform(0.08,0.12)
        if req_body.has_employees:
            self.rows["23"] = self.rows["11"]*random.uniform(0.01,0.02)
        else:
            self.rows["23"] = 0
        if req_body.has_employees:
            self.rows["24"] = self.rows["11"]*random.uniform(0.005,0.01)
        else:
            self.rows["24"] = 0
        self.rows["25"] = 0
        self.rows["26"] = 0
        self.rows["27"] = sum([self.rows[str(i)] for i in range(12,27)])
        
        self.rows["28"] = self.rows["11"] - self.rows["27"]
        if firm.NOL is None:
            self.rows["29a"] = 0
        else:
            self.rows["29a"] = firm.NOL
        
        #schedule c
        self.rows["c:23"] = self.rows["4"]
        self.rows["c:1a"] = self.rows["c:23"]*random.uniform(0.15,0.2)
        self.rows["c:1b"] = 0.5*self.rows["c:1a"]
        self.rows["c:4a"] = self.rows["c:23"]*random.uniform(0.5,0.6)
        self.rows["c:4b"] = 0.233*self.rows["c:4a"]
        self.rows["c:6a"] = self.rows["c:23"] - (self.rows["c:1a"] + self.rows["c:4a"])
        self.rows["c:6b"] = 0.5*self.rows["c:6a"]
        self.rows["c:8a"] = self.rows["c:1a"] + self.rows["c:4a"] + self.rows["c:6a"]
        self.rows["c:8b"] = self.rows["c:1b"] + self.rows["c:4b"] + self.rows["c:6b"]
        self.rows["c:24"] = self.rows["c:8b"]
        
        #return to form1120 main
        self.rows["29b"] = self.rows["c:24"]
        self.rows["30"] = self.rows["28"] - (self.rows["29a"] + self.rows["29b"])
        if self.rows["30"] < 0:
            for i,p in {"13":0.205, "16":0.045, "17":0.065}.items():
                self.rows[i] = self.rows["11"]*p
                self.rows["27"] = sum([self.rows[str(i)] for i in range(12,27)])
                self.rows["28"] = self.rows["11"] - self.rows["27"]
                self.rows["30"] = self.rows["28"] - (self.rows["29a"] + self.rows["29b"])
                if self.rows["30"] > 0:
                    break
        if self.rows["30"] < 0:
            firm.NOL = -self.rows["30"]
            self.rows["30"] = 0
        
        self.rows["31"] = self.rows["30"]*0.21
        self.rows["32"] = 0
        if req_body.refund_or_tax_due == "TAX_REFUND":
            self.rows["33"] = self.rows["31"] + req_body.refund_amount
        else:
            self.rows["33"] = self.rows["31"] - req_body.tax_due_amount
            if self.rows["33"] < 0:
                need = -self.rows["33"] * 10
                self.rows["33"] = 0
                self.rows["4"] += need
                #schedule c
                self.rows["c:23"] = self.rows["4"]
                self.rows["c:1a"] = self.rows["c:23"]*random.uniform(0.15,0.2)
                self.rows["c:1b"] = 0.5*self.rows["c:1a"]
                self.rows["c:4a"] = self.rows["c:23"]*random.uniform(0.5,0.6)
                self.rows["c:4b"] = 0.233*self.rows["c:4a"]
                self.rows["c:6a"] = self.rows["c:23"] - (self.rows["c:1a"] + self.rows["c:4a"])
                self.rows["c:6b"] = 0.5*self.rows["c:6a"]
                self.rows["c:8a"] = self.rows["c:1a"] + self.rows["c:4a"] + self.rows["c:6a"]
                self.rows["c:8b"] = self.rows["c:1b"] + self.rows["c:4b"] + self.rows["c:6b"]
                self.rows["c:24"] = self.rows["c:8b"]
                
                self.rows["11"] = sum([self.rows[i] for i in ("3", "4", "5", "6", "7", "8", "9", "10")])
                self.rows["28"] = self.rows["11"] - self.rows["27"]
                self.rows["29b"] = self.rows["c:24"]
                self.rows["30"] = self.rows["28"] - (self.rows["29a"] + self.rows["29b"])
                self.rows["31"] = self.rows["30"]*0.21
                self.rows["33"] = self.rows["31"] - req_body.tax_due_amount
        
        self.rows["34"] = 0
        if req_body.refund_or_tax_due == "TAX_DUE":
            self.rows["35"] = req_body.tax_due_amount
            self.rows["36"] = 0
        else:
            self.rows["35"] = 0
            self.rows["36"] = req_body.refund_amount
        self.rows["38"] = self.rows["36"]
        self.rows["37"] = 0
        
        #schedule j
        self.rows["j:1a"] = self.rows["31"]
        self.rows["j:2"] = self.rows["j:1a"]
        self.rows["j:12"] = self.rows["j:1a"]
        self.rows["j:23"] = self.rows["33"]
        self.rows["j:14"] = self.rows["j:23"]
        self.rows["j:19"] = self.rows["j:14"]
        
        #schedule k
        self.rows["k:Accrual"] = True
        self.rows["k:2a"] = req_body.business_activity_code
        self.rows["k:2b"] = req_body.business_activity
        self.rows["k:2c"] = req_body.principal_product_service
        self.rows["k:3_No"] = True
        self.rows["k:4a_No"] = True
        for officer in req_body.officers:
            if officer.ownership_percentage > 20:
                self.rows["k:4b_Yes"] = True
                break
        else:
            self.rows["k:4b_No"] = True
        self.rows["k:5a_No"] = True
        self.rows["k:5b_No"] = True
        self.rows["k:6_No"] = True
        self.rows["k:7_No"] = True
        self.rows["k:8_No"] = True
        self.rows["k:10"] = str(len(req_body.officers))
        if req_body.total_assets is None:
            total_assets = min(350000, self.rows["11"]*0.3)
        else:
            total_assets = req_body.total_assets
        if total_assets > 250000 and self.rows["1a"] + sum([self.rows[str(i)] for i in range(4,11)]) > 250000:
            self.rows["k:13_Yes"] = True
            self.rows["k:13"] = (self.rows["30"] - self.rows["33"]) * random.uniform(0.5, 0.6)
        else:
            self.rows["k:13_No"] = True
        self.rows["k:14_No"] = True
        self.rows["k:15a_Yes"] = True
        self.rows["k:15b_Yes"] = True
        for i in range(16, 27):
            self.rows[f"k:{i}_No"] = True
        self.rows["k:27_Yes"] = True
        self.rows["k:28_No"] = True
        for i in "abc":
            self.rows[f"k:29{i}_No"] = True
            self.rows[f"k:30{i}_No"] = True
        self.rows["k:31_No"] = True
        
        if total_assets > 250000 or self.rows["1a"] + sum([self.rows[str(i)] for i in range(4,11)]) > 250000:
            # schedule m-1
            self.rows["m1:10"] = self.rows["28"]
            self.rows["m1:6"] = self.rows["m1:10"]
            self.rows["m1:1"] = self.rows["30"] - self.rows["31"]
            self.rows["m1:2"] = self.rows["m1:10"] - self.rows["m1:1"]
            
            # schedule m-2
            if firm.balance_begin_year is None:
                self.rows["m2:1"] = self.rows["m1:1"] * random.uniform(0.4, 0.45)
            else:
                # Исправление: корректный перенос баланса
                self.rows["m2:1"] = firm.balance_begin_year
            
            self.rows["m2:2"] = self.rows["m1:1"]
            self.rows["m2:4"] = self.rows["m2:1"] + self.rows["m2:2"]
            self.rows["m2:5a"] = min(self.rows["m2:2"] * random.uniform(0.5, 0.55), self.rows["m2:4"])
            self.rows["m2:7"] = self.rows["m2:5a"]
            self.rows["m2:8"] = self.rows["m2:4"] - self.rows["m2:7"]
            
            if self.rows["m2:8"] > min(250000, total_assets*0.65):
                self.rows["m2:5a"] += self.rows["m2:8"] - min(250000, total_assets*0.65)
                self.rows["m2:5a"] = min(self.rows["m2:5a"], self.rows["m2:4"])
                self.rows["m2:7"] = self.rows["m2:5a"]
                self.rows["m2:8"] = self.rows["m2:4"] - self.rows["m2:7"]
            
            firm.balance_begin_year = self.rows["m2:8"]
            
            # schedule L - ИСПРАВЛЕНИЕ БАЛАНСА
            if req_body.sells_products_or_services == "Products":
                self.rows["l:3b"] = firm.inventory_start_year
                self.rows["l:3d"] = firm.inventory_end_year
            else:
                self.rows["l:3b"] = 0
                self.rows["l:3d"] = 0
            
            self.rows["l:25b"] = self.rows["m2:1"]
            self.rows["l:25d"] = self.rows["m2:8"]
            self.rows["l:15d"] = total_assets
            
            # Исправление: обеспечение баланса активов и пассивов
            if firm.assets_begin_year is None:
                # Начальные активы = начальные пассивы + капитал
                total_liabilities_equity_begin = self.rows["l:25b"] + random.uniform(0.1, 0.2) * total_assets
                self.rows["l:15b"] = total_liabilities_equity_begin
                
                # Пропорциональное распределение активов
                self.rows["l:1b"] = total_liabilities_equity_begin * random.uniform(0.6, 0.7)
                self.rows["l:4b"] = total_liabilities_equity_begin * random.uniform(0.05, 0.1)
                self.rows["l:8b"] = total_liabilities_equity_begin * random.uniform(0.05, 0.1)
                self.rows["l:3b"] = total_liabilities_equity_begin - (self.rows["l:1b"] + self.rows["l:4b"] + self.rows["l:8b"])
                
            else:
                # Корректный перенос из предыдущего года
                self.rows["l:15b"] = firm.assets_begin_year["l:15d"]
                self.rows["l:1b"] = firm.assets_begin_year["l:1d"]
                self.rows["l:4b"] = firm.assets_begin_year["l:4d"]
                self.rows["l:8b"] = firm.assets_begin_year["l:8d"]
                self.rows["l:3b"] = firm.assets_begin_year["l:3d"]
            
            # Расчет конечных значений с обеспечением баланса
            total_liabilities_equity_end = self.rows["l:25d"] + random.uniform(0.1, 0.2) * total_assets
            self.rows["l:15d"] = total_liabilities_equity_end
            
            # Пропорциональное распределение активов на конец года
            if firm.assets_begin_year is None:
                self.rows["l:1d"] = self.rows["l:1b"] + self.rows["m1:1"] - self.rows["m2:5a"]
                self.rows["l:8d"] = self.rows["l:15d"] - (self.rows["l:4d"] + self.rows["l:3d"] + self.rows["l:1d"])
            else:
                asset_growth_ratio = total_liabilities_equity_end / self.rows["l:15b"]
                self.rows["l:1d"] = self.rows["l:1b"] * asset_growth_ratio
                self.rows["l:4d"] = self.rows["l:4b"] * asset_growth_ratio
                self.rows["l:8d"] = self.rows["l:8b"] * asset_growth_ratio
                self.rows["l:3d"] = self.rows["l:3b"] * asset_growth_ratio
            
            # Финальная проверка и корректировка баланса
            total_assets_calc = self.rows["l:1d"] + self.rows["l:4d"] + self.rows["l:8d"] + self.rows["l:3d"]
            if abs(total_assets_calc - total_liabilities_equity_end) > 1:
                # Равномерно распределяем разницу
                diff_per_asset = (total_liabilities_equity_end - total_assets_calc) / 4
                self.rows["l:1d"] += diff_per_asset
                self.rows["l:4d"] += diff_per_asset
                self.rows["l:8d"] += diff_per_asset
                self.rows["l:3d"] += diff_per_asset
            
            # Сохраняем для переноса на следующий год
            firm.assets_begin_year = {
                "l:15d": self.rows["l:15d"],
                "l:1d": self.rows["l:1d"],
                "l:4d": self.rows["l:4d"],
                "l:8d": self.rows["l:8d"],
                "l:3d": self.rows["l:3d"]
            }
            
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein
        self.rows["address"] = req_body.company_street_address
        self.rows["date_inc"] = req_body.date_inc
        if req_body.filing_year < 2025:
            self.rows["town_state_zip"] = req_body.company_town + ", " + req_body.company_state + ", " + req_body.company_zip
        else:
            self.rows["town"] = req_body.company_town
            self.rows["state"] = req_body.company_state
            self.rows["country"] = "United States"
            self.rows["zip"] = req_body.company_zip
        self.rows["total_assets"] = total_assets
        self.rows["CEO_Signature"] = req_body.ceo_signature
        self.rows["Date_Obj"] = get_random_day(req_body.filing_year)
        self.rows["Date"] = self.rows["Date_Obj"].strftime("%m/%d/%Y")
        firm.date = self.rows["Date"]
        self.rows["Title"] = req_body.ceo_position
        if req_body.use_own_cpa:
            self.rows["preparer_Signature"] = req_body.cpa_info.preparer_signature
            self.rows["preparer_Date"] = self.rows["Date"]
            self.rows["preparer_Name"] = req_body.cpa_info.preparer_name
            self.rows["firm_Name"] = req_body.cpa_info.firm_name
            self.rows["preparer_Address"] = req_body.cpa_info.firm_address
            self.rows["preparer_EIN"] = req_body.cpa_info.firm_ein
            self.rows["preparer_PTIN"] = req_body.cpa_info.ptin
            self.rows["preparer_Phone"] = req_body.cpa_info.firm_phone
            
    def insert_need_images(self):
        if "CEO_Signature" in self.rows and len(self.rows["CEO_Signature"]) > 0:
            self.insert_image(0, (102.2,672.5, 124.4,683.8), decode_image(self.rows["CEO_Signature"]))
        self.insert_image(0, (276.5,672.8, 312.5,683.6), text_to_img(self.rows["Date"]))
        if "preparer_Signature" in self.rows and len(self.rows["preparer_Signature"]) > 0:
            self.insert_image(0, (275.6,704.9, 297.8,716.2), decode_image(self.rows["preparer_Signature"]))
        if "preparer_Date" in self.rows:
            self.insert_image(0, (415.8,709, 451.8,719.8), text_to_img(self.rows["preparer_Date"]))

class Form_1125E(Form):
    def __init__(self, req_body, firm):
        super().__init__("f1125e")
        sort_officers = sorted(req_body.officers, key=lambda x: x.compensation_percentage)[:4]
        for i, officer in enumerate(sort_officers):
            self.rows[f"name_{i}"] = officer.name
            self.rows[f"ssn_{i}"] = officer.ssn
            self.rows[f"time_percentage_{i}"] = officer.time_percentage
            self.rows[f"ownership_percentage_{i}"] = officer.ownership_percentage
            self.rows[f"compensation_{i}"] = officer.compensation_percentage / 100 * req_body.compensation_of_officers
        self.rows["2"] = req_body.compensation_of_officers
        self.rows["3"] = 0
        self.rows["4"] = firm.officers_compensation
            
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

class ScheduleG(Form):
    def __init__(self, req_body, firm):
        super().__init__("f1120sg")
        
        sort_owners = sorted(req_body.owners, key=lambda x: x.ownership_percentage)
        for i, owner in enumerate(sort_owners):
            if owner.ownership_percentage < 20:
                break
            self.rows[f"name_{i}"] = owner.name
            self.rows[f"id_{i}"] = owner.ssn
            self.rows[f"country_{i}"] = "United States"
            self.rows[f"percentage_owned_{i}"] = owner.ownership_percentage
        
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

#filled before 1120
class Form8949(Form):
    def __init__(self, req_body, firm):
        super().__init__("f8949")
        
        self.rows["C"] = True
        #self.rows["2h"] = firm.short_term_capitals
        transactions_df_this_year = transactions_df.loc[transactions_df["year"]==req_body.filing_year]
        #start of the math of 1120
        self.rows["1a"] = req_body.gross_receipts_sales
        if not(req_body.returns_allowances is None):
            self.rows["1b"] = req_body.returns_allowances
        else:
            self.rows["1b"] = 0
        self.rows["1c"] = self.rows["1a"] - self.rows["1b"]
        if req_body.sells_products_or_services == "Services":
            self.rows["2"] = 0
        elif req_body.sells_products_or_services == "Both":
            self.rows["2"] = req_body.products_percentage/100 * req_body.gross_receipts_sales
        else:
            self.rows["2"] = firm.cost_of_goods_sold
        self.rows["3"] = self.rows["1c"] - self.rows["2"]
        self.rows["8"] = self.rows["3"]*random.uniform(0.10,0.15)
        start_num = self.rows["8"]
        for i in ("1a", "1b", "1c", "2", "3", "8"):
            self.rows.pop(i)
        
        need_sum = start_num * 0.3
        sum_ = 0
        sum_d = 0
        sum_e = 0
        n = random.randint(3,4)
        was = set()
        for i in range(n):
            if i == n-1:
                need_sum = start_num - sum_
            x = random.choice(transactions_df_this_year.index)
            ser = transactions_df_this_year.loc[x]
            was.add(x)
            profit = ser["sell_price"] - ser["buy_price"]
            need_num = need_sum//profit
            if i < n-1:
                need_num += 1
            self.rows[f"{i}_a"] = f"{int(need_num)} sh. {ser['symbol']} Co."
            self.rows[f"{i}_b"] = ser["buy_date"]
            self.rows[f"{i}_c"] = ser["sell_date"]
            self.rows[f"{i}_d"] = ser["sell_price"] * need_num
            self.rows[f"{i}_e"] = ser["buy_price"] * need_num
            self.rows[f"{i}_f"] = random.choice("BCEGL")
            self.rows[f"{i}_h"] = self.rows[f"{i}_d"] - self.rows[f"{i}_e"]
            sum_d += self.rows[f"{i}_d"]
            sum_e += self.rows[f"{i}_e"]
            sum_ += self.rows[f"{i}_h"]
        self.rows["2e"] = sum_e
        self.rows["2d"] = sum_d
        self.rows["2h"] = sum_
        firm.short_term_capitals = sum_
        
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

class ScheduleD(Form):
    def __init__(self, req_body, firm):
        super().__init__("f1120sd")
        
        #self.rows["18"] = firm.short_term_capitals
        self.rows["7"] = firm.short_term_capitals
        self.rows["3g"] = firm.short_term_capitals
        self.rows["3h"] = firm.short_term_capitals
        
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

class ScheduleD_S(Form):
    def __init__(self, req_body, firm):
        super().__init__("f1120ssd")
        
        #self.rows["18"] = firm.short_term_capitals
        self.rows["7"] = firm.short_term_capitals
        self.rows["3g"] = firm.short_term_capitals
        self.rows["3h"] = firm.short_term_capitals
        
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein

class FirmAuthorization(Form):
    def __init__(self, req_body, firm):
        super().__init__("f8879c")
        
        #вставляем личные данные
        self.rows["Corporation_name"] = req_body.company_name
        self.rows["EIN"] = req_body.ein
        if req_body.filing_year >=2022:
            self.rows["Tax_Year"] = str(req_body.filing_year)[2:]
        if req_body.filing_year >=2022:
            if req_body.company_type == "C corp":
                self.rows["1"] = firm.total_income
            else:
                self.rows["3"] = firm.total_income
        else:
            self.rows["1"] = firm.total_income
            self.rows["4"] = req_body.tax_due_amount
            self.rows["5"] = req_body.refund_amount
            
        self.rows["PIN"] = str(random.randint(10**4,10**5-1))
        self.rows["EROs_PIN"] = str(random.randint(10**19,10**20-1))[:6]+str(random.randint(10**4,10**5-1))
        self.rows["Signature_Date"] = firm.date
        self.rows["PIN_as_my_signature"] = True
        self.rows["Title"] = req_body.ceo_position
        
    def insert_need_images(self):
        self.insert_image(0, (343.3,471.3, 385.2,479.5), text_to_img(self.rows["Signature_Date"]))

#forms 1040 for personal tax returning
#изменено с учётом входных данных и объекта вместо json
standart_deduction_df = pd.read_csv("configs/Standard_Deduction_Config.csv")
tax_brackets_df = pd.read_csv("configs/federal_tax_brackets.csv")
tax_brackets_df = tax_brackets_df.fillna(-1)
companies_df = pd.read_csv("configs/companies_dividents.csv")

#функция для вычисления общего налога
def get_tax(year, married, income):
    global tax_brackets_df
    df = tax_brackets_df.loc[(tax_brackets_df["Year"]==year) & (tax_brackets_df["FilingStatus"]==married)]
    tax = 0
    for i in df.index:
        ser = df.loc[i]
        if ser["BracketLower"] < income:
            if ser["BracketUpper"] == -1:
                tax += (income-ser["BracketLower"])*ser["RatePercent"]*0.01
            else:
                tax += (min(ser["BracketUpper"], income)-ser["BracketLower"])*ser["RatePercent"]*0.01
        else:
            break
    return round(tax, 2)

#в этом классе помещаем логику выбора форм и наиболее часто использующиеся данные
class Person:
    def __init__(self):
        self.total_income = None
        self.additional_income = None
        self.adjustments = None
        self.qualified_dividents = None
        self.date = None
        self.total_tax = None
        self.federal_tax_withheld = None
        self.refund_amount = None
        self.owe_amount = None
        self.date = None

#классы форм

class Form_1040(Form):
    def __init__(self, owner_info, req_body, person, firm, year, officer):
        super().__init__("1040")
        
        #числовое ядро
        #person.total_income = owner_info.ownership_percentage / 100 * firm.gross_income
        #self.rows["9"] = person.total_income
        #self.rows["1a"] = random.uniform(0.75, 0.8) * person.total_income
        self.rows["1a"] = owner_info.ownership_percentage / 100 * firm.gross_income
        #self.rows["3b"] = random.uniform(0.03, 0.05) * person.total_income
        self.rows["3b"] = officer.compensation_percentage / 100 * req_body.compensation_of_officers
        self.rows["9"] = self.rows["3b"] + self.rows["1a"]
        person.total_income = self.rows["9"]
        self.rows["10"] = random.uniform(0.03, 0.06) * person.total_income
        self.rows["11"] = person.total_income - self.rows["10"]
        deduction = standart_deduction_df.loc[(standart_deduction_df["Year"]==year) & (standart_deduction_df["FilingStatus"]==owner_info.marital_status)]["StandardDeduction"].iloc[0]
        self.rows["12"] = min(self.rows["11"], deduction)
        self.rows["13"] = 0    #для дальнейшего использования
        self.rows["14"] = self.rows["12"]+self.rows["13"]
        self.rows["15"] = self.rows["11"] - self.rows["14"]
        self.rows["16"] = get_tax(year, owner_info.marital_status, self.rows["15"])
        self.rows["17"] = 0
        self.rows["18"] = self.rows["16"]+self.rows["17"]
        self.rows["21"] = 0    #для дальнейшего использования
        self.rows["22"] = self.rows["18"] - self.rows["21"]
        self.rows["23"] = 0    #налог для самозанятых не выплачивается
        self.rows["24"] = self.rows["22"]+self.rows["23"]
        if owner_info.personal_refund_or_tax_due == "TAX_REFUND":
            self.rows["35a"] = owner_info.personal_refund_amount
            self.rows["37"] = 0
            person.refund_amount = self.rows["35a"]
            self.rows["25a"] = self.rows["35a"]+self.rows["24"]
            self.rows["25b"] = 0
            self.rows["25c"] = 0
            self.rows["25d"] = self.rows["25a"]+self.rows["25b"]+self.rows["25c"]
            self.rows["26"] = 0
            self.rows["32"] = 0
            self.rows["33"] = self.rows["32"]+self.rows["26"]+self.rows["25d"]
            self.rows["34"] = self.rows["35a"]
            self.rows["35b"] = owner_info.personal_routing_number
            self.rows["35d"] = owner_info.personal_account_number
        else:
            self.rows["34"] = 0
            self.rows["37"] = owner_info.personal_tax_due_amount
            person.owe_amount = self.rows["37"]
            self.rows["25a"] = self.rows["24"] - self.rows["37"]
            self.rows["25b"] = 0
            self.rows["25c"] = 0
            self.rows["25d"] = self.rows["25a"]+self.rows["25b"]+self.rows["25c"]
            self.rows["26"] = 0
            self.rows["32"] = 0
            self.rows["33"] = self.rows["32"]+self.rows["26"]+self.rows["25d"]
        
        #очищаем ненужные поля
        need_rows = ["1a", "1c", "1z", "3b", "8", "9", "10", "11", "12", "14", "15", "16", "17", "18", "22", "24"]
        if owner_info.personal_refund_or_tax_due == "TAX_REFUND":
            need_rows += ["25a", "25d", "33", "34", "35a", "35b", "35d"]
        else:
            need_rows += ["25a", "25d", "33", "37"]
        no_need_rows = list(set(self.rows) - set(need_rows))
        for row in no_need_rows:
            if row in self.rows:
                self.rows.pop(row)
        
        #вставляем личные данные
        if owner_info.marital_status == "MarriedFilingJointly":
            self.rows["Married_filing_jointly"] = True
        else:
            self.rows["Single"] = True
        self.rows["Your_first_name_and_middle_initial"], self.rows["Last_name"] = owner_info.name.split()
        
        self.rows["Your_social_security_number"] = owner_info.ssn
        self.rows["Your_occupation"] = owner_info.position
        self.rows["Your_Signature"] = owner_info.signature
        self.rows["Date"] = get_random_day(year).strftime("%m/%d/%Y")
        if owner_info.dependents:
            for n,dependent in enumerate(owner_info.dependents):
                self.rows[f"Dependent_{n}_name"] = dependent.name
                self.rows[f"Dependent_{n}_SSN"] = dependent.ssn
                self.rows[f"Dependent_{n}_relation"] = dependent.relationship
        self.rows["35c_checking"] = True
        self.rows["Digital_Assets_No"] = True
        
        #поля для фирмы по подготовке налогов
        if req_body.use_own_cpa:
            self.rows["preparer_Name"] = req_body.cpa_info.preparer_name
            self.rows["preparer_PTIN"] = req_body.cpa_info.ptin
            self.rows["preparer_Phone"] = req_body.cpa_info.firm_phone
            self.rows["preparer_Firm_Name"] = req_body.cpa_info.firm_name
            self.rows["preparer_Firm_Address"] = req_body.cpa_info.firm_address
            self.rows["preparer_Firm_EIN"] = req_body.cpa_info.firm_ein
            self.rows["preparer_Signature"] = req_body.cpa_info.preparer_signature
            self.rows["preparer_Date"] = self.rows["Date"]
        
        #запоминаем общие значения
        person.additional_income = 0
        person.adjustments = self.rows["10"]
        person.qualified_dividents = self.rows["3b"]
        person.total_tax = self.rows["24"]
        person.federal_tax_withheld = self.rows["25d"]
        person.date = self.rows["Date"]
    
    def insert_need_images(self):
        #вставляем подписи
        if "Your_Signature" in self.rows and len(self.rows["Your_Signature"]) > 0:
            self.insert_image(1, (110,465, 137,497), decode_image(self.rows["Your_Signature"]))
        #вставляем даты
        self.insert_image(1, (275,476, 323,491), text_to_img(self.rows["Date"]))
        if "preparer_Signature" in self.rows and len(self.rows["preparer_Signature"]) > 0:
            self.insert_image(1, (224,543, 380,558), decode_image(self.rows["preparer_Signature"]))
        if "preparer_Date" in self.rows:
            self.insert_image(1, (392,544, 440,559), text_to_img(self.rows["preparer_Date"]))

class Schedule1(Form):
    def __init__(self, owner_info, person):
        super().__init__("Schedule1")
        
        #числовое ядро
        self.rows["10"] = person.additional_income
        self.rows["26"] = person.adjustments
        if self.rows["26"] < 7000:
            self.rows["20"] = self.rows["26"]
        else:
            self.rows["20"] = 7000
            self.rows["22"] = self.rows["26"] - 7000
        self.rows["8b"] = round(person.additional_income*random.uniform(0.3,0.4), 2)
        self.rows["8i"] = round(person.additional_income*random.uniform(0.3,0.4), 2)
        self.rows["8k"] = self.rows["10"] - (self.rows["8b"] + self.rows["8i"])
        self.rows["9"] = self.rows["10"]
        need_rows = ["8b", "8i", "8k", "9", "10", "20", "26"]
        
        #очищаем ненужные поля
        no_need_rows = list(set(self.rows) - set(need_rows))
        for row in no_need_rows:
            if row in self.rows:
                self.rows.pop(row)
        
        #вставляем личные данные
        self.rows["Name(s)_shown"] = owner_info.name
        self.rows["Your_social_security_number"] = owner_info.ssn

class ScheduleB(Form):
    def __init__(self, owner_info, person):
        super().__init__("ScheduleB")
        
        #числовое ядро
        self.rows["6"] = person.qualified_dividents
        if person.qualified_dividents >= 1500:
            self.rows["7a_NO"] = True
            self.rows["7b_NO"] = True
            self.rows["8_NO"] = True
        
        #вставляем личные данные
        self.rows["Name(s)_shown"] = owner_info.name
        self.rows["Your_social_security_number"] = owner_info.ssn
        companies = [random.choice(companies_df["Full Legal Name"]) for i in range(random.randint(3,6))]
        average = person.qualified_dividents/len(companies)
        companies_values = [round(average*(1+random.uniform(-0.05,0.05)), 2) for i in range(len(companies)-1)]
        companies_values.append(person.qualified_dividents-sum(companies_values))
        for n, company in enumerate(companies):
            self.rows[f"List_of_companies_row{n+1}"] = company
        for n, value in enumerate(companies_values):
            self.rows[f"Amount_companies_row{n+1}"] = value

class Authorization(Form):
    def __init__(self, year, owner_info, person):
        super().__init__("Authorization")
        
        #вставляем личные данные
        self.rows["Taxpayer(s)_name"] = owner_info.name
        self.rows["Social_security_number"] = owner_info.ssn
        self.rows["Tax_Year_Ending"] = str(year)
        self.rows["SID"] = str(random.randint(10**19,10**20-1))
        self.rows["PIN"] = str(random.randint(10**4,10**5-1))
        self.rows["EROs_PIN"] = self.rows["SID"][:6]+str(random.randint(10**4,10**5-1))
        self.rows["Signature_Date"] = person.date
        self.rows["PIN_as_my_signature"] = True
        self.rows["Adjusted_gross_income"] = person.total_income-person.adjustments
        self.rows["Total_tax"] = person.total_tax
        self.rows["Federal_income_tax"] = person.federal_tax_withheld
        if person.refund_amount:
            self.rows["Amount_to_be_refunded"] = person.refund_amount
        if person.owe_amount:
            self.rows["Amount_to_be_owed"] = person.owe_amount
    
    def insert_need_images(self):
        #вставляем даты
        self.insert_image(0, (450,475, 542,492), text_to_img(self.rows["Signature_Date"]))

class Form_1120S(Form):
    #form1120 + schedules C, J, K, L, M-1, M-2
    def __init__(self, req_body, firm):
        super().__init__("f1120s")
        
        #form1120 main
        self.year = req_body.filing_year
        self.rows["1a"] = req_body.gross_receipts_sales
        if not(req_body.returns_allowances is None):
            self.rows["1b"] = req_body.returns_allowances
        else:
            self.rows["1b"] = random.uniform(0.05, 0.1) * self.rows["1a"]
        self.rows["1c"] = self.rows["1a"] - self.rows["1b"]
        if req_body.sells_products_or_services == "Services":
            self.rows["2"] = 0
        else:
            if req_body.sells_products_or_services == "Products":
                if not(firm.cost_of_goods_sold is None):
                    self.rows["2"] = firm.cost_of_goods_sold
                else:
                    self.rows["2"] = random.uniform(0.4, 0.55) * self.rows["1c"]
            else:
                self.rows["2"] = req_body.products_percentage/100 * req_body.gross_receipts_sales
        self.rows["3"] = self.rows["1c"] - self.rows["2"]
        firm.gross_income = self.rows["3"]
        self.rows["4"] = 0
        self.rows["5"] = 0
        self.rows["6"] = self.rows["3"] + self.rows["4"] + self.rows["5"]
        firm.total_income = self.rows["6"]
        
        self.rows["7"] = min(req_body.compensation_of_officers, 0.5*self.rows["6"])
        firm.officers_compensation = self.rows["7"]
        if req_body.has_employees:
            if not(req_body.salaries_wages is None):
                self.rows["8"] = req_body.salaries_wages   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["6"]*0.205
            else:
                self.rows["8"] = self.rows["6"]*random.uniform(0.15,0.2)
        else:
            self.rows["8"] = 0
        if not(req_body.repairs_maintenance is None):
            self.rows["9"] = req_body.repairs_maintenance
        else:
            self.rows["9"] = 0
        self.rows["10"] = self.rows["6"]*random.uniform(0.02,0.03)
        if not(req_body.gross_rents is None):
            self.rows["11"] = max(req_body.gross_rents, self.rows["6"]*random.uniform(0.04,0.05))   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["6"]*0.045
        else:
            self.rows["11"] = 0
        if not(req_body.taxes_licenses is None):
            self.rows["12"] = max(req_body.taxes_licenses, self.rows["6"]*random.uniform(0.055,0.06))   #если в итоге налогооблагаемая прибыль будет отрицательной, посчитаем как self.rows["6"]*0.065
        else:
            self.rows["12"] = 0
        self.rows["13"] = 0
        self.rows["14"] = 0
        self.rows["15"] = 0
        self.rows["16"] = self.rows["6"]*random.uniform(0.08,0.12)
        if req_body.has_employees:
            self.rows["17"] = self.rows["6"]*random.uniform(0.01,0.02)
        else:
            self.rows["17"] = 0
        if req_body.has_employees:
            self.rows["18"] = self.rows["6"]*random.uniform(0.005,0.01)
        else:
            self.rows["18"] = 0
        self.rows["19"] = 0
        self.rows["20"] = 0
        self.rows["21"] = sum([self.rows[str(i)] for i in range(7,21)])
        
        self.rows["22"] = self.rows["6"] - self.rows["21"]
        
        self.rows["25"] = 0
        self.rows["24b"] = 0
        self.rows["24c"] = 0
        self.rows["24d"] = 0
        self.rows["23b"] = 0
        if req_body.refund_or_tax_due == "TAX_DUE":
            self.rows["26"] = req_body.tax_due_amount
            self.rows["23a"] = req_body.tax_due_amount
            self.rows["23c"] = req_body.tax_due_amount
            self.rows["24a"] = 0
            self.rows["24z"] = 0
            self.rows["27"] = 0
        else:
            self.rows["26"] = 0
            self.rows["27"] = req_body.refund_amount
            self.rows["28"] = req_body.refund_amount
            self.rows["28_Refunded"] = req_body.refund_amount
            self.rows["23a"] = 0
            self.rows["23c"] = 0
            self.rows["24a"] = req_body.refund_amount
            self.rows["24z"] = req_body.refund_amount
        
        #schedule b
        self.rows["b:Accrual"] = True
        self.rows["b:2a"] = req_body.business_activity
        self.rows["b:2b"] = req_body.principal_product_service
        self.rows["b:3_No"] = True
        self.rows["b:4a_No"] = True
        self.rows["b:4b_No"] = True
        self.rows["b:5a_No"] = True
        self.rows["b:5b_No"] = True
        self.rows["b:6_No"] = True
        self.rows["b:7_No"] = True
        self.rows["b:9_No"] = True
        self.rows["b:10_No"] = True
        if req_body.total_assets is None:
            total_assets = min(350000, self.rows["6"]*0.3)
        else:
            total_assets = req_body.total_assets
        if total_assets > 250000 and self.rows["1a"] + self.rows["4"] + self.rows["5"] > 250000:
            self.rows["b:11_Yes"] = True
        else:
            self.rows["b:11_No"] = True
        self.rows["b:12_No"] = True
        self.rows["b:13_No"] = True
        self.rows["b:14a_No"] = True
        self.rows["b:14b_No"] = True
        self.rows["b:15_No"] = True
        self.rows["b:16_No"] = True
        
        #schedule k
        self.rows["k:1"] = self.rows["22"]
        self.rows["k:2"] = 0
        self.rows["k:3a"] = 0
        self.rows["k:3b"] = 0
        self.rows["k:3c"] = 0
        self.rows["k:4"] = 0
        self.rows["k:5a"] = self.rows["3"] * random.uniform(0.05,0.1)
        self.rows["k:5b"] = self.rows["k:5a"]
        self.rows["k:6"] = 0
        self.rows["k:7"] = firm.short_term_capitals
        self.rows["k:8a"] = 0
        firm.long_term_capitals = self.rows["k:8a"]
        self.rows["k:8b"] = 0
        self.rows["k:8c"] = 0
        self.rows["k:9"] = 0
        self.rows["k:10"] = 0
        self.rows["k:11"] = 0
        for l in "abcd":
            self.rows[f"k:12{l}"] = 0
        for l in "abcdefg":
            self.rows[f"k:13{l}"] = 0
        for l in "abcdef":
            self.rows[f"k:15{l}"] = 0
        for l in "abcef":
            self.rows[f"k:16{l}"] = 0
        self.rows["k:16d"] = self.rows["22"] * 0.5
        for l in "abc":
            self.rows[f"k:17{l}"] = 0
        self.rows["k:18"] = sum([self.rows[f"k:{i}"] for i in range(1,11) if i != 3 and i != 5 and i != 8]) + self.rows["k:5a"] + self.rows["k:8a"] - self.rows["k:11"] - self.rows["k:12d"] - self.rows["k:16f"]
        firm.k_info = {i.replace("k:", ""):v for i,v in self.rows.items() if ("k:" in i)}
        
        if total_assets > 250000 or self.rows["1a"] + sum([self.rows[str(i)] for i in range(4,11)]) > 250000:
            # schedule m-1
            self.rows["m1:1"] = self.rows["k:18"]
            self.rows["m1:4"] = self.rows["m1:1"]
            self.rows["m1:8"] = self.rows["m1:4"]
            
            # schedule m-2
            if firm.balance_begin_year is None:
                self.rows["m2:1"] = self.rows["m1:1"] * random.uniform(0.4, 0.45)
            else:
                # Исправление: корректный перенос баланса из предыдущего года
                self.rows["m2:1"] = firm.balance_begin_year
            
            self.rows["m2:2"] = self.rows["22"]
            self.rows["m2:3"] = self.rows["k:5a"]
            self.rows["m2:4"] = 0
            self.rows["m2:5"] = 0
            self.rows["m2:6"] = self.rows["m2:1"] + self.rows["m2:2"] + self.rows["m2:3"] - (self.rows["m2:4"] + self.rows["m2:5"])
            self.rows["m2:7"] = self.rows["k:16d"]
            self.rows["m2:8"] = self.rows["m2:6"] - self.rows["m2:7"]
            firm.balance_begin_year = self.rows["m2:8"]
            
            # schedule L - ИСПРАВЛЕНИЕ БАЛАНСА
            if req_body.sells_products_or_services == "Products":
                self.rows["l:3b"] = firm.inventory_start_year
                self.rows["l:3d"] = firm.inventory_end_year
            else:
                self.rows["l:3b"] = 0
                self.rows["l:3d"] = 0
            
            self.rows["l:24b"] = self.rows["m2:1"]
            self.rows["l:24d"] = self.rows["m2:8"]
            self.rows["l:15d"] = total_assets
            
            # Исправление: обеспечение равенства активов и пассивов на начало года
            if firm.assets_begin_year is None:
                # Начальные активы должны равняться начальным пассивам + капиталу
                total_liabilities_equity_begin = self.rows["l:24b"] + random.uniform(0.1, 0.2) * total_assets
                self.rows["l:15b"] = total_liabilities_equity_begin
                
                # Распределение активов с обеспечением баланса
                self.rows["l:4b"] = total_liabilities_equity_begin * random.uniform(0.05, 0.1)
                self.rows["l:1b"] = total_liabilities_equity_begin * random.uniform(0.6, 0.7)
                self.rows["l:8b"] = total_liabilities_equity_begin * random.uniform(0.05, 0.1)
                self.rows["l:3b"] = total_liabilities_equity_begin - (self.rows["l:1b"] + self.rows["l:4b"] + self.rows["l:8b"])
                
                # Обеспечение равенства на конец года
                total_liabilities_equity_end = self.rows["l:24d"] + random.uniform(0.1, 0.2) * total_assets
                self.rows["l:15d"] = total_liabilities_equity_end
                
                self.rows["l:4d"] = total_liabilities_equity_end * random.uniform(0.05, 0.1)
                self.rows["l:1d"] = total_liabilities_equity_end * random.uniform(0.6, 0.7)
                self.rows["l:8d"] = total_liabilities_equity_end * random.uniform(0.05, 0.1)
                self.rows["l:3d"] = total_liabilities_equity_end - (self.rows["l:1d"] + self.rows["l:4d"] + self.rows["l:8d"])
                
            else:
                # Исправление: корректный перенос активов из предыдущего года
                self.rows["l:15b"] = firm.assets_begin_year["l:15d"]  # BOY = предыдущий EOY
                self.rows["l:1b"] = firm.assets_begin_year["l:1d"]
                self.rows["l:4b"] = firm.assets_begin_year["l:4d"]
                self.rows["l:8b"] = firm.assets_begin_year["l:8d"]
                self.rows["l:3b"] = firm.assets_begin_year["l:3d"]
                
                # Расчет конечных значений с обеспечением баланса
                total_liabilities_equity_end = self.rows["l:24d"] + random.uniform(0.1, 0.2) * total_assets
                self.rows["l:15d"] = total_liabilities_equity_end
                
                # Пропорциональное распределение активов на конец года
                asset_ratio = total_liabilities_equity_end / self.rows["l:15b"]
                self.rows["l:1d"] = self.rows["l:1b"] * asset_ratio
                self.rows["l:4d"] = self.rows["l:4b"] * asset_ratio
                self.rows["l:8d"] = self.rows["l:8b"] * asset_ratio
                self.rows["l:3d"] = self.rows["l:3b"] * asset_ratio
                
                # Корректировка для точного равенства
                total_assets_calc = self.rows["l:1d"] + self.rows["l:4d"] + self.rows["l:8d"] + self.rows["l:3d"]
                if abs(total_assets_calc - total_liabilities_equity_end) > 1:
                    # Равномерно распределяем разницу
                    diff_per_asset = (total_liabilities_equity_end - total_assets_calc) / 4
                    self.rows["l:1d"] += diff_per_asset
                    self.rows["l:4d"] += diff_per_asset
                    self.rows["l:8d"] += diff_per_asset
                    self.rows["l:3d"] += diff_per_asset
            
            # Сохраняем активы на конец года для переноса на следующий год
            firm.assets_begin_year = {
                "l:15d": self.rows["l:15d"],
                "l:1d": self.rows["l:1d"],
                "l:4d": self.rows["l:4d"],
                "l:8d": self.rows["l:8d"],
                "l:3d": self.rows["l:3d"]
            }
            
           
            
        self.rows["name"] = req_body.company_name
        self.rows["ein"] = req_body.ein
        self.rows["address"] = req_body.company_street_address
        self.rows["date_inc"] = req_body.date_inc
        if req_body.filing_year < 2025:
            self.rows["town_state_zip"] = req_body.company_town + ", " + req_body.company_state + ", " + req_body.company_zip
        else:
            self.rows["town"] = req_body.company_town
            self.rows["state"] = req_body.company_state
            self.rows["country"] = "United States"
            self.rows["zip"] = req_body.company_zip
        self.rows["total_assets"] = total_assets
        self.rows["CEO_Signature"] = req_body.ceo_signature
        self.rows["Date_Obj"] = get_random_day(req_body.filing_year)
        self.rows["Date"] = self.rows["Date_Obj"].strftime("%m/%d/%Y")
        firm.date = self.rows["Date"]
        self.rows["Title"] = req_body.ceo_position
        if req_body.use_own_cpa:
            self.rows["preparer_Signature"] = req_body.cpa_info.preparer_signature
            self.rows["preparer_Date"] = self.rows["Date"]
            self.rows["preparer_Name"] = req_body.cpa_info.preparer_name
            self.rows["firm_Name"] = req_body.cpa_info.firm_name
            self.rows["preparer_Address"] = req_body.cpa_info.firm_address
            self.rows["preparer_EIN"] = req_body.cpa_info.firm_ein
            self.rows["preparer_PTIN"] = req_body.cpa_info.ptin
            self.rows["preparer_Phone"] = req_body.cpa_info.firm_phone
            
    def insert_need_images(self):
        if self.year >= 2023:
            if "CEO_Signature" in self.rows and len(self.rows["CEO_Signature"]) > 0:
                self.insert_image(0, (102.2,672.5, 124.4,683.8), decode_image(self.rows["CEO_Signature"]))
            self.insert_image(0, (276.5,672.8, 312.5,683.6), text_to_img(self.rows["Date"]))
            if "preparer_Signature" in self.rows and len(self.rows["preparer_Signature"]) > 0:
                self.insert_image(0, (275.6,704.9, 297.8,716.2), decode_image(self.rows["preparer_Signature"]))
            if "preparer_Date" in self.rows:
                self.insert_image(0, (415.8,709, 451.8,719.8), text_to_img(self.rows["preparer_Date"]))
        else:
            if "CEO_Signature" in self.rows and len(self.rows["CEO_Signature"]) > 0:
                self.insert_image(0, (102.2,662.5, 124.4,673.8), decode_image(self.rows["CEO_Signature"]))
            self.insert_image(0, (276.5,662.8, 312.5,673.6), text_to_img(self.rows["Date"]))
            if "preparer_Signature" in self.rows and len(self.rows["preparer_Signature"]) > 0:
                self.insert_image(0, (275.6,694.9, 297.8,706.2), decode_image(self.rows["preparer_Signature"]))
            if "preparer_Date" in self.rows:
                self.insert_image(0, (415.8,699, 451.8,709.8), text_to_img(self.rows["preparer_Date"]))

class Schedule_K1(Form):
    def __init__(self, req_body, owner, firm):
        super().__init__("f1120ssk")
        
        self.rows["ein"] = req_body.ein
        self.rows["name_address"] = req_body.company_name + ", " + req_body.company_street_address + ", " + req_body.company_town + ", " + req_body.company_state + ", " + req_body.company_zip
        
        self.rows["owner_ssn"] = owner.ssn
        self.rows["owner_name"] = owner.name
        self.rows["owner_percent"] = owner.ownership_percentage
        
        self.rows["1"] = firm.k_info["1"] * owner.ownership_percentage / 100
        self.rows["2"] = firm.k_info["2"] * owner.ownership_percentage / 100
        self.rows["3"] = firm.k_info["3c"] * owner.ownership_percentage / 100
        self.rows["4"] = firm.k_info["4"] * owner.ownership_percentage / 100
        self.rows["5a"] = firm.k_info["5a"] * owner.ownership_percentage / 100
        self.rows["5b"] = firm.k_info["5b"] * owner.ownership_percentage / 100
        self.rows["6"] = firm.k_info["6"] * owner.ownership_percentage / 100
        self.rows["7"] = firm.k_info["7"] * owner.ownership_percentage / 100
        self.rows["8a"] = firm.k_info["8a"] * owner.ownership_percentage / 100
        self.rows["8b"] = firm.k_info["8b"] * owner.ownership_percentage / 100
        self.rows["8c"] = firm.k_info["8c"] * owner.ownership_percentage / 100
        self.rows["9"] = firm.k_info["9"] * owner.ownership_percentage / 100
        self.rows["10"] = firm.k_info["10"] * owner.ownership_percentage / 100
        self.rows["11"] = firm.k_info["11"] * owner.ownership_percentage / 100
        self.rows["12a"] = firm.k_info["12a"] * owner.ownership_percentage / 100
        self.rows["12b"] = firm.k_info["12b"] * owner.ownership_percentage / 100
        self.rows["12c"] = firm.k_info["12c"] * owner.ownership_percentage / 100
        self.rows["12d"] = firm.k_info["12d"] * owner.ownership_percentage / 100
        
        self.rows["12a_l"] = "a"
        self.rows["12b_l"] = "b"
        self.rows["12c_l"] = "c"
        self.rows["12d_l"] = "d"
        
        self.rows["16a_l"] = "a"
        self.rows["16b_l"] = "b"
        self.rows["16c_l"] = "c"
        self.rows["16d_l"] = "d"
        
        self.rows["16a"] = firm.k_info["16a"] * owner.ownership_percentage / 100
        self.rows["16b"] = firm.k_info["16b"] * owner.ownership_percentage / 100
        self.rows["16c"] = firm.k_info["16c"] * owner.ownership_percentage / 100
        self.rows["16d"] = firm.k_info["16d"] * owner.ownership_percentage / 100

class TaxTranscript1120(Form):
    def __init__(self, req_body, form1120, form1125a=None):
        super().__init__("tax_transcript1120")
        
        # Словарь для хранения счетчиков дублирующихся строк
        counters = {}
        
        # Основные секции и их маппинг
        if req_body.company_type == "S corp":
            sections_mapping = self.get_1120s_mapping()
        else:
            sections_mapping = self.get_1120_mapping()
        
        self.rows = {}
        
        for section, fields in sections_mapping.items():
            for field_name, form_line in fields:
                # Обработка дублирующихся имен полей
                if field_name in self.rows:
                    if field_name not in counters:
                        counters[field_name] = 0
                        unique_field_name = field_name
                    else:
                        unique_field_name = f"{field_name}{counters[field_name]}"
                    counters[field_name] += 1
                else:
                    unique_field_name = field_name
                    counters[field_name] = 1
                
                # Получение значения из формы 1120 или установка 0
                if form_line is None:
                    self.rows[unique_field_name] = 0
                else:
                    # Поиск значения в форме 1120
                    form_key = form_line
                    if form_key in form1120.rows:
                        self.rows[unique_field_name] = form1120.rows[form_key]
                    else:
                        # Если строка не найдена, устанавливаем 0
                        self.rows[unique_field_name] = 0
        
        #вставляем общие данные
        start_date = get_random_day(req_body.filing_year, form1120.rows["Date_Obj"].day)
        self.rows["Request_Date"] = start_date.strftime("%m-%d-%Y")
        self.rows["Response_Date"] = start_date.strftime("%m-%d-%Y")
        self.rows["Tax_Year"] = str(req_body.filing_year)
        self.rows["EIN"] = req_body.ein
        self.rows["Name"] = req_body.company_name
        self.rows["Received_Data"] = (start_date+timedelta(days=random.randint(1,10))).strftime("%b %d, %Y")
        self.rows["Address"] = req_body.company_town + ", " + req_body.company_state + ", " + req_body.company_zip + ", " + req_body.company_street_address
        self.rows["Cycle_Posted"] = str(req_body.filing_year+1)+random.choice(('05','01','02','03','04'))+str(random.randint(19,25))
        self.rows["Tracking_Number"] = str(1120+req_body.filing_year+1-2020)+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+"XXX"
        if req_body.prepared_by == "CPA/Paid Preparer" and req_body.use_own_cpa:
            self.rows["PTIN"] = req_body.cpa_info.ptin
            self.rows["EIN_Preparer"] = req_body.cpa_info.firm_ein
        
        self.rows["Total compensation of officers"] = form1120.rows["12"]
        self.rows["Total compensation of officers per computer"] = form1120.rows["12"]
        if form1125a:
            self.rows["Inventory at beginning of year"] = form1125a.rows["1"]
            self.rows["Purchases"] = form1125a.rows["2"]
            self.rows["Cost of labor"] = form1125a.rows["3"]
            self.rows["Other costs"] = form1125a.rows["5"]
            self.rows["Other costs per computer"] = form1125a.rows["5"]
            self.rows["Total costs"] = form1125a.rows["6"]
            self.rows["Total costs per computer"] = form1125a.rows["6"]
            self.rows["Inventory at end of year"] = form1125a.rows["7"]
            self.rows["Inventory at end of year per computer"] = form1125a.rows["7"]
            self.rows["Cost of goods sold"] = form1125a.rows["8"]
            self.rows["Cost of goods sold per computer"] = form1125a.rows["8"]
    
    def get_1120_mapping(self):
        return {
            'INCOME': [
                ('Gross receipts or sales', '1a'),
                ('Gross receipts or sales per computer', '1a'),
                ('Returns and allowances', '1b'),
                ('Balance', '1c'),
                ('Balance per computer', '1c'),
                ('Cost of goods sold', '2'),
                ('Gross profit', '3'),
                ('Gross profit per computer', '3'),
                ('Dividends and inclusions', '4'),
                ('Interest', None),  # 0
                ('Gross rents', '6'),
                ('Gross royalties', None),  # 0
                ('Capital gain net income', '8'),
                ('Other income', '10'),
                ('Total income', '11'),
                ('Total income per computer', '11')
            ],
            
            'DEDUCTIONS': [
                ('Compensation of officers', '12'),
                ('Compensation of officers per computer', '12'),
                ('Salaries and wages', '13'),
                ('Repairs and maintenance', '14'),
                ('Bad debts', '15'),
                ('Rents', '16'),
                ('Taxes and licenses', '17'),
                ('Interest', '18'),
                ('Charitable contributions', None),  # 0
                ('Depreciation', '20'),
                ('Depletion', None),  # 0
                ('Advertising', '22'),
                ('Pension, profit-sharing, etc., plans', '23'),
                ('Employee benefit programs', '24'),
                ('Other deductions', '26'),
                ('Total deductions', '27'),
                ('Total deductions per computer', '27'),
                ('Taxable income before net operating loss deduction', '28'),
                ('Net operating loss deduction', None),  # 0
                ('Special deductions', '29b'),
                ('Total net operating loss deduction and special deductions', '29b')
            ],
            
            'TAX, CREDITS AND PAYMENTS': [
                ('Taxable income', '30'),
                ('Taxable income per computer', '30'),
                ('Total tax', '31'),
                ('Total payments and credits', '33'),
                ('Amount owed', '35'),
                ('Overpayment', '-'),
                ('Credited to 2025 estimated tax', None),  # 0
                ('Refunded', '36')
            ],
            
            'SCHEDULE C': [
                ('Dividends from less-than-20%-owned domestic corporations', 'c:1a'),
                ('Dividends from 20%-or-more-owned domestic corporations', None),  # 0
                ('Dividends on certain debt-financed stock of domestic and foreign corporations', None),  # 0
                ('Dividends on certain preferred stock of less-than-20%-owned public utilities', 'c:4a'),
                ('Dividends on certain preferred stock of 20%-or-more-owned public utilities', None),  # 0
                ('Dividends from less-than-20%-owned foreign corporations and certain FSCs', 'c:6a'),
                ('Dividends from 20%-or-more-owned foreign corporations and certain FSCs', None),  # 0
                ('Dividends from wholly owned foreign subsidiaries', None),  # 0
                ('Dividends from domestic corporations received by a small business', None),  # 0
                ('Foreign-source portion of dividends', None),  # 0
                ('Reserved for future use', None),  # 0
                ('Global Intangible Low-Taxed Income', None),  # 0
                ('Gross-up for foreign taxes deemed paid', None),  # 0
                ('IC-DISC and former DISC dividends', None),  # 0
                ('Other dividends', None),  # 0
                ('Total dividends and inclusions', 'c:23'),
                ('Total dividends and inclusions per computer', 'c:23'),
                ('Total special deductions', 'c:24'),
                ('Total special deductions per computer', 'c:24')
            ],
            
            'SCHEDULE J': [
                ('Income tax', 'j:1a'),
                ('Tax from Form 1120-L', None),  # 0
                ('Total income tax', 'j:1a'),
                ('Total income tax per computer', 'j:1a'),
                ('Total credits', 'j:6'),
                ('Total tax', 'j:12'),
                ('Total tax per computer', 'j:12'),
                ('Current year\'s estimated tax payments', 'j:14'),
                ('Reserved for future use', None),  # 0
                ('Total payments', 'j:19'),
                ('Total payments per computer', 'j:19'),
                ('Total credits', None),  # 0
                ('Total credits per computer', None),  # 0
                ('Total payments and credits', 'j:23'),
                ('Total payments and credits per computer', 'j:23')
            ],
            
            'SCHEDULE L': [
                ('Total assets at beginning of tax year', "l:15b"),
                ('Total assets at beginning of tax year per computer', "l:15b"),
                ('Total assets at end of tax year', "l:15d"),
                ('Total assets at end of tax year per computer', "l:15d")
            ],
            
            'SCHEDULE M-1': [
                ('Net income (loss) per books', 'm1:1'),
                ('Net income (loss) per books', 'm1:2'),
                ('Excess of capital losses over capital gains', None),  # 0
                ('Income subject to tax not recorded on books this year', None),  # 0
                ('Deductions on this return not charged against book income this year', None),  # 0
                ('Income', 'm1:1')
            ],
            
            'SCHEDULE M-2': [
                ('Balance at beginning of year', 'm2:1'),
                ('Net income (loss) per books', 'm2:2'),
                ('Other increases', None),  # 0
                ('Distributions', 'm2:5a'),
                ('Other decreases', 'm2:6'),
                ('Balance at end of year', 'm2:8')
            ]
        }
    
    def get_1120s_mapping(self):
        return {
            'INCOME': [
                ('Gross receipts or sales', '1a'),
                ('Returns and allowances', '1b'),
                ('Balance', '1c'),
                ('Cost of goods sold', '2'),
                ('Gross profit', '3'),
                ('Net gain (loss) from Form 4797', '4'),
                ('Other income (loss)', '5'),
                ('Total income (loss)', '6')
            ],
            
            'DEDUCTIONS': [
                ('Compensation of officers', '7'),
                ('Salaries and wages', '8'),
                ('Repairs and maintenance', '9'),
                ('Bad debts', '10'),
                ('Rents', '11'),
                ('Taxes and licenses', '12'),
                ('Interest', '13'),
                ('Depreciation from Form 4562', '14'),
                ('Depletion', '15'),
                ('Advertising', '16'),
                ('Pension, profit-sharing, etc., plans', '17'),
                ('Employee benefit programs', '18'),
                ('Energy efficient commercial buildings deduction', '19'),
                ('Other deductions', '20'),
                ('Total deductions', '21'),
                ('Ordinary business income (loss)', '22')
            ],
            
            'TAX AND PAYMENTS': [
                ('Excess net passive income or LIFO recapture tax', '23a'),
                ('Tax from Schedule D', '23b'),
                ('Total tax', '23c'),
                ('Current year\'s estimated tax payments', '24a'),
                ('Tax deposited with Form 7004', '24b'),
                ('Credit for federal tax paid on fuels', '24c'),
                ('Elective payment election amount from Form 3800', '24d'),
                ('Total payments and credits', '24z'),
                ('Estimated tax penalty', '25'),
                ('Amount owed', '26'),
                ('Overpayment', '-'),
                ('Credited to 2024 estimated tax', '28'),
                ('Refunded', '28')
            ],
            
            'SCHEDULE K': [
                ('Ordinary business income (loss)', 'k:1'),
                ('Net rental real estate income (loss)', 'k:2'),
                ('Other gross rental income (loss)', 'k:3a'),
                ('Expenses from other rental activities', 'k:3b'),
                ('Other net rental income (loss)', 'k:3c'),
                ('Interest income', 'k:4'),
                ('Ordinary dividends', 'k:5a'),
                ('Qualified dividends', 'k:5b'),
                ('Royalties', 'k:6'),
                ('Net short-term capital gain (loss)', 'k:7'),
                ('Net long-term capital gain (loss)', 'k:8a'),
                ('Collectibles (28%) gain (loss)', 'k:8b'),
                ('Unrecaptured section 1250 gain', 'k:8c'),
                ('Net section 1231 gain (loss)', 'k:9'),
                ('Other income (loss)', 'k:10'),
                ('Section 179 deduction', 'k:11'),
                ('Charitable contributions', 'k:12a'),
                ('Investment interest expense', 'k:12b'),
                ('Section 59(e)(2) expenditures', 'k:12c'),
                ('Other deductions', 'k:12d'),
                ('Low-income housing credit (section 42(j)(5))', 'k:13a'),
                ('Low-income housing credit (other)', 'k:13b'),
                ('Qualified rehabilitation expenditures', 'k:13c'),
                ('Other rental real estate credits', 'k:13d'),
                ('Other rental credits', 'k:13e'),
                ('Biofuel producer credit', 'k:13f'),
                ('Other credits', 'k:13g'),
                ('Post-1986 depreciation adjustment', 'k:15a'),
                ('Adjusted gain or loss', 'k:15b'),
                ('Depletion (other than oil and gas)', 'k:15c'),
                ('Oil, gas, and geothermal properties—gross income', 'k:15d'),
                ('Oil, gas, and geothermal properties—deductions', 'k:15e'),
                ('Other AMT items', 'k:15f'),
                ('Tax-exempt interest income', 'k:16a'),
                ('Other tax-exempt income', 'k:16b'),
                ('Nondeductible expenses', 'k:16c'),
                ('Distributions', 'k:16d'),
                ('Repayment of loans from shareholders', 'k:16e'),
                ('Foreign taxes paid or accrued', 'k:16f'),
                ('Investment income', 'k:17a'),
                ('Investment expenses', 'k:17b'),
                ('Dividend distributions paid from accumulated earnings and profits', 'k:17c'),
                ('Income (loss) reconciliation', 'k:18')
            ],
            
            'SCHEDULE L': [
                ('Total assets at beginning of tax year', "l:15b"),
                ('Total assets at beginning of tax year per computer', "l:15b"),
                ('Total assets at end of tax year', "l:15d"),
                ('Total assets at end of tax year per computer', "l:15d")
            ],
            
            'SCHEDULE M-1': [
                ('Net income (loss) per books', 'm1:1'),
                ('Net income (loss) per books', 'm1:2'),
                ('Excess of capital losses over capital gains', None),  # 0
                ('Income subject to tax not recorded on books this year', None),  # 0
                ('Deductions on this return not charged against book income this year', None),  # 0
                ('Income', 'm1:1')
            ],
            
            'SCHEDULE M-2': [
                ('Balance at beginning of year', 'm2:1'),
                ('Net income (loss) per books', 'm2:2'),
                ('Other increases', None),  # 0
                ('Distributions', 'm2:5a'),
                ('Other decreases', 'm2:6'),
                ('Balance at end of year', 'm2:8')
            ],
            
            'OTHER INFORMATION': [
                ('Accounting method - Cash', '1a'),
                ('Accounting method - Accrual', '1b'),
                ('Accounting method - Other', '1c'),
                ('Business activity', '2a'),
                ('Product or service', '2b'),
                ('Shareholder information - disregarded entities, trusts, etc.', '3'),
                ('Corporate ownership - 20% or more of other corporations', '4a'),
                ('Partnership/trust ownership - 20% or more interest', '4b'),
                ('Restricted stock outstanding', '5a'),
                ('Stock options, warrants outstanding', '5b'),
                ('Form 8918 required', '6'),
                ('Publicly offered debt instruments', '7'),
                ('Net unrealized built-in gain', '8'),
                ('Section 163(j) election', '9'),
                ('Section 163(j) limitations apply', '10'),
                ('Small corporation exemption', '11'),
                ('Non-shareholder debt canceled or modified', '12'),
                ('QSub election terminated or revoked', '13'),
                ('Form 1099 payments made', '14a'),
                ('Form 1099 filed or will file', '14b'),
                ('Qualified Opportunity Fund', '15'),
                ('Digital asset transactions', '16')
            ]
        }
