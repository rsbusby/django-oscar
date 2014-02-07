import zlib

from django.conf import settings
from django.db.models import get_model

from oscar.core.loading import get_class

from oscar.apps.customer.history_helpers import _get_list_from_json_string, _get_json_string_from_list

Applicator = get_class('offer.utils', 'Applicator')
Basket = get_model('basket', 'basket')
Seller = get_model('homemade', 'Seller')


from apps.homemade.homeMade import *

class BasketMiddleware(object):

    def process_request(self, request):
        request.cookies_to_delete = []

        #print "in basket middleware, yay"
        #print request.user
        basket = self.get_basket(request)
        #   baskets = self.get_baskets(request)        
        self.apply_offers_to_basket(request, basket)
        #for b in baskets:
        #    self.apply_offers_to_basket(request, b)    
       
        request.basket = basket

        if hasattr(request, 'user') and request.user.is_authenticated():
            request.mu = getSellerFromOscarID(request.user.id)
        #request.baskets = baskets
        return

    def get_basket(self, request):
        manager = Basket.open


        cookie_basket = self.get_cookie_basket(
            settings.OSCAR_BASKET_COOKIE_OPEN, request, manager)

        cookie_baskets = self.get_cookie_baskets(
            settings.OSCAR_BASKET_COOKIE_OPEN + 's', request, manager)

        if not hasattr(request, 'seller'):
            seller = None
        if hasattr(request, 'user') and request.user.is_authenticated():
            # Signed-in user: if they have a cookie basket too, it means
            # that they have just signed in and we need to merge their cookie
            # basket into their user basket, then delete the cookie

            ## if cookie baskets, rtansfer those
            if cookie_baskets:
                ## merge is easy, since just means to set the owner
                ## for now I'm not going to merge the contents really, just overwrite.
                ## If people really need that, then . .. weell deal with it later
                ## Oops, non-merge just results in 2 baskets, not that bad really
                for basket in cookie_baskets:
                    if basket.owner:
                        raise Exception
                    ## don;t add baskets for your own booth yo
                    if basket.seller != request.user:
                        basket.owner = request.user
                        basket.save()

                ## delete anon cookie(s)
                request.cookies_to_delete.append(settings.OSCAR_BASKET_COOKIE_OPEN + 's')
                request.cookies_to_delete.append(settings.OSCAR_BASKET_COOKIE_OPEN)  

                ## get rid of empty default basket if exists
                try:
                    basket = Basket.objects.filter(owner=request.user)[0]
                    if basket.is_empty():
                        basket.delete()
                except:
                    pass

                return cookie_baskets[0]

            try:
                basket, _ = manager.get_or_create(owner=request.user) #seller=seller
            except Basket.MultipleObjectsReturned:
                # Not sure quite how we end up here with multiple baskets
                # We merge them and create a fresh one
                #old_baskets = list(manager.filter(owner=request.user))
                #if not hasattr(basket, 'seller'):
                #    basket = old_baskets[0]
                #    for other_basket in old_baskets[1:]:
                #        self.merge_baskets(basket, other_basket)
                #else:
                #    baskets = []
                #    self.merge_baskets_by_seller(baskets, old_baskets)
                baskets = manager.filter(owner=request.user)
                if request.session.has_key('cur_basket_id'):
                    try:
                        basket = Basket.objects.filter(id=request.session['cur_basket_id'])[0]
                    except:
                        basket = baskets[0]
                else:
                    basket = baskets[0]
            # Assign user onto basket to prevent further SQL queries when
            # basket.owner is accessed.
            #basket.owner = request.user

            if cookie_basket:
                self.merge_baskets(basket, cookie_basket)
                request.cookies_to_delete.append(
                    settings.OSCAR_BASKET_COOKIE_OPEN)
        elif cookie_basket:
            # Anonymous user with a basket tied to the cookie
            basket = cookie_basket
        else:
            # Anonymous user with no basket - we don't save the basket until
            # we need to.
            basket = Basket()
        return basket ##, baskets


    def get_baskets(self, request):
        manager = Basket.open
        cookie_baskets = self.get_cookie_baskets(
            settings.OSCAR_BASKET_COOKIE_OPEN, request, manager)

        #if not hasattr(request, 'seller'):
        #    seller = None
        if hasattr(request, 'user') and request.user.is_authenticated():
            # Signed-in user: if they have a cookie basket too, it means
            # that they have just signed in and we need to merge their cookie
            # basket into their user basket, then delete the cookie
            
            baskets = manager.filter(owner=request.user)
            #try:
            #    basket, _ = manager.get_or_create(owner=request.user) #seller=seller
            # except Basket.MultipleObjectsReturned:
            #     #  multiple baskets are OK, since there could be one for each booth/seller
            #     # We merge the ones for each seller
            #     old_baskets = list(manager.filter(owner=request.user))
            #     if not hasattr(basket, 'seller'):
            #         basket = old_baskets[0]
            #         for other_basket in old_baskets[1:]:
            #             self.merge_baskets(basket, other_basket)
            #     else:
            #         baskets = []
            #         self.merge_baskets_by_seller(baskets, old_baskets)

            # Assign user onto basket to prevent further SQL queries when
            # basket.owner is accessed.
            #for b in baskets:
            #    b.owner = request.user
            #    b.save()

            #if cookie_baskets:
            #    self.merge_baskets_by_seller(baskets, cookie_baskets)
            #    request.cookies_to_delete.append(
            #        settings.OSCAR_BASKET_COOKIE_OPEN)
        elif cookie_baskets:
            # Anonymous user with baskets tied to the cookie
            baskets = cookie_baskets

        else:
            # Anonymous user with no basket - we don't save the basket until
            # we need to.
            basket = Basket()
            baskets = []
            baskets.append(basket)
        return baskets

    def merge_baskets(self, master, slave):
        """
        Merge one basket into another.

        This is its own method to allow it to be overridden
        """
        master.merge(slave, add_quantities=False)


    def merge_baskets_by_seller(self, baskets, old_baskets):
        """
        Merge baskets which correspond to the same seller(s).

        """



        master.merge(slave, add_quantities=False)
        return

    def process_response(self, request, response):
        # Delete any surplus cookies

        if hasattr(request, 'cookies_to_delete'):
            for cookie_key in request.cookies_to_delete:
                response.delete_cookie(cookie_key)

        # If a basket has had products added to it, but the user is anonymous
        # then we need to assign it to a cookie
       
        baskets = []
        #print request.basket
        if hasattr(request, 'basket') and request.basket.id > 0 and not request.user.is_authenticated():
            baskets = self.get_cookie_baskets( settings.OSCAR_BASKET_COOKIE_OPEN + 's', request, Basket.open)
            print "Process response"
            print baskets
            if request.basket not in baskets:
                baskets.append(request.basket)
            print baskets
            basket_ids = [b.id for b in baskets]
            #cookie = "%s_%s" % (
            #    request.basket.id, self.get_basket_hash(request.basket.id))
            response.set_cookie( settings.OSCAR_BASKET_COOKIE_OPEN + 's',
                                    _get_json_string_from_list(basket_ids),
                                    max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
                                    httponly=True)   
             

        if (hasattr(request, 'basket') and request.basket.id > 0
                and not request.user.is_authenticated()
                and settings.OSCAR_BASKET_COOKIE_OPEN not in request.COOKIES):
            cookie = "%s_%s" % (
                request.basket.id, self.get_basket_hash(request.basket.id))
            response.set_cookie(settings.OSCAR_BASKET_COOKIE_OPEN,
                                cookie,
                                max_age=settings.OSCAR_BASKET_COOKIE_LIFETIME,
                                httponly=True)
        return response

    def process_template_response(self, request, response):
        if hasattr(response, 'context_data'):
            if response.context_data is None:
                response.context_data = {}

            if 'basket' not in response.context_data:
                response.context_data['basket'] = request.basket
            else:
                # Occasionally, a view will want to pass an alternative basket
                # to be rendered.  This can happen as part of checkout
                # processes where the submitted basket is frozen when the
                # customer is redirected to another site (eg PayPal).  When the
                # customer returns and we want to show the order preview
                # template, we need to ensure that the frozen basket gets
                # rendered (not request.basket).  We still keep a reference to
                # the request basket (just in case).
                response.context_data['request_basket'] = request.basket
        return response

    def get_cookie_basket(self, cookie_key, request, manager):
        """
        Looks for a basket which is referenced by a cookie.

        If a cookie key is found with no matching basket, then we add
        it to the list to be deleted.
        """
        basket = None

        if cookie_key in request.COOKIES:
            parts = request.COOKIES[cookie_key].split("_")
            if len(parts) != 2:
                return basket
            basket_id, basket_hash = parts
            if basket_hash == self.get_basket_hash(basket_id):
                try:
                    basket = Basket.objects.get(pk=basket_id, owner=None,
                                                status=Basket.OPEN)
                except Basket.DoesNotExist:
                    request.cookies_to_delete.append(cookie_key)
            else:
                request.cookies_to_delete.append(cookie_key)
        return basket


    def get_cookie_baskets(self, cookie_key, request, manager):
        """
        Looks for baskets which are referenced by a cookie.

        If a cookie key is found with no matching baskets, then we add
        it to the list to be deleted.
        """
        baskets = []
        
        if cookie_key in request.COOKIES:
            #parts = request.COOKIES[cookie_key].split("_")
            #if len(parts) != 2:
            #    return baskets
            #basket_id, basket_hash = parts
            
            basketIdList = _get_list_from_json_string(request.COOKIES[cookie_key])

            for basket_id in basketIdList:
                if 1: ##basket_hash == self.get_basket_hash(basket_id):
                    try:

                        basket = Basket.objects.get(pk=basket_id, owner=None,
                                                    status=Basket.OPEN)
                        baskets.append(basket)
                    except Basket.DoesNotExist:
                        request.cookies_to_delete.append(cookie_key)
                else:
                    request.cookies_to_delete.append(cookie_key)
        return baskets

    def apply_offers_to_basket(self, request, basket):
        if not basket.is_empty:
            Applicator().apply(request, basket)

    def get_basket_hash(self, basket_id):
        return str(zlib.crc32(str(basket_id) + settings.SECRET_KEY))
