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

startIndex = sys.argv[1]
endIndex = sys.argv[2]
index = int(startIndex)
index_end = int(endIndex)

row_tries = 0
player_db = {}
zero_players = set()

phantomjs_path = r"C:\Users\asus\AppData\Local\Programs\Python\Python37\misc\phantomjs.exe"
browser = webdriver.PhantomJS(executable_path=phantomjs_path, service_log_path=os.path.devnull)
browser.set_window_size(1400, 1000)

dataUrl = "https://raw.githubusercontent.com/colonelsalt/COMP0036/master/epl-training.csv"
data = pd.read_csv(dataUrl)

f_rows = open(startIndex + ".txt", "wb", 0)                   
                    
def processESPN(espn_link, tryAgain):
    if tryAgain == 3:
        return False, "", None, None
    
    url_espn = None
    try:
        url_espn = urlopen(espn_link)
    except HTTPError as e:
        print(e)
        time.sleep(1)
        return processESPN(espn_link, tryAgain + 1)
    except Exception as e:
        print(e)
        return False, "", None, None
    
    time.sleep(.100)
    
    html_espn = str(url_espn.read())
    soup_espn = BeautifulSoup(html_espn, features="html.parser")
    spans = soup_espn.find_all('span', attrs = {'class': 'name'})
    tables = soup_espn.find_all('table', attrs = {'data-behavior': 'table_accordion'})
    teams = soup_espn.find_all('span', attrs = {'class' : 'short-name'})
    score_fields = soup_espn.find_all('div', attrs = {'class' : 'score-container'})
    
    score = ""
    for s in score_fields:
        score_i = repr(s.text)
        score_i = score_i.replace('\\t', '').replace('\\n', '').replace('\\xa0', '').replace('\\', '').replace('\'','')
        score = score + score_i 
    
    return True, score, teams, tables
    
def extractPlayers(table):
    team1 = []
    team2 = []
    team = 1;
    for table in tables:
        tbody = table.find('tbody')
        
        if tbody is None:
            return team1, team2
            
        tbody_spans = tbody.find_all('span', attrs = {'class': 'name'});
        for span in tbody_spans:
            if span.find('span', attrs = {'style' : ' display:inline-block; width: 24px;'}) is None:
                name = ''
                if span.find('span') is not None:
                  name = repr(span.contents[0])
                else:
                  name = repr(span.text) 

                name = name.replace('\\t', '').replace('\\n', '').replace('\\xa0', '').replace('\\', '').replace('\'','')
                if name:
                    if team == 1: team1.append(name)
                    else: team2.append(name)
        
        team = team + 1
    
    return team1, team2    
    
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
            print(player + " " + str(rating))
    print("fixed: " + str(fixed))
    print("not fixed: " + str(len(zero_players)))
    
loadPickles() 
   
while index <= index_end:
    if index >= len(data.index):
        break
    row = data.iloc[index, :]
    team1 = row['HomeTeam']
    team2 = row['AwayTeam']
    ftag = row['FTAG']
    fthg = row['FTHG']
    date = row['Date']
    date = datetime.datetime.strptime(date, '%d-%b-%y').strftime('%d %B %Y')

    link = "Premier League " + team1 + " vs " + team2 + " " + date
    print (link, flush=True)
    link = link.replace(" ", "%20")
    link = "http://www.espn.co.uk/search/results?q=" + link
    
    try:
        browser.get(link)
        time.sleep(1)
        html_fut = browser.page_source.encode('utf-8')
        time.sleep(1)
    except Exception as e:
        er = str(index) + ",ERROR try exception\n"
        print(er)
        print(e, flush=True)
        f_rows.write(er.encode("utf-8"))
        time.sleep(30)
        row_tries = row_tries + 1
        if row_tries == 2:
            index = index + 1
            row_tries = 0
        continue
        
    soup = BeautifulSoup(html_fut, features="html.parser")
    
    if soup is None:
        er = str(index) + ",ERROR soup is none\n"
        f_rows.write(er.encode("utf-8"))
        print(er, flush=True)
        time.sleep(10)
        row_tries = row_tries + 1
        if row_tries == 2:
            index = index + 1
            row_tries = 0
        continue
        
    links = soup.find_all('a', attrs = {'class' : 'gs-title'})
    espn_link = ""
    
    success = False
    score = None
    teams = None 
    tables = None
    
    for t in links:
        try:
            l = t['href']
            reg = re.compile(r"www\.espn\.co\.uk\/soccer\/(\w+)\?gameId=(\d+)")
            
            if reg.search(l) is not None:
                espn_link = reg.sub(repl=r'www.espn.co.uk/soccer/match?gameId=\g<2>', string=l)
                success, score, teams, tables = processESPN(espn_link, 0)
                
                if score != str(fthg) + str(ftag):
                    print(espn_link)
                    print("SCORE ERROR: " + score + " " + str(fthg) + str(ftag))
                    continue
            else:
                continue
            break
        except KeyError:
            continue
    
    print(espn_link)
    
    if(success is False):
        er = str(index) + ",ERROR ESPN not processed\n"
        f_rows.write(er.encode("utf-8"))
        print(er, flush=True)
        time.sleep(15)
        row_tries = row_tries + 1
        if row_tries == 2:
            index = index + 1
            row_tries = 0
        continue
    
    team1, team2 = extractPlayers(espn_link)
    
    new_row = str(index) + "," + espn_link
    
    for player in team1 + team2:
        if player in player_db:
            if (player_db[player] == 0):
                success, rating = getRating(player)
                player_db[player] = rating
        else:
            success, rating = getRating(player)
            player_db[player] = rating
       
        if player in team1: teamSgn = "1 "
        else: teamSgn = "2 "
        
        print(player + " " + str(player_db[player]))
        
        new_row = new_row + "," + teamSgn + player 
    
    new_row = new_row + "\n"
    print(new_row)
    f_rows.write(new_row.encode("utf-8"))
    
    with open(startIndex + '.pickle', 'wb') as handle:
        pickle.dump(player_db, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
    index = index + 1
    row_tries = 0
    
f_rows.close()
browser.close()    
os.execv(sys.executable, ['python', 'c.py', str(index_end + 1), str(index_end + 15)])