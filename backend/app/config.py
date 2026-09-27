from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[1] / '.env', extra='ignore')
    app_mode: Literal['local', 'live'] = 'local'
    cors_origins: list[str] = ['http://localhost:5173', 'http://127.0.0.1:5173']
    uploads_enabled: bool = True
    deletes_enabled: bool = True
    demo_access_token: str = ''
    supabase_url: str = ''
    supabase_service_role_key: str = ''
    openai_api_key: str = ''
    openai_base_url: str = ''
    storage_bucket: str = 'research-pdfs'
    embedding_model: str = 'text-embedding-3-small'
    answer_model: str = 'gpt-4.1-mini'
    answer_provider: Literal['local', 'openai'] = 'local'
    embedding_dimensions: int = 1536
    max_file_mb: int = Field(default=10, ge=1, le=20)
    max_documents: int = Field(default=30, ge=1, le=100)
    max_pages: int = Field(default=150, ge=1, le=300)
    requests_per_minute: int = 60
    questions_per_minute: int = 10
    uploads_per_hour: int = 10
    similarity_threshold: float = Field(default=0.3, ge=0, le=1)
    local_data_dir: Path = Path('.local-data')

    @model_validator(mode='after')
    def validate_live_settings(self):
        if '*' in self.cors_origins:
            raise ValueError('Set exact CORS origins; wildcard access is not supported.')
        if self.app_mode == 'live':
            if not all([self.supabase_url, self.supabase_service_role_key, self.openai_api_key]):
                raise ValueError('Live mode requires Supabase URL, service role key, and OpenAI key.')
            if not self.supabase_url.startswith('https://'):
                raise ValueError('Supabase URL must use HTTPS.')
            if self.embedding_dimensions != 1536:
                raise ValueError('The current database migration requires 1536 dimensions.')
            if (self.uploads_enabled or self.deletes_enabled) and len(self.demo_access_token) < 24:
                raise ValueError('Live uploads/deletes require a shared access token of at least 24 characters.')
        return self
