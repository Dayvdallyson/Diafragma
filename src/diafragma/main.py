from fastapi import FastAPI
from diafragma.routes.products.router import router as products_router

app = FastAPI()

app.include_router(products_router)
