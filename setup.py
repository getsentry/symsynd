import os
from setuptools import setup, find_packages


# Build with clang if not otherwise specified.
os.environ.setdefault('CC', 'clang')


setup(
    name='symsynd',
    version='0.5.2',
    url='http://github.com/getsentry/symsynd',
    description='Helps symbolicating crash dumps.',
    license='BSD',
    author='Sentry',
    author_email='hello@getsentry.com',
    packages=find_packages(),
    cffi_modules=['demangler_build.py:ffi'],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    install_requires=[
        'macholib',
        'cffi>=1.0.0',
    ],
    setup_requires=[
        'cffi>=1.0.0'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
