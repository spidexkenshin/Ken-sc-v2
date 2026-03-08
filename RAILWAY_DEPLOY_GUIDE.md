# 🚀 Deploying Your Anime Scraper Bot to Railway

Follow these steps to deploy your bot on Railway using GitHub.

## 1. Prepare Your GitHub Repository
1. Create a new **private** repository on GitHub.
2. Upload all the files from the `anime_scraper_bot` folder to your repository.
3. Ensure you have `requirements.txt`, `main.py`, `config.py`, `database.py`, and `scrapers.py`.

## 2. Set Up Railway
1. Go to [Railway.app](https://railway.app/) and log in with your GitHub account.
2. Click on **"New Project"** and select **"Deploy from GitHub repo"**.
3. Choose your bot's repository.
4. Click **"Deploy Now"**.

## 3. Add Environment Variables
In your Railway project, go to the **Variables** tab and add the following:

| Variable | Value |
| :--- | :--- |
| `API_ID` | `37407868` |
| `API_HASH` | `d7d3bff9f7cf9f3b111129bdbd13a065` |
| `BOT_TOKEN` | `8562237682:AAEJCVtlLNFuteUUTnTphORPKHwRPweiHcY` |
| `MONGO_URI` | `mongodb+srv://iamnotmohit1_db_user:iammohitgurjar.1@kenshindb.esj4x5f.mongodb.net/?appName=KENSHINDB` |
| `ADMINS` | `6728678197` |

## 4. Deployment Command
Railway should automatically detect the `requirements.txt` and start the bot. If it asks for a start command, use:
```bash
python3 main.py
```

## 5. Bot Commands
Once the bot is live, you can use these commands:
- `/start` - Start the bot
- `/help` - Show help menu
- `/search <anime>` - Search for anime
- `/setcaption <text>` - Set custom caption
- `/setthumbnail` - Set custom thumbnail (send with photo)
- `/setfilename <name>` - Set custom filename format
- `/addadmin <user_id>` - Add a new admin
- `/deladmin <user_id>` - Remove an admin
- `/admins` - List all admins

---
**Note:** The bot uses `pyrofork` as requested for the caption and other features.
