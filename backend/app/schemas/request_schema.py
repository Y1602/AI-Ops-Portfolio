from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    log_type: str
    log_text: str


class IngestLogRequest(BaseModel):
    source: str = Field(..., min_length=1, description="日志来源，例如 docker-host-01")
    service_name: str = Field(..., min_length=1, description="服务名称，例如 nginx")
    log_type: str = Field(..., min_length=1, description="日志类型")
    env: str = Field("dev", description="环境名称，例如 dev、test、prod")
    log_text: str = Field(..., min_length=1, description="多行日志内容")
