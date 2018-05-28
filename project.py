from flask import Flask, render_template, request, redirect
from flask import make_response, jsonify, url_for, flash, session
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, Item, User
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
import random
import string
from datetime import datetime

# Load google client secret for OAUHT
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

app = Flask(__name__)

# Connect to Database and create database session
engine = create_engine('sqlite:///catalogapp.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# show login form
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    # Set anti-forgery state token
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Connect google acount with OAuth
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    output += '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# Disconnect google acount with OAuth
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCatalogs'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCatalogs'))


# Show all catalogs
@app.route('/')
@app.route('/catalog/')
def showCatalogs():
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    items = session.query(Item).order_by(asc(Item.created_at)).limit(10)
    return render_template(
        'catalog/catalogs.html',
        catalogs=catalogs,
        items=items)


# Show all catalogs json with related items
@app.route('/catalog/json')
def showCatalogsJson():
    catalogs = session.query(Catalog).order_by(asc(Catalog.name)).all()
    return jsonify(catalogs=[c.serialize for c in catalogs])


# Create a new catalog
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newcatalog():
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newcatalog = catalog(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newcatalog)
        session.commit()
        flash('New catalog %s Successfully Created' % newcatalog.name)
        return redirect(url_for('showCatalogs'))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template('catalog/newCatalog.html', catalogs=catalogs)


# Edit a catalog
@app.route('/catalog/<int:catalog_id>/edit/', methods=['GET', 'POST'])
def editcatalog(catalog_id):
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    editedCatalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        editedCatalog.name = request.form['name']
        session.add(editedCatalog)
        session.commit()
        flash('catalog Successfully Edited')
        return redirect(url_for('showCatalogs'))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'catalog/editCatalog.html',
            catalog=editedCatalog,
            catalogs=catalogs)


# Delete a catalog
@app.route('/catalog/<int:catalog_id>/delete/', methods=['GET', 'POST'])
def deleteCatalog(catalog_id):
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    deletedCatalog = session.query(Catalog).filter_by(id=catalog_id).one()
    if request.method == 'POST':
        session.delete(deletedCatalog)
        session.commit()
        flash('catalog Successfully Deleted')
        return redirect(url_for('showCatalogs'))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'catalog/deleteCatalog.html',
            catalog=deletedCatalog,
            catalogs=catalogs)


# Show catalog's all items
@app.route('/catalog/<int:catalog_id>/item/')
def showItems(catalog_id):
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    items = session.query(Item).filter_by(catalog_id=catalog.id)
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    return render_template(
        'item/items.html',
        items=items.all(),
        catalog=catalog,
        catalogs=catalogs,
        catalog_item_count=items.count())


# Show items json
@app.route('/catalog/<int:catalog_id>/item/json')
def showItemsJson(catalog_id):
    items = session.query(Item).filter_by(
        catalog_id=catalog_id).all()
    return jsonify(items=[i.serialize for i in items])


# Create a new item
@app.route('/catalog/<int:catalog_id>/item/new/', methods=['GET', 'POST'])
def newItem(catalog_id):
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        now = datetime.now()
        newItem = Item(
            title=request.form['title'],
            description=request.form['description'],
            catalog_id=request.form['catalog_id'],
            user_id=login_session['user_id'],
            created_at=now,
            updated_at=now
        )
        session.add(newItem)
        flash('New Item %s Successfully Created' % newItem.title)
        session.commit()
        return redirect(url_for('showItems', catalog_id=catalog_id))
    else:
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'item/newItem.html',
            catalogs=catalogs,
            catalog_id=catalog_id)


# show a item
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/',
    methods=['GET', 'POST'])
def showItem(catalog_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    catalogs = session.query(Catalog).order_by(asc(Catalog.name))
    catalog = session.query(Catalog).filter_by(id=catalog_id).one()
    return render_template(
        'item/item.html',
        item=item,
        catalog=catalog,
        catalogs=catalogs)


# Show item's json
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/json',
    methods=['GET', 'POST'])
def showItemJson(catalog_id, item_id):
    item = session.query(Item).filter_by(
        id=item_id).one()
    return jsonify(item=item.serialize)


# Edit a item
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/edit/',
    methods=['GET', 'POST'])
def editItem(catalog_id, item_id):
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        editedItem.title = request.form['title']
        editedItem.description = request.form['description']
        editedItem.updated_at = datetime.now()
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(
            url_for(
                'showItem',
                catalog_id=editedItem.catalog_id,
                item_id=editedItem.id)
            )
    else:
        catalog = session.query(Catalog).filter_by(id=catalog_id).one()
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'item/editItem.html',
            item=editedItem,
            catalog=catalog,
            catalogs=catalogs)


# Delete a item
@app.route(
    '/catalog/<int:catalog_id>/item/<int:item_id>/delete/',
    methods=['GET', 'POST'])
def deleteItem(catalog_id, item_id):
    # check logined or not
    if 'username' not in login_session:
        return redirect('/login')
    deletedItem = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(
            url_for('showItems', catalog_id=deletedItem.catalog_id))
    else:
        catalog = session.query(Catalog).filter_by(id=catalog_id).one()
        catalogs = session.query(Catalog).order_by(asc(Catalog.name))
        return render_template(
            'item/deleteItem.html',
            item=deletedItem,
            catalog=catalog,
            catalogs=catalogs)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
