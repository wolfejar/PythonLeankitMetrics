import logging
import requests

from . import config


class Connector(object):
    session = requests.Session()

    def authenticate(self, domain, username, password):
        self.session.auth = (username, password)
        self.base = 'https://{}.leankit.com/kanban/api'.format(domain)

    def get(self, url):
        log.debug('GET {}'.format(url))
        try:
            request = self.session.get(self.base + url, verify=True)
        except Exception as error:
            raise ConnectionError("Unable to make request: {}".format(error))
        if request.ok:
            try:
                response = request.json()
                if response['ReplyCode'] == 200:
                    return response['ReplyData'][0]
                else:
                    msg = "Error {ReplyCode}: {ReplyText}".format(**response)
                    raise ConnectionError(msg)

            except ValueError:
                raise IOError("Invalid response")
        else:
            msg = 'Server responded with code {0.status_code}'.format(request)
            raise ConnectionError(msg)


log = logging.getLogger(__name__)
api = Connector()
api.authenticate(**config.credentials)
