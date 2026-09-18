from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import uuid
import os
from create_pdf import main_tax_return
import re
import json
from fast_api_models import TaxReturnRequest
from fastapi.middleware.cors import CORSMiddleware
import logging

app = FastAPI()

# Добавьте это после создания app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Для разработки, в продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Разрешить все заголовки
)

UPLOAD_FOLDER = "./generated_files"
os.makedirs("./logs", exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER+"/transcripts", exist_ok=True)
os.makedirs(UPLOAD_FOLDER+"/personal", exist_ok=True)

HOST = "127.0.0.1"
PORT = 8000

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("interface.html", "r", encoding="utf-8") as html_file:
        html_content = html_file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/generate-file", response_model=dict)
async def generate_file(req_body: TaxReturnRequest):
        
    try:
        # Генерируем уникальный ID для файлов
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}_{req_body.company_name}.pdf"
        transcript_name = f"{file_id}_{req_body.company_name}_transcript.pdf"
        
        # Вызываем функцию генерации PDF и получаем все файлы
        resp = main_tax_return(req_body, file_name, transcript_name, UPLOAD_FOLDER, os.path.join(UPLOAD_FOLDER, "transcripts"), os.path.join(UPLOAD_FOLDER, "personal"))
        
        # Возвращаем ID файла и ссылку для скачивания
        return resp
    except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))

@app.options("/generate-file")
async def options_submit():
    return {"message": "OK"}

@app.get("/file/{file_path:path}")
async def download_file(file_path: str):
    print(file_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
