from decimal import Decimal as D

from django.conf import settings
from django.contrib import messages

import easypost
import json



class ShippingMethod(object):
    """
    Superclass for all shipping method objects.

    It is an actual superclass to the classes in methods.py, and a de-facto
    superclass to the classes in models.py. This allows using all
    shipping methods interchangeably (aka polymorphism).
    """

    # This is the interface that all shipping methods must implement

    #: Used to store this method in the session.  Each shipping method should
    #  have a unique code.
    code = '__default__'

    #: The name of the shipping method, shown to the customer during checkout
    name = 'Default shipping'

    #: A more detailed description of the shipping method shown to the customer
    # during checkout
    description = ''

    # These are not intended to be overridden
    is_discounted = False
    discount = D('0.00')
    is_primed = False
    basket_total_shipping = None

    carrier = None
    service = None



    def getShippingRate(self):

        shipping_info = self.basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)

            ## first look for methods that are not EasyPost
            shipMethods = ["local-pickup", "fixed-price-shipping", "PriorityMedium", "PrioritySmall"]
            if self.code in shipMethods:
                rateStr = shipDict[self.code]
                return D(rateStr)                

            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict['easypost_info'], easypost.api_key)

            rate = None
            for r in eo.rates:
                if r.carrier == self.carrier and r.service == self.service:
                    rate = D(r.rate)

            return rate

    def get_shipping_rate_id(self):

        try:        
            shipping_info = self.basket.shipping_info
        except:
            return None
        if not shipping_info:
            return None
        else:
            shipDict = json.loads(shipping_info)
            easypost.api_key = settings.EASYPOST_KEY
            if shipDict.get('easypost_info'):
                eo =  easypost.convert_to_easypost_object(shipDict.get('easypost_info'), easypost.api_key)


                for r in eo.rates:
                    if r.carrier == self.carrier and r.service == self.service:
                        return r.id
            ## none found
            return None

    def __init__(self, *args, **kwargs):
        self.exempt_from_tax = False
        super(ShippingMethod, self).__init__(*args, **kwargs)

    def set_basket(self, basket):
        self.basket = basket

    def shippingPaidBySeller(self):

        try:        
            shipping_info = self.basket.shipping_info
        except:
            return True
        if not shipping_info:
            return True
        else:
            shipDict = json.loads(shipping_info)
            if shipDict.has_key('shippingPaidBySeller'):
                if shipDict.get('shippingPaidBySeller') == False:
                    return False

        ## by default, shipping costs go to seller
        return True


    def basket_charge_incl_tax(self):
        """
        Return the shipping charge including any taxes
        """
        return self.getShippingRate()

        ##raise NotImplemented()

    def basket_charge_excl_tax(self):
        """
        Return the shipping charge excluding taxes
        """
        return self.basket_charge_incl_tax()
        #raise NotImplemented()
