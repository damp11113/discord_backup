import discord
import traceback
import asyncio
import logging

from damp11113 import BooleanArgs

log = logging.getLogger(__name__)


class BackupLoader:
    def __init__(self, bot, guild, data):
        self.bot = bot
        self.guild = guild
        self.data = data
        self.id_translator = {}
        self.options = BooleanArgs([])
        self.semaphore = asyncio.Semaphore(2)

    async def overwritefjson(self, json):
        overwrites = {}
        for union_id, overwrite in json.items():
            try:
                union = await self.guild.fetch_member(int(union_id))
            except discord.NotFound:
                roles = list(
                    filter(lambda r: r.id == self.id_translator.get(union_id), self.guild.roles))
                if len(roles) == 0:
                    continue

                union = roles[0]

            overwrites[union] = discord.PermissionOverwrite(**overwrite)

        return overwrites

    def _translate_mentions(self, text):
        if not text:
            return text

        formats = ["<#%s>", "<@&%s>"]
        for key, value in self.id_translator.items():
            for _format in formats:
                text = text.replace(_format % str(key), _format % str(value))

        return text

    async def run_tasks(self, coros, wait=True):
        async def executor(_coro):
            try:
                await _coro

            except Exception:
                pass

            finally:
                self.semaphore.release()

        tasks = []
        for coro in coros:
            await self.semaphore.acquire()
            tasks.append(self.bot.loop.create_task(executor(coro)))

        if wait and tasks:
            await asyncio.wait(tasks)

    async def _prepare_guild(self):
        log.debug(f"Deleting roles on {self.guild.id}")
        if self.options.roles:
            existing_roles = list(filter(
                lambda r: not r.managed and self.guild.me.top_role.position > r.position,
                self.guild.roles
            ))
            difference = len(self.data["roles"]) - len(existing_roles)
            for role in existing_roles:
                if difference < 0:
                    try:
                        await role.delete(reason=self.reason)
                    except Exception:
                        raise Exception(traceback.format_exc())

                    else:
                        difference += 1

                else:
                    break

        if self.options.channels:
            log.debug(f"Deleting channels on {self.guild.id}")
            for channel in self.guild.channels:
                try:
                    await channel.delete(reason=self.reason)
                except Exception:
                    raise Exception(traceback.format_exc())

    async def _load_settings(self):
        log.debug(f"Loading settings on {self.guild.id}")
        await self.guild.edit(
            name=self.data["name"],
            # region=discord.VoiceRegion(self.data["region"]),
            afk_channel=self.guild.get_channel(self.id_translator.get(self.data["afk_channel"])),
            afk_timeout=self.data["afk_timeout"],
            # verification_level=discord.VerificationLevel(self.data["verification_level"]),
            system_channel=self.guild.get_channel(self.id_translator.get(self.data["system_channel"])),
            reason=self.reason
        )

    async def _load_roles(self):
        log.debug(f"Loading roles on {self.guild.id}")
        existing_roles = list(reversed(list(filter(
            lambda r: not r.managed and not r.is_default()
                    and self.guild.me.top_role.position > r.position,
            self.guild.roles
        ))))
        for role in reversed(self.data["roles"]):
            try:
                if role["default"]:
                    await self.guild.default_role.edit(
                        permissions=discord.Permissions(role["permissions"])
                    )
                    new_role = self.guild.default_role
                else:
                    kwargs = {
                        "name": role["name"],
                        "hoist": role["hoist"],
                        "mentionable": role["mentionable"],
                        "color": discord.Color(role["color"]),
                        "permissions": discord.Permissions.none(),
                        "reason": self.reason
                    }

                    if len(existing_roles) == 0:
                        try:
                            new_role = await asyncio.wait_for(self.guild.create_role(**kwargs), 10)
                        except asyncio.TimeoutError:
                            # Probably hit the 24h rate limit. Just skip roles
                            break
                    else:
                        new_role = existing_roles.pop(0)
                        await new_role.edit(**kwargs)

                self.id_translator[role["id"]] = new_role.id
            except Exception:
                raise Exception(traceback.format_exc())
    
    async def _load_role_permissions(self):
        tasks = []
        for role in self.data["roles"]:
            to_edit = self.guild.get_role(self.id_translator.get(role["id"]))
            if to_edit:
                tasks.append(to_edit.edit(permissions=discord.Permissions(role["permissions"])))

        await self.run_tasks(tasks)

    async def _load_categories(self):
        log.debug(f"Loading categories on {self.guild.id}")
        for category in self.data["categories"]:
            try:
                created = await self.guild.create_category_channel(
                    name=category["name"],
                    overwrites=await self._overwrites_from_json(category["overwrites"]),
                    reason=self.reason
                )
                self.id_translator[category["id"]] = created.id
            except Exception:
                raise Exception(traceback.format_exc())

    async def _load_text_channels(self):
        log.debug(f"Loading text channels on {self.guild.id}")
        for tchannel in self.data["text_channels"]:
            try:
                created = await self.guild.create_text_channel(
                    name=tchannel["name"],
                    overwrites=await self._overwrites_from_json(tchannel["overwrites"]),
                    category=discord.Object(self.id_translator.get(tchannel["category"])),
                    reason=self.reason
                )

                self.id_translator[tchannel["id"]] = created.id
                await created.edit(
                    topic=self._translate_mentions(tchannel["topic"]),
                    nsfw=tchannel["nsfw"],
                )
            except Exception:
                raise Exception

    async def _load_voice_channels(self):
        log.debug(f"Loading voice channels on {self.guild.id}")
        for vchannel in self.data["voice_channels"]:
            try:
                created = await self.guild.create_voice_channel(
                    name=vchannel["name"],
                    overwrites=await self._overwrites_from_json(vchannel["overwrites"]),
                    category=discord.Object(self.id_translator.get(vchannel["category"])),
                    reason=self.reason
                )
                await created.edit(
                    bitrate=vchannel["bitrate"],
                    user_limit=vchannel["user_limit"]
                )
                self.id_translator[vchannel["id"]] = created.id
            except Exception:
                raise Exception

    async def _load_channels(self):
        await self._load_categories()
        await self._load_text_channels()
        await self._load_voice_channels()

    async def _load_bans(self):
        log.debug(f"Loading bans on {self.guild.id}")

        tasks = [
            self.guild.ban(user=discord.Object(int(ban["user"])), reason=ban["reason"])
            for ban in self.data["bans"]
        ]
        await self.run_tasks(tasks)

    async def _load_members(self):
        log.debug(f"Loading members on {self.guild.id}")

        async def edit_member(member, member_data):
            roles = [
                discord.Object(self.id_translator.get(role))
                for role in member_data["roles"]
                if role in self.id_translator.keys()
            ]

            if self.guild.me.top_role.position > member.top_role.position:
                try:
                    if member != self.guild.owner:
                        await member.edit(
                            nick=member_data.get("nick"),
                            roles=[r for r in member.roles if r.managed] + roles,
                            reason=self.reason
                        )

                except discord.Forbidden:
                    try:
                        await member.edit(
                            roles=[r for r in member.roles if r.managed] + roles,
                            reason=self.reason
                        )

                    except discord.Forbidden:
                        await member.add_roles(*roles)

            else:
                await member.add_roles(*roles)

        tasks = []
        default_data = {
            "nick": None,
            "roles": []
        }
        async for member in self.guild.fetch_members(limit=self.guild.member_count):
            fits = list(filter(lambda m: m["id"] == str(member.id), self.data["members"]))
            if fits:
                tasks.append(edit_member(member, fits[0]))

            else:
                tasks.append(edit_member(member, default_data))

        await self.run_tasks(tasks)

    async def load(self, guild, loader, options: BooleanArgs = None):
        self.options = options or self.options
        self.guild = guild
        self.loader = loader
        self.reason = f"Backup loaded by {loader}"

        log.debug(f"Loading backup on {self.guild.id}")

        try:
            await self._prepare_guild()
        except Exception:
            traceback.print_exc()

        print("Loading data...")


        steps = [
            ("roles", self._load_roles),
            ("channels", self._load_channels),
            ("settings", self._load_settings),
            ("bans", self._load_bans),
            ("members", self._load_members),
            ("roles", self._load_role_permissions)
        ]
        for option, coro in steps:
            if self.options.get(option):
                try:
                    await coro()
                except Exception:
                    traceback.print_exc()

        log.debug(f"Finished loading backup on {self.guild.id}")
        print("Finished loading backup.")