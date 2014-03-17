import os
import random

## can incorporate into Django app
STAND_ALONE=False

from flask import Flask, render_template, jsonify, request, url_for, g, flash, redirect, session, send_file, send_from_directory, json, Markup
from werkzeug import check_password_hash, generate_password_hash, secure_filename

if STAND_ALONE:
    from flask.ext.mongoengine import MongoEngine

if not STAND_ALONE:
    from django.shortcuts import render_to_response, render, redirect


from mongoengine import *
from wand.image import Image

import os
import smtplib
from collections import OrderedDict

from math import floor

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


## needed for some specific queries, mongoengine used for the rest
import pymongo

## static files hosted by AWS S3
from flask_s3 import FlaskS3


import datetime, time
import stripe
from mandrill import Mandrill


#from pyzipcode import ZipCodeDatabase


from rauth.service import OAuth2Service

DEBUG = True

testVar = 9

app = Flask(__name__)
app.config.from_object(__name__)

app.config.from_envvar('HOMEMADE_SETTINGS', silent=True)


# rauth OAuth 2.0 service wrapper
# graph_url = 'https://graph.facebook.com/'
# facebook = OAuth2Service(name='facebook',
#                          authorize_url='https://www.facebook.com/dialog/oauth',
#                          access_token_url=graph_url + 'oauth/access_token',
#                          client_id=app.config['FB_CLIENT_ID'],
#                          client_secret=app.config['FB_CLIENT_SECRET'],
#                          base_url=graph_url)



stripe_keys = {
    'secret_key': os.environ['STRIPE_SECRET_KEY'],
    'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY']
}
 
app.config['stripe_client_id']=os.environ['STRIPE_CLIENT_ID']


## Flask-S3 config

s3 = FlaskS3(app)

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(PROJECT_ROOT,'static/uploads')
app.config['STATIC_FOLDER'] = os.path.join(PROJECT_ROOT,'static')
app.config['UPLOAD_RELATIVE_FOLDER'] = 'uploads'
app.config['STATIC_RELATIVE_FOLDER'] = 'static'

if not os.uname()[1].count('buzzy') and  not os.uname()[1].count('skuzzy') :
    print("Assuming on Heroku. Using remote database.")

    if os.environ['STRIPE_IS_LIVE'] == "1":
        print("ATTN: Using Stripe live account")

        stripe_keys = {
        'secret_key': os.environ['STRIPE_SK_LIVE'],
        'publishable_key': os.environ['STRIPE_PK_LIVE']
        }
        app.config['stripe_client_id']=os.environ['STRIPE_CLIENT_ID_LIVE']
    else:
        print("Using test account for Stripe")

    app.config['ADMIN_USERNAME'] = 'rb_admin'
    
    app.config['DEBUG'] =  os.environ['DEBUG']#False
    app.config['USE_S3_DEBUG'] = True

    app.config["HEROKU"] = True
    #app.config['SITE_URL'] = "https://nara-5692.herokussl.com"

else:
    print("Assuming local, not Heroku")
  

    app.config['ADMIN_USERNAME'] = 'rb_admin'
    app.config['UPLOAD_FOLDER'] = '/Users/busby/projects/flaskWeb/homeMade/static/uploads'
    app.config['STATIC_FOLDER'] = os.path.join(PROJECT_ROOT,'static')

    print("Using local database.")
    app.config['DEBUG'] = True
    app.config["HEROKU"] = False

    if app.config['DEBUG']:
        app.config['TRAP_BAD_REQUEST_ERRORS'] = True

    #app.config['USE_S3_DEBUG'] = True
    
    #app.config['SITE_URL'] = 'http://localhost:5000'


stripe.api_key = stripe_keys['secret_key']
stripeAuth = OAuth2Service(name='stripe',
                         authorize_url='https://connect.stripe.com/oauth/authorize',
                         access_token_url='https://connect.stripe.com/oauth/token' ,
                         client_id=app.config['stripe_client_id'],
                         client_secret=stripe.api_key,
                         base_url='https://connect.stripe.com/oauth')

##app.config["SECRET_KEY"] = os.environ['SECRET_KEY']


if STAND_ALONE:
    db = MongoEngine(app)

    def renderFO(req, template, **kwargs):
        return render_template(template, kwargs)

    def wrapForDjangoIfNeeded(fn):
        def new(*args):
            return fn(*args)
        return new

    def my_decorator(fn):
        def new(*args):
            return fn(*args)
        return new


if not STAND_ALONE:


    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    from django.conf import settings
    from django.contrib import messages


    from django.http import HttpResponse, HttpResponseRedirect
    from django.core.urlresolvers import reverse
    from django.template import RequestContext, Context, loader
    import inspect
    import django
    from django.contrib.sites.models import get_current_site

    from oscar.apps.partner.models import Partner
    from oscar.apps.order.models import Order as OscarOrder
    from oscar.apps.order.models import Line as OrderLine

    from django.contrib.auth.models import User

    from oscar.core.loading import get_class, get_profile_class, get_classes
    from django.db.models import get_model

    UserAddress = get_model('address', 'UserAddress')
 



    from functools import wraps

    app.config['UPLOAD_FOLDER'] = settings.MEDIA_ROOT
    app.config['STATIC_FOLDER'] = settings.STATIC_ROOT
    app.config['UPLOAD_RELATIVE_FOLDER'] = ''
    app.config['STATIC_RELATIVE_FOLDER'] = ''


    def prepareOscarVars(*args):
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        g = request

        u = getSellerFromOscarID(request.user.id)


    def my_decorator(view_func):
        def _decorator(request, *args, **kwargs):
            # maybe do something before the view_func call
            response = view_func(request, *args, **kwargs)
            # maybe do something after the view_func call
            return response
        return wraps(view_func)(_decorator)


    # def url_for(*args, **kwargs):
    #     print "in url_for"
    #     print args
    #     print kwargs
    #     return args[0], kwargs

    def url_for(func, **kwargs):

        url =  reverse(func)
        ignoreList = ['_external']
        for k in kwargs.keys():
            if k == "_external":
                cf = inspect.currentframe()
                pf = cf.f_back
                request=pf.f_locals['request']
                base = request.build_absolute_uri('/')[:-1]
                print "Base URL is " + base
                url = base + url
            else:
                url = url + "?" + str(k) + "=" + str(kwargs[k])
        print "Url is " + url
        return url

    def redirect(url):

        print "in redirect"
        print "Redirect URL is " + url

        return django.shortcuts.redirect(url)

    def wrapForDjangoIfNeeded(fn):
        def new(request, *args):
            ## can put this in a decorator?
            #cf = inspect.currentframe()
            #pf = cf.f_back
            #request=pf.f_locals['request']
            #request = args[0]
            request.args = request.POST
            request.form = request.POST
            g = request
            return fn(*args)
        return new

    class Protect(object):
        def __init__(self, *permissions):
            self.permissions = permissions
        def __call__(self, f):
            def inner(*args):
                print self.permissions[0]
                return f(*args)  
            return inner 


    # def msg_decorator(f):
    #     def inner_dec(*args, **kwargs):
    #         g = f.func_globals
    #         sentinel = object()

    #         oldvalue = g.get('request', sentinel)
    #         g['request'] = value

    #         try:
    #             res = f(*args, **kwargs)
    #         finally:
    #             if oldvalue is sentinel:
    #                 del g['request']
    #             else:
    #                 g['request'] = oldvalue

    #         return res
    #     return inner_dec

    # @msg_decorator()
    # def msg_printer():
    #     print request

    def getDjangoTemplateName(tn):
        return '.'.join(tn.split('.')[:-1]) + ".dj.html"

    def render_template(template, **kwargs):
        
        djTemplate = getDjangoTemplateName(template)
        t = loader.get_template(djTemplate)

        ## get the request object from the previous frame, awesome!!!
        cf = inspect.currentframe()
        prevFrame = cf.f_back
        request = prevFrame.f_locals['request']

        ## set up dictionary for template render
        td = kwargs
        ## emulate Flask global object  
        td['g'] = request
        c = RequestContext(request, td)
        return HttpResponse(t.render(c), content_type="text/html; charset=UTF-8")


## globals

blogPostList = []
categoryList = []

defaultCategoryGlobal = "Other"

app.config['S3_UPLOAD_DIR'] = os.environ['S3_UPLOAD_DIR']
app.config['logoPath']= app.config['S3_UPLOAD_DIR']  + app.config['UPLOAD_RELATIVE_FOLDER'] + '/' + "spoonLogoTemp.png"

app.config['PUBLISHABLE_KEY'] = os.environ['STRIPE_PUBLISHABLE_KEY']
app.config['SECRET_KEY'] = os.environ['STRIPE_SECRET_KEY']

#zcdb = ZipCodeDatabase()

siteName = "Homemade 1616" 

def getDateAsIdString(dateTimeObj):
    return dateTimeObj.strftime("%d%b%Y-%H%M%S-%f")

def getDollarsFromCents(priceCents):
        if priceCents < 10:
            priceStr = "0." + str(priceCents) 
        else:
            pStr = str(priceCents)
            priceStr = pStr[0:-2] + "." + pStr[-2:]

        return priceStr

class HMGeoData(DynamicDocument):
    zipcode = StringField()
    lat = StringField()
    long = StringField()
    town = StringField()
    stateFullName = StringField()
    state = StringField()
    locCoords = GeoPointField()


def getGeoData():

    geoNamesFile = "US.txt"
    HMGeoData.drop_collection()

    try:
        f = open(geoNamesFile, 'r')

        i = 0
        for line in f:
            i = i+1

            lsp = line.split('\t')

            if i < 12:
                print(i)

            zip = lsp[1]
            lat = lsp[-3]
            long = lsp[-2]



            gd = HMGeoData()
            gd.zipcode = lsp[1]
            gd.town = lsp[2]
            gd.stateFullName = lsp[3]
            gd.state = lsp[4]
            lat = lsp[-3]
            long = lsp[-2]
            gd.lat = lat
            gd.long = long
            gd.locCoords = [float(lat), float(long)]
            gd.save()
        print("Done with zipcode import")
    except:
        
        error =  "Import of zipcodes not happening dude."
        print(error)
        return error
    
    return None



class Counties(DynamicDocument):
    
    county = StringField(required=True)
    state = StringField(required=True)

class States(DynamicDocument):
    name = StringField(required=True)
    countyList = ListField(ObjectIdField)

class EmailInvites(DynamicDocument):
    seqId = SequenceField()
    email = StringField(required=True)

    
class Categories(DynamicDocument):
    seqId =SequenceField()
    displayOrderId = IntField()
    name = StringField(required=True)
    iconFileLink=StringField()
    iconFileHover=StringField()
    
    isPrimary = BooleanField()

    
    #
    # reset, then set categories

units = {'lb':'pound','g':'gram','dozen':'dozen'}



class SponsoredOrg(DynamicDocument):
    """Non-profit organizations to benefit from sales """
    seqId = SequenceField()
    name = StringField(required=True)
    description = StringField()
    about = StringField()
    totalDonated = IntField(required=True, default=0)

    def getTotalDonatedDollars(self):
        return getDollarsFromCents(self.totalDonated)
    
class Event(DynamicDocument):
    name = StringField(required = True)
    seqId = SequenceField()
    date = DateTimeField(required=True)    
    description = StringField(required = True)
    website = StringField()
    fbPage = StringField()



class Seller(DynamicDocument):
    """ Buyers and sellers. Users."""
    name = StringField(required = True)
    email = StringField(required=True)
    pw_hash = StringField(required=True)
    isAdmin = BooleanField(required=True, default=False)
    isBlogAdmin = BooleanField(required=True, default=False)

    # Oscar stuff
    oscarUserID = IntField()

    # Selling stuff
    permitType = StringField()
    permitPicPath =  StringField()
    storeExists = BooleanField(required=True, default=False)
    storeIsInactive = BooleanField()
    storeName =  StringField()
    storeDesc = StringField()
    storePicPath = StringField()
    itemIds = ListField(ObjectIdField()) ## list of item id's in store
    agreedToTerms = BooleanField(default=False)
    
    # Buying stuff
    openOrderIds = ListField(ObjectIdField())   ## id for current order, before checkout. 
    cartItems= ListField(StringField())  ## list of item ids
    orderHistoryIds = ListField(ObjectIdField())   ## list of orders. Can also query orders by user, ignoring any open

    # Stripe info for buying
    stripeAccountToken = StringField()
    stripeID = StringField()
    stripeHasCard = BooleanField(default=False)
    
    # Stripe info for selling
    stripeSellerPubKey = StringField()
    stripeSellerID = StringField()
    stripeSellerToken = StringField()
    
    # Other info
    personalName = StringField()
    bio =  StringField()
    personalPicPath = StringField()
    facebook = StringField()
    homePage = StringField()
    zipcode = StringField(min_length=5, max_length=5)
    county = StringField()
    locCoordsCoarse = GeoPointField()
    eventList= ListField(StringField())  ## list of past and future events attend(ed/ing)  (db keys, of course)
    favItemList = ListField(ObjectIdField())
    favSellerList = ListField(StringField())

    hiddenItemList = ListField(ObjectIdField())
    hiddenSellerList = ListField(StringField())


    if not STAND_ALONE:

        def getSellerFromOscarID(oscarUserID):
            try:
                return Seller.objects.filter(oscarUserID=oscarUserID).first()
            except:
                return None

        #from oscar.core.compat import get_user_model
        from oscar.apps.customer.models import get_user_model

        from django.db.models.signals import post_save, post_delete, pre_delete 
        from django.dispatch import receiver
        @receiver(post_save, sender=get_user_model())
        def createUser(sender, instance, created, **kwargs):

            importing = False ##settings.IMPORTING
            if not importing:
                #print "Receiver called for post_save of user,  checking if exists"
                if created:
                    try:
                        s = Seller.objects.filter(email = instance.email)[0]
                        print "User " + instance.email + " exists."
                    except:
                        s = Seller()
                        s.email = instance.email
                        print "Created a new user in Mongo DB, email " + instance.email
                        
                    s.name = instance.email
                    s.pw_hash = instance.password
                    s.oscarUserID = instance.id
                    s.save()
                    instance.mongo_id = s.id
                    instance.save()
                
        ## delete Mongo user when PostGre user is deleted. Mostly used in testing?
        @receiver(pre_delete, sender=get_user_model())
        def deleteUser(sender, instance, **kwargs):

            print "Receiver called for deleteUser, attempting to delete a user in MongoDB also, checking if exists"
            try:
                s = Seller.objects.filter(id=instance.mongo_id)[0]
                s.delete()
                print "user with email " + instance.email + " was deleted from Mongo DB"
            except:
                print "Was unable to delete the Mongo User with email " + instance.email
                pass

    @staticmethod
    def getOrCreate(username, fb_id):
        user = Seller.objects.filter(name=username).first()
        if user is None:
            user = Seller(name=username, fb_id=fb_id)
            user.pw_hash = '0000'
            user.email = 'none@homemade1616.us'
            user.save()
        return user

    def getStoreName(self):
        if self.storeName:
            return self.storeName
        else:
            return self.name + "'s booth"

    def getBio(self):
        if self.bio:
            return self.bio
        else:
            return ""

    def getPersonalNameIfExists(self):
        if self.personalName:
            return self.personalName
        else:
            ## don't return 'name' since that might be an email
            return None
    
    def getFirstName(self):
        if self.personalName:
            return self.personalName.split()[0]
        else:
            return None
    
    def setPassword(self, passwd):
        self.pw_hash = generate_password_hash(passwd)
        
    def getCartItems(self):
        return Item.objects(slug__in=cart)


    
    def getRandomHexColor(self):
        randColor = '%06x' % random.randrange(16777215)
        print("Background color is " + str(randColor))
        return "#" + str(randColor)


class Item(DynamicDocument):
    seqId=SequenceField()
    name = StringField(required=True)
    sellerId = ObjectIdField()
    seller = ReferenceField(Seller)    
    sellerName = StringField(required=True)
    storeName = StringField(required=False)    

    ## link to Oscar
    oscarID = IntField()
    
    description = StringField()
    inventory =  IntField(required=True, default=-1)  ## negative is made to order
    picPath = StringField()
    picPathLarge = StringField()
    
    pic = BinaryField()
    priceCents = IntField(required=True)
    category = StringField()
    tags = ListField(StringField()) ## vegan, vegetarian, dairy-free, gluten-free, etc.
    locCoords = GeoPointField()

    isHidden = BooleanField(default=False)   # will show in order history, but not in search
    isCollageable = BooleanField(default=False)
    collagePortrait = BooleanField(default=False)  # default is landscape

    ratingDict = DictField()   # key is person id, value is stars. Comments?
    
    #picList
    #priceList
    #seeAlso
    #variants peach, pear, etc

    def getLargePicPath(self):
        if self.picPathLarge:
            return self.picPathLarge
        else:
            return self.picPath
        
    
    def getPrice(self):
        if self.priceCents:
            return getDollarsFromCents(self.priceCents)
        else:
            return None

    def setPriceFromDollarsToCents(self, priceInDollars):
        self.priceCents = int(float(priceInDollars) * 100) 

    def getInventoryString(self):
        if self.inventory < 0:
            return "Made to order"
        else:
            return str(self.inventory) + " available."
        
    def getStoreName(self):
        if self.storeName:
            return self.storeName
        elif self.seller:
            if seller.storeName:
                return seller.storeName
        else:
            return i.sellerName
        
class OrderItem(EmbeddedDocument):
    """Record of an item from an order """
    seqId = SequenceField()
    name = StringField(required=True)
    sellerName = StringField(required=True)
    item = ReferenceField(Item, required=True)
    itemId = ObjectIdField()
    priceAtTimeOfSale =  IntField(required=True)  ## in cents
    quantity =  IntField(required=True, default=1)
    totalPrice =  IntField(required=True)
    isOpen = BooleanField()

    def getPrice(self):
        return getDollarsFromCents(self.priceAtTimeOfSale)

    def getCurrentTotal(self):
        return self.item.priceCents * self.quantity

    def getTotal(self):
        return self.priceAtTimeOfSale * self.quantity

    def getTotalInDollars(self):
        return getDollarsFromCents(self.getTotal())

    def getCurrentTotalInDollars(self):
        return getDollarsFromCents(self.item.priceCents * self.quantity)

    def getCurrentPriceInDollars(self):
        return getDollarsFromCents(self.item.priceCents)


class GlobalPics(DynamicDocument):
    picDict = DictField()   # key is pic string id, value is pic path

class Order(DynamicDocument):
    """Only one store per order, for now """
    seqId = SequenceField()
    date = DateTimeField(required=False)
    #dateID = StringField(required=True, default= getDateAsIdString(datetime.datetime.today()))
    #itemList = ListField(StringField())  ## list of item ids, get straight from cartItems
    userId = ObjectIdField(required=True)
    userName = StringField(required=True)
    sellerName = StringField()
    seller = ReferenceField(Seller)
    sponsoredOrg = ReferenceField(SponsoredOrg)
    orderItemList =  ListField(EmbeddedDocumentField(OrderItem))
    status = StringField(required=True, default="open") ## open, submitted, completed, delivered, contested, etc.

    def getSellerName(self):
        # return self.seller.name
        return self.sellerName
    
    def getCurrentTotalCents(self):
        totalCents = 0
        for oi in self.orderItemList:
            totalCents = totalCents + oi.getCurrentTotal()
        return totalCents

    def getTotalCents(self):
        totalCents = 0
        for oi in self.orderItemList:
            totalCents = totalCents + oi.getTotal()
        return totalCents

    def getTotalStringInDollars(self):
        return getDollarsFromCents(self.getTotalCents())
    
    def getCurrentTotalStringInDollars(self):
        return getDollarsFromCents(self.getCurrentTotalCents() )

def getTotalSalesForOrg(so):
    if not str(type(so)).count("SponsoredOrg"):
        error  = "Problem in retrieving the total."
        print(error)
        return -1
    try:
        totalRev = 0
        oo = Order.objects(sponsoredOrg=so)
        for o in oo:
            totalRev = totalRev + o.getTotalCents()
    except:
        error = "Problem in calculating the total."
        print(error)
        return -1

    return totalRev



    
def getOpenOrders(u):   
    idList = u.openOrderIds
    return Order.objects(id__in=idList)

def getOrderHistory(u):
    idList = u.orderHistoryIds
    return Order.objects(id__in=idList)
    
def getCoordsFromZipcode(zc):
    try:
        loc = HMGeoData.objects(zipcode=zc)[0].locCoords
        return loc
    except:
        error = "Bad zipcode"
        print(error)
        return None





def getAllItemsWithinRadius(lc, radiusInMiles, itemObjectList):
    """ Search within distance
    lc is GeoPointField, and or lat, long coord tuple/list """

    iList = itemObjectList(locCoords__within_distance=[lc, float(radiusInMiles)])

    #print("Any items from geo search?")
    #for i in iList:
    #    print(i.name)
    #print("OK")
    return iList


categoryList = ["2"]
print("cat list: " + str(categoryList))
def getAllCategoryNames():
    ##if not len(categoryList):
    #for c in Categories.objects():
    #    c.displayOrderId = c.seqId
    #    c.save()
    categoryList = [c.name for c in Categories.objects().order_by('displayOrderId')]
    return categoryList

def getCategories():
    return Categories.objects().order_by('displayOrderId')

class BlogPost(DynamicDocument):
    title = StringField(required=True)
    content = StringField(required=True)
    date = DateTimeField(default=datetime.datetime.today(), required=True)
    seqId = SequenceField()
    tags = ListField(StringField())
    author = StringField()
    picPath=StringField()
    picPathLarge=StringField()
    picPathOrig=StringField()        
    eventId = StringField()  ## if the post refers to an event, this is the ID of that event


    def getLargePicPath(self):
        if self.picPathLarge:
            return self.picPathLarge
        else:
            return self.picPath

def orderSuccess(user, o):

    o.date = datetime.datetime.today()
    o.status = "submitted"
    o.save()
    getTotalSalesForOrg(o.sponsoredOrg)
    user.orderHistoryIds.append(o.id)
    user.openOrderIds.remove(o.id)
    user.save()

    seller = Seller.objects(name=o.sellerName)[0]
    # send msg/email to user and seller
    subjectBuyer = "Order sent to " + seller.getStoreName()
    msgBuyer = "Order #"+ str(o.seqId) + " submitted at " +  o.date.strftime('%B %d, %Y. %H:%M')
    emailUser(user, seller, subjectBuyer, msgBuyer)

    subjectSeller = "You have a new order, #" + str(o.seqId)
    msgSeller = "Order submitted at " +  o.date.strftime('%B %d, %Y. %H:%M') + ".  "
    msgSeller = msgSeller + "From " + user.getPersonalNameIfExists() + "\n"
    msgSeller = msgSeller + '<a href="http://www.homemade1616.com/orders/' + str(o.seqId) + '"> Link to order page </a>'
    emailUser(seller, user, subjectSeller, msgSeller)
    # adjust inventory of seller's items.
    for oi in o.orderItemList:
        try:
            #print(oi)
            #print(oi.item)
            i = oi.item
            #print(i.inventory)
            if i.inventory >= 1:
                i.inventory = i.inventory - oi.quantity
                i.save()
        except:
            error = "ERROR for admin: Unable to adjust the inventory of item " + i.name + " in order " + str(o.seqId)
            print(error)
    return
    


def getSellerFromOscarID(oscarUserID):
    try:
        return Seller.objects.filter(oscarUserID=oscarUserID).first()
    except:
        return None

def clearDatabases():

    ## get rid of orders
    Order.drop_collection()
    SponsoredOrg.drop_collection()
    Seller.drop_collection()
    Item.drop_collection()
    BlogPost.drop_collection()
    Categories.drop_collection()


    ## get rid of sponsored orgs
    #for s in SponsoredOrg.objects():
    #    s.delete()
    ## get rid of sellers
    #for s in Seller.objects():
    #    s.delete()
    ## get rid of items
    #for s in Item.objects():
    #    s.delete()
    ## get rid of blog entries
    #for s in BlogPost.objects():
    #    s.delete()

    
def generateSampleDB():

    clearDatabases()
    
    c = Categories(isPrimary=True, name = "Jams and Preserves")
    c.save()
    c = Categories(isPrimary=True, name = "Baked Goods")
    c.save()
    c = Categories(isPrimary=True, name = "Fruits and Vegetables")
    c.save()
    c = Categories(isPrimary=True, name = "Nut Butters")
    c.save()
    c = Categories(isPrimary=True, name = "Homemade Candy")
    c.save()
    c = Categories(isPrimary=True, name = "Granola and Cereals")
    c.save()
    c = Categories(isPrimary=True, name = "Other")
    c.save()
    
    
    s = SponsoredOrg()
    s.name = "Gardens of Attitude"
    s.save()
    s = SponsoredOrg(name='Dumpster Divers Anonymous')
    s.save()
    s = SponsoredOrg(name='Food Backwards')
    s.save()

    #
    #  create default admin account
    blogger =  Seller(name="blogger")
    blogger.pw_hash = generate_password_hash("ok")
    blogger.email = "rb@b.com"
    blogger.isAdmin = True
    blogger.isBlogAdmin = True    
    blogger.save()

    ## save user
    rb = Seller(name="rb")
    rb.pw_hash = generate_password_hash("ok")
    rb.email = "rb@b.com"
    rb.storeExists = False
    rb.bio="A computer programmer who also grows vegetables."
    rb.zipcode="90291"
    rb.save()
    # sample item
    wm = Item(name="Watermelon",picPath="watermelon02.png", slug="asdasdh3", priceCents=340, sellerName='rb')
    wm.locCoords = getCoordsFromZipcode(rb.zipcode)
    wm.save()
    rb.itemIds.append(wm.id)
    rb.storeExists = True
    rb.save()
    
    dr = Seller(name="Sample", pw_hash = generate_password_hash("ok"), email = "b@b.com")
    dr.zipcode = "90403"
    dr.storeName = "Super Samples"
    wm3 = Item(name="Canteloupe",picPath="watermelon02.png", slug="sjdh3", priceCents=340, sellerName=dr.name)
    wm3.locCoords = getCoordsFromZipcode(dr.zipcode)
    wm3.save()
    dr.itemIds.append(wm3.id)

    ## add the above item to the OTHER user's cart
    o = Order(userId=rb.id, userName=rb.name, status="open")
    o.save()
    rb.openOrderIds.append(o.id)
    rb.save()
    oi = OrderItem(item=wm3)
    oi.sellerName = wm3.sellerName
    oi.name = wm3.name
    oi.priceAtTimeOfSale = wm3.priceCents
    oi.quantity = 2
    oi.totalPrice = oi.priceAtTimeOfSale * oi.quantity
    o.orderItemList.append(oi)
    ls = str(len(o.orderItemList))
    print("Now have " + ls +" in list.")
    o.sellerName = wm3.sellerName
    o.save()

    #rb.orderHistory.append(o)
    rb.save()

    # add more items
    pch = Item(name="Peach")
    pch.picPath = "huevos48Icon3.png"
    pch.slug = "Asda3"
    pch.priceCents = 225
    pch.sellerName = dr.name
    pch.locCoords = getCoordsFromZipcode(dr.zipcode)
    pch.save()
    dr.itemIds.append(pch.id)


    pch = Item(name="Eggs")
    pch.picPath = "huevos48Icon3.png"
    pch.slug = "Asd234"
    pch.priceCents = 150
    pch.sellerName = dr.name
    pch.category="Other"
    pch.locCoords = getCoordsFromZipcode(dr.zipcode)
    pch.save()
    dr.itemIds.append(pch.id)
    
    pch = Item(name="Pears")
    pch.picPath = wm.picPath
    pch.slug = "asdq33"
    pch.priceCents = 200
    pch.sellerName = dr.name
    pch.category = "Fruits and Vegetables"
    pch.locCoords = getCoordsFromZipcode(dr.zipcode)
    pch.save()
    dr.itemIds.append(pch.id)
    
    ## save the seller to the database
    dr.storeExists = True 
    dr.save()
        
    # set up sample blog entries
    b1 = BlogPost()
    b1.title = "My awesome event and/or recipe!"
    b1.author = "RB"
    b1.content = "Coming soon, some actual content."
    b1.save()
    
    blogPostList.append(b1)

    b2 = BlogPost(title="New Swap Meet", author="RB", content = "Come to our next swap meet.")
    b2.save()
    blogPostList.append(b2)

    
    b2 = BlogPost(title="New Store", author="RB", content = "Check out our newest store: ")
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Recipe 2", author="RB", content = "Check out our newest store: ")
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Recipe 3", author="RB", content = "Check out our store")
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Post about nothing.", author="RB", content = "Check out our store")
    ct = 'Random text here. '
    for i in range(34):
        ct = ct + "Another random set of characters. "
    b2.content = ct
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Event 2", author="RB", content = "Check out our store")
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Recipe 6", author="RB", content = "Check out our store")
    b2.save()
    blogPostList.append(b2)
    b2 = BlogPost(title="Event 4", author="RB", content = "Check out our store")
    b2.save()
    blogPostList.append(b2)

def getItem(id):
    return Item.objects(slug=id)

def get_user(uname):
    r = Seller.objects(name=uname)
    if not len(r):
        return None
    else:
        if len(r) == 1:
            return r[0]
        if len(r) > 1:
            return "ERROR"


@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = get_user(session['user_id'])
        

@app.route('/landing')
def landing():
    #if g.user:
    #    print("User logged in!")
    if request.args.has_key('msg'):
        msg = request.args['msg']
    else:
        msg = None

    collageItemsPortrait = Item.objects(isCollageable=True, collagePortrait=True)  # (isCollageable=True)
    collageItemsLandscape = Item.objects(isCollageable=True, collagePortrait=False).order_by("id")
    #for i in collageItemsPortrait:
    #    print("P" + i.name)
    #for i in collageItemsLandscape:
    #    print("L" + i.name)

    
    return render_template('index.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, msg=msg)
#return render_template('browseHome.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, iList=collageItemsLandscape, msg=msg)

@app.route('/password_reset')
def passwordReset():

    if not g.user:
        return redirect(url_for('index', msg=msg))
    if g.user:
        print("User logged in!")
    if request.args.has_key('msg'):
        msg = request.args['msg']
    else:
        msg = None

    collageItemsPortrait = Item.objects(isCollageable=True, collagePortrait=True)  # (isCollageable=True)
    collageItemsLandscape = Item.objects(isCollageable=True, collagePortrait=False).order_by("id")

    return render_template('index.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, msg=msg)

@app.route('/_add_numbers')
def add_numbers():
    """Add two numbers server side, ridiculous but well..."""
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)

@app.route('/_ajax_test')
def ajax_test():
    """  """
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    
    print "DONE"
    return jsonify(result=True)


@app.route('/')
def index():
    #if g.user:
    #    print("User logged in!")

    if request.args.has_key('msg'):
        msg = request.args['msg']
    else:
        msg = None
    
    if not g.user:
        return redirect(url_for('invite', msg=msg))

    favList = None
    if g.user:
        idList = g.user.favItemList
        favList = Item.objects(id__in=idList)
    

    collageItemsPortrait = Item.objects(isCollageable=True, collagePortrait=True)  # (isCollageable=True)
    collageItemsLandscape = Item.objects(isCollageable=True, collagePortrait__nin=[True]).order_by("-id")
    #print "In index()"
    #for i in collageItemsPortrait:
    #    print("P" + i.name)
    #for i in collageItemsLandscape:
    #    print("L" + i.name)

    iList = collageItemsLandscape
    sampleNum = 9
    if sampleNum > len(iList):
        sampleNum = len(iList)
    iList = random.sample(iList, sampleNum)
    
    print ("DEBUG",  DEBUG)

    ##return render_template('index.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, msg=msg)
    if DEBUG:
        return render_template('browseFoundTest.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, iList=iList, favList=favList,msg=msg)
    else:
        return render_template('browseHome.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, iList=iList, favList=favList,msg=msg)


@app.route('/fnd')
def indexEx():
    #if g.user:
    #    print("User logged in!")

    if request.args.has_key('msg'):
        msg = request.args['msg']
    else:
        msg = None
    
    if not g.user:
        return redirect(url_for('invite', msg=msg))

    favList = None
    if g.user:
        idList = g.user.favItemList
        favList = Item.objects(id__in=idList)
    

    collageItemsPortrait = Item.objects(isCollageable=True, collagePortrait=True)  # (isCollageable=True)
    collageItemsLandscape = Item.objects(isCollageable=True, collagePortrait__nin=[True]).order_by("-id")
    #print "In index()"
    #for i in collageItemsPortrait:
    #    print("P" + i.name)
    #for i in collageItemsLandscape:
    #    print("L" + i.name)

    iList = collageItemsLandscape
    sampleNum = 9
    if sampleNum > len(iList):
        sampleNum = len(iList)
    iList = random.sample(iList, sampleNum)
    

    ##return render_template('index.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, msg=msg)
    return render_template('browseFoundTest.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, iList=iList, favList=favList,msg=msg)
    ##return render_template('browseHome.html', cList=getCategories(), collageItemsPortrait = collageItemsPortrait, collageItemsLandscape=collageItemsLandscape, iList=iList, favList=favList,msg=msg)


#@app.route("/favicon.ico")
#def favicon():
#    return app.send_static_file("H1616_32x32.png")


@app.route("/booths")
def browse_stores_as_list():
    
    sList = Seller.objects(storeExists=True)
    return render_template("browse_stores_as_list.html", sList=sList )


@app.route("/permit_info/")
def permitDescription(zipcode=None):
    render_template('permit_info.html', county="The county has not been implemented.", zipcode=zipcode)

def faq_main(*args, **kwargs):

    request = args[0]
    request.args = request.GET
    request.form = request.POST
    request.files = request.FILES

    return render_template("faq_main.html")


def hm_test(*args, **kwargs):

    request = args[0]
    request.args = request.GET
    request.form = request.POST
    request.files = request.FILES

    return render_template("hm_test.html")

@app.route("/invite/", methods=['GET', 'POST'])
def invite(*args, **kwargs):


    if STAND_ALONE:
        r = 9        
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request

    if request.method == 'POST':
        if not request.form.has_key('email'):
            msg = 'Please enter an email address.'
            return render_template('invite.html', msg=msg)
        else:
            email = request.form['email']
            enew = EmailInvites(email=email)
            enew.save()
            return render_template('inviteThanks.html')

    collageItemsLandscape = Item.objects(isCollageable=True, collagePortrait__nin=[True]).order_by("-id")
    if not GlobalPics.objects():
        n = GlobalPics()
        n.picDict['test'] = "test"
        n.save()
    pd = (GlobalPics.objects())[0].picDict
    for k in pd.keys():
        print k + "  " + pd[k]
    return render_template("invite.html", collageItemsLandscape=collageItemsLandscape, picDict=pd)

@app.route("/contact_us/", methods=['GET', 'POST'])
def contactUs(*args, **kwargs):




    if STAND_ALONE:
        if g.user:
            u = g.user


    else:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
        if request.user.is_authenticated():
            u = getSellerFromOscarID(request.user.id)
        else:
            u = None

    #adminName = app.config['ADMIN_USERNAME']

    topicDict = OrderedDict()
    if request.method == 'GET':
        if request.GET.get("topic"):
            topicDict['other'] = request.GET.get("topic")

    topicDict["general question"] = "General question"
    topicDict["website"] = "Website issue"

    #adminUser= getSellerFromOscarID(id)##Seller.objects(name=adminName)[0]

    try:
        oscarUserToMsg = User.objects.filter(is_staff=True)[0]

    except:
        msg = "No user or booth by that name."
        return redirect(url_for('about',  msg=msg))


    try:
        print "user to msg: " + oscarUserToMsg.email
    except:
        pass

    msg = None
    if request.method == 'POST':
        if not request.form['text']:
            msg = 'Please enter a message.'
            return render_template('contact_peer.html', topicDict=topicDict, oscarUserToMsg=oscarUserToMsg)
            ##return render_template('contact_peer.html', topicDict=topicDict, msg=msg, userToMsg=adminUser)
        else:
            msg = request.form['text']
            topicForSubject = ""
            #topic = None

            anonEmail = None
            if request.form.get('email'):
                anonEmail = request.form.get('email')
                print "anonymous email from " + anonEmail

            if request.form['topicChoice']:
                topic = request.form['topicChoice']
                topicForSubject = ""
                if topic == "website":
                    topicForSubject = " about the " +topic

                #elif topic != "misc":
                #    topicForSubject = " " + topic

            try:
                
                senderName = request.user.partner.name
            except:
                try:
                    if request.user.first_name:
                        sender = request.user
                        senderName = request.user.first_name + ' ' + request.user.last_name
                        if not senderName:
                            senderName = " user " + request.user.id
                    else:
                        senderName = "an anonymous user"
                except:
                    senderName = "an anonymous user"

            subject = "Homemade 1616 question" +topicForSubject+ ", from " + senderName 

            ctx = {
                'user': request.user,
                'userToMsg': oscarUserToMsg,
                ##'muserTo': adminUser,
                'muserFrom': u,
                'msgFromUser': msg,
                'subject': subject,
                'site': get_current_site(request),

            }
            Dispatcher = get_class('customer.utils', 'Dispatcher')
            CommunicationEventType = get_model('customer', 'CommunicationEventType')

            msgs = CommunicationEventType.objects.get_and_render(
                code="CONTACT_PEER", context=ctx)
         
            sender = None
            if request.user.is_authenticated():
                sender = request.user

            Dispatcher().dispatch_user_messages(oscarUserToMsg, msgs, sender)
            ## hack
            try:
                if subject.count("question") > 0:
                    ewUser = User.objects.filter(email="erica@homemade1616.com")[0]
                    Dispatcher().dispatch_user_messages(ewUser, msgs, sender=sender)            
            except:
                pass

            #emailUser(adminUser, sender=sender, subject=subject, msgStr=msg)
        messages.info(request, "Sent your message to the Homemade staff")
        return redirect(url_for('catalogue:index',  msg="Sent your message to the Homemade staff"))
    # if GET
    return render_template('contact_peer.html', topicDict=topicDict, oscarUserToMsg=oscarUserToMsg)

@app.route("/contact/<store_name>", methods=['GET', 'POST'])

def contactGuestBuyer(*args, **kwargs):


    request = args[0]
    request.args = request.GET
    request.form = request.POST
    request.files = request.FILES
    g = request
    u = getSellerFromOscarID(request.user.id)
    adminName = 'blogger'

    if request.args.has_key('order_num'):
        ##emailToMsg = request.args.get('email')

        try:
            o = OscarOrder.objects.get(number=request.args.get('order_num') )
        except:
            errMsg = "Page not found"
            messages.info(request, errMsg)
            return redirect(url_for('catalogue:index'))

        ## don't show this page unless admin or seller
        if not request.user.is_staff:
            firstLine = OrderLine.objects.filter(order=o)[0]
            partner = firstLine.partner
            seller = partner.user
            if seller != request.user:
                errMsg = "Page not found"
                messages.info(request, errMsg)
                return redirect(url_for('catalogue:index'))

    else:
        errMsg = "Page not found"
        messages.info(request, errMsg)
        return redirect(url_for('catalogue:index'))

    oscarSender = request.user

    subject = "Order " + o.number
    ## set previous subject and text if a reply
    if request.args.has_key('subject'):
        subject = request.args['subject']

    try:
        a = oscarSender.email
    except:
        oscarSender = None

    try:
        if oscarSender.first_name or oscarSender.last_name:
            personalNameOfSender = oscarSender.first_name + " " + oscarSender.last_name
        else:
            personalNameOfSender = None
    except:
        personalNameOfSender = None
    #personalNameOfSender = userToMsg.getPersonalNameIfExists()
    if not personalNameOfSender:
        personalNameOfSender = "a customer "
    
    # if request.args.has_key('order_id'):
    #     orderSeqId = request.args['orderSeqId']
    #     #o = Order.objects(seqId=orderSeqId)
    #     topicDict['order'] = "Question about order #" + str(orderSeqId)
    #     topicDict["item"] = "Question about an item"
    #     topicDict["misc"] = "General question"
    #     msgText = "Regarding " + url_for("order", orderID=int(orderSeqId), _external=True)
    #     # print url_for(order(orderSeqId))
    # else:
    #     topicDict["item"] = "Question about an item"
    #     topicDict["order"] = "Order information"
    #     topicDict["misc"] = "General question"

    msg = ''

    if request.method == 'POST':

        if not request.form['text']:
            msg = 'Please enter a message.'
            return render_template('contact_peer.html', msg=msg, topicDict=topicDict, oscarUserToMsg=None)
        else:
            msg = request.form['text']


            topicForSubject = "Message regarding order " + o.number

            guestEmail = None
            if request.form.get('email'):
                guestEmail = request.form.get('email')

            else:
                guestEmail = o.email

            if request.form['subject'] != "None" and request.form['subject'] != '':
                subject = request.form['subject']
            else:
                subject = "Message from " + personalNameOfSender + " " + topicForSubject
            ##emailUser(userToMsg, sender=u, subject=subject, msgStr=msg)
            
            ##if guestEmail:
            ##    subject = subject #+ ", from " + anonEmail

            replyToFlag = False
            if request.POST.get('reply_to'):
                if request.POST.get('reply_to') == "on":
                    replyToFlag = True


            thread_ref = None

            ctx = {
                'user': request.user,
                'userToMsg': None,
                'msgFromUser': msg,
                'subject': subject,
                'site': get_current_site(request),
                'thread_ref':thread_ref,
                'guest_recipient': True, 
                'replyToFlag': replyToFlag,

            }
            Dispatcher = get_class('customer.utils', 'Dispatcher')
            CommunicationEventType = get_model('customer', 'CommunicationEventType')

            msgs = CommunicationEventType.objects.get_and_render(
                code="CONTACT_PEER", context=ctx)
            Dispatcher().dispatch_guest_messages(guestEmail, msgs, oscarSender, replyToFlag = replyToFlag)


        return redirect(url_for('customer:sales-list'))
    # if GET , show this
    return render_template('contact_peer.html', topicDict=[], oscarUserToMsg=None, msgText=msg, subject=subject, email=o.guest_email)






def contactPeer(*args, **kwargs):##store_name=None, orderSeqId=None):
 
    if STAND_ALONE:
        if not g.user:
            return render_template('login.html')
 

        if g.user:
            u = g.user
        adminName = app.config['ADMIN_USERNAME']




    else:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
        u = getSellerFromOscarID(request.user.id)
        adminName = 'blogger'

    print "REQ"
    print request.args

    if request.args.has_key('store_name'):
        store_name = request.args['store_name']
        print store_name
        try:
            oscarUserToMsg = User.objects.filter(partner__name=store_name)[0]

        #        oscarUserToMsg = User.objects.filter(username=userToMsg.id)[0]
        except:
            msg = "No user or booth by that name."
            return redirect(url_for('about',  msg=msg))

    elif request.args.has_key('booth'):
        boothId = request.args['booth']
        print "boothId: "
        print boothId
        try:
            oscarUserToMsg = User.objects.filter(partner__id=int(boothId))[0]

        except:
            msg = "No user or booth by that name."
            return redirect(url_for('about',  msg=msg))
    
    elif request.args.has_key('user'):
        userHash = request.args['user']
        try:
            oscarUserToMsg = User.objects.filter(username=userHash)[0]
            print "Found user with username " + userHash
        except:
            msg = "No user or booth by that name."
            print "user " + userHash+ " not found for emailing"
            return redirect(url_for('about',  msg=msg))
    elif request.args.has_key('email'):
        r= 9
    else:
        msg = "No user or booth specified"
        return redirect(url_for('about',  msg=msg))

    # if not userToMsg:   
    #     msg = "No user or booth by that name."
    #     print msg
    #     return redirect(url_for('about',  msg=msg))


    topicDict = OrderedDict()
    msgText = ''
    subject= None

    oscarSender = request.user


    ## set previous subject and text if a reply
    if request.args.has_key('subject'):
        subject = request.args['subject']



    try:
        a = oscarSender.email
    except:
        oscarSender = None

    try:
        if oscarSender.first_name or oscarSender.last_name:
            personalNameOfSender = oscarSender.first_name + " " + oscarSender.last_name
        else:
            personalNameOfSender = None
    except:
        personalNameOfSender = None
    #personalNameOfSender = userToMsg.getPersonalNameIfExists()
    if not personalNameOfSender:
        personalNameOfSender = "a customer "
    
    if request.args.has_key('orderSeqId'):
        orderSeqId = request.args['orderSeqId']
        #o = Order.objects(seqId=orderSeqId)
        topicDict['order'] = "Question about order #" + str(orderSeqId)
        topicDict["item"] = "Question about an item"
        topicDict["misc"] = "General question"
        msgText = "Regarding " + url_for("order", orderID=int(orderSeqId), _external=True)
        # print url_for(order(orderSeqId))
    else:
        topicDict["item"] = "Question about an item"
        topicDict["order"] = "Order information"
        topicDict["misc"] = "General question"

    msg = None
    if request.method == 'POST':

        if not request.form['text']:
            msg = 'Please enter a message.'
            return render_template('contact_peer.html', msg=msg, topicDict=topicDict, oscarUserToMsg=oscarUserToMsg)
        else:
            msg = request.form['text']
            topicForSubject = ""
            if request.form.has_key('topicChoice'):
                topic = request.form['topicChoice']
                if topic != "misc":
                    topicForSubject = " regarding an " + topic 

            anonEmail = None
            if request.form.get('email'):
                anonEmail = request.form.get('email')

            replyToFlag = False
            if request.POST.get('reply_to'):
                if request.POST.get('reply_to') == "on":
                    replyToFlag = True


            if request.form['subject'] != "None" and request.form['subject'] != '':
                subject = request.form['subject']
            else:
                subject = "Message from " + personalNameOfSender + " " + topicForSubject
            ##emailUser(userToMsg, sender=u, subject=subject, msgStr=msg)
            
            if anonEmail:
                subject = subject + ", from " + anonEmail

            ctx = {
                'user': request.user,
                'userToMsg': oscarUserToMsg,
                #'muserTo': userToMsg,
                #'muserFrom': u,
                'msgFromUser': msg,
                'subject': subject,
                'site': get_current_site(request),
                'replyToFlag': replyToFlag,

            }
            Dispatcher = get_class('customer.utils', 'Dispatcher')
            CommunicationEventType = get_model('customer', 'CommunicationEventType')

            msgs = CommunicationEventType.objects.get_and_render(
                code="CONTACT_PEER", context=ctx)
            Dispatcher().dispatch_user_messages(oscarUserToMsg, msgs, oscarSender, replyToFlag = replyToFlag)


        
        return redirect(url_for('catalogue:index', booth=oscarUserToMsg.partner.id))##, msg="Sent your message to " + userToMsg.storeName))
    # if GET 
    return render_template('contact_peer.html', topicDict=topicDict, oscarUserToMsg=oscarUserToMsg, msgText=msgText, subject=subject)





@app.route("/folks/<user_name>/favorite_folks")
def favSellers(*args):

    if not STAND_ALONE:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        g = request
        mu = getSellerFromOscarID(request.user.id)
    else:
        mu = g.user

    user_name = request.args['user_name']
    if user_name:
        u = Seller.objects(name=user_name)[0]
    else:
        u = mu
    nameList = u.favSellerList
    sList = Seller.objects(name__in=nameList)
    #return render_template("browse_stores_as_list.html", sList=sList )
    return render_template("favBooths.html", sList=sList,u=u, mu=mu )


@app.route('/add_seller_to_favs/<seller_name>')
def add_seller_to_favs(seller_name=None):

    g.user.favSellerList.append(seller_name)
    g.user.save()
    return redirect(url_for('store', store_name=seller_name))

@app.route('/remove_seller_from_favs/<seller_name>')
def remove_seller_from_favs(seller_name=None):
    g.user.favSellerList.remove(seller_name)
    g.user.save()
    return redirect(url_for('store', store_name=seller_name))



@app.route("/folks/<user_name>/favs")
def favItems(user_name=None):
    #if request.args.has_key("user_name"):
    #    u = Seller.objects(name=request.args['user_name'])[0]
    if user_name:
        u = Seller.objects(name=user_name)[0]
    else:
        u = g.user
    print("user: " + str(u.name))
    idList = u.favItemList
    iList = Item.objects(id__in=idList)
    return render_template("favItems.html", iList=iList, cList=getCategories(), u=u)

#return render_template("browse_items.html", iList=iList, cList=getCategories(), u=u)


@app.route('/add_to_favs/<item_id>')
def add_to_favs(item_id=None):
    g.user.favItemList.append(item_id)
    g.user.save()
    return redirect(url_for('item', item_id = item_id))

@app.route('/remove_from_favs/<item_id>')
def remove_from_favs(item_id=None):
    id = Item.objects(id=item_id)[0].id
    g.user.favItemList.remove(id)
    g.user.save()
    return redirect(url_for('item', item_id = item_id))


def emailUser(receiver, sender, subject, msgStr, sendAsFromUserEmailAddress=False, addLogo=False):
    print("Mailing to " + receiver.name + ":")
    print("Subject: " + subject)
    print(msgStr)

    ## JSON interface
    toData = {"email":receiver.email, "name":receiver.getPersonalNameIfExists()}
    sendEmail = "Homemade 1616 <messaging@homemade1616.com>"
    if sendAsFromUserEmailAddress:
        sendEmail = sender.email
    #msgData = {"subject":subject, "html":msgStr, "from_email":sendEmail, "from_name":sender.getPersonalNameIfExists(), "to":toData}
    msgData = {"subject":subject, "html":msgStr, "from_email":sendEmail, "from_name":"Homemade 1616", "to":toData}
    mStruct = json.dumps({"message":msgData})
    print(mStruct)
    key = os.environ['MANDRILL_KEY']

    if False:
        m = Mandrill(key)
        m.messages.send(message=mStruct)

    msg = MIMEMultipart('alternative')

    msg['Subject'] = subject
    msg['From']    = sendEmail  #sender.email #"rsbusby@gmail.com" # Your from name and email address
    msg['To']      = receiver.email #"RB <rsbusby@gmail.com>"

    text = str(msgStr)
    part1 = MIMEText(text, 'plain')

    logoStr = ''
    if addLogo:
        logoStr = '<img style="" src="' + url_for('static', filename=('icons/H1616-LOGO-BROWN.png')) +'"  >'

    html = logoStr + msgStr
    part2 = MIMEText(html, 'html')

    #username = os.environ['MANDRILL_USERNAME']
    #password = os.environ['MANDRILL_PASSWORD']
    username = "app10788552@heroku.com"
    password = key

    msg.attach(part1)
    msg.attach(part2)

    s = smtplib.SMTP('smtp.mandrillapp.com', 587)

    s.login(username, password)
    s.sendmail(msg['From'], msg['To'], msg.as_string())

    s.quit()

    return

@app.route('/orders/<orderID>')
def order(orderID=None):
    if not g.user:
        return render_template('login.html')
    
    try:
        o = Order.objects(seqId=int(orderID))[0]
    except:
        msg = "No order with the ID " + str(orderID)
        return render_template('index.html',msg=msg)

    ## allow for admin to see anyone's order history
    if g.user.name != o.userName and not g.user.isAdmin and o.sellerName != g.user.name:
        return render_template('index.html')
        
    return render_template('order.html', o = o, oiList = o.orderItemList)

@app.route('/folks/<user_name>/sales_history')
def sales_history(user_name=None):
    
    if not g.user:
        return render_template('login.html')
    ## allow for admin to see anyone's order history
    if g.user.name != user_name and not g.user.isAdmin:
        return render_template('index.html')
    
    try:
        user = Seller.objects(name=user_name)[0]
    except:
        msg = "No person with the name " + user_name 
        return render_template('index.html', msg=msg)

    oList = Order.objects(sellerName = user_name)
    if len(oList) == 0:
        oList = []
    print(oList)
    return render_template('order_history.html', u=user, oList=oList, orderString = "Sales")

@app.route('/folks/<user_name>/order_history')
def order_history(user_name=None):
    
    if not g.user:
        return render_template('login.html')
    ## allow for admin to see anyone's order history
    if g.user.name != user_name and not g.user.isAdmin:
        return render_template('index.html')
    
    try:
        user = Seller.objects(name=user_name)[0]
    except:
        msg = "No person with the name " + user_name 
        return render_template('index.html', msg=msg)
    oList = getOrderHistory(user)
    if not oList:
        oList = []
    return render_template('order_history.html', u=user, oList=oList, orderString = "Order")

    
@app.route('/folks/<user_name>')
def profile(user_name=None):

    try:
        userObj = Seller.objects(name=user_name)[0]
    except:
        msg = "No person with the name " + user_name 
        return render_template('index.html', msg=msg)
    
    return render_template('profile.html', u=userObj)


@app.route('/folks/<user_name>/edit', methods=['GET', 'POST'])
def edit_profile(user_name=None):


    if not g.user:
        return redirect(url_for('login'))
    # if not the logged in user (or admin), just send to the profile page
    if user_name != g.user.name and not g.user.isAdmin :
        try:
            u = Seller.objects(name=user_name)[0]
            return render_template('profile.html', u=u)
        except:
            msg = "No person with the name " + user_name 
            return render_template('index.html', msg=msg)

    print "in edit"
    print request
    print request.form
    print " "
    print " "
    for k in request.form.keys():
        print k
    
    print " files"
    print request.files
    print " "
    
    returnToForm = False

    try:
        u = Seller.objects(name=user_name)[0]
    except:
        msg = "No such user found"
        return redirect(url_for('index', msg=msg))

    print("USing " + u.getPersonalNameIfExists())

    if request.method == 'POST':



        # check for delete
        if request.form.has_key('deleteUserId'):
            try:
                uid = request.form['deleteUserId']
                print "Can find"
                print Seller.objects(id=uid)
                uToDelete = Seller.objects(id=uid).first()
                print("Deleting " + uToDelete.name)
                msg = "The user " + uToDelete.name + " has been removed from the system."
                ## delete user
                uToDelete.delete()
                # logout if not admin
                if not g.user.isAdmin:
                    session.pop('user_id', None)
                return redirect(url_for('index', msg=msg ))      
            except:
                msg = "Not possible"
                return redirect(url_for('index', msg=msg))

            return redirect(url_for('index', s))

        ## control flow
        if request.form.has_key('x1'):
            returnToForm = True


        # only update the database if info changes
        if request.form.has_key('storeName'):
            if request.form['storeName'] != u.storeName:
                u.storeName = request.form['storeName']
        print "val is now " + str(u.storeIsInactive)
        if request.form.has_key('hideBooth'):
            if request.form['hideBooth'] == 'on':
                u.storeIsInactive = True
                print "setting to true"
        else:
            print "setting to false"
            u.storeIsInactive = False
        if request.form.has_key('personalName'):
            if request.form['personalName'] != u.personalName:
                u.personalName = request.form['personalName']
        if request.form.has_key('email'):
            if request.form['email'] != u.email:
                u.email = request.form['email']
        if request.form.has_key('zipcode'):
            if request.form['zipcode'] != u.zipcode:
                u.zipcode = request.form['zipcode']
        if request.form.has_key('bio'):
            if request.form['bio'] != u.bio:
                u.bio = request.form['bio']

        
        if request.files.has_key('pic'):
            getProfilePic(u, request)
            #getPicJCrop(u, 'pic',  request)

        if request.files.has_key('store_pic'):
            if request.form.has_key('h') and request.form['h'] != '':
                getPicJCrop(u, 'store_pic', request)
            else:
                getStorePic(u, request)
        if request.form.has_key('old_password'):
            if not check_password_hash(u.pw_hash, request.form['old_password']):
                msg = 'Invalid password'
            elif request.form.has_key('password'):
                if not request.form.has_key('password2'):
                    msg = 'Please verify the new password'
                elif request.form['password'] != request.form['password2']:
                    msg = 'The two new passwords did not match'
                else:
                    u.pw_hash = generate_password_hash(request.form['password'])
    
        u.save()
        if returnToForm:
            return render_template('edit_profile.html', u=u)
        else:
            return render_template('profile.html', u=u)


    return render_template('edit_profile.html', u=u)

def getProfilePic(u, request):
    file = request.files['pic']
    # should check that file is good type
    if file:
        filename = secure_filename(file.filename)
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename

        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fileSaveNameAbs)
        fileDirAbs = app.config['UPLOAD_FOLDER']
        fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
        u.personalPicPath = scaleImage(fileSaveNameAbs, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=300)
        uploadPicsToS3([u.personalPicPath], dir=app.config['STATIC_FOLDER'])
        u.save()


def getPicJCrop(u, fileKey, request):
    
    file = request.files[fileKey]
 
    if file:
        filename = secure_filename(file.name)
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename
        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        ## for Django
        # or self.files['image'] in your form
        path = default_storage.save(filename, ContentFile(file.read()))
        fileSaveNameAbs = os.path.join(settings.MEDIA_ROOT, path)


        #file.save(fileSaveNameAbs)
        fileDirAbs = settings.MEDIA_ROOT #app.config['UPLOAD_FOLDER']
        fileDirRelative = '' ## app.config['UPLOAD_RELATIVE_FOLDER']
      
       
        if fileKey.count('store'):
            print "saving store pic"

            if u:
                u.storePicPath = filename
            #u.storePicPath = scaleImageFromJCrop(request, fileSaveNameAbs, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=500)
            #uploadPicsToS3([u.storePicPath], dir=fileDirAbs)

        else:
            if u:
                u.personalPicPath = scaleImageFromJCrop(request, fileSaveNameAbs, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=300)
            print "saving profile pic"
            uploadPicsToS3([u.personalPicPath], dir=app.config['STATIC_FOLDER'])

        #u.storePicPath = scaleImage(fileSaveNameAbs, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=500)
        if u:
            u.save()

        return filename



def getStorePic(u, request):
    
    file = request.files['store_pic']
    # should check that file is good type
    if file:
        filename = secure_filename(file.filename)
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename
        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fileSaveNameAbs)
        fileDirAbs = app.config['UPLOAD_FOLDER']
        fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
        
        u.storePicPath = scaleImage(fileSaveNameAbs, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=500)
        
        uploadPicsToS3([u.storePicPath], dir=app.config['STATIC_FOLDER'])
        u.save()

@app.route('/booth/<store_name>')
def store(*args):

    if not STAND_ALONE:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        g = request
        mu = getSellerFromOscarID(request.user.id)
    else:
        mu = g.user

    user_name = request.args['store_name']
    try:
        u = Seller.objects(name=user_name)[0]
    except:
        msg = "No booth with the name " + user_name 
        return render_template('index.html', msg=msg)

    msg = None

    if u.storeIsInactive:
        if u == mu or u.isAdmin:
            msg = "Your booth is currently closed"
        else:
            msg = u.getPersonalNameIfExists() + "'s booth is currently closed"
            return render_template('browseHome.html', msg=msg)

    s = u.itemIds
    iList = Item.objects(id__in=s)
    if request.args.has_key('msg'):
        msg = request.args['msg']


    #print u.bio
    
    return render_template('store.html', iList=iList, u = u, msg=msg, mu = mu)

@app.route('/add_to_cart/<item_id>')
def add_to_cart(item_id=None):
    if not g.user:
        return redirect(url_for('login'))
    else:
        user = g.user
    ## check that the item exists
    iRes = Item.objects(id=item_id)
    if not len(iRes):
        return redirect(url_for('store', store_name=store_name))
    i = iRes[0]

    quantity = 1 
    if request.args.has_key('quantity'):
        try:
            quantity = int(request.args['quantity'])
        except:
            print("ERROR in updating quantity. Value not int? " + request.args['quantity'] + "  " + str(int(request.args['quantity'])))

    if len(g.user.openOrderIds):
        ooList = getOpenOrders(g.user)
        openOrderSellers = [o.getSellerName() for o in ooList]
    else:
        openOrderSellers = []
    if not g.user.openOrderIds or i.sellerName not in openOrderSellers:
        # make a new current order, sub-cart
        o = Order(userId=g.user.id, userName=g.user.name, status="open")
        o.sellerName = i.sellerName
        o.seller = Seller.objects(name=i.sellerName).first()
        o.save()
        g.user.openOrderIds.append(o.id)
        g.user.save()
    else:
        # find the openOrder to add to
        for oo in getOpenOrders(g.user):
            if oo.sellerName == i.sellerName:
                o = oo

    # check if item already in order
    iList = [e.item for e in o.orderItemList]
    if i in iList:
        for e in o.orderItemList:
            if e.item == i:
                if request.args.has_key("update"):
                    e.quantity = quantity
                else:
                    e.quantity = e.quantity + quantity
                o.save()
    else:
        oi = OrderItem(item=i)
        oi.sellerName = i.sellerName
        oi.name = i.name
        oi.priceAtTimeOfSale = i.priceCents
        oi.quantity = quantity
        oi.totalPrice = oi.priceAtTimeOfSale * oi.quantity
        o.orderItemList.append(oi)
        #for oiii in o.orderItemList:
        #    print(oiii.name)
        ls = str(len(o.orderItemList))
        o.save()
        
    g.user.save()

    #for p in getOpenOrders(g.user):
    ##    #print(p.getSellerName())
    ##    #for pi in p.orderItemList:
    ###        print(pi.name)
    
    return redirect(url_for('cart', username = g.user.name) )
#return redirect(url_for('filter', showLast=True) )


@app.route('/remove_from_cart/<order_item_id>')
def remove_from_cart(order_item_id=None):
    if not g.user:
        return redirect(url_for('login'))
    oo = getOpenOrders(g.user)
    removeList = []
    for o in oo:
        #print(o)
        #print(len(o.orderItemList))
        for ii in o.orderItemList:
            
            #print(str(type(ii.seqId)) + "  " + str(type(order_item_id)) + "   " + str(ii.seqId == int(order_item_id)))
            if ii.seqId == int(order_item_id):
                oi = ii
                print("Removing item " + oi.name)
                o.orderItemList.remove(oi)
                o.save()
        if not len(o.orderItemList):
            removeList.append(o)

    for o in removeList:
        #oo.remove(o)
        g.user.openOrderIds.remove(o.id)
    g.user.save()
    return redirect(url_for('cart', username = g.user.name))

@app.route('/<username>/cart')
def cart(username):
    
    # allow to use when not logged in
    #if not g.user:
    #    return redirect(url_for('login'))


    # migrate to mongoengine 0.8
    for o in Order.objects:
        o._mark_as_changed('sponsoredOrg')
        o._mark_as_changed('seller')
        for oi in o.orderItemList:
            oi._mark_as_changed('item')
        o.save()
    
    #g.user.stripeHasCard = False

    msg = ''
    if len(g.user.openOrderIds):
        oo = getOpenOrders(g.user)
        # update items' prices if necessary.
        # also make sure the item still exists!!!
        for o in oo:
            for oi in o.orderItemList:
                #print "open order item seqId: " + str(oi.seqId) 
                try:
                    if  oi.priceAtTimeOfSale != oi.item.priceCents:
                        oi.priceAtTimeOfSale = oi.item.priceCents
                        oi.totalPrice = oi.priceAtTimeOfSale * oi.quantity
                except:
                    # item might be gone
                    msg = "One of the items previously in your cart has been removed by the seller."
                    print("Removing item " + oi.name +" from current order")
                    o.orderItemList.remove(oi)
                    o.save()
    else:
        oo = None

    return render_template('cart.html', username=g.user.name, openOrders=oo,  key=stripe_keys['publishable_key'], msg=msg)


@app.route('/getgeodata', methods=['GET', 'POST'])
def getGeoData():
    if not g.user:
        return redirect(url_for('login'))
    ## check that the user is an admin
    if not g.user.isAdmin:
        return redirect(url_for('index'))

    e  = getGeoData()
    if not e:
        print("Re-generating data")
        generateSampleDB()
        msg = "Just added the zipcode DB remotely. Then re-generated the other data. Nice job."
    else:
        msg = "Msg, zipcodes not imported."
    return redirect(url_for('index', msg=msg))



@app.route('/admin')
def admin():
 
    ## get totals for orgs
    for o in SponsoredOrg.objects:
        o.totalDonated = getTotalSalesForOrg(o)
        o.save()
    
    return render_template('admin.html', o=Order.objects, so=SponsoredOrg.objects)


@app.route('/setblogadmin')
def setBlogAdmin():

    if not g.user:
        return redirect(url_for('login'))
    ## check that the user is an admin
    if not g.user.isAdmin:
        return redirect(url_for('index'))

    b = Seller.objects(name='blogger')[0]
    b.isBlogAdmin = True
    b.save()
    return redirect(url_for('blogAll'))

def processBlogEntryPostData(b, request, u):

        msg = ""
        if not request.form['title']:
            msg = 'Please enter a title for the blog post'
            return render_template('new_blog_entry.html', msg=msg)
        else:
            b.title=request.form['title']
            if request.form['text']:
                b.content = Markup(request.form['text'])

            if request.form['tagStr']:
                ts = request.form['tagStr']
                b.tags = [t.strip() for t in ts.split(',')]
            b.author = u.name

            if request.files.has_key('pic'):
                file = request.files['pic']
                # should check that file is good type
                if file:

                    filename = secure_filename(file.name)
                    s = filename.split('.')
                    if (len(s) > 1):
                        fileroot = filename.split('.')[-2]
                    else:
                        fileroot = filename
                    fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    
                    ## for Django
                    # or self.files['image'] in your form
                    path = default_storage.save(filename, ContentFile(file.read()))
                    fileSaveNameAbs = os.path.join(settings.MEDIA_ROOT, path)


                    filestem = get_fileroot(filename)

                    #file.save(fileSaveNameAbs)
                    fileDirAbs = settings.MEDIA_ROOT #app.config['UPLOAD_FOLDER']
                    fileDirRelative = '' ## app.config['UPLOAD_RELATIVE_FOLDER']
                  
                    b.picPathOrig  = filename
                    
                    # with Image(filename=settings['stat_url']+filename) as image:

                    #     image = Image(filename)
                    #     s = image.size()
                    #     ratio = 200.0 / s[0]
                    #     newsize = (s[0]*ratio, s[1]*ratio)
                    #     ##newimg = image.resize((s[0]*ratio, s[1]*ratio), Image.ANTIALIAS)

                    #     image.thumbnail(newsize, Image.ANTIALIAS)
                    #     normalSizePath = filestem+"_200.jpg"
                    #     image.save(normalSizePath)

                    b.picPath  = filename
                    b.picPathLarge = filename                   

            b.save()
        return msg

def get_fileroot(filename):
    s = filename.split('.')
    if (len(s) > 1):
        fileroot = filename.split('.')[-2]
    else:
        fileroot = filename
    return fileroot




def resizePic(filename):
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename
        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fileSaveNameAbs)
        fileDirAbs = app.config['UPLOAD_FOLDER']
        fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
        ii.picPath = fileDirRelative + '/' + filename
        with Image(filename=fileSaveNameAbs) as img:
            print("The size of the image is")
            print(img.size)
            for r in 1, 2:
                with img.clone() as i:
                    i.resize(int(i.width * r * 0.10), int(i.height * r * 0.10))
                    #i.rotate(90 * r)
                    i.save(filename= fileDirAbs + '/' + fileroot+'_{0}.png'.format(r))
                    #display(i)

            ii.picPath = fileDirRelative + "/" + fileroot + '_1.png'




def new_blog_post_b(*args, **kwargs):
    """Adds a new blog or event post, using WYSIWYG JS code?"""

    if STAND_ALONE:
        u = g.user
        if not g.user:
            return redirect(url_for('login'))
        ## check that the user is an admin
        if not g.user.isAdmin:
            return redirect(url_for('index'))
        
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
        u = getSellerFromOscarID(request.user.id)
        if not g.user.is_staff:
            return redirect(url_for('about'))



    msg = None
    ## POST. Process the form data
    if request.method == 'POST':
        b = BlogPost()
        msg = processBlogEntryPostData(b,request, u=u)
        if not msg:
            if STAND_ALONE:
                flash('You successfully added a new blog post')
            return redirect(url_for('blogAll'))
    

    ## GET ... set up the tags for select2
    tagsses = [bp.tags for bp in BlogPost.objects()]

    ## flatten list
    flattenedTags = [item for sublist in tagsses for item in sublist] 
    ## unique list
    tagsAll = set(flattenedTags)
    clearBlanksFromSet(tagsAll)
    
    return render_template('new_blog_entry.html', msg=msg, tags=tagsAll)
    ##return render_template('wy2.html', msg=msg, tags=tagsAll) 



@app.route('/blog/new', methods=['GET', 'POST'])
def new_blog_post(*args, **kwargs):
    """Adds a new item."""
    if not g.user:
        return redirect(url_for('login'))
    ## check that the user is an admin
    if not g.user.isAdmin:
        return redirect(url_for('blogAll'))

    msg = None
    if request.method == 'POST':
        b = BlogPost()
        msg = processBlogEntryPostData(b,request, u=g.user)
        if not msg:
            flash('You successfully added a new blog post')
            return redirect(url_for('blogAll'))
    
    tagsses = [bp.tags for bp in BlogPost.objects()]

    ## flatten list
    flattenedTags = [item for sublist in tagsses for item in sublist] 
    ## unique list
    tagsAll = set(flattenedTags)
    clearBlanksFromSet(tagsAll)
    
    return render_template('new_blog_entry.html', msg=msg, tags=tagsAll)


def clearBlanksFromSet(s):
    if "" in s:
        s.remove("")
    if " " in s:
        s.remove(" ")
    return

@app.route('/booth/reopen')
def reopenBooth():
    g.user.storeExists = False
    g.user.save()
    return redirect(url_for('register_store'))

@app.route('/blog/<blog_post_id>/delete')
def delete_blog_post(blog_post_id):
    post = BlogPost.objects(seqId=int(blog_post_id))[0]
    deleteFiles([post.picPath, post.picPathLarge, post.picPathOrig], dir =app.config['STATIC_RELATIVE_FOLDER'])
    post.delete()
    return redirect(url_for('blogAll'))

@app.route('/blog/<blog_post_id>/edit', methods=['GET', 'POST'])
def edit_blog_post( *args, **kwargs):

    if STAND_ALONE:
        u = g.user
        if not g.user:
            return redirect(url_for('login'))
        ## check that the user is an admin
        if not g.user.isAdmin:
            return redirect(url_for('index'))
        
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
        u = getSellerFromOscarID(request.user.id)
        if not g.user.is_staff:
            return redirect(url_for('about'))


    blog_post_id = kwargs['blog_post_id']


    post = BlogPost.objects(seqId=int(blog_post_id))[0]
    #deleteFiles([post.picPath, post.picPathLarge, post.picPathOrig], dir =app.config['STATIC_RELATIVE_FOLDER'])
    #post.delete()
    if request.method == 'POST':
        processBlogEntryPostData(post, request, u=u)
        return redirect(url_for('blogAll'))


    tagsses = [bp.tags for bp in BlogPost.objects()]
    ## flatten list
    flattenedTags = [item for sublist in tagsses for item in sublist] 
    ## unique list
    tagsAll = set(flattenedTags)
    clearBlanksFromSet(tagsAll)
 

    return render_template('edit_blog_post.html',bp=post, tags=tagsAll)

@app.route('/blog/<blog_post_id>')
def blog_post(*args, **kwargs):

    if STAND_ALONE:
        u = g.user
        if not g.user:
            return redirect(url_for('login'))
        
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.POST
        g = request
        u = getSellerFromOscarID(request.user.id)
   
    print "meethod"
    print request.method
    if request.method == "POST":
        print request.POST
        if request.form.has_key('delete'):
            blog_post_id = request.form['blog_post_id']
            post = BlogPost.objects(seqId=int(blog_post_id))
            post.delete()
            return redirect(url_for('blogAll'))

    blog_post_id = kwargs['blog_post_id']

    post = BlogPost.objects(seqId=int(blog_post_id))
    #print("working?")
    #print(len(post))
    return render_template('blog.html', blogObjects=post, postNum = 1)

@app.route('/blog')
def blogAll(*args, **kwargs):
    
    if STAND_ALONE:
        try:
            u = g.user
        except:
            u = None
        
    else:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.POST
        g = request
        u = getSellerFromOscarID(request.user.id)

    collection = BlogPost._get_collection()
    #posts = collection.find({"tags":"blog"}).sort('seqId', pymongo.DESCENDING)
    posts = collection.find().sort('seqId', pymongo.DESCENDING)
    #cs = cl.sort('seqId')
    blogList = []
    for c in posts:
        print(c['title'])
        blogList.append(BlogPost.objects(seqId = int(c['seqId']))[0] )
    return render_template('blog.html', blogObjects=blogList, postNum = len(blogList), blogType="News and Events")

@app.route('/about')
def about(*kwargs):
    if not STAND_ALONE:
        from django.http import HttpResponse
        from django.template import RequestContext, Context, loader
        request = kwargs[0]
        t = loader.get_template('about.dj.html')
        c = RequestContext(request, {})
        return HttpResponse(t.render(c), content_type="text/html; charset=UTF-8")

    return render_template("about.html")

@app.route('/aboutCA1616')
def aboutCaliLaw(*args):
    if STAND_ALONE:
        u = g.user
          
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
 
    return render_template("aboutCaliLaw.html")

def bios(*args):
    if STAND_ALONE:
        u = g.user
          
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
 
    return render_template("bios.html")

def resources(*args):
    if STAND_ALONE:
        u = g.user
          
    else:     
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        #request.files = request.FILES
        g = request
 
    return render_template("resources.html")

@app.route('/terms_of_use')
def termsOfUse(*args):

    if not STAND_ALONE:

        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request

    return render_template("termsOfUseStandalone.html")

@app.route('/folks/<seller_name>')
def seller_profile():
    return render_template('index.html')

import string
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

@app.route('/login', methods=['GET', 'POST'])
def loginOld():
    """Logs the user in."""
    #flash("Is this working?")
    #if g.user:
    #    return redirect(url_for('seller_profile'))

    msg = None
    if request.method == 'POST':
        #for s in Seller.objects:
        #    print(s.name)
        #print("---")

        print "logggin "
        print request

        if request.form.has_key('password_reset'):
            if 1:
                if not request.form.has_key('email_to_reset'):
                    msg = 'Please type your email address.'
                    return render_template('login.html', msg=msg)
                user = Seller.objects(email__iexact=request.form['email_to_reset'])[0]
                email = user.email
                newPassword = id_generator()
                user.pw_hash = generate_password_hash(newPassword)
                user.save()
                msgReset = "Hi, " + user.getPersonalNameIfExists() + ", we've reset your password, it is now " + newPassword + ". Please login and change it to one of your choosing by going to 'My account'. Thanks!"  
                subjectReset = "Your " + siteName + " password has been reset"
                emailUser(user, user, subjectReset, msgReset)
                msg = 'A new temporary password was sent to your email address'
                return render_template('login.html', msg=msg)                
            else:
                msg = 'Email not found. Are you sure you have an account?'
                return render_template('login.html', msg=msg)

        if not request.form['username']:
            msg = 'Invalid username'
            return render_template('login.html', msg=msg)
        try:
            user = Seller.objects(name__iexact=request.form['username'])[0]
        except:
            # email?
            try:
                user = Seller.objects(email__iexact=request.form['username'])[0]
            except:
                msg = 'Invalid username or password'
                return render_template('login.html', msg=msg)

        if not check_password_hash(user.pw_hash, request.form['password']):
            msg = 'Invalid username or password'
        else:
            flash('You were logged in')
            session['user_id'] = user.name
            return redirect(url_for('index'))
    if request.args.has_key('name'):
        name= request.args['name']
    else:
        name = ""
    if request.args.has_key('msg'):
        msg= request.args['msg']
    return render_template('login.html', msg=msg, name=name)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    #if g.user:
    #    return redirect(url_for('timeline'))
    msg = None
    if request.method == 'POST':
        import re
        if not request.form['username']:
            msg = 'Please enter a username'

        elif re.match('^[\w-]+$', request.form['username'] ) is None:
             msg = 'Please enter a username containing only letters and numbers'
        elif not request.form['email'] or '@' not in request.form['email']:
            msg = 'Please enter a valid email address'
        elif not request.form['password']:
            msg = 'Please enter a password'
        elif request.form['password'] != request.form['password2']:
            msg = 'The two passwords do not match'
        elif Seller.objects(name__iexact=request.form['username']).first() is not None:
            msg = 'The username is already taken'
        else:
            dr = Seller(name=request.form['username'])
            dr.email = request.form['email']
            dr.pw_hash =  generate_password_hash(request.form['password'])
            #dr.storeExists= False
            dr.save()
            flash('You were successfully registered and can login now')
            msg = 'You were successfully registered and can login now'
            
            try:
                adminUser = Seller.objects.filter(name=app.config['ADMIN_USERNAME']).first()
            except:
                adminUser = dr
            msgStr = ''
            if dr.getFirstName():
                msgStr = "Hi " + dr.getFirstName() + ", w"
            else:
                msgStr = "W"
            msgStr += "e're glad you've joined this community of folks that care about where their food is coming from. We hope you find something on Homemade 1616 that you like, please let us know if you have any ideas or comments. "
            emailUser(dr, adminUser, "Welcome to Homemade 1616", msgStr)

            return redirect(url_for('login', name=dr.name, msg=msg))
    return render_template('register_alpha.html', msg=msg)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect(url_for('index', msg="You were logged out"))

@app.route('/edit_store', methods=['GET', 'POST'])
def edit_store(*args, **kwargs):

    return redirect(url_for('register_store' ))

    ##register_store(args[0], template = "edit_store.html")


@app.route('/register_store', methods=['GET', 'POST'])
def register_store(*args, **kwargs):
    """Registers a store for the user."""

    if STAND_ALONE:
        u = g.user
        if not g.user:
            return redirect(url_for('login'))
        if g.user.storeExists:
            return redirect(url_for('store', store_name=g.user.name))

    else:   
        ## can put this in a decorator?
        #cf = inspect.currentframe()
        #pf = cf.f_back
        #request=pf.f_locals['request']
        #print args[0]
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request
        user = request.user
        storeExists = False
        partner = None

        ## make sure is authenticated
        if not user.id:
            messages.success(request, "Please login or register to begin the selling setup process.")
            return redirect(url_for('customer:login') + "?next=" + "/homemade/register_store/")

        try:
            if user.partner:
                storeExists = True
                partner = user.partner
        except:
            pass


        try:
            u = getSellerFromOscarID(request.user.id)
        except:
            u = None
        #if storeExists: 
        #template = "edit_store.html"
        #else:
        template = "edit_store.html"



    msg = None
    if request.method == 'POST':
        storeName = None
        zipcode = None
        bio = None
        if u:
            if request.args.has_key("termsCheck"):
                if request.args['termsCheck'] == "on":
                    u.agreedToTerms = True
                    u.save()
                elif request.args['termsCheck'] == "off":
                    u.agreedToTerms = False
                    u.save()

        print request.form
        if request.form['store_name']:

            storeName =  request.form['store_name']
            #u.save()
        #if request.form["county"]:
        #    u.county = request.form["county"]
        #else:
        #    msg = "Please enter your county of residence. " 
        #    return render_template(template, u=u, msg=msg, counties = Counties.objects())

        ## for debugging uncomment the next line
        #return render_template('register_store.html', u=u, msg=msg, counties = Counties.objects())

        #if request.form['permitType']:
        #    u.permitType = request.form['permitType']
        #else:
        #    msg = "Please select the type of sellers permit that you have. " 
        #    return render_template('register_store.html', msg=msg)
        if request.form['zipcode']:
            try:
                #zcObj = zcdb[request.form['zipcode']]
                #lt = zcObj.latitude
                #ll = zcObj.longitude
                #u.latCoarse = lt
                #u.longCoarse = ll
                zipcode = request.form['zipcode']
            except:
                msg = "Invalid zipcode."
                return render_template(template, u=u, partner=partner, msg=msg)

        storePicPath = None
        if request.files.has_key('store_pic') and request.files['store_pic'] != '':

            #if request.form.has_key('h') and request.form['h'] != '':
            ## do this fo all cases now since not cropping at the moment
            storePicPath = getPicJCrop(u, 'store_pic', request)
            #else:
            #    getStorePic(u, request)


        if request.form.has_key('bio'):
            #if request.form['bio'] != u.bio:
            bio = request.form['bio']

        if u:
            u.storeExists = True

            u.save()


        ## create a partner
        boothIsNew = False
        try:
            partner = Partner.objects.filter(user=request.user)[0]
        except:
            boothIsNew = True
            partner = Partner.objects.create(name=storeName)
        if u:
            partner.code = u.id
        #partner.name = u.storeName
        partner.user = request.user
        partner.users.add(request.user)
        partner.name = storeName
        partner.zipcode = zipcode
        partner.bio = bio
        if storePicPath:
            partner.picPath = storePicPath

        partner.save() 

        ## set the partner address ?? 

        ## email the user about their new booth
        if boothIsNew:
            emailAboutNewBooth(request)

        # flash('Your booth was successfully registered')
        #return redirect(url_for('termsOfUse', store_name=u.name))

        ## if no payment credentials, set those up
        if not partner.stripeToken or not partner.stripePubKey:
            return redirect(url_for('stripe_connect_signup'))
        ## otherwise go to the booth page
        return redirect(url_for('catalogue:index', booth=partner.id))


    # if not STAND_ALONE:
    #     from django.http import HttpResponse
    #     from django.template import RequestContext, Context, loader
    #     #request = args[0]
    #     t = loader.get_template('register_store.dj.html')

    #     ## emulate Flask global object
        
    #     c = RequestContext(request, {'g':request, 'du':request.user, 'u':Seller.getSellerFromOscarID(request.user.id), 'msg':msg, 'counties':Counties.objects()})
    #     #c = RequestContext(request, {uuu:None, msg:msg, counties:Counties.objects()})
    #     return HttpResponse(t.render(c), content_type="text/html; charset=UTF-8")
    
    return render_template(template, u=u, partner=partner, msg=msg)


def emailAboutNewBooth(request):
    ctx = {
        'user': request.user,
        #'muserTo': mu,
        #'subject': subject,
        'site': get_current_site(request),

    }
    Dispatcher = get_class('customer.utils', 'Dispatcher')
    CommunicationEventType = get_model('customer', 'CommunicationEventType')

    msgs = CommunicationEventType.objects.get_and_render(
        code="STORE_REGISTRATION", context=ctx)
 
    Dispatcher().dispatch_user_messages(request.user, msgs, None)

    #emailUser(adminUser, sender=sender, subject=subject, msgStr=msg)
    messages.info(request, "You have successfully created your booth.")


@app.route('/info/general')
def permitInfo(zipcode=None):
        
    blogEntryAboutPermits = BlogPost.objects(tags__in=['info'])
    return render_template('blog.html', blogObjects=blogEntryAboutPermits, postNum = len(blogEntryAboutPermits))


@app.route('/articles')
def filterPosts():

    if request.args.has_key('tags'):
        tags =  request.args['tags'].split('+')
    blogEntriesWithTags = BlogPost.objects(tags__in=tags)
    return render_template('blog.html', blogObjects=blogEntriesWithTags, postNum = len(blogEntriesWithTags))

@app.route('/events')
def showEvents(*args, **kwargs):

    if STAND_ALONE:
        try:
            u = g.user
        except:
            u = None
        
    else:
        request = args[0]
        g = request
        u = getSellerFromOscarID(request.user.id)

    collection = BlogPost._get_collection()
    posts = collection.find({"tags":"blog"}).sort('seqId', pymongo.DESCENDING)
    blogEntriesWithTags = BlogPost.objects(tags__in=['event','events']).order_by("-id")
    return render_template('blog.html', blogObjects=blogEntriesWithTags, postNum = len(blogEntriesWithTags), blogType="Events")

@app.route('/events/filter')
def filterEvents(*args, **kwargs):
      
    if not STAND_ALONE:
        request = args[0]
        request.args = request.GET

    tagList = []
    if request.method == 'GET' and request.args:
        tags = request.args.keys()
        for tag in tags:
            tagList.append(tag)
    #blogEntriesWithTags = BlogPost.objects(tags__in=['event','events']).filter(tags__in=tagList).order_by("-id")
    blogEntriesWithTags = BlogPost.objects(tags__in=tagList).filter(tags__in=tagList).order_by("-id")
    #for b in BlogPost.objects:
    #    print b.tags
    blogType = 'News, Information, and Events'
    if len(tagList):
        t = tagList[0]
        if 'swap' in tagList:
            blogType = "Food Swaps"
        elif "workshop" in tagList:
            blogType = "Workshops"
        elif "event" in tagList or 'events' in tagList:
            blogType = "Events"


    return render_template('blog.html', blogObjects=blogEntriesWithTags, postNum = len(blogEntriesWithTags), blogType=blogType)

@app.route('/wander/filter')
def filter():

    if request.method == 'GET':
        iList = Item.objects

        argsOldAndNew = {}
        for i in request.args.keys():
            argsOldAndNew[i] = request.args[i]

        # add last filters to new, if showLast argument given. This can be used for returning to a search
        if request.args.get('showLast') and  session.has_key('browseLastArgs'):
            oldArgs = session['browseLastArgs']
            if oldArgs:
                for k in oldArgs.keys():
                    if k not in request.args.keys():
                        argsOldAndNew[k] = oldArgs[k]

        
        if argsOldAndNew.get('category'):
            print("Filtering by category " +  argsOldAndNew['category'] )
            iList = iList(category=argsOldAndNew.get('category'))

        if argsOldAndNew.get('search_string'):
            ss = argsOldAndNew.get('search_string')
            iList= Item.objects(name__icontains=ss)
            #iList = Item.objects(Q(name__icontains=ss) | Q(category__icontains=ss))
            #iList = iList + Item.objects(category__icontains=ss)
            #iList = iList + Page.objects(__raw__={'name': /^bar$/i })
            #sList = Item.objects(sellerName__contains=ss)
            #dList = Item.objects(description__contains=ss)

        if argsOldAndNew.get('radius'):
            print("See radius of " + argsOldAndNew.get('radius'))
            radius = argsOldAndNew.get('radius')
        else:
            radius = 20

        if not argsOldAndNew.get('zipcode') and argsOldAndNew.get('radius'):
            msg = "Location search cannot be done without a valid zipcode."
            #return render_template("browse_items.html", iList=iList, msg=msg)
        elif argsOldAndNew.get('zipcode'):
            zc = argsOldAndNew.get('zipcode')
            print("Found zipcode? " + zc)
            zCoords = getCoordsFromZipcode(zc)
            print("Found zipcode coods? " + str(zCoords))
            if zCoords:
                iList = getAllItemsWithinRadius(zCoords, radius, iList)
            else:
                msg = "Invalid zipcode"
                iList = []

    
        session['browseLastArgs'] = argsOldAndNew



    # limit hack
    iList = iList[:30]
    argStr = ["" + c + "=" + request.args[c]  for c in request.args.keys()]
    argStr = ','.join(argStr)
    if argsOldAndNew.get('view'):
        if argsOldAndNew.get('view') == 'list':
            return render_template("browse_items_as_list.html", iList=iList, cList=getCategories(), aarghs=request.args, argStr = argStr)
    return render_template("browse_items.html", iList=iList, cList=getCategories(), aarghs=request.args, argStr=argStr)

@app.route('/test/')
def filterTest():

    iList = Item.objects
    return render_template("browse_items_as_list.html", iList=iList,cList = getCategories())

@app.route('/wander/all_items')
def browse_items_grid():
    
    start = 0
    end = 24
    perPage = 24
    try:
        if request.args:
            args = request.args
            if args.has_key('start'):
                start = int(args['start'])
            if args.has_key('end'):
                end = int(args['end'])
            if args.has_key('page'):
                page = int(args['page'])
                start = (page -1) * perPage
                end = (page * perPage)
    except:
        pass
        
            

    iList = Item.objects.order_by("-id")
    if g.user and g.user.zipcode:
        zipcode=g.user.zipcode
    else:
        zipcode=""
    
    session['browseLastArgs'] = []
    favList = None
    if g.user:
        idList = g.user.favItemList
        favList = Item.objects(id__in=idList)
    
    iList = iList[start:end]

    return render_template("browse_items.html", iList=iList, favList=favList, zipcode=zipcode, cList = getCategories())


@app.route('/wander/grab_bag')
def grabBag(iList=Item.objects):

    #iList = Item.objects
    if g.user and g.user.zipcode:
        zipcode=g.user.zipcode
    else:
        zipcode=""
    
    session['browseLastArgs'] = []
    favList = None
    if g.user:
        idList = g.user.favItemList
        favList = Item.objects(id__in=idList)

    sampleNum = 12
    if sampleNum > len(iList):
        sampleNum = len(iList)
    iList = random.sample(iList, sampleNum)

    return render_template("browse_items.html", iList=iList, favList=favList, zipcode=zipcode, cList = getCategories())

@app.route('/wander/all_items_list')
def browse_items_list():

    iList = Item.objects
    session['browseLastArgs'] = []
    favList = None
    if g.user:
        idList = g.user.favItemList
        favList = Item.objects(id__in=idList)

    iList = iList[:30]
    return render_template("browse_items_as_list.html", iList=iList,favList=favList, cList = getCategories())

@app.route('/items/<item_id>', methods=['GET','POST'])
def item(item_id = None):

    if request.method == 'POST':
        #    if request.args.get('delete'):

        try:
            it = Item.objects(id=item_id).first()
            print("Deleting " + it.name)
            it.delete()
        except:
            ids = str(item_id)
            msg = "Item " + ids +"not found"
            #return render_template('store.html', msg=msg)
            return redirect(url_for('store', store_name=g.user.name, msg=msg))

        return redirect(url_for('store', store_name=g.user.name))
            

    try:
        it = Item.objects(id=item_id).first()



        store_name = it.sellerName
        #return render_template("item.html", i=it)
        #print("in item, id=" + it.name)
        ## in case using API
    
        sellerDB = Seller.objects(name=it.sellerName)[0]
    except:
        msg = "Item " + str(item_id) +"not found"
        return redirect(url_for('browse_items_grid'))

    # is item already in the cart?
    numInCart = 0
    if g.user:

        try:
            oo = getOpenOrders(g.user)
        except:
            g.user.openOrderIds = None
            g.user.save()

        oo = getOpenOrders(g.user)
        #iList = [oi.item for oi in oo.orderItemList]
        if oo:
            for o in oo:
                oi = None
                if o.getSellerName() == it.sellerName:
                    for oiTemp in o.orderItemList:
                        #print(it.name + "  " + oiTemp.item.name)
                        if it == oiTemp.item:
                            oi = oiTemp
                            numInCart = oi.quantity
                            #print "numInCart " + str(numInCart)
    # print("request")
    # print(request)
    
    return render_template("item_delete_test.html", i=it, storeName=store_name, sellerObj=sellerDB, numInCart=numInCart)


@app.route('/pick_sponsored_org')
def pick_sponsored_org(sponsored_org=None, orderSeqId=None):
    """Sets the sponsored organization for this session/transaction"""
    
    if not g.user:
        return redirect(url_for('login'))

    sponsored_org = request.args['sponsoredOrg']
    orderSeqId = int(request.args['orderSeqId'])

    if not len(g.user.openOrderIds):
        return redirect(url_for('cart', username=g.user.name))
    try:
        so = SponsoredOrg.objects(name=sponsored_org)[0]
    except:
        print("No sponsored organization by the name of " + sponsored_org)
    try:
        o = Order.objects.filter(seqId=orderSeqId)[0]
    except:
        msg = "No such order, " + str(orderSeqId)
        print("ERROR: " + msg)
        return redirect(url_for('cart', username = g.user.name, msg=msg))

    o.sponsoredOrg = so
    o.save()

    return redirect(url_for('cart', username = g.user.name))

@app.route('/repick_sponsored_org/',  methods=['GET', 'POST'])
def repick_sponsored_org(openOrderSeqId=None):
    """Resets the sponsored org for this session/transaction/order"""
    if not g.user:
        return redirect(url_for('login'))

    try:
        ooSeqId = int(request.args['openOrderSeqId'])
    except:
        msg = "No order specified"
        return redirect(url_for('index', msg=msg))
     
    if len(g.user.openOrderIds):
        try:
            oo = Order.objects(seqId=ooSeqId).first()
        except:
            msg = "Can't find that order"
            return redirect(url_for('index', msg=msg))
            
        oo.sponsoredOrg= None
        oo.save()
        
    return redirect(url_for('cart', username = g.user.name))


#@app.route('/show/<filename>')
#def uploaded_file(filename):
#    filename = 'http://127.0.0.1:5000/uploads/static' + filename
#    return render_template('test_image.html', filename=filename)

@app.route('/uploads/<filename>')
def send_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        # should check that file is good type
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #return redirect(url_for('uploaded_file', filename=filename))
            return redirect(url_for('index'))

    return '    <!doctype html>    <title>Upload new File</title>    <h1>Upload new File</h1>    <form action="" method="post" enctype=multipart/form-data> <input type="file" file name="file">  <input type="submit" value="Upload">    </form>    '
        #return redirect(url_for('/blog')

@app.route('/new_item', methods=['GET', 'POST'])
def new_item():

    """Adds a new item."""
    if not g.user:
        return redirect(url_for('login'))
    if not g.user.storeExists:
        return redirect(url_for('register_store'))
    msg = None
    if request.method == 'POST':
        if not request.form['name']:
            msg = 'Please enter a product name'
        else:
            ii = Item(name=request.form['name'])
            #print("In new_item")
            #print(g.user.name)
            ii.slug = generate_password_hash(ii.name)
            #print(ii.slug)
                
            #print(request.form)
            if request.form['priceInDollars']:
                ii.priceCents = int(float(request.form['priceInDollars']) * 100) 
            else:
                msg = "Please enter a price for the item."
                return render_template('new_item.html', msg=msg)
            ii.sellerName = g.user.name
            ii.storeName = g.user.storeName
            #print(ii.sellerName)
            if request.form['description']:
                ii.description =  request.form['description']
                #print("done with descript")
            if request.form.has_key('tagStr'):
                ts = request.form['tagStr']
                ii.tags = [t.strip() for t in ts.split(',')]
            if request.form['inventory']:
                ii.inventory =  request.form['inventory']
            if request.form['categoryChoice']:
                try:
                    ii.category = request.form['categoryChoice']
                except:
                    print("Problem choosing a category")
            if request.form.has_key('lat') and request.form.has_key('long'):
                ii.geoCoords =  [request.form['lat'], request.form['long'] ]
            else:
                if g.user.zipcode:
                    try:
                        loc = HMGeoData.objects(zipcode=g.user.zipcode)[0]
                        ii.locCoords = loc.locCoords
                    except:
                        print("Problem getting zipcode coordinates")
                        
            try:
                file = request.files['pic']
            except:
                print("No file in form data.")
                file = None
            # should check that file is good type
            if file:
                filename = secure_filename(file.filename)
                s = filename.split('.')
                if (len(s) > 1):
                    fileroot = filename.split('.')[-2]
                else:
                    fileroot = filename
                fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(fileSaveNameAbs)
                fileDirAbs = app.config['UPLOAD_FOLDER']
                fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
                ii.picPathOrig = fileDirRelative + '/' + filename
                ii.picPath = fileDirRelative + '/' + filename                

                createImgSizes(fileSaveNameAbs, dbObj=ii, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=200)
                ## can upload this to AWS S3?
                print([ii.picPath, ii.picPathLarge])
                uploadPicsToS3([ii.picPath, ii.picPathLarge], dir=app.config['STATIC_FOLDER'])
                
            ii.save()
            g.user.itemIds.append(ii.id)
            g.user.save()
            flash('You successfully added a new item')
            return redirect(url_for('store',store_name=g.user.name))
        #return redirect(url_for('index'))
    tagsses = [t.tags for t in Item.objects()]
    ## flatten list
    flattenedTags = [item for sublist in tagsses for item in sublist] 
    ## unique list
    tagsAll = set(flattenedTags) 
    clearBlanksFromSet(tagsAll)
    
    return render_template('new_item.html', msg=msg, categories=[c.name for c in Categories.objects(name__ne="Other")], tags=tagsAll)


def getPicFileUpload(request, ii):
    """ ii is Item object
    request is web request
    """
    try:
        file = request.files['pic']
    except:
        print("No file in form data.")
        file = None
    # should check that file is good type
    if file:
        filename = secure_filename(file.filename)
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename
        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fileSaveNameAbs)
        fileDirAbs = app.config['UPLOAD_FOLDER']
        fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
        ii.picPath = fileDirRelative + '/' + filename
        with Image(filename=fileSaveNameAbs) as img:
            print("The size of the image is")
            print(img.size)
            for r in 1, 2:
                with img.clone() as i:
                    i.resize(int(i.width * r * 0.10), int(i.height * r * 0.10))
                    #i.rotate(90 * r)
                    i.save(filename= fileDirAbs + '/' + fileroot+'_{0}.png'.format(r))
                    #display(i)

            ii.picPath = fileDirRelative + "/" + fileroot + '_1.png'


def processPic(file):
    # should check that file is good type
    if file:
        filename = secure_filename(file.filename)
        s = filename.split('.')
        if (len(s) > 1):
            fileroot = filename.split('.')[-2]
        else:
            fileroot = filename
        fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(fileSaveNameAbs)
        fileDirAbs = app.config['UPLOAD_FOLDER']
        fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
        ii.picPath = fileDirRelative + '/' + filename
        ii.picPathOrig = fileDirRelative + '/' + filename
        createImgSizes(fileSaveNameAbs, dbObj=ii, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=200)
        ## can upload this to AWS S3?
        print([ii.picPath, ii.picPathLarge])
        uploadPicsToS3([ii.picPath, ii.picPathLarge], dir=app.config['STATIC_FOLDER'])

        return


@app.route('/set_invite_pic/')
def setInvitePic():

    print request.args
    try:
        item_id = request.args['item_id']
        pos = request.args['position']
    except:
        pos = None
        item_id = None
        pass
    if not g.user or not g.user.isAdmin or not item_id or not pos:
        return redirect(url_for('index'))

    
    if not pos:
        print "no pos"
        return redirect(url_for('item', item_id=i.id))
    else:
        print "pos = " + pos
    i = Item.objects(id=item_id)[0]
    gp = GlobalPics.objects()[0]
    pd = gp.picDict
    pd[pos] = i.picPath
    gp.save()
    return redirect(url_for('item', item_id=i.id))

@app.route('/set_item_collagable/<item_id>')
def set_item_collageable(item_id=None, collageable=None):

    if not g.user or not g.user.isAdmin or not item_id:
        return redirect(url_for('index'))
        
    i = Item.objects(id=item_id)[0]
    if not i.isCollageable:
        i.isCollageable = True
    else:
        i.isCollageable = False

    i.save()
    return redirect(url_for('item', item_id=i.id))

@app.route('/set_item_collagable_portrait/<item_id>')
def set_item_as_collage_portrait(item_id=None, collagePortrait=None):

    if not g.user or not g.user.isAdmin or not item_id:
        return redirect(url_for('index'))
        
    i = Item.objects(id=item_id)[0]
    if not i.collagePortrait:
        i.collagePortrait= True
    else:
        i.collagePortrait = False
    i.save()
    return redirect(url_for('item', item_id=i.id))

@app.route('/edit_item_form/<item_id>', methods=['GET', 'POST'])
def edit_item_form(item_id=None):
    """Edits an existing item."""

    if not g.user:
        return redirect(url_for('login'))
    msg = None
    if request.method == 'POST':
        if not request.form['name']:
            msg = 'Please enter a product name'
        else:
            if item_id != None:
                #print(request.form)
                ii = Item.objects(id=item_id)[0]
                #print(g.user.name)
                ii.name =  request.form['name']
                if request.form['descriptionblock']:
                    ii.description =  request.form['descriptionblock']
                    if len(ii.description) == 0 or ii.description == 'None':
                        ii.description = None
                if request.form['inventory']:
                    ii.inventory =  request.form['inventory']
                if request.form['priceInDollars']:
                    ii.setPriceFromDollarsToCents(request.form['priceInDollars'])
                if request.form['categoryChoice']:
                    print("category chosen to be " + str(request.form['categoryChoice']))
                    try:
                        ii.category = request.form['categoryChoice']
                    except:
                        print("Problem choosing a category")
                if request.form['tagStr']:
                    ts = request.form['tagStr']
                    ii.tags = [t.strip() for t in ts.split(',')]
                
                try:
                    file = request.files['pic']
                except:
                    print("No file in form data.")
                    file = None
                # should check that file is good type
                if file:
                    filename = secure_filename(file.filename)
                    s = filename.split('.')
                    if (len(s) > 1):
                        fileroot = filename.split('.')[-2]
                    else:
                        fileroot = filename
                    fileSaveNameAbs = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(fileSaveNameAbs)
                    fileDirAbs = app.config['UPLOAD_FOLDER']
                    fileDirRelative =  app.config['UPLOAD_RELATIVE_FOLDER']
                    ii.picPath = fileDirRelative + '/' + filename
                    ii.picPathOrig = fileDirRelative + '/' + filename
                    createImgSizes(fileSaveNameAbs, dbObj=ii, fileroot=fileroot, fileDirAbs=fileDirAbs, fileDirRelative = fileDirRelative, optimalPixelWidth=200)
                    ## can upload this to AWS S3?
                    print([ii.picPath, ii.picPathLarge])
                    uploadPicsToS3([ii.picPath, ii.picPathLarge], dir=app.config['STATIC_FOLDER'])
 
                ii.save()
                
                flash('You successfully edited your item')
                return redirect(url_for('store',store_name=g.user.name))
            else:
                msg = 'There is a problem with the website.'

        #return redirect(url_for('index'))
    try:
        i = Item.objects(id=item_id)[0]
    except:
        msg = "No item " + str(item_id)
        return render_template('index.html', msg=msg)

    if i.category:
        categories=Categories.objects(name__ne=i.category)
        categories = [c.name for c in Categories.objects(name__ne=i.category)]
    else:
        categories = [c.name for c in Categories.objects(name__ne="Other")]
    
    tagsses = [t.tags for t in Item.objects()]
    ## flatten list
    flattenedTags = [item for sublist in tagsses for item in sublist] 
    ## unique list
    tagsAll = set(flattenedTags) 
    clearBlanksFromSet(tagsAll)
    
    return render_template('edit_item.html', msg=msg, i=i, categories=categories, tags=tagsAll )


def intify(num):
    return int(floor(float(num)))

def scaleImageFromJCrop(request, fileOrig, fileroot, fileDirAbs, fileDirRelative, optimalPixelWidth=200):
    """Saves a single image, returns the path 
    Uses the parameters from JCrop in the request
    """

    f = request.form

    x1 = intify(f['x1'])
    x2 = intify(request.form['x2'])
    y1 = intify(request.form['y1'])
    y2 = intify(request.form['y2'])
    w = intify(f['w'])
    h = intify(f['h'])
    filedim = f['filedim']
        
    with Image(filename=fileOrig) as img:
        with img.clone() as i:
            scale = float(optimalPixelWidth) / float(w)
            width = optimalPixelWidth
             
            i = img[x1:x2, y1:y2]
             
            i.resize(width, int(h * scale))
            if width > 300:
                extension = "jpg"
            else:
                extension = "jpg"
            f = fileroot+'_{0}.'.format(int(optimalPixelWidth)) + extension
            fn = f
            if fileDirAbs != '':
                fn = fileDirAbs + '/' + f
            i.save(filename=fn)

            newImgPath = f        
            if fileDirRelative != '':
                newImgPath = fileDirRelative + '/' + f

    return newImgPath


def scaleImage(fileOrig, fileroot, fileDirAbs, fileDirRelative, optimalPixelWidth=200):
    """Saves a single image, returns the path """
    with Image(filename=fileOrig) as img:
        with img.clone() as i:
            scale = float(optimalPixelWidth) / float(i.width)
            width = optimalPixelWidth 
            i.resize(width, int(i.height * scale))
            if width > 300:
                extension = "jpg"
            else:
                extension = "jpg"
            f = fileroot+'_{0}.'.format(int(optimalPixelWidth)) + extension
            fn = fileDirAbs + '/' + f
            i.save(filename=fn)
            newImgPath = fileDirRelative + '/' + f

    return newImgPath

def createImgSizes(fileOrig, dbObj, fileroot, fileDirAbs, fileDirRelative, optimalPixelWidth=200):

     with Image(filename=fileOrig) as img:
            print("The size of the image is")
            print(img.size)
            for r in 1, 2:
                with img.clone() as i:
                    scale = float(optimalPixelWidth) / float(i.width)
                    print("debug image")
                    print(scale)
                    print(i.height)
                    print(int(i.height * r * scale))
                    print(i.height * r * scale)
                    width = optimalPixelWidth * r
                    i.resize(width, int(i.height * r * scale))
                    #i.rotate(90 * r)
                    if width > 300:
                        extension = "jpg"
                    else:
                        extension = "jpg"
                    f = fileroot+'_{0}.'.format(int(r*200)) + extension
                    fn = fileDirAbs + '/' + f
                    if r == 1:
                        dbObj.picPath = fileDirRelative + '/' + f
                    if r == 2:
                        dbObj.picPathLarge = fileDirRelative + '/' + f
                        dbObj.picPath = fileDirRelative + '/' + f
                                                
                    dbObj.save()
                    print("SAVING " + fn)
                    i.save(filename= fn )
                    #display(i)

import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key

def uploadPicsToS3(picList, dir):
    s3user = os.environ['S3_USER'] 
    s3pw = os.environ['S3_PASSWORD'] 
    conn = S3Connection(s3user, s3pw)
    bucket = conn.create_bucket(app.config['S3_BUCKET_NAME'])
    for picPath in picList:
        print("Here is where I am uploading " + str(picPath))
        k = Key(bucket=bucket)
        k.key='static/' + picPath
        filePath = dir + '/' + picPath
        print('static/' + picPath)
        print(filePath)
        k.set_contents_from_filename(filePath)
        k.make_public()
    return "Success"

def deleteFiles(picPathList, dir):
    s3user = os.environ['S3_USER'] 
    s3pw = os.environ['S3_PASSWORD'] 
    conn = S3Connection(s3user, s3pw)
    bucket = conn.create_bucket(app.config['S3_BUCKET_NAME'])
    for picPath in picPathList:
        if picPath:
            k = Key(bucket=bucket)
            k.key=dir + '/' + picPath
            bucket.delete_key(k)
    return "Success"


################
## Stripe stuff


  
@app.route('/charge', methods=['POST'])
def charge():
    if not g.user:
        return redirect(url_for('login'))
    print "in charge()"

    try:
        orderSeqId = request.form['orderSeqId']
        o = Order.objects(seqId=int(orderSeqId))[0]
    except:
        msg = "No order with ID " + str(orderSeqId)
        print("ERROR: " + msg)
        return redirect(url_for('index',msg=msg))

    if not o.sponsoredOrg:
        msg = "Please choose an organization to sponsor before paying."
        return redirect(url_for('cart',msg=msg))

    amount = o.getCurrentTotalCents()
    amountDollars = o.getCurrentTotalStringInDollars()

    useStripe = False
    if useStripe:
        customer = stripe.Customer.create(
            email='customer@example.com',
            card=request.form['stripeToken']
            )
        
        charge = stripe.Charge.create(
            customer=customer.id,
            amount=amount,
            currency='usd',
            application_fee=int(floor(int(amount) * 0.035)), # amount in cents
            description='Flask Charge'
            )

    orderSuccess(g.user, o)
 
    return render_template('charge.html', amount=amount, amountDollars=amountDollars, order=o)

def tokenDecoder(response):

    res = json.loads(response)
    #print "result from Stripe"
    
    #print res
    return res

@app.route('/stripe_login')
def stripeLogin(*args):

    if not STAND_ALONE:
        request = args[0]
        g = request

    if not g.user:
        return redirect(url_for('login'))

    #redirect_uri = url_for('stripeAuthorized', _external=True)
    #params = {'redirect_uri': redirect_uri, 'response_type':'code', 'scope':'read_write', 'state':'1234'}


    ##return redirect(stripeAuth.get_authorize_url(**params))

    ## if testing then go to test redirect URL

    try:
        if settings.TEST_LOCAL:
            testStripeRedirect = "http://localhost:8081/homemade/stripe_authorized/"
            return redirect("https://connect.stripe.com/oauth/authorize?redirect_uri=" + testStripeRedirect +"&response_type=code&scope=read_write&client_id="+app.config['stripe_client_id'])
    except:
        pass

    return redirect("https://connect.stripe.com/oauth/authorize?response_type=code&scope=read_write&client_id="+app.config['stripe_client_id'])



@app.route('/stripe_connect_signup')
def stripe_connect_signup(*args):
    

    if STAND_ALONE:
        if not g.user:
            return redirect(url_for('login'))
        u=g.user

    else:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        request.files = request.FILES
        g = request        
        sellerObj = getSellerFromOscarID(request.user.id)


    return render_template('stripe_connect_signup.html', partner=request.user.partner)


PROCESS_TOKEN_ERROR = ('Decoder failed to handle {key} with data as returned '
                       'by provider. A different decoder may be needed. '
                       'Provider returned: {raw}')


def process_token_request(r, decoder, *args):

    try:
        data = decoder(r.content)
        return tuple(data[key] for key in args)
    except KeyError, e:  # pragma: no cover
        bad_key = e.args[0]
        raise KeyError(PROCESS_TOKEN_ERROR.format(key=bad_key, raw=r.content))

    
@app.route('/stripe/authorized')
def stripeAuthorized(*args):

    if not STAND_ALONE:
        request = args[0]
        request.args = request.GET
        request.form = request.POST
        g = request

        u = getSellerFromOscarID(request.user.id)

    print "was redirected from Stripe"
    print "request "
    print request
    print request.args
    if not g.user:
        return redirect(url_for('login'))
    

    # check to make sure the user authorized the request
    if not 'code' in request.args:
        msg = 'You did not authorize the request'
        return redirect(url_for('catalogue:index'))

    # make a request for the access token credentials using code
    data = {'redirect_uri': '', 'code':request.args['code'], 'grant_type':'authorization_code'}
    
    ## note that pub key is set here?
    #token = stripeAuth.get_access_token(data=data, decoder=tokenDecoder, method='POST')
    r = stripeAuth.get_raw_access_token(data=data, method='POST')


    key = 'access_token'
    access_token, stripe_user_id, stripe_publishable_key = process_token_request(r, tokenDecoder, 'access_token', 'stripe_user_id', 'stripe_publishable_key')
    
    
    #print "DEBUG" 
    #print stripe_user_id
    #print "DEBUG over"
    
    if u:
        u.stripeSellerID = stripe_user_id
        #if not g.user.stripeID:
        #    cust = stripe.Customer.create(
        #        description=g.user.email
        #        )    
        #    g.user.stripeID = cust.id    

        # saved the token and ID for later payments to this user's account
        u.stripeSellerToken = access_token
        u.stripeSellerPubKey = stripe_publishable_key  # this is set during the get_access_token call, in tokenDecoder
        u.save()

    ## save to Oscar partner
    ou = request.user
    partner = ou.partner
    partner.stripePubKey = stripe_publishable_key
    partner.stripeToken = access_token
    partner.save()


    #print "pub ,secret: "
    #print g.user.stripePubKey
    #print g.user.stripeAccountToken
    
    # Create a Token from the existing customer on the application's account
    #t = stripe.Token.create(
    #    customer=cust.id,
    #    api_key=token # SELLER's access token from the Stripe Connect flow
    #    )

    #print t
    
    #User.get_or_create(me['username'], me['id'])

    #flash('Logged in as ' + me['name'])
    #return redirect(url_for('catalogue:index', booth=u.storeName))

    ## is there a default store address already? If so just go straight to booth

    try:
        defaultAddress = UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_store')[0]
        if defaultAddress:
            return redirect(url_for('catalogue:index', booth=partner.id))
    except:
        pass
    return redirect(url_for('customer:store-shipping-options'))


@app.route('/stripe_info')
def stripeInfo():
    if not g.user:
        return redirect(url_for('login'))
    return render_template('stripe_info.html')

# @app.route('/charge_shared', methods=['POST'])
def chargeSharedOscar(request, basket, order_number, amountInCents, feeInCents):

    if not STAND_ALONE:
        #request = args[0]
        #request.args = request.GET
        request.form = request.POST
        #g = request

        u = request.user


        mu = getSellerFromOscarID(request.user.id)

        #basket = request.basket
        seller = getSellerFromOscarID(basket.seller.user.id)

        if not basket:
            return redirect(url_for('catalogue:index'))


    else:
        print "in charge shared"
        if not g.user:
            return redirect(url_for('login'))
    
    #amount = basket.total_incl_tax_in_cents()

    #amountDollars = float(amountInCents) / 100.0 

    #print "is there a stripe ID? "
    #print mu.stripeID
    #print mu.stripeHasCard 
    
   
    # if mu.stripeID:
    #     print "has a stripe ID **********************" 
    #     custID = mu.stripeID
    #     ## make a new token??
    #     # Create a Token from the existing customer on the application's account


    # else: 
    ## not saving the Stripe IS for now
    if True:   
        print "no stripe ID ##################"
        try:
            customer = stripe.Customer.create(
                                      email=request.user.email,
                                      card=request.form['stripeToken'],
                                      api_key=stripe.api_key
                                      )

        except stripe.CardError, e:
            ## report error to user and fail (gracefully)
            body = e.json_body
            err  = body['error']
            print "Stripe customer create fail, msg: %s" % err['message']
            errMsg = err['message']
            messages.error(request, errMsg)
            return False

        custID = customer.id
        #mu.stripeID = customer.id
        #mu.save()

    ## make a token
    # Create a Token from the existing customer on the application's account
    stripe.api_key = basket.seller.stripeToken ##seller.stripeSellerToken
    tempToken = stripe.Token.create(
      customer=custID,  ## customer ID on application
      api_key=basket.seller.stripeToken ##seller.stripeSellerToken # seller's access token from the Stripe Connect flow
    )

    # customerConnected = stripe.Customer.create(
    #                                   email=mu.email,
    #                                   card=tempToken.card,
    #                                   api_key=seller.stripeAccountToken
    #                                   )

    
    print tempToken
    try:
        charge = stripe.Charge.create(
            #customer=custID, 
            #card = request.form['stripeToken'],
            card = tempToken.id,
            amount=amountInCents,
            currency='usd',
            #application_fee=int(floor(int(amountInCents) * 0.035)), # amount in cents
            application_fee=feeInCents, # amount in cents            
            api_key=basket.seller.stripeToken,  ##seller.stripeSellerToken,
            #api_key=stripe.api_key,
            description=str(order_number)
            )

    except stripe.CardError, e:
        ## report error to user and fail (gracefully)
        body = e.json_body
        err  = body['error']
        print "Stripe customer create fail, msg: %s" % err['message']
        errMsg = err['message']
        messages.error(request, errMsg)
        return False
    except stripe.APIConnectionError, ae:
        errMsg = "Trouble connecting to the Stripe payment center. Please check your network connection. If the problem persists contact us."
        messages.error(request, errMsg)
        return False


    print "CHARGE RESPONSE"
    print charge

    success = not charge.failure_code 
    if not charge.failure_code:
        print "no fail, charging " ##+ str(mu.stripeHasCard )
        
        #if not mu.stripeHasCard:
        #    print "did it work?"
        #    mu.stripeHasCard = True
        #    mu.save()
            
    #orderSuccess(mu, o)
    #return redirect(url_for('cart', username = g.user.name) )    
    #return render_template('charge.html', amount=amount, amountDollars=amountDollars, order=o)

    ## switch back the api_key
    stripe.api_key = stripe_keys['secret_key']

    return charge




# END Stripe stuff
####################

## jquery test

@app.route('/slider')
def testSlider():

     
    return render_template('testSlider.html')


##############
## FB test

@app.route('/facebook')
def facebookTest():
    return render_template('facebook_login.html')

@app.route('/facebook/login')
def loginFacebook():
    redirect_uri = url_for('authorized', _external=True)
    params = {'redirect_uri': redirect_uri}
    return redirect(facebook.get_authorize_url(**params))


@app.route('/facebook/authorized')
def authorized():
    # check to make sure the user authorized the request
    if not 'code' in request.args:
        flash('You did not authorize the request')
        return redirect(url_for('facebookTest'))

    # make a request for the access token credentials using code
    redirect_uri = url_for('authorized', _external=True)
    data = dict(code=request.args['code'], redirect_uri=redirect_uri)

    sessionFB = facebook.get_auth_session(data=data)

    # the "me" response
    me = sessionFB.get('me').json()

    user = Seller.getOrCreate(me['username'], me['id'])

    flash('Logged in as ' + me['name'])
    flash('You were logged in')
    session['user_id'] = user.name
    #return redirect(url_for('index'))
    return redirect(url_for('facebookTest'))
    



if not STAND_ALONE:

    from django.http import HttpResponse
    from django.template import RequestContext, Context, loader

    def o_about(*kwargs):
        request = kwargs[0]
        t = loader.get_template('about.jinja.html')
        c = RequestContext(request, {})
        return HttpResponse(t.render(c), content_type="text/html; charset=UTF-8")




##        return render(request, "about.jinja")



port = int(os.environ.get('PORT', 5000)) 

if __name__ == '__main__':
    #app.run(debug=True)
    app.run(host='0.0.0.0', port=port)


    


