# Bad answer from a BDAP HTTP(S) request
class InvalidBDAPAnswerException(Exception):
    "Raised when BDAP server fails to answer"

    def __init__(self, url, data=''):
        self.message = 'BDAP failed to correctly execute the command: ' + str(url)
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)

    # Invalid STAC item


class InvalidSTACitemException(Exception):
    'Raised when an invalid STAC item is passed to sentinel2* members of layer class'

    def __init__(self, stacitem):
        self.message = 'Invalid STAC item: ' + str(stacitem)
        super().__init__(self.message)

    # Customizable exception


class CustomException(Exception):

    def __init__(self, message, data=''):
        self.message = message
        if len(data) > 0:
            self.message += '\nData: ' + str(data)
        super().__init__(self.message)
