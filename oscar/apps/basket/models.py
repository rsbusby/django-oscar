from oscar.apps.basket.abstract_models import (
    AbstractBasket, AbstractLine, AbstractLineAttribute)

from django.db import models
from django.utils.translation import ugettext as _



class InvalidBasketLineError(Exception):
    pass


class Basket(AbstractBasket):
    
	sponsored_org = models.ForeignKey(
        'order.SponsoredOrganization', null=True, blank=True,
        verbose_name=("Organization to Benefit"))

	## JSON shipping info from shipping SAAS, i.e. EasyPost or Postmaster.io Could use JSON field but I don't care if it's valid
	shipping_info = models.TextField(_("Shipping Info"), blank=True, null=True)

	easyPostInfo = None


class Line(AbstractLine):
    pass


class LineAttribute(AbstractLineAttribute):
    pass
