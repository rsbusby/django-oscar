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


    def getLatLongFromZipcode(self, zipcode):

        from apps.homemade.homeMade import HMGeoData

        gd = HMGeoData.objects.filter(zipcode=str(zipcode))[0]

        return [gd.lat, gd.long]

    def get_location(self):
        # Remember, longitude FIRST!

        if self.stockrecord.latitude:
            print "location from sotckrecord for " + self.title +" : " + str(self.stockrecord.longitude) +"  " + str(self.stockrecord.latitude)
            self.stockrecord.longitude = None
            self.stockrecord.latitude = None
            self.stockrecord.save()
            #return Point(self.stockrecord.longitude, self.stockrecord.latitude)
        else:
            # try:

            print "try"
            if self.stockrecord.partner.primary_address:
                address = self.stockrecord.partner.primary_address
                print self.stockrecord.partner.name + " has address"
               
                try:

                    zipcode = address.postcode
                except:
                    print "user " +  self.stockrecord.partner.name + " has no zipcode"
                    return None ##Point(0.0, 0.0)

                [lat, long] = self.getLatLongFromZipcode(zipcode)
                print "OK"
                print "got location from " + str(zipcode) + " for " + self.stockrecord.partner.name
                return str(long) + ',' + str(lat) ##Point(long, lat)


        return None ##Point(0.0, 0.0)

    


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
