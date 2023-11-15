from pyrogram import Client
import config, asyncio


user_client = Client("pyrogram", phone_number=config.PHONE_NUMBER, api_id=config.API_ID, api_hash=config.API_HASH)

async def main():
    await user_client.start()
    me = await user_client.get_me()
    print(f"{me.first_name} {me.last_name}")

if __name__ == '__main__':
    asyncio.run(main())