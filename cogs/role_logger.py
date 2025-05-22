import discord
from discord.ext import commands

ROLE_LOG_CHANNEL_ID = 1374439655415611393  # Remplace par ton ID

class RoleLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        # Ignore le rôle @everyone (toujours présent par défaut)
        everyone_role = after.guild.default_role
        before_roles.discard(everyone_role)
        after_roles.discard(everyone_role)

        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles

        if not added_roles and not removed_roles:
            return  # Aucun rôle ajouté ou retiré

        guild = after.guild
        log_chan = guild.get_channel(ROLE_LOG_CHANNEL_ID)
        if log_chan is None:
            return  # Canal non trouvé

        executor = None
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                executor = entry.user
                break

        author = executor.mention if executor else "Inconnu"

        for role in added_roles:
            await log_chan.send(f"🔧 Rôle **{role.name}** ajouté à {after.mention} par {author}")

        for role in removed_roles:
            await log_chan.send(f"🚫 Rôle **{role.name}** retiré à {after.mention} par {author}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RoleLogger(bot))
