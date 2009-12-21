from jflow.db.instdata.models import DataField, VendorId
from base import DataVendor, DateFromString
from ccy import ecbzipccy


class ecbwriter(object):
    
    def __init__(self, h, start, end):
        self.ecb      = h
        self.start    = start
        self.end      = end
        self.vendor   = self.ecb.dbobj()
        self.factory  = self.ecb.cache_factory()
        self.field    = DataField.objects.get(code = 'LAST_PRICE')
        self.vids     = {}
        
    def newccydata(self, cur, dte, value):
        if dte > self.end:
            return
        vid = self.vids.get(cur,None)
        if vid is None:
            try:
                vid = VendorId.objects.get(ticker = cur, vendor = self.vendor)
            except:
                vid = False
            self.vids[cur] = vid
        if vid:
            m = self.factory.get_or_create(vendor_id = vid, field = self.field, dt = dte)[0]
            m.mkt_value = value
            m.save()
    


class ecb(DataVendor):
    '''
    European Central Bank market rates.
    The European central bank provides, free of charges, 
    market data and European area economic statistics. 
    '''
    
    def _history(self, ticker, startdate, enddate, field = None):
        w = ecbwriter(self, startdate, enddate)
        ecbzipccy(start = startdate, end = enddate, handler = w.newccydata)
    
    def historyarrived(self,res):
        pass
    
    def newccydata(self, cur, dte, value):
        pass
    
    
    
    
    
    
ecb()