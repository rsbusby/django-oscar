from oscar.apps.address.abstract_models import (
    AbstractUserAddress, AbstractCountry)
from django.db import models
from django.utils.translation import ugettext_lazy as _, pgettext_lazy


class UserAddress(AbstractUserAddress):


	#: Whether this address is the default for shipping FROM, sending packages
    is_default_for_store = models.BooleanField(
        _("Default store address?"), default=False)

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def get_location(self):
        # Remember, longitude FIRST!
        return Point(self.longitude, self.latitude)




class Country(AbstractCountry):
    pass
