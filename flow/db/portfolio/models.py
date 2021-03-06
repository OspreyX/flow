from datetime import date, datetime

import ccy

from stdnet import orm
from stdnet.contrib.timeserie.models import TimeSeries

__all__ = ['VendorTicker',
           'MktData',
           'FinIns',
           'PortfolioHolder',
           'Portfolio',
           'Position',
           'PortfolioView',
           'PortfolioViewFolder',
           'UserViewDefault']



class VendorTicker(TimeSeries):
    code = orm.SymbolField(index = False)
    
    def __str__(self):
        return self.code


class MktData(orm.StdModel):
    code    = orm.SymbolField(unique = True)
    vendors = orm.HashField(VendorTicker)
    
    def get_ticker_and_provider(self, field, provider, providers):
        '''Given a field a provider and a dictionary of available providers, return the best possible
match as 3 elements tuple (provider ticker, provider field, provider object)'''
        pass
    
    def __str__(self):
        return self.code
    

class FinIns(orm.StdModel):
    '''Financial instrument base class. Contains a time-serie field.                
    '''
    code      = orm.SymbolField(unique = True)
    firm_code = orm.SymbolField()
    curncy    = orm.SymbolField()
    country   = orm.SymbolField()
    type      = orm.SymbolField(required = False)
    data      = orm.ForeignKey(MktData)
        
    def __str__(self):
        return self.code
        
    def pv01(self):
        '''Present value of a basis point. This is a Fixed Income notation which we try to extrapolate to
        all financial instruments'''
        return 0
    
    def price_to_value(self, price, size, dt):
        raise NotImplementedError("Cannot convert price and size to value")
    
    
class PortfolioHolder(orm.StdModel):
    name       = orm.SymbolField(unique = True)
    group      = orm.SymbolField()
    ccy        = orm.SymbolField()
    parent     = orm.ForeignKey('self',
                                required = False,
                                related_name = 'children')
    
    def __init__(self, description = '', **kwargs):
        super(PortfolioHolder,self).__init__(**kwargs)
        self.description = description
        
    def __str__(self):
        return self.name
    
    def root(self):
        '''Return Root Portfolio'''
        if self.parent:
            return self.parent.root()
        else:
            return self
    

class FinPositionBase(orm.StdModel):
    editable = False
    canaddto = False
    movable  = False
    folder   = True
    
    class Meta:
        abstract = True
    
    def get_tree(self):
        return None
    
    def alldata(self):
        d = self.todict()
        d['tree'] = self.get_tree()
        return d
    
    
class Portfolio(FinPositionBase):
    '''A portfolio containing positions and portfolios'''
    holder     = orm.ForeignKey(PortfolioHolder, related_name = 'dates')
    dt         = orm.DateField()
    
    def __str__(self):
        return '%s: %s' % (self.holder,self.dt)
    
    def root(self):
        '''Return Root Portfolio'''
        root = self.holder.root()
        if root == self.holder:
            return self
        else:
            raise NotImplementedError
        
    def children(self):
        children = self.holder.children.all()
        if children:
            for child in children:
                raise NotImplementedError
        else:
            return None
        
    def customAttribute(self, name):
        return getattr(self.holder,name)
        
    def addnewposition(self, inst, size, value):
        '''Add new position to portfolio:
 * *inst* FinIns instance
 * *size* position size
 * *value* position value

*inst* must not be in portfolio already, otherwise a ValueError will raise.
 '''
        pos = self.positions.filter(instrument = inst)
        if pos.count():
            raise ValueError('Cannot add position %s to portfolio. It is already available.' % inst)
        p = Position(portfolio = self,
                     size = size,
                     value = value,
                     dt = self.dt,
                     instrument = inst)
        return p.save()
    
    def add(self, item):
        item.parent = self
        item.save()
    
    def _todict(self):
        d = super(Portfolio,self).todict()
        if self.instrument:
            d['description'] = self.instrument.description
        else:
            ps = []
            d['positions'] = ps
            for position in self.positions():
                ps.append(position.todict())
        return d
    
    def create_view(self, name, user = None):
        root = self.root()
        p = PortfolioView(name = name,
                          user = user,
                          portfolio = root)
        return p.save()
        
    def get_tree(self):
        return [p.alldata() for p in self.positions.all()]
    

class Position(FinPositionBase):
    '''Financial position::
    
        * *sid* security id or None. For securities this is the underlying financial instrument id.
        * *size* size of position
        * *value* initial value of position
        * *dt* position date
    '''
    instrument = orm.ForeignKey(FinIns)
    portfolio  = orm.ForeignKey(Portfolio, related_name = 'positions')
    
    def __init__(self, size = 1, value = 0, **kwargs):
        self.size   = size
        self.value  = value
        super(Position,self).__init__(**kwargs)
    
    def customAttribute(self, name):
        return getattr(self.instrument,name)
    
    @property
    def dt(self):
        return self.portfolio.dt
        
    
class PortfolioView(FinPositionBase):
    name = orm.SymbolField()
    user = orm.SymbolField(required = False)
    portfolio = orm.ForeignKey(Portfolio, related_name = 'views')
    
    def __str__(self):
        return '%s: %s' % (self.portfolio,self.name)
    
    def customAttribute(self, name):
        return getattr(self.portfolio,name)
    
    def addfolder(self, name):
        '''Add folder for portfolio view. Self must have holder attribute available.'''
        return PortfolioViewFolder(name = name, view = self).save()
    
    def get_tree(self):
        return [p.alldata() for p in self.folders.all()]
    
    def isdefault(self, user):
        defaults = UserViewDefault.objects.filter(user = str(user), portfolio = self.portfolio)
        if defaults:
            return defaults[0].view == self
        else:
            return False
        
    @property
    def dt(self):
        return self.portfolio.dt
    
    
class PortfolioViewFolder(FinPositionBase):
    '''A Folder within a portfolio view'''
    name   = orm.SymbolField()
    parent = orm.ForeignKey('self',
                            required = False,
                            related_name = 'children')
    view   = orm.ForeignKey(PortfolioView,
                            required = False,
                            related_name = 'folders')
    positions = orm.SetField(Position)
    
    def get_tree(self):
        tree = [p.alldata() for p in self.children.all()]
        [tree.append(p.alldata()) for p in self.positions.all()]
        return tree
    
    @property
    def reference(self):
        if self.view:
            return self.view
        else:
            return self.parent
        
    @property
    def user(self):
        return self.reference.user
    
    @property
    def dt(self):
        return self.reference.dt
    
    
    
class UserViewDefault(orm.StdModel):
    user = orm.SymbolField()
    portfolio = orm.ForeignKey(Portfolio, related_name = 'user_defaults')
    view = orm.ForeignKey(PortfolioView, related_name = 'user_defaults')

    
