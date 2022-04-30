import discord
import traceback
import asyncio
import damp11113
import logging

log = logging.getLogger(__name__)

class backup_exception(Exception):
    pass

class BackupServer:
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.data = {}

    @staticmethod
    def _overwrites2json(overwrites):
        try:
            return {str(target.id): overwrite._values for target, overwrite in overwrites.items()}
        except Exception:
            raise backup_exception("Failed to convert overwrites to json")

    async def _save_channels(self):
        for category in self.guild.categories:
            try:
                self.data["categories"].append({
                    "name": category.name,
                    "position": category.position,
                    "category": None if category.category is None else str(category.category.id),
                    "id": str(category.id),
                    "overwrites": self._overwrites2json(category.overwrites)
                })
            except Exception:
                raise backup_exception("Failed to save category")

            await asyncio.sleep(0)

        for tchannel in self.guild.text_channels:
            try:
                self.data["text_channels"].append({
                    "name": tchannel.name,
                    "position": tchannel.position,
                    "category": None if tchannel.category is None else str(tchannel.category.id),
                    "id": str(tchannel.id),
                    "overwrites": self._overwrites2json(tchannel.overwrites),
                    "topic": tchannel.topic,
                    "slowmode_delay": tchannel.slowmode_delay,
                    "nsfw": tchannel.is_nsfw(),
                    "messages": [],
                    "webhooks": [{
                        "channel": str(webhook.channel.id),
                        "name": webhook.name,
                        "avatar": str(webhook.avatar_url),
                        "url": webhook.url

                    } for webhook in await tchannel.webhooks()]
                })
            except Exception:
                raise backup_exception("Failed to save text channel")

            await asyncio.sleep(0)

        for vchannel in self.guild.voice_channels:
            try:
                self.data["voice_channels"].append({
                    "name": vchannel.name,
                    "position": vchannel.position,
                    "category": None if vchannel.category is None else str(vchannel.category.id),
                    "id": str(vchannel.id),
                    "overwrites": self._overwrites2json(vchannel.overwrites),
                    "bitrate": vchannel.bitrate,
                    "user_limit": vchannel.user_limit,
                })
            except Exception:
                raise backup_exception("Failed to save voice channel")

            await asyncio.sleep(0)

    async def _save_roles(self):
        for role in self.guild.roles:
            try:
                if role.managed:
                    continue

                self.data["roles"].append({
                    "id": str(role.id),
                    "default": role.is_default(),
                    "name": role.name,
                    "permissions": role.permissions.value,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "position": role.position,
                    "mentionable": role.mentionable
                })
            except Exception:
                raise backup_exception("Failed to save role")

            await asyncio.sleep(0)

    async def _save_members(self):
        if self.guild.large:
            await self.bot.request_offline_members(self.guild)

        async for member in self.guild.fetch_members(limit=1000):
            try:
                self.data["members"].append({
                    "id": str(member.id),
                    "name": member.name,
                    "discriminator": member.discriminator,
                    "nick": member.nick,
                    "roles": [str(role.id) for role in member.roles[1:] if not role.managed]
                })
            except Exception:
                raise backup_exception("Failed to save member")

            await asyncio.sleep(0)

    async def _save_bans(self):
        for reason, user in await self.guild.bans():
            try:
                self.data["bans"].append({
                    "user": str(user.id),
                    "reason": reason
                })
            except Exception:
                raise backup_exception("Failed to save ban")

            await asyncio.sleep(0)

    async def _save_emojis(self):
        for emoji in self.guild.emojis:
            try:
                self.data["emojis"].append({
                    "id": str(emoji.id),
                    "name": emoji.name,
                    "roles": [str(role.id) for role in emoji.roles],
                    "animated": emoji.animated,
                    "managed": emoji.managed,
                    "require_colons": emoji.require_colons,
                    "url": emoji.url
                })
            except Exception:
                raise backup_exception("Failed to save emoji")

            await asyncio.sleep(0)

    async def save(self):
        self.data = {
            "create_backup_at": damp11113.timestamp(),
            "id": str(self.guild.id),
            "name": self.guild.name,
            "icon_url": str(self.guild.icon_url),
            "owner": str(self.guild.owner_id),
            "member_count": self.guild.member_count,
            "region": str(self.guild.region),
            "system_channel": str(self.guild.system_channel),
            "afk_timeout": self.guild.afk_timeout,
            "afk_channel": None if self.guild.afk_channel is None else str(self.guild.afk_channel.id),
            "mfa_level": self.guild.mfa_level,
            "verification_level": str(self.guild.verification_level),
            "explicit_content_filter": str(self.guild.explicit_content_filter),
            "large": self.guild.large,

            "text_channels": [],
            "voice_channels": [],
            "categories": [],
            "roles": [],
            "members": [],
            "bans": [],
            "emojis": [],
        }

        execution_order = [self._save_roles, self._save_channels, self._save_members, self._save_bans, self._save_emojis]

        for method in execution_order:
            try:
                await method()
            except Exception:
                traceback.print_exc()
                raise backup_exception("Failed to save guild")

        return self.data

    def __dict__(self):
        return self.data

        
