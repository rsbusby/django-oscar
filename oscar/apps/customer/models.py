from oscar.apps.customer import abstract_models
from django.db import models
from oscar.core.compat import AUTH_USER_MODEL
from django.utils.translation import ugettext_lazy as _


class Email(abstract_models.AbstractEmail):
	sender = models.ForeignKey(AUTH_USER_MODEL, related_name='sent_emails', verbose_name=_("Sender"),
			blank=True, null=True)
    


class CommunicationEventType(abstract_models.AbstractCommunicationEventType):
    pass


class Notification(abstract_models.AbstractNotification):
    pass


class ProductAlert(abstract_models.AbstractProductAlert):
    pass


from oscar.apps.customer.history_helpers import *
from oscar.apps.customer.alerts.receivers import *