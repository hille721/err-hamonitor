err-hamonitor
=============

Errbot plugin to monitor your home assistant instance or any other kind of server/application.


Installation
------------

    !repos install https://github.com/hille721/err-hamonitor.git

Configuration
-------------

Either via chat:
    !plugin config hamonitor
    !plugin config Webserver

Or you are also able to configurate the plugin in the `config.py`

    HAMONITOR = {
        "HOSTS": {
            "examplehostname": {
                "NAME": "examplehostname",
                "IP": "1.2.3.4",
                "APPLICATIONS": {"appl1": {"PORT": 80, "PATH": "/path"}},
                "INTERVAL": 60,
                "DELAY": 60,
            }
        },
        "DEFAULT_INTERVAL": 60,
        "DEFAULT_DELAY": 30,
    }

    WEBSERVER = {
        "HOST": "0.0.0.0",
        "PORT": 3141,
        "SSL": {
            "enabled": False,
            "host": "0.0.0.0",
            "port": 3142,
            "certificate": "",
            "key": "",
        },
    }
