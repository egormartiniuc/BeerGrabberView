'''
Created on Jun 2, 2016

@author: emartini
'''
import sys
import os
import pickle
import urllib.request
from bs4 import BeautifulSoup
import csv
from collections import OrderedDict

def code(value):
    s = str()
    for c in value:
        if ord(c) < 128:
            s += c
        else:
            s += ' '
    return s.strip()
        

if __name__ == '__main__':
    sys.argv
    
    baseurl = "http://www.deliriumcafe.be/bieres.html"
    basepath = os.path.join('..', 'BeerDelirium')
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
    #text = html.decode('ISO-8859-1') Latin
    #text = html.decode('ISO 3166-2') France
    soup = BeautifulSoup(html, "lxml")
    
    pages = OrderedDict()
    for ol in soup.findAll('ol'):
        for li in ol.findAll('li'):
            if ol.li.text == li.text:
                continue
            text = li.text.replace('\n', '')
            text = text.replace('\r', '')
            text = text.replace('\t', '')
            text = text.strip()
            if not text:
                continue
            pages[int(text)] = li.a['href']
    
    beerPages = []
    for ul in soup.findAll('ul', {'class': 'products-grid'}):
        for li in ul.findAll('li'):
            name = li.a['title']
            url = li.a['href']
            img = None
            if li.img:
                img = li.img['src']
            beerPages.append((name, url, img))
    pageList = list(pages)
    for page in pageList:
        print(page)
        req = opener.open( pages[page] )
        html = req.read()
        soup = BeautifulSoup(html, "lxml")
        for ul in soup.findAll('ul', {'class': 'products-grid'}):
            for li in ul.findAll('li'):
                name = li.a['title']
                url = li.a['href']
                img = None
                if li.img:
                    img = li.img['src']
                beerPages.append((code(name), url, img))
        for ol in soup.findAll('ol'):
            for li in ol.findAll('li'):
                if ol.li.text == li.text:
                    continue
                text = li.text.replace('\n', '')
                text = text.replace('\r', '')
                text = text.replace('\t', '')
                text = text.strip()
                if not text:
                    continue
                if li.a:
                    if int(text) > 1 and int(text) not in pageList:
                        pages[int(text)] = li.a['href']
                        pageList.append(int(text))
    
    print(len(beerPages))
    
    #sys.exit(0)
    
    fh = open(os.path.join(basepath, 'beers.csv'), 'w+')
    writer = csv.writer(fh, 
                        delimiter='\t', 
                        quotechar='"',
                        lineterminator='\n')
    writer.writerow(["name", 'page_url', 'img_url'])
    for (name, url, img) in beerPages:
        writer.writerow((name, url, img))
    fh.close()
    
    rows = OrderedDict()
    for itempos, (name, pageurl, img) in enumerate(beerPages):
        print(itempos, name)
        rows[itempos] = OrderedDict()
        rows[itempos]['name'] = name
        rows[itempos]['page_url'] = pageurl
        rows[itempos]['img_url'] = img
        rows[itempos]['img_file'] = str()
        rows[itempos]['img_urls_pretty'] = []
        rows[itempos]['img_files_pretty'] = []
        rows[itempos]['data'] = OrderedDict()
        #if itempos < 1163:
        #    continue
        fileImgName = str()
        if img:
            fileImgName = os.path.join(imagepath, '100', os.path.basename(img))
            rows[itempos]['img_file'] = fileImgName
            if not os.path.exists(fileImgName):
                req = opener.open( img )
                html = req.read()
                fh = open(fileImgName, 'wb+')
                fh.write(html)
                fh.close()
        req = opener.open( pageurl )
        html = req.read()
        soup = BeautifulSoup(html, "lxml")
        prettyImages = []
        for div in soup.findAll('div', {'class': 'more-views'}):
            for li in div.ul.findAll('li'):
                prettyImages.append(li.a['href']) 
        rows[itempos]['img_urls_pretty'] = prettyImages
        
        for div_ in soup.findAll('div', {'class': 'short-description'}):
            texts = []
            for i, div in enumerate(div_.findAll('div')):
                text = code(div.text)
                text = text.replace("\n", ' ')
                text = text.replace("\r", ' ')
                text = text.replace("\t", ' ')
                text = text.strip()
                texts.append(text)
            for i, text in enumerate(texts):
                rows[itempos]['data'][i] = text
        for prettyImage in prettyImages:
            fileImgName = os.path.join(imagepath, 'orig', os.path.basename(prettyImage))
            rows[itempos]['img_files_pretty'].append(fileImgName)
            if not os.path.exists(fileImgName):
                req = opener.open( prettyImage )
                html = req.read()
                fh = open(fileImgName, 'wb+')
                fh.write(html)
                fh.close()
        #if itempos > 10:
        #    break
    fh = open(os.path.join(basepath, 'beerdata.dat'), 'wb+')
    pickle.dump(rows, fh)
    fh.close()
    
            