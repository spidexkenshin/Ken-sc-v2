import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.getenv("API_ID", "37407868"))
    API_HASH = os.getenv("API_HASH", "d7d3bff9f7cf9f3b111129bdbd13a065")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8562237682:AAEJCVtlLNFuteUUTnTphORPKHwRPweiHcY")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://iamnotmohit1_db_user:iammohitgurjar.1@kenshindb.esj4x5f.mongodb.net/?appName=KENSHINDB")
    ADMINS = [int(x) for x in os.getenv("ADMINS", "6728678197").split(",")]
    DATABASE_NAME = "AnimeScraperBot"
