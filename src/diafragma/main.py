from fastapi import FastAPI

from diafragma.routes.auth.router import router as auth_roter
from diafragma.routes.products.router import router as products_router

app = FastAPI()

app.include_router(products_router)
app.include_router(auth_roter)
