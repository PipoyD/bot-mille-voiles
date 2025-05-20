# cogs/role_logger.py

import discord
from discord.ext import commands

# Remplace par l'ID de ton canal de logs
ROLE_LOG_CHANNEL_ID = 1374439655415611393

class RoleLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # 1️⃣ Détecte les rôles ajoutés et retirés
        before_roles = set(before.roles)
        after_roles  = set(after.roles)

        added_roles   = after_roles - before_roles
        removed_roles = before_roles - after_roles

        if not added_roles and not removed_roles:
            return  # pas de changement

        guild = after.guild
        log_chan = guild.get_channel(ROLE_LOG_CHANNEL_ID)
        if log_chan is None:
            return  # canal non trouvé

        # 2️⃣ Cherche dans les logs d’audit qui a fait le changement
        executor = None
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                executor = entry.user
                break

        # 3️⃣ Pour chaque rôle ajouté, envoie un message simple
        for role in added_roles:
            author = executor.mention if executor else "Inconnu"
            await log_chan.send(
                f"🔧 Rôle **{role.name}** ajouté à {after.mention} par {author}"
            )

        # 4️⃣ Pour chaque rôle retiré, envoie un message simple
        for role in removed_roles:
            author = executor.mention if executor else "Inconnu"
            await log_chan.send(
                f"🚫 Rôle **{role.name}** retiré à {after.mention} par {author}"
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(RoleLogger(bot))
