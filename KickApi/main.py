import uvicorn
from app.main import app
from app.core.config import Config


if __name__ == "__main__":
    uvicorn.run(app, host=Config.HOST, port=Config.PORT)
