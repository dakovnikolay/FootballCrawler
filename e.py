from selenium import webdriver
from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import os
import datetime
import pandas as pd
import time
import re
import requests
import pickle
from os import listdir
from os.path import isfile, join
import sys
import statistics

player_db = {}
zero_players = set()
data = []
validMatches = []

def getRating(name):
    subscriptionKey = "8e10ea4e445b4f8c829cfcb052b349a8"
    customConfigId = "1d708042-4fab-4d18-87d1-ea30fa4d9202"
    
    searchTerm = name + " futhead"

    url = 'https://api.cognitive.microsoft.com/bingcustomsearch/v7.0/search?' + 'q=' + searchTerm + '&' + 'customconfig=' + customConfigId + '&count=20'

    r = requests.get(url, headers={'Ocp-Apim-Subscription-Key': subscriptionKey})
    fut_json = r.json()

    playerUrl = ""
    reg2 = re.compile(r"\/players\/(\d+)")

    if ("webPages" not in fut_json):
        return False, 0
        
    for page in fut_json["webPages"]["value"]:
        if (reg2.search(page["url"]) is not None):
            playerUrl = page["url"]
        break
    
    rating = 0
    if playerUrl is not "":
        hdr = {'User-Agent': 'Mozilla/5.0'}
        
        try:
            req = Request(playerUrl, headers = hdr)
            html_fut = None
            html_fut = urlopen(req)
        except: return False, 0
                
        soup = BeautifulSoup(str(html_fut.read()), features="html.parser")
        
        ratingStr = repr(soup.find('div', attrs = {'class': 'playercard-rating'}).text)
        ratingStr = ratingStr.replace('\\n', '').replace(' ', '').replace('\\', '').replace('\'','')
        rating = int(ratingStr)

    time.sleep(.20)
    return True, rating

def loadPickles():
    pickles = [f for f in listdir(".") if isfile(join(".", f)) and ".pickle" in f]
    
    for f in pickles: 
        with open(f, 'rb') as handle:
            b = pickle.load(handle)
            for key, value in b.items():
                if (value not in player_db):
                    player_db[key] = (value)
                    if value == 0:
                        zero_players.add(key)
                elif (value in player_db and value != 0 and player_db[key] == 0):
                    player_db[key] = (value)
                    zero_players.remove(key)

def fixZeroPlayers():                    
    fixed = 0
    for player in zero_players.copy():
        success = False
        rating = 0
        try:
            success, rating = getRating(player)
            time.sleep(.5)
        except:
            continue
        
        if rating != 0:
            player_db[player] = rating
            zero_players.remove(player)
            fixed = fixed + 1
            print(rating)
            print(player + " " + str(player_db[player]))
    print("fixed: " + str(fixed))
    print("not fixed: " + str(len(zero_players)))

def loadTxts():
    txts = [f for f in listdir(".") if isfile(join(".", f)) and ".txt" in f]
    data.append("index,team1_avg,team2_avg,differential")
    
    for f in txts: 
        with open(f) as fp:
            for cnt, line in enumerate(fp):
                items = line.split(",")
                
                if len(items) < 16:
                    #print("len smaller than 16")
                    continue
                
                #team1 = []
                #team2 = []
                
                team1_scores = []
                team2_scores = []
                index = items.pop(0)
                link = items.pop(0)
                for i in items:                   
                    team = i[0]
                    name = i[2:].replace('\n', '')

                    if team == "1":
                        team1_scores.append(player_db[name])
                        #team1.append(name)
                    elif team == "2":
                        team2_scores.append(player_db[name])
                        #team2.append(name)
                    else:
                        #print("error")
                        continue
                
                if len(team1_scores) < 7 or len(team2_scores) < 7:
                    continue
                
                team1_avg = (sum(team1_scores) + team1_scores.count(0) * int(statistics.median(list(filter(lambda a: a != 0, team1_scores))))) / len(team1_scores)
                team2_avg = (sum(team2_scores) + team2_scores.count(0) * int(statistics.median(list(filter(lambda a: a != 0, team2_scores))))) / len(team2_scores)
                
                validMatches.append(line)
                data.append("{0},{1},{2},{3}".format(index, team1_avg, team2_avg, team1_avg - team2_avg))
                
    print(len(validMatches))
            
loadPickles()
#fixZeroPlayers()

#with open('fixed.pickle', 'wb') as handle:
#    pickle.dump(player_db, handle, protocol=pickle.HIGHEST_PROTOCOL)

loadTxts()
#with open('team_scores_diff.csv', 'w') as f:
#    for item in data:
#        f.write("%s\n" % item)
with open('valid_matches.txt', 'w') as f:
    for item in validMatches:
        f.write("%s\n" % item)