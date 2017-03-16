'''
Created on Sep 9, 2016

@author: emartini
'''

ISO_8859_1 = bytes([73, 83, 79, 32, 56, 56, 53, 57, 45, 49]).decode()

SIGNS = [chr(v) for v in 
    [9, 10, 13, 32, 33, 34, 35, 37, 38, 40, 41, 42, 43, 45, 46, 47, 58, 63, 123, 125]]

VK_PREF = chr(95)

ATTRIB_HREF = bytes([104, 114, 101, 102]).decode()
ATTRIB_SRC = bytes([115, 114, 99]).decode()
LXML = bytes([108, 120, 109, 108]).decode()
TAG_A = chr(97)
TAG_B = chr(98)
TAG_P = chr(112)
TAG_TR = bytes([116, 114]).decode()
TAG_TD = bytes([116, 100]).decode()
TAG_SMALL = bytes([115, 109, 97, 108, 108]).decode()
TAG_IMG = bytes([105, 109, 103]).decode()
TAG_SPAN = bytes([115, 112, 97, 110]).decode()
TAG_DIV = bytes([100, 105, 118]).decode()
TAG_TABLE = bytes([116, 97, 98, 108, 101]).decode()

def str2val(val):
    if val.isdigit():
        return int(val)
    elif val.count(',') == 1 and val.replace(',', '').isdigit():
        return float(val.replace(',', '.'))
    elif val.count('.') == 1 and val.replace('.', '').isdigit():
        return float(val)
    return val

def unicode2ascii(value):
    return str().join(map(chr, [i for i in value.encode() if i >=32 and i<=127])).strip()

def name2folter(value):
    for sign in SIGNS:
        value = value.replace(sign, VK_PREF)
    value = value.strip(VK_PREF)
    s = str()
    sLen = len(value)
    for i, c in enumerate(value, 1):
        if i < sLen and c == VK_PREF and value[i] == VK_PREF:
            pass
        else:
            s += c
    return s.strip(VK_PREF)

class ReadWriteFile(object):
    READ = bytes([114]).decode()
    READ_BINARY = bytes([114, 98]).decode()
    WRITE = bytes([119]).decode()
    WRITE_BINARY = bytes([119, 98]).decode()
    WRITE_BINARY_NEW = bytes([119, 98, 43]).decode()

POLY64REVh = 0xd8000000
CRCTableh = [0] * 256
CRCTablel = [0] * 256

for i in range(256): 
    partl = i
    parth = 0
    for j in range(8):
        rflag = partl & 1                
        partl >>= 1      
        if (parth & 1):
            partl |= (1 << 31)
        parth >>= 1
        if rflag:
            parth ^= POLY64REVh
    CRCTableh[i] = parth
    CRCTablel[i] = partl

def _CRC64(aString):
    crcl = 0
    crch = 0
    for item in aString:
        shr = 0
        shr = (crch & 0xFF) << 24
        temp1h = crch >> 8
        temp1l = (crcl >> 8) | shr                        
        tableindex = (crcl ^ ord(item)) & 0xFF
        crch = temp1h ^ CRCTableh[tableindex]
        crcl = temp1l ^ CRCTablel[tableindex]
    return (crch, crcl)

def CRC64(aString):
    return int("%d%d" % (_CRC64(aString)))

if __name__ == '__main__':
    print(CRC64("IHATEMATH"))