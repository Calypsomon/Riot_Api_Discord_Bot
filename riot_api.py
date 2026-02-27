from dotenv import load_dotenv
import os
import requests

# ensure environment variables are loaded when the module is imported
load_dotenv(override=True)

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
API_KEY = os.getenv('RIOT_API_KEY')


def get_lp(puuid):
    lp_api_key = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}?api_key={API_KEY}"
    entries = requests.get(lp_api_key).json()
    solo_rank = None
    for entry in entries:
        if entry.get('queueType') == "RANKED_SOLO_5x5":
            solo_rank = entry
    if solo_rank['tier'] == "IRON":
        x= 0
    elif solo_rank['tier'] == "BRONZE":
        x= 400
    elif solo_rank['tier'] == "SILVER":
        x= 800
    elif solo_rank['tier'] == "GOLD":
        x= 1200
    elif solo_rank['tier'] == "PLATINUM":
        x= 1600
    elif solo_rank['tier'] == "EMERALD":
        x= 2000 
    elif solo_rank['tier'] == "DIAMOND":
        x= 2400
    elif solo_rank['tier'] == "MASTER":
        x= 2800
    elif solo_rank['tier'] == "GRANDMASTER":
        x= 3200
    elif solo_rank['tier'] == "CHALLENGER":
        x= 3600
    if solo_rank['rank'] == "IV":
        y= 0
    elif solo_rank['rank'] == "III":
        y= 100
    elif solo_rank['rank'] == "II":
        y= 200
    elif solo_rank['rank'] == "I":
        y= 300
    lp = x + y + solo_rank['leaguePoints']
    return lp

def get_rank(lp):
    rank = lp/400
    tier = (lp%400)/100
    ranks = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM","EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    tiers = ["IV", "III", "II", "I"]
    return f"{ranks[int(rank)]} {tiers[int(tier)]}"


def get_name(puuid):
    name_api_key = f"https://europe.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}?api_key={API_KEY}"
    name = requests.get(name_api_key).json()['gameName']
    tag = requests.get(name_api_key).json()['tagLine']
    return f"{name}#{tag}"