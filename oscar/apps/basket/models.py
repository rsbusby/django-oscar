from oscar.apps.basket.abstract_models import (
    AbstractBasket, AbstractLine, AbstractLineAttribute)

from django.db import models


class InvalidBasketLineError(Exception):
    pass


class Basket(AbstractBasket):
    
	sponsored_org = models.ForeignKey(
        'order.SponsoredOrganization', null=True, blank=True,
        verbose_name=("Organization to Benefit"))




class Line(AbstractLine):
    pass


class LineAttribute(AbstractLineAttribute):
    pass
