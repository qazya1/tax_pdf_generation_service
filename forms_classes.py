import random
import pandas as pd
from pdf_filling import Form, decode_image, text_to_img, get_image_from_path
from datetime import datetime, timedelta

standart_deduction_df = pd.read_csv("configs/Standard_Deduction_Config.csv")
tax_brackets_df = pd.read_csv("configs/federal_tax_brackets.csv")
tax_brackets_df = tax_brackets_df.fillna(-1)
se_tax_df = pd.read_csv("configs/SE_tax_config.csv")
companies_df = pd.read_csv("configs/companies_dividents.csv")
cpa_df = pd.read_csv("configs/CPA_Firms_Config.csv")
cpa_df = cpa_df.fillna("")

#функция для выбора фирмы
def prepared_firm_choice(state):
    CPA_firm_serie = cpa_df.loc[cpa_df["CPA FIRM STATE"]==state]
    if len(CPA_firm_serie) == 0:
        i_l = []
        for i in df.index:
            if type(df.loc[i, "STATES ALSO SERVED"]) == str and ("OH" in df.loc[i, "STATES ALSO SERVED"]):
                i_l.append(i)
        if len(i_l) == 0:
            state = random.choice(("NY", "CA", "FL", "TX"))
            CPA_firm_serie = cpa_df.loc[cpa_df["CPA FIRM STATE"]==state]
            CPA_firm_serie = CPA_firm_serie.loc[random.choice(CPA_firm_serie.index)]
        else:
            CPA_firm_serie = df.loc[random.choice(i_l)]
    else:
        CPA_firm_serie = CPA_firm_serie.loc[random.choice(CPA_firm_serie.index)]
    return CPA_firm_serie

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

#функция для вычисления налога самозанятого
def get_self_employed_tax(year, married, income):
    global se_tax_df
    bool_cond = (se_tax_df["Year"]==year) & (se_tax_df["FilingStatus"]==married)
    net_profit = income*se_tax_df.loc[bool_cond]["NetEarningsFactor"].iloc[0]
    #print(net_profit)
    with_ss = min(net_profit,se_tax_df.loc[bool_cond]["SSWageBase"].iloc[0]) * se_tax_df.loc[bool_cond]["SSRatePercent"].iloc[0] * 0.01
    #print(with_ss)
    with_mediacare = net_profit * se_tax_df.loc[bool_cond]["MedicareRatePercent"].iloc[0] * 0.01
    #print(with_mediacare)
    if with_mediacare > se_tax_df.loc[bool_cond]["AddMedThreshold"].iloc[0]:
        with_mediacare += net_profit*se_tax_df.loc[bool_cond]["AddMedRatePercent"].iloc[0] * 0.01
    #print(with_mediacare)
    se_tax = with_ss + with_mediacare
    #print(se_tax)
    return round(se_tax, 2)

#функция для генерации дат
def get_random_day(year):
    dt = datetime(year=year+1, day=random.randint(1,15), month=4)
    while dt.weekday() == 6:
        dt = datetime(year=year+1, day=random.randint(1,15), month=4)
    return dt.strftime("%m/%d/%Y")

#в этом классе помещаем логику выбора форм и наиболее часто использующиеся данные
class Person:
    def __init__(self, json_interface):
        self.total_income = json_interface["grossIncomeAmount"]
        self.employee = json_interface["employmentType"]
        self.marital_status = json_interface["maritalStatus"]
        self.year = json_interface["year"]
        self.self_employed_tax = 0
        self.additional_income = None
        self.adjustments = None
        self.qualified_dividents = None
        self.date = None
        self.total_tax = None
        self.federal_tax_withheld = None
        self.refund_amount = None
        self.owe_amount = None
        self.prepared_firm_info = None
        self.all_wages_salaries_etc = None
        self.standart_deduction = None
        self.total_payments = None
        self.balance = None
        self.se_info = None
        self.taxable_income = None

#классы форм

class Form_1040(Form):
    def __init__(self, json_interface, person):
        global standart_deduction_df
        super().__init__("1040")
        self.tax_refund = json_interface["refundOrPayment"]
        
        #числовое ядро
        self.rows["9"] = person.total_income
        if person.employee == "Employed":
            self.rows["1a"] = round(random.uniform(0.75, 0.8) * person.total_income, 2)
            self.rows["1c"] = round(random.uniform(0.01, 0.05) * person.total_income, 2)
            #для дальнейшего использования
            self.rows["1b"] = 0
            self.rows["1d"] = 0
            self.rows["1e"] = 0
            self.rows["1f"] = 0
            self.rows["1g"] = 0
            self.rows["1h"] = 0
            
            self.rows["1z"] = self.rows["1a"]+self.rows["1c"]+self.rows["1b"]+self.rows["1d"]+self.rows["1e"]+self.rows["1f"]+self.rows["1g"]+self.rows["1h"]
            self.rows["3b"] = round(random.uniform(0.03, 0.05) * person.total_income, 2)
            self.rows["8"] = person.total_income - self.rows["1z"] - self.rows["3b"]
            self.rows["10"] = round(random.uniform(0.03, 0.06) * person.total_income, 2)
            self.rows["11"] = person.total_income - self.rows["10"]
            deduction = standart_deduction_df.loc[(standart_deduction_df["Year"]==person.year) & (standart_deduction_df["FilingStatus"]==person.marital_status)]["StandardDeduction"].iloc[0]
            self.rows["12"] = min(self.rows["11"], deduction)
            self.rows["13"] = 0    #для дальнейшего использования
            self.rows["14"] = self.rows["12"]+self.rows["13"]
            self.rows["15"] = self.rows["11"] - self.rows["14"]
            self.rows["16"] = get_tax(person.year, person.marital_status, self.rows["15"])
            self.rows["17"] = 0
            self.rows["18"] = self.rows["16"]+self.rows["17"]
            self.rows["21"] = 0    #для дальнейшего использования
            self.rows["22"] = self.rows["18"] - self.rows["21"]
            self.rows["23"] = 0    #налог для самозанятых не выплачивается
            self.rows["24"] = self.rows["22"]+self.rows["23"]
        else:
            self.rows["1a"] = round(random.uniform(0.05, 0.15) * person.total_income, 2)
            self.rows["1c"] = round(random.uniform(0.01, 0.05) * person.total_income, 2)
            #для дальнейшего использования
            self.rows["1b"] = 0
            self.rows["1d"] = 0
            self.rows["1e"] = 0
            self.rows["1f"] = 0
            self.rows["1g"] = 0
            self.rows["1h"] = 0
            
            self.rows["1z"] = self.rows["1a"]+self.rows["1c"]+self.rows["1b"]+self.rows["1d"]+self.rows["1e"]+self.rows["1f"]+self.rows["1g"]+self.rows["1h"]
            
            self.rows["8"] = round(random.uniform(0.6, 0.8) * person.total_income, 2)
            person.self_employed_tax = get_self_employed_tax(person.year, person.marital_status, self.rows["8"])
            self.rows["3b"] = person.total_income - self.rows["1z"] - self.rows["8"]
            if self.rows["3b"] < 0:
                self.rows["3b"] = 0
            self.rows["10"] = round(person.self_employed_tax * 0.5, 2)
            
            self.rows["11"] = person.total_income - self.rows["10"]
            deduction = standart_deduction_df.loc[(standart_deduction_df["Year"]==person.year) & (standart_deduction_df["FilingStatus"]==person.marital_status)]["StandardDeduction"].iloc[0]
            self.rows["12"] = min(self.rows["11"], deduction)
            self.rows["13"] = 0    #для дальнейшего использования
            self.rows["14"] = self.rows["12"]+self.rows["13"]
            self.rows["15"] = self.rows["11"] - self.rows["14"]
            self.rows["16"] = get_tax(person.year, person.marital_status, self.rows["15"])
            self.rows["17"] = 0
            self.rows["18"] = self.rows["16"]+self.rows["17"]
            self.rows["21"] = 0    #для дальнейшего использования
            self.rows["22"] = self.rows["18"] - self.rows["21"]
            self.rows["23"] = person.self_employed_tax
            self.rows["24"] = self.rows["22"]+self.rows["23"]
        if self.tax_refund == "TAX_REFUND":
            self.rows["35a"] = json_interface["refundAmount"]
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
            self.rows["35b"] = json_interface["bankRoutingNumber"]
            self.rows["35d"] = json_interface["bankAccountNumber"]
        else:
            self.rows["34"] = 0
            self.rows["37"] = json_interface["taxesDueAmount"]
            person.owe_amount = self.rows["37"]
            self.rows["25a"] = self.rows["24"] - self.rows["37"]
            if self.rows["25a"] < 0:
                #print(1)
                self.rows["23"] = -self.rows["25a"]
                #print(1)
                person.self_employed_tax = self.rows["23"]
                self.rows["10"] = round(person.self_employed_tax * 0.5, 2)
                self.rows["25a"] = 0
                self.rows["24"] = self.rows["22"]+self.rows["23"]
                
                self.rows["11"] = person.total_income - self.rows["10"]
                self.rows["12"] = min(self.rows["11"], deduction)
                self.rows["13"] = 0    #для дальнейшего использования
                self.rows["14"] = self.rows["12"]+self.rows["13"]
                self.rows["15"] = self.rows["11"] - self.rows["14"]
                self.rows["16"] = get_tax(person.year, person.marital_status, self.rows["15"])
                self.rows["17"] = 0
                self.rows["18"] = self.rows["16"]+self.rows["17"]
                self.rows["21"] = 0    #для дальнейшего использования
                self.rows["22"] = self.rows["18"] - self.rows["21"]
                self.rows["24"] = self.rows["22"]+self.rows["23"]
            self.rows["25b"] = 0
            self.rows["25c"] = 0
            self.rows["25d"] = self.rows["25a"]+self.rows["25b"]+self.rows["25c"]
            self.rows["26"] = 0
            self.rows["32"] = 0
            self.rows["33"] = self.rows["32"]+self.rows["26"]+self.rows["25d"]
        
        person.balance = self.rows["34"]-self.rows["37"]
        
        #очищаем ненужные поля
        need_rows = ["1a", "1c", "1z", "3b", "8", "9", "10", "11", "12", "14", "15", "16", "17", "18", "22", "24"]
        if person.employee != "Employed":
            need_rows.append("23")
        if self.tax_refund == "TAX_REFUND":
            need_rows += ["25a", "25d", "33", "34", "35a", "35b", "35d"]
        else:
            need_rows += ["25a", "25d", "33", "37"]
        no_need_rows = list(set(self.rows) - set(need_rows))
        for row in no_need_rows:
            if row in self.rows:
                self.rows.pop(row)
        
        #вставляем личные данные
        if person.marital_status == "MarriedFilingJointly":
            self.rows["Married_filing_jointly"] = True
        else:
            self.rows["Single"] = True
        self.rows["Your_first_name_and_middle_initial"] = json_interface["firstName"]
        self.rows["Last_name"] = json_interface["lastName"]
        
        if "spouseFirstName" in json_interface:
            self.rows["Spouse_First_Name"] = json_interface["spouseFirstName"]
        if "spouseLastName" in json_interface:
            self.rows["Spouse_Last_Name"] = json_interface["spouseLastName"]
        
        self.rows["Home_Address"] = json_interface["residentialAddress"]
        self.rows["City_town_post_office"] = json_interface["town"]
        self.rows["State"] = json_interface["state"]
        self.rows["ZIP_code"] = json_interface["zipCode"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]
        if "spouseSsn" in json_interface:
            self.rows["Spouse_social_security_number"] = json_interface["spouseSsn"]
        self.rows["Your_occupation"] = json_interface["occupation"]
        if "spouseOccupation" in json_interface:
            self.rows["Spouse_occupation"] = json_interface["spouseOccupation"]
        if "signature" in json_interface:
            self.rows["Your_Spouse_Signature"] = json_interface["signature"]
        if "spouseSignature" in json_interface:
            self.rows["Your_Spouse_Signature"] = json_interface["spouseSignature"]
        self.rows["Date"] = get_random_day(person.year)
        if person.marital_status == "MarriedFilingJointly":
            self.rows["Spouce_Date"] = self.rows["Date"]
        if "dependents" in json_interface:
            for n,dependent in enumerate(json_interface["dependents"]):
                self.rows[f"Dependent_{n}_name"] = dependent["name"]
                self.rows[f"Dependent_{n}_SSN"] = dependent["ssn"]
                self.rows[f"Dependent_{n}_relation"] = dependent["relation"]
        self.rows["35c_checking"] = True
        self.rows["Digital_Assets_No"] = True
        
        #поля для фирмы по подготовке налогов
        if json_interface["preparationType"] != "Self-prepared":
            CPA_firm_serie = prepared_firm_choice(json_interface["state"])
            self.rows["preparer_Name"] = CPA_firm_serie["CPA PERSONAL NAME"]
            self.rows["preparer_PTIN"] = CPA_firm_serie["CPA FIRM PTIN"]
            self.rows["preparer_Phone"] = CPA_firm_serie["CPA FIRM PHONE NUMBER"]
            self.rows["preparer_Firm_Name"] = CPA_firm_serie["CPA FIRM NAME"]
            CPA_firm_serie["CPA FIRM ZIP CODE"] = str(CPA_firm_serie["CPA FIRM ZIP CODE"])
            self.rows["preparer_Firm_Address"] = CPA_firm_serie["CPA FIRM ADDRESS"] + ", " + CPA_firm_serie["CPA FIRM TOWN"] + ", " + CPA_firm_serie["CPA FIRM STATE"] + " " +CPA_firm_serie["CPA FIRM ZIP CODE"]
            self.rows["preparer_Firm_EIN"] = CPA_firm_serie["CPA FIRM EIN"]
            self.rows["preparer_Signature"] = CPA_firm_serie["CPA SIGNATURE"]
            self.rows["preparer_Date"] = self.rows["Date"]
            person.prepared_firm_info = CPA_firm_serie
        
        #запоминаем общие значения
        person.additional_income = self.rows["8"]
        person.adjustments = self.rows["10"]
        person.qualified_dividents = self.rows["3b"]
        person.total_tax = self.rows["24"]
        person.federal_tax_withheld = self.rows["25d"]
        person.date = self.rows["Date"]
        person.all_wages_salaries_etc = self.rows["1z"]
        person.standart_deduction = self.rows["12"]
        person.total_payments = self.rows["33"]
        person.taxable_income = self.rows["15"]
    
    def insert_need_images(self):
        #вставляем подписи
        if "Your_Signature" in self.rows:
            self.insert_image(1, (110,465, 137,497), decode_image(self.rows["Your_Signature"]))
        if "Your_Spouse_Signature" in self.rows:
            self.insert_image(1, (112,495, 139,527), decode_image(self.rows["Your_Spouse_Signature"]))
        #вставляем даты
        self.insert_image(1, (275,476, 323,491), text_to_img(self.rows["Date"]))
        if "Spouce_Date" in self.rows:
            self.insert_image(1, (275,505, 323,520), text_to_img(self.rows["Spouce_Date"]))
        if "preparer_Signature" in self.rows and len(self.rows["preparer_Signature"]) > 0:
            self.insert_image(1, (224,543, 380,558), get_image_from_path(self.rows["preparer_Signature"]))
        if "preparer_Date" in self.rows:
            self.insert_image(1, (392,544, 440,559), text_to_img(self.rows["preparer_Date"]))

class Schedule1(Form):
    def __init__(self, json_interface, person):
        super().__init__("Schedule1")
        
        #числовое ядро
        if person.employee == "Employed":
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
        else:
            self.rows["3"] = person.additional_income
            self.rows["10"] = person.additional_income
            self.rows["26"] = person.adjustments
            self.rows["15"] = round(person.self_employed_tax * 0.5, 2)
            self.rows["22"] = self.rows["26"] - self.rows["15"]
            need_rows = ["3", "15", "10", "22", "26"]
        
        #очищаем ненужные поля
        no_need_rows = list(set(self.rows) - set(need_rows))
        for row in no_need_rows:
            if row in self.rows:
                self.rows.pop(row)
        
        #вставляем личные данные
        if person.marital_status == "Single":
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"]
        else:
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"] + " ; " + json_interface["spouseFirstName"] + " " + json_interface["spouseLastName"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]

class Schedule2(Form):
    def __init__(self, json_interface, person):
        super().__init__("Schedule2")
        #числовое ядро
        self.rows["4"] = person.self_employed_tax
        self.rows["18"] = person.self_employed_tax
        self.rows["21"] = person.self_employed_tax
        
        #вставляем личные данные
        if person.marital_status == "Single":
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"]
        else:
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"] + " ; " + json_interface["spouseFirstName"] + " " + json_interface["spouseLastName"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]

class ScheduleB(Form):
    def __init__(self, json_interface, person):
        super().__init__("ScheduleB")
        
        #числовое ядро
        self.rows["6"] = person.qualified_dividents
        if person.qualified_dividents >= 1500:
            self.rows["7a_NO"] = True
            self.rows["7b_NO"] = True
            self.rows["8_NO"] = True
        
        #вставляем личные данные
        if person.marital_status == "Single":
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"]
        else:
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"] + " ; " + json_interface["spouseFirstName"] + " " + json_interface["spouseLastName"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]
        companies = [random.choice(companies_df["Full Legal Name"]) for i in range(random.randint(3,6))]
        average = person.qualified_dividents/len(companies)
        companies_values = [round(average*(1+random.uniform(-0.05,0.05)), 2) for i in range(len(companies)-1)]
        companies_values.append(person.qualified_dividents-sum(companies_values))
        for n, company in enumerate(companies):
            self.rows[f"List_of_companies_row{n+1}"] = company
        for n, value in enumerate(companies_values):
            self.rows[f"Amount_companies_row{n+1}"] = value

class ScheduleC(Form):
    def __init__(self, json_interface, person):
        super().__init__("ScheduleC")
        
        #числовое ядро
        self.rows["31"] = person.additional_income
        self.rows["1"] = round(person.additional_income * random.uniform(1.5, 1.9), 2)
        self.rows["2"] = round(self.rows["1"] * random.uniform(0.03, 0.05), 2)
        self.rows["3"] = self.rows["1"] - self.rows["2"]
        self.rows["4"] = round(self.rows["1"] * random.uniform(0.15, 0.2), 2)
        self.rows["35"] = round(self.rows["1"] * random.uniform(0.3, 0.4), 2)
        self.rows["5"] = self.rows["3"] - self.rows["4"]
        self.rows["6"] = 0    #для дальнейшего использования
        self.rows["7"] = self.rows["5"] + self.rows["6"]
        self.rows["28"] = round(self.rows["7"] - self.rows["31"])
        self.rows["29"] = self.rows["31"]
        self.rows["8"] = round(self.rows["28"] * random.uniform(0.15, 0.2), 2)
        self.rows["9"] = round(self.rows["28"] * random.uniform(0.05, 0.07), 2)
        self.rows["11"] = round(self.rows["28"] * random.uniform(0.1, 0.15), 2)
        self.rows["15"] = round(self.rows["28"] * random.uniform(0.05, 0.07), 2)
        self.rows["17"] = round(self.rows["28"] * random.uniform(0.05, 0.07), 2)
        self.rows["18"] = round(self.rows["28"] * random.uniform(0.1, 0.15), 2)
        self.rows["20a"] = round(self.rows["28"] * random.uniform(0.05, 0.15), 2)
        self.rows["24a"] = round(self.rows["28"] * random.uniform(0.1, 0.15), 2)
        self.rows["25"] = round(self.rows["28"] * random.uniform(0.05, 0.07), 2)
        result_sum = self.rows["8"] + self.rows["9"] + self.rows["11"] + self.rows["15"] + self.rows["17"] + self.rows["18"] + self.rows["20a"] + self.rows["24a"] + self.rows["25"]
        if result_sum > self.rows["28"]:
            over_part = round(0.02 * self.rows["28"], 2)
            for i in ["8", "9", "11", "15", "17", "18", "20a", "24a", "25"]:
                self.rows[i] -= over_part
        result_sum = self.rows["8"] + self.rows["9"] + self.rows["11"] + self.rows["15"] + self.rows["17"] + self.rows["18"] + self.rows["20a"] + self.rows["24a"] + self.rows["25"]
        if result_sum < self.rows["28"]:
            self.rows["23"] = self.rows["28"] - result_sum
        self.rows["26"] = 0    #для дальнейшего использования
        self.rows["37"] = self.rows["26"] + self.rows["11"]
        base_number = self.rows["37"] + self.rows["35"] - self.rows["4"]
        self.rows["38"] = round(random.uniform(0.8, 1.2)*base_number, 2)
        self.rows["39"] = round(random.uniform(0.8, 1.2)*base_number, 2)
        self.rows["41"] = base_number + self.rows["38"] + self.rows["39"]
        self.rows["42"] = self.rows["4"]
        self.rows["33_cost"] = True
        self.rows["34_no"] = True
        
        #очищаем ненужные поля
        no_need_rows = ["6", "26"]
        for row in no_need_rows:
            if row in self.rows:
                self.rows.pop(row)
        
        #вставляем личные данные
        self.rows["Name_of_propietor"] = json_interface["firstName"] + " " + json_interface["lastName"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]
        self.rows["Principal_business_or_profession"] = json_interface["principalBusiness"]
        if "businessName" in json_interface:
            self.rows["Business_Name"] = json_interface["businessName"]
        else:
            self.rows["Business_Name"] = json_interface["firstName"] + " " + json_interface["lastName"] + " Sole Prop."
        if "businessAddress" in json_interface:
            self.rows["Business_Address"] = json_interface["businessAddress"]
        else:
            self.rows["Business_Address"] = json_interface["residentialAddress"]
        place = ""
        if "businessTown" in json_interface:
            place += json_interface["businessTown"]
        else:
            place += json_interface["town"]
        place += ", "
        if "businessState" in json_interface:
            place += json_interface["businessState"]
        else:
            place += json_interface["state"]
        place += " "
        if "businessZip" in json_interface:
            place += json_interface["businessZip"]
        else:
            place += json_interface["zipCode"]
        self.rows["City_town_post_office"] = place
        if "ein" in json_interface:
            self.rows["Employer_ID_number"] = json_interface["ein"].replace("-", "")
        self.rows["Code_from_instructions"] = json_interface["naicsCode"]
        self.rows["F_Accrual"] = True
        self.rows["G_Yes"] = True
        self.rows["I_No"] = True

class ScheduleSE(Form):
    def __init__(self, json_interface, person):
        super().__init__("ScheduleSE")
        
        #числовое ядро
        self.rows["2"] = person.additional_income
        self.rows["12"] = person.self_employed_tax
        self.rows["13"] = round(person.self_employed_tax * 0.5, 2)
        if person.additional_income > 0:
            self.rows["4c"] = round(0.9235*self.rows["2"], 2)
            self.rows["3"] = self.rows["4c"]
        
        #вставляем личные данные
        if person.marital_status == "Single":
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"]
        else:
            self.rows["Name(s)_shown"] = json_interface["firstName"] + " " + json_interface["lastName"] + " ; " + json_interface["spouseFirstName"] + " " + json_interface["spouseLastName"]
        self.rows["Your_social_security_number"] = json_interface["ssn"]

class Authorization(Form):
    def __init__(self, json_interface, person):
        super().__init__("Authorization")
        
        #вставляем личные данные
        self.rows["Taxpayer(s)_name"] = json_interface["firstName"] + " " + json_interface["lastName"]
        self.rows["Social_security_number"] = json_interface["ssn"]
        if person.marital_status != "Single":
            self.rows["Spouse(s)_name"] = json_interface["spouseFirstName"] + " " + json_interface["spouseLastName"]
            self.rows["Spouse(s)_Social_security_number"] = json_interface["spouseSsn"]
        self.rows["Tax_Year_Ending"] = str(person.year)
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

class TaxTranscript(Form):
    def __init__(self, json_interface, person):
        if person.employee == "Employed":
            super().__init__("tax_transcript_employed")
        else:
            super().__init__("tax_transcript_se")
        if person.employee == "Employed":
            self.rows = {i:"$0.00" for i in ("Request_Date", "Filing_Status", "Response_Date", "Tracking_Number", "SSN_Provided", "Tax_Year", "Spouse_SSN", "SSN", "Name", "Address", "Cycle_Posted", "Received_Data", "Dependent_Name1", "Dependent_Name2", "Dependent_Name3", "Dependent_Name4", "Dependent_SSN1", "Dependent_SSN2", "Dependent_SSN3", "Dependent_SSN4", "PTIN", "EIN_Preparer", "Wages_Salaries_Tips", "Taxable_Interest_Income", "Tax_Except_Interest", "Ordinary_Dividents_Income", "Qualified_Dividents", "Refunds_State_Local_Taxes", "Alimony_Received", "Business_Income_Loss", "Business_Income_Loss_Per", "Capital_Gain_Loss", "Capital_Gain_Loss_Per", "Other_Gains_Losses", "Total_Ira_Distributions", "Taxable_Ira_Distributions", "Total_Pensions", "Taxable_Pension", "Additional_Income", "Additional_Income_Per", "Refundable_Credits_Per", "Refundable_Education_Credit_Per_1", "Qual_Business_Income_Deduction", "Rent_Other", "Rent_Other_Per", "Rent_Other_Income_Loss_Per", "Estate_Income_Loss_Per", "Partnership_Income_Loss_Per", "Farm_Income_Loss", "Farm_Income_Loss_Per", "Unemployment_Compensation", "Total_Social_Sec_Benefit", "Taxable_Social_Sec_Benefit", "Taxable_Social_Soc_Benefit_Per", "Other_Income", "Schedule_Eic_Se_Income_Per", "Schedule_Eic_Earned_Income_Per", "Sch_Eic_Disqual_Inc_Computer", "Excess_Child_Tax_Credit_Per", "Prim_Economic_Impact_Payment2", "Secondary_Economic_Impact_Payment2", "Prim_Advanced_CTC_Payments", "Tax_Income_Less_State_Refund_Per", "Secondary_Advanced_CTC_Payments", "Additional_CTC_Earned_Income", "Eic_Prior_Year_Earned_Income", "CTC_Prior_Year_Earned_Income", "Qual_Business_Income_Deduction_1", "F8995_Qual_Business_Income_Deduction", "Prim_Economic_Impact_Payment", "Secondary_Economic_Impact_Payment", "Scholarship_Fellowship_Grant", "Total_Income", "Total_Income_Per", "Educator_Expenses", "Eduxator_Expenses_Per", "Reservist_Expense", "Health_Savings_Acct_Deduction", "Health_Savings_Acct_Deduction_Per", "Movig_Expenses_F3903", "Keogh_Contribution_Deduction", "SE_Health_Deduction", "Early_Withdr_Savings_Penalty", "Alimony_Paid_SSN", "Alimony_Paid", "Shoclarship_Fellowship_Excluded", "Ira_Deduction", "Ira_Deduction_Per", "Student_Loan_Interest_Deduction", "Student_Loan_Interest_Deduction_Per", "Student_Loan_Interest_Deduction_Verfied", "Tuition_Deduction", "Tuition_Deduction_Per", "Other_Adjustments", "Archer_MSA_Deduction", "Archer_MSA_Deduction_Per", "Total_Adjustments_Per", "Total_Adjustments", "Adjusted_Gross_Income", "Adjusted_Gross_Income_Per", "Standart_Deduction_Per", "Add_Standart_Deduction_Per", "Tax_Table_Income_Per", "Exemption_Amount_Per", "Taxable_Income", "Taxable_Income_Per", "Total_Positive_Income_Per", "Tentative_Tax", "Tentative_Tax_Per", "Form_8814_Add_Tax_Amount", "Tax_Income_Less_Soc_Sec_Per", "Form6251_Alt_Min_Tax", "Form6251_Alt_Min_Tax_Per", "Foreign_Tax_Credit", "Foreign_Tax_Credit_Per", "Foreign_Income_Exclusion_Per", "Foreign_Income_Exclusion_Tax_Per", "Exc_Advance_Premium_Tax_Credit_Amount", "Exc_Advance_Premium_Tax_Credit_Ver_Amount", "Child_Dependent_Care_Credit", "Child_Dependent_Care_Credit_Per", "Credit_For_Elderly_And_Disabled", "Credit_For_Elderly_And_Disabled_Per", "Education_Credit", "Education_Credit_Per", "Gross_Education_Credit_Per", "Retirement_Savings_CNTRB_Credit", "Retirement_Savings_CNTRB_Credit_Per", "Prim_Ret_Sav_CNTRB", "Sec_Ret_Sav_CNTRB", "Total_Retirement_Savings_Contrib", "Residental_Energy_Credit", "Residental_Energy_Credit_Per", "Child_Dependent_Credit", "Child_Dependent_Credit_Per", "Adoption_Credit", "Adoption_Credit_Per", "Form8396_Cert_Credit", "Form8396_Cert_Credit_Per", "Total_Other_Non_Refund_Credit", "Form3800_Gen_Business_Credits", "Total_Education_Credit_Amount", "Total_Education_Credit_Per", "Form3800_Gen_Business_Credits_Per", "Prior_Min_Tax_Credit", "Prior_Min_Tax_Credit_Per", "Electric_Motor_Credit_Amount", "Electric_Motor_Credit_Amount_Per", "Alt_Motor_Credit_Amount", "Alt_Motor_Credit_Amount_Per", "Sick_Famili_Leave_Credit", "Non_Item_Char_Contr_Deduction", "Non_Item_Char_Contr_Per", "Refundable_Child_Care_Credit", "Sick_Family_Leave_Credit_3_31_21", "Refundable_Child_Care_Credit_Verified", "Recovery_Rebate_Credit", "Recovery_Rebate_Credit_Per", "Recovery_Rebate_Credit_Verified", "Other_Credits", "Total_Credits", "Total_Credits_Per", "Income_Tax_After_Credits_Per", "SE_Tax", "SE_Tax_Per", "Soc_Sec_Med_Tax_Unreported_Tips", "Soc_Sec_Med_Tax_Unreported_Tips_Per", "Tax_Qual_Plans", "Tax_Qual_Plans_Per", "Iraf_Tax_Per", "TP_Tax_Figures_Per", "IMF_Total_Tax_Credit_Per", "Total_Other_Taxes_Per", "Unpaid_Fica_Reported_Tips", "Interest_Deferred_Tax", "Total_Other_Taxes", "Recapture_Tax", "Household_Emp_Taxes", "Household_Emp_Taxes_Per", "Interest_Installment", "Add_Tax_Computer", "Refundable_Child_Care_Comp", "Health_Coverage_Recapture", "Deferred_Tax", "Max_Deferred_Tax_Per", "Total_Add_Taxes", "Total_Assessment_Per", "Total_Tax_Liability", "Total_Tax_Liability_Per", "Federal_Income_Tax_Withheld", "Sch8812_Add_Tax", "Estimated_Tax_Payments", "Other_Payment_Credit", "Refundable_Education_Credit", "Refundable_Education_Credit_Per", "Refundable_Education_Credit_Verified", "Refundable_Credit", "Earned_Income_Credit", "Earned_Income_Credit_Per", "Earned_Income_Credit_Combat_Pay", "Sch8812_Nontax_Combat_Pay", "Exc_Soc_Sec_RRTA_Tax_Withheld", "Sch8812_TOT_SS_Withheld", "Sch8812_Add_Child_Tax_Credit", "Sch8812_Add_Child_Tax_Credit_Per", "Sch8812_Add_Child_Tax_Credit_Verified", "Amount_Paid_With_Form4868", "Form2439_Regulated_Investment_Company_Credit", "Form4136_Credit_For_Tax_Fuels", "Form4136_Credit_For_Tax_Fuels_Per", "Health_Coverage_TX_CR", "Sec965_Tax_Installment", "Sec965_Tax_Liability", "Prem_Tax_Credit_Amount", "Prem_Tax_Credit_Verified_Amount", "Prim_Nap_First_Time_Home_Buyer", "Secondary_Nap_First_Time_Home_Buyer", "First_Time_Homebuyer_Credit", "Form5405_Total_Homebuyers_Credit", "Small_Employer_Health_Insur", "Small_Employer_Health_Insur2", "Total_Other_Payments_Refundable", "Total_Payments1", "Total_Payments_Per", "Refund_Amount", "F8867_Cert", "Form8888_Total_Refund_Per", "Applied_Next_Year_Est_Tax", "Est_Tax_Penalty", "Qual_Eic_Dependents", "Child_Name1", "Child_SSN1", "Year_Birth_Child1", "Child_Name2", "Child_SSN2", "Year_Birth_Child2", "Child_Name3", "Child_SSN3", "Year_Birth_Child3", "Child_Name4", "Child_SSN4", "Year_Birth_Child4", "Total_Payments", "Total_Tax", "Refund_Balance_Due")}
        else:
            self.rows = {i:"$0.00" for i in ("Request_Date", "Filing_Status", "Response_Date", "Tracking_Number", "SSN_Provided", "Tax_Year", "Spouse_SSN", "SSN", "Name", "Address", "Cycle_Posted", "Received_Data", "Dependent_Name1", "Dependent_Name2", "Dependent_Name3", "Dependent_Name4", "Dependent_SSN1", "Dependent_SSN2", "Dependent_SSN3", "Dependent_SSN4", "PTIN", "EIN_Preparer", "Wages_Salaries_Tips", "Taxable_Interest_Income", "Tax_Except_Interest", "Ordinary_Dividents_Income", "Qualified_Dividents", "Refunds_State_Local_Taxes", "Alimony_Received", "Business_Income_Loss", "Business_Income_Loss_Per", "Capital_Gain_Loss", "Capital_Gain_Loss_Per", "Other_Gains_Losses", "Total_Ira_Distributions", "Taxable_Ira_Distributions", "Total_Pensions", "Taxable_Pension", "Additional_Income", "Additional_Income_Per", "Refundable_Credits_Per", "Refundable_Education_Credit_Per_1", "Qual_Business_Income_Deduction", "Rent_Other", "Rent_Other_Per", "Rent_Other_Income_Loss_Per", "Estate_Income_Loss_Per", "Partnership_Income_Loss_Per", "Farm_Income_Loss", "Farm_Income_Loss_Per", "Unemployment_Compensation", "Total_Social_Sec_Benefit", "Taxable_Social_Sec_Benefit", "Taxable_Social_Soc_Benefit_Per", "Other_Income", "Schedule_Eic_Se_Income_Per", "Schedule_Eic_Earned_Income_Per", "Sch_Eic_Disqual_Inc_Computer", "Excess_Child_Tax_Credit_Per", "Prim_Economic_Impact_Payment2", "Secondary_Economic_Impact_Payment2", "Prim_Advanced_CTC_Payments", "Tax_Income_Less_State_Refund_Per", "Secondary_Advanced_CTC_Payments", "Additional_CTC_Earned_Income", "Eic_Prior_Year_Earned_Income", "CTC_Prior_Year_Earned_Income", "Qual_Business_Income_Deduction_1", "F8995_Qual_Business_Income_Deduction", "Prim_Economic_Impact_Payment", "Secondary_Economic_Impact_Payment", "Scholarship_Fellowship_Grant", "Total_Income", "Total_Income_Per", "SE_Tax_Deduction", "SE_Tax_Deduction_Per", "SE_Tax_Deduction_Verified", "Gross_Receipts_Or_Sales", "Gross_Receipts_Or_Sales_Per", "Net_Profit_Or_Loss", "Business_Income_Or_Loss", "Educator_Expenses", "Eduxator_Expenses_Per", "Reservist_Expense", "Health_Savings_Acct_Deduction", "Health_Savings_Acct_Deduction_Per", "Movig_Expenses_F3903", "Keogh_Contribution_Deduction", "SE_Health_Deduction", "Early_Withdr_Savings_Penalty", "Alimony_Paid_SSN", "Alimony_Paid", "Shoclarship_Fellowship_Excluded", "Ira_Deduction", "Ira_Deduction_Per", "Student_Loan_Interest_Deduction", "Student_Loan_Interest_Deduction_Per", "Student_Loan_Interest_Deduction_Verfied", "Tuition_Deduction", "Tuition_Deduction_Per", "Other_Adjustments", "Archer_MSA_Deduction", "Archer_MSA_Deduction_Per", "Total_Adjustments_Per", "Total_Adjustments", "Adjusted_Gross_Income", "Adjusted_Gross_Income_Per", "Standart_Deduction_Per", "Add_Standart_Deduction_Per", "Tax_Table_Income_Per", "Exemption_Amount_Per", "Taxable_Income", "Taxable_Income_Per", "Total_Positive_Income_Per", "Tentative_Tax", "Tentative_Tax_Per", "Form_8814_Add_Tax_Amount", "Tax_Income_Less_Soc_Sec_Per", "Form6251_Alt_Min_Tax", "Form6251_Alt_Min_Tax_Per", "Foreign_Tax_Credit", "Foreign_Tax_Credit_Per", "Foreign_Income_Exclusion_Per", "Foreign_Income_Exclusion_Tax_Per", "Exc_Advance_Premium_Tax_Credit_Amount", "Exc_Advance_Premium_Tax_Credit_Ver_Amount", "Child_Dependent_Care_Credit", "Child_Dependent_Care_Credit_Per", "Credit_For_Elderly_And_Disabled", "Credit_For_Elderly_And_Disabled_Per", "Education_Credit", "Education_Credit_Per", "Gross_Education_Credit_Per", "Retirement_Savings_CNTRB_Credit", "Retirement_Savings_CNTRB_Credit_Per", "Prim_Ret_Sav_CNTRB", "Sec_Ret_Sav_CNTRB", "Total_Retirement_Savings_Contrib", "Residental_Energy_Credit", "Residental_Energy_Credit_Per", "Child_Dependent_Credit", "Total_Education_Credit_Amount", "Total_Education_Credit_Per", "Child_Dependent_Credit_Per", "Adoption_Credit", "Adoption_Credit_Per", "Form8396_Cert_Credit", "Form8396_Cert_Credit_Per", "Total_Other_Non_Refund_Credit", "Form3800_Gen_Business_Credits", "Form3800_Gen_Business_Credits_Per", "Prior_Min_Tax_Credit", "Prior_Min_Tax_Credit_Per", "Electric_Motor_Credit_Amount", "Electric_Motor_Credit_Amount_Per", "Alt_Motor_Credit_Amount", "Alt_Motor_Credit_Amount_Per", "Sick_Famili_Leave_Credit", "Non_Item_Char_Contr_Deduction", "Non_Item_Char_Contr_Per", "Refundable_Child_Care_Credit", "Sick_Family_Leave_Credit_3_31_21", "Refundable_Child_Care_Credit_Verified", "Recovery_Rebate_Credit", "Recovery_Rebate_Credit_Per", "Recovery_Rebate_Credit_Verified", "Other_Credits", "Total_Credits", "Total_Credits_Per", "Income_Tax_After_Credits_Per", "SE_Tax", "SE_Tax_Per", "Soc_Sec_Med_Tax_Unreported_Tips", "Soc_Sec_Med_Tax_Unreported_Tips_Per", "Tax_Qual_Plans", "Tax_Qual_Plans_Per", "Iraf_Tax_Per", "TP_Tax_Figures_Per", "IMF_Total_Tax_Credit_Per", "Total_Other_Taxes_Per", "Unpaid_Fica_Reported_Tips", "Interest_Deferred_Tax", "Total_Other_Taxes", "Recapture_Tax", "Household_Emp_Taxes", "Household_Emp_Taxes_Per", "Interest_Installment", "Add_Tax_Computer", "Refundable_Child_Care_Comp", "Health_Coverage_Recapture", "Deferred_Tax", "Max_Deferred_Tax_Per", "Total_Add_Taxes", "Total_Assessment_Per", "Total_Tax_Liability", "Total_Tax_Liability_Per", "F8867_Cert", "Federal_Income_Tax_Withheld", "Sch8812_Add_Tax", "Estimated_Tax_Payments", "Other_Payment_Credit", "Refundable_Education_Credit", "Refundable_Education_Credit_Per", "Refundable_Education_Credit_Verified", "Refundable_Credit", "Earned_Income_Credit", "Earned_Income_Credit_Per", "Earned_Income_Credit_Combat_Pay", "Sch8812_Nontax_Combat_Pay", "Exc_Soc_Sec_RRTA_Tax_Withheld", "Sch8812_TOT_SS_Withheld", "Sch8812_Add_Child_Tax_Credit", "Sch8812_Add_Child_Tax_Credit_Per", "Sch8812_Add_Child_Tax_Credit_Verified", "Amount_Paid_With_Form4868", "Form2439_Regulated_Investment_Company_Credit", "Form4136_Credit_For_Tax_Fuels", "Form4136_Credit_For_Tax_Fuels_Per", "Health_Coverage_TX_CR", "Sec965_Tax_Installment", "Sec965_Tax_Liability", "Prem_Tax_Credit_Amount", "Prem_Tax_Credit_Verified_Amount", "Prim_Nap_First_Time_Home_Buyer", "Secondary_Nap_First_Time_Home_Buyer", "First_Time_Homebuyer_Credit", "Form5405_Total_Homebuyers_Credit", "Small_Employer_Health_Insur", "Small_Employer_Health_Insur2", "Total_Other_Payments_Refundable", "Total_Payments1", "Total_Payments_Per", "Refund_Amount", "Form8888_Total_Refund_Per", "Applied_Next_Year_Est_Tax", "Est_Tax_Penalty", "Total_Payments", "Total_Tax", "Refund_Balance_Due", "SE_Tax1", "Total_Add_Taxes1", "SE_Tax1", "Total_Add_Taxes1", "Alt_Min_Tax", "Alt_Min_Tax_Per", "Exc_Adv_PTC_Repayment", "Exc_Adv_PTC_Repayment_PC", "SE_Tax_Per1", "Unreported_Soc_Sec_Mediacare_Tax", "Unreported_Soc_Sec_Mediacare_Tax_PC", "Add_Tax_On_IRA_Qual_Plans", "Add_Tax_On_IRA_Qual_Plans_PC", "Household_Emp_Taxes_PC", "1st_Time_Homebuyer_Credit_Repayment", "1st_Time_Homebuyer_Credit_Repayment_PC", "Add_Mediacare_Tax", "Add_Mediacare_Tax_PC", "Net_Investment_Income_Tax", "Net_Investment_Income_Tax_PC", "Uncollected_SS_Medicare_Tax_On_Tips", "Uncollected_SS_Medicare_Tax_On_Tips_PC", "Section_965_Net_Tax_Liability", "Section_965_Net_Tax_Liability_PC", "Other_Add_Taxes", "Other_Add_Taxes_PC", "Total_Other_Taxes_PC", "Gross_Receipts_Sales1", "Returns_Allowances", "Advertising", "Car_Truck", "Contract_Labor", "Deprecation_Sec179", "Insurance", "Legal_Professional", "Office_Expense", "Rent_Lease", "Repairs_Maintenance", "Supplies", "Taxes_Licenses", "Travel", "Meals", "Utilities", "Wages", "Other_Expenses", "Net_Profit_Loss1", "Cost_Goods_Sold", "Cost_Goods_Sold_PC", "Gross_Profit", "Gross_Profit_PC", "Other_Income1", "Other_Income1_PC", "Gross_Income", "Gross_Income_PC", "Comissions_Fees", "Comissions_Fees_PC", "Depletion", "Depletion_PC", "Employee_Benefit_Programs", "Employee_Benefit_Programs_PC", "Interest_Mortgage", "Interest_Mortgage_PC", "Interest_Oher", "Interest_Other_PC", "Pension_Profit_Sharing_Plans", "Pension_Profit_Sharing_Plans_PC", "Inventory_Beginning", "Inventory_Beginning_PC", "Purchases", "Purchases_PC", "Cost_Labor", "Cost_Labor_PC", "Materials_Supplies", "Qual_Eic_Dependents", "Child_Name1", "Child_SSN1", "Year_Birth_Child1", "Child_Name2", "Child_SSN2", "Year_Birth_Child2", "Child_Name3", "Child_SSN3", "Year_Birth_Child3", "Child_Name4", "Child_SSN4", "Year_Birth_Child4", "Materials_Supplies_PC", "Other_Cost", "Other_Cost_PC", "Inventory_End", "Inventory_End_PC", "SE_Income2", "SE_Tax2", "Deferred_SE_Tax2")}
        for i in ("Request_Date", "Filing_Status", "Response_Date", "Tracking_Number", "SSN_Provided", "Tax_Year", "SSN", "Spouse_SSN", "Name", "Address", "Cycle_Posted", "Received_Date", "Dependent_Name1", "Dependent_SSN1", "Dependent_Name2", "Dependent_SSN2", "Dependent_Name3", "Dependent_SSN3", "Dependent_Name4", "Dependent_SSN4", "PTIN", "EIN_Preparer", "Alimony_Paid_SSN", "Child_Name1", "Child_SSN1", "Year_Birth_Child1", "Child_Name2", "Child_SSN2", "Year_Birth_Child2", "Child_Name3", "Child_SSN3", "Year_Birth_Child3", "Child_Name4", "Child_SSN4", "Year_Birth_Child4", "Qual_Eic_Dependents"):
            self.rows[i] = ""
        start_date = datetime(year=json_interface["year"]+1, day=random.randint(1,28), month=random.randint(1,12))
        self.rows["Request_Date"] = start_date.strftime("%m-%d-%Y")
        self.rows["Response_Date"] = start_date.strftime("%m-%d-%Y")
        self.rows["Received_Data"] = (start_date+timedelta(days=random.randint(1,10))).strftime("%b %d, %Y")
        self.rows["Tax_Year"] = str(json_interface["year"])
        self.rows["SSN"] = json_interface["ssn"]
        if person.marital_status != "Single":
            self.rows["Spouse_SSN"] = json_interface["spouseSsn"]
            self.rows["Filing_Status"] = "Married"
        else:
            self.rows["Filing_Status"] = "Single"
        self.rows["Name"] = json_interface["firstName"] + " " + json_interface["lastName"]
        self.rows["Address"] = json_interface["residentialAddress"]
        self.rows["Cycle_Posted"] = str(json_interface["year"]+1)+random.choice(('05','01','02','03','04'))+str(random.randint(19,25))
        self.rows["Tracking_Number"] = str(1040+json_interface["year"]+1-2020)+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+str(random.randint(0,9))+"XXX"
        if "dependents" in json_interface:
            for n,dependent in enumerate(json_interface["dependents"]):
                self.rows[f"Dependent_Name{n+1}"] = dependent["name"]
                self.rows[f"Dependent_SSN{n+1}"] = dependent["ssn"]
            self.rows["Dependent_Number"] = len(json_interface["dependents"])
        else:
            self.rows["Dependent_Number"] = 0
        if json_interface["preparationType"] != "Self-prepared":
            CPA_firm_serie = prepared_firm_choice(json_interface["state"])
            self.rows["PTIN"] = CPA_firm_serie["CPA FIRM PTIN"]
            self.rows["EIN_Preparer"] = CPA_firm_serie["CPA FIRM EIN"]
        self.rows["Adjusted_Gross_Income"] = person.total_income - person.adjustments
        self.rows["Adjusted_Gross_Income_Per"] = person.total_income - person.adjustments
        self.rows["Other_Income"] = person.additional_income
        self.rows["Ordinary_Dividents_Income"] = person.qualified_dividents
        self.rows["Wages_Salaries_Tips"] = person.all_wages_salaries_etc
        self.rows["Standart_Deduction_Per"] = person.standart_deduction
        self.rows["Total_Other_Taxes"] = person.self_employed_tax
        self.rows["Total_Other_Taxes_Per"] = person.self_employed_tax
        self.rows["Total_Payments"] = person.total_payments
        self.rows["Taxable_Income"] = person.taxable_income
        self.rows["Taxable_Income_Per"] = person.taxable_income
        self.rows["Total_Income"] = person.total_income
        self.rows["Total_Income_Per"] = person.total_income
        self.rows["Total_Adjustments"] = person.adjustments
        self.rows["Federal_Income_Tax_Withheld"] = person.federal_tax_withheld
        self.rows["Tentative_Tax"] = person.total_tax - person.federal_tax_withheld
        self.rows["Tentative_Tax_Per"] = person.total_tax - person.federal_tax_withheld
        self.rows["Total_Adjustments_Per"] = person.adjustments
        self.rows["Total_Payments1"] = person.total_payments
        self.rows["Total_Payments_Per"] = person.total_payments
        self.rows["Total_Tax"] = person.total_tax
        self.rows["Total_Tax_Liability"] = person.total_tax
        self.rows["Total_Tax_Liability_Per"] = person.total_tax
        self.rows["Income_Tax_After_Credits_Per"] = get_tax(person.year, person.marital_status, person.taxable_income)
        if json_interface["refundOrPayment"] == "TAX_REFUND":
            self.rows["Refund_Balance_Due"] = "REFUND,"+str(person.balance)
        else:
            self.rows["Refund_Balance_Due"] = "BALANCE DUE,"+str(-person.balance)
        if person.employee != "Employed":
            self.rows["Gross_Receipts_Or_Sales"] = person.se_info["1"]
            self.rows["Gross_Receipts_Or_Sales_Per"] = person.se_info["1"]
            self.rows["Gross_Receipts_Sales1"] = person.se_info["1"]
            self.rows["Business_Income_Or_Loss"] = person.additional_income
            self.rows["SE_Tax_Deduction"] = person.adjustments
            self.rows["SE_Tax_Deduction_Per"] = person.adjustments
            self.rows["SE_Tax_Deduction_Verified"] = person.adjustments
            self.rows["SE_Tax1"] = person.self_employed_tax
            self.rows["SE_Tax_Per1"] = person.self_employed_tax
            self.rows["Gross_Receipts_Sales1"] = person.se_info["7"]
            self.rows["Returns_Allowances"] = person.se_info["2"]
            self.rows["Advertising"] = person.se_info["8"]
            self.rows["Car_Truck"] = person.se_info["9"]
            self.rows["Contract_Labor"] = person.se_info["11"]
            self.rows["Insurance"] = person.se_info["15"]
            self.rows["Legal_Professional"] = person.se_info["17"]
            self.rows["Office_Expense"] = person.se_info["18"]
            self.rows["Rent_Lease"] = person.se_info["20a"]
            #self.rows["Repairs_Maintenance"] = person.se_info["21"]
            #self.rows["Supplies"] = person.se_info["22"]
            self.rows["Taxes_Licenses"] = person.se_info["23"]
            self.rows["Travel"] = person.se_info["24a"]
            self.rows["Utilities"] = person.se_info["25"]
            self.rows["Net_Profit_Loss1"] = person.se_info["31"]
            self.rows["Legal_Professional"] = person.se_info["17"]
            self.rows["Cost_Goods_Sold"] = person.se_info["4"]
            self.rows["Cost_Goods_Sold_PC"] = person.se_info["4"]
            #self.rows["Other_Income1"] = person.se_info["6"]
            #self.rows["Other_Income1_PC"] = person.se_info["6"]
            self.rows["Gross_Income"] = person.se_info["7"]
            self.rows["Gross_Income_PC"] = person.se_info["7"]
            self.rows["Inventory_Beginning"] = person.se_info["35"]
            self.rows["Inventory_Beginning_PC"] = person.se_info["35"]
            self.rows["Cost_Labor"] = person.se_info["37"]
            self.rows["Cost_Labor_PC"] = person.se_info["37"]
            self.rows["Materials_Supplies"] = person.se_info["38"]
            self.rows["Materials_Supplies_PC"] = person.se_info["38"]
            self.rows["Other_Cost"] = person.se_info["39"]
            self.rows["Other_Cost_PC"] = person.se_info["39"]
            self.rows["Inventory_End"] = person.se_info["41"]
            self.rows["Inventory_End_PC"] = person.se_info["41"]
            self.rows["Cost_Goods_Sold"] = person.se_info["42"]
            self.rows["Cost_Goods_Sold_PC"] = person.se_info["42"]
            self.rows["SE_Income2"] = person.additional_income
            self.rows["SE_Tax2"] = person.self_employed_tax
        self.rows["Children_Number"] = 0
        if "dependents" in json_interface:
            for n,dependent in enumerate(json_interface["dependents"]):
                if ("son" in dependent["relation"].lower()) or ("daughter" in dependent["relation"].lower()):
                    self.rows[f"Child_Name{n+1}"] = dependent["name"]
                    self.rows[f"Child_SSN{n+1}"] = dependent["ssn"]
                    self.rows["Children_Number"] += 1