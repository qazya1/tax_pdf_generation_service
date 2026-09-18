from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import uuid
import os
from create_pdf import main_tax_return
import re
import json
import mysql.connector as mysql_con
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки, в продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Разрешить все заголовки
)

with open('config.json', 'r', encoding='utf-8') as config_file:
    config_json = json.load(config_file)
    DATABASE_NAME = config_json["databaseName"]
    USER = config_json["user"]
    PASSWORD = config_json["password"]

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("interface.html", "r", encoding="utf-8") as html_file:
        html_content = html_file.read()
    return HTMLResponse(content=html_content, status_code=200)

def preparing_json(json_):
    all_fields = ["firstName", "lastName", "maritalStatus", "spouseFirstName", "spouseLastName", "residentialAddress", "town", "state", "zipCode", "ssn", "spouseSsn", "occupation", "spouseOccupation", "employmentType", "principalBusiness", "ein", "naicsCode", "businessName", "businessAddress", "businessTown", "businessState", "businessZip", "year", "grossIncomeAmount", "refundOrPayment", "refundAmount", "bankAccountNumber", "bankRoutingNumber", "taxesDueAmount", "preparationType", "dependents", "signature", "spouseSignature"]
    for field in json_.copy():
        if not(field in all_fields):    #удаляем ненужные поля
            json_.pop(field)
        elif not(json_[field]):
            json_.pop(field)
    return json_

def check_json_is_valid(json_):
    try:
        required_fields = ["firstName", "lastName", "maritalStatus", "residentialAddress", "town", "state", "zipCode", "ssn", "occupation", "employmentType", "year", "grossIncomeAmount", "refundOrPayment", "preparationType"]
        for field in required_fields:
            if not(field in json_):
                return False
        if json_["maritalStatus"] != "MarriedFilingJointly" and json_["maritalStatus"] != "Single":
            return False
        if not(re.fullmatch(r"\d{5}", json_["zipCode"])) and not(re.fullmatch(r"\d{5}-\d{4}", json_["zipCode"])):
            return False
        if not(re.fullmatch(r"\d{9}", json_["ssn"])):
            return False
        if json_["employmentType"] != "Sole Prop. / Self-employed" and json_["employmentType"] != "Employed":
            return False
        if not(2022 <= json_["year"] <= 2025):
            return False
        if json_["grossIncomeAmount"] < 0:
            return False
        if json_["refundOrPayment"] != "TAX_REFUND" and json_["refundOrPayment"] != "TAX_DUE":
            return False
        
        if json_["maritalStatus"] == "MarriedFilingJointly":
            required_fields = ["spouseFirstName", "spouseLastName", "spouseSsn", "spouseOccupation", "spouseSignature"]
            for field in required_fields:
                if not(field in json_):
                    return False
            if not(re.fullmatch(r"\d{9}", json_["spouseSsn"])):
                return False
        
        if json_["employmentType"] == "Sole Prop. / Self-employed":
            required_fields = ["principalBusiness", "naicsCode"]
            for field in required_fields:
                if not(field in json_):
                    return False
            if ("ein" in json_) and not(re.fullmatch(r"\d{2}-\d{7}", json_["ein"])):
                return False
            if not(re.fullmatch(r"\d{6}", json_["naicsCode"])):
                return False
        if ("businessZip" in json_) and (not(re.fullmatch(r"\d{5}", json_["businessZip"]) or re.fullmatch(r"\d{5}-\d{4}", json_["businessZip"]))):
            return False
        
        if json_["refundOrPayment"] == "TAX_REFUND":
            required_fields = ["refundAmount", "bankAccountNumber", "bankRoutingNumber"]
            for field in required_fields:
                if not(field in json_):
                    return False
            if json_["refundAmount"] < 0:
                return False
            if not(re.fullmatch(r"\d{,17}", json_["bankAccountNumber"])):
                return False
            if not(re.fullmatch(r"\d{,9}", json_["bankRoutingNumber"])):
                return False
        else:
            if not("taxesDueAmount" in json_):
                return False
            elif json_["taxesDueAmount"] < 0:
                return False
        if "dependents" in json_:
            if len(json_["dependents"]) > 4:
                return False
            else:
                for dependent in json_["dependents"]:
                    required_fields = ["name", "ssn", "relation"]
                    for field in required_fields:
                        if not(field in dependent):
                            return False
                    if not(re.fullmatch(r"\d{9}", dependent["ssn"])):
                        return False
        return True
    except BaseException:
        return False

def init_db():
    conn = mysql_con.connect(user=USER, database=DATABASE_NAME, passwd=PASSWORD)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id CHAR(36) PRIMARY KEY,
            filePathName VARCHAR(100) NOT NULL UNIQUE,
            transcriptPathName VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            taxYear INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            maritalStatus BOOL NOT NULL,
            spouseName VARCHAR(100),
            SSN CHAR(11) NOT NULL,
            spouseSSN CHAR(11),
            refundOrOwed BOOL NOT NULL,
            refundAmount FLOAT,
            owedAmount FLOAT,
            dependent1Name VARCHAR(100),
            dependent2Name VARCHAR(100),
            dependent3Name VARCHAR(100),
            dependent4Name VARCHAR(100),
            preparerFirmName VARCHAR(50),
            preparerFirmAddress VARCHAR(100),
            preparerFirmEIN CHAR(10),
            preparerFirmPTIN CHAR(9)
        )
    """)
    #maritalStatus = True - в браке
    #refundOrOwed = True - refund
    conn.commit()
    conn.close()

def insert_to_db(file_id, file_path, transcript_path, json_interface, preparerFirmName=None, preparerFirmAddress=None, preparerFirmEIN=None, preparerFirmPTIN=None):
    conn = mysql_con.connect(user=USER, database=DATABASE_NAME, passwd=PASSWORD)
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO files (
                            id,
                            filePathName,
                            transcriptPathName,
                            taxYear,
                            name,
                            maritalStatus,
                            spouseName,
                            SSN,
                            spouseSSN,
                            refundOrOwed,
                            refundAmount,
                            owedAmount,
                            dependent1Name,
                            dependent2Name,
                            dependent3Name,
                            dependent4Name,
                            preparerFirmName,
                            preparerFirmAddress,
                            preparerFirmEIN,
                            preparerFirmPTIN
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
        (
        file_id,
        file_path,
        transcript_path,
        json_interface["year"],
        json_interface["firstName"]+ " " +json_interface["lastName"],
        True if json_interface["maritalStatus"] == "MarriedFilingJointly" else False,
        json_interface["spouseFirstName"]+ " " +json_interface["spouseLastName"] if json_interface["maritalStatus"] == "MarriedFilingJointly" else None,
        f'{json_interface["ssn"][:3]}-{json_interface["ssn"][3:5]}-{json_interface["ssn"][5:]}',
        f'{json_interface["spouseSsn"][:3]}-{json_interface["spouseSsn"][3:5]}-{json_interface["spouseSsn"][5:]}' if json_interface["maritalStatus"] == "MarriedFilingJointly" else None,
        True if json_interface["refundOrPayment"] == "TAX_REFUND" else False,
        json_interface["refundAmount"] if json_interface["refundOrPayment"] == "TAX_REFUND" else None,
        json_interface["taxesDueAmount"] if json_interface["refundOrPayment"] == "TAX_DUE" else None,
        json_interface["dependents"][0]["name"] if ("dependents" in json_interface) and len(json_interface["dependents"]) > 0 else None,
        json_interface["dependents"][1]["name"] if ("dependents" in json_interface) and len(json_interface["dependents"]) > 1 else None,
        json_interface["dependents"][2]["name"] if ("dependents" in json_interface) and len(json_interface["dependents"]) > 2 else None,
        json_interface["dependents"][3]["name"] if ("dependents" in json_interface) and len(json_interface["dependents"]) > 3 else None,
        preparerFirmName,
        preparerFirmAddress,
        preparerFirmEIN,
        preparerFirmPTIN
        )
    )
    conn.commit()
    conn.close()

init_db()

UPLOAD_FOLDER = "generated_files"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "transcripts"), exist_ok=True)

@app.post("/generate-file")
async def generate_file(json_interface: Dict):
    try:
        json_interface = preparing_json(json_interface)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if not(check_json_is_valid(json_interface)):
        raise HTTPException(status_code=400, detail="Incorrect JSON data")
        
    try:
        # Генерируем уникальный ID для файла
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}_{json_interface['lastName']}.pdf"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        transcript_path = os.path.join(UPLOAD_FOLDER, "transcripts", f"{file_id}_{json_interface['lastName']}_transcript.pdf")
        
        # Вызываем функцию генерации PDF и получаем информацию о подготовившей фирме
        firm_info = main_tax_return(json_interface, file_path, transcript_path)
        
        # Сохраняем информацию в базу данных
        try:
            insert_to_db(file_id, file_path, transcript_path, json_interface, firm_info["CPA FIRM NAME"], firm_info["CPA FIRM ADDRESS"] + ", " + firm_info["CPA FIRM TOWN"] + ", " + firm_info["CPA FIRM STATE"] + " " +firm_info["CPA FIRM ZIP CODE"], firm_info["CPA FIRM EIN"], firm_info["CPA FIRM PTIN"])
        except TypeError:
            insert_to_db(file_id, file_path, transcript_path, json_interface)
        
        # Возвращаем ID файла и ссылку для скачивания
        return {
            "fileId": file_id,
            "downloadLink": f"/download/{file_id}",
            "transcriptLink": f"/download/transcript/{file_id}",
            "status": "success"
        }
    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    conn = mysql_con.connect(user=USER, database=DATABASE_NAME, passwd=PASSWORD)
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT filePathName FROM files WHERE id = %s", (file_id,))
    file_path = None
    
    for i in cursor:
        file_path = i[0]
    
    conn.close()
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(file_path, filename="form_1040.pdf")

@app.get("/download/transcript/{file_id}")
async def download_transcipt_file(file_id: str):
    conn = mysql_con.connect(user=USER, database=DATABASE_NAME, passwd=PASSWORD)
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT transcriptPathName FROM files WHERE id = %s", (file_id,))
    file_path = None
    
    for i in cursor:
        file_path = i[0]
    
    print(file_path)
    conn.close()
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(file_path, filename="tax_transcript.pdf")

@app.get("/info/{file_id}")
async def file_info(file_id: str):
    conn = mysql_con.connect(user=USER, database=DATABASE_NAME, passwd=PASSWORD)
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT taxYear, name, maritalStatus, spouseName, SSN, spouseSSN, refundOrOwed, refundAmount, owedAmount, dependent1Name, dependent2Name, dependent3Name, dependent4Name, preparerFirmName, preparerFirmAddress, preparerFirmEIN, preparerFirmPTIN FROM files WHERE id = %s", (file_id,))
    need_row = None
    
    for i in cursor:
        need_row = i
    
    conn.close()
    
    if not need_row:
        raise HTTPException(status_code=404, detail="File not found")
    
    json_ans = {field:need_row[n] for n, field in enumerate(["taxYear", "name", "maritalStatus", "spouseName", "SSN", "spouseSSN", "refundOrOwed", "refundAmount", "owedAmount", "dependent1Name", "dependent2Name", "dependent3Name", "dependent4Name", "preparerFirmName", "preparerFirmAddress", "preparerFirmEIN", "preparerFirmPTIN"])}
    if json_ans["maritalStatus"]:
        json_ans["maritalStatus"] = "Married, filling jointly"
    else:
        json_ans["maritalStatus"] = "Single"
    if json_ans["refundOrOwed"]:
        json_ans["refundOrOwed"] = "I want to claim a refund"
    else:
        json_ans["refundOrOwed"] = "I want to pay taxes due"
    
    return json_ans

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)