from logging import getLogger

from .connector import api
from .kanban import Board


__author__ = "Guillermo Guirao Aguilar"
__email__ = "contact@guillermoguiraoaguilar.com"
__license__ = "MIT"
__version__ = "1.5.0"


def get_boards():
    log.debug('Getting boards')
    return api.get('/Boards')


def get_newer_if_exists(board_id, version, timezone='UTC'):
    """ Downloads a board if a newer version number exists """
    url = '/Board/{}/BoardVersion/{}/GetNewerIfExists'
    log.debug('Getting board {} version >{}'.format(board_id, version))
    board = api.get(url.format(board_id, version))
    if board:
        return Board(board, timezone)
    else:
        return None


log = getLogger(__name__)
