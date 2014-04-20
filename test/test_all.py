'''

    whooshalchemy flask extension
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Adds whoosh indexing capabilities to SQLAlchemy models for Flask
    applications.

    :copyright: (c) 2012 by Karl Gyllstrom
    :license: BSD (see LICENSE.txt)

'''

from __future__ import absolute_import

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.testing import TestCase
import flask.ext.whooshalchemy as wa

import datetime
import os
import tempfile
import shutil


db = SQLAlchemy()


class BlogishBlob(object):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    content = db.Column(db.String)
    blurb = db.Column(db.Unicode)
    ignored = db.Column(db.Unicode)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow())

    def __repr__(self):
        return '{0}(title={1})'.format(self.__class__.__name__, self.title)


def _after_flush(app, changes):
    from sqlalchemy.orm import EXT_CONTINUE
    return EXT_CONTINUE


class ObjectA(db.Model, BlogishBlob):
    __tablename__ = 'objectA'
    __searchable__ = ['title', 'content', 'blurb']


class ObjectB(db.Model, BlogishBlob):
    __tablename__ = 'objectB'
    __searchable__ = ['title', 'content', 'content']  # dup intentional (why?)


class ObjectC(db.Model, BlogishBlob):
    __tablename__ = 'objectC'
    __searchable__ = ['title', 'field_that_doesnt_exist']


class Tests(TestCase):
    DATABASE_URL = ':memory:'
    TESTING = True

    def create_app(self):
        tmp_dir = tempfile.mkdtemp()

        app = Flask(__name__)
        app.config['WHOOSH_BASE'] = os.path.join(tmp_dir, 'whoosh')
        db.init_app(app)

        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        try:
            # currently fails on windows, since something in whoosh
            # seems to be keeping the index files open
            shutil.rmtree(self.app.config['WHOOSH_BASE'])
        except OSError as e:
            if e.errno != 2:  # code 2 - no such file or directory
                raise

        db.session.remove()
        db.drop_all()

    def test_flask(self):
        """Used to fail due to a bug in Flask-SQLAlchemy."""
        from flask.ext.sqlalchemy import before_models_committed, models_committed
        
        before_models_committed.connect(_after_flush)
        models_committed.connect(_after_flush)
        db.session.add(ObjectB(title=u'my title', content=u'hello world'))
        db.session.add(ObjectA(title=u'a title', content=u'hello world'))
        db.session.flush()
        db.session.commit()

    def test_add_entry(self):
        db.session.add(ObjectA(title=u'title', blurb='this is a blurb'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search('blurb').count(), 1)

    def test_simple_search(self):
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search('what').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'no match').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 1)
        self.assertEqual(ObjectA.query.whoosh_search(u'hello').count(), 1)

    def test_conflict_fails(self):
        # Can't have two tables with same title and content? why not?
        db.session.add(ObjectB(title=u'my title', content=u'hello world'))
        db.session.commit()

        db.session.add(ObjectC(title=u'my title', content=u'hello world'))
        self.assertRaises(AttributeError, db.session.commit)

    def test_tables_dont_interfere(self):
        # Currently fails about half of the time
        # probably due to duplicated content field in ObjectB.__searchable__
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.add(ObjectB(title=u'what title', content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'what').count(), 0)
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 1)

        self.assertEqual(ObjectB.query.whoosh_search(u'what').count(), 1)
        self.assertEqual(ObjectB.query.whoosh_search(u'title').count(), 1)

    def test_search_multiple_rows(self):
        db.session.add(
            ObjectA(
                title=u'a slightly long title',
                content=u'hello world'))
        db.session.add(
            ObjectA(title='another title', content=u'a different message'))
        db.session.add(
            ObjectA(
                title="ceci n'est pas un titre",
                content='yet another message'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 2)

    def test_ranking(self):
        db.session.add(
            ObjectA(title=u'a slightly long title', content=u'hello world'))
        db.session.add(
            ObjectA(title=u'another title', content=u'a different message'))
        db.session.add(
            ObjectA(title=u'wow another title', content=u'another message'))
        db.session.commit()
        results = ObjectA.query.whoosh_search('title').all()
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].title, u'another title')
        self.assertEqual(results[1].title, u'wow another title')
        self.assertEqual(results[2].title, u'a slightly long title')

    def test_filter(self):
        db.session.add(
            ObjectA(title=u'a slightly long title', content=u'hello world'))
        db.session.add(
            ObjectA(title=u'another title', content=u'a different message'))
        one_day_ago = datetime.date.today() - datetime.timedelta(1)
        two_days_ago = datetime.date.today() - datetime.timedelta(2)
        db.session.add(
            ObjectA(
                title=u'an as yet unseen title',
                content='something', created=two_days_ago))
        db.session.commit()
        recent = (ObjectA.query.whoosh_search(u'title')
                  .filter(ObjectA.created >= one_day_ago).count())
        self.assertEqual(recent, 2)

    def test_limit(self):
        db.session.add(
            ObjectA(title=u'a slightly long title', content=u'hello world'))
        db.session.add(
            ObjectA(title=u'another title', content=u'a different message'))
        db.session.add(
            ObjectA(title=u'wow another title', content=u'another message'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 3)
        self.assertEqual(
            ObjectA.query.whoosh_search(u'title', limit=2).count(), 2)

    def test_restrict_fields(self):
        db.session.add(ObjectA(title=u'my title', content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 1)
        self.assertEqual(ObjectA.query.whoosh_search(u'hello').count(), 1)
        self.assertEqual(
            ObjectA.query.whoosh_search(
                u'title', fields=('title',)).count(), 1)
        self.assertEqual(
            ObjectA.query.whoosh_search(
                u'hello', fields=('title',)).count(), 0)
        self.assertEqual(
            ObjectA.query.whoosh_search(
                u'title', fields=('content',)).count(), 0)
        self.assertEqual(
            ObjectA.query.whoosh_search(
                u'hello', fields=('content',)).count(), 1)

    def test_and_or(self):
        db.session.add(ObjectA(title=u'my title', content=u'hello world'))
        db.session.commit()
        self.assertEqual(ObjectA.query.whoosh_search(u'hello dude').count(), 0)
        self.assertEqual(
            ObjectA.query.whoosh_search(u'hello dude', or_=True).count(), 1)

    def test_chaining(self):
        db.session.add(ObjectA(title=u'title one', content=u'a poem'))
        db.session.add(ObjectA(title=u'title two', content=u'about testing'))
        db.session.add(
            ObjectA(title=u'title three', content=u'is delightfully tested'))
        db.session.add(ObjectA(title=u'four', content=u'tests'))
        db.session.commit()

        self.assertEqual(ObjectA.query.whoosh_search(u'title').count(), 3)
        self.assertEqual(ObjectA.query.whoosh_search(u'test').count(), 3)

        # chained query, operates as AND
        self.assertEqual(
            ObjectA.query.whoosh_search(u'title')
                         .whoosh_search(u'test')
                         .count(), 2)

if __name__ == '__main__':
    import unittest
    unittest.main()
