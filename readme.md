# Working locally

First time setup:
```
$ git clone https://github.com/bhaumikdebanshu/aiplotter
$ cd aiplotter
$ python -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ # do your work
$ deactivate
```

Every time you work:
```
$ cd aiplotter
$ source .venv/bin/activate
$ # do your work
$ deactivate
```

Updating the requirements:
```
$ source .venv/bin/activate
$ pip freeze > requirements.txt
$ deactivate
```

Running Flask server:
```
$ source .venv/bin/activate
$ export FLASK_APP=aiplotter
$ export FLASK_ENV=development
$ flask run
```
