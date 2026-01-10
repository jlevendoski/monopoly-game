"""
Server configuration loaded from environment variables.

No .env file dependency - use system environment variables or CLI arguments.
For systemd services, set Environment= directives in the service file.
"""
import os
from pathlib import Path


class Config:
    """Server configuration."""
    
    # Server settings
    HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("SERVER_PORT", "8765"))
    SECRET_KEY: str = os.getenv("SERVER_SECRET_KEY", "change-me-in-production")
    
    # Database
    DATABASE_PATH: Path = Path(os.getenv("DATABASE_PATH", "./data/monopoly.db"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Game settings
    MIN_PLAYERS: int = 2
    MAX_PLAYERS: int = 4
    TURN_TIMEOUT: int = 300  # 5 minutes per turn
    
    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        cls.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_args(cls, host: str = None, port: int = None, db_path: str = None) -> 'Config':
        """
        Create config with CLI overrides.
        
        CLI args > Environment variables > Defaults
        """
        if host:
            cls.HOST = host
        if port:
            cls.PORT = port
        if db_path:
            cls.DATABASE_PATH = Path(db_path)
        return cls


config = Config()
settings = config  # Alias for backward compatibility
