from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_path: str = "./.data/qdrant"
    qdrant_collection: str = "memories"
    embedding_model: str = "BAAI/bge-small-en-v1.5"


settings = Settings()
