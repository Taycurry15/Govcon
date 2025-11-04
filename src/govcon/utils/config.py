"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    postgres_url: str = "postgresql://bronze:password@localhost:5432/govcon"

    # Cache & Vector Store
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Object Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "bronze"
    minio_secret_key: str = "bronze_secret"
    minio_bucket: str = "govcon-artifacts"
    minio_secure: bool = False

    # AI Models
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7

    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    default_llm_provider: str = "openai"
    discovery_agent_llm_provider: Optional[str] = None
    discovery_agent_llm_model: Optional[str] = None
    bid_nobid_agent_llm_provider: Optional[str] = None
    bid_nobid_agent_llm_model: Optional[str] = None
    communications_agent_llm_provider: Optional[str] = None
    communications_agent_llm_model: Optional[str] = None
    solicitation_review_agent_llm_provider: Optional[str] = None
    solicitation_review_agent_llm_model: Optional[str] = None
    proposal_generation_agent_llm_provider: Optional[str] = None
    proposal_generation_agent_llm_model: Optional[str] = None
    pricing_agent_llm_provider: Optional[str] = None
    pricing_agent_llm_model: Optional[str] = None
    orchestrator_llm_provider: Optional[str] = None
    orchestrator_llm_model: Optional[str] = None

    # Company Configuration
    company_name: str = "The Bronze Shield"
    company_uei: str = "<your-uei-here>"
    company_cage: str = "<your-cage-here>"

    set_aside_prefs: list[str] = ["SDVOSBC", "VOSB", "SBA", "WOSB", "8A"]
    allowed_naics: list[str] = [
        "541512",
        "541511",
        "541519",
        "541513",
        "541690",
        "541611",
        "541930",
        "561410",
        "518210",
        "541990",
    ]
    allowed_psc: list[str] = [
        "D301",
        "D302",
        "D307",
        "D308",
        "D310",
        "D314",
        "D316",
        "D318",
        "D399",
        "R408",
        "R410",
        "R413",
        "R420",
        "R499",
        "R699",
        "R608",
        "U012",
        "U099",
    ]

    # Discovery Settings
    sam_gov_api_key: Optional[str] = None
    sam_gov_base_url: str = "https://api.sam.gov"
    discovery_days_back: int = 30
    discovery_min_value: float = 25000
    discovery_max_value: float = 10000000

    discovery_sources: list[str] = ["sam_gov", "neco"]
    discovery_keywords: list[str] = [
        "Zero Trust",
        "ICAM",
        "RMF",
        "CMMC",
        "SOC2",
        "ISO 27001",
        "cybersecurity",
        "data management",
        "translation",
        "interpretation",
        "ASL",
        "transcription",
        "IT services",
        "help desk",
        "PMO",
    ]
    target_agencies: list[str] = ["VA", "DoD", "DHS", "HHS", "DOJ", "USDA"]

    # Bid/No-Bid Scoring
    bid_nobid_auto_threshold: float = 75.0
    bid_nobid_require_approval: bool = True

    score_weight_set_aside: int = 25
    score_weight_scope: int = 25
    score_weight_timeline: int = 15
    score_weight_competition: int = 10
    score_weight_staffing: int = 10
    score_weight_pricing: int = 10
    score_weight_strategic: int = 5

    # Pricing
    bls_api_key: Optional[str] = None
    bls_base_url: str = "https://api.bls.gov/publicAPI/v2"
    gsa_calc_base_url: str = "https://api.gsa.gov/acquisition/calc"

    default_fringe_rate: float = 30.0
    default_overhead_rate: float = 15.0
    default_ga_rate: float = 10.0
    default_fee_rate: float = 8.0

    # NECO (Navy Electronic Commerce Online)
    neco_base_url: str = "https://www.neco.navy.mil"
    neco_verify_ssl: bool = False
    neco_timeout: float = 30.0
    neco_max_pages: int = 3
    neco_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )

    # Security
    auth_issuer: str = "https://accounts.bronzeshield.com/"
    auth_audience: str = "govcon-api"
    jwt_signing_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    session_secret_key: str = "change_me"
    encryption_key: str = "change_me"

    # Audit & Compliance
    audit_log_enabled: bool = True
    audit_log_level: str = "INFO"
    audit_retention_days: int = 2555

    cmmc_level: int = 2
    nist_800_171_compliant: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = False
    api_log_level: str = "info"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "./logs/govcon.log"

    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"

    # Workflow
    require_pink_team_approval: bool = True
    require_gold_team_approval: bool = True
    pink_team_max_attempts: int = 3
    gold_team_max_attempts: int = 3

    # Development
    debug: bool = False
    testing: bool = False
    agent_tracing_enabled: bool = True
    agent_tracing_processor: str = "console"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
