import os
import subprocess
from setuptools import setup, find_packages
from distutils.command.build_ext import build_ext


# Build with clang if not otherwise specified.
os.environ.setdefault('CC', 'clang')


class LLVMBuildExt(build_ext):

    def pre_run(self, ext, ffi):
        if ext.name != '_symsynd_symbolizer':
            return
        subprocess.Popen(
            ['make', 'build'],
            cwd=os.path.abspath(os.path.dirname(__file__))
        ).wait()


setup(
    name='symsynd',
    version='0.8.3',
    url='http://github.com/getsentry/symsynd',
    description='Helps symbolicating crash dumps.',
    license='BSD',
    author='Sentry',
    author_email='hello@getsentry.com',
    packages=find_packages(),
    cffi_modules=['demangler_build.py:ffi',
                  'symbolizer_build.py:ffi'],
    cmdclass={
        'build_ext': LLVMBuildExt,
    },
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
