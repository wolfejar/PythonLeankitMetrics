import os
import json
import logging


def save():  # pragma: no cover
    if not os.path.exists(folder):
        log.debug('Creating new config folder')
        os.makedirs(folder)
    creds = {key: input(key.capitalize() + ': ') for key in credentials}
    with open(filename, 'w') as conf:
        json.dump(creds, conf, indent=2)
        log.debug('Credentials stored at {}'.format(filename))


def load():  # pragma: no cover
    if os.path.exists(filename):
        log.debug("Loading user credentials")
        with open(filename) as conf:
            try:
                return json.load(conf)
            except json.JSONDecodeError:
                log.warning("Failed to load configuration file")


log = logging.getLogger(__name__)
folder = os.path.expanduser('~/.config/leankit')
filename = os.path.join(folder, 'config.json')
credentials = {key: os.getenv('LEANKIT_' + key.upper()) for key in
               ['domain', 'username', 'password']}
credentials.update(load() or {})


if __name__ == "__main__":  # pragma: no cover
    save()
