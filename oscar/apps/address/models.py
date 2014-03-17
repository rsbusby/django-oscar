from oscar.apps.address.abstract_models import (
    AbstractUserAddress, AbstractCountry, AbstractShippingAddress)
from django.db import models
from django.utils.translation import ugettext_lazy as _, pgettext_lazy


class UserAddress(AbstractUserAddress):


    location_name = models.CharField(
        _("Location Name"), max_length=255, blank=True, null=True)

	#: Whether this address is the default for shipping FROM, sending packages
    is_default_for_store = models.BooleanField(
        _("Default store address?"), default=False)

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def get_location(self):
        # Remember, longitude FIRST!
        return Point(self.longitude, self.latitude)


    def getDistanceBetweenTwoAddresses(a1, a2):
        '''For short distances. For longer, user haversine formula'''

        lon1 = a1.longitude
        lat1 = a1.latitude
        lon2 = a2.longitude
        lat2 = a2.latitude
        R = 3959  ##(mi) ##6371 ##(km)

        x = (lon2-lon1) * Math.cos((lat1+lat2)/2);
        y = (lat2-lat1);
        d = Math.sqrt(x*x + y*y) * R;

        return d


class Country(AbstractCountry):
    pass


