
from homeMade import *

from oscar.test.factories import *

from django.core.files import File
from django.conf import settings


##from oscar.apps.customer.models import User
from django.contrib.auth.models import User

from oscar.apps.catalogue.models import Category, ProductCategory
from oscar.apps.partner.models import Partner


## for all partners in Oscar, copy the stripe info from Mongo to partner model


for p in Partner.objects.all():

	if getSellerFromOscarID(p.user.id):
		mu = getSellerFromOscarID(p.user.id)
		#if mu.stripeSellerToken:
		#	p.stripeToken = mu.stripeSellerToken
		#if mu.stripeSellerPubKey:
		#	p.stripePubKey = mu.stripeSellerPubKey
		
		#if mu.bio:
		#	p.bio = mu.bio
		
		#if mu.zipcode:
		#	p.zipcode = mu.zipcode

		if mu.storePicPath:
			p.picPath = mu.storePicPath

		p.save()



