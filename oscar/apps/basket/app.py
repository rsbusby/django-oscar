from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from oscar.apps.basket import views
from oscar.core.application import Application


class BasketApplication(Application):
    name = 'basket'
    summary_view = views.BasketView
    multi_vendor_view = views.BasketListView
    saved_view = views.SavedView
    add_view = views.BasketAddView
    add_voucher_view = views.VoucherAddView
    remove_voucher_view = views.VoucherRemoveView

    def get_urls(self):
        urlpatterns = patterns('',
            #url(r'^$', self.summary_view.as_view(), name='summary'),
            url(r'^$', self.summary_view.as_view(), name='single'),            
            url(r'^/(?P<basket_id>\d+)/$', self.summary_view.as_view(), name='single'),            

            url(r'^multi$', self.summary_view.as_view(), name='multi'),
            url(r'^list/$', self.multi_vendor_view.as_view(), name='summary'),
            url(r'^add/$', self.add_view.as_view(), name='add'),
            url(r'^vouchers/add/$', self.add_voucher_view.as_view(),
                name='vouchers-add'),
            url(r'^vouchers/(?P<pk>\d+)/remove/$',
                self.remove_voucher_view.as_view(), name='vouchers-remove'),
            url(r'^saved/$', login_required(self.saved_view.as_view()),
                name='saved'),
        )
        return self.post_process_urls(urlpatterns)


application = BasketApplication()
