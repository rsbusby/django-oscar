from oscar.apps.address.abstract_models import AbstractPartnerAddress
from oscar.apps.partner.abstract_models import (
    AbstractPartner, AbstractStockRecord, AbstractStockAlert)

from oscar.apps.catalogue.models import Product
#from apps.homemade.homeMade import Item
from django.db import models
from django.utils.translation import ugettext_lazy as _


from haystack.utils.geo import Point, D


class Partner(AbstractPartner):
    pass


class PartnerAddress(AbstractPartnerAddress):

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def get_location(self):
        # Remember, longitude FIRST!
        return Point(self.longitude, self.latitude)

    pass


class StockRecord(AbstractStockRecord):


    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def get_location(self):
        # Remember, longitude FIRST!
        return Point(self.longitude, self.latitude)

    made_to_order = models.BooleanField(_("Made To Order"), default=False, db_index=True)

    is_shippable = models.BooleanField(_("Is Shippable"), default=False, db_index=True)

    weight = models.FloatField(_("Weight"), blank=True, null=True)

    pass

#from oscar.apps.partner.receivers import *
#from django.db.models.signals import post_save
#from django.dispatch import receiver
#@receiver(post_save, sender=Product)

##def createLinkFromUserToPartner(sender, instance, created, **kwargs):
    #print "OK receiver called for createStockRecord"
    #i = Item()
    #if created:
    #    print "OK makin' a stockrecorddddddddd"	
    ## create stockrecord, maybe don't need to???

    ## create new Partner if necessary

    ## check if partner exists.

    ## make changes to MongoDB model, store present, etc.

    #s.email = instance.email
    #s.password = instance.password
    #s.djangoID = instance.id
    #i.save()



class StockAlert(AbstractStockAlert):
    pass


