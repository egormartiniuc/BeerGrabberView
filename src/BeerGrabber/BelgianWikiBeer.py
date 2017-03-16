'''
Created on Dec 19, 2014

@author: eegomar
'''

import sys
import re
import urllib.request
from bs4 import BeautifulSoup
import xlsxwriter

if __name__ == '__main__':
    """
    """
    sys.argv
    baseurl = "https://en.wikipedia.org/wiki/List_of_Belgian_beer"
    
    proxy_info = {
    'user' : '*****',
    'pass' : '*****',
    'host' : "***.***.***.***",
    'port' : 0000
    }
    proxy = {"https" : "http://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info}
    
    proxy_support = urllib.request.ProxyHandler(proxy)
    opener = urllib.request.build_opener(proxy_support)
    req = opener.open( baseurl )
    html = req.read()
    soup = BeautifulSoup(html, 'lxml')
    
    fields = []
    beers = []
    beerCount = 0
    for table in soup.findAll('table', {'class': 'wikitable sortable'}):
        i = -1
        for tr in table.findAll('tr'):
            i += 1
            if i==0:
                if not fields:
                    for th in tr.findAll('th'):
                        fields.append( th.b.text )
            else:
                beer = [td.text for td in tr.findAll('td')]
                search = re.search('[\d.]+', beer[2])
                if search:
                    beer[2] = float(search.group())
                beers.append( beer )
                beerCount += 1
            #if i > 10:
            #    break
    beerCount -= 4
    beers = beers[4:]
    
    print( beerCount, len(beers) )
    
    workbook = xlsxwriter.Workbook('..\\BeerBelgian\\beers.xlsx')
    worksheet = workbook.add_worksheet('beers')
    rowPos = 0
    worksheet.write(rowPos, 0, 'name')
    worksheet.write(rowPos, 1, 'type')
    worksheet.write(rowPos, 2, 'alcohol')
    worksheet.write(rowPos, 3, 'brewery')
    for beer in beers:
        rowPos += 1
        for colPos, v in enumerate(beer):
            worksheet.write(rowPos, colPos, v)
    workbook.close()
    
    