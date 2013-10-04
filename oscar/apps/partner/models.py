from oscar.apps.address.abstract_models import AbstractPartnerAddress
from oscar.apps.partner.abstract_models import (
    AbstractPartner, AbstractStockRecord, AbstractStockAlert)

from oscar.apps.catalogue.models import Product
#from apps.homemade.homeMade import Item

class Partner(AbstractPartner):
    pass


class PartnerAddress(AbstractPartnerAddress):
    pass


class StockRecord(AbstractStockRecord):
    pass


from django.db.models.signals import post_save
from django.dispatch import receiver
@receiver(post_save, sender=Product)
def createLinkFromUserToPartner(sender, instance, **kwargs):
    print "OK receiver called for createStockRecord"
    #i = Item()
    print "OK makin' a stockrecorddddddddd"	
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


from oscar.apps.partner.receivers import *