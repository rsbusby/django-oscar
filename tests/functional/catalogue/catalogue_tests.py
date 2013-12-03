import httplib

from django.core.urlresolvers import reverse
from oscar.apps.catalogue.models import Category, ProductAttribute
from oscar.test.testcases import WebTestCase

from oscar.test.factories import create_product
from oscar.apps.catalogue.views import ProductListView

## mine
from django.db.models import get_model
from django.test.client import Client
from django.template import Template, Context
from django_dynamic_fixture import get, G
from django.test import LiveServerTestCase

from oscar.test.testcases import ClientTestCase, WebTestCase
from oscar.test.factories import create_order, create_product
from oscar.apps.order.models import Order, OrderNote, ShippingAddress, SponsoredOrganization
from oscar.core.compat import get_user_model
from oscar.apps.address.models import Country

from selenium import webdriver

User = get_user_model()
Basket = get_model('basket', 'Basket')
Partner = get_model('partner', 'Partner')
ShippingAddress = get_model('order', 'ShippingAddress')
SponsoredOrganization = get_model('order', 'SponsoredOrganization')
ProductAttribute = get_model('catalogue', 'ProductAttribute')


from apps.homemade.urls import urlpatterns




import urls

def show_urls(urllist, depth=0):
  for entry in urllist:
    print "  " * depth, entry.regex.pattern
    if hasattr(entry, 'url_patterns'):
        show_urls(entry.url_patterns, depth + 1)

def ff(browser, fid, val):
    ''' fill in form with Selenium'''
    form_element = browser.find_element_by_id(fid)
    form_element.send_keys(val)

class TestProductStuff(WebTestCase, ClientTestCase):
    username = 'customer'
    password = 'cheeseshop'
    email = 'customer@example.com'

    def setUp(self):

        self.client = Client()
        self.user1 = self.create_user(username='user1@example.com')
        self.user2 = self.create_user(username='user2@example.com')
        self.partner1 = G(Partner, users=[self.user1])
        self.partner2 = G(Partner, users=[self.user2])
        self.product1 = create_product(partner=self.partner1)
        self.product2 = create_product(partner=self.partner2)
        self.basket1 = Basket.objects.create()
        self.basket2 = Basket.objects.create()
        self.basket12 = Basket.objects.create()
        self.basket1.add_product(self.product1)
        self.basket2.add_product(self.product2)
        self.basket12.add_product(self.product1)
        self.basket12.add_product(self.product2)
        self.address = G(ShippingAddress)
        #self.order1 = create_order(basket=self.basket1,
        #                           shipping_address=self.address)
        #self.order2 = create_order(basket=self.basket2,
        #                           shipping_address=self.address)
        self.order12 = create_order(basket=self.basket12,
                                    shipping_address=self.address)

    def test_add_and_delete_from_basket(self):


        self.client.login(username=self.user1.username, password=self.password)
        url = reverse('basket:summary')
        response = self.client.get(url)
        self.assertContains(response, "Continue shopping")
        
        #self.basket2.owner = self.user1
        #self.basket2.save()

        b = Basket.objects.filter(owner=self.user1, status="Open").order_by('-id')[0]

        ## basket no item
        b.add_product(self.product2)
        b.save()

        page = self.client.get(url)
        #print page
        self.assertNotContains(page, "Continue shopping")

        ## now test deletion

        #b.
        response = self.client.post('/basket/list/', {'basket_id':b.id, 'line_id':b.lines.all()[0].id, 'remove-line':True})

        page = self.client.get(url)
        #print page
        self.assertContains(page, "Continue shopping")


    def test_hide_disabled_items(self):


        ## make an item
        p = create_product(title="notUniqueEnuf")

        ## is it in the browse
        r = self.app.get(reverse('catalogue:index'))
        self.assertContains(r,p.title)

        ## in the booth ?
        url = reverse('catalogue:index') + "?booth=" + p.stockrecord.partner.name
        r = self.app.get(url)
        self.assertContains(r,p.title)

        ## able to access detail
        kwargs = {'product_slug': p.slug,
                  'pk': p.id}
        url = reverse('catalogue:detail', kwargs=kwargs)
        r = self.app.get(url)
        self.assertContains(r,p.title)

        ## make it disabled
        p.status = "admin_disabled"
        p.save()


        ## is it in the browse
        r = self.app.get(reverse('catalogue:index'))
        self.assertNotContains(r,p.title)

        ## in the booth ?
        url = reverse('catalogue:index') + "?booth=" + p.stockrecord.partner.name
        r = self.app.get(url)
        self.assertNotContains(r,p.title)

        ## able to access detail? should be 302 error
        kwargs = {'product_slug': p.slug,
                  'pk': p.id}
        url = reverse('catalogue:detail', kwargs=kwargs)
        r = self.app.get(url)
        self.assertEquals(302, r.status_code)


    def test_contact_us_has_app_name(self):

        ##make a staff user
        self.user2.is_staff = True
        self.user2.save()

        right_url = reverse('contactUs')

        #print reverse('promotions:home')

        #self.is_staff = True
        self.login()

        page = self.app.get(right_url)
        #print type(right_url)
        #page = self.app.get(reverse('catalogue:index') + p.slug +"_" + str(p.id)+"/")
        #print page
        #print p.title
        self.assertContains(page, "Homemade 1616")
        ## need to be logged in for this
        #self.assertContains(page, "Add to basket")


    def test_shows_add_to_basket_button_for_available_product(self):
        p = create_product()

        kwargs = {'product_slug': p.slug,
                  'pk': p.id}
        right_url = reverse('catalogue:detail', kwargs=kwargs)

        page = self.app.get(right_url)
        print type(right_url)
        print "TYPE"
        #page = self.app.get(reverse('catalogue:index') + p.slug +"_" + str(p.id)+"/")
        #print page
        #print p.title
        self.assertContains(page, p.title)
        ## need to be logged in for this
        #self.assertContains(page, "Add to basket")


#class TestBoothStuff(WebTestCase):

    def test_shows_add_to_basket_button_for_available_products_in_booth(self):
        p = create_product()
        self.is_staff = True
        print "start"
        #print self.login()

        url = reverse('catalogue:index') + "?booth=" + p.stockrecord.partner.name
        url = "/catalogue/?booth=Dummy partner"
        page = self.app.get(url)
        #print page
        #print p.title
        print url
        #print self.product1.id
        self.assertContains(page, p.title)

        ## logged in
        #self.assertContains(page, "Add to basket")


    def test_shows_edit_button_in_booth_when_logged_in(self):
        p = create_product()
        self.is_staff = True
        print "start"
        self.login()

        url = reverse('catalogue:index') + "?booth=" + p.stockrecord.partner.name
        page = self.get(url)
        #print page
        #print p.title
        print url
        #print self.product1.id
        self.assertContains(page, p.title)

        ## logged in
        self.assertContains(page, "Edit this Booth")



    # def test_shows_weight_in_edit_item(self):
    #     #p = create_product()
    #     #p.stockrecord.partner = self.partner2
    #     #p.stockrecord.partner.user = self.user2
    #     #p.save()
    #     #p.stockrecord.save()
    #     #self.partner2.save()

    #     p = self.product1
    #     self.client.login(username=self.user1.username, password=self.password)

    #     self.user1.partner = self.partner1
    #     self.user1.is_staff = False
    #     self.user1.save()
    #     self.partner1.save()


    #     kwargs = {'pk': p.id}
    #     url = reverse('dashboard:catalogue-product', kwargs=kwargs)
    #     #print url
    #     #page = self.get(url)  
    #     page = self.app.get(url)

    #     #print page
    #     #print p.title
    #     print url
    #     #print self.product1.id
    #     #self.assertContains(page, p.title)

    #     ## logged in
    #     self.assertContains(page, "Price")
    #     #show_urls(urls.urlpatterns)

    #     self.user1.is_staff = False
    #     self.user1.save()


    def test_booth_ship_address_saved(self):

        ''' 
        make sure the shipping address is saved. This was a problem at one point
        '''
        ## make a country
        Country.objects.get_or_create(
            iso_3166_1_a2='US',
            is_shipping_country=True
        )

        ## make a user, log in
        #self.client.login()
        self.client.login(username=self.user1.username, password=self.password)

        self.user1.partner = self.partner1
        self.user1.save()
        self.partner1.save()

        ## make a booth/partner

        ## post to set the address.
        fd = {
        'first_name': "Bill",
        'last_name': "Smith",
        #'is_default_for_store': "True",
        'line1': "710 Hampton Dr",
        'line4': "Venice",
        'country':'US',
        'state': "CA",
        'postcode': "90291",
        'notes': "leave it anywhere",


        }

        ## waht happens if not logged in? Redirect

        response = self.client.post(reverse('customer:store-shipping-address'), fd)

        url = response.__getitem__("Location")
        self.failIf(url.count("booth") < 1)

        ## might be cool to test the form display, too?

        ## check that the user associated with that partner now has an address.
        self.failIf(len(self.user1.addresses.all()) < 1)        


class TestHolisticStuff(LiveServerTestCase, WebTestCase, ClientTestCase):

    username = 'customer'
    password = 'cheeseshop'
    email = 'customer@example.com'


    def setUp(self):

        #from apps.homemade.homeMade import *
        #for s in Seller.objects.all(): s.delete()

        #self.client = Client()
        self.user1 = self.create_user(username='user1@example.com')
        self.user2 = self.create_user(username='user2@example.com')
        self.user1.email = self.user1.username
        self.user2.email = self.user2.username        
        self.user1.save()
        self.user2.save()        
        self.partner1 = G(Partner, users=[self.user1])
        self.partner2 = G(Partner, users=[self.user2])
        self.product1 = create_product(partner=self.partner1)
        self.product2 = create_product(partner=self.partner2, attributes={'weight':1.0})

        ## make a country, this will act as default
        Country.objects.get_or_create(
            iso_3166_1_a2='US',
            is_shipping_country=True
        )

        self.browser = None ## webdriver.Firefox()

    def go(self, url, browser = None):
        if not browser:
            browser= self.browser
        surl = self.live_server_url + url
        browser.get(surl)


    def loginUser(self, user = None, browser=None):

        if not browser:
            browser=self.browser
        if not user:
            user = self.user1

        self.go("/accounts/login/", browser)

        #elem = browser.find_element_by_class_name('icon-signin')
        #elem.click()

        ## fill in login form
        lin = browser.find_element_by_id('id_login-username')
        lin.send_keys(user.email)
        lpw = browser.find_element_by_id('id_login-password')
        lpw.send_keys(self.password) 
        browser.find_element_by_name("login_submit").click()

    def test_ship_address_sel(self):
        ''' 
        make sure the shipping address is saved. This was a problem at one point
        '''

        browser = webdriver.Firefox()
        #browser.get('http://seleniumhq.org/')

        from selenium.webdriver.common.keys import Keys
        #browser.get('http://')
        url = reverse('catalogue:index')
        surl = self.live_server_url + url
        browser.get(surl)


    


        ## make a user, log in via Selenium

        elem = browser.find_element_by_class_name('icon-signin')
        elem.click()

        ## fill in login form
        lin = browser.find_element_by_id('id_login-username')
        lin.send_keys(self.user1.username)
        lpw = browser.find_element_by_id('id_login-password')
        lpw.send_keys(self.password)  


        browser.find_element_by_name("login_submit").click()
        #lf = browser.find_element_by_id('login_form')
        #lf.submit()

        ## make a booth/partner
        self.user1.partner = self.partner1
        self.user1.save()
        self.partner1.save()

        ## go to the booth page
        url = reverse('catalogue:index') + "?booth=" + self.partner1.name
        surl = self.live_server_url + url
        browser.get(surl)

        ## go to ship address form
        browser.find_element_by_class_name("orgButton").click()

        b = browser

        ff(b, 'id_first_name', 'Bob')
        ff(b, 'id_last_name', 'Bob')
        ff(b, 'id_line1', '710 Hampton Dr')                
        ff(b, 'id_line4', 'Venice') 
        ##ff(b, 'id_country', 'US')                                               
        ff(b, 'id_state', 'CA')  
        ff(b, 'id_postcode', '90291')

        browser.find_element_by_id("store-ship-new-submit").click()

        ## check that alert is there

        ## go to addresses page, check that the new address is there and has default ship address

        ## waht happens if not logged in? Redirect

        #response = self.client.post(reverse('customer:store-shipping-address'), fd)

        #url = response.__getitem__("Location")
        #self.failIf(url.count("booth") < 1)

        ## might be cool to test the form display, too?

        ## check that the user associated with that partner now has an address.
        self.failIf(len(self.user1.addresses.all()) < 1)        

        self.failIf(self.user1.addresses.all()[0].is_default_for_store != True)        

        browser.quit()



    def test_sent_email_display(self):

        ''' send msg from one user to another and check that the sent msges display'''

        browser = webdriver.Firefox()
        self.browser = browser

        ## --- send msg from user1 to user2
        ## login as user1
        self.loginUser(user=self.user1, browser=browser)

        ## make sure user2 has a boo        ## make a booth/partner
        #self.user2.partner = self.partner2
        #self.user2.save()
        #self.partner2.save()

        ## go to the booth page
        #url = reverse('catalogue:index') + "?booth=" + self.partner1.name
        #surl = self.live_server_url + url
        #browser.get(surl)

        ## go to contact page
        #browser.find_element_by_class_name("orgButton").click()th 

        ## go to contact user2 page
        url = "/homemade/contact/" + "?store_name=" + self.partner2.name
        surl = self.live_server_url + url
        browser.get(surl)

        ## ensure that the correct name is there

        ## fill out form with something

        ta = browser.find_element_by_tag_name("textarea")
        ta.send_keys("this is a test message ")


        ## submit form
        browser.find_element_by_id("msg-submit").click()

        ## go to sent emails page
        url = "/accounts/emails/?sent=True"
        surl = self.live_server_url + url
        pg = browser.get(surl)

        ## ensure that sent email is there
        self.failIf(browser.page_source.count("Message from a cust") < 1)


        ## check other list view
        self.go("/accounts/")
        self.failIf(browser.page_source.count("Message from a cust") < 1)

        ## check that able to reply

        ## log out and log in as user2

        ## check that received msg is there

        ## ok done
        browser.quit()



    def test_open_booth(self):

        ''' send msg from one user to another and check that the sent msges display'''

        browser = webdriver.Firefox()
        self.browser = browser

        user3 = User.objects.create_user(username="user3",
                                         email="rsbusby+234234@gmail.com", password=self.password)

        ## --- send msg from user1 to user2
        ## make a new user
        #user3 = self.create_user(username='rsbusby+34534@gmail.com')


        self.loginUser(user3, browser)


        ## go to open booth page
        browser.find_element_by_id
        elem = browser.find_element_by_id('open-booth')
        elem.click()

        ## fill out form
        b = browser

        ff(b, 'store_name', 'Test Store2')
        ff(b, 'zipcode', "90291")
        #ff(b, 'filter', "Los Angeles")


        from apps.homemade.homeMade import *
        county = Counties(county = "Kern", state="CA")
        county.save()


        from selenium.webdriver.common.keys import Keys

        bcc = browser.find_element_by_class_name("select2-choice")
        bcc.click()
        bb = browser.find_element_by_class_name('select2-input')
        bb.send_keys("Kern")
        bb.send_keys(Keys.RETURN)

        ## upload pic
        #browser.find_element_by_id("IdOfInputTypeFile").send_keys(os.getcwd()+"/image.png")

        elem = browser.find_element_by_id('submit-booth').click()

        ##

        browser.find_element_by_id('skip-stripe').click()        


        ## now can deal with the address form!



        ## ok done

        ## test the edit form
        self.go(reverse('register_store'), browser)
        elem = browser.find_element_by_id('submit-booth').click()



        ## test the add item form
        ## go to the booth page
        url = reverse('catalogue:index')# + "?booth=" + user3.partner.name
        print url
        self.go(url)

        url = reverse('catalogue:index') + "?booth=" + user3.partner.name
        print url
        self.go(url)

        browser.find_element_by_id('addNewItemButton').click()

        ## should be on new item page now
        #self.failIf(browser.page_source.count("Weight") < 1)
        self.failIf(browser.page_source.count("shipping options") < 1)        
        self.failIf(browser.page_source.count("Price") < 1)



        #surl = self.live_server_url + url
        #print surl
        #browser.get(surl)

        ## clean up Mongo seller?
        user3.delete()



        browser.quit()




    def test_checkout(self):
        ''' test checkoiut and shipping options for an item'''

        browser = webdriver.Firefox()
        self.browser = browser



        ## give user2 an address, needed for shipping

        self.loginUser(self.user2, browser)


        ## make a booth/partner
        self.user2.partner = self.partner2
        self.user2.save()
        self.partner2.save()


        ## go to the booth page
        url = reverse('catalogue:index') + "?booth=" + self.partner2.name
        surl = self.live_server_url + url
        browser.get(surl)

        ## go to ship address form
        browser.find_element_by_class_name("orgButton").click()

        b = browser

        ff(b, 'id_first_name', 'Bob')
        ff(b, 'id_last_name', 'number2')
        ff(b, 'id_line1', '708 Hampton Dr')                
        ff(b, 'id_line4', 'Venice') 
        ##ff(b, 'id_country', 'US')                                               
        ff(b, 'id_state', 'CA')  
        ff(b, 'id_postcode', '90291')

        browser.find_element_by_id("store-ship-new-submit").click()


        ## set user2 to accept remote payments

        from apps.homemade.homeMade import getSellerFromOscarID
        seller = getSellerFromOscarID(self.user2.id)

        seller.stripeSellerToken = "fkae_token"
        seller.stripeSellerPubKey = "fake_key"
        seller.save()


        ## logout user2
        self.go(reverse('customer:logout'))

        ## login
        user3 = User.objects.create_user(username="user3",
                                         email="rsbusby+234234@gmail.com", password=self.password)

        self.loginUser(user3, browser)


        ## add address

        ## go to address page 
        url = "/accounts/addresses/add/"
        self.go(url)

        ## fill out form

        b = browser

        ff(b, 'id_first_name', 'Bob')
        ff(b, 'id_last_name', 'Borders')
        ff(b, 'id_line1', '716 Hampton Dr')                
        ff(b, 'id_line4', 'Venice') 
        ##ff(b, 'id_country', 'US')                                               
        ff(b, 'id_state', 'CA')  
        ff(b, 'id_postcode', '90291')



        ## submit form
        b.find_element_by_id("save-address").click()

        ## add sponsored org
        sorg = SponsoredOrganization(name="Food Backwards", is_current=True)
        sorg.save()

        ## make an attribute
        #ProductAttribute(name="weight", code="weight", type="float", product_class=self.product2.product_class)

        ## give product a weight
        ## make sure product2 has a weight


        #setattr(self.product2.attr, 'weight', 5)
        #setattr(self.product2.attr, 'Weight', 7)        
       
        ## make sure product can be shipped, for now local pickup?



        self.product2.stockrecord.is_shippable = True 
        self.product2.stockrecord.local_pickup_enabled = True 


        self.product2.save()
        self.product2.stockrecord.save()

        ## add item to basket
        ## go to item page
        kwargs = {'product_slug': self.product2.slug,
                  'pk': self.product2.id}
        url = reverse('catalogue:detail', kwargs=kwargs)

        self.go(url)

        ## click add to basket

        b.find_element_by_class_name("addToBasket").click()

        ## go to basket, OK
        self.go(reverse('basket:summary'))

        ## click checkout
        b.find_element_by_class_name("go-to-checkout").click()

        ## choose an address
        b.find_element_by_class_name("ship-address").click()

        ## are shipping options there

        ## choose shipping option
        b.find_element_by_class_name("select-shipping").click()



        ## choose sponsored org
        b.find_element_by_class_name("orgButton").click()




        ## choose payment method
        b.find_element_by_id("choose-stripe").click()

        ## preview looks OK?

        ## pay with card ?? (this probably won't work)

        ## tear down

        ## clean up Mongo seller?
        user3.delete()

        browser.quit()




    def tearDown(self):

        from apps.homemade.homeMade import *
        print "YOYOYOYOYO"
        #for s in Seller.objects.all(): s.delete()
        return


##/dashboard/catalogue/products/132/


class TestProductDetailView(WebTestCase):

    def test_enforces_canonical_url(self):
        p = create_product()
        kwargs = {'product_slug': '1_wrong-but-valid-slug_1',
                  'pk': p.id}
        wrong_url = reverse('catalogue:detail', kwargs=kwargs)

        response = self.app.get(wrong_url)
        self.assertEquals(httplib.MOVED_PERMANENTLY, response.status_code)
        self.assertTrue(p.get_absolute_url() in response.location)

    def test_variant_to_parent_redirect(self):
        parent_product = create_product()
        kwargs = {'product_slug': parent_product.slug,
                  'pk': parent_product.id}
        parent_product_url = reverse('catalogue:detail', kwargs=kwargs)

        variant = create_product(title="Variant 1", parent=parent_product)
        kwargs = {'product_slug': variant.slug,
                  'pk': variant.id}
        variant_url = reverse('catalogue:detail', kwargs=kwargs)

        response = self.app.get(parent_product_url)
        self.assertEquals(httplib.OK, response.status_code)

        response = self.app.get(variant_url)
        self.assertEquals(httplib.MOVED_PERMANENTLY, response.status_code)


class TestProductListView(WebTestCase):

    def dtest_shows_add_to_basket_button_for_available_product(self):
        product = create_product()

        page = self.app.get(reverse('catalogue:index'))
        print page
        print product.title
        self.assertContains(page, product.title)
        self.assertContains(page, "Add to basket")

    def dtest_shows_not_available_for_out_of_stock_product(self):
        product = create_product(num_in_stock=0)

        page = self.app.get(reverse('catalogue:index'))

        self.assertContains(page, product.title)
        self.assertContains(page, "Not available")

    def test_shows_pagination_navigation_for_multiple_pages(self):
        per_page = ProductListView.paginate_by
        title = u"Product #%d"
        for idx in range(0, int(1.5 * per_page)):
            create_product(title=title % idx)

        page = self.app.get(reverse('catalogue:index'))

        self.assertContains(page, "Page 1 of 2")


class TestProductCategoryView(WebTestCase):

    def setUp(self):
        self.category = Category.add_root(name="Products")

    def test_browsing_works(self):
        correct_url = self.category.get_absolute_url()
        response = self.app.get(correct_url)
        self.assertEquals(httplib.OK, response.status_code)

    def test_enforces_canonical_url(self):
        kwargs = {'category_slug': '1_wrong-but-valid-slug_1',
                  'pk': self.category.pk}
        wrong_url = reverse('catalogue:category', kwargs=kwargs)

        response = self.app.get(wrong_url)
        self.assertEquals(httplib.MOVED_PERMANENTLY, response.status_code)
        self.assertTrue(self.category.get_absolute_url() in response.location)
