# apartment hunter

```sh
$ python --version
Python 3.10.12

virtualenv venv
. venv/bin/activate

pip install -r requirements.txt

cp example.env .env

# edit .env

./apt.py
```


## discord setup

create app

use the oauth2 stuff to create URL and go to URL in browser to invite the bot to server

add bot to channel

remember, use `await fetch_channel(id)` instead of `get_channel(id)`, the docs/examples are broken. channel needs to be fetched to cache first