from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.client[Config.DATABASE_NAME]
        self.users = self.db.users
        self.settings = self.db.settings
        self.admins = self.db.admins

    async def add_admin(self, user_id):
        if not await self.is_admin(user_id):
            await self.admins.insert_one({"user_id": user_id})

    async def remove_admin(self, user_id):
        await self.admins.delete_one({"user_id": user_id})

    async def get_admins(self):
        admins = await self.admins.find().to_list(length=100)
        return [admin["user_id"] for admin in admins] + Config.ADMINS

    async def is_admin(self, user_id):
        if user_id in Config.ADMINS:
            return True
        admin = await self.admins.find_one({"user_id": user_id})
        return admin is not None

    async def set_setting(self, key, value):
        await self.settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

    async def get_setting(self, key, default=None):
        setting = await self.settings.find_one({"key": key})
        return setting["value"] if setting else default

db = Database()
