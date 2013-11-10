"""
Vanilla product models
"""
from oscar.apps.catalogue.abstract_models import *

from haystack.utils.geo import Point, D



class ProductClass(AbstractProductClass):
    pass


class Category(AbstractCategory):
    pass


class ProductCategory(AbstractProductCategory):
    pass


class Product(AbstractProduct):


    def get_location(self):
        # Remember, longitude FIRST!

        if self.stockrecord.latitude:
            return Point(self.stockrecord.longitude, self.stockrecord.latitude)
        else:
            #if self.stockrecord.partner.latitude:
            #    return Point(self.stockrecord.partner.longitude, self.stockrecord.partner.latitude)
            #else:
            return Point(0.0, 0.0)

    pass


class ContributorRole(AbstractContributorRole):
    pass


class Contributor(AbstractContributor):
    pass


class ProductContributor(AbstractProductContributor):
    pass


class ProductAttribute(AbstractProductAttribute):
    pass


class ProductAttributeValue(AbstractProductAttributeValue):
    pass


class AttributeOptionGroup(AbstractAttributeOptionGroup):
    pass


class AttributeOption(AbstractAttributeOption):
    pass


class AttributeEntity(AbstractAttributeEntity):
    pass


class AttributeEntityType(AbstractAttributeEntityType):
    pass


class Option(AbstractOption):
    pass


class ProductImage(AbstractProductImage):
    pass

from .receivers import *
