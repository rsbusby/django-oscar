from decimal import Decimal as D

from django.utils.translation import ugettext_lazy as _

from oscar.apps.shipping.base import ShippingMethod
from django.conf import settings
from django.contrib import messages


import easypost
import json



class Free(ShippingMethod):
    """
    Simple method for free shipping
    """
    code = 'free-shipping'
    name = _('Free shipping')

    def basket_charge_incl_tax(self):
        return D('0.00')

    def basket_charge_excl_tax(self):
        return D('0.00')


class LocalPickup(ShippingMethod):
    """
    Simple method for local pickup
    """
    code = 'local-pickup'
    name = _('Local pickup')

    def __init__(self, charge_incl_tax = 0.0, charge_excl_tax=None):

        self.charge_incl_tax = charge_incl_tax
        if not charge_excl_tax:
            charge_excl_tax = charge_incl_tax
        self.charge_excl_tax = charge_excl_tax

    def basket_charge_incl_tax(self):
        return D(self.charge_incl_tax)

    def basket_charge_excl_tax(self):
        return D(self.charge_excl_tax)

class Negotiable(ShippingMethod):
    """
    Placeholder method for negotiable rates, for delivery or shipping.
    """
    code = 'negotiable'
    name = _('Negotiable')

    def basket_charge_incl_tax(self):
        return D('0.00')

    def basket_charge_excl_tax(self):
        return D('0.00')


class NoShippingRequired(Free):
    """
    This is a special shipping method that indicates that no shipping is
    actually required (eg for digital goods).
    """
    code = 'no-shipping-required'
    name = _('No shipping required')




class FixedPrice(ShippingMethod):
    code = 'fixed-price-shipping'
    name = _('Fixed price shipping')
    basket_total_shipping = None

    def __init__(self, charge_incl_tax=0.0, charge_excl_tax=None):
        self.charge_incl_tax = charge_incl_tax
        if not charge_excl_tax:
            charge_excl_tax = charge_incl_tax
        self.charge_excl_tax = charge_excl_tax

    #def basket_charge_incl_tax(self):
    #    return self.charge_incl_tax

    #def basket_charge_excl_tax(self):
    #    return self.charge_excl_tax

class QuerySeller(FixedPrice):
    code = 'query-seller'
    name = _('Shipping estimate unavailable')
    basket_total_shipping = None



class dotdict(dict):
    def __getattr__(self, attr):
        return self.get(attr, None)
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__


# def getEasyPostRate(basket, service):
#     shipping_info = basket.shipping_info
#     if shipping_info:
#         shipDict = json.loads(shipping_info)
#         easypost.api_key = settings.EASYPOST_KEY
#         eo =  easypost.convert_to_easypost_object(shipDict, easypost.api_key)

#         rate = None
#         for r in eo.rates:
#             if r.carrier == "USPS" and r.service = service:
#                 rate = D(r.rate)

#         return rate

class First(ShippingMethod):

    code = 'First'
    service = 'First'
    carrier = "USPS"
    name = _('First Class USPS Mail')
    basket_total_shipping = None


class Priority(ShippingMethod):

    code = 'Priority'
    service = 'Priority'
    carrier = "USPS"
    name = _('USPS Priority Mail')
    basket_total_shipping = None

class PrioritySmall(ShippingMethod):

    code = 'PrioritySmall'
    service = 'PrioritySmall'
    carrier = "USPS"
    name = _('USPS Priority Mail')
    basket_total_shipping = None

class PriorityMedium(ShippingMethod):

    code = 'PriorityMedium'
    service = 'PriorityMedium'
    carrier = "USPS"
    name = _('USPS Priority Mail')
    basket_total_shipping = None



class UPSGround(ShippingMethod):

    code = 'ups-ground'
    service = "Ground"
    carrier = "UPS"
    name = _('UPS Ground')
    basket_total_shipping = None


class uspsShipping(ShippingMethod):
    code = 'usps-shipping'
    name = _('U.S. Postal Service')
    basket_total_shipping = None
    is_primed = False

    def __init__(self):
        self.has_rate = False

    # def __init__(self, charge_incl_tax, charge_excl_tax=None):
    #     self.charge_incl_tax = charge_incl_tax
    #     if not charge_excl_tax:
    #         charge_excl_tax = charge_incl_tax
    #     self.charge_excl_tax = charge_excl_tax

    #def set_basket(self, basket):
    #    self.basket = basket

    def basket_charge_incl_tax(self):

        shipping_info = self.basket.shipping_info

        servicesToIgnore = ("LibraryMail", "MediaMail")

        if shipping_info:
            shipDict = json.loads(shipping_info)
            import easypost
            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict, easypost.api_key)

            lowRateService = None
            lowRate = None
            for r in eo.rates:
                if r.carrier == "USPS":
                    if r.service not in servicesToIgnore:
                        if not lowRate or float(r.rate) < lowRate:
                            lowRate = float(r.rate)
                            lowRateService = r.service

            return D(lowRate)




        elif self.basket_total_shipping:
            return self.basket_total_shipping
        else:
            return self.calc_basket_charge_incl_tax()


    def calc_basket_charge_incl_tax(self):

        # import postmaster

        # postmaster.config.api_key = settings.POSTMASTER_IO_KEY
 
        # rates = postmaster.get_rate(
        #     from_zip='28771',
        #     to_zip='90291',
        #     weight='1.0',
        # ##carrier='ups',
        # )

        # print rates



        # time_ups = postmaster.get_transit_time(
        #     from_zip='28771',
        #     to_zip='78704',
        #     weight='1.0',
        #  carrier='ups'  
        # )

        # try:
        #     time_usps = postmaster.get_transit_time(
        #         from_zip='28771',
        #         to_zip='78704',
        #         weight='1.0',
        #      carrier='usps'  
        #     )
        # except:
        #     time_usps = None
        # print time_ups
        # print time_usps


        import easypost
        easypost.api_key = settings.EASYPOST_KEY

        ## calculate total weight of basket.

        weight = 0.0

        for line in self.basket.lines.all():
            p = line.product
            try:
                weight = weight + p.attr.weight
            except:
                #messages.error(request, "Some items in your basket do not have listed weights so the shipping estimate will be low.")
                print "Some items in your basket do not have listed weights so the shipping estimate will be low."
                pass

        try:
            to_address = easypost.Address.create(
              #name = 'Dr. Steve Brule',
              #street1 = '179 N Harbor Dr',
              #city = 'Redondo Beach',
              #state = 'CA',
              zip = '90277',
              country = 'US',
            #email = 'dr_steve_brule@gmail.com'
            )

            from_address = easypost.Address.create(
                zip = '90291',
                )
            import random

            if weight == 0.0:
                print "setting weight randomly"
                w = random.randrange(4,7)
            else:
                w = weight
            print w
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
            messages.warning(request, _("Shipping information unavailable - please check your network connection"))

            return None

        print shi.lowest_rate()

        self.basket.shipping_info = json.dumps(shi.to_dict())
        self.basket.save()

        usps_rate = None
        for r in shi.rates:
            if r.carrier == "USPS":
                if usps_rate == None or float(r.rate) < usps_rate:
                    usps_rate = float(r.rate)

        #self.is_primed = True
        self.basket_total_shipping = D(usps_rate)
        return D(usps_rate)

    def basket_charge_excl_tax(self):
        return D('2.00')

    #def basket_charge_incl_tax(self):
    #    return self.charge_incl_tax

    #def basket_charge_excl_tax(self):
    #    return self.charge_excl_tax



class OfferDiscount(ShippingMethod):
    """
    Wrapper class that applies a discount to an existing shipping method's
    charges
    """

    def __init__(self, method, offer):
        self.method = method
        self.offer = offer

    @property
    def is_discounted(self):
        # We check to see if the discount is non-zero.  It is possible to have
        # zero shipping already in which case this the offer does not lead to
        # any further discount.
        return self.get_discount()['discount'] > 0

    @property
    def discount(self):
        return self.get_discount()['discount']

    @property
    def code(self):
        return self.method.code

    @property
    def name(self):
        return self.method.name

    @property
    def description(self):
        return self.method.description

    def get_discount(self):
        # Return a 'discount' dictionary in the same form as that used by the
        # OfferApplications class
        parent_charge = self.method.basket_charge_incl_tax()
        return {
            'offer': self.offer,
            'result': None,
            'name': self.offer.name,
            'description': '',
            'voucher': self.offer.get_voucher(),
            'freq': 1,
            'discount': self.offer.shipping_discount(parent_charge)}

    def basket_charge_incl_tax_before_discount(self):
        return self.method.basket_charge_incl_tax()

    def basket_charge_excl_tax_before_discount(self):
        return self.method.basket_charge_excl_tax()

    def basket_charge_incl_tax(self):
        parent_charge = self.method.basket_charge_incl_tax()
        discount = self.offer.shipping_discount(parent_charge)
        return parent_charge - discount

    def basket_charge_excl_tax(self):
        # Adjust tax exclusive rate using the ratio of the two tax inclusive
        # charges.
        parent_charge_excl_tax = self.method.basket_charge_excl_tax()
        parent_charge_incl_tax = self.method.basket_charge_incl_tax()
        charge_incl_tax = self.basket_charge_incl_tax()
        if parent_charge_incl_tax == 0:
            return D('0.00')
        return parent_charge_excl_tax * (charge_incl_tax /
                                         parent_charge_incl_tax)
