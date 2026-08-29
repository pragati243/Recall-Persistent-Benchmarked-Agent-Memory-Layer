from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_path: str = "./.data/qdrant"
    qdrant_collection: str = "memories"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "recall-dev-password"

    anthropic_api_key: str = ""
    extraction_model: str = "claude-haiku-4-5-20251001"
    agent_model: str = "claude-sonnet-5"

    postgres_dsn: str = "postgresql://recall:recall-dev-password@localhost:5432/recall"


settings = Settings()
