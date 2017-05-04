class SymbolicationError(Exception):
    message = None

    def __init__(self, message):
        if isinstance(message, bytes):
            message = message.decode('utf-8', 'replace')
        Exception.__init__(self, message)
        self.message = message

    def __str__(self):
        return self.message.encode('utf-8')

    def __unicode__(self):
        return self.message


class DebugInfoError(SymbolicationError):
    pass


class DwarfLookupError(DebugInfoError):
    pass


class NoSuchArch(DwarfLookupError):
    pass


class NoSuchSection(DwarfLookupError):
    pass


class NoSuchAttribute(DwarfLookupError):
    pass
