from __future__ import print_function
import time
import urllib
import Telstra_Messaging
from Telstra_Messaging.rest import ApiException
from flask import Flask, abort, request 
from tinydb import TinyDB, Query
from tinydb.operations import delete, add

app = Flask(__name__)

db = TinyDB('./db.json')

client_id = 'client_id in here'
client_secret = 'client_secret in here'
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
def hello():
    prov = provision()
    return "All up and running, a number is provisioned at "+prov
    

@app.route("/", methods=['POST'])
def post():
	data = request.get_json()

	List = Query()

	Prof = Query()
	rtn = db.upsert({'profile': data['from']}, Prof.profile == data['from'])
	profile = db.get(Prof.profile == data['from'])

	if profile['nick'] is None: 
		db.update({'nick': data['from']}, doc_ids=[profile.doc_id])
		profile['nick'] = data['from'][2].replace("+61", "0", 1)+data['from'][3:]

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
		sendsms(data['from'], "SMSlist help - create [list], send [list], delete [list], add/remove [list] [mobile], restrict/unrestrict [list]. Example: 'create list1'. [list] = list name with no spaces in list name and alpha/numbers only. ::: Set Name [nickname] to set name in send.")

	return ""

 
if __name__ == "__main__":
    app.run()
