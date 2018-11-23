"""AlayaNotes

Usage:
  main.py [run]
  main.py initdb
  main.py migrate FILE
"""
from docopt import docopt
import os
import subprocess
import sys

from alayatodo import app, views


def _run_sql(filename):
    try:
        with open(filename, 'rb') as sql:
            output = subprocess.check_output(
                ['sqlite3', app.config['DATABASE']],
                stdin=sql,
                stderr=subprocess.STDOUT,
            )
    except subprocess.CalledProcessError as ex:
        print('Error: {}'.format(ex.output.decode()))
        sys.exit(ex)


if __name__ == '__main__':
    args = docopt(__doc__)
    if args['initdb']:
        _run_sql('resources/database.sql')
        _run_sql('resources/fixtures.sql')
        print("AlayaTodo: Database initialized.")
    elif args['migrate']:
        fname = os.path.basename(args['FILE'])
        print('Migrating {}'.format(fname))
        _run_sql(os.path.join('resources', fname))
    else:
        app.run(use_reloader=True)
