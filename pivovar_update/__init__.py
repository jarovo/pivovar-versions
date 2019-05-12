from contextlib import contextmanager
import logging
import os
import re
import subprocess
import requests
import yaml


VERSIONS_URL = (
    "https://raw.githubusercontent.com/jaryn/pivovar-versions/master/"
    "v2018-08-07"
)


logger = logging.getLogger('Updater')


@contextmanager
def chwd(directory):
    logger.info('Changing working dir to: %s.', directory)
    prev_wd = os.getcwd()
    os.chdir(directory)
    yield
    logger.info('Changing working dir back to: %s.', prev_wd)
    os.chdir(prev_wd)


def hostnamectl_values(hostnamectl):
    for line in hostnamectl.split('\n'):
        m = re.match(r'^\s*(.+):\s*(.+)$', line)
        if m:
            yield m.group(1), m.group(2)


def get_record(versions_url, machine_id):
    resp = requests.get(versions_url)
    if not resp.ok:
        raise Exception('Problem loading the versions file: HTTP {}'.format(
            resp.status_code))
    versions = yaml.load(resp.text)
    return versions[machine_id]


def update(args):
    hostnamectl = subprocess.check_output('hostnamectl').decode()
    machine_id = dict(hostnamectl_values(hostnamectl))['Machine ID']
    versions_url = args.versions_url

    logger.info('Checking updates for machine with id %s', machine_id)
    record = get_record(versions_url, machine_id)
    if record.get('skip-update'):
        return
    if record['packager'] == 'git':
        local_repo_path = args.local_repo_path
        virtualenv_path = args.virtualenv_path
        git_update(record, local_repo_path, virtualenv_path)


def git_update(record, local_repo_path, virtualenv_path):
    fetch_repo = record['repo']
    refspec = record['refspec']
    with chwd(local_repo_path):
        call(('git', 'fetch', fetch_repo, refspec))
        call(('git', 'checkout', 'FETCH_HEAD'))
    call((virtualenv_path + '/bin/pip3', 'install', '--force-reinstall', '-e',
          local_repo_path))


def call(commands):
    logger.info("Calling %s", ' '.join(commands))
    retval = subprocess.check_call(commands)
    logger.info("Call finished fine!")
    return retval


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pivovar software updater.')
    parser.add_argument('--versions-url', action='store', default=VERSIONS_URL,
                        help='URL of versions file.')
    parser.add_argument('--local-repo-path', action='store',
                        help='Path to local repo to update.')
    parser.add_argument('--virtualenv-path', action='store',
                        help='Path to virtualenv to update.')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    update(args)


if __name__ == '__main__':
    main()
