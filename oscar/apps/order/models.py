from oscar.apps.order.abstract_models import *
from oscar.apps.address.abstract_models import AbstractShippingAddress, AbstractBillingAddress

from django.db import models


class Order(AbstractOrder):


    sponsored_org = models.ForeignKey(
        'order.SponsoredOrganization', null=True, blank=True,
        verbose_name=("Organization to Benefit"))

    ## shipping rate id for EasyPost  

    shipping_rate_id = models.CharField(("Shipping Rate ID"), max_length=128, null=True, blank=True)
    shipping_carrier = models.CharField(("Shipping Carrier"), max_length=128, null=True, blank=True)
    shipping_service = models.CharField(("Shipping Service"), max_length=128, null=True, blank=True)

    ## JSON shipping info from shipping SAAS, i.e. EasyPost or Postmaster.io Could use JSON field but I don't care if it's valid
    shipping_info_json = models.TextField(("Shipping Info"), blank=True, null=True)
    shipping_label_json = models.TextField(("Shipping Label Info"), blank=True, null=True)

class SponsoredOrganization(models.Model):

    name = models.CharField(("Name"), max_length=256, null=True, blank=True)
    status = models.CharField(("Status"), max_length=128, null=True, blank=True)
    website = models.CharField(("Website"), max_length=256, null=True, blank=True)
    description = models.TextField(("Description"), null=True, blank=True)

class OrderNote(AbstractOrderNote):
    pass


class CommunicationEvent(AbstractCommunicationEvent):
    pass


class ShippingAddress(AbstractShippingAddress):
    pass


class BillingAddress(AbstractBillingAddress):
    pass
    

class Line(AbstractLine):
    pass


class LinePrice(AbstractLinePrice):
    pass


class LineAttribute(AbstractLineAttribute):
    pass


class ShippingEvent(AbstractShippingEvent):
    pass


class ShippingEventType(AbstractShippingEventType):
    pass


class PaymentEvent(AbstractPaymentEvent):
    pass


class PaymentEventType(AbstractPaymentEventType):
    pass


class OrderDiscount(AbstractOrderDiscount):
    pass


    