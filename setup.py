"""
Flask-WhooshAlchemy
-------------

Whoosh extension to Flask/SQLAlchemy
"""

from setuptools import setup
import os

from flask_whooshalchemyplus import __version__ as VERSION

setup(
    name='Flask-WhooshAlchemyPlus',
    version=VERSION,
    url='https://github.com/revolution1/Flask-WhooshAlchemyPlus',
    license='BSD',
    author='Revolution1',
    author_email='crj93106@gmail.com',
    description='Whoosh extension to Flask/SQLAlchemy',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),

    py_modules=['flask_whooshalchemyplus'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[x.strip() for x in
        open(os.path.join(os.path.dirname(__file__),
            'requirements.txt'))],
    tests_require=['Flask-Testing'],

    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    test_suite='test.test_all',
)
