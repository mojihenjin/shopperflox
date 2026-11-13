from fastapi import FastAPI


def create_app():
    return FastAPI()


def configurate_app(app: FastAPI):

    return app


def get_app():
    return configurate_app(app=create_app())
