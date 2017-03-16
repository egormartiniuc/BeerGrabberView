
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
from BeerGrabber.utils import LXML
from BeerGrabber.utils import ATTRIB_SRC
from BeerGrabber.utils import ATTRIB_HREF
from BeerGrabber.utils import TAG_A
from BeerGrabber.utils import TAG_TR
from BeerGrabber.utils import TAG_IMG
from BeerGrabber.utils import TAG_SMALL


TASK_FINISHED = 0
TASK_TOTAL = 0


def collectCountryBrewers(url_base, countryurl, countryname, proxies):
    brewers = OrderedDict()
    try:
        req = requests.get(countryurl, proxies=proxies)
    except Exception as err:
        print('Error (BeerBrewers) request')
        print(' '*4, countryurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (BeerBrewers) soup:', countryurl.encode(), err)
        else:
            for a in soup.find_all(TAG_A, href=re.compile('/brewers/[\W\w\d]+/[\d]+/')):
                try:
                    url_ = url_base + a[ATTRIB_HREF]
                    name = unicode2ascii(a.text)
                except Exception as err:
                    print('Error (BeerBrewers) iterator name:', err)
                    continue
                else:
                    try:
                        row = [name] + [unicode2ascii(td.text) for td in a.parent.parent]
                    except Exception as err:
                        print('Error (BeerBrewers) iterator row:', err)
                        row = [name, ] + [str()]*5
                    finally:
                        brewers[url_] = tuple(row)
    return countryurl, countryname, brewers

def resultCountryBrewers(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, brewers = args
    graber_.countryBreweryPages[(url, name)] = brewers

def collectBeers(url_base, breweryurl, breweryname, proxies):
    beerUrls = OrderedDict()
    soup = None
    req = None
    try:
        req = requests.get(breweryurl, proxies=proxies)
    except Exception as err:
        print('Error (BeerBrewers) request')
        print(' '*4, breweryurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (BeerBrewers) soup:', breweryurl.encode(), err)
        else:
            for tr in soup.find_all(TAG_TR, {'valign': 'middle'}):
                try:
                    beer_name = unicode2ascii(tr.td.a.text)
                    beer_url = url_base + tr.td.a[ATTRIB_HREF]
                except Exception as err:
                    print('Error (BeerBrewers) iterator beer name:', err)
                    continue
                else:
                    try:
                        row = [beer_name, ] + [unicode2ascii(td) if isinstance(td, str) else unicode2ascii(td.text) for td in tr][1:]
                    except Exception as err:
                        print('Error (BeerBrewers) iterator row:', err)
                        row = [beer_name, ] + [str()]*5
                    finally:
                        beerUrls[beer_url] = tuple(row)
    return (breweryurl, breweryname, beerUrls)

def resultBeers(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, dic = args
    graber_.beerPages[(url, name)] = dic

def collectBeerPages(beerurl, beername, image_basepath, proxies):
    
    row = [beername, beerurl, image_basepath, None, None, None, None, 0, None]
    
    try:
        req = requests.get(beerurl, proxies=proxies)
    except Exception as err:
        print('Error (BeerImage) request:')
        print(' '*4, beerurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (BeerImage) soup:')
            print(' '*4, beerurl.encode())
            print(' '*4, err)
        else:
            image_url = None
            image_path = None
            image_basename = None
            info = None
            
            for a in soup.find_all(TAG_A, href=re.compile('/beerstyles/[\w\W\d]+/[\d]+')):
                row[8] = unicode2ascii(a.text)
                if row[8] != 'Top By Style':
                    break
            
            for img in soup.find_all(TAG_IMG, {'itemprop': 'image'}):
                image_url = img[ATTRIB_SRC]
                image_basename = os.path.basename(image_url)
                image_path = os.path.join(image_basepath, image_basename)
            
            for small in soup.find_all(TAG_SMALL):
                data = unicode2ascii(small.text)
                if 'RATINGS:' in data:
                    info = data
                    break
                elif len(small) > 8:
                    info = data
                    break
            
            if info is None:
                for a in soup.find_all('a', href=re.compile('/beer/[\W\w\d]+/[\d]+/')):
                    if b'Proceed to the aliased beer' in a.parent.text.encode():
                        info = unicode2ascii(a.parent.text)
                        break
            
            if info is None and b"we didn't find this beer" in req.content:
                info = unicode2ascii(req.content.decode())
            
            row[3] = image_url
            row[4] = image_path
            row[5] = info
            
            if image_url and (os.path.exists(image_path)):
                row[7] = os.stat(image_path).st_size
            elif image_url and (not os.path.exists(image_path)):
                p, _ = os.path.split(image_url)
                p, _ = os.path.split(p)
                img_url = chr(47).join([p, image_basename])
                row[6] = img_url
                try:
                    req = requests.get(img_url, proxies=proxies)
                except Exception as err:
                    print('Error (BeerImage) image:')
                    print(' '*4, beerurl.encode())
                    print(' '*4, err)
                else:
                    iLen = len(req.content)
                    if iLen > 0:
                        try:
                            open(image_path, ReadWriteFile.WRITE_BINARY_NEW).write(req.content)
                        except Exception as err:
                            print('Error (BeerImage) image)save:')
                            print(' '*4, beerurl.encode())
                            print(' '*4, err)
                        else:
                            row[7] = iLen
    return (beerurl, beername, row)

def resultBeerPages(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, row = args
    graber_.beerData[(url, name)] = row

class RateBeerGrabber(Thread):
    
    THREAD_NUMBER = 10
    PROGRESS_UPDATE_TIME = 10

    def __init__(self, export_path, proxies, update_all=False, countries=[]):
        Thread.__init__(self)
        
        self.exportPath = export_path
        self.proxies = proxies
        self.update_all = update_all
        self.countries = set([name.upper() for name in countries])
        
        self._url_base = 'http://www.ratebeer.com'
        self._url_country_brewers = 'http://www.ratebeer.com/breweries/'
        self._url_brewers = 'http://www.ratebeer.com/browsebrewers-A.htm'
        self._url_rigeons = 'http://www.ratebeer.com/places/browse/'
        
        self.imageExportPath = os.path.join(self.exportPath, 
            bytes([105, 109, 97, 103, 101, 115]).decode())
        
        self.countryBreweryPages = OrderedDict()
        self.beerPages = OrderedDict()
        self.beerPageNames = OrderedDict()
        self.beerData = OrderedDict()
        
        self.countryBreweryPath = os.path.join(self.exportPath, 'CountryBrewery.pac')
        self.beerPath = os.path.join(self.exportPath, 'Beers.pac')
        self.beerDataPath = os.path.join(self.exportPath, 'BeersData.pac')
        
        
        self.execTime = 0
    
    def runCountryBrewers(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        if os.path.exists(self.countryBreweryPath):
            with open(self.countryBreweryPath, ReadWriteFile.READ_BINARY) as fh:
                self.countryBreweryPages.update( pickle.load(fh) )
            print('Countries-Breweries:', sum(len(self.countryBreweryPages[c]) for c in self.countryBreweryPages))
            return
        if not self.update_all:
            return
        pages = OrderedDict()
        
        try:
            req = requests.get(self._url_country_brewers, proxies=self.proxies)
        except Exception as err:
            print('Error (BeerBrewers) request')
            print(' '*4, self._url_country_brewers.encode())
            print(' '*4, err)
        else:
            try:
                soup = BeautifulSoup(req.content, LXML)
            except Exception as err:
                print('Error (BeerBrewers) soup:', err)
            else:
                for a in soup.find_all(TAG_A, href=re.compile('/breweries/[\W\w\d]+/[\d]+/')):
                    url_ = self._url_base + a[ATTRIB_HREF]
                    name = unicode2ascii(a.text)
                    pages[url_] = name
                    
        print('Countries:', len(pages))
        progress = len(pages)
        pool = Pool(processes=self.THREAD_NUMBER)
        for step, country_url in enumerate(pages, 1):
            country_name = pages[country_url]
            print('run page', step,'-', progress,':', 
                  country_name, country_url.encode())
            pool.apply_async(collectCountryBrewers, 
                args = (self._url_base, 
                        country_url, country_name, self.proxies),
                callback = resultCountryBrewers
                )
            TASK_TOTAL += 1
        pool.close()
        
        print('Total tasks:', TASK_TOTAL)
        while ((TASK_TOTAL != TASK_FINISHED)):
            print( 'executed:', TASK_FINISHED, 
                   'from:', TASK_TOTAL, 
                   'progress:',  TASK_FINISHED / TASK_TOTAL)
            sleep(self.PROGRESS_UPDATE_TIME)
        pool.join()
        
        print('Countries-Breweries:', sum(len(self.countryBreweryPages[c]) for c in self.countryBreweryPages))
        with open(self.countryBreweryPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.countryBreweryPages, fh)
    
    def runBeers(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        self.beerPageNames.clear()
        
        if os.path.exists(self.beerPath):
            with open(self.beerPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerPages.update( pickle.load(fh) )
            for brewery_url, brewery_name in self.beerPages:
                self.beerPageNames[brewery_name] = self.beerPages[(brewery_url, brewery_name)]
            print('Beers:', sum(len(self.beerPages[v]) for v in self.beerPages))
            return
        if not self.update_all:
            return
        
        pool = Pool(processes=self.THREAD_NUMBER)
        for country_url, country_name in self.countryBreweryPages:
            if self.countries and country_name.upper() not in self.countries:
                continue
            for brewery_url in self.countryBreweryPages[(country_url, country_name)]:
                brewery_name,*_ = self.countryBreweryPages[(country_url, country_name)][brewery_url]
                pool.apply_async(collectBeers, 
                    args = (self._url_base, brewery_url, brewery_name, self.proxies),
                    callback = resultBeers)
                TASK_TOTAL += 1  
        pool.close()
        
        print('Total tasks:', TASK_TOTAL)
        
        while ((TASK_TOTAL != TASK_FINISHED)):
            print( 'executed:', TASK_FINISHED, 
                   'from:', TASK_TOTAL, 
                   'progress:',  TASK_FINISHED / TASK_TOTAL)
            sleep(self.PROGRESS_UPDATE_TIME)
        pool.join()
        
        for brewery_url, brewery_name in self.beerPages:
            self.beerPageNames[brewery_name] = self.beerPages[(brewery_url, brewery_name)]
        
        print('Beers:', sum(len(self.beerPages[v]) for v in self.beerPages))
        
        with open(self.beerPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.beerPages, fh)
    
    def runBeerPages(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        
        if (not self.update_all) and os.path.exists(self.beerDataPath):
            with open(self.beerDataPath, ReadWriteFile.READ_BINARY) as fh:
                self.beerData.update( pickle.load(fh) )
            print('Beer-data:', len(self.beerData))
            return
        if not self.update_all:
            return
        
        pool = Pool(processes=self.THREAD_NUMBER)
        for country_url, country_name in self.countryBreweryPages:
            if self.countries and country_name.upper() not in self.countries:
                continue
            print(country_name, '- Breweries:', 
                len(self.countryBreweryPages[(country_url, country_name)]),
                'beers:', 
                (sum(len(self.beerPageNames[self.countryBreweryPages[(country_url, country_name)][v][0]]) 
                if self.countryBreweryPages[(country_url, country_name)][v][0] in self.beerPageNames 
                else 0 for v in self.countryBreweryPages[(country_url, country_name)])))
            
            for brewery_url in self.countryBreweryPages[(country_url, country_name)]:
                r = self.countryBreweryPages[(country_url, country_name)][brewery_url]
                brewery_name = r[0]
                for beer_url in self.beerPageNames[brewery_name]:
                    r = self.beerPageNames[brewery_name][beer_url]
                    beer_name = r[0]
                    
                    pool.apply_async(collectBeerPages, 
                        args = (beer_url, beer_name, self.imageExportPath, self.proxies),
                        callback = resultBeerPages)
                    TASK_TOTAL += 1
                    #if TASK_TOTAL > 12:
                    #    break
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
        _tic_time = clock()
        self.execTime = 0
        
        self.countryBreweryPages.clear()
        self.beerPages.clear()
        self.beerPageNames.clear()
        self.beerData.clear()
        
        os.makedirs(self.exportPath, exist_ok=True)
        os.makedirs(self.imageExportPath, exist_ok=True)
        
        self.runCountryBrewers()
        self.runBeers()
        self.runBeerPages()
        
        self.execTime = clock() - _tic_time
    
    def beerRows(self, print_ = False):
        FIELDS = ['brewery', 'beer', 'ABV', 'Added', 
        'Score', 'Style', 'Reviews',
        ]
        
        STATS = [('RATINGS:', -1),
            ('MEAN:', '-1/-1'),
            ('WEIGHTED AVG:', -1),
            ('SEASONAL:', str()),
            ('EST. CALORIES:', -1),
            ('ABV:', '-1%'),
            ('IBU:', -1),
        ]
        DEL_OR_CHANGED_BEER_STR = 'Most likely there was a name change, merge or the beer was deleted'
        
        FIELDS.extend([n for n,_ in STATS])
        if print_:
            print(chr(9).join(map(str, FIELDS)))
        FIELDS.append('IMAGE')  
        ROWS = []
        iROWS = set()
        for b_url, b_name in self.beerPages:
            for beer_url in self.beerPages[(b_url, b_name)]:
                beer_info = self.beerPages[(b_url, b_name)][beer_url]
                
                beer_name, alco, add_date, *beer_info = beer_info
                alco = -1. if alco == '-' else str2val(alco)
                _, score, _, reviews, *_ = beer_info
                
                score = str2val(score) if score else -1.
                reviews = str2val(reviews) if reviews else -1.
                
                row = [b_name, beer_name, alco, add_date, score, str(), reviews]
                
                stats = OrderedDict(STATS)
                
                img_path = None
                if (beer_url, beer_name) in self.beerData:
                    values = self.beerData[(beer_url, beer_name)]
                    _,_,_,_,_img_path,desc,_,img_size,style = values
                    row[5] = style
                    if _img_path:
                        _img_path = os.path.basename(_img_path)
                        _img_path = os.path.join(self.imageExportPath, _img_path)
                        if os.path.exists(_img_path):
                            img_size = os.stat(_img_path).st_size
                            if img_size > 0:
                                img_path = _img_path
                    if desc:
                        if DEL_OR_CHANGED_BEER_STR in desc:
                            continue
                        names = list(stats.keys())
                        starts = [(desc.find(name) if name in desc else -1, name) for name in names]
                        starts.sort(key=itemgetter(0))
                        iLen = len(starts)
                        for i, (start, name) in enumerate(starts, 1):
                            if start == -1: continue
                            if i < iLen:
                                d = desc[start: starts[i][0]]
                            else:
                                d = desc[start:]
                            d = d[len(name):].strip()
                            if d == '-': continue
                            stats[name] = d
                row.extend(stats.values())
                
                if print_:
                    print(chr(9).join(map(str, row)))
                row.append(img_path)
                    
                id_ = hash(tuple(row))
                if id_ in iROWS:
                    continue
                iROWS.add(id_)
                ROWS.append(row)
        
        return FIELDS, ROWS
    
if __name__ == '__main__':
    
    proxy_info = {
    'user' : '*****',
    'pass' : '*****',
    'host' : "***.***.***.***",
    'port' : 0000
    }
    
    proxy = {"http" : "http://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info,
             "https" : "https://%(user)s:%(pass)s@%(host)s:%(port)d" % proxy_info}
    #proxy.clear()
    
    graber_ = RateBeerGrabber(os.path.join('..', '..', 'RateBeer'), proxy,
        update_all=True,
        countries=['Belgium']
        #countries=['Netherlands']
        #countries=['Moldova']
        #countries=['Romania']
        #countries=['Czech Republic']
    )
    
    graber_.start()
    graber_.join()
    
    fs, rs = graber_.beerRows()
    
    print(len(rs))
    #collectBeerPages(
    #    b'http://www.ratebeer.com/beer/prearis-grand-cru-2013-makers-mark-bourbon-ba/242115/',
    #    'Praris Grand Cru 2013 (Makers Mark Bourbon BA)',
    #    graber.imageExportPath,
    #    proxy)
    
    