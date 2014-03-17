from django.conf.urls import patterns, url, include

#from apps.gateway import views
from apps.homemade.homeMade import *
import oscar

#print "TESTVar"
#print testVar

#print" App"
#print app

#import pdb;pdb.set_trace()

#app.request = 
#urlpatterns = patterns('',
#    url(r'^$', 'o_about', name='about')
#)
urlpatterns = patterns('',
    url(r'^$', about, name='about'),
    url(r'^aboutCA1616/$', aboutCaliLaw, name='aboutCaliLaw'),
    url(r'^our_team/$', bios, name='bios'),
    url(r'^resources/$', resources, name='resources'),


    url(r'^register_store/$', register_store, name='register_store'),
    url(r'^edit_store/$', edit_store, name='edit_store'),
    url(r'^blog/$', blogAll, name='blogAll'),
    url(r'^events/$', showEvents, name='showEvents'),
    url(r'^events/filter/$', filterEvents, name='filterEvents'),

    url(r'^invite/$', invite, name='invite'),

    url(r'^faq_main/$', faq_main, name='faq_main'),
    url(r'^hm_test/$', hm_test, name='hm_test'),

    url(r'^blog/(?P<blog_post_id>\d+)/$', blog_post, name='blog_post'),
    url(r'^new_blog_post/$', new_blog_post_b, name='new_blog_post'),
    url(r'^blog_edit/(?P<blog_post_id>\d+)/$', edit_blog_post, name='edit_blog_post'),


##            url(r'^category/(?P<category_slug>[\w-]+(/[\w-]+)*)_(?P<pk>\d+)/$',


    url(r'^contact_us/$', contactUs, name='contactUs'),
    ##url(r'^contact/(?P<store_name>[\w-]*)/$', contactPeer, name='contactPeer'),
    url(r'^contact/$', contactPeer, name='contactPeer'),    
    url(r'^contact_buyer/$', contactGuestBuyer, name='contactGuestBuyer'),    


    url(r'^terms_of_use/$', termsOfUse, name='termsOfUse'),
    url(r'^stripe_connect_signup/$', stripe_connect_signup, name='stripe_connect_signup'),
    url(r'^stripe_login/$', stripeLogin, name='stripeLogin'),
    url(r'^stripe_authorized/$', stripeAuthorized, name='stripeAuthorized'),
    # url(r'^store/$', store, name='store'),
	url(r'^store/$', oscar.apps.catalogue.views.ProductListView.as_view(), name='booth'),

    url(r'^folks/favorite_folks"/$', favSellers, name='favSellers'),


    ##url(r'^weblog/', include('zinnia.urls')),
    #url(r'^comments/', include('django.contrib.comments.urls')),


)

