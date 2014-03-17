from oscar.apps.address.abstract_models import AbstractPartnerAddress
from oscar.apps.partner.abstract_models import (
    AbstractPartner, AbstractStockRecord, AbstractStockAlert)

from django.db import models
from django.db.models import Sum, Count, get_model

##from oscar.apps.catalogue.models import Product, ProductImage
from oscar.apps.catalogue.abstract_models import AbstractProduct, AbstractProductImage
#Product = get_model('product', 'Product')
#ProductImage = get_model('product_image', 'ProductImage')

#from apps.homemade.homeMade import Item
#from django.db import models
from django.utils.translation import ugettext_lazy as _


from haystack.utils.geo import Point, D

from oscar.apps.shipping.models import ShippingMethod

class Partner(AbstractPartner):


    ## took this from reviews, should work nicely for moderating booths
    FOR_MODERATION, APPROVED, REJECTED = range(0, 3)
    STATUS_CHOICES = (
        (FOR_MODERATION, _("Requires moderation")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
    )
    default_status = FOR_MODERATION ##if settings.OSCAR_MODERATE_REVIEWS else APPROVED
    status = models.SmallIntegerField(
        _("Status"), choices=STATUS_CHOICES, default=default_status)

    
    stripePubKey = models.CharField(max_length=32, blank=True, null=True,  help_text="Stripe public key for connected user")
    stripeToken  = models.CharField(max_length=32, blank=True, null=True,  help_text="Stripe access key returned from Stripe Connect authorization process")

    bio = models.TextField(("Bio"), null=True, blank=True)

    zipcode = models.CharField(
        _("Zipcode"), max_length=5, blank=True, null=True)

    picPath = models.CharField(
        _("Pic path"), max_length=255, blank=True, null=True)

    ## JSON blob of shipping prefs
    shipping_options = models.TextField(("Shipping Options"), null=True, blank=True)


class PartnerImage(AbstractProductImage):
    
    partner = models.ForeignKey(
        'partner.Partner', related_name='images', verbose_name=_("Partner"))

    class Meta:
        abstract = True
        unique_together = ("partner", "display_order")
        ordering = ["display_order"]
        verbose_name = _('Partner Image')
        verbose_name_plural = _('Partner Images')



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
    local_pickup_enabled = models.BooleanField(_("Local Pickup Enabled"), default=False, db_index=True)
    weight = models.FloatField(_("Weight"), blank=True, null=True)

    #shipping_methods = models.ManyToManyField(ShippingMethod, null=True,
    #                                   blank=True, verbose_name=_("Shipping Methods"))

    shipping_options = models.TextField(_("Shipping Options"), blank=True, null=True)


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


