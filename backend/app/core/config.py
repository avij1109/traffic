from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "SIH 2026 Intelligent Traffic Surveillance Platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./traffic_surveillance.db"
    CORS_ORIGINS: List[str] = ["*"]
    
    # Simulation settings
    SIMULATOR_AUTO_START: bool = True
    SIMULATOR_FLEET_SIZE: int = 50
    SIMULATOR_SPEED_MULTIPLIER: float = 2.0

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
