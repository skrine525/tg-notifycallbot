import config, asyncio, pyrogram
from pyrogram import Client
from botlib.db.engine import Session
from botlib.db.model import ListeningChannel, NotifiedUser, User
from botlib.call import calls


user_client = Client("pyrogram", phone_number=config.PHONE_NUMBER, api_id=config.API_ID, api_hash=config.API_HASH)

async def discard_call_and_call_next(call: calls.OutgoingCall, delay: float, tg_user_ids: list):
    if len(tg_user_ids) > 0:
        loop = asyncio.get_event_loop()
        task = loop.create_task(call_next(tg_user_ids))
    await asyncio.sleep(delay)
    await call.discard_call()
        
async def call_next(tg_user_ids: list):
    if len(tg_user_ids) > 0:
        tg_user_id = tg_user_ids[0]
        tg_user_ids.remove(tg_user_id)
        call = calls.OutgoingCall(user_client, tg_user_id)
        await call.request()
        loop = asyncio.get_event_loop()
        task = loop.create_task(discard_call_and_call_next(call, config.CALL_DURATION, tg_user_ids))
    
@user_client.on_message("*")
async def user_client_message_handler(client: Client, message: pyrogram.types.Message):
    with Session() as session:
        query_result = (
            session.query(ListeningChannel, NotifiedUser, User)
            .join(NotifiedUser, ListeningChannel.listening_channel_id == NotifiedUser.listening_channel_id, isouter=False)
            .join(User, NotifiedUser.user_id == User.user_id, isouter=False)
            .filter(ListeningChannel.tg_chat_id == message.chat.id, ListeningChannel.enabled == True, NotifiedUser.notifications_enabled == True)
            .all()
        )
        
        tg_user_ids = []
        for listening_channel, notified_user, user in query_result:
            tg_user_ids.append(user.tg_user_id)
            print(listening_channel.title, user.name)
            
        if len(tg_user_ids) > 0:
            loop = asyncio.get_event_loop()
            task = loop.create_task(call_next(tg_user_ids))
