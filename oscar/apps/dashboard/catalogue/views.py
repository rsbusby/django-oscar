from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ImproperlyConfigured
from django.views import generic
from django.db.models import get_model
from django.http import HttpResponseRedirect, Http404
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oscar.core.loading import get_classes

import json

(ProductForm,
 ProductSearchForm,
 CategoryForm,
 StockRecordForm,
 StockAlertSearchForm,
 ProductCategoryFormSet,
 ProductImageFormSet,
 ProductRecommendationFormSet) = get_classes('dashboard.catalogue.forms',
                                    ('ProductForm',
                                     'ProductSearchForm',
                                     'CategoryForm',
                                     'StockRecordForm',
                                     'StockAlertSearchForm',
                                     'ProductCategoryFormSet',
                                     'ProductImageFormSet',
                                     'ProductRecommendationFormSet'))
Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')
ProductImage = get_model('catalogue', 'ProductImage')
ProductCategory = get_model('catalogue', 'ProductCategory')
ProductClass = get_model('catalogue', 'ProductClass')
StockRecord = get_model('partner', 'StockRecord')
StockAlert = get_model('partner', 'StockAlert')
Partner = get_model('partner', 'Partner')


class ProductListView(generic.ListView):
    template_name = 'dashboard/catalogue/product_list.html'
    model = Product
    context_object_name = 'products'
    form_class = ProductSearchForm
    description_template = _(u'Products %(upc_filter)s %(title_filter)s')
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super(ProductListView, self).get_context_data(**kwargs)
        ctx['product_classes'] = ProductClass.objects.all()
        ctx['form'] = self.form
        ctx['queryset_description'] = self.description
        return ctx

    def get_queryset_for_user(self, user):
        if user.is_staff:
            return self.model._default_manager.all()
        else:
            return self.model._default_manager.filter(
                stockrecord__partner__users__pk=user.pk)

    def get_queryset(self):
        """
        Build the queryset for this list and also update the title that
        describes the queryset
        """
        description_ctx = {'upc_filter': '',
                           'title_filter': ''}
        queryset = self.get_queryset_for_user(self.request.user)
        queryset = queryset.order_by('-date_created').prefetch_related(
            'product_class', 'stockrecord__partner')
        self.form = self.form_class(self.request.GET)
        if not self.form.is_valid():
            self.description = self.description_template % description_ctx
            return queryset

        data = self.form.cleaned_data

        if data['upc']:
            queryset = queryset.filter(upc=data['upc'])
            description_ctx['upc_filter'] = _(
                " including an item with UPC '%s'") % data['upc']

        if data['title']:
            queryset = queryset.filter(
                title__icontains=data['title']).distinct()
            description_ctx['title_filter'] = _(
                " including an item with title matching '%s'") % data['title']

        self.description = self.description_template % description_ctx
        return queryset


class ProductCreateRedirectView(generic.RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        product_class_id = self.request.GET.get('product_class', None)
        if not product_class_id or not product_class_id.isdigit():
            messages.error(self.request, _("Please choose a product class"))
            return reverse('dashboard:catalogue-product-list')
        try:
            product_class = ProductClass.objects.get(id=product_class_id)
        except ProductClass.DoesNotExist:
            messages.error(self.request, _("Please choose a product class"))
            return reverse('dashboard:catalogue-product-list')
        else:
            return reverse('dashboard:catalogue-product-create',
                           kwargs={'product_class_id': product_class.id})


class ProductCreateUpdateView(generic.UpdateView):
    template_name = 'dashboard/catalogue/product_update.html'
    model = Product
    context_object_name = 'product'

    form_class = ProductForm
    category_formset = ProductCategoryFormSet
    image_formset = ProductImageFormSet
    ##recommendations_formset = ProductRecommendationFormSet
    stockrecord_form = StockRecordForm



    def get(self, request, *args, **kwargs):

        ## don't let staff create new items right now
        user = self.request.user

        self.creating = not 'pk' in self.kwargs
        if self.creating:
            if self.request.user.is_staff:
                messages.error(self.request,
                           _("Currently admin users are not allowed to create items"))
                return HttpResponseRedirect(reverse('catalogue:index'))


        if not self.creating:
            self.object = product = self.get_object()
            partner = product.stockrecord.partner
            owner = partner.user

            if self.request.user != owner and not self.request.user.is_staff:
                return HttpResponseRedirect(reverse('catalogue:index'))

        return super(ProductCreateUpdateView, self).get(request, *args, **kwargs)


    def get_object(self, queryset=None):
        """
        This parts allows generic.UpdateView to handle creating products as
        well. The only distinction between an UpdateView and a CreateView
        is that self.object is None. We emulate this behavior.
        Additionally, self.product_class is set.
        """

        user = self.request.user
        self.require_user_stockrecord = not user.is_staff
        self.creating = not 'pk' in self.kwargs
        if self.creating:

            try:
                product_class_id = self.kwargs.get('product_class_id', None)
                self.product_class = ProductClass.objects.get(
                    id=product_class_id)
            except ObjectDoesNotExist:
                raise Http404
            else:
                return None  # success
        else:
            obj = super(ProductCreateUpdateView, self).get_object(queryset)
            self.product_class = obj.product_class
            return obj

    def boothIsApproved(self):
        p =  self.object ##ctx['product']
        try:
            partner = p.stockrecord.partner
            if partner.status == 1:
                return True
            else:
                return False
        except:
            return False

    def paymentsEnabled(self):
        p =  self.object ##ctx['product']
        #u = p.stockrecord.partner.user

        if self.request.user.is_staff:
            return True
        partner = self.request.user.partner
        #from apps.homemade.homeMade import getSellerFromOscarID
        #muser = getSellerFromOscarID(u.id)
        acceptsPayments = False
        #if muser.stripeSellerToken and muser.stripeSellerPubKey:
        if partner.stripeToken and partner.stripePubKey:
            acceptsPayments = True

        return acceptsPayments


    def getSelfShipCost(self):
        p = self.object

        if not p.stockrecord.shipping_options:
            return None
        soptsDict = json.loads(p.stockrecord.shipping_options)
        if soptsDict:
            if soptsDict.has_key('self_ship_cost'):
                self_ship_cost = soptsDict['self_ship_cost']
                return self_ship_cost

        return None


    def get_context_data(self, **kwargs):

        ctx = super(ProductCreateUpdateView, self).get_context_data(**kwargs)
        if 'stockrecord_form' not in ctx:
            ctx['stockrecord_form'] = self.get_stockrecord_form()
        if 'category_formset' not in ctx:
            ctx['category_formset'] = self.category_formset(instance=self.object)
        if 'image_formset' not in ctx:
            ctx['image_formset'] = self.image_formset(instance=self.object) #, minimum_forms=1, minimum_forms_message="At least one image is needed for this item.")
        #if 'recommended_formset' not in ctx:
        #    ctx['recommended_formset'] = self.recommendations_formset(instance=self.object)
        if self.object is None:
            ctx['title'] = _('New item') ## % self.product_class.name
            ctx['scoreVal'] = None
        else:
            ctx['title'] = ctx['product'].get_title()
            ctx['scoreVal'] = self.object.score


        ## whether the seller/partner can take payments, and therefore ship

        ctx['payments_enabled'] = self.paymentsEnabled()

        if not self.creating:
            p = self.object
            partner = p.stockrecord.partner
        else:
            partner = self.request.user.partner

        if not self.creating:
            if p.stockrecord.shipping_options:
                soptsDict = json.loads(p.stockrecord.shipping_options)
                if soptsDict:

                    ctx['self_ship_cost'] = soptsDict.get('self_ship_cost')
                    #if ctx['self_ship_cost'] == None:
                    #    ctx['self_ship_cost'] = ''

                    ctx['self_ship'] = soptsDict.get('self_ship')
                    ctx['calculate_ship'] = soptsDict.get('calculate_ship')

                    ctx['printLabel'] = soptsDict.get('printLabel')

                    ctx['PMSmall_num'] = soptsDict.get('PMSmall_num')
                    ctx['PMMedium_num'] = soptsDict.get('PMMedium_num')
                    ctx['PMLarge_num'] = soptsDict.get('PMLarge_num')

                    ctx['PMSmall_used'] = soptsDict.get('PMSmall_used')
                    ctx['PMMedium_used'] = soptsDict.get('PMMedium_used')
                    ctx['PMLarge_used'] = soptsDict.get('PMLarge_used')

                    ctx['first_used'] = soptsDict.get('first_used')
                    ctx['parcel_select_used'] = soptsDict.get('parcel_select_used')
                    ctx['max_per_box'] = soptsDict.get('max_per_box')


                    ctx['UPS_used'] = soptsDict.get('UPS_used')

                    ctx['local_delivery_used'] = soptsDict.get('local_delivery_used')


        ## get shipping preferences for the booth/seller
        if partner.shipping_options:
            soptsDict = json.loads(partner.shipping_options)
            if soptsDict:
                ctx['s_self_ship'] = soptsDict.get('self_ship')
                ctx['s_calculate_ship'] = soptsDict.get('calculate_ship')

                ctx['s_printLabel'] = soptsDict.get('printLabel')

                ctx['s_PMSmall_used'] = soptsDict.get('PMSmall_used')
                ctx['s_PMMedium_used'] = soptsDict.get('PMMedium_used')
                ctx['s_PMLarge_used'] = soptsDict.get('PMLarge_used')

                ctx['s_first_used'] = soptsDict.get('first_used')
                ctx['s_parcel_select_used'] = soptsDict.get('parcel_select_used')                

                ctx['s_UPS_used'] = soptsDict.get('UPS_used')

                ctx['s_local_pickup_used'] = soptsDict.get('local_pickup_used')
                if not soptsDict.get('local_pickup_used'):
                    p.stockrecord.local_pickup_enabled = False
                    p.stockrecord.save()
                    
                ctx['s_local_delivery_used'] = soptsDict.get('local_delivery_used')

        return ctx

    def get_form_kwargs(self):
        kwargs = super(ProductCreateUpdateView, self).get_form_kwargs()
        kwargs['product_class'] = self.product_class
        return kwargs

    def is_stockrecord_submitted(self):
        """
        Check if there's POST data that matches StockRecordForm field names
        """

        fields = dict(self.stockrecord_form.base_fields.items() +
                      self.stockrecord_form.declared_fields.items())
        for name, field in fields.iteritems():
            if len(self.request.POST.get(name, '')) > 0:
                return True
        return False

    def get_stockrecord_form(self):
        """
        Get the the ``StockRecordForm`` prepopulated with POST
        data if available. If the product in this view has a
        stock record it will be passed into the form as
        ``instance``.
        """
        form_kwargs = {'product_class': self.product_class, }
        try:
            form_kwargs['instance'] = self.object.stockrecord
        except (AttributeError, StockRecord.DoesNotExist):
            # either self.object is None, or no stockrecord
            form_kwargs['instance'] = None
        if self.request.method == 'POST':
            form_kwargs['data'] = self.request.POST
        form = self.stockrecord_form(**form_kwargs)
        if self.require_user_stockrecord:
            # only show partners that have current user in their users
            t = 9
            ## commented this out since partner not part of the form
            # partners = Partner._default_manager.filter(users__pk=
            #                                            self.request.user.pk)
            # if len(partners) == 0:  # len instead of .count() -> only one query
            #     raise ImproperlyConfigured("User can't set a valid stock record. Add her to at least one partner")
            # form.fields['partner'].queryset = partners
        return form

    def form_valid(self, form):
        return self.process_all_forms(form)

    def form_invalid(self, form):
        return self.process_all_forms(form)

    def process_all_forms(self, form):
        """
        Short-circuits the regular logic to have one place to have our
        logic to check all forms
        """
        # Need to create the product here because the inline forms need it
        # can't use commit=False because ProductForm does not support it


        if self.creating and form.is_valid():
            self.object = form.save()

        stockrecord_form = self.get_stockrecord_form()
        category_formset = self.category_formset(self.request.POST,
                                                 instance=self.object)
        image_formset = self.image_formset(self.request.POST,
                                           self.request.FILES,
                                           instance=self.object,
                                           #minimum_forms=1, minimum_forms_message="At least one image is needed for this item."
                                           )
        #recommended_formset = self.recommendations_formset(
        #    self.request.POST, self.request.FILES, instance=self.object)
        
        ## this is a big hack, save the stockrecord to keep shipping info if invalid
        ## Otherwise the instance is updated with new info, but doesn't keep the old info. Great....
        #import copy
        #stockrecordSaved = copy.deepcopy(self.object.stockrecord)
        is_valid = all([
            form.is_valid(),
            category_formset.is_valid(),
            image_formset.is_valid(),
            #recommended_formset.is_valid(),
            # enforce if self.require_user_stockrecord, skip if not submitted
            stockrecord_form.is_valid() or not self.require_user_stockrecord, ## and not self.is_stockrecord_submitted()),
                        ])

        if is_valid:
            return self.forms_valid(form, stockrecord_form, category_formset,
                                    image_formset) ## , recommended_formset)
        else:
            # delete the temporary product again
            if self.creating and form.is_valid():
                self.object.delete()
                self.object = None
            ##self.object.stockrecord = stockrecordSaved
            #image_formset.save()
            return self.forms_invalid(form, stockrecord_form, category_formset,
                                      image_formset) ##, recommended_formset)


    def createProductVariant(self):
        ''' Copy the current product '''
        from copy import copy

        ## copy product
        p = self.object
        vc = copy(p)
        vc.pk = None
        vc.parent = p
        vc.parent_id = p.id
        vc.save()

        ## copy stockrecord
        sr = p.stockrecord
        src = copy(sr) 
        src.product = vc
        src.product_id = vc.id
        src.pk = None
        src.save()

        ## set stockrecord to the copy
        vc.stockrecord = src

        ## did we miss anything?

        return vc

    def forms_valid(self, form, stockrecord_form, category_formset,
                    image_formset): ##, recommended_formset):
        """
        Save all changes and display a success url.
        """
        if not self.creating:
            # a just created product was already saved in process_all_forms()
            try:
                self.object = form.save()
            except:
                ## probably bad Haystack to index connection, if index is in the cloud
                ## not much I can do, 'cept update the index manually later
                pass

        try:
            if form.data.get('scoreVal'):
                self.object.score = form.data.get('scoreVal')
                self.object.save()
        except:
            pass

        if self.is_stockrecord_submitted():
            # Save stock record
            stockrecord = stockrecord_form.save(commit=False)
            stockrecord.product = self.object         
            stockrecord.save()
        elif self.creating:
            stockrecord = stockrecord_form.save(commit=False)
            stockrecord.product = self.object
            stockrecord.save()

        ## don't change partners once the item is created.
        if not self.object.stockrecord.partner and self.require_user_stockrecord:
            try:
                stockrecord.partner = self.request.user.partner

            except ObjectDoesNotExist:
                partner = Partner.objects.create(user=self.request.user, name=self.request.user.get_full_name())
                partner.save()    
                stockrecord.partner = self.request.user.partner

            stockrecord.save()
        ## don't delete since we want a partner

        #else:
        #    # delete it
        #    if self.object.has_stockrecord:


        #        self.object.stockrecord.delete()

        # Save formsets
        category_formset.save()
        image_formset.save()
        ##recommended_formset.save()


        ## if no pic, hide the item


        imageTest = self.object.primary_image()
        imageExists = True

        try:
            if imageTest.get("is_missing"):
                imageExists = False
        except:
            pass

        if not imageExists:
            self.object.status = "no_image_disabled"
            self.object.save()
            messages.info(self.request,    
                       _("No image was given for this item, so it will not yet be displayed on the market.  Please "
                         "add an image to enable buyers to see your products. "))
        elif self.object.status == "no_image_disabled":
            self.object.status = None
            self.object.save()

        ## custom form handling:

        if stockrecord.shipping_options:
            soptsDict = json.loads(stockrecord.shipping_options)
        else:
            ## this will always get called since the stockrecord is 'new'
            soptsDict = {}


        print self.request.POST

        if False:
            ## add shipping options to the stockrecord
            shipChoice = self.request.POST.get('shipChoice')
            soptsDict['shipChoice'] = self.request.POST.get("shipChoice")

            if shipChoice == "calculate_ship":
                soptsDict['calculate_ship'] = True
                soptsDict['self_ship'] = False

            ## priority mail
            soptsDict['PMMedium_num'] = self.request.POST.get("PMMedium_num")
            soptsDict['PMLarge_num'] = self.request.POST.get("PMLarge_num")
            soptsDict['PMSmall_num'] = self.request.POST.get("PMSmall_num")
        
            p = self.object

            if self.request.POST.get("PMSmall_toggle") == "on" and soptsDict.get("PMSmall_num"):
                soptsDict['PMSmall_used'] = True           
                p.stockrecord.is_shippable = True       

            if self.request.POST.get("PMMedium_toggle") == "on" and soptsDict.get("PMMedium_num"):
                soptsDict['PMMedium_used'] = True   
                p.stockrecord.is_shippable = True       
        
            if self.request.POST.get("PMLarge_toggle") == "on" and soptsDict.get("PMLarge_num"):
                soptsDict['PMLarge_used'] = True
                p.stockrecord.is_shippable = True       

            if self.request.POST.get("FirstClass_toggle") == "on":
                soptsDict['first_used'] = True  
                soptsDict['parcel_select_used'] = True  


            if self.request.POST.get("UPS_toggle") == "on":
                soptsDict['UPS_used'] = True  

            if self.request.POST.get("local_delivery_toggle") == "on":
                soptsDict['local_delivery_used'] = True  

            if shipChoice == "self_ship":
                soptsDict['calculate_ship'] = False
                soptsDict['self_ship'] = False ## in case no ship cost given

            if self.request.POST.has_key("self_ship_cost"):
                self_ship_cost = self.request.POST['self_ship_cost']
                ## add shipping options to the stockrecord
                if self_ship_cost != '' and self_ship_cost != None:
                    soptsDict['self_ship_cost'] = self_ship_cost
                    if shipChoice == "self_ship":
                        soptsDict['self_ship'] = True
                        stockrecord.is_shippable = True




            stockrecord.shipping_options = json.dumps(soptsDict)

            if (soptsDict.get('first_used') or soptsDict.get('parcel_select_used') or soptsDict.get('UPS_used') ) and stockrecord.weight > 0.0:
                stockrecord.is_shippable = True

            stockrecord.save()


        ## deal with variants
        if self.request.POST.has_key("variant_info"):
            variant_json = self.request.POST['variant_info']
            vc = self.createProductVariant()
            vc.title = vc.title + "_1"
            print "Creating a variant, " + vc.title
            vc.save()


        ## check if store has payments enabled. If not, disable the item
        #try:
        #if not self.paymentsEnabled() or not self.boothIsApproved:
        #    self.object.status = "disabled_" + str(self.object.status)
        #    self.object.save()
        #except:
        #    pass

        #if self.instance.is_top_level and self.get_num_categories() == 0:
        #    default_category = Category.objects.filter(name="Other")
        #    self.categories.add(default_category)

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, stockrecord_form, category_formset,
                      image_formset): ##, recommended_formset):
        
        messages.error(self.request,
                       _("There is more information needed to create the item -- please "
                         "see below to add to or correct the form. "))
        
        ctx = self.get_context_data(form=form,
                                    stockrecord_form=stockrecord_form,
                                    category_formset=category_formset,
                                    image_formset=image_formset) #,
                                    ##recommended_formset=recommended_formset)
        return self.render_to_response(ctx)

    def get_url_with_querystring(self, url):
        url_parts = [url]
        if self.request.GET.urlencode():
            url_parts += [self.request.GET.urlencode()]
        return "?".join(url_parts)

    def get_success_url(self):
        if self.creating:
            msg = _("Created product '%s'") % self.object.title
        else:
            msg = _("Updated product '%s'") % self.object.title
        messages.success(self.request, msg)
        #url = reverse('dashboard:catalogue-product-list')
        try:
            url = "/catalogue/?booth=" + str(self.object.stockrecord.partner.id)
        except:
            url = "/catalogue/"
        if self.request.POST.get('action') == 'continue' :
            url = reverse('dashboard:catalogue-product',
                          kwargs={"pk": self.object.id})
        return self.get_url_with_querystring(url)


class ProductDeleteView(generic.DeleteView):
    template_name = 'dashboard/catalogue/product_delete.html'
    model = Product
    context_object_name = 'product'

    def get_object(self, queryset=None):
        """
        Check permissions before returning product. The user having the
        catalogue.delete_product permission is enforced in dashboard's app.py
        """
        product = super(ProductDeleteView, self).get_object(queryset)
        user = self.request.user
        if user.is_staff or product.user_in_partner_users(user):
            return product
        else:
            raise PermissionDenied

    def get_success_url(self):
        msg =_("Deleted product '%s'") % self.object.title
        messages.success(self.request, msg)
        return reverse('dashboard:catalogue-product-list')


class StockAlertListView(generic.ListView):
    template_name = 'dashboard/catalogue/stockalert_list.html'
    model = StockAlert
    context_object_name = 'alerts'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        ctx = super(StockAlertListView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['description'] = self.description
        return ctx

    def get_queryset(self):
        if 'status' in self.request.GET:
            self.form = StockAlertSearchForm(self.request.GET)
            if self.form.is_valid():
                status = self.form.cleaned_data['status']
                self.description = _('Alerts with status "%s"') % status
                return self.model.objects.filter(status=status)
        else:
            self.description = _('All alerts')
            self.form = StockAlertSearchForm()
        return self.model.objects.all()


class CategoryListView(generic.TemplateView):
    template_name = 'dashboard/catalogue/category_list.html'

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryListView, self).get_context_data(*args, **kwargs)
        ctx['child_categories'] = Category.get_root_nodes()
        return ctx


class CategoryDetailListView(generic.DetailView):
    template_name = 'dashboard/catalogue/category_list.html'
    model = Category
    context_object_name = 'category'

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryDetailListView, self).get_context_data(*args, **kwargs)
        ctx['child_categories'] = self.object.get_children()
        ctx['ancestors'] = self.object.get_ancestors()
        return ctx


class CategoryListMixin(object):

    def get_success_url(self):
        parent = self.object.get_parent()
        if parent is None:
            return reverse("dashboard:catalogue-category-list")
        else:
            return reverse("dashboard:catalogue-category-detail-list",
                            args=(parent.pk,))


class CategoryCreateView(CategoryListMixin, generic.CreateView):
    template_name = 'dashboard/catalogue/category_form.html'
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super(CategoryCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Add a new category")
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category created successfully"))
        return super(CategoryCreateView, self).get_success_url()


class CategoryUpdateView(CategoryListMixin, generic.UpdateView):
    template_name = 'dashboard/catalogue/category_form.html'
    model = Category
    form_class = CategoryForm

    def get_context_data(self, **kwargs):
        ctx = super(CategoryUpdateView, self).get_context_data(**kwargs)
        ctx['title'] = _("Update category '%s'") % self.object.name
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category updated successfully"))
        return super(CategoryUpdateView, self).get_success_url()


class CategoryDeleteView(CategoryListMixin, generic.DeleteView):
    template_name = 'dashboard/catalogue/category_delete.html'
    model = Category

    def get_context_data(self, *args, **kwargs):
        ctx = super(CategoryDeleteView, self).get_context_data(*args, **kwargs)
        ctx['parent'] = self.object.get_parent()
        return ctx

    def get_success_url(self):
        messages.info(self.request, _("Category deleted successfully"))
        return super(CategoryDeleteView, self).get_success_url()
