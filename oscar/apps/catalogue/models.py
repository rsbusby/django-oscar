"""
Vanilla product models
"""
from oscar.apps.catalogue.abstract_models import *
UserAddress = get_model('address', 'UserAddress')

from haystack.utils.geo import Point, D



class ProductClass(AbstractProductClass):
    pass


class Category(AbstractCategory):
    pass


class ProductCategory(AbstractProductCategory):
    pass


class Product(AbstractProduct):


    partner = models.ForeignKey('partner.Partner', verbose_name=("Partner"), blank=True, null=True)

    def get_partner(self):
        '''get partner from product or stockrecord.'''
        try:
            if self.partner:
                return self.partner
        except:
            pass
        if self.has_stockrecord:
            return self.stockrecord.partner

        return None

    def getLatLongFromZipcode(self, zipcode):

        from apps.homemade.homeMade import HMGeoData
        if not zipcode:
            return None
        try:
            gd = HMGeoData.objects.filter(zipcode=str(zipcode))[0]
        except:
            return None
        return [gd.lat, gd.long]

    def getDistanceToBuyer(self, a1):
        
        '''For short distances. For longer, user haversine formula'''

        partnerAddress = UserAddress._default_manager.filter(user=self.stockrecord.partner.user).order_by('-is_default_for_shipping')[0]

        z1 = a1.postcode
        try:
            z2 = partnerAddress.postcode
        except:

            z2 = self.stockrecord.partner.zipcode

        if not z2:
            return None

        return self.getDistanceBetweenTwoCloseZipcodes(z1, z2)


    def getDistanceBetweenTwoCloseZipcodes(self,z1,z2):
        '''For short distances. For longer, user haversine formula'''


        from math import radians, sqrt, cos

        [lat1, lon1] = self.getLatLongFromZipcode(z1)
        [lat2, lon2] = self.getLatLongFromZipcode(z2)
        # lon1 = a1.longitude
        # lat1 = a1.latitude
        # lon2 = a2.longitude
        # lat2 = a2.latitude
        R = 3959.0  ##(mi) ##6371 ##(km)
        lat1 = radians(float(lat1))
        lon1 = radians(float(lon1))
        lat2 = radians(float(lat2))
        lon2 = radians(float(lon2))

        x = (lon2-lon1) * cos( (lat1+lat2)/2.0)
        y = lat2-lat1

        d = sqrt(x*x + y*y) * R

        return d



    def get_location(self):
        try:
            [lat, long] = self.getLatLong() 
            return str(long) + ',' + str(lat) 
        except:
            return None

    def getLatLong(self):
         return self.getLatLongFromZipcode(self.getZipcode())

    def getZipcode(self):
        # Remember, longitude FIRST!
        #import ipdb;ipdb.set_trace()
        try:
            if not self.stockrecord:
                return None
            
            #if hasattr(self.stockrecord, "latitude"):
            #if self.stockrecord.latitude:
            #        #print "location from sotckrecord for " + self.title +" : " + str(self.stockrecord.longitude) +"  " + str(self.stockrecord.latitude)
            #        self.stockrecord.longitude = None
            #        self.stockrecord.latitude = None
            #        self.stockrecord.save()
                #return Point(self.stockrecord.longitude, self.stockrecord.latitude)
            #else:
                # try:

            try:
                if self.stockrecord.partner.primary_address:
                    address = self.stockrecord.partner.primary_address
                    #print self.stockrecord.partner.name + " has address"
                   
                    try:
                        zipcode = address.postcode
                    except:
                        #print "user " +  self.stockrecord.partner.name + " has no zipcode"
                        return None ##Point(0.0, 0.0)

                    #[lat, long] = self.getLatLongFromZipcode(zipcode)
                    #print "OK"
                    #print "got location from " + str(zipcode) + " for " + self.stockrecord.partner.name
                    return zipcode #[lat, long] ##Point(long, lat)

            except:
                pass

            try:
                zipcode = self.stockrecord.partner.zipcode
                return zipcode ##self.getLatLongFromZipcode(zipcode)
            except:
                pass
        except:
            pass


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
