import warnings
from django.conf import settings
from django.shortcuts import redirect

from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import get_model
from django.utils.translation import ugettext_lazy as _

from oscar.core.loading import get_class
from oscar.apps.catalogue.signals import product_viewed, product_search

from apps.homemade.homeMade import Seller
#from apps.user.models import ExtendedUser
from django.db.models import Q



Product = get_model('catalogue', 'product')
ProductReview = get_model('reviews', 'ProductReview')
Category = get_model('catalogue', 'category')
ProductAlert = get_model('customer', 'ProductAlert')
ProductAlertForm = get_class('customer.forms', 'ProductAlertForm')
Partner = get_model('partner', 'partner')


class ProductDetailView(DetailView):
    context_object_name = 'product'
    model = Product
    view_signal = product_viewed
    template_folder = "catalogue"

    def post(self, request, *args, **kwargs):
        ##import ipdb;ipdb.set_trace()

        print "WHOASSA in post"
        self.object = product = self.get_object()
        partner = product.stockrecord.partner
        owner = partner.user
        if self.request.user != owner and not self.request.user.is_staff:
            return self.get(request, **kwargs)
        print request.POST
        if request.POST.has_key('enable'):
            self.object = product = self.get_object()
            product.status = None
            product.save()  
        if request.POST.has_key('disable'):    
            if request.user.is_staff:
                product.status = "admin_disabled"
            else:
                product.status = "user_disabled"
            product.save()
        return self.get(request, **kwargs)



    def get(self, request, **kwargs):
        """
        Ensures that the correct URL is used before rendering a response
        """
        #import pdb;pdb.set_trace()
        self.object = product = self.get_object()

        ## check permissions, if item is disabled reroute.
        if product.status:
            partner = product.stockrecord.partner
            owner = partner.user

            if product.status.count('disable') and self.request.user != owner and not self.request.user.is_staff:
                return redirect('/catalogue/')

        if product.is_variant:
            return HttpResponsePermanentRedirect(
                product.parent.get_absolute_url())

        correct_path = product.get_absolute_url()
        if correct_path != request.path:
            return HttpResponsePermanentRedirect(correct_path)

        response = super(ProductDetailView, self).get(request, **kwargs)
        self.send_signal(request, response, product)
        return response

    def get_object(self, queryset=None):
        # Check if self.object is already set to prevent unnecessary DB calls
        if hasattr(self, 'object'):
            return self.object
        else:
            return super(ProductDetailView, self).get_object(queryset)

    def get_context_data(self, **kwargs):
        ctx = super(ProductDetailView, self).get_context_data(**kwargs)
        ctx['reviews'] = self.get_reviews()
        ctx['alert_form'] = self.get_alert_form()
        ctx['has_active_alert'] = self.get_alert_status()

        try:
            product = self.object
            partner = product.stockrecord.partner
            ctx['partner'] = partner
            ctx['seller'] = partner.user
            ctx['sellerObj'] = Seller.objects.filter(oscarUserID=partner.user.id)[0]
        except:
            pass
        try:
            ctx['muser'] = Seller.objects.filter(oscarUserID=self.request.user.id)[0]
            ctx['u'] = Seller.objects.filter(oscarUserID=self.request.user.id)[0]
        except:
            pass
        return ctx

    def get_alert_status(self):
        # Check if this user already have an alert for this product
        has_alert = False
        if self.request.user.is_authenticated():
            alerts = ProductAlert.objects.filter(
                product=self.object, user=self.request.user,
                status=ProductAlert.ACTIVE)
            has_alert = alerts.count() > 0
        return has_alert

    def get_alert_form(self):
        return ProductAlertForm(
            user=self.request.user, product=self.object)

    def get_reviews(self):
        return self.object.reviews.filter(status=ProductReview.APPROVED)

    def send_signal(self, request, response, product):
        self.view_signal.send(
            sender=self, product=product, user=request.user, request=request,
            response=response)

    def get_template_names(self):
        """
        Return a list of possible templates.

        We try 2 options before defaulting to catalogue/detail.html:
            1). detail-for-upc-<upc>.html
            2). detail-for-class-<classname>.html

        This allows alternative templates to be provided for a per-product
        and a per-item-class basis.
        """
        return [
            '%s/detail-for-upc-%s.html' % (
                self.template_folder, self.object.upc),
            '%s/detail-for-class-%s.html' % (
                self.template_folder, self.object.get_product_class().slug),
            '%s/detail.html' % (self.template_folder)]


def get_product_base_queryset():
    """
    Deprecated. Kept only for backwards compatibility.
    Product.browsable.base_queryset() should be used instead.
    """
    warnings.warn(("`get_product_base_queryset` is deprecated in favour of"
                   "`base_queryset` on Product's managers. It will be removed"
                   "in Oscar 0.7."))
    return Product.browsable.base_queryset()

class ProductCategoryView(ListView):
    """
    Browse products in a given category

    Category URLs used to be based on solely the slug. Renaming the category
    or any of the parent categories would break the URL. Hence, the new URLs
    consist of both the slug and category PK (compare product URLs).
    The legacy way still works to not break existing systems.
    """
    context_object_name = "products"
    template_name = 'catalogue/browse.html'
    paginate_by = settings.OSCAR_PRODUCTS_PER_PAGE

    def get_object(self):
        if 'pk' in self.kwargs:
            self.category = get_object_or_404(Category, pk=self.kwargs['pk'])
        else:
            self.category = get_object_or_404(Category,
                                              slug=self.kwargs['category_slug'])

    def get(self, request, *args, **kwargs):
        self.get_object()
        correct_path = self.category.get_absolute_url()
        if correct_path != request.path:
            return HttpResponsePermanentRedirect(correct_path)
        self.categories = self.get_categories()
        return super(ProductCategoryView, self).get(request, *args, **kwargs)

    def get_categories(self):
        """
        Return a list of the current category and it's ancestors
        """
        categories = list(self.category.get_descendants())
        categories.append(self.category)
        return categories

    def get_context_data(self, **kwargs):
        context = super(ProductCategoryView, self).get_context_data(**kwargs)

        context['categories'] = self.categories
        context['category'] = self.category
        context['summary'] = self.category.name
        return context

    def get_queryset(self):
        return Product.browsable.base_queryset().filter(
            categories__in=self.categories
        ).distinct()


class ProductListView(ListView):
    """
    A list of products
    """
    context_object_name = "products"
    template_name = 'catalogue/browse.html'
    paginate_by = settings.OSCAR_PRODUCTS_PER_PAGE
    search_signal = product_search
    model = Product
    q = None
    pq = None


    def post(self, request, *args, **kwargs):
        ##import ipdb;ipdb.set_trace()

        print "WHOASSA in post"
        self.get_search_query()
        qs = self.get_queryset()
        ps = self.model.objects.all()
        print request.POST
        print qs
        for p in qs:
            partner = p.stockrecord.partner
            owner = partner.user
            if self.request.user != owner and not self.request.user.is_staff:
                return self.get(request, **kwargs)

            if request.POST.has_key('enable'):
                p.status = None
                p.save()  
            if request.POST.has_key('disable'):    
                if request.user.is_staff:
                    p.status = "admin_disabled"
                else:
                    p.status = "user_disabled"
                p.save()
        return self.get(request, **kwargs)


    def get_search_query(self):
        q = self.request.GET.get('q', None)
        self.q =  q.strip() if q else None
        pq = self.request.GET.get('booth', None)
        self.pq = pq.strip() if pq else None
        return 

    def get_queryset(self):
        q = self.get_search_query()
        q = self.q
        pq = self.pq
       
        #if not q:
        #     q = self.model.objects.exclude(status='disabled')
        # else:
        #     q = q.exclude(status='')
        # if not pq:
        #     pq = Q(exclude(status=''))
        # else:
        #     pq = pq.exclude(status='')        
        qs = Product.browsable.base_queryset()

        if q:
            # Send signal to record the view of this product
            #self.search_signal.send(sender=self, query=q, user=self.request.user)
            qs = qs.filter(title__icontains=q)
           
            return qs
        elif pq:
            try:
                partner = Partner.objects.filter(name=pq)[0]
            except:
                return qs
            qs = Product.objects.all()
            qs = qs.filter(stockrecord__partner__name=pq)
            owner = partner.user
            if not (self.request.user.is_staff or self.request.user == owner):
                qs = qs.exclude(status='disabled')
            return qs
        else:
            ## if not filtered, don'tshow "Other" items
            category = Category.objects.filter(name="Other")[0]
            categories = list(category.get_descendants())
            categories.append(category)
            qs = qs.exclude(categories__in=categories)
            return qs

    def get_context_data(self, **kwargs):
        context = super(ProductListView, self).get_context_data(**kwargs)
        self.get_search_query()
        q = self.q
        pq = self.pq
        if not q and not pq:
            context['summary'] = _('All items')
        else:
            context['summary'] = _("Products matching '%(query)s'") % {'query': q}
            context['search_term'] = q
            if pq:

                try:
                ##if True:
                    #partner = self.request.user.partner
                    partner = Partner.objects.filter(name=pq)[0]
                    context['partner'] = partner
                    context['summary'] = partner.name
                    ## current user in MongoDB
                    context['muser'] = Seller.objects.filter(oscarUserID=self.request.user.id)[0]
                    ## seller (booth owner) in Mongo
                    context['u'] = Seller.objects.filter(oscarUserID=partner.user.id)[0]
                    context['sellerObj'] = Seller.objects.filter(oscarUserID=partner.user.id)[0]

                    self.template_name = 'catalogue/booth.html'
                    #self.template_name = '../../sites/homemade/apps/homemade/templates/store.dj.html' 

                except:
                    pass

        return context

class ProductWithPartnerListView(ListView):
    """
    A list of products
    """
    context_object_name = "products"
    template_name = 'catalogue/browse.html'
    paginate_by = settings.OSCAR_PRODUCTS_PER_PAGE
    search_signal = product_search
    model = Product
    q = None
    pq = None


    def get_search_query(self):
        q = self.request.GET.get('q', None)
        self.q =  q.strip() if q else None
        pq = self.request.GET.get('booth', None)
        self.pq = pq.strip() if pq else None
        return 

    def get_queryset(self):
        q = self.get_search_query()
        q = self.q
        pq = self.pq
        qs = Product.browsable.base_queryset()
        if q:
            # Send signal to record the view of this product
            self.search_signal.send(sender=self, query=q, user=self.request.user)
            return qs.filter(title__icontains=q)
        elif pq:
            return qs.filter(stockrecord__partner__name=pq)
        else:
            return qs

    def get_context_data(self, **kwargs):
        context = super(ProductWithPartnerListView, self).get_context_data(**kwargs)
        self.get_search_query()
        q = self.q
        pq = self.pq
        if not q and not pq:
            context['summary'] = _('All products')
        else:
            context['summary'] = _("Products matching '%(query)s'") % {'query': q}
            context['search_term'] = q
            if pq:

                try:
                    partner = self.request.user.partner
                    context['partner'] = partner
                    context['summary'] = partner.name
                    mongo_key = self.request.user.email
                    context['muser'] = Seller.objects.filter(email=self.request.user.email)
                    self.template_name = 'catalogue/booth.html'

                except:
                    pass

        return context



class PartnerListView(ProductListView):
    """
    A list of products filtered by partner
    """
    context_object_name = "products"
    template_name = 'catalogue/browse.html'
    paginate_by = settings.OSCAR_PRODUCTS_PER_PAGE
    search_signal = product_search
    model = Product

    def get_context_data(self, **kwargs):
        context = super(ProductListView, self).get_context_data(**kwargs)
        q = self.get_search_query()
        if not q:
            context['summary'] = _('Products for all booths')
        else:
            context['summary'] = _("Products matching '%(query)s'") % {'query': q}
            context['search_term'] = q
        return context

