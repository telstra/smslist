# SMSList demo 

## Requirements

* Python 2.7
* Valid and active client_id and client_secret from [Dev.Telstra.com](https://dev.telstra.com)

## Installation & Usage

```sh
pip install -r requirements.txt
```
Open app.py and update the following on lines 14 and 15 of app.py using the keys obtained from [Dev.Telstra.com](https://dev.telstra.com)

```python
client_id = 'client_id in here'
client_secret = 'client_secret in here'
```

Once the app is ready to go youll need a publicly available url, open the base url in a browser which will create the provision subscription and set a mobile number for the app creds. 

By default the notify_url is set as the base url that you open the site root at, if you change the baseurl just open the root site again and it will update. This can be changed at line 27 of app.py

## Running the demo 

Once dependencies have been handled run the following

```python
python app.py 
```

or via pm2

```
pm2 start app.py
```
