'''
Created on Jun 3, 2016

@author: emartini
'''

import os
import re
import csv
import sys
import pickle
from collections import OrderedDict
import urllib.request
from bs4 import BeautifulSoup
from bs4.element import Tag

def code(value):
    s = str()
    for c in value:
        if ord(c) < 128:
            s += c
        else:
            s += ' '
    return s.strip()

def iterAll(sp, d=OrderedDict()):
    name = 'Unknown'
    for v in sp:
        if isinstance(v, Tag):
            if v.name == 'h2':
                name = code(v.text)
            elif v.name == 'p':
                text = code(v.text)
                try:
                    d[name].append(text)
                except KeyError:
                    d[name] = [text]
            iterAll(v)
        else:
            pass
    return d

if __name__ == '__main__':
    sys.argv
    
    baseurl = 'http://belgium.beertourism.com/belgian-beers'
    basepath = os.path.join('..', 'BeerTourism')
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
    
    soup = BeautifulSoup(html, 'lxml')
    
    pages = {}
    pos = -1
    imgformar = re.compile('.[\w+]?')
    for div in soup.findAll('div', {'class': 'entry'}):
        beername = None
        page = None
        img = div.find('img')
        imgurl = img['src']
        imgname = os.path.basename(imgurl)
        imgname = imgname.replace('%', '')
        if '?' in imgname:
            imgname, _ = imgname.split('?')
        imgname = imgname.strip()
        imgpath = os.path.join(imagepath, '100', imgname)
        if not os.path.exists(imgpath):
            req = opener.open( imgurl )
            html = req.read()
            fh = open(imgpath, 'wb+')
            fh.write(html)
            fh.close()
        
        for p in div.findAll('p', {}):
            item = p.find('strong')
            if item:
                beername = item.text
                beername = beername.strip()
            item = p.find('a')
            if item:
                page = item['href']
        if beername and page:
            pos += 1
            pages[pos] = (beername, page, imgurl, imgname)
        else:
            print(beername, page, imgurl)
    print('Beers Count:', len(pages))
    
    beers = list(pages.values())
    beers.sort()
    
    fh = open(os.path.join(basepath, 'beers.csv'), 'w+')
    writer = csv.writer(fh, 
                        delimiter='\t', 
                        quotechar='"',
                        lineterminator='\n')
    writer.writerow(["name", 'page_url', 'img_url', 'img_name'])
    for (beername, page, imgurl, imgname) in beers:
        writer.writerow((beername, page, imgurl, imgname))
    fh.close()
    
    fields = ['Beer Style', 'The Beer', 'Alcohol', 'Fermentation', 'Ingredients', 'Colour & Transparency',
              'Serving Temperature', 'Serving Glass', 'Character, Tastes & Aromas', 'Culinary',
              'Keeping and Storage', 'Availability']
    
    beerData = OrderedDict()
    for pos, (beername, page, imgurl, imgname) in enumerate(beers):
        print(pos, beername)
        req = opener.open( page )
        html = req.read()
        soup = BeautifulSoup(html, 'lxml')
        data = iterAll(soup)
        for name in ['Unknown', 'More Beer']:
            if name in data:
                _ = data.pop(name)
        images = []
        for img in soup.findAll('img', {'class': 'image_normal'}):
            imgurl = img['src']
            imgname = os.path.basename( imgurl )
            imgname = imgname.replace('%', '')
            if '?' in imgname:
                imgname, _ = imgname.split('?')
            imgname = imgname.strip()
            imgpath = os.path.join(imagepath, 'orig', imgname)
            print(' '*4, imgname )
            if not os.path.exists(imgpath):
                req = opener.open( imgurl )
                html = req.read()
                fh = open(imgpath, 'wb+')
                fh.write(html)
                fh.close()
            images.append((imgname, imgurl, imgpath))
        
        data['IMAGES'] = images
        beerData[pos] = data
    
    fh = open(os.path.join(basepath, 'beerdata.dat'), 'wb+')
    pickle.dump(beerData, fh)
    fh.close()
    
        
        