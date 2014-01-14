from django.db import models
from django.db.models import Q

class OpenBasketManager(models.Manager):
    """For searching/creating OPEN baskets only."""
    status_filter = "Open"

    def get_query_set(self):
        return super(OpenBasketManager, self).get_query_set().filter(
            status=self.status_filter)

    def get_or_create(self, **kwargs):
        return self.get_query_set().get_or_create(
            status=self.status_filter, **kwargs)


class OpenOrFrozenBasketManager(OpenBasketManager):
    """For searching/creating OPEN baskets only."""
    status_filters = ["Open", "Frozen"]


    def get_query_set(self):
        return super(OpenBasketManager, self).get_query_set().filter(
            Q(status="Open") | Q(status="Frozen"))

    def get_or_create(self, **kwargs):
        #import ipdb;ipdb.set_trace()
        return self.get_query_set().get_or_create(
            status=self.status_filter, **kwargs)


    # def get_query_set(self):
    #      q = super(OpenOrFrozenBasketManager, self).get_query_set()
    #      q.filter(Q(status="Open") | Q(status="Frozen"))
    #      return q

    # def get_or_create(self, **kwargs):
    #     try:
    #         b = self.get(self.get_query_set(), **kwargs )
    #         return b, False
    #     except:
    #         b = super(OpenOrFrozenBasketManager, self).create()
    #         return b, True


class SavedBasketManager(models.Manager):
    """For searching/creating SAVED baskets only."""
    status_filter = "Saved"

    def get_query_set(self):
        return super(SavedBasketManager, self).get_query_set().filter(
            status=self.status_filter)

    def create(self, **kwargs):
        return self.get_query_set().create(status=self.status_filter, **kwargs)

    def get_or_create(self, **kwargs):
        return self.get_query_set().get_or_create(
            status=self.status_filter, **kwargs)
