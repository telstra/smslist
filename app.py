from __future__ import print_function
import time
import urllib
import Telstra_Messaging
from Telstra_Messaging.rest import ApiException
from flask import Flask, abort, request, render_template
from tinydb import TinyDB, Query
from tinydb.operations import delete, add

app = Flask(__name__)

db = TinyDB('./db.json')

client_id = 'client_id'
client_secret = 'client_secret' 
grant_type = 'client_credentials' 

def provision():
	api_instance = Telstra_Messaging.AuthenticationApi()
	
	api_response = api_instance.auth_token(client_id, client_secret, grant_type)

	configuration = Telstra_Messaging.Configuration()
	configuration.access_token = api_response.access_token

	api_instance = Telstra_Messaging.ProvisioningApi(Telstra_Messaging.ApiClient(configuration))
	body = Telstra_Messaging.ProvisionNumberRequest(30, request.base_url)

	api_response = api_instance.create_subscription(body)
	return api_response.destination_address

def sendsms(to, msg):
	api_instance = Telstra_Messaging.AuthenticationApi()
	
	api_response = api_instance.auth_token(client_id, client_secret, grant_type)

	configuration = Telstra_Messaging.Configuration()
	configuration.access_token = api_response.access_token

	api_instance = Telstra_Messaging.MessagingApi(Telstra_Messaging.ApiClient(configuration))
	var = {'to': to, 'body': msg}

	api_response = api_instance.send_sms(var)


@app.route("/")
def home():

	c1 = Query()
	count = db.count(c1.name.exists())
	users = db.count(c1.profile.exists())
	prov = provision()

	inst = []
	inst.append({'title': 'Create/Delete [list]', 'blurb': 'Create/Delete [list] is a single word (no spaces) that can contain alphanumerics.', 'example': 'Create testlist | Delete testlist'})
	inst.append({'title': 'send [list] [message]', 'blurb': 'Sends a message to a list of mobiles, if the list is restricted (see below) the sending mobile number will need to be part of the list. send and the list name are removed from the group sms', 'example': 'send testlist hello world'})
	inst.append({'title': 'add/remove [list] [mobile]', 'blurb': 'add/remove [list] [mobile], needs to be an existing list and sending mobile has to be the admin/owner of it.', 'example': 'add testlist 0400000000 | remove testlist 0400000000'})
	inst.append({'title': 'restrict/unrestrict [list]', 'blurb': 'locks the list so that only numbers listed will be able to send messages to the list group.', 'example': 'restrict testlist | unrestrict testlist'})
	inst.append({'title': 'Set Name [nickname]', 'blurb': 'Sets a username against a mobile number to display in list send so the name shows instead of the mobile number', 'example': 'set name hello_world'})

	return render_template("index.html", prov=prov, lists=count, users=users, inst=inst)

@app.route("/", methods=['POST'])
def post():
	data = request.get_json()

	List = Query()

	Prof = Query()

	profile = db.get(Prof.profile == data['from'])

	if profile is None: 
		rtn = db.upsert({'profile': data['from'], 'nick': data['from'][0:3].replace("+61", "0", 1)+data['from'][3:]}, Prof.profile == data['from'])
		profile = db.get(Prof.profile == data['from'])

	first = data['body'].split(' ')

	if first[0].lower() == "set":
		
		if first[1].lower() == "name":
			db.update({'nick': first[2]}, doc_ids=[profile.doc_id])
			sendsms(data['from'], "Your nickname "+first[2]+" has been set")	

	elif first[0].lower() == "list":
		res = db.search(List.admin == data['from'])

		msg = "It doesnt look like you are admin of any lists yet"

		names = ""

		for item in res:
			names += "|"+item['name']

		if len(names) > 0: msg = "You are an admin of these lists: "+names.replace("|","",1)

		sendsms(data['from'], msg)		


	elif first[0].lower() == "send":
		msg = "computer says no, something has gone wrong"

		res = db.get((List.name == first[1].lower()))

		data['body'] = data['body'].replace(first[0]+" ", "").replace(first[1]+" ", "")

		if res is None: msg = "Computer says no, that list doesnt exist or you are not able to send to it"
		elif res['lock'] == 1 and data['from'] in res['sub'] or res['lock'] == 0:
			data['from'] = res['sub']
			msg = profile['nick']+": "+data['body']
			
		sendsms(data['from'], msg)	

	elif first[0].lower() == "add" or first[0].lower() == "remove":

		rtnmsg = "Something has gone wrong"
		
		first[2] = urllib.unquote_plus(first[2][0].replace("0", "+61", 1)+first[2][1:])

		List = Query()
		res = db.get((List.name == first[1].lower()) & (List.admin == data['from']))

		if res is not None:
			if first[0].lower() == "add":
				if first[2] in res['sub'] : rtnmsg = "that number already exists "
				else: 
					res['sub'].append(first[2])
					db.update({'sub': res['sub']}, List.name == first[1].lower())
					rtnmsg = "'"+first[2]+"' has been added to the '"+first[1].lower()+"' list"

					sendsms(first[2], "You have been added to the smslist '"+first[1].lower()+"' by "+profile['nick'])
			elif first[0].lower() == "remove":
				if first[2] not in res['sub'] : rtnmsg = "that number doesnt exist in this list"
				else:
					res['sub'].remove(first[2])
					db.update({'sub': res['sub']}, List.name == first[1].lower())
					rtnmsg = "'"+first[2]+"' has been removed from the '"+first[1].lower()+"' list"
		else: 
			rtnmsg = "Computer says no, looks like that doesnt exist or you are not the admin"

		sendsms(data['from'], rtnmsg)
	elif first[0].lower() == "restrict" or first[0].lower() == "unrestrict":

		msg = "Computer says no, Something has gone wrong"

		check = db.get((List.name == first[1].lower()) & (List.admin == data['from']))

		if not check:
			msg = "Computer says no, the list '"+first[1]+"' doesnt exist or you are not admin"
		else:

			if first[0].lower() == "restrict": lock = 1
			else: lock = 0

			db.update({'lock': lock}, List.name == first[1].lower())			

			msg = first[0]+" is now set on list '"+first[1]+"'"

		sendsms(data['from'], msg)

	elif first[0].lower() == "delete":

		check = db.get((List.name == first[1].lower()) & (List.admin == data['from']))

		msg = "Computer says no, Something has gone wrong"		

		if check: 
			db.remove(doc_ids=[check.doc_id])
			msg = "List '"+first[1]+"' has been deleted"
		else: msg = "List '"+first[1]+"' doesnt exist or you are not the admin for it"

		sendsms(data['from'], msg)

	elif first[0].lower() == "create":			

			res = db.get(List.name == first[1].lower())

			if not res:
				newlist = [data['from']] 

				db.insert({'name': first[1], 'admin': data['from'], 'sub': newlist, 'lock': 0})
				sendsms(data['from'], "List '"+first[1].lower()+"' has been created and you are the admin.")		
			else:
				sendsms(data['from'], "Computer says no, looks like the list '"+first[1].lower()+"' already exists")		


	else: 
		sendsms(data['from'], "SMSlist help - create [list], send [list], delete [list], add/remove [list] [mobile], restrict/unrestrict [list]. see https://smslist.telstradev.com for more info")

	return ""

 
if __name__ == "__main__":
    app.run(debug = True, passthrough_errors=True)
