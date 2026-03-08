import os
import shutil
import pandas as pd
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel

from etl.adapters import IfindAdapter, TongdaxinAdapter, GenericFinancialAdapter
from nlp.deepseek_client import DeepSeek_LLM_Client
from business.matching_engine import MatchingEngine

app = FastAPI(title="Backend API System")

# Ensure required directories exist
os.makedirs("./data/inputs", exist_ok=True)
os.makedirs("./data/processed", exist_ok=True)

class FetchRequest(BaseModel):
    source: str
    company_code: str

class NlpAnalyzeRequest(BaseModel):
    text: str

@app.post("/api/v1/etl/fetch")
async def fetch_etl_data(request: FetchRequest):
    """
    异步调度现有的 FinancialDataAdapter 拉取与清洗数据。
    """
    try:
        source_lower = request.source.lower()
        if source_lower == "ifind":
            adapter = IfindAdapter()
        elif source_lower == "tongdaxin":
            adapter = TongdaxinAdapter()
        elif source_lower == "generic":
            adapter = GenericFinancialAdapter()
        else:
            raise HTTPException(status_code=400, detail="Invalid data source. Choose from: iFinD, Tongdaxin, Generic")

        # In a real async environment we would use run_in_threadpool if these are blocking.
        # But for this scope, a synchronous call within the async route works for the mocked data.
        df = adapter.get_standardized_10yr_financials(request.company_code)

        # Convert pandas DataFrame to records format for JSON response
        records = df.to_dict(orient="records")
        return {"status": "success", "company_code": request.company_code, "data": records}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/nlp/analyze")
async def analyze_nlp(request: NlpAnalyzeRequest, x_api_key: Optional[str] = Header(None)):
    """
    异步封装 DeepSeek_LLM_Client，提供文本结构化服务。
    """
    try:
        # If API key is provided via header, set it in the environment temporarily
        # or instantiate the client with it. For simplicity, we temporarily set the env var.
        original_key = os.environ.get("DEEPSEEK_API_KEY")
        if x_api_key:
            os.environ["DEEPSEEK_API_KEY"] = x_api_key

        client = DeepSeek_LLM_Client()
        result = client.analyze_document(request.text)

        # Restore the original key
        if original_key is not None:
             os.environ["DEEPSEEK_API_KEY"] = original_key
        elif "DEEPSEEK_API_KEY" in os.environ:
             del os.environ["DEEPSEEK_API_KEY"]

        return {"status": "success", "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/business/match")
async def match_business(file: UploadFile = File(...)):
    """
    接收前端上传的承载地禀赋数据结构（Excel），调用 MatchingEngine 运算并返回排序后的 JSON 结果矩阵。
    """
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are supported")

    # Sanitize filename using uuid to prevent path traversal
    safe_filename = f"{uuid.uuid4()}.xlsx"
    temp_file_path = f"./data/inputs/{safe_filename}"

    try:
        # Save uploaded file
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process matching
        engine = MatchingEngine(input_dir="./data/inputs", processed_dir="./data/processed")

        # The processing engine method will handle parsing and the matrix dot product score
        results_df = engine.process_file(temp_file_path)

        # Move processed file
        os.rename(temp_file_path, os.path.join("./data/processed", safe_filename))

        return {
            "status": "success",
            "matches": results_df.to_dict(orient="records")
        }

    except Exception as e:
        # Clean up on failure if necessary
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)