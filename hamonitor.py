import platform
import subprocess
from subprocess import DEVNULL
import time
import urllib3

import requests

from errbot import BotPlugin, webhook


urllib3.disable_warnings()


class Hamonitor(BotPlugin):
    """
    Monitor your home assistant instance or any other kind of server/application
    """

    def activate(self):
        """
        Start monitoring after plugin activation.
        """
        super().activate()
        for hostname, hostconfig in self.config.get("HOSTS").items():
            self._set_host_status(hostname, "up")
            if hostconfig.get("APPLICATIONS"):
                for applicationname in hostconfig.get("APPLICATIONS").keys():
                    self._set_application_status(hostname, applicationname, "up")
            self.start_poller(
                interval=hostconfig.get(
                    "INTERVAL", self.config.get("DEFAULT_INTERVAL", 60 * 10)
                ),
                method=self.monitor,
                times=None,
                args=(hostname,),
            )

        # configure Webserver from config.py
        self.other = self.get_plugin("Webserver")
        if not self.other.config:
            self.other.config = self.bot_config.__dict__.get("WEBSERVER")
            self.other.activate()

    def get_configuration_template(self):
        """
        Defines the configuration structure this plugin supports
        """
        return {
            "HOSTS": {
                "examplehostname": {
                    "NAME": "examplehostname",
                    "IP": "1.2.3.4",
                    "APPLICATIONS": {"appl1": {"PORT": 80, "PATH": "/path"}},
                }
            },
            "DEFAULT_INTERVAL": 60,
            "DEFAULT_DELAY": 30,
        }

    def configure(self, configuration=None):
        if configuration == None and self.bot_config.__dict__.get("HAMONITOR"):
            self.log.info("Found config for HAMONITOR in config.py")
            config = self.bot_config.__dict__.get("HAMONITOR")
            if config.get("HOSTS") and isinstance(config.get("HOSTS"), dict):
                self.config = config
                return
            self.log.error("Config of HAMONITOR in config.py in wrong format.")
        self.config = configuration
        return

    def _set_host_status(self, hostname, status):
        """Helper method to set status of host in `self.config`

        Args:
            hostname (string): hostname
            status (string): status (up/down)
        """
        self.config["HOSTS"][hostname]["STATUS"] = status

    def _set_application_status(self, hostname, applicationname, status):
        """Helper method to set status of application in `self.config`

        Args:
            hostname (string): hostname
            applicationname (string): applicationname
            status (string): status (up/down)
        """
        self.config["HOSTS"][hostname]["APPLICATIONS"][applicationname][
            "STATUS"
        ] = status

    def _pingcmd(self, ip):
        """Ping an IP address

        Args:
            ip (string): IP to ping

        Returns:
            bool: `True` if ip pings, `False` if not
        """
        try:
            subprocess.run(
                [
                    "ping",
                    f"-{'n' if platform.system().lower() == 'windows' else 'c'}",
                    "1",
                    ip,
                ],
                stdout=DEVNULL,
                stderr=DEVNULL,
                check=True,
            )
            self.log.info("Ping %s succeeded", ip)
            return True
        except Exception:
            self.log.info("Ping %s failed", ip)
            return False

    def check_ping_host(self, hostname):
        """Running ping check on host

        Args:
            host (dict): host dictionaries out of `self.config["HOSTS"]`

        Returns:
            bool: `True` if it worked , `False` if something failed
        """

        host = self.config["HOSTS"][hostname]
        ip = host.get("IP")

        # ping host
        ping_result = self._pingcmd(ip)

        # host down
        if not ping_result:
            # ping changed from up to down
            if host["STATUS"] == "up":
                # wait the delay time till we notify
                start = time.time()
                while not ping_result and (time.time() - start) < host.get(
                    "DELAY", self.config.get("DEFAULT_DELAY", 0)
                ):
                    time.sleep(10)
                    ping_result = self._pingcmd(ip)

                # send alert
                self.send(
                    self.build_identifier("@CHANGE_ME"),
                    f"server {hostname} ({ip}) is down.",
                )
                self._set_host_status(hostname, "down")
                return False

            # host is still down
            if host["STATUS"] == "down":
                return False

        # host up
        if ping_result:
            # host changed from down to up
            if host["STATUS"] == "down":
                # send alive message again
                self.send(
                    self.build_identifier("@CHANGE_ME"),
                    f"server {hostname} ({ip}) is up again.",
                )
                self._set_host_status(hostname, "up")
                return True

        # host is stil up
        return True

    def _fetch(self, url):
        try:
            response = requests.get(url, verify=False)
            if response.status_code != 200:
                self.log.info(
                    "Application %s does not respond with 200 status code", url
                )
                return False
            self.log.info("Application %s responds with 200 status code.", url)
        except Exception as exc:
            self.log.info("Application %s responds with error: %s", url, str(exc))
            return False
        return True

    def check_application(self, hostname, applicationname):

        host = self.config["HOSTS"][hostname]
        application = host["APPLICATIONS"][applicationname]
        url = f"http://{host['IP']}:{application.get('PORT', 80)}{application.get('PATH', '')}"

        appl_fetch_result = self._fetch(url)

        # application down
        if not appl_fetch_result:
            # application changed from up to down
            if application["STATUS"] == "up":
                # wait the delay time till we notify
                start = time.time()
                while not appl_fetch_result and (time.time() - start) < host.get(
                    "DELAY", self.config.get("DEFAULT_DELAY", 0)
                ):
                    time.sleep(10)
                    appl_fetch_result = self._fetch(url)

                # send alert
                self.send(
                    self.build_identifier("@CHANGE_ME"),
                    f"application {hostname} - {applicationname} ({url}) is down.",
                )
                self._set_application_status(hostname, applicationname, "down")
                return False

            # host is still down
            if application["STATUS"] == "down":
                return False

        # application up
        if appl_fetch_result:
            # application changed from down to up
            if application["STATUS"] == "down":
                # send alive message again
                self.send(
                    self.build_identifier("@CHANGE_ME"),
                    f"application {hostname}-{applicationname} ({url}) is up again.",
                )
                self._set_application_status(hostname, applicationname, "up")
                return True

        # application is still up
        return True

    def monitor(self, hostname):

        ping_host_result = self.check_ping_host(hostname)

        if not ping_host_result:
            return False

        applications = self.config["HOSTS"][hostname].get("APPLICATIONS", [])
        if not len(applications):
            self.log.info("No applications defined for host %s", hostname)
            return True

        for applicationname in applications.keys():
            self.check_application(hostname, applicationname)
            return True

        return True

    @webhook
    def hamonitor_health(self, request):
        """Check status of this plugin via https call on /hamonitor_health"""
        # TODO: we have to check if the pollers are still running
        return "Ok"
