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
from BeerGrabber.utils import ATTRIB_SRC
from BeerGrabber.utils import LXML
from BeerGrabber.utils import TAG_A
from BeerGrabber.utils import TAG_P
from BeerGrabber.utils import TAG_SPAN
from BeerGrabber.utils import TAG_DIV
from BeerGrabber.utils import TAG_TABLE
from BeerGrabber.utils import TAG_IMG
from BeerGrabber.utils import TAG_TR
from BeerGrabber.utils import TAG_TD

TASK_FINISHED = 0
TASK_TOTAL = 0

def collectBeerData(base_url, beerurl, beername, image_basepath, proxies):
    beerData = OrderedDict()
    beerData[BeerPlanetGrabber.STR_BEER_IMAGES] = []
    beerData[BeerPlanetGrabber.STR_TABLE_INFO] = []
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
            try:
                for img in soup.find_all(TAG_IMG, {'class': 'img_brd'}):
                    basename = os.path.basename(img[ATTRIB_SRC])
                    image_path = os.path.join(image_basepath, basename)
                    image_url = chr(47).join([base_url, img[ATTRIB_SRC]])
                    images.append((image_url, image_path))
            except Exception as err:
                print('Error (BeerPages) soup(img):')
                print(' '*4, err)
            for td in soup.find_all(TAG_TD, {'class': 'text_beer'}):
                r = []
                data = td.text.strip()
                for v in data.split('\n'):
                    for val in v.split('\r'):
                        if val.strip():
                            r.append(val.strip())
                if r:
                    beerData[BeerPlanetGrabber.STR_TABLE_INFO].append(r)
            for image_url, image_path in images:
                if os.path.exists(image_path):
                    beerData[BeerPlanetGrabber.STR_BEER_IMAGES].append((image_url, image_path))
                else:
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
                                beerData[BeerPlanetGrabber.STR_BEER_IMAGES].append((image_url, image_path))
    
    return (beerurl, beername, beerData)

def resultBeerData(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, dic = args
    graber_.beerData[(url, name)] = dic



class BeerPlanetGrabber(Thread):
    
    THREAD_NUMBER = 10
    PROGRESS_UPDATE_TIME = 10
    
    STR_BEER_IMAGES = 'BEER IMAGES'
    STR_TABLE_INFO = 'TABLE INFO'
    
    def __init__(self, export_path, proxies, update_all=False):
        Thread.__init__(self)
        
        self.exportPath = export_path
        self.proxies = proxies
        self.update_all = update_all
        
        self._url_base = 'http://www.beerplanet.eu'
        self._url_beer_types = 'http://www.beerplanet.eu/index.php?cnt=2'
        
        self.imageExportPath = os.path.join(self.exportPath, 
            bytes([105, 109, 97, 103, 101, 115]).decode())
        
        self.beerTypes = OrderedDict()
        self.beerPages = OrderedDict()
        self.beerData = OrderedDict()
        
        self.beerPath = os.path.join(self.exportPath, 'Beers.pac')
        self.beerDataPath = os.path.join(self.exportPath, 'BeersData.pac')
        
        self.execTime = 0
    
    def runBeers(self):
        if (not self.update_all) and os.path.exists(self.beerPath):
            with open(self.beerPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerTypes.update( pickle.load(fh) )
                self.beerPages.update( pickle.load(fh) )
            print('Beers:', len(self.beerPages))
            return
        if (not self.update_all):
            return
        try:
            req = requests.get(self._url_beer_types, proxies=self.proxies)
        except Exception as err:
            print('Error (Beers) request')
            print(' '*4, self._url_beer_types.encode())
            print(' '*4, err)
        else:
            try:
                soup = BeautifulSoup(req.content, LXML)
            except Exception as err:
                print('Error (Beers) soup:', err)
            else:
                for a in soup.find_all(TAG_A, {'class': 'footer'}):
                    name = unicode2ascii(a.text)
                    url = chr(47).join([self._url_base, a[ATTRIB_HREF]])
                    self.beerTypes[url] = [name, OrderedDict()]
        
        for type_url, (name, beers) in self.beerTypes.items():
            try:
                req = requests.get(type_url, proxies=self.proxies)
            except Exception as err:
                print('Error (Beers) request')
                print(' '*4, type_url.encode())
                print(' '*4, err)
            else:
                try:
                    soup = BeautifulSoup(req.content, LXML)
                except Exception as err:
                    print('Error (Beers) soup:', err)
                else:
                    for a in soup.find_all(TAG_A, {'class': 'beer'}):
                        beer_name = unicode2ascii(a.text)
                        beer_url = chr(47).join([self._url_base, a[ATTRIB_HREF]])
                        if 'UBID=' in beer_url:
                            beers[beer_url] = beer_name
                            self.beerPages[beer_url] = beer_name
        
        print('Beers:', len(self.beerPages))
        with open(self.beerPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.beerTypes, fh)
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
        for beer_url, beer_name in self.beerPages.items():
            pool.apply_async(collectBeerData, 
                args = (self._url_base, beer_url, beer_name, 
                        self.imageExportPath, self.proxies),
                callback = resultBeerData)
            TASK_TOTAL += 1
            #if TASK_TOTAL > 10:
            #    break
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
        
        self.beerTypes.clear()
        self.beerPages.clear()
        self.beerData.clear()
        
        self.runBeers()
        self.runBeerData()
        
        self.execTime = clock() - _tick_time 
    
    def beerRows(self, print_ = False):
        
        FIELDS = ['name', 'type']
        ROWS = []
        
        INFO = [('Accessory:', str()),
            ('Alcohol:', str()),
            ('Awards:', str()),
            ('Brewery:', str()),
            ('Color:', str()),
            ('Country:', str()),
            ('Hop:', str()),
            ('IBU:', str()),
            ('Malt:', str()),
            ('Plato:', str()),
            ('Rating:', str()),
            ('Recipes:', str()),
            ('Served:', str()),
            ('Type:', str())]
        
        FIELDS.extend([v for v,_ in INFO])
        FIELDS.append('Description')
        if print_:
            print(chr(9).join(FIELDS))
        FIELDS.append(self.STR_BEER_IMAGES)
        for _, (beer_type, beers) in self.beerTypes.items():
            for beer_url, beer_name in beers.items():
                row = [beer_name, beer_type]
                beerData = self.beerData[(beer_url, beer_name)]
                info = beerData[self.STR_TABLE_INFO]
                for i, r in enumerate(info):
                    if i == 0:
                        _, *r = r
                        d = OrderedDict(INFO)
                        ir = len(r)
                        for iv, v in enumerate(r, 1):
                            if v.endswith(':'):
                                if iv < ir:
                                    if (not r[iv].endswith(':')):
                                        d[v] = unicode2ascii(r[iv])
                        row.extend(d.values())
                    elif i == 1:
                        row.append(unicode2ascii(chr(10).join(r)))
                    else:
                        print('pass row:', r)
                if len(info) == 0:
                    d = OrderedDict(INFO)
                    row.extend(d.values())
                    row.append(str())
                elif len(info) == 1:
                    row.append(str())
                if print_:
                    print(chr(9).join(map(str, row)))
                images = [image_path for _, image_path in beerData[self.STR_BEER_IMAGES]]
                if not images:
                    print(beer_name, beer_type, beer_url)
                    
                row.append(images)
                ROWS.append(row)
        
        return FIELDS, ROWS
                
    
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
    
    graber_ = BeerPlanetGrabber(os.path.join('..', '..', 'BeerPlanet'), proxy,
        update_all=False)
    
    graber_.start()
    graber_.join()
    print()
    graber_.beerRows(print_=False)
    