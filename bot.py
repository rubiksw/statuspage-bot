import discord
import requests
import json
import asyncio
from discord.ext.commands import Bot
import config

intents = discord.Intents.default()
bot = Bot(command_prefix=config.BOT_PREFIX, intents=intents)
bot.remove_command('help')

@bot.event
async def on_ready():
    bot.loop.create_task(bot_activity())
    bot.loop.create_task(incidents())
    bot.loop.create_task(maintenance())
    print('STATUSPAGE MONITOR: LOGGED IN')

async def bot_activity():
    while True:
        try:
            r = requests.get(f'https://{config.STATUSPAGE}/api/v2/summary.json')
            json_data = json.loads(r.text)
            status = json_data['status']['description']
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{config.STATUSPAGE}'))
            await asyncio.sleep(config.ACTIVITY_REFRESH_RATE)
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{status}'))
            await asyncio.sleep(config.ACTIVITY_REFRESH_RATE)
        except json.JSONDecodeError as e:
            print(f"An error occurred in bot_activity: {e}")

def GetMessageID(method, IncidentID):
    Found = False
    with open(f'{method}.txt', 'r') as r:
        lines = r.readlines()
        for line in lines:
            if f"{IncidentID}=" in line:
                Found = line.split('=')[1].strip()
                break
        else:
            Found = False
    return Found

async def incidents():
    while True:
        try:
            r = requests.get(f'https://{config.STATUSPAGE}/api/v2/incidents.json')
            json_data = json.loads(r.text)
            
            if json_data['incidents']:
                incident_id = json_data['incidents'][0]['id']
                Impact = json_data['incidents'][0]['impact']
                Title = json_data['incidents'][0]['name']
                Status = json_data['incidents'][0]['status']
                LastUpdate = json_data['incidents'][0]['updated_at']
                Desc = json_data['incidents'][0]['incident_updates'][0]['body']
                channel = bot.get_channel(config.LOG_CHANNEL_ID)

                if Status == "resolved":
                    color = 0xdadee6
                elif Impact == "critical":
                    color = 0xce422b
                elif Impact == "major":
                    color = 0xe57e21
                elif Impact == "minor":
                    color = 0xe5c61e
                else:
                    color = 0x596074

                with open('incidents.txt', 'a+') as f:
                    if not GetMessageID('incidents', incident_id):
                        embed = discord.Embed(
                            title=f'Incident Report: {Title}',
                            description=Desc,
                            color=color,
                            url=f"https://{config.STATUSPAGE}/incidents/{incident_id}",
                        )
                        embed.set_thumbnail(
                            url=config.EMBED_THUMBNAIL
                        )
                        embed.add_field(
                            name="Status:",
                            value=Status.capitalize(),
                            inline=True
                        )
                        embed.add_field(
                            name="Impact:",
                            value=Impact.capitalize(),
                            inline=True
                        )
                        embed.add_field(
                            name="Updated:",
                            value=LastUpdate,
                            inline=True
                        )
                        embed.set_footer(
                            text=f"ID: {incident_id}"
                        )
                        if config.SHOULD_PING:
                            await channel.send(f'<@&{config.PING_ROLE_ID}> a new incident has been reported: {Title}')
                        embed_message = await channel.send(embed=embed)
                        f.write(f"{incident_id}={embed_message.id} \n")
                        await asyncio.sleep(config.INCIDENT_REFRESH_RATE)
                    else:
                        await asyncio.sleep(config.INCIDENT_REFRESH_RATE)
            else:
                await asyncio.sleep(config.INCIDENT_REFRESH_RATE)
        except (requests.exceptions.RequestException, json.JSONDecodeError, IndexError) as e:
            print(f"An error occurred in incidents: {e}")

async def maintenance():
    while True:
        try:
            r = requests.get(f'https://{config.STATUSPAGE}/api/v2/scheduled-maintenances.json')
            json_data = json.loads(r.text)

            if json_data['scheduled_maintenances']:
                incident_id = json_data['scheduled_maintenances'][0]['id']
                Impact = json_data['scheduled_maintenances'][0]['impact']
                Title = json_data['scheduled_maintenances'][0]['name']
                Status = json_data['scheduled_maintenances'][0]['status']
                LastUpdate = json_data['scheduled_maintenances'][0]['updated_at']
                Desc = json_data['scheduled_maintenances'][0]['incident_updates'][0]['body']
                channel = bot.get_channel(config.LOG_CHANNEL_ID)

                with open('maintenance.txt', 'a+') as f:
                    if not GetMessageID('maintenance', incident_id):
                        embed = discord.Embed(
                            title=Title,
                            description=Desc,
                            color=0x3598db,
                            url=f"https://{config.STATUSPAGE}/incidents/{incident_id}",
                        )
                        embed.set_thumbnail(
                            url=config.EMBED_THUMBNAIL
                        )
                        embed.add_field(
                            name="Status:",
                            value=Status.capitalize(),
                            inline=True
                        )
                        embed.add_field(
                            name="Impact:",
                            value=Impact.capitalize(),
                            inline=True
                        )
                        embed.add_field(
                            name="Updated:",
                            value=LastUpdate,
                            inline=True
                        )
                        embed.set_footer(
                            text=f"ID: {incident_id}"
                        )
                        if config.SHOULD_PING:
                            await channel.send(f'<@&{config.PING_ROLE_ID}> {Title}')
                        embed_message = await channel.send(embed=embed)
                        f.write(f"{incident_id}={embed_message.id} \n")
                        await asyncio.sleep(config.MAINTENANCE_REFRESH_RATE)
                    else:
                        await asyncio.sleep(config.MAINTENANCE_REFRESH_RATE)
            else:
                await asyncio.sleep(config.MAINTENANCE_REFRESH_RATE)
        except (requests.exceptions.RequestException, json.JSONDecodeError, IndexError, discord.errors.NotFound) as e:
            print(f"An error occurred in maintenance: {e}")
            if isinstance(e, discord.errors.NotFound):
                with open('maintenance.txt', 'r') as f:
                    lines = f.readlines()
                with open('maintenance.txt', 'w') as f:
                    for line in lines:
                        if f"{incident_id}=" not in line:
                            f.write(line)

bot.run(config.TOKEN)
