from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from oscar.apps.shipping.methods import (
    Free, FixedPrice, Negotiable, LocalPickup, SelfDelivery, uspsShipping, First, ParcelSelect, UPSGround, 
    Priority, PrioritySmall, PriorityMedium, NoShippingRequired, OfferDiscount, QuerySeller)

from decimal import Decimal as D
from math import ceil

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

class ItemNotShippable(Exception):
    """ Easy to understand naming conventions work best! """
    pass


class Repository(object):
    """
    Repository class responsible for returning ShippingMethod
    objects for a given user, basket etc
    """
    methods = [QuerySeller(), LocalPickup(), SelfDelivery(), First(), ParcelSelect(), FixedPrice(), Priority(), UPSGround(), PrioritySmall(), PriorityMedium()]

    availableMethods = []

    easyPostServicesToIgnore = ("LibraryMail", "MediaMail", "CriticalMail")

    easyPostServicesSelectedBySeller = []


    services = []



    def getShippingInfo(self, basket, shippingAddress):
        import easypost
        easypost.api_key = settings.EASYPOST_KEY

        ## make a dictionary of up-to-date shipping info. This is saved to the basket in JSON format, and accessed in shipping/base.py 
        shipping_info = basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)
        else:
            shipDict = {}

        ## list of keywords corresponding to shipping services available
        serviceList = []

        ## zero out weight to start
        weight = 0.0

        ## check for self shipping of options
        selfShipCostTotal = -1

        ## whether the seller needs to be contacted for an estimate
        needNewEstimate = False

        ## in the case where estimate already exists
        if shipDict:
            if shipDict.get('customShipAmount') and shipDict.get('needNewEstimate') == False: ## and basket.status=="Frozen":
                ## customShipAmount should have the estimate already if this condition holds
                selfShipCostTotal = shipDict.get('customShipAmount')
                if selfShipCostTotal > 0.0:
                    for m in self.methods:
                        if m.code == 'fixed-price-shipping':
                            self.availableMethods.append(m)

                    shipDict['fixed-price-shipping'] = str(selfShipCostTotal)
                    basket.shipping_info = json.dumps(shipDict)
                    basket.save()
                    ## don't show calculated options
                    return serviceList


        local_delivery_cost = 0.0

        for line in basket.lines.all():

            p = line.product
            if not p.stockrecord.shipping_options:
                break
            soptsDict = json.loads(p.stockrecord.shipping_options)
            if soptsDict:

                if soptsDict.get('local_delivery_used') == True:


                    try:
                        boothOpts = json.loads(p.stockrecord.partner.shipping_options)
                        local_delivery_cost = boothOpts['local_delivery_cost']
                        local_delivery_radius = boothOpts['local_delivery_radius']

                        ## make sure within radius
                        dist = p.getDistanceToBuyer(shippingAddress)

                        print "delivery dist: " 
                        print dist

                        if dist and float(dist) < float(local_delivery_radius):

                            for m in self.methods:
                                if m.code == 'self-delivery':
                                    self.availableMethods.append(m)
                                    shipDict['self-delivery'] = local_delivery_cost

                                    basket.shipping_info = json.dumps(shipDict)
                                    ## freeze basket if need a shipping estimate
                                    #basket.freeze()
                                basket.save()
                    except:
                        print "Problem with self-delivery in repo.py"



        for line in basket.lines.all():

            p = line.product
            if not p.stockrecord.shipping_options:
                break
            soptsDict = json.loads(p.stockrecord.shipping_options)
            if soptsDict:
                if soptsDict.get('self_ship') == True:
                    try:
                        self_ship_cost = soptsDict['self_ship_cost']
                        if self_ship_cost != '' and self_ship_cost != None:
                            if selfShipCostTotal < 0:
                                selfShipCostTotal = 0.0
                            selfShipCostTotal = selfShipCostTotal + (float(self_ship_cost) * line.quantity)
                    except:
                        pass
                    ## if more than one item, need an estimate.
                    if line.quantity > 1: ## and soptsDict.get('newEstimateForMultipleItems'):
                        needNewEstimate = True
                    ## if more than one type of item, get an estimate
                    if len(basket.lines.all() ) > 1:
                        needNewEstimate = True


        ## if a new estimate is needed, this trumps everything else
        if needNewEstimate:
            for m in self.methods:
                if m.code == 'query-seller':
                    self.availableMethods.append(m)

            shipDict['needNewEstimate'] = True
            shipDict['customShipAmount'] = None
            shipDict['query-seller'] = None


            basket.shipping_info = json.dumps(shipDict)
            ## freeze basket if need a shipping estimate
            #basket.freeze()
            basket.save()
            ## don't show calculated options
            return serviceList

        if selfShipCostTotal >= 0.0:
            for m in self.methods:
                if m.code == 'fixed-price-shipping':
                    self.availableMethods.append(m)

            shipDict['fixed-price-shipping'] = str(selfShipCostTotal)
            basket.shipping_info = json.dumps(shipDict)
            basket.save()
            ## don't show calculated options
            return serviceList

        ## now deal with Priority Mail box filling. This doesn't need weight, or EasyPost.
        smallBoxes = 0
        mediumBoxes = 0
        largeBoxes = 0
        for line in basket.lines.all():

            p = line.product
            try:
                soptsDict = json.loads(p.stockrecord.shipping_options)
            except:
                break
            if soptsDict:

                if soptsDict.get("PMSmall_used") and soptsDict.get("PMSmall_num"):
                    PMSmall_num = soptsDict.get("PMSmall_num")
                    try:
                        if PMSmall_num > 0: 
                            smallBoxes = smallBoxes + ( float(line.quantity) / float(PMSmall_num) )
                    except:
                        pass
                if soptsDict.get("PMMedium_used") and soptsDict.get("PMMedium_num"):
                    PMMedium_num = soptsDict.get("PMMedium_num")
                    try:
                        if PMMedium_num > 0: 
                            mediumBoxes = mediumBoxes + ( float(line.quantity) / float(PMMedium_num) )
                    except:
                        pass
                if soptsDict.get("PMLarge_used") and soptsDict.get("PMLarge_num"):
                    PMLarge_num = soptsDict.get("PMLarge_num")
                    try:
                        if PMLarge_num > 0: 
                            largeBoxes = largeBoxes + ( float(line.quantity) / float(PMLarge_num) )
                    except:
                        pass

        smallBoxCost = 5.15
        mediumBoxCost = 11.30
        if smallBoxes > 0:

            smallBoxes = int(ceil(smallBoxes))
            print "Can ship in " + str(smallBoxes) + " small PM boxes."
            shipDict['PrioritySmall'] = smallBoxes * smallBoxCost
            basket.shipping_info = json.dumps(shipDict)
            basket.save()

            for m in self.methods:
                if m.code == 'PrioritySmall':
                    self.availableMethods.append(m)

        if mediumBoxes > 0:
            mediumBoxes = int(ceil(mediumBoxes))
            print "Can ship in " + str(mediumBoxes) + " medium PM boxes."
            shipDict['PriorityMedium'] = mediumBoxes * mediumBoxCost
            basket.shipping_info = json.dumps(shipDict)
            basket.save()
            for m in self.methods:
                if m.code == 'PriorityMedium':
                    self.availableMethods.append(m)

        if largeBoxes > 0:

            largeBoxes = int(ceil(largeBoxes))                                    

        #if mediumBoxes > 0 or largeBoxes > 0 or smallBoxes > 0:
        #    return serviceList            

        ##oscarToAddress = get_object_or_404(UserAddress, id=shippingAddress.id)

        ## if still here, then using the rate calculator. Need weights (and ideally box size) for this
        ## sum weights

        weightBasedShippingAllowed = True
        for line in basket.lines.all():

            p = line.product
            if not p.stockrecord.shipping_options:
                break
            soptsDict = json.loads(p.stockrecord.shipping_options)
            if soptsDict:
                if soptsDict.get("max_per_box"):
                    try:
                        if soptsDict.get('max_per_box') != '' and soptsDict.get('max_per_box') != None:
                            if line.quantity > int(soptsDict.get('max_per_box')):
                                ## too many items to predict for now, instead of UPS/USPS ask for quote
                                weightBasedShippingAllowed = False
                    except:
                        pass

        for line in basket.lines.all():
            p = line.product


            if not p.stockrecord.is_shippable:
                #raise ItemNotShippable
                weightBasedShippingAllowed = False

            try:
                weight = weight + p.stockrecord.weight * line.quantity
            except:
                #messages.error(request, "Some items in your basket do not have listed weights so the shipping estimate will be low.")
                print "Some items in your basket do not have listed weights so the shipping estimate will be low."
                    
                weight = None
                raise ItemHasNoWeight
                break
                pass


        if not weightBasedShippingAllowed:
            for m in self.methods:
                if m.code == 'query-seller':
                    self.availableMethods.append(m)

            shipDict['needNewEstimate'] = True
            shipDict['customShipAmount'] = None
            shipDict['query-seller'] = None


            basket.shipping_info = json.dumps(shipDict)
            ## freeze basket if need a shipping estimate
            #basket.freeze()
            basket.save()
            ## don't show calculated options
            return serviceList

        ## weight based shipping calculation
        ota = shippingAddress

        ofa = basket.seller.primary_address
        if not ofa:
            raise SellerCannotShip
            return None

        if True:
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
                length = 6.0, 
                width = 6.0,
                height = 8.0,
                weight = weight,
            )

            shi = easypost.Shipment.create(
                to_address = to_address,
                from_address = from_address,
                parcel = parcel,

            )

            # parcelHalf = easypost.Parcel.create(
            #     length = 16.0, 
            #     width = 16.0,
            #     height = 18.0,
            #     weight = weight/2.0,
            # )

            # shipment2 = easypost.Shipment.create(
            #     to_address = to_address,
            #     from_address = from_address,
            #     parcel = parcelHalf,

            # )



        #except:
        #    print "problem with easypost call"
        #    #messages.warning(request, _("Shipping information unavailable - please check your network connection"))
        #
        #    return None


        print shi
        # print shipment2
        shipDict['easypost_info'] = shi.to_dict()
        basket.shipping_info = json.dumps(shipDict)
        basket.save()

        self.easyPostServicesSelectedBySeller = self.getServicesForSeller(basket)

        for r in shi.rates:
            print r.service
            if r.service not in self.easyPostServicesToIgnore and r.service in self.easyPostServicesSelectedBySeller:
                   
                serviceList.append(r.service)

        return serviceList

    def setWhetherShippingPaidBySeller(self, basket):
        shippingPaidBySeller = None

        for line in basket.lines.all():
            p = line.product
            if not p.stockrecord.shipping_options:
                raise ImproperlyConfigured(
                _("shipping options not present."))

            soptsDict = json.loads(p.stockrecord.shipping_options)
            if soptsDict:

                if soptsDict.get('shipChoice') == "calculate_ship" and soptsDict.get('printLabel'):
                    shippingForThisItemPaidBySeller = False
                else:
                    shippingForThisItemPaidBySeller = True

                if shippingPaidBySeller == None:
                    shippingPaidBySeller = shippingForThisItemPaidBySeller
                else:
                    if shippingPaidBySeller != shippingForThisItemPaidBySeller:
                        raise ImproperlyConfigured(
                            _("Inconsistency in shipping payment, seller vs site"))

        ## save to basket
        shipping_info = basket.shipping_info
        if shipping_info:
            shipDict = json.loads(shipping_info)
        else:
            shipDict = {}
        shipDict['shippingPaidBySeller'] = shippingPaidBySeller
        basket.shipping_info = json.dumps(shipDict)
        basket.save()

        return shippingPaidBySeller

    def getServicesForSeller(self, basket):
        services = []

        try:
            p = basket.lines.all()[0].product
            soptsDict = json.loads(p.stockrecord.shipping_options)
        except:
            return []

        try:
            seller = basket.seller
            boothShipOptsDict = json.loads(basket.seller.shipping_options)
        except:
            return []

        if soptsDict:
            if soptsDict.get("UPS_used") and boothShipOptsDict.get("UPS_used"):
                services.append("Ground")
            if soptsDict.get("first_used") and boothShipOptsDict.get("first_used"):
                services.append("First")
            if soptsDict.get("parcel_select_used") and boothShipOptsDict.get("first_used"):
                services.append("ParcelSelect")
        return services

    def getServicesFromJSON(self, basket):
        shipping_info = basket.shipping_info
        if shipping_info:

            shipDict = json.loads(shipping_info)

            ## first look for methods that are not EasyPost
            shipMethods = ["local-pickup", "query-seller", "fixed-price-shipping", "self-delivery", "PriorityMedium", "PrioritySmall"]
            for code in shipMethods:
                if shipDict.get(code):
                    self.availableMethods.append(self.find_by_code(code)) 

            easypost.api_key = settings.EASYPOST_KEY

            ## if no EasyPost specific information, return null serviceList
            if not shipDict.has_key('easypost_info'): return []

            eo =  easypost.convert_to_easypost_object(shipDict['easypost_info'], easypost.api_key)

            serviceList = []
            for r in eo.rates:
                if r.service not in self.easyPostServicesToIgnore:
                    serviceList.append(r.service)

            return serviceList
        return None
    
    def localPickupEnabled(self, basket):
        '''
        Making the assumption that if one of the items is available for local pickup, then they all are.
        For now....

        '''
        for line in basket.lines.all():
            p = line.product

            if p.stockrecord.local_pickup_enabled:
                return True

        return False


    

    def get_shipping_methods(self, user, basket, shipping_addr=None, **kwargs):
        """
        Return a list of all applicable shipping method objects
        for a given basket.

        We default to returning the Method models that have been defined but
        this behaviour can easily be overridden by subclassing this class
        and overriding this method.
        """

        if not self.sellerAcceptsRemotePayments(basket):
            if self.localPickupEnabled(basket): 
                self.methods = (LocalPickup(),)
            else:
                self.methods = ()

        self.services = ()
        self.availableMethods = []

        self.setWhetherShippingPaidBySeller(basket)

        try:

            self.services = self.getShippingInfo(basket, shipping_addr)
            ## set whether shipping paid by seller

            print self.services
        except (SellerCannotShip, ItemHasNoWeight, ItemNotShippable) as e:
            ## only do local pickup
            if self.localPickupEnabled(basket): 
                self.availableMethods.append(LocalPickup())
            return self.prime_methods(basket, self.availableMethods)
        except (ImproperlyConfigured) as e:
            print e
            return self.prime_methods(basket, [])

        print self.services

        for m in self.methods:
            m.basket_total_shipping = None

        if self.localPickupEnabled(basket): 
            self.availableMethods.append(LocalPickup())

        if self.services:
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

        #if not self.sellerAcceptsRemotePayments(basket):
        #    self.methods = (LocalPickup(),)

        self.availableMethods = []
        self.services = self.getServicesFromJSON(basket)

        if not self.services:
            return self.get_shipping_methods(user, basket, shipping_addr)

        if self.localPickupEnabled(basket): 
            self.availableMethods.append(LocalPickup())

        for m in self.methods:
            if m.service in self.services:
                self.availableMethods.append(m)

        return self.prime_methods(basket, self.availableMethods)


    def sellerAcceptsRemotePayments(self, basket):

        #from apps.homemade.homeMade import getSellerFromOscarID

        try:
            #seller = getSellerFromOscarID(basket.seller.user.id)

        #if seller.stripeSellerToken and seller.stripeSellerPubKey:
            if basket.seller.stripeToken and basket.seller.stripePubKey:
                return True
            elif settings.TEST_LOCAL:
                return True
        except:
            
            pass
        
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

    def find_by_code(self, code, basket=None):
        """
        Return the appropriate Method object for the given code
        """
        for method in self.methods:
            if method.code == code:
                return method #self.prime_method(basket, method)

        # Check for NoShippingRequired as that is a special case
        if code == NoShippingRequired.code:
            return self.prime_method(basket, NoShippingRequired())
