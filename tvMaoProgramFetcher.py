# -*- coding: UTF-8
from bs4 import BeautifulSoup
import requests
import time
import re
import xml.etree.ElementTree as ET
import time
from datetime import date, timedelta
import base64
import codecs

siteUrl = 'https://www.tvmao.com'
logToFile = 1
gLogFile = 'log.log'

def debugTrace(str):
    if logToFile == 1:
        writeToFile(gLogFile, str)
    else:
        print(str)

def writeToFile(filePath, str):
    targetFile = codecs.open(filePath, 'a+', 'utf-8')
    targetFile.write(str + '\n')
    targetFile.close()

def fetchContentFromLink(link, json = False):
    time.sleep(2)
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0',
            'Connection' : 'keep-alive', 'Cache-Control': 'no-cache'}
    r = requests.get(link, headers = headers)
    if r.status_code == 200:
        if json:
            return r.json()
        else:
            return BeautifulSoup(r.text, 'html5lib')
    else:
        debugTrace("Fail to get %s, status code: %d" % (link, r.status_code))

def getProgramEntry(li, day):
    entry = {
        'day': day,
        'title': '',
        'start': [],
        'end': []
    }
    if li.div == None:
        return None
    spans = li.div.find_all('span', recursive = False)
    if len(spans) < 2:
        return None
    #if re.match("am|pm|nt", spans[0]['class']) == None:
    #    return None
    timeStrs = spans[0].string.split(':')
    entry['start'] = map(lambda x: int(x), timeStrs)
    entry['start'].append(0)
    #if spans[1]['class'] != 'p_show' or spans[1].a == None:
    #    return None
    if spans[1].a == None:
        entry['title'] = spans[1].string
    else:
        entry['title'] = spans[1].a.string
    return entry

def sortAndFillUpPrograms(programs, day):
    filterPrograms = filter(lambda x: x['day'] == day, programs)
    filterPrograms = sorted(filterPrograms, key = lambda x: x['start'][0]*60 + x['start'][1] )
    for i in range(len(programs)):
        if i == len(programs) - 1:
            programs[i]['end'] = [23, 59, 0]
        else:
            programs[i]['end'] = programs[i+1]['start']

def getProgramLinkForNoonNight(soup):
    form = soup.find('form', attrs = {'name': 'QF', 'id': 'searchform'})
    if form == None:
        return ''
    q = form['q']
    a = form['a']
    id = form.button['id']
    _keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    if q == None or a == None or id == None:
        return ''
    str1 = "|" + q;
    v = base64.b64encode(str1.encode('utf-8'));
    str2 = id + "|" + a;
    w = base64.b64encode(str2.encode('utf-8'));
    wday = date.today().isoweekday()
    F = _keyStr[wday * wday];
    return siteUrl + '/api/pg?p=' + ( F + w.encode('utf-8') + v.encode('utf-8'));

def fetchProgramByChannelOfOneDay(channel, day):
    debugTrace("weekday %d" % day.isoweekday())
    link = channel['link'] + ("-w%d.html" % day.isoweekday())
    debugTrace(link)
    soup = fetchContentFromLink(link)
    if soup == None:
        return channel
    noonNightLink = getProgramLinkForNoonNight(soup)
    json = fetchContentFromLink(noonNightLink, json = True)
    jsonSoup = BeautifulSoup(json[1], 'html5lib')
    jsonLis = jsonSoup.find_all('li')
    #debugTrace(json)
    ul = soup.find('ul', attrs={'id': 'pgrow'})
    if ul == None:
        return channel
    lis = ul.find_all('li')
    lis.extend(jsonLis)
    for li in lis:
        program = getProgramEntry(li, day)
        if program != None:
            channel['programs'].append(program)
    sortAndFillUpPrograms(channel['programs'], day)

def fetchProgramByChannel(channel):
    debugTrace("get programs of " + channel['name'])
    channel['programs'] = []
    today = date.today()
    weekdays = map(lambda x: today + timedelta(x) ,range(7 - today.weekday()))
    for day in weekdays:
        fetchProgramByChannelOfOneDay(channel, day)
    return channel

def generateOneProgram(program, channelId):
    dateStr = program['day'].strftime("%Y%m%d")
    startStr = dateStr + ''.join(map(lambda x: "%02d" % x, program['start'])) + ' +0800'
    endStr = dateStr + ''.join(map(lambda x: "%02d" % x, program['end'])) + ' +0800'
    p = ET.Element('programme ', attrib={'start': startStr, 'stop': endStr, 'channel': str(channelId)})
    title = ET.SubElement(p, 'title', attrib={'lang': 'zh'})
    title.text = program['title']
    return p

def generateOneChannel(channel):
    cElem = ET.Element('channel', attrib={'id': str(channel['id'])})
    displayName = ET.SubElement(cElem, 'display-name')
    displayName.text = channel['name']
    return cElem

def generateEpg(channels, output='epgMao.xml'):
    tv = ET.Element('tv', attrib={'date': time.strftime("%Y-%m-%d", time.localtime())})
    for c in channels:
        cElem = generateOneChannel(c)
        tv.append(cElem)
        for p in c['programs']:
            pElem = generateOneProgram(p, c['id'])
            tv.append(pElem)
    #ET.dump(tv)
    tree = ET.ElementTree(tv)
    tree.write(output, encoding = 'utf-8', xml_declaration=True)

def getChannelsFromTxtFile(filepath='tvMaoChannelList.txt'):
    lines = []
    try:
        f = open(filepath)
        lines = f.readlines()
    finally:
        if f:
            f.close()
    channels = []
    for line in lines:
        line = line.decode('utf-8')
        lineStrs = line.split('|')
        if len(lineStrs) < 3:
            continue
        path = lineStrs[1]
        name = lineStrs[-1].strip()
        channels.append({
            'name': name,
            'link': siteUrl + path
            })
    return channels

if __name__ == "__main__":
    totalChannels = getChannelsFromTxtFile()
    channelIdx = 0
    for c in totalChannels:
        channelIdx = channelIdx + 1
        c['id'] = channelIdx
        debugTrace(c['name'] + (" [id = %03d] " % c['id']) + ": " + c['link'])
        fetchProgramByChannel(c)
        for p in c['programs']:
            debugTrace(p['day'].strftime("%Y%m%d") + '| ' + '-'.join(map(lambda x: "%02d" % x, p['start']))+ ' ~ ' + '-'.join(map(lambda x: "%02d" % x, p['end'])) + ' | ' + p['title'])
    generateEpg(totalChannels)
