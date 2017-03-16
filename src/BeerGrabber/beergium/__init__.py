
import re
import os
import pickle
import requests

from time import clock
from time import sleep
from threading import Thread
from bs4 import BeautifulSoup
from operator import itemgetter
from multiprocessing import Pool
from collections import OrderedDict

from BeerGrabber.utils import ReadWriteFile
from BeerGrabber.utils import str2val
from BeerGrabber.utils import unicode2ascii
from BeerGrabber.utils import name2folter
from BeerGrabber.utils import ATTRIB_HREF
from BeerGrabber.utils import LXML
from BeerGrabber.utils import TAG_A
from BeerGrabber.utils import TAG_P
from BeerGrabber.utils import TAG_SPAN
from BeerGrabber.utils import TAG_DIV
from BeerGrabber.utils import TAG_TABLE

TASK_FINISHED = 0
TASK_TOTAL = 0

def collectBeerData(beerurl, beername, image_basepath, proxies):
    beerData = OrderedDict()
    
    beerData[BeerGiumGrabber.STR_SHORT_DESCRIPTION] = str()
    beerData[BeerGiumGrabber.STR_MORE_INFO] = str()
    beerData[BeerGiumGrabber.STR_TABLE_INFO] = []
    beerData[BeerGiumGrabber.STR_BEER_IMAGES] = []
    
    try:
        req = requests.get(beerurl, proxies=proxies)
    except Exception as err:
        print('Error (BeerPages) request:')
        print(' '*4, beerurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (BeerPages) soup:')
            print(' '*4, beerurl.encode())
            print(' '*4, err)
        else:
            images = []
            for a in soup.find_all(TAG_A, {'class': 'jqzoom'}):
                basename = os.path.basename(a[ATTRIB_HREF])
                image_path = os.path.join(image_basepath, basename)
                images.append((a[ATTRIB_HREF], image_path))
            for div in soup.find_all(TAG_DIV, {'id': 'short_description_content'}):
                beerData[BeerGiumGrabber.STR_SHORT_DESCRIPTION] = unicode2ascii(div.text)
                break
            for div in soup.find_all(TAG_DIV, {'id': 'more_info_sheets'}):
                beerData[BeerGiumGrabber.STR_MORE_INFO] = unicode2ascii(div.text)
                break
            for table in soup.find_all(TAG_TABLE, {'class': 'table-data-sheet table-bordered'}):
                for tr in table:
                    r = [unicode2ascii(td.text) for td in tr]
                    beerData[BeerGiumGrabber.STR_TABLE_INFO].append(r)
                break
            for image_url, image_path in images:
                if not os.path.exists(image_path):
                    try:
                        req = requests.get(image_url, proxies=proxies)
                    except Exception as err:
                        print('Error (BeerPages) request:')
                        print(' '*4, image_url.encode())
                        print(' '*4, err)
                    else:
                        if len(req.content) > 0:
                            try:
                                open(image_path, ReadWriteFile.WRITE_BINARY_NEW).write(req.content)
                            except Exception as err:
                                print('Error (BeerPages) BeerImage save:')
                                print(' '*4, err)
                            else:
                                beerData[BeerGiumGrabber.STR_BEER_IMAGES].append((image_url, image_path))
    return (beerurl, beername, beerData)

def resultBeerData(args):
    global graber
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, dic = args
    graber.beerData[(url, name)] = dic


class BeerGiumGrabber(Thread):
    
    THREAD_NUMBER = 10
    PROGRESS_UPDATE_TIME = 10
    
    STR_MORE_INFO = 'MORE INFO'
    STR_SHORT_DESCRIPTION = 'SHORT DESCRIPTION'
    STR_TABLE_INFO = 'TABLE INFO'
    STR_BEER_IMAGES = 'BEER IMAGES'
    
    def __init__(self, export_path, proxies, update_all=False):
        Thread.__init__(self)
        
        self.exportPath = export_path
        self.proxies = proxies
        self.update_all = update_all
        
        self._url_base = 'https://www.beergium.com'
        self._url_beers = 'https://www.beergium.com/en/5-breweries'
        self._url_beer_belgium = 'https://www.beergium.com/en/360-belgium'
        
        self.imageExportPath = os.path.join(self.exportPath, 
            bytes([105, 109, 97, 103, 101, 115]).decode())
        
        self.beerPages = OrderedDict()
        self.beerData = OrderedDict()
        
        self.beerPath = os.path.join(self.exportPath, 'Beers.pac')
        self.beerDataPath = os.path.join(self.exportPath, 'BeersData.pac')
        
        self.execTime = 0
    
    def runBeers(self):
        
        if (not self.update_all) and os.path.exists(self.beerPath):
            with open(self.beerPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerPages.update( pickle.load(fh) )
            print('Beers:', len(self.beerPages))
            return
        if (not self.update_all):
            return
        numPages = 0
        try:
            req = requests.get(self._url_beers, proxies=self.proxies)
        except Exception as err:
            print('Error (Beers) request')
            print(' '*4, self._url_country.encode())
            print(' '*4, err)
        else:
            try:
                soup = BeautifulSoup(req.content, LXML)
            except Exception as err:
                print('Error (Beers) soup:', err)
            else:
                pages = []
                for a in soup.find_all(TAG_A, href=re.compile('/en/5-breweries\?p=[\d]+')):
                    pages.append(int(a[ATTRIB_HREF].split(chr(61), 1)[1]))
                numPages = max(pages)
                
                for a in soup.find_all(TAG_A, {'class': 'product-name'}):
                    name = unicode2ascii(a.text)
                    self.beerPages[a[ATTRIB_HREF]] = [name, str(), str()]
                    for p in a.parent.parent.find_all(TAG_P, {'class': 'pro_list_manufacturer'}):
                        self.beerPages[a[ATTRIB_HREF]][1] = unicode2ascii(p.text)
                    for span in a.parent.parent.find_all(TAG_SPAN, {'itemprop': 'price'}):
                        self.beerPages[a[ATTRIB_HREF]][2] = unicode2ascii(span.text)
                
        print(numPages, len(self.beerPages))
        
        for pageId in range(2, numPages+1):
            url = '{}/en/5-breweries?p={}'.format(self._url_base, pageId)
            try:
                req = requests.get(url, proxies=self.proxies)
            except Exception as err:
                print('Error (Beers) request')
                print(' '*4, self._url_country.encode())
                print(' '*4, err)
            else:
                try:
                    soup = BeautifulSoup(req.content, LXML)
                except Exception as err:
                    print('Error (Beers) soup:', err)
                else:
                    for a in soup.find_all(TAG_A, {'class': 'product-name'}):
                        name = unicode2ascii(a.text)
                        self.beerPages[a[ATTRIB_HREF]] = [name, str(), str()]
                        for p in a.parent.parent.find_all(TAG_P, {'class': 'pro_list_manufacturer'}):
                            self.beerPages[a[ATTRIB_HREF]][1] = unicode2ascii(p.text)
                        for span in a.parent.parent.find_all(TAG_SPAN, {'itemprop': 'price'}):
                            self.beerPages[a[ATTRIB_HREF]][2] = unicode2ascii(span.text)
        
        print('Beers:', len(self.beerPages))
        with open(self.beerPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.beerPages, fh)
        
    def runBelgiumBeers(self):
        
        if (not self.update_all) and os.path.exists(self.beerPath):
            with open(self.beerPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerPages.update( pickle.load(fh) )
            print('Beers:', len(self.beerPages))
            return
        if (not self.update_all):
            return
        numPages = 0
        try:
            req = requests.get(self._url_beer_belgium, proxies=self.proxies)
        except Exception as err:
            print('Error (Beers) request')
            print(' '*4, self._url_country.encode())
            print(' '*4, err)
        else:
            try:
                soup = BeautifulSoup(req.content, LXML)
            except Exception as err:
                print('Error (Beers) soup:', err)
            else:
                pages = []
                for a in soup.find_all(TAG_A, href=re.compile('/en/360-belgium\?p=[\d]+')):
                    pages.append(int(a[ATTRIB_HREF].split(chr(61), 1)[1]))
                numPages = max(pages)
                for a in soup.find_all(TAG_A, {'class': 'product-name'}):
                    name = unicode2ascii(a.text)
                    self.beerPages[a[ATTRIB_HREF]] = [name, str(), str()]
                    for p in a.parent.parent.find_all(TAG_P, {'class': 'pro_list_manufacturer'}):
                        self.beerPages[a[ATTRIB_HREF]][1] = unicode2ascii(p.text)
                    for span in a.parent.parent.find_all(TAG_SPAN, {'itemprop': 'price'}):
                        self.beerPages[a[ATTRIB_HREF]][2] = unicode2ascii(span.text)
        
        print(numPages, len(self.beerPages))
        
        for pageId in range(2, numPages+1):
            url = '{}/en/360-belgium?p={}'.format(self._url_base, pageId)
            try:
                req = requests.get(url, proxies=self.proxies)
            except Exception as err:
                print('Error (Beers) request')
                print(' '*4, self._url_country.encode())
                print(' '*4, err)
            else:
                try:
                    soup = BeautifulSoup(req.content, LXML)
                except Exception as err:
                    print('Error (Beers) soup:', err)
                else:
                    for a in soup.find_all(TAG_A, {'class': 'product-name'}):
                        name = unicode2ascii(a.text)
                        self.beerPages[a[ATTRIB_HREF]] = [name, str(), str()]
                        for p in a.parent.parent.find_all(TAG_P, {'class': 'pro_list_manufacturer'}):
                            self.beerPages[a[ATTRIB_HREF]][1] = unicode2ascii(p.text)
                        for span in a.parent.parent.find_all(TAG_SPAN, {'itemprop': 'price'}):
                            self.beerPages[a[ATTRIB_HREF]][2] = unicode2ascii(span.text)
        
        print('Beers:', len(self.beerPages))
        with open(self.beerPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.beerPages, fh)
            
    def runBeerData(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        
        
        if (not self.update_all) and os.path.exists(self.beerDataPath):
            with open(self.beerDataPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerData.update( pickle.load(fh) )
            print('Beer-data:', len(self.beerData))
            return
        if (not self.update_all):
            return
        
        pool = Pool(processes=self.THREAD_NUMBER)
        for beer_url, (beer_name, _, _) in self.beerPages.items():
            #if beer_url != 'https://www.beergium.com/en/founders-brewing-company/2826-founders-imperial-stout-35cl.html':
            #    continue
            pool.apply_async(collectBeerData, 
                args = (beer_url, beer_name, self.imageExportPath, self.proxies),
                callback = resultBeerData)
            TASK_TOTAL += 1
            #break
        pool.close()
        
        print('Total tasks:', TASK_TOTAL)
        
        while ((TASK_TOTAL != TASK_FINISHED)):
            print( 'executed:', TASK_FINISHED, 
                   'from:', TASK_TOTAL, 
                   'progress:',  TASK_FINISHED / TASK_TOTAL)
            sleep(self.PROGRESS_UPDATE_TIME)
        pool.join()
        
        print('Beer-data:', len(self.beerData))
        
        with open(self.beerDataPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.beerData, fh)  
    
    def run(self):
        
        _tick_time = clock()
        self.execTime = 0
        
        os.makedirs(self.exportPath, exist_ok=True)
        os.makedirs(self.imageExportPath, exist_ok=True)
        
        self.beerPages.clear()
        self.beerData.clear()
        
        self.runBeers()
        #self.runBelgiumBeers()
        self.runBeerData()
        
        self.execTime = clock() - _tick_time 
    
    
    
if __name__ == '__main__':
    import sys
    
    proxy_info = {
    'user' : '*****',
    'pass' : '*****',
    'host' : "***.***.***.***",
    'port' : 0000
    }
    
    proxy = {"http" : "http://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info,
             "https" : "https://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info}
    #proxy.clear()
    
    graber = BeerGiumGrabber(
        os.path.join('..', '..', 'BeerGium'), 
        proxy,
        update_all=False)
    
    graber.start()
    graber.join()
    print()
    
    INFO = [('Country', str()),
        ('Brewery', str()),
        ('Style', str()),
        ('ABV', str()),
        ('Color', str()),
        ('RateBeer Overall', str()),
        ('RateBeer Style', str()),
        ('Size', str()),
    ]
    FIELDS = ['Beer']
    FIELDS.extend([n for n,_ in INFO])
    FIELDS.append('Price')
    FIELDS.append(graber.STR_SHORT_DESCRIPTION.capitalize())
    print(chr(9).join(FIELDS))
    
    for _, beer_name in graber.beerData:
        row = [beer_name]
        beerData = graber.beerData[(_, beer_name)]
        if not beerData[graber.STR_TABLE_INFO]:
            continue
        info = OrderedDict(INFO)
        info.update(OrderedDict(beerData[graber.STR_TABLE_INFO]))
        row.extend(info.values())
        price = graber.beerPages[_][2].strip()
        price = price.replace(chr(44), chr(46)) if price else '-1.'
        row.append(price)
        row.append(beerData[graber.STR_SHORT_DESCRIPTION])
        
        print(chr(9).join(row))
    