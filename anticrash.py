import disnake
from disnake.ext import commands
from difflib import SequenceMatcher

intents = disnake.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.bans = True
intents.message_content = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
previous_channels = {}
spam_count = {}
whitelist = [] #поместите айди для вайтлиста


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


log_channel_id = 1325892292581789817
log_channel = None


def get_log_channel():
    global log_channel
    if log_channel is None:
        log_channel = bot.get_channel(log_channel_id)
    return log_channel


@bot.event
async def on_member_ban(guild: disnake.Guild, user: disnake.User):
    channel = get_log_channel()
    if channel:
        async for entry in guild.audit_logs(limit=1, action=disnake.AuditLogAction.ban):
            responsible_user = entry.user

            if responsible_user.id not in whitelist:
                embed = disnake.Embed(
                    title=f"🛑 Участник **{user}** был забанен",
                    description=f"Забанил: **{responsible_user}**",
                    color=disnake.Color.red()
                )
                embed.add_field(name="Участника нет в вайт листе и он был забанен!", value="", inline=False)
                await guild.ban(user, reason="Попытка сноса сервера")
                await channel.send(embed=embed)
            else:
                embed = disnake.Embed(
                    title=f"🛡️ Участник **{user}** был кикнут",
                    description=f"Кикнул: **{responsible_user}**",
                    color=disnake.Color.green()
                )
                await channel.send(embed=embed)


@bot.event
async def on_member_remove(member: disnake.Member):
    channel = get_log_channel()
    if channel:
        async for entry in member.guild.audit_logs(limit=1, action=disnake.AuditLogAction.kick):
            if entry.target.id == member.id:
                kicker = entry.user
                if kicker.id not in whitelist:
                    embed = disnake.Embed(
                        title=f"🛑 Участник **{member}** был кикнут",
                        description=f"Кикнул: **{kicker}**",
                        color=disnake.Color.red()
                    )
                    embed.add_field(name="Участника нет в вайт листе и он был забанен!", value="", inline=False)
                    await kicker.ban(reason="Кикнул участника, что запрещено.")
                    await channel.send(embed=embed)
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Участник **{member}** был кикнут",
                        description=f"Кикнул: **{kicker}**",
                        color=disnake.Color.green()
                    )
                    await channel.send(embed=embed)


@bot.event
async def on_guild_role_update(before: disnake.Role, after: disnake.Role):
    async for entry in after.guild.audit_logs(limit=1, action=disnake.AuditLogAction.role_update):
        if entry.target.id == after.id:
            changer = entry.user
            permissions_changed = []
            for perm in disnake.Permissions.VALID_FLAGS:
                before_perm = getattr(before.permissions, perm)
                after_perm = getattr(after.permissions, perm)
                if before_perm != after_perm:
                    change = f"{'✅' if after_perm else '❌'} {perm}"
                    permissions_changed.append(change)

            if permissions_changed:
                if changer.id not in whitelist:
                    embed = disnake.Embed(
                        title=f"🛑 Роль **{after.name}** была изменена",
                        description=f"Изменил: **{changer}**",
                        color=disnake.Color.red()
                    )
                    embed.add_field(name="Измененные права:", value="\n".join(permissions_changed), inline=False)
                    embed.add_field(name="Участника нет в вайт листе и он был забанен!", value="", inline=False)
                    channel = get_log_channel()
                    await channel.send(embed=embed)
                    await changer.ban(reason="Попытка сноса сервера!")
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Роль **{after.name}** была изменена",
                        description=f"Изменил: **{changer}**",
                        color=disnake.Color.green()
                    )
                    embed.add_field(name="Измененные права:", value="\n".join(permissions_changed), inline=False)

                    channel = get_log_channel()
                    await channel.send(embed=embed)
            break


@bot.event
async def on_guild_channel_create(channel: disnake.abc.GuildChannel):
    log_channel = get_log_channel()
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_create):
        if entry.user.id not in whitelist:
            embed = disnake.Embed(
                title=f"🛑 Был создан канал **{channel.name}**",
                description=f"Создатель: **{entry.user}**",
                color=disnake.Color.red()
            )
            embed.add_field(name="Участника нет в вайт-листе, он был забанен, а канал удален!", value="", inline=False)
            await log_channel.send(embed=embed)
            await channel.delete(reason="Создание канала без разрешения")
            await entry.user.ban(reason="Попытка сноса сервера!")
        else:
            embed = disnake.Embed(
                title=f"🛡️ Был создан канал **{channel.name}**",
                description=f"Создатель: **{entry.user}**",
                color=disnake.Color.green()
            )
            await log_channel.send(embed=embed)


@bot.event
async def on_message(message: disnake.Message):
    if message.author.bot or message.author.id in whitelist:
        return

    channel = get_log_channel()
    banned_words = ["http", "https", ".com", ".gg", ".ru", ".net", ".fun"]
    content = message.content.lower()

    for word in banned_words:
        if word in content:
            muted_role = disnake.utils.get(message.guild.roles, name="Muted")
            if not muted_role:
                muted_role = await message.guild.create_role(name="Muted")
                for ch in message.guild.channels:
                    await ch.set_permissions(muted_role, send_messages=False)

            await message.author.add_roles(muted_role)
            embed = disnake.Embed(
                title=f"🛡️ **{message.author}** был замучен за отправку запрещенных ссылок",
                description=f"Сообщение: `{message.content}`",
                color=disnake.Color.red()
            )
            await channel.send(embed=embed)
            await message.delete()
            break

    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    channel = get_log_channel()
    added_roles = set(after.roles) - set(before.roles)
    for role in added_roles:
        if role.permissions.administrator:

            if channel:
                async for entry in after.guild.audit_logs(limit=1, action=disnake.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        admin_issuer = entry.user
                        if admin_issuer.id not in whitelist:
                            embed = disnake.Embed(
                                title="🔔 Попытка выдачи администраторской роли",
                                description=(
                                    f"**Роль выдана:** {role.mention}\n"
                                    f"**Выдана пользователю:** {after.mention} (ID: {after.id})\n"
                                    f"**Выдал роль:** {admin_issuer.mention} (ID: {admin_issuer.id})"
                                ),
                                color=disnake.Color.red()
                            )
                            embed.add_field(
                                name="⚠️ Действие заблокировано",
                                value=(
                                    f"**{admin_issuer.mention}** не имеет права выдавать роль с правами администратора, "
                                    f"поэтому его действия были заблокированы."
                                ),
                                inline=False
                            )
                            await channel.send(embed=embed)
                            await after.remove_roles(role)
                            await admin_issuer.ban(reason="Попытка выдать админскую роль без разрешения.")
                        else:
                            embed = disnake.Embed(
                                title="🛡️ Роль с правами администратора была выдана",
                                description=(
                                    f"**Роль выдана:** {role.mention}\n"
                                    f"**Выдана пользователю:** {after.mention} (ID: {after.id})\n"
                                    f"**Выдал роль:** {admin_issuer.mention} (ID: {admin_issuer.id})"
                                ),
                                color=disnake.Color.green()
                            )
                            embed.add_field(
                                name="✅ Действие разрешено",
                                value=f"**{admin_issuer.mention}** выдал администраторскую роль пользователю **{after.mention}**.",
                                inline=False
                            )
                            await channel.send(embed=embed)
@bot.event
async def on_message(message):
    banned_words = ["http", "https", ".com", ",com", ",gg", ".gg", ".ru", "ru", ".net", ",net", "gg/", "gg /", ".fun", ",fun"]
    if any(word in message.content.lower() for word in banned_words):
        embed = disnake.Embed(
            title=f"🛑 **{message.author}** был замучен за спам-ссылки",
            description=f"Сообщение: `{message.content}`",
            color=disnake.Color.red()
        )
        await channel.send(embed=embed)
        await message.delete()
        await message.author.ban(reason="Использование запрещенных ссылок.")
    await bot.process_commands(message)
@bot.event
async def on_message(message):
    author_id = message.author.id
    if author_id in whitelist:
        return

    # Проверяем схожесть сообщений
    if author_id not in spam_count:
        spam_count[author_id] = {'count': 1, 'last_message': message.content}
    else:
        similarity = similar(message.content, spam_count[author_id]['last_message'])
        if similarity >= 0.75:
            spam_count[author_id]['count'] += 1
            if spam_count[author_id]['count'] > 2:
                # Если слишком много похожих сообщений
                embed = disnake.Embed(
                    title=f"🛑 **{message.author}** был забанен за спам",
                    description=f"Сообщение: `{message.content}`",
                    color=disnake.Color.red()
                )
                await channel.send(embed=embed)
                await message.author.ban(reason="Попытка спама.")
                spam_count[author_id]['count'] = 0  # Сбросить счетчик
        else:
            spam_count[author_id] = {'count': 1, 'last_message': message.content}

    await bot.process_commands(message)
@bot.event
async def on_guild_role_create(role):
    channel = get_log_channel()
    if channel:
        async for entry in role.guild.audit_logs(limit=1, action=disnake.AuditLogAction.role_create):
            user = entry.user
            if user.guild_permissions.manage_roles:
                if user.id not in whitelist:
                    embed = disnake.Embed(
                        title=f"🛑 Роль с правами администратора **{role.name}** была создана",
                        description=f"Создал: {user.mention} (ID: {user.id})",
                        color=disnake.Color.red()
                    )
                    await channel.send(embed=embed)
                    await user.ban(reason="Попытка создать роль с админскими правами без разрешения.")
                else:
                    embed = disnake.Embed(
                        title=f"🛡️ Роль с правами администратора **{role.name}** была создана",
                        description=f"Создал: {user.mention} (ID: {user.id})",
                        color=disnake.Color.green()
                    )
                    await channel.send(embed=embed)
@bot.event
async def on_guild_channel_create(channel):
    channel1 = get_log_channel()
    if channel.guild:
        async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_create):
            if entry.user.id not in whitelist:
                embed = disnake.Embed(
                    title=f"🛑 Канал **{channel.name}** был создан",
                    description=f"Создал: {entry.user.mention} (ID: {entry.user.id})",
                    color=disnake.Color.red()
                )
                embed.add_field(
                    name="⚠️ Действие было заблокировано",
                    value=f"Создание канала без разрешения. Канал будет удален.",
                    inline=False
                )
                await channel1.send(embed=embed)
                await channel.delete(reason="Создание канала без разрешения")
                await entry.user.ban(reason="Создание канала без разрешения.")
            else:
                embed = disnake.Embed(
                    title=f"🛡️ Канал **{channel.name}** был создан",
                    description=f"Создал: {entry.user.mention} (ID: {entry.user.id})",
                    color=disnake.Color.green()
                )
                await channel1.send(embed=embed)
@bot.event
async def on_member_join(member):
    if member.bot:
        embed = disnake.Embed(
            title=f"🛑 **{member}** был удален, так как это бот",
            description=f"Бот был удален: {member.mention} (ID: {member.id})",
            color=disnake.Color.red()
        )
        await member.guild.system_channel.send(embed=embed)
        await member.kick(reason="Попытка добавить бот на сервер.")

@bot.event
async def on_webhooks_update(channel):
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.user.id not in whitelist:
            log_channel = get_log_channel()
            embed = disnake.Embed(
                title="🚨 Попытка создания вебхука!",
                description=f"Вебхук **{webhook.name}** был создан в канале **{channel.name}**.\n"
                            f"Создатель: **{webhook.user.mention}** (ID: {webhook.user.id})",
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)

            await webhook.delete(reason="Создание вебхука без разрешения")
            await webhook.user.ban(reason="Попытка создать вебхук!")

deleted_channels = {}

@bot.event
async def on_guild_channel_delete(channel):
    user_id = None
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_delete):
        user = entry.user
        user_id = user.id

        # Проверяем, находится ли пользователь в вайтлисте
        if user_id not in whitelist:
            # Логируем удаление
            log_channel = get_log_channel()
            embed = disnake.Embed(
                title="🚨 Попытка удаления канала!",
                description=f"Канал **{channel.name}** был удалён.\n"
                            f"Удалил: **{user.mention}** (ID: {user.id})",
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)

            # Восстанавливаем канал
            await channel.guild.create_text_channel(
                name=channel.name,
                category=channel.category,
                overwrites=channel.overwrites
            )
            await user.ban(reason="Попытка массового удаления каналов!")
        break

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=disnake.AuditLogAction.channel_delete):
        user = entry.user

        if user.id not in whitelist:
            log_channel = get_log_channel()
            embed = disnake.Embed(
                title="🚨 Попытка удаления канала!",
                description=f"Канал **{channel.name}** был удалён.\n"
                            f"Удалил: **{user.mention}** (ID: {user.id})",
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)

            # Восстанавливаем канал
            new_channel = await channel.guild.create_text_channel(
                name=channel.name,
                category=channel.category,
                overwrites=channel.overwrites
            )
            await log_channel.send(f"Канал **{new_channel.name}** был восстановлен!")
            await user.ban(reason="Удаление канала без разрешения!")
        break
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Игнорируем сообщения от ботов

    # Проверяем, содержит ли сообщение пересылку
    if message.reference:
        await message.delete()

        # Логирование в канал логов (если есть)
        log_channel = disnake.utils.get(message.guild.text_channels, name="лог")
        if log_channel:
            embed = disnake.Embed(
                title="🚨 Запрещённая пересылка сообщения",
                description=(
                    f"**Пользователь:** {message.author.mention} (ID: {message.author.id})\n"
                    f"**Канал:** {message.channel.mention}\n"
                    "Сообщение было удалено, а пользователь заблокирован."
                ),
                color=disnake.Color.red()
            )
            await log_channel.send(embed=embed)

        # Бан пользователя
        try:
            await message.author.ban(reason="Отправка пересылок, что запрещено правилами")
        except disnake.Forbidden:
            if log_channel:
                await log_channel.send(
                    embed=disnake.Embed(
                        title="❌ Ошибка",
                        description=(
                            f"Не удалось забанить пользователя {message.author.mention} "
                            f"(возможно, у бота нет прав)."
                        ),
                        color=disnake.Color.red()
                    )
                )

    await bot.process_commands(message)  # Не забываем обрабатывать команды
@bot.event
async def on_ready():
    log_channel = disnake.utils.get(bot.get_all_channels(), name="лог")  # Название канала логов
    if log_channel:
        embed = disnake.Embed(
            title="🔧 Функции бота",
            description="Бот успешно запущен! Вот список всех доступных функций:",
            color=disnake.Color.green()
        )

        # Добавляем список всех команд
        commands_list = "\n".join([f"`/{cmd.name}` - {cmd.description or 'Без описания'}" for cmd in bot.commands])
        embed.add_field(name="Доступные команды", value=commands_list if commands_list else "Нет команд.", inline=False)

        # Добавляем список событий
        events_list = [name for name in dir(bot) if name.startswith("on_")]
        events_list = "\n".join([f"`{event}`" for event in events_list])
        embed.add_field(name="Обработчики событий", value=events_list if events_list else "Нет событий.", inline=False)

        await log_channel.send(embed=embed)

    print(f"Бот запущен как {bot.user}.")  # Лог в консоль
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Игнорируем сообщения от ботов

    # Форматы ссылок, которые нужно блокировать
    blocked_links = ["discord.com/invite", "discord.gg", "discordapp.com/invite"]

    # Проверяем, содержит ли сообщение запрещенные ссылки
    if any(link in message.content for link in blocked_links):
        if message.author.id not in whitelist:  # Проверяем, есть ли пользователь в вайтлисте
            log_channel = bot.get_channel(log_channel_id)  # Получаем канал логов

            try:
                await message.delete()  # Удаляем сообщение
                await message.author.ban(reason="Отправка запрещенных ссылок")  # Баним пользователя
                
                # Создаем embed для логов
                embed = disnake.Embed(
                    title="🚨 Заблокировано сообщение с запрещенной ссылкой",
                    description=f"Сообщение от пользователя {message.author.mention} было удалено, и пользователь был забанен.",
                    color=disnake.Color.red(),
                )
                embed.add_field(name="Спамер:", value=f"{message.author} (ID: {message.author.id})", inline=False)
                embed.add_field(name="Сообщение:", value=message.content, inline=False)
                embed.add_field(name="Канал:", value=message.channel.mention, inline=True)
                embed.set_footer(text=f"Пользователь был забанен за нарушение правил.")

                if log_channel:
                    await log_channel.send(embed=embed)  # Отправляем лог
            except disnake.Forbidden:
                print("Боту не хватает прав для удаления сообщения или бана пользователя.")
                if log_channel:
                    await log_channel.send(
                        f"⚠️ Бот не смог забанить пользователя {message.author.mention} из-за отсутствия прав."
                    )
            except disnake.HTTPException as e:
                print(f"Ошибка при удалении сообщения или бана: {e}")
                if log_channel:
                    await log_channel.send(
                        f"⚠️ Произошла ошибка при попытке забанить пользователя {message.author.mention}: {e}"
                    )

    await bot.process_commands(message)  # Обрабатываем команды

bot.run("")
