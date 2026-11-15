from src.app import get_app
from src.core import settings


def main(
    app_url: str = "main:app",
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool | None = None,
):
    import uvicorn

    should_reload = settings.debug if reload is None else reload
    uvicorn.run(app=app_url, host=host, port=port, reload=should_reload)


app = get_app(settings=settings)

if __name__ == "__main__":
    main()
