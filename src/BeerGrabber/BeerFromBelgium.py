'''
Created on Dec 19, 2014

@author: eegomar
'''

import os
import sys
import csv
import pickle
from collections import OrderedDict
import urllib.request
from bs4 import BeautifulSoup


if __name__ == '__main__':
    sys.argv
    
    baseurl = 'http://beerfrombelgium.blogspot.se'
    basepath = os.path.join('..', 'BeerFromBelgium')
    imagepath = os.path.join(basepath, 'images')
    
    proxy_info = {
    'user' : '*****',
    'pass' : '*****',
    'host' : "***.***.***.***",
    'port' : 0000
    }
    proxy = {"http" : "http://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info}
    
    proxy_support = urllib.request.ProxyHandler(proxy)
    opener = urllib.request.build_opener(proxy_support)
    req = opener.open( baseurl )
    html = req.read()
    
    beers = []
    imageId = 0
    pagePos = 0
    beerpos = -1
    last_page_url = baseurl
    soup = BeautifulSoup(html, 'lxml')
    link = soup.find('a', {'class': 'blog-pager-older-link'})
    while link:
        pagePos += 1
        print('Page:', pagePos, last_page_url)
        for div in soup.findAll('div', {'class': 'article-right'}):
            beerpos += 1
            header = div.find('div', {'class': 'article-header'})
            beerid = -1
            images = []
            for d in div.findAll('div', {}):
                if 'id' in d.attrs and d['id'].startswith('summary'):
                    beerid = d['id'][len('summary'):]
                    for d1 in d.findAll('div', {}):
                        if d1.a:
                            imageId += 1
                            imgurl = d1.a['href']
                            imgname = os.path.basename(imgurl)
                            imgname = imgname.replace('%', '')
                            imgname = str(imageId)+'_'+imgname.strip()
                            for sign in ['+', ':', '-']:
                                imgname = imgname.replace(sign, '_')
                             
                            imgpath = os.path.join(imagepath, '100', imgname)
                            if not os.path.exists(imgpath):
                                req = opener.open( imgurl )
                                html = req.read()
                                fh = open(imgpath, 'wb+')
                                fh.write(html)
                                fh.close()
                            images.append((imgname, imgurl))
            beername = header.h2.a.text.strip()
            beer_page = header.h2.a['href']
            beers.append((beername, beerid, beer_page, images))
            
            print(' '*2, beerpos, beername, '-', beerid)
            for imgname, _ in images:
                print(' '*6, imgname )
            
        last_page_url = link['href']
        req = opener.open( link['href'] )
        html = req.read()
        soup = BeautifulSoup(html, 'lxml')
        link = soup.find('a', {'class': 'blog-pager-older-link'})
        #break
    
    fh = open(os.path.join(basepath, 'beers.csv'), 'w+')
    writer = csv.writer(fh, 
                        delimiter='\t', 
                        quotechar='"',
                        lineterminator='\n')
    writer.writerow(["name", 'id', 'page_url', 'img_url', 'img_name'])
    for (beername, beerid, beer_page, images) in beers:
        for imgname, imgurl in images:
            writer.writerow((beername, beerid, beer_page, imgname, imgurl))
    fh.close()
    
    print('Pages Scanned:', pagePos)
    
    beerData = OrderedDict()
    for beerPos, (beername, beerid, beer_page, images) in enumerate(beers):
        print(beerPos, beername)
        print(' '*6, os.path.basename(beer_page) )
        req = opener.open( beer_page )
        html = req.read()
        soup = BeautifulSoup(html, 'lxml')
        texts = [] 
        for td in soup.findAll('td', {'class': 'tr-caption'}):
            texts.append( td.text.strip() )
        beerData[beerPos] = beername, beerid, beer_page, images, texts
    
    fh = open(os.path.join(basepath, 'beerdata.dat'), 'wb+')
    pickle.dump(beerData, fh)
    fh.close()
    
    
    
        
        
    
        