import enum


class RequestStatus(enum.Enum):
    SUCCESS = 'Successfully served'
    WAITING_FOR_PORT = 'Waiting for port (searching every 5 sec)'
    PORT_WAITING = 'Port is waiting 1 min'
    MISSED = 'Missed (no request for 1 min)'
    FINISHED = 'After successful /endport'
    AUTO_FINISHED = 'Auto finished after rent timeout, no /endport'


class ResponseStatus(enum.Enum):
    SUCCESS = 'Successfully served'
    PORT_WAITING = 'Port is waiting 1 min (searching every 5 sec)'
    MISSED = 'Missed (no request for 1 min)'
    FINISHED = 'After successful /endport'
    AUTO_FINISHED = 'Auto finished after rent timeout, no /endport'


class RotationType(enum.Enum):
    STATIC = 'Static'
    BY_LINK = 'By link'
    BY_TIME = 'By time'
    BY_CONNECTION = 'By connection'
