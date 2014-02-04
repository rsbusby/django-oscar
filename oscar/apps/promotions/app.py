from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy


from oscar.core.application import Application
from oscar.apps.promotions.views import HomeView, RecordClickView
from oscar.apps.promotions.models import PagePromotion, KeywordPromotion
from oscar.apps.catalogue.views import ProductListView

#from homemade.apps.homemade.homeMade import invite

from apps.homemade.homeMade import *


class PromotionsApplication(Application):
    name = 'promotions'
    
    home_view = HomeView
    record_click_view = RecordClickView

    catalogueView = ProductListView

    def get_urls(self):
        urlpatterns = patterns('',
            url(r'page-redirect/(?P<page_promotion_id>\d+)/$', 
                self.record_click_view.as_view(model=PagePromotion), name='page-click'),
            url(r'keyword-redirect/(?P<keyword_promotion_id>\d+)/$', 
                self.record_click_view.as_view(model=KeywordPromotion), name='keyword-click'),
            ##url(r'^$', self.home_view.as_view(), name='home'),
            url(r'^$', ProductListView.as_view(), name='home'),
            #url(r'^$', invite, name='home'),

        )
        return self.post_process_urls(urlpatterns)


application = PromotionsApplication()