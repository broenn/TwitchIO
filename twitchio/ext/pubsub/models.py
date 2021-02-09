import datetime
from typing import List, Optional

from twitchio import PartialUser, Client, Channel, CustomReward

__all__ = (
    "PoolError",
    "PoolFull",

    "PubSubMessage",
    "PubSubBitsMessage",
    "PubSubBitsBadgeMessage",
    "PubSubChatMessage",
    "PubSubBadgeEntitlement",
    "PubSubChannelPointsMessage",
    "PubSubModerationAction"
)

class PoolError(Exception):
    pass

class PoolFull(PoolError):
    pass

class PubSubChatMessage:
    __slots__ = "content", "id", "type"

    def __init__(self, content: str, id: str, type: str):
        self.content = content
        self.id = int(id)
        self.type = type

class PubSubBadgeEntitlement:
    __slots__ = "new", "old"
    def __init__(self, new: int, old: int):
        self.new = new
        self.old = old

class PubSubMessage:
    __slots__ = "topic", "_data"

    def __init__(self, client: Client, topic: Optional[str], data: dict):
        self.topic = topic
        self._data = data

class PubSubBitsMessage(PubSubMessage):
    __slots__ = "badge_entitlement", "bits_used", "channel_id", "context", "anonymous", "message", "user", "version"

    def __init__(self, client: Client, topic: str, data: dict):
        super().__init__(client, topic, data)
        self.message = PubSubChatMessage(data['chat_message'], data['message_id'], data['message_type'])
        self.badge_entitlement = PubSubBadgeEntitlement(
            data['badge_entitlement']['new_version'],
            data['badge_entitlement']['old_version']
        ) if data['badge_entitlement'] else None
        self.bits_used: int = data['bits_used']
        self.channel_id: int = int(data['channel_id'])
        self.user = PartialUser(client._http, data['user_id'], data['user_name']) if data['user_id'] is not None else None
        self.version: str = data['version']

class PubSubBitsBadgeMessage(PubSubMessage):
    __slots__ = "user", "channel", "badge_tier", "message", "timestamp"

    def __init__(self, client: Client, topic: str, data: dict):
        super().__init__(client, topic, data)
        self.user = PartialUser(client._http, data['user_id'], data['user_name'])
        self.channel: Channel = client.get_channel(data['channel_name']) or Channel(name=data['channel_name'], websocket=client._connection)
        self.badge_tier: int = data['badge_tier']
        self.message = data['chat_message']
        self.timestamp = datetime.datetime.strptime(data['time'], "%Y-%m-%dT%H:%M:%SZ")

class PubSubChannelPointsMessage(PubSubMessage):
    __slots__ = "timestamp", "channel_id", "user", "id", "reward", "input", "status"

    def __init__(self, client: Client, data: dict):
        super().__init__(client, None, data)
        self.timestamp = datetime.datetime.strptime(data['redemption']['redeemed_at'], "%Y-%m-%dT%H:%M:%SZ")
        self.channel_id: int = int(data['redemption']['channel_id'])
        self.id: str = data['redemption']['id']
        self.user = PartialUser(client._http, data['user']['id'], data['user']['display_name'])
        self.reward = CustomReward(client._http, data['redemption']['reward'], PartialUser(client._http, self.channel_id, None))
        self.input: str = data['redemption']['user_input']
        self.status: str = data['redemption']['status']

class PubSubModerationAction(PubSubMessage):
    __slots__ = "action", "args", "created_by", "message_id", "target", "from_automod"

    def __init__(self, client: Client, topic: str, data: dict):
        super().__init__(client, topic, data)
        self.action: str = data['message']['data']['moderation_action']
        self.args: List[str] = data['message']['data']['args']
        self.created_by = PartialUser(client._http, data['message']['data']['created_by_user_id'], data['message']['data']['created_by'])
        self.message_id: str = data['message']['data']['msg_id']
        self.target = PartialUser(
            client._http,
            data['message']['data']['target_user_id'],
            data['message']['data']['target_user_login'])\
            if data['message']['data']['target_user_id'] else None
        self.from_automod: bool = data['message']['data']['from_automod']

_mapping = {
    "channel-bits-events-v2": ("pubsub_bits", PubSubBitsMessage),
    "channel-bits-badge-unlocks": ("pubsub_bits_badge", PubSubBitsBadgeMessage),
    "channel-subscribe-events-v1": ("pubsub_subscription", None),
    "chat_moderator_actions": ("pubsub_moderation", PubSubModerationAction),
    "whispers": ("pubsub_whisper", None)
}

def create_message(client, msg: dict):
    topic = msg['data']['topic'].split('.')[0]
    r = _mapping[topic]
    return r[0], r[1](client, topic, msg['data'])