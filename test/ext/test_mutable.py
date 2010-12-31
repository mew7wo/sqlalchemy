from sqlalchemy import Integer
from sqlalchemy.types import PickleType, TypeDecorator, VARCHAR
from sqlalchemy.orm import mapper, Session, composite
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.instrumentation import ClassManager
from test.lib.schema import Table, Column
from test.lib.testing import eq_
from test.lib import testing
from test.orm import _base
import sys

class _MutableDictTestBase(object):
    @classmethod
    def _type_fixture(cls):
        from sqlalchemy.ext.mutable import Mutable
        
        # needed for pickle support
        global MutationDict
        
        class MutationDict(Mutable, dict):
            @classmethod
            def coerce(cls, key, value):
                if not isinstance(value, MutationDict):
                    if isinstance(value, dict):
                        return MutationDict(value)
                    return Mutable.coerce(key, value)
                else:
                    return value
        
            def __getstate__(self):
                return dict(self)
        
            def __setstate__(self, dict):
                self.update(dict)
            
            def __setitem__(self, key, value):
                dict.__setitem__(self, key, value)
                self.change()
    
            def __delitem__(self, key):
                dict.__delitem__(self, key)
                self.change()
        return MutationDict
    
    @testing.resolve_artifact_names
    def setup_mappers(cls):
        class Foo(_base.BasicEntity):
            pass
        
        mapper(Foo, foo)

    def teardown(self):
        # clear out mapper events
        Mapper.dispatch._clear()
        ClassManager.dispatch._clear()
        super(_MutableDictTestBase, self).teardown()
        
    @testing.resolve_artifact_names
    def test_in_place_mutation(self):
        sess = Session()

        f1 = Foo(data={'a':'b'})
        sess.add(f1)
        sess.commit()

        f1.data['a'] = 'c'
        sess.commit()

        eq_(f1.data, {'a':'c'})

    @testing.resolve_artifact_names
    def _test_non_mutable(self):
        sess = Session()

        f1 = Foo(non_mutable_data={'a':'b'})
        sess.add(f1)
        sess.commit()

        f1.non_mutable_data['a'] = 'c'
        sess.commit()

        eq_(f1.non_mutable_data, {'a':'b'})

class MutableWithScalarPickleTest(_MutableDictTestBase, _base.MappedTest):
    @classmethod
    def define_tables(cls, metadata):
        MutationDict = cls._type_fixture()
        
        Table('foo', metadata,
            Column('id', Integer, primary_key=True, test_needs_pk=True),
            Column('data', MutationDict.as_mutable(PickleType)),
            Column('non_mutable_data', PickleType)
        )
    
    def test_non_mutable(self):
        self._test_non_mutable()
        
class MutableWithScalarJSONTest(_MutableDictTestBase, _base.MappedTest):
    # json introduced in 2.6
    __skip_if__ = lambda : sys.version_info < (2, 6),

    @classmethod
    def define_tables(cls, metadata):
        import json

        class JSONEncodedDict(TypeDecorator):
            impl = VARCHAR

            def process_bind_param(self, value, dialect):
                if value is not None:
                    value = json.dumps(value)

                return value

            def process_result_value(self, value, dialect):
                if value is not None:
                    value = json.loads(value)
                return value
        
        MutationDict = cls._type_fixture()

        Table('foo', metadata,
            Column('id', Integer, primary_key=True, test_needs_pk=True),
            Column('data', MutationDict.as_mutable(JSONEncodedDict)),
            Column('non_mutable_data', JSONEncodedDict)
        )

    def test_non_mutable(self):
        self._test_non_mutable()

class MutableAssociationScalarPickleTest(_MutableDictTestBase, _base.MappedTest):
    @classmethod
    def define_tables(cls, metadata):
        MutationDict = cls._type_fixture()
        MutationDict.associate_with(PickleType)
        
        Table('foo', metadata,
            Column('id', Integer, primary_key=True, test_needs_pk=True),
            Column('data', PickleType)
        )

class MutableAssociationScalarJSONTest(_MutableDictTestBase, _base.MappedTest):
    # json introduced in 2.6
    __skip_if__ = lambda : sys.version_info < (2, 6),

    @classmethod
    def define_tables(cls, metadata):
        import json

        class JSONEncodedDict(TypeDecorator):
            impl = VARCHAR

            def process_bind_param(self, value, dialect):
                if value is not None:
                    value = json.dumps(value)

                return value

            def process_result_value(self, value, dialect):
                if value is not None:
                    value = json.loads(value)
                return value

        MutationDict = cls._type_fixture()
        MutationDict.associate_with(JSONEncodedDict)
        
        Table('foo', metadata,
            Column('id', Integer, primary_key=True, test_needs_pk=True),
            Column('data', JSONEncodedDict)
        )
        
class MutableCompositesTest(_base.MappedTest):
    @classmethod
    def define_tables(cls, metadata):
        Table('foo', metadata,
            Column('id', Integer, primary_key=True, test_needs_pk=True),
            Column('x', Integer),
            Column('y', Integer)
        )

    def teardown(self):
        # clear out mapper events
        Mapper.dispatch._clear()
        ClassManager.dispatch._clear()
        super(MutableCompositesTest, self).teardown()

    @classmethod
    def _type_fixture(cls):
        
        from sqlalchemy.ext.mutable import Mutable
        from sqlalchemy.ext.mutable import MutableComposite
        
        global Point
        
        class Point(MutableComposite):
            def __init__(self, x, y):
                self.x = x
                self.y = y

            def __setattr__(self, key, value):
                object.__setattr__(self, key, value)
                self.change()
        
            def __composite_values__(self):
                return self.x, self.y
            
            def __eq__(self, other):
                return isinstance(other, Point) and \
                    other.x == self.x and \
                    other.y == self.y
        return Point
        
    @classmethod
    @testing.resolve_artifact_names
    def setup_mappers(cls):
        Point = cls._type_fixture()
        
        class Foo(_base.BasicEntity):
            pass
            
        mapper(Foo, foo, properties={
            'data':composite(Point, foo.c.x, foo.c.y)
        })

    @testing.resolve_artifact_names
    def test_in_place_mutation(self):
        sess = Session()
        d = Point(3, 4)
        f1 = Foo(data=d)
        sess.add(f1)
        sess.commit()

        f1.data.y = 5
        sess.commit()

        eq_(f1.data, Point(3, 5))

                