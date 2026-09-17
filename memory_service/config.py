from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_path: str = "./.data/qdrant"
    qdrant_url: str = "http://localhost:6333"  # Docker Compose's host-facing Qdrant endpoint
    qdrant_collection: str = "memories"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "recall-dev-password"

    groq_api_key: str = ""
    # Groq recommends GPT-OSS 120B for workloads previously using Llama 3.3 70B.
    extraction_model: str = "openai/gpt-oss-120b"
    agent_model: str = "openai/gpt-oss-120b"

    postgres_dsn: str = "postgresql://recall:recall-dev-password@localhost:55432/recall"


settings = Settings()
