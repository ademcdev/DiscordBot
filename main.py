import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
import asyncio
import yt_dlp as ytdl

load_dotenv()
TOKEN = os.getenv('discord_token')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

ytdl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'data/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = ytdl.YoutubeDL(ytdl_format_options)

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("/"),
    description='Simple music bot',
    intents=intents,
)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume = 0.2):
        super().__init__(source, volume)
        
        self.data = data
        
        self.title = data.get('title')
        self.url = data.get('url')
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

def getResponse(rawUserInput):
        userInput = rawUserInput.lower()
        if userInput == '':
            return 'Well, you are awfully silent...'
        elif 'help' in userInput:
            return 'Commands: To receive a private message, write a DM at the beginning of the sentence.'
        elif 'hello' in userInput:
            return 'Hello there'
        elif 'obi-wan' in userInput or 'obiwan' in userInput or 'obi wan kenobi' in userInput:
            return 'I will do what I must.'
        elif 'you were the chosen one' in userInput or 'it was said that you would destroy the sith, not join them!' in userInput or 'bring balance to the force, not leave it in darkness!' in userInput:
            return 'I HATE YOU!!!!'
        elif 'i hate you' in userInput:
            return 'You were my brother anakin. I loved you'
        else:
            return 'Do or do not. There is no try'

async def sendMessage(message, rawUserInput) -> None:
        if not rawUserInput:
            print('Message was empty because intents were not enabled')
            return
        isPrivate = rawUserInput[0] == 'dm'
        if isPrivate:
            rawUserInput = rawUserInput[1:]
        try:
            response = getResponse(rawUserInput)
            await message.author.send(response) if isPrivate else await message.channel.send(response)
        except Exception as e:
            print(e)

class MyClient(discord.Client):
    async def on_ready(self) -> None:
        print(f'{client.user} is connected to the following guilds:')
        for guild in client.guilds:
            print(f'{guild.name} (id:{guild.id})')

    async def on_message(self, message) -> None:
        if message.content.startswith('-'):
            if message.author == client.user:
                return
            else:
                username = message.author
                rawUserInput = message.content
                channel = message.channel
                print(f'[{channel}] [{username}]: "{rawUserInput}"')
                await sendMessage(message, rawUserInput)

    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            msg = f'**Did you hear that? {member.mention}**'
            await channel.send(msg)

    async def on_member_remove(self, member):
        channel = member.guild.system_channel
        if channel is not None:
            msg = f'**Farewell {member.mention}. May the force be with you**'
            await channel.send(msg)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.role_message_id = 1237450786196160613
        self.emoji_to_role = {
            discord.PartialEmoji(name='jedi_master', id=1237434764193959936): 1237415351462006866,
            discord.PartialEmoji(name='one_ring', id=1237442284878954599): 1237416413015179478,
            discord.PartialEmoji(name='auror', id=1237444023942123582): 1237417424618524683,
        }

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # print(payload.emoji)
        if payload.message_id != self.role_message_id:
            return
        guild = self.get_guild(payload.guild_id)
        if guild is None:
            return
        try:
            roleID = self.emoji_to_role[payload.emoji]
        except KeyError:
            return
        role = guild.get_role(roleID)
        if role is None:
            return
        try:
            await payload.member.add_roles(role)
        except discord.HTTPException as de:
            print(f'An error occurred! {de}')
            
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.message_id != self.role_message_id:
            return
        guild = self.get_guild(payload.guild_id)
        if guild is None:
            return
        try:
            roleID = self.emoji_to_role[payload.emoji]
        except KeyError:
            return
        role = guild.get_role(roleID)
        if role is None:
            return
        member = guild.get_member(payload.user_id)
        if member is None:
            return
        try:
            await member.remove_roles(role)
        except discord.HTTPException as de:
            print(f'An error occurred! {de}')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.current_song = None

    async def play_next(self, ctx):
        musician = ctx.voice_client
        if len(self.queue) > 0:
            self.current_song = self.queue.pop(0)
            musician.play(self.current_song, after=lambda e: print(f'Player error: {e}') if e else None)
            embed_msg = discord.Embed(description=f'Şimdi oynatılıyor **{self.current_song.title}**', color=discord.Color.blue())
            await ctx.send(embed = embed_msg)
        else:
            self.current_song = None
            embed_msg = discord.Embed(description=f'Sıra da herhangi bir müzik yok. **/rplay** ile müzik ekleyebilirsiniz.', color=discord.Color.blue())
            await ctx.send(embed = embed_msg)

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Bot belirtilen ses kanalına katılır"""
        musician = ctx.voice_client
        if musician is not None:
            return await musician.move_to(channel)
        
        await channel.connect()
    
    @commands.command()
    async def localplay(self, ctx, *, query):
        """Bilgisayar da yüklü olan bir dosyayı oynatır"""
        musician = ctx.voice_client
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        musician.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        
        await ctx.send(f'**Şimdi oynatılıyor:** {query}')
    
    @commands.command()
    async def rplay(self, ctx, *, url):
        """Link ile istenilen müzikleri oynatır"""
        musician = ctx.voice_client
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            self.queue.append(player)
            if musician.is_playing() or musician.is_paused():
                embed_msg = discord.Embed(description=f'Sıraya eklendi **{player.title}**', color=discord.Color.blue())
                await ctx.send(embed = embed_msg)
            else:
                await self.play_next(ctx)

    @commands.command()
    async def rskip(self, ctx):
        """Bir sonraki müziğe geçer."""
        musician = ctx.voice_client
        if musician.is_playing():
            musician.stop()
            await self.play_next(ctx)
    
    @commands.command()
    async def rstream(self, ctx, *, url):
        """Link ile istenilen müzikleri yayınlar"""
        musician = ctx.voice_client
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            musician.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            
        embed_msg = discord.Embed(description=f'Şimdi oynatılıyor **{player.title}**', color=discord.Color.blue())
        await ctx.send(embed = embed_msg)
        
    @commands.command()
    async def rvolume(self, ctx, volume: int):
        """Oynatıcının ses seviyesini ayarlar"""
        
        musician = ctx.voice_client
        if musician is None:
            embed_msg = discord.Embed(description='Oynatıcı bir **ses kanalına** bağlı değil!', color=discord.Color.red())
            return await ctx.send(embed = embed_msg)
        
        musician.source.volume = volume / 100
        embed_msg = discord.Embed(description=f'Ses seviyesi **%{volume}** olarak değiştirildi', color=discord.Color.random())
        await ctx.send(embed = embed_msg)
    
    @commands.command()
    async def rpause(self, ctx):
        """Bot çalmayı geçici olarak durdurur"""
        musician = ctx.voice_client
        if musician.is_playing():
            musician.pause()
            embed_msg = discord.Embed(description='Oynatıcı duraklatıldı', color=discord.Color.red())
            await ctx.send(embed = embed_msg)
        else:
            musician.resume()
            embed_msg = discord.Embed(description='Oynatıcı devam ediyor', color=discord.Color.blue())
            await ctx.send(embed = embed_msg)
    
    @commands.command()
    async def rstop(self, ctx):
        """Bot çalmayı durdurur ve ses kanalından çıkar """
        
        musician = ctx.voice_client
        musician.stop()
        self.queue = []
        await musician.disconnect()
        embed_msg = discord.Embed(description='Oynatıcı durduruldu', color=discord.Color.red())
        await ctx.send(embed = embed_msg)

    @localplay.before_invoke
    @rplay.before_invoke
    @rstream.before_invoke
    async def ensure_voice(self, ctx):
        musician = ctx.voice_client
        if musician is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                embed_msg = discord.Embed(description='Önce bir **ses kanalına** bağlı olmanız gerekiyor!', color=discord.Color.red())
                await ctx.send(embed = embed_msg)
                raise commands.CommandError('Author not connected to a voice channel.')

client = MyClient(intents=intents)

async def main() -> None:
    async with bot:
        await bot.add_cog(Music(bot))
        await bot.start(TOKEN)
    client.run(TOKEN)

if __name__ == '__main__':
    main()