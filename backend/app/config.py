from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8002

    qbit_base: str = "http://localhost:8080/api/v2"
    qbit_user: str = ""
    qbit_pass: str = ""

    jellyfin_base: str = "http://localhost:8096"
    jellyfin_api_key: str = ""

    media_path: str = "/data/media"
    file_home: str = ""
    weather_city: str = ""

    tmdb_api_key: str = ""
    tmdb_base: str = "https://api.themoviedb.org/3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
