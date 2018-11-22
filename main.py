"""AlayaNotes

Usage:
  main.py [run]
  main.py initdb
"""
from docopt import docopt
import subprocess
import sys

from alayatodo import app, views


def _run_sql(filename):
    try:
        with open(filename, 'rb') as sql:
            subprocess.check_output(
                ['sqlite3', app.config['DATABASE']],
                stdin=sql,
                stderr=subprocess.STDOUT,
            )
    except subprocess.CalledProcessError as ex:
        sys.exit(ex)


if __name__ == '__main__':
    args = docopt(__doc__)
    if args['initdb']:
        _run_sql('resources/database.sql')
        _run_sql('resources/fixtures.sql')
        print("AlayaTodo: Database initialized.")
    else:
        app.run(use_reloader=True)
