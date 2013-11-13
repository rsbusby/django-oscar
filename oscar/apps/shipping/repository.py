from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from oscar.apps.shipping.methods import (
    Free, LocalPickup, uspsShipping, First, UPSGround, Priority, NoShippingRequired, OfferDiscount)

from decimal import Decimal as D

from oscar.apps.address.models import UserAddress



from django.conf import settings
from django.contrib import messages
import json
import easypost


class SellerCannotShip(Exception):
    """ Easy to understand naming conventions work best! """
    pass

class ItemHasNoWeight(Exception):
    """ Easy to understand naming conventions work best! """
    pass


class Repository(object):
    """
    Repository class responsible for returning ShippingMethod
    objects for a given user, basket etc
    """
    methods = (LocalPickup(), First(), Priority(), UPSGround())

    availableMethods = []

    easyPostServicesToIgnore = ("LibraryMail", "MediaMail", "CriticalMail")

    services = []



    def getShippingInfo(self, basket, shippingAddress):
        import easypost
        easypost.api_key = settings.EASYPOST_KEY

        weight = 0.0

        for line in basket.lines.all():
            p = line.product
            try:
                weight = weight + p.attr.weight
            except:
                #messages.error(request, "Some items in your basket do not have listed weights so the shipping estimate will be low.")
                print "Some items in your basket do not have listed weights so the shipping estimate will be low."
                    
                weight = None
                raise ItemHasNoWeight
                break
                pass

        ##oscarToAddress = get_object_or_404(UserAddress, id=shippingAddress.id)
        #import ipdb;ipdb.set_trace()
        ota = shippingAddress

        ofa = basket.seller.primary_address
        if not ofa:
            raise SellerCannotShip
            return None

        try:
            to_address = easypost.Address.create(
              name = ota.name,
              street1 = ota.line1,
              city = ota.city,
              state = ota.state,
              zip = ota.postcode,
              country = ota.country.iso_3166_1_a2,
            #email = 'dr_steve_brule@gmail.com'
            )

            from_address = easypost.Address.create(
              name = ofa.name,
              street1 = ofa.line1,
              city = ofa.city,
              state = ofa.state,
              zip = ofa.postcode,
              country = ofa.country.iso_3166_1_a2,
                )
            import random

            # if weight == 0.0:
            #     print "setting weight randomly"
            #     w = random.randrange(4,7)
            # else:
            #     w = weight
            # print w

            if not weight:
                raise ItemHasNoWeight

            parcel = easypost.Parcel.create(
                length = 20.2, 
                width = 10.9,
                height = 5,
                weight = w,
            )

            shi = easypost.Shipment.create(
                to_address = to_address,
                from_address = from_address,
                parcel = parcel,

            )
        except:
            print "problem with easypost call"
            #messages.warning(request, _("Shipping information unavailable - please check your network connection"))

            return None

        basket.shipping_info = json.dumps(shi.to_dict())
        basket.save()

        serviceList = []
        for r in shi.rates:
            if r.service not in self.easyPostServicesToIgnore:
                serviceList.append(r.service)

        return serviceList


    def getServicesFromJSON(self, basket):
        shipping_info = basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)
            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict, easypost.api_key)

            serviceList = []
            for r in eo.rates:
                if r.service not in self.easyPostServicesToIgnore:
                    serviceList.append(r.service)

            return serviceList
        return None
     

    def get_shipping_methods(self, user, basket, shipping_addr=None, **kwargs):
        """
        Return a list of all applicable shipping method objects
        for a given basket.

        We default to returning the Method models that have been defined but
        this behaviour can easily be overridden by subclassing this class
        and overriding this method.
        """

        if not self.userAcceptsRemotePayments(basket):
            self.methods = (LocalPickup(),)

        self.services = ()
        try:
            self.services = self.getShippingInfo(basket, shipping_addr)
        except (SellerCannotShip, ItemHasNoWeight) as e:
            ## only do local pickup
            self.availableMethods = []
            self.availableMethods.append(LocalPickup())
            return self.prime_methods(basket, self.availableMethods)

        print self.services

        for m in self.methods:
            m.basket_total_shipping = None

        self.availableMethods = []
        
        self.availableMethods.append(LocalPickup())
        for m in self.methods:
            if m.service in self.services:
                self.availableMethods.append(m)



        #return self.availableMethods

        return self.prime_methods(basket, self.availableMethods)


    def get_shipping_methods_no_reset(self, user, basket, shipping_addr=None, **kwargs):
        """
        Return a list of all applicable shipping method objects
        for a given basket.

        We default to returning the Method models that have been defined but
        this behaviour can easily be overridden by subclassing this class
        and overriding this method.
        """

        #if not self.userAcceptsRemotePayments(basket):
        #    self.methods = (LocalPickup(),)
        #import ipdb;ipdb.set_trace()

        self.services = self.getServicesFromJSON(basket)
        if not self.services:
            return self.get_shipping_methods(user, basket, shipping_addr)

        self.availableMethods = []
        
        self.availableMethods.append(LocalPickup())
        for m in self.methods:
            if m.service in self.services:
                self.availableMethods.append(m)

        return self.prime_methods(basket, self.availableMethods)


    def userAcceptsRemotePayments(self, basket):

        from apps.homemade.homeMade import getSellerFromOscarID

        seller = getSellerFromOscarID(basket.seller.user.id)

        if seller.stripeSellerToken and seller.stripeSellerPubKey:
            return True

        return False

    def get_default_shipping_method(self, user, basket, shipping_addr=None,
                                    **kwargs):
        """
        Return a 'default' shipping method to show on the basket page to give
        the customer an indication of what their order will cost.
        """
        methods = self.get_shipping_methods(
            user, basket, shipping_addr, **kwargs)
        if len(methods) == 0:
            raise ImproperlyConfigured(
                _("You need to define some shipping methods"))

        # Choose the cheapest method by default
        return min(methods, key=lambda method: method.basket_charge_incl_tax())

    def prime_methods(self, basket, methods):
        """
        Prime a list of shipping method instances

        This involves injecting the basket instance into each and adding any
        discount wrappers.
        """
        return [self.prime_method(basket, method) for
                method in methods]

    def prime_method(self, basket, method):
        """
        Prime an individual method instance
        """

        if method.is_primed:
            return method

        method.basket_total_shipping = None
        method.set_basket(basket)
        # If the basket has a shipping offer, wrap the shipping method with a
        # decorating class that applies the offer discount to the shipping
        # charge.
        if basket.offer_applications.shipping_discounts:
            # We assume there is only one shipping discount available
            discount = basket.offer_applications.shipping_discounts[0]
            if method.basket_charge_incl_tax > D('0.00'):
                return OfferDiscount(method, discount['offer'])
        return method

    def find_by_code(self, code, basket):
        """
        Return the appropriate Method object for the given code
        """
        for method in self.methods:
            if method.code == code:
                return method #self.prime_method(basket, method)

        # Check for NoShippingRequired as that is a special case
        if code == NoShippingRequired.code:
            return self.prime_method(basket, NoShippingRequired())
