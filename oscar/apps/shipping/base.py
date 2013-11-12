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

    def getEasyPostRate(self):

        shipping_info = self.basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)
            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict, easypost.api_key)

            rate = None
            for r in eo.rates:
                if r.carrier == self.carrier and r.service == self.service:
                    rate = D(r.rate)

            return rate

    def get_shipping_rate_id(self):
        shipping_info = self.basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)
            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict, easypost.api_key)


            for r in eo.rates:
                if r.carrier == self.carrier and r.service == self.service:
                    return r.id
            return None


    def __init__(self, *args, **kwargs):
        self.exempt_from_tax = False
        super(ShippingMethod, self).__init__(*args, **kwargs)

    def set_basket(self, basket):
        self.basket = basket

    def basket_charge_incl_tax(self):
        """
        Return the shipping charge including any taxes
        """
        return self.getEasyPostRate()

        ##raise NotImplemented()

    def basket_charge_excl_tax(self):
        """
        Return the shipping charge excluding taxes
        """
        return self.basket_charge_incl_tax()
        #raise NotImplemented()
