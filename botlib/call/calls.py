#  tgcalls - a Python binding for C++ library by Telegram
#  pytgcalls - a library connecting the Python binding with MTProto
#  Copyright (C) 2020-2021 Il`ya (Marshal) <https://github.com/MarshalX>
#
#  This file is part of tgcalls and pytgcalls.
#
#  tgcalls and pytgcalls is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  tgcalls and pytgcalls is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License v3
#  along with tgcalls. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import hashlib
import os
from random import randint
from typing import Union

import pyrogram
from pyrogram import errors
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw import functions, types
from pyrogram.utils import MAX_CHANNEL_ID

from .helpers import b2i, calc_fingerprint, check_g, generate_visualization, i2b


class DH:
    def __init__(self, dhc: types.messages.DhConfig):
        self.p = b2i(dhc.p)
        self.g = dhc.g
        self.resp = dhc

    def __repr__(self):
        return f'<DH p={self.p} g={self.g} resp={self.resp}>'


class Call:
    def __init__(self, client: pyrogram.Client):
        if not client.is_connected:
            raise RuntimeError('Client must be started first')

        self.client = client
        self.native_instance = None

        self.call = None
        self.call_access_hash = None

        self.peer = None
        self.call_peer = None

        self.state = None

        self.dhc = None
        self.a = None
        self.g_a = None
        self.g_a_hash = None
        self.b = None
        self.g_b = None
        self.g_b_hash = None
        self.auth_key = None
        self.key_fingerprint = None

        self.auth_key_visualization = None

        self.init_encrypted_handlers = []

        self._update_handler = RawUpdateHandler(self.process_update)
        self.client.add_handler(self._update_handler, -1)

    async def process_update(self, _, update, users, chats):
        if isinstance(update, types.UpdatePhoneCallSignalingData) and self.native_instance:
            print('receiveSignalingData')
            self.native_instance.receiveSignalingData([x for x in update.data])

        if not isinstance(update, types.UpdatePhoneCall):
            raise pyrogram.ContinuePropagation

        call = update.phone_call
        if not self.call or not call or call.id != self.call.id:
            raise pyrogram.ContinuePropagation
        self.call = call

        if hasattr(call, 'access_hash') and call.access_hash:
            self.call_access_hash = call.access_hash
            self.call_peer = types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash)
            try:
                await self.received_call()
            except Exception as e:
                print(e)

        if isinstance(call, types.PhoneCallDiscarded):
            self.call_discarded()
            raise pyrogram.StopPropagation

    @property
    def auth_key_bytes(self) -> bytes:
        return i2b(self.auth_key) if self.auth_key is not None else b''

    @property
    def call_id(self) -> int:
        return self.call.id if self.call else 0

    @staticmethod
    def get_protocol() -> types.PhoneCallProtocol:
        return types.PhoneCallProtocol(
            min_layer=92,
            max_layer=92,
            udp_p2p=True,
            udp_reflector=True,
            library_versions=['3.0.0'],
        )

    async def get_dhc(self):
        self.dhc = DH(await self.client.invoke(functions.messages.GetDhConfig(version=0, random_length=256)))
        return self.dhc

    def check_g(self, g_x: int, p: int) -> None:
        try:
            check_g(g_x, p)
        except RuntimeError:
            self.call_discarded()
            raise

    def stop(self) -> None:
        async def _():
            try:
                self.client.remove_handler(self._update_handler, -1)
            except ValueError:
                pass

        asyncio.ensure_future(_())

    def update_state(self, val) -> None:
        self.state = val

    def call_ended(self) -> None:
        self.update_state('Ended')
        self.stop()

    def call_failed(self, error=None) -> None:
        print('Call', self.call_id, 'failed with error', error)
        self.update_state('FAILED')
        self.stop()

    def call_discarded(self):
        if isinstance(self.call.reason, types.PhoneCallDiscardReasonBusy):
            self.update_state('BUSY')
            self.stop()
        else:
            self.call_ended()

    async def received_call(self):
        r = await self.client.invoke(
            functions.phone.ReceivedCall(peer=types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash))
        )
        print(r)

    async def discard_call(self, reason=None):
        if not reason:
            reason = types.PhoneCallDiscardReasonDisconnect()
        try:
            r = await self.client.invoke(
                functions.phone.DiscardCall(
                    peer=types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash),
                    duration=0,  # TODO
                    connection_id=0,
                    reason=reason,
                )
            )
            print(self.call_id)
        except (errors.CallAlreadyDeclined, errors.CallAlreadyAccepted) as e:
            pass

        self.call_ended()

    def signalling_data_emitted_callback(self, data):
        async def _():
            await self.client.invoke(
                functions.phone.invokeSignalingData(
                    # peer=self.call_peer,
                    peer=types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash),
                    data=bytes(data),
                )
            )

        asyncio.ensure_future(_(), loop=self.client.loop)

    async def _initiate_encrypted_call(self) -> None:
        await self.client.invoke(functions.help.GetConfig())

        self.update_state('ESTABLISHED')
        self.auth_key_visualization = generate_visualization(self.auth_key, self.g_a)

        for handler in self.init_encrypted_handlers:
            asyncio.iscoroutinefunction(handler) and asyncio.ensure_future(handler(self), loop=self.client.loop)

    def on_init_encrypted_call(self, func: callable) -> callable:
        self.init_encrypted_handlers.append(func)
        return func


class OutgoingCall(Call):
    is_outgoing = True

    def __init__(self, client, user_id: Union[int, str]):
        super().__init__(client)
        self.user_id = user_id

    async def request(self):
        self.update_state('REQUESTING')

        self.peer = await self.client.resolve_peer(self.user_id)

        await self.get_dhc()
        self.a = randint(2, self.dhc.p - 1)
        self.g_a = pow(self.dhc.g, self.a, self.dhc.p)
        self.g_a_hash = hashlib.sha256(i2b(self.g_a)).digest()

        self.call = (
            await self.client.invoke(
                functions.phone.RequestCall(
                    user_id=self.peer,
                    random_id=randint(0, 0x7FFFFFFF - 1),
                    g_a_hash=self.g_a_hash,
                    protocol=self.get_protocol(),
                )
            )
        ).phone_call

        self.update_state('WAITING')

    async def process_update(self, _, update, users, chats) -> None:
        await super().process_update(_, update, users, chats)

        if isinstance(self.call, types.PhoneCallAccepted) and not self.auth_key:
            await self.call_accepted()
            raise pyrogram.StopPropagation

        raise pyrogram.ContinuePropagation

    async def call_accepted(self) -> None:
        self.update_state('EXCHANGING_KEYS')

        await self.get_dhc()
        self.g_b = b2i(self.call.g_b)
        self.check_g(self.g_b, self.dhc.p)
        self.auth_key = pow(self.g_b, self.a, self.dhc.p)
        self.key_fingerprint = calc_fingerprint(self.auth_key_bytes)

        self.call = (
            await self.client.invoke(
                functions.phone.ConfirmCall(
                    key_fingerprint=self.key_fingerprint,
                    # peer=self.call_peer,
                    peer=types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash),
                    g_a=i2b(self.g_a),
                    protocol=self.get_protocol(),
                )
            )
        ).phone_call

        await self._initiate_encrypted_call()


class IncomingCall(Call):
    is_outgoing = False

    def __init__(self, call: types.PhoneCallRequested, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_accepted_handlers = []
        self.update_state('WAITING_INCOMING')
        self.call = call
        self.call_access_hash = call.access_hash

    async def process_update(self, _, update, users, chats):
        await super().process_update(_, update, users, chats)
        if isinstance(self.call, types.PhoneCall) and not self.auth_key:
            await self.call_accepted()
            raise pyrogram.StopPropagation
        raise pyrogram.ContinuePropagation

    async def on_call_accepted(self, func: callable) -> callable:
        self.call_accepted_handlers.append(func)
        return func

    async def accept(self) -> bool:
        self.update_state('EXCHANGING_KEYS')

        if not self.call:
            self.call_failed()
            raise RuntimeError('call is not set')

        if isinstance(self.call, types.PhoneCallDiscarded):
            print('Call is already discarded')
            self.call_discarded()
            return False

        await self.get_dhc()
        self.b = randint(2, self.dhc.p - 1)
        self.g_b = pow(self.dhc.g, self.b, self.dhc.p)
        self.g_a_hash = self.call.g_a_hash

        try:
            self.call = (
                await self.client.invoke(
                    functions.phone.AcceptCall(
                        peer=types.InputPhoneCall(id=self.call_id, access_hash=self.call_access_hash),
                        g_b=i2b(self.g_b),
                        protocol=self.get_protocol(),
                    )
                )
            ).phone_call
        except Exception as e:
            print(e)

            await self.discard_call()

            self.stop()
            self.call_discarded()
            return False

        return True

    async def call_accepted(self) -> None:
        if not self.call.g_a_or_b:
            print('g_a is null')
            self.call_failed()
            return

        if self.g_a_hash != hashlib.sha256(self.call.g_a_or_b).digest():
            print('g_a_hash doesn\'t match')
            self.call_failed()
            return

        self.g_a = b2i(self.call.g_a_or_b)
        self.check_g(self.g_a, self.dhc.p)
        self.auth_key = pow(self.g_a, self.b, self.dhc.p)
        self.key_fingerprint = calc_fingerprint(self.auth_key_bytes)

        if self.key_fingerprint != self.call.key_fingerprint:
            print('fingerprints don\'t match')
            self.call_failed()
            return

        await self._initiate_encrypted_call()