import os
import sys
import subprocess
from setuptools import setup, find_packages
from distutils.command.build_py import build_py
from distutils.command.build_ext import build_ext


# Build with clang if not otherwise specified.
os.environ.setdefault('CC', 'clang')
os.environ.setdefault('CXX', 'clang++')


PACKAGE = 'symsynd'
EXT_EXT = sys.platform == 'darwin' and '.dylib' or '.so'


def build_libsymboizer(base_path):
    lib_path = os.path.join(base_path, '_libsymbolizer.so')
    here = os.path.abspath(os.path.dirname(__file__))
    rv = subprocess.Popen(['make', 'build'], cwd=here).wait()
    if rv != 0:
        sys.exit(rv)
    src_path = os.path.join(here, 'libsymbolizer', 'build', 'lib',
                            'libLLVMSymbolizer' + EXT_EXT)
    if os.path.isfile(src_path):
        os.rename(src_path, lib_path)


class CustomBuildPy(build_py):
    def run(self):
        build_py.run(self)
        build_libsymboizer(os.path.join(self.build_lib, *PACKAGE.split('.')))


class CustomBuildExt(build_ext):
    def run(self):
        build_ext.run(self)
        if self.inplace:
            build_py = self.get_finalized_command('build_py')
            build_libsymboizer(build_py.get_package_dir(PACKAGE))


setup(
    name='symsynd',
    version='0.8.3',
    url='http://github.com/getsentry/symsynd',
    description='Helps symbolicating crash dumps.',
    license='BSD',
    author='Sentry',
    author_email='hello@getsentry.com',
    packages=find_packages(),
    cffi_modules=['build.py:demangle_ffi',
                  'build.py:sym_ffi'],
    cmdclass={
        'build_ext': CustomBuildExt,
        'build_py': CustomBuildPy,
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
