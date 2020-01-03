# -*- coding: UTF-8
from bs4 import BeautifulSoup
import requests
import time
import re
import xml.etree.ElementTree as ET
import time

siteUrl = 'https://www.tvsou.com'
groupPageDict = [
    {
        'name': 'cctv',
        'link': 'https://www.tvsou.com/epg/yangshi/'
    },
    {
        'name': 'weishi',
        'link': 'https://www.tvsou.com/epg/weishi/'
    }
]

'''
    ,
    {
        'name': 'shuzi',
        'link': 'https://www.tvsou.com/epg/shuzi/'
    },
    {
        'name': 'gaoqing',
        'link': 'https://www.tvsou.com/epg/gaoqing/'
    }
'''

blackChannelList = [
    'e4e3801d', #CCTV-5+
    '53eda06f', #CCTV-3
    'ddb707c0', #CCTV-6
    '13e8f054', #CCTV-8
    '63a3b196', #CCTV-4 Euro
    '9d22479f', #CCTV-4 America
    '6cf61152', #青海卫视
    '1d7e3bf3', #海峡卫视
    '8024c685', #旅游卫视
    'a3aa4d01', #吉林卫视
    'd6253770', #厦门卫视
    'e5815c01', #珠江频道
    'f0a3d1b2', #南方卫视
    'c33fa0cc', #延边卫视
    '8334edbd', #黄河卫视
    '5ccb1172', #康巴卫视
    'ccfe6b99' #广东南方卫视
    ]
whiteChannelList = []

def fetchContentFromLink(link):
    time.sleep(2)
    r = requests.get(link)
    if r.status_code == 200:
        return BeautifulSoup(r.text, 'html5lib')
    else:
        print("Fail to get %s, status code: %d" % (link, r.status_code))

def getChannelEntryFromElementA(a):
    i = a.find('i')
    if i != None and re.match('/epg/[0-9a-f]+/w\d', a['href']) != None:
        return {
            'name': i.string,
            'link': siteUrl + a['href']
        }
    return None

def fetchAllChannels(link):
    channels = []
    soup = fetchContentFromLink(link)
    if soup == None:
        return channels
    cListMain = soup.find('ul', attrs={'class': 'c_list_main'})
    if cListMain == None:
        return channels
    ElementAs = cListMain.find_all('a')
    if len(ElementAs) <= 0:
        return channels
    for a in ElementAs:
        channelEntry = getChannelEntryFromElementA(a)
        if channelEntry != None:
            channels.append(channelEntry)
    return channels

def getProgramEntry(tr):
    tdAs = tr.find_all('a')
    if len(tdAs) < 2:
        return None
    startTimeStr = tdAs[0].string
    title = tdAs[1].string
    timeArray = startTimeStr.split(":")
    if len(timeArray) < 2:
        return None
    return {
        'start': [int(timeArray[0]), int(timeArray[1]), 0],
        'end': [],
        'title': title
    }

def sortAndFillUpPrograms(programs):
    programs = sorted(programs, key = lambda x: x['start'][0]*60 + x['start'][1] )
    for i in range(len(programs)):
        if i == len(programs) - 1:
            programs[i]['end'] = [23, 59, 0]
        else:
            programs[i]['end'] = programs[i+1]['start']


def fetchProgramByChannel(channel):
    relateDayStr = 'w%d' % (time.localtime().tm_wday + 1)
    print("get programs of " + channel['name'])
    channel['programs'] = []
    soup = fetchContentFromLink(channel['link'])
    if soup == None:
        soup = fetchContentFromLink(channel['link'] + relateDayStr)
        if soup == None:
            return channel
    div = soup.find('div', attrs={'class': 'layui-tab-item layui-show'})
    if div == None:
        return channel
    table = div.find('table', attrs={'class': 'layui-table c_table'})
    if table == None:
        return channel
    trs = table.find_all('tr')
    for tr in trs:
        program = getProgramEntry(tr)
        if program != None:
            channel['programs'].append(program)
    sortAndFillUpPrograms(channel['programs'])

def generateOneProgram(program, channelId):
    dateStr = time.strftime("%Y%m%d", time.localtime())
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

def generateEpg(channels):
    tv = ET.Element('tv', attrib={'date': time.strftime("%Y-%m-%d", time.localtime())})
    for c in channels:
        cElem = generateOneChannel(c)
        tv.append(cElem)
        for p in c['programs']:
            pElem = generateOneProgram(p, c['id'])
            tv.append(pElem)
    #ET.dump(tv)
    tree = ET.ElementTree(tv)
    tree.write('tvSouEpg.xml', encoding = 'utf-8', xml_declaration=True)

def adjustChannels(channels):
    newList = []
    for c in channels:
        hashStr = c['link'].split('/')[-2]
        if hashStr not in blackChannelList:
            newList.append(c)
    return newList

def getOneChannelGroup(pdTitDiv, pdConDiv):
    group = {}
    if pdTitDiv.string == None:
        return None
    group['name'] = pdTitDiv.string
    group['channelList'] = []
    a_s = pdConDiv.find_all('a')
    for a in a_s:
        c = {
            'name': a.string,
            'hash': a['href'].split('/')[-2]
        }
        group['channelList'].append(c)
    return group

def getAllChannels():
    link = 'https://www.tvsou.com/epg/difang/'
    soup = fetchContentFromLink(link)
    if soup == None:
        return
    pdTitDivs = soup.find_all('div', attrs={'class': 'pd_tit'})
    pdConDivs = soup.find_all('div', attrs={'class': 'pd_con'})
    if len(pdTitDivs) != len(pdConDivs):
        return
    groups = []
    for i in range(len(pdTitDivs)):
        group = getOneChannelGroup(pdTitDivs[i], pdConDivs[i])
        if group != None:
            groups.append(group)
    for g in groups:
        print("===== " + g['name'] + " =====")
        for c in g['channelList']:
            print("|" + c['hash'] + '|' + c['name'])

def getChannelsFromTxtFile(filepath='tvSouChannelList.txt'):
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
        hashStr = lineStrs[1]
        name = lineStrs[-1].strip()
        channels.append({
            'name': name,
            'link': siteUrl + '/epg/' + hashStr + '/'
            })
    return channels

if __name__ == "__main__":
    #getAllChannels()
    #exit(0)
    totalChannels = getChannelsFromTxtFile()
    if len(totalChannels) <= 0:
        for groupPage in groupPageDict:
            print("process group " + groupPage['name'])
            channels = fetchAllChannels(groupPage['link'])
            totalChannels.extend(channels)
    totalChannels = adjustChannels(totalChannels)
    channelIdx = 0
    for c in totalChannels:
        channelIdx = channelIdx + 1
        c['id'] = channelIdx
        print(c['name'] + (" [id = %03d] " % c['id']) + ": " + c['link'])
        fetchProgramByChannel(c)
        for p in c['programs']:
            print('| ' + '-'.join(map(lambda x: "%02d" % x, p['start']))+ ' ~ ' + '-'.join(map(lambda x: "%02d" % x, p['end'])) + ' | ' + p['title'])
    generateEpg(totalChannels)
