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

    def list(self, **kwargs):
        return [self.model_class(**r) for r in self._list(kwargs).fetchall()]

    def get(self, **kwargs):
        cr = self._list(kwargs)
        row = cr.fetchone()
        if row is None:
            raise DoesNotExist
        if cr.fetchone() is not None:
            raise MultipleObjectsReturned
        return self.model_class(**row)

    def delete(self, **kwargs):
        if not kwargs:
            raise ValueError('No filter provided to delete!  Use delete_all() if you really want this.')
        return g.db.execute('DELETE FROM {}{}'.format(self.tablename, self._where(kwargs)), list(kwargs.values()))

    def delete_all(self):
        return g.db.execute('DELETE FROM {}'.format(self.tablename))

    def update(self, where, **kwargs):
        """TODO: finish"""
        if not where:
            raise ValueError('No where argument provided to update!  Use update_all() if you really want this.')
        sql = 'UPDATE {} SET {}{}'.format(self.tablename, ', '.join(self._params(kwargs)), self._where(where))
        return g.db.execute(sql, list(valdict.values()) + list(where.values()))

    def update_all(**kwargs):
        sql = 'UPDATE {} SET {}'.format(self.tablename, ', '.join(self._params(kwargs)))
        return g.db.execute(sql, list(valdict.values()))

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
        sql = 'SELECT * FROM {}{}'.format(self.tablename, self._where(valdict))
        # print('QUERY: {}, {}'.format(sql, valdict.values()))
        return g.db.execute(sql, list(valdict.values()))

    def _where(self, valdict):
        """Supports only equality operators ANDed together."""
        if valdict:
            return ' WHERE {}'.format(' AND '.join(self._params(valdict)))
        return ''

    def _params(self, valdict):
        """Returns key=? strings suitable for sqlite's parameter substitution."""
        return ['{} = ?'.format(f) for f in self._validate_fields(valdict)]

    def _validate_fields(self, valdict):
        """Ensures that a dict contains only keys corresponding to columns in
        the table.
        """
        not_fields = valdict.keys() - self.fields.keys() - {'rowid'}
        if not_fields:
            raise ValueError('Unexpected columns for {}: {}.  Table: {}'.format(self.tablename, not_fields, list(self.tablename)))
        return valdict


class DBModel(object):
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
            self._manager.insert(*self)
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
