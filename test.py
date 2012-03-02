from flask import Flask
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.testing import Twill, TestCase

import whooshalchemy

import os
import tempfile
import shutil


class Tests(TestCase):
    def create_app(self):
        tmp_dir = tempfile.mkdtemp()

        config = dict(DATABASE_URL='sqlite://',
                      TESTING=True)

        app = Flask(__name__)
        app.config.update(config)

        app.config['WHOOSH_INDEX'] = os.path.join(tmp_dir, 'whoosh')

        app.db = SQLAlchemy(app)

        class ObjectA(app.db.Model):
            __tablename__ = 'objectA'
            __searchable__ = ['title']

            id = app.db.Column(app.db.Integer, primary_key=True)
            title = app.db.Column(app.db.Text)

            def __repr__(self):
                return '{0}(title={1})'.format(self.__class__.__name__, self.title)

        self.ObjectA = ObjectA
        app.db.create_all()

        return app

    def tearDown(self):
        try:
            shutil.rmtree(self.app.config['WHOOSH_INDEX'])
        except OSError, e:
            if e.errno != 2: # code 2 - no such file or directory
                raise

    def test_main(self):
        def add(title):
            item = self.ObjectA(title=title)
            self.app.db.session.add(item)
            self.app.db.session.commit()
            return item

        a = add(u'good times were had by all')
        res = list(self.ObjectA.search_query(u'good'))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, a.id)

        b = add(u'good natured people are fun')
        res = list(self.ObjectA.search_query(u'good'))
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].id, a.id)
        self.assertEqual(res[1].id, b.id)

        res = list(self.ObjectA.search_query(u'people'))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, b.id)

        a = self.ObjectA.query.get(1)
        self.app.db.session.delete(a)
        self.app.db.session.commit()

        res = list(self.ObjectA.search_query(u'good'))
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, b.id)
#
#        with Twill(self.app, port=5000) as t:
#            t.browser.go(t.url('/'))
#            t.browser.show()


if __name__ == '__main__':
    import unittest
    unittest.main()
