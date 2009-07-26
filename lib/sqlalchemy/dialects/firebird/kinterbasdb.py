from sqlalchemy.dialects.firebird.base import FBDialect, FBCompiler
from sqlalchemy.engine.default import DefaultExecutionContext

_initialized_kb  = False

class Firebird_kinterbasdb(FBDialect):
    driver = 'kinterbasdb'
    supports_sane_rowcount = False
    supports_sane_multi_rowcount = False

    def __init__(self, type_conv=200, concurrency_level=1, **kwargs):
        super(Firebird_kinterbasdb, self).__init__(**kwargs)

        self.type_conv = type_conv
        self.concurrency_level = concurrency_level

    @classmethod
    def dbapi(cls):
        k = __import__('kinterbasdb')
        return k

    def create_connect_args(self, url):
        opts = url.translate_connect_args(username='user')
        if opts.get('port'):
            opts['host'] = "%s/%s" % (opts['host'], opts['port'])
            del opts['port']
        opts.update(url.query)

        type_conv = opts.pop('type_conv', self.type_conv)
        concurrency_level = opts.pop('concurrency_level', self.concurrency_level)
        global _initialized_kb
        if not _initialized_kb and self.dbapi is not None:
            _initialized_kb = True
            self.dbapi.init(type_conv=type_conv, concurrency_level=concurrency_level)
        return ([], opts)

    def _get_server_version_info(self, connection):
        """Get the version of the Firebird server used by a connection.

        Returns a tuple of (`major`, `minor`, `build`), three integers
        representing the version of the attached server.
        """

        # This is the simpler approach (the other uses the services api),
        # that for backward compatibility reasons returns a string like
        #   LI-V6.3.3.12981 Firebird 2.0
        # where the first version is a fake one resembling the old
        # Interbase signature. This is more than enough for our purposes,
        # as this is mainly (only?) used by the testsuite.

        from re import match

        fbconn = connection.connection
        version = fbconn.server_version
        m = match('\w+-V(\d+)\.(\d+)\.(\d+)\.(\d+) \w+ (\d+)\.(\d+)', version)
        if not m:
            raise AssertionError("Could not determine version from string '%s'" % version)
        return tuple([int(x) for x in m.group(5, 6, 4)])

    def is_disconnect(self, e):
        if isinstance(e, self.dbapi.OperationalError):
            return 'Unable to complete network request to host' in str(e)
        elif isinstance(e, self.dbapi.ProgrammingError):
            msg = str(e)
            return ('Invalid connection state' in msg or
                    'Invalid cursor state' in msg)
        else:
            return False

dialect = Firebird_kinterbasdb