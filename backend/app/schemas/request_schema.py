from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    log_type: str
    log_text: str

