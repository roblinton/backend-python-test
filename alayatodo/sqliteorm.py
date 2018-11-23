import re
from collections import OrderedDict
from itertools import chain
from flask import g


class DoesNotExist(Exception):
    pass


class MultipleObjectsReturned(Exception):
    pass


class Table:

    def __init__(self, tablename):
        self.tablename = re.sub(r'\W', '', tablename)
        self.fields = self._fetch_fields()

    def create(self, **kwargs):
        self._validate_fields(kwargs)
        sql = "INSERT INTO {} ({}) VALUES ({})".format(self.tablename, ', '.join(kwargs.keys()), ', '.join(['?']*len(kwargs)))
        cr = g.db.execute(sql, list(kwargs.values()))
        return self.get(rowid=cr.lastrowid)

    def all(self):
        return self._query()

    def where(self, **kwargs):
        return self._query(**kwargs)

    def get(self, **kwargs):
        qry = iter(self._list(kwargs))
        try:
            obj = next(qry)
        except StopIteration:
            raise DoesNotExist
        try:
            next(qry)
            raise MultipleObjectsReturned
        except StopIteration:
            return obj

    def count(self):
        return self._query().count()

    @property
    def model_class(self):
        try:
            return self._model_class
        except AttributeError:
            self._model_class = type(self.tablename.capitalize(), (DBModel,), {'__slots__': tuple(self.fields.keys()), '_manager': self})
        return self._model_class

    @property
    def primary_key(self):
        """This logic does not account for multiple primary keys."""
        try:
            return self._primary_key
        except AttributeError:
            try:
                self._primary_key = next(k for k,v in self.fields.items() if v['pk'] == 1)
            except StopIteration:
                self._primary_key = 'rowid'
        return self._primary_key

    def _fetch_fields(self):
        tabledesc = g.db.execute('PRAGMA table_info({})'.format(self.tablename)).fetchall()
        if not tabledesc:
            raise ValueError('No such table: {}!'.format(self.tablename))
        return OrderedDict((f['name'], dict(f)) for f in tabledesc)

    def _list(self, valdict):
        """Returns a cursor with the rows returned according to the filters in
        valdict.
        """
        return self._query(**valdict).select()

    def _query(self, **where):
        return Query(self).where(**where)

    def _validate_fields(self, valdict):
        """Ensures that a dict contains only keys corresponding to columns in
        the table.
        """
        not_fields = valdict.keys() - self.fields.keys() - {'rowid'}
        if not_fields:
            raise ValueError('Unexpected columns for {}: {}.  Table: {}'.format(self.tablename, not_fields, list(self.tablename)))
        return valdict


class Query:
    """
    """

    def __init__(self, model):
        self.model = model
        self._update = {}
        self._where = {}
        self._offset = None
        self._limit = None

    def __iter__(self):
        return self.select()

    def __getitem__(self, k):
        if isinstance(k, slice):
            self._offset = int(k.start)
            self._limit = int(k.stop - k.start)
            if k.step is not None:
                raise ValueError('Stepping is not supported.')
            if self._offset < 0 or self._limit < 0:
                raise ValueError('Offset and limit arguments cannot be negative.')
            return list(self.select())
        else:
            self._offset = int(k)
            self._limit = 1
            try:
                return self.model.model_class(**next(self.select()))
            except StopIteration as e:
                raise IndexError from e

    def where(self, **where):
        self._where.update(where)
        return self

    def select(self):
        self.base_qry = 'SELECT * FROM {}'.format(self.model.tablename)
        return (self.model.model_class(**row) for row in self._execute())

    def update(self, **kwargs):
        self.base_sql = 'UPDATE {}'.format(self.tablename)
        self._update.update(**kwargs)
        return self._execute()

    def delete(self):
        self.base_qry = 'DELETE FROM {}'.format(self.model.tablename)
        return self._execute()

    def count(self):
        self.base_qry = 'SELECT count({}) AS total FROM {}'.format(self.model.primary_key, self.model.tablename)
        return next(self._execute())['total']

    def _execute(self):
        sql, qry_args = self._build_query(self.base_qry)
        print('_execute() {}, {}'.format(sql, qry_args))
        return g.db.execute(sql, qry_args)

    def _build_query(self, base_qry):
        qry_args = []
        update = self._build_update(qry_args)
        where = self._build_where(qry_args)
        limit = ' LIMIT {}'.format(self._limit) if self._limit is not None else ''
        offset = ' OFFSET {}'.format(self._offset) if self._offset is not None else ''
        print('_build_query() {}, {}, {}'.format(where, self._limit, self._offset))
        return ('{}{}{}{}'.format(base_qry, where, limit, offset), qry_args)

    def _build_where(self, qry_args):
        """Supports only equality operators ANDed together."""
        qry_args.extend(self._where.values())
        return ' WHERE {}'.format(' AND '.join(self._params(self._where))) if self._where else ''

    def _build_update(self, qry_args):
        qry_args.extend(self._update.values())
        return 'SET {}'.format(', '.join(self._params(self._update))) if self._update else ''

    def _params(self, valdict):
        """Returns key=? strings suitable for sqlite's parameter substitution."""
        return ['{} = ?'.format(f) for f in self.model._validate_fields(valdict)]


class DBModel:
    """A DBModel represents a row in the database.

    Mostly works like a dict.  Implements __slots__ so it's more efficient
    memory-wise and you cannot assign attributes that don't already exist.
    """

    __slots__ = ()

    def __init__(self, *args, **kwargs):
        if len(args) > len(self.__slots__):
            raise TypeError('Too many args')
        for k,v in chain(zip(self.__slots__, args), kwargs.items()):
            setattr(self, k, v)

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(self.__slots__)

    def items(self):
        return self.todict().items()

    def keys(self):
        return iter(self.__slots__)

    def values(self):
        return (getattr(self, k, None) for k in self.__slots__)

    def todict(self):
        return OrderedDict([(k, getattr(self, k, None)) for k in self.__slots__])

    def save(self):
        """Saves the instance, either via an update or an insert depending on
        whether a primary key is defined.  Does not currently support updating
        a primary key.
        """
        if getattr(self, self._manager.primary_key) is None:
            self._manager.create(**self.todict())
        else:
            valdict = obj.todict()
            where = {self._manager.primary_key: valdict.pop(self._manager.primary_key)}
            self._manager.update(where, **valdict)


class ModelAccessor:

    def __getattr__(self, key):
        try:
            return self.__dict__[key]
        except KeyError:
            model = Table(key)
            setattr(self, key, model)
            return model
