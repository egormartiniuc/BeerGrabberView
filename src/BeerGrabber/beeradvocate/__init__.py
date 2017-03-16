
import re
import os
import pickle
import requests

from time import clock
from time import sleep
from threading import Thread
from bs4 import BeautifulSoup
from multiprocessing import Pool
from collections import OrderedDict

from BeerGrabber.utils import ReadWriteFile
from BeerGrabber.utils import str2val
from BeerGrabber.utils import unicode2ascii
from BeerGrabber.utils import name2folter
from BeerGrabber.utils import LXML
from BeerGrabber.utils import ATTRIB_HREF
from BeerGrabber.utils import ATTRIB_SRC
from BeerGrabber.utils import TAG_A
from BeerGrabber.utils import TAG_B
from BeerGrabber.utils import TAG_IMG

TASK_FINISHED = 0
TASK_TOTAL = 0

def collectCountryBrewers(url_base, countryurl, countryname, proxies):
    brewers = OrderedDict()
    prefixies = []
    
    try:
        req = requests.get(countryurl, proxies=proxies)
    except Exception as err:
        print('Error (CountryBrewers) request:')
        print(' '*4, countryurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (CountryBrewers) soup:')
            print(' '*4, countryurl.encode())
            print(' '*4, err)
        else:
            urls = []
            for a in soup.find_all(TAG_A, href=re.compile('/place/list/[\w\W\d]+brewery=Y')):
                urls.append(url_base + a[ATTRIB_HREF])
            
            for a in soup.find_all(TAG_A, href=re.compile('/place/list/\?city=[\w\W\d]+')):
                urls.append(url_base + a[ATTRIB_HREF])
            
            for pos, url in enumerate(urls, 1):
                print(pos)
                try:
                    req = requests.get(url, proxies=proxies)
                except Exception as err:
                    print('Error (CountryBrewers) request-1-{}:'.format(pos))
                    print(' '*4, url.encode())
                    print(' '*4, err)
                else:
                    try:
                        soup = BeautifulSoup(req.text, LXML)
                    except Exception as err:
                        print('Error (CountryBrewers) soup-1-{}:'.format(pos))
                        print(' '*4, url.encode())
                        print(' '*4, err)
                    else:
                        prefix_s = str()
                        prefix_e = str()
                        
                        indexes = []
                        for a in soup.find_all(TAG_A, href=re.compile('/place/list/\?start=[\d]+')):
                            ids = re.findall('[\d]+', a[ATTRIB_HREF])
                            if ids:
                                prefix_s, prefix_e = a[ATTRIB_HREF].split(chr(61), 1)
                                prefix_e = prefix_e.lstrip(ids[0])
                                indexes.append( int(ids[0]) )
                        if indexes:
                            minIndex = min(indexes)
                            maxIndex = max(indexes)
                            for a in soup.find_all(TAG_A, href=re.compile('/beer/profile')):
                                brewery_name = unicode2ascii(a.b.text) 
                                brewery_url = url_base + a[ATTRIB_HREF]
                                brewers[brewery_url] = brewery_name
                            prefixies.append((minIndex, maxIndex, prefix_s, prefix_e))
                        else:
                            for a in soup.find_all(TAG_A, href=re.compile('/beer/profile')):
                                brewery_name = unicode2ascii(a.b.text)
                                brewery_url = url_base + a[ATTRIB_HREF]
                                brewers[brewery_url] = brewery_name
    
    for minIndex, maxIndex, prefix_s, prefix_e in prefixies:
        for pos, index in enumerate(range(minIndex, maxIndex+20, 20)):
            url = url_base + prefix_s + '=' + str(index) + prefix_e
            try:
                req = requests.get(url, proxies=proxies)
            except Exception as err:
                print('Error (CountryBrewers) request-2-{}:'.format(pos))
                print(' '*4, url.encode())
                print(' '*4, err)
            else:
                try:
                    soup = BeautifulSoup(req.text, LXML)
                except Exception as err:
                    print('Error (CountryBrewers) soup-2-{}:'.format(pos))
                    print(' '*4, brewery_url.encode())
                    print(' '*4, err)
                else:
                    for a in soup.find_all(TAG_A, href=re.compile('/beer/profile')):
                        brewery_name = unicode2ascii(a.b.text) 
                        brewery_url = url_base + a[ATTRIB_HREF]
                        brewers[brewery_url] = brewery_name
    
    
    return countryurl, countryname, brewers

def resultCountryBrewers(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, brewers = args
    graber_.countryBreweryPages[(url, name)] = brewers

def collectBeers(url_base, breweryurl, breweryname, proxies):
    beerUrls = OrderedDict()
    brewerData = OrderedDict()
    url = breweryurl + '?view=beers&show=all'
    try:
        req = requests.get(url, proxies=proxies)
    except Exception as err:
        print('Error (Beers) request:')
        print(' '*4, breweryurl.encode())
        print(' '*4, err)
    else:
        try:
            soup = BeautifulSoup(req.content, LXML)
        except Exception as err:
            print('Error (Beers) soup:')
            print(' '*4, breweryurl.encode())
            print(' '*4, err)
        else:
            for a in soup.find_all(TAG_A, href=re.compile('/beer/profile/[\d]+/[\d]+')):
                try:
                    beer_url = url_base + a[ATTRIB_HREF]
                    row = [unicode2ascii(td.text) for td in a.parent.parent]
                    beer_name = row[0]
                except Exception as err:
                    print('Error (Beers) profile:')
                    print(' '*4, err)
                else:
                    beerUrls[(beer_url, beer_name)] = row
            
            for b in soup.find_all(TAG_B):
                text = unicode2ascii(b.text)
                if text == 'BEER AVG':
                    data = b.parent.text.lstrip(text).encode()
                    brewerData[text] = data
                elif text == 'PLACE INFO':
                    data = b.parent.text.lstrip(text).encode()
                    brewerData[text] = data
                elif text == 'BEER STATS':
                    data = b.parent.text.lstrip(text).encode()
                    brewerData[text] = data
    return (breweryurl, breweryname, beerUrls, brewerData)

def resultBeers(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, beer_dic, brewery_dic = args
    graber_.beerPages[(url, name)] = beer_dic
    graber_.breweryData[(url, name)] = brewery_dic
    
def collectBeerPages(beerurl, beername, image_basepath, proxies):
    beerData = OrderedDict()
    beerData[BeerAdvocateGrabber.STR_BEER_IMAGES] = []
    beerData[BeerAdvocateGrabber.STR_BA_SCORE] = bytes()
    beerData[BeerAdvocateGrabber.STR_THE_BROS] = bytes()
    beerData[BeerAdvocateGrabber.STR_BEER_STATS] = bytes()
    beerData[BeerAdvocateGrabber.STR_BEER_INFO] = bytes()
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
            for b in soup.find_all(TAG_B):
                text = unicode2ascii(b.text)
                if text == BeerAdvocateGrabber.STR_BA_SCORE:
                    beerData[text] = b.parent.text.lstrip(text).encode()
                elif text == BeerAdvocateGrabber.STR_THE_BROS:
                    beerData[text] = b.parent.text.lstrip(text).encode()
                elif text == BeerAdvocateGrabber.STR_BEER_STATS:
                    beerData[text] = b.parent.text.lstrip(text).encode()
                elif text == BeerAdvocateGrabber.STR_BEER_INFO:
                    beerData[text] = b.parent.text.lstrip(text).encode()
            
            for img in soup.find_all(TAG_IMG):
                if not '/beers/' in img[ATTRIB_SRC]:
                    continue
                basename = os.path.basename(img[ATTRIB_SRC])
                if basename == 'c_beer_image.gif':
                        continue
                elif basename == 'placeholder-beer.jpg':
                    continue
                image_path = os.path.join(image_basepath, basename)
                if os.path.exists(image_path):
                    beerData[BeerAdvocateGrabber.STR_BEER_IMAGES].append((img[ATTRIB_SRC], image_path))
                else:
                    try:
                        req = requests.get(img[ATTRIB_SRC], proxies=proxies)
                    except Exception as err:
                        print('Error (BeerPages) BeerImage request:')
                        print(' '*4, img[ATTRIB_SRC].encode())
                        print(' '*4, err)
                    else:
                        try:
                            open(image_path, ReadWriteFile.WRITE_BINARY_NEW).write(req.content)
                        except Exception as err:
                            print('Error (BeerPages) BeerImage save:')
                            print(' '*4, err)
                        else:
                            beerData[BeerAdvocateGrabber.STR_BEER_IMAGES].append((img[ATTRIB_SRC], image_path))
    return (beerurl, beername, beerData)

def resultBeerPages(args):
    global graber_
    global TASK_FINISHED
    TASK_FINISHED += 1
    url, name, dic = args
    graber_.beerData[(url, name)] = dic


class BeerAdvocateGrabber(Thread):
    
    THREAD_NUMBER = 10
    PROGRESS_UPDATE_TIME = 10
    
    STR_BA_SCORE = 'BA SCORE'
    STR_THE_BROS = 'THE BROS'
    STR_BEER_INFO = 'BEER INFO'
    STR_BEER_STATS = 'BEER STATS'
    STR_BEER_IMAGES = 'BEER IMAGES'
    
    def __init__(self, export_path, proxies, update_all=False, countries=[]):
        Thread.__init__(self)
        
        self.exportPath = export_path
        self.proxies = proxies
        self.update_all = update_all
        self.countries = set([name.upper() for name in countries])
        
        self._url_base = 'http://www.beeradvocate.com'
        self._url_search = 'http://www.beeradvocate.com/search/?q={name}&qt=beer'
        self._url_country = 'http://www.beeradvocate.com/place/directory/?show=all'
        self._url_beer = 'http://www.beeradvocate.com/beer/'
        
        self.imageExportPath = os.path.join(self.exportPath, 
            bytes([105, 109, 97, 103, 101, 115]).decode())
        
        self.execTime = 0
        
        self.countryPages = []
        self.countryBreweryPages = OrderedDict()
        self.breweryData = OrderedDict()
        self.beerPages = OrderedDict()
        self.beerData = OrderedDict()
        
        self.countryPath = os.path.join(self.exportPath, 'Countries.pac')
        self.countryBreweryPath = os.path.join(self.exportPath, 'CountryBrewery.pac')
        self.breweryDataPath = os.path.join(self.exportPath, 'BreweryData.pac')
        self.beerPath = os.path.join(self.exportPath, 'Beer.pac')
        self.beerDataPath = os.path.join(self.exportPath, 'BeerData.pac')
        
    def runCountries(self):
        
        if (not self.update_all) and os.path.exists(self.countryPath):
            with open(self.countryPath, ReadWriteFile.READ_BINARY) as fh:
                self.countryPages.extend( pickle.load(fh) )
            print('Countries:', len(self.countryPages))
            return
        if (not self.update_all):
            return
        try:
            req = requests.get(self._url_country, proxies=self.proxies)
        except Exception as err:
            print('Error (Countries) request')
            print(' '*4, self._url_country.encode())
            print(' '*4, err)
        else:
            try:
                soup = BeautifulSoup(req.content, LXML)
            except Exception as err:
                print('Error (Countries) soup:', err)
            else:
                for a in soup.find_all(TAG_A, href=re.compile('/place/directory/0/[\W\w\d]+/')):
                    name = unicode2ascii(a.text)
                    url = self._url_base + a[ATTRIB_HREF]
                    num, = re.findall('(\d+)', name)
                    name = name.replace('(%s)'%num, str())
                    name = name.strip()
                    self.countryPages.append((url, name, int(num))) 
        
        print('Countries:', len(self.countryPages))
        with open(self.countryPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.countryPages, fh)
    
    def runCountryBrewers(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        
        if (not self.update_all) and os.path.exists(self.countryBreweryPath):
            with open(self.countryBreweryPath, ReadWriteFile.READ_BINARY) as fh:
                self.countryBreweryPages.update( pickle.load(fh) )
            print('Countries-Breweries:', sum(len(self.countryBreweryPages[k]) for k in self.countryBreweryPages))
            return
        if (not self.update_all):
            return
        pool = Pool(processes=self.THREAD_NUMBER)
        for pos, (country_url, country_name, beer_number) in enumerate(self.countryPages, 1):
            if self.countries and country_name.upper() not in self.countries:
                continue
            print(pos, ')', country_name, '- Breweries:', beer_number)
            pool.apply_async(collectCountryBrewers, 
                             args = (self._url_base, country_url, country_name, self.proxies),
                             callback = resultCountryBrewers)
            TASK_TOTAL += 1
         
        pool.close()
        
        print('Total tasks:', TASK_TOTAL)
        while ((TASK_TOTAL != TASK_FINISHED)):
            print( 'executed:', TASK_FINISHED, 
                   'from:', TASK_TOTAL, 
                   'progress:',  TASK_FINISHED / TASK_TOTAL)
            sleep(self.PROGRESS_UPDATE_TIME)
        pool.join()
        
        print('Countries-Breweries:', sum(len(self.countryBreweryPages[k]) for k in self.countryBreweryPages))
        with open(self.countryBreweryPath, ReadWriteFile.WRITE_BINARY_NEW) as fh:
            pickle.dump(self.countryBreweryPages, fh)
    
    def runBeers(self):
        global TASK_FINISHED
        global TASK_TOTAL
        TASK_FINISHED = 0
        TASK_TOTAL = 0
        
        if (not self.update_all):
            if os.path.exists(self.beerPath):
                with open(self.beerPath, 'rb') as fh:
                    self.beerPages.update( pickle.load(fh) )
                print('Beers:', sum(len(self.beerPages[k]) for k in self.beerPages))
            if os.path.exists(self.breweryDataPath):
                with open(self.breweryDataPath, 'rb') as fh:
                    self.breweryData.update( pickle.load(fh) )
                print('Brewers-Data:', len(self.breweryData))
            return
        if (not self.update_all):
            return
        pool = Pool(processes=self.THREAD_NUMBER)
        for country_url, country_name in self.countryBreweryPages:
            if self.countries and country_name.upper() not in self.countries:
                continue
            print(country_name)
            for brewery_url in self.countryBreweryPages[(country_url, country_name)]:
                brewery_name = self.countryBreweryPages[(country_url, country_name)][brewery_url]
                print(' '*4, brewery_name)
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
        
        print('Beers:', sum(len(self.beerPages[k]) for k in self.beerPages))
        print('Brewers-Data:', len(self.breweryData))
        with open(self.beerPath, 'wb+') as fh:
            pickle.dump(self.beerPages, fh)
            
        with open(self.breweryDataPath, 'wb+') as fh:
            pickle.dump(self.breweryData, fh)
    
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
        if (not self.update_all):
            return
        pool = Pool(processes=self.THREAD_NUMBER)
        
        for c_url, c_name in self.countryBreweryPages:
            if self.countries and c_name.upper() not in self.countries:
                continue
            print(c_name)
            print(c_name, '- Breweries:', 
                len(self.countryBreweryPages[(c_url, c_name)]),
                'beers:', 
                (sum(len(self.beerPages[key]) if key in self.beerPages else 0 for key in self.countryBreweryPages[(c_url, c_name)].items())))
            for b_url, b_name in self.countryBreweryPages[(c_url, c_name)].items():
                if (b_url, b_name) in self.beerPages:
                    for beer_url, beer_name in self.beerPages[(b_url, b_name)]:
                        pool.apply_async(collectBeerPages, 
                            args = (beer_url, beer_name, self.imageExportPath, self.proxies),
                            callback = resultBeerPages)
                        TASK_TOTAL += 1
                        #break
                    #break
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
        
        self.countryPages.clear()
        self.countryBreweryPages.clear()
        self.breweryData.clear()
        self.beerPages.clear()
        self.beerData.clear()
        
        self.runCountries()
        self.runCountryBrewers()
        self.runBeers()
        self.runBeerPages()
        
        self.execTime = clock() - _tick_time 
    
    def beerRows(self, print_ = False):
        
        STATS = [('Reviews:', -1),
         ('Ratings:', -1),
         ('Avg:', -1),
         ('pDev:', '-1%'),
         ('Wants:', -1),
         ('Gots:', -1),
         ('For Trade:', -1),
        ]
        
        INFO = [('Brewed by:', str()),
                ('Style:', str()),
                ('Alcohol by volume (ABV):', str()),
                ('Availability:', str()),
                ('Notes / Commercial Description:', str()),
                ('Added by', str()),
        ]
        
        FIELDS = ['brewery', 'beer', 
            'ba-score', 'ba-desc', 'ba-reviews',
            'bros-score', 'bros-desc',
        ]
        
        FIELDS.extend([n for n, _ in STATS])
        FIELDS.extend([n for n, _ in INFO])
        if print_:
            print(chr(9).join(map(str, FIELDS)))
        FIELDS.append(self.STR_BEER_IMAGES)
        
        ROWS = []
        iROWS = set()
        beers = OrderedDict()
        beer_number = 0     
        for b_url, b_name in self.beerPages:
            beers[b_name] = OrderedDict()
            #print(b_name, b_url.encode())
            for beer_url, beer_name in self.beerPages[(b_url, b_name)]:
                if not beer_url.endswith(chr(47)): continue
                #print(' '*4, beer_name, beer_url.encode())
                beerData = self.beerData[(beer_url, beer_name)]
                
                ba_score = beerData[self.STR_BA_SCORE]
                ba_score = ba_score.decode().replace(chr(9), str()).split(chr(10))
                ba_score = ba_score[ba_score.index(self.STR_BA_SCORE)+2:]
                ba_score_index = -1
                if ba_score[0].isdigit():
                    ba_score_index = int(ba_score[0])
                elif ba_score[0] == '-':
                    ba_score_index = 0
                review, = re.findall('[\d,.]+', ba_score[-1])
                
                the_bros = beerData[self.STR_THE_BROS]
                the_bros = the_bros.decode().replace(chr(9), str()).split(chr(10))
                the_bros = the_bros[the_bros.index(self.STR_THE_BROS)+2:]
                the_bros_index = -1
                if the_bros[0].isdigit():
                    the_bros_index = int(the_bros[0])
                elif the_bros[0] == '-':
                    the_bros_index = 0
                
                beer_stats = beerData[self.STR_BEER_STATS]
                beer_stats = beer_stats.decode().replace(chr(9), str()).split(chr(10))
                beer_stats = beer_stats[beer_stats.index(self.STR_BEER_STATS)+3:]
                stats = OrderedDict(STATS)
                for name in stats:
                    if name in beer_stats:
                        value = beer_stats[beer_stats.index(name)+1]
                        if not value:
                            value = beer_stats[beer_stats.index(name)+2]
                        if value == 'NAN%':
                            continue
                        stats[name] = str2val(value)
                
                
                beer_info = beerData[self.STR_BEER_INFO]
                beer_info = beer_info.decode().replace(chr(9), str()).split(chr(10))
                beer_info = beer_info[beer_info.index(self.STR_BEER_INFO)+2:]
                
                info = OrderedDict(INFO)
                names = list(info.keys())
                
                #print(names)
                #print(beer_info)
                
                for f, n in zip(names, names[1:]+[None]):
                    s,e = -1,-1
                    for i, v in enumerate(beer_info):
                        if f in v:
                            s = i
                        if n and n in v:
                            e = i+1
                            break
                    if s > -1 and e > -1:
                        d = chr(32).join(beer_info[s: e]).strip()
                        d = d[d.find(f)+len(f): d.find(n)].strip()
                    elif s > -1 and e == -1:
                        d = chr(32).join(beer_info[s:]).strip()
                        d = d[d.find(f)+len(f):].strip()
                    else:
                        continue
                    if d in ('No notes at this time.', 'not listed'):
                        continue
                    info[f] = unicode2ascii(d)
                
                row = [b_name, beer_name, 
                    ba_score_index, str2val(ba_score[1]), str2val(review),
                    the_bros_index, the_bros[1],
                ]    
                row.extend(stats.values())
                row.extend(info.values())
                if print_:
                    print(chr(9).join(map(str, row)))
                id_ = hash(tuple(row))
                if id_ in iROWS:
                    continue
                iROWS.add(id_)
                row.append(beerData[self.STR_BEER_IMAGES])
                ROWS.append(row)
                beer_number += 1
        
        print('Beers:', beer_number)
        
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
    proxy.clear()
    
    graber_ = BeerAdvocateGrabber(os.path.join('..', '..', 'BeerAdvocate'), proxy,
        update_all=False, 
        #countries=['Belgium']
        countries=['Netherlands']
    )
    
    graber_.start()
    graber_.join()
    #sys.exit(0)
    graber_.beerRows()
    
    
            
            