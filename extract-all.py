import os
import sys
import click
from symsynd.bulkextract import BulkExtractor


@click.command()
@click.option('--sdk', default='iOS')
@click.argument('files', nargs=-1, type=click.Path())
def cli(sdk, files):
    ex = BulkExtractor()
    for filename in files:
        dst = os.path.basename(filename).rstrip('/') + '.zip'
        if not os.path.isfile(dst):
            ex.build_symbol_archive(filename, dst, sdk=sdk, log=True)


cli()
