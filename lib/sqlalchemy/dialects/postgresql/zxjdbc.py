"""Support for the PostgreSQL database via the zxjdbc JDBC connector.

JDBC Driver
-----------

The official Postgresql JDBC driver is at http://jdbc.postgresql.org/.

"""
from sqlalchemy.dialects.postgresql.base import PGCompiler, PGDialect
from sqlalchemy.connectors.zxJDBC import ZxJDBCConnector
from sqlalchemy.engine import default

class PostgreSQL_jdbcExecutionContext(default.DefaultExecutionContext):
    pass

class PostgreSQL_jdbcCompiler(PGCompiler):

    def post_process_text(self, text):
        # Don't escape '%' like PGCompiler
        return text

class PostgreSQL_jdbc(ZxJDBCConnector, PGDialect):
    execution_ctx_cls = PostgreSQL_jdbcExecutionContext
    statement_compiler = PostgreSQL_jdbcCompiler

    jdbc_db_name = 'postgresql'
    jdbc_driver_name = "org.postgresql.Driver"

    def _get_server_version_info(self, connection):
        return tuple(int(x) for x in connection.connection.dbversion.split('.'))
        
dialect = PostgreSQL_jdbc