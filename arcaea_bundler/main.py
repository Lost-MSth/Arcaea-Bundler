import argparse
import hmac
import json
import logging
import os
from base64 import b64decode, b64encode
from hashlib import sha256
from sys import version_info
from traceback import print_exc

if version_info < (3, 8):
    # from backports.cached_property import cached_property
    cached_property = property  # 别问，问就是懒
else:
    from functools import cached_property


APP_NAME = 'arcaea_bundler'
APP_VERSION = '1.0'

# Calvin S
DESCRIPTION = '''
╔═╗┬─┐┌─┐┌─┐┌─┐┌─┐  ╔╗ ┬ ┬┌┐┌┌┬┐┬  ┌─┐┬─┐
╠═╣├┬┘│  ├─┤├┤ ├─┤  ╠╩╗│ ││││ │││  ├┤ ├┬┘
╩ ╩┴└─└─┘┴ ┴└─┘┴ ┴  ╚═╝└─┘┘└┘─┴┘┴─┘└─┘┴└─

Arcaea Bundler is a tool to bundle or debundle content bundles of Arcaea.

Maded by Lost-MSth @ 2024
'''

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def version_tuple(version: 'str | None') -> tuple:
    if version is None:
        return (0, 0, 0)
    return tuple(map(int, version.split('.')))


def std_path(path: str) -> str:
    return path.replace('\\', '/')


def bytes_format(b: int) -> str:
    for i in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f'{b:.3f} {i}'
        b /= 1024
    return f'{b:.3f} PB'


class FileParser:
    KEY = b'\xd4\x1f\xdb\xe37\xd0\x01h\x0c*MC\xaf\xe5p\xc7\x1f\xde\x85\xd8\xf3\xd4\xc4o7\x99\xc1\x8f\x1fP\x82w\xac\xa7\xabc2\x83q\x0c+\xb4\x1a\x07\x8e\xfb\xe7\xc1\x9c\xf0\x87\xa7\xe17u*\xb7X\x1c\x8d\x9c\x0e=\xe9'

    def __init__(self):
        self.file_path: str = None  # 绝对路径
        self.rel_path: str = None  # 相对路径
        self.offset: int = None
        self.length: int = None

        self.data: bytes = None

    def _get_file_data(self) -> bytes:
        with open(self.file_path, 'rb') as f:
            return f.read()

    def to_dict(self) -> dict:
        return {
            'path': self.rel_path,
            'byteOffset': self.offset,
            'length': self.length,
            'sha256HashBase64Encoded': self.file_hash_base64
        }

    @cached_property
    def file_hash(self) -> bytes:
        return sha256(self.data).digest()

    @cached_property
    def file_hash_base64(self) -> str:
        return b64encode(self.file_hash).decode()

    @cached_property
    def detail_hash(self) -> bytes:
        return hmac.new(self.KEY, self.data, sha256).digest()

    @cached_property
    def detail_hash_base64(self) -> str:
        return b64encode(self.detail_hash).decode()

    @classmethod
    def from_bundle(cls, bundle_handler, file_abspath: str, offset: int, length: int, file_hash: bytes):
        c = cls()
        c.file_path = file_abspath
        c.offset = offset
        c.length = length
        bundle_handler.seek(offset)
        c.data = bundle_handler.read(length)
        logger.debug(
            f'File `{file_abspath}` read from bundle: offset={offset}, length={length}, SHA256={b64encode(file_hash).decode()}')
        if c.file_hash != file_hash:
            logger.debug(
                f'File hash mismatch for `{file_abspath}`: expected={file_hash.hex()}, actual={c.file_hash.hex()}')
            raise ValueError(f'File hash mismatch for `{file_abspath}`')
        return c

    def to_file(self) -> None:
        paths = os.path.split(self.file_path)
        if not os.path.isdir(paths[0]):
            logger.debug(f'Creating directory `{paths[0]}`')
            os.makedirs(paths[0])
        with open(self.file_path, 'wb') as f:
            logger.debug(f'Writing file `{self.file_path}`')
            f.write(self.data)

    @classmethod
    def from_file(cls, file_abspath: str, file_relpath: str, offset: int = 0):
        c = cls()
        c.file_path = file_abspath
        c.rel_path = file_relpath
        c.data = c._get_file_data()
        c.length = len(c.data)
        c.offset = offset
        return c


class Debundler:
    def __init__(self, file_path, metadata_path, output_dir):
        self.file_path = file_path
        self.metadata_path = metadata_path
        self.output_dir = output_dir
        self.file_handler = None
        self.file_handler = self._get_bundle_file_handler()

    def __del__(self):
        if self.file_handler is not None:
            self.file_handler.close()

    def _get_bundle_file_handler(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(
                f'Bundle file `{self.file_path}` not found')
        return open(self.file_path, 'rb')

    @property
    def metadata(self) -> dict:
        if not os.path.isfile(self.metadata_path):
            raise FileNotFoundError(
                f'Metadata file `{self.metadata_path}` not found')
        try:
            with open(self.metadata_path, 'rb') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f'Metadata file `{self.metadata_path}` is not a valid JSON file') from e

    def parse(self):
        added: 'list[dict]' = self.metadata.get('added', None)
        if added is None:
            raise ValueError(
                f'Metadata file `{self.metadata_path}` does not contain `added` field')

        if not os.path.isdir(self.output_dir):
            logger.info(f'Creating output directory `{self.output_dir}`')
            os.makedirs(self.output_dir)
        else:
            if os.listdir(self.output_dir):
                raise FileExistsError(
                    f'Output directory `{self.output_dir}` is not empty')
            logger.info(
                f'Output directory `{self.output_dir}` exists and is empty')

        for file in added:
            FileParser.from_bundle(
                self.file_handler,
                os.path.join(self.output_dir, file['path']),
                file['byteOffset'],
                file['length'],
                b64decode(file['sha256HashBase64Encoded'])
            ).to_file()

        logger.info(f'Debundling completed: {len(added)} files written')


class Bundler:

    APP_VERSION_KEY = 'applicationVersionNumber'
    BUNDLE_VERSION_KEY = 'versionNumber'
    PREV_BUNDLE_VERSION_KEY = 'previousVersionNumber'
    PATH_TO_HASH_KEY = 'pathToHash'
    PATH_TO_DETAILS_KEY = 'pathToDetails'

    PATH_TO_DETAILS_FILES = ['songs/unlocks',
                             'songs/packlist', 'songs/songlist']

    OLD_METADATA_SUFFIX = '.oldjson'

    def __init__(self, input_dir, output_file, output_metadata_file, old_metadata_relpath):
        self.input_dir = input_dir
        self.output_file = output_file
        self.output_metadata_file = output_metadata_file
        self.old_metadata_relpath = old_metadata_relpath + self.OLD_METADATA_SUFFIX
        self.metadata = None

        self.init_file_name()

        self.file_handler = None
        self.metadata_handler = None
        self.file_handler = self._get_bundle_file_handler()
        self.metadata_handler = self._get_metadata_file_handler()

        self.app_version = None
        self.bundle_version = None
        self.prev_bundle_version = None

        self.prev_path_to_hash = {}  # 用来检测文件变更，生成 add 和 remove
        self.prev_path_to_details = {}  # 用来生成 metadata

        self.old_parse()

    def init_file_name(self):
        x = os.path.splitext(self.output_file)
        if x[1] != '.cb':
            self.output_file += '.cb'
            x = os.path.splitext(self.output_file)

        if self.output_metadata_file is None:
            self.output_metadata_file = f'{x[0]}.json'
        else:
            x = os.path.splitext(self.output_metadata_file)
            if x[1] != '.json':
                self.output_metadata_file += '.json'

    def __del__(self):
        if self.file_handler is not None:
            self.file_handler.close()
        if self.metadata_handler is not None:
            self.metadata_handler.close()

    def _get_bundle_file_handler(self):
        if os.path.isfile(self.output_file):
            raise FileExistsError(
                f'Bundle file `{self.output_file}` already exists')
        return open(self.output_file, 'wb')

    def _get_metadata_file_handler(self):
        if os.path.isfile(self.output_metadata_file):
            raise FileExistsError(
                f'Metadata file `{self.output_metadata_file}` already exists')
        return open(self.output_metadata_file, 'w')

    def set_version(self, app_version, bundle_version, previous_bundle_version):
        if app_version is not None:
            self.app_version = app_version
        if bundle_version is not None:
            self.bundle_version = bundle_version
        if previous_bundle_version is not None:
            self.prev_bundle_version = previous_bundle_version

    @property
    def old_metadata_path(self) -> str:
        return os.path.join(self.input_dir, self.old_metadata_relpath)

    @property
    def old_metadata(self) -> list:
        if not os.path.isfile(self.old_metadata_path):
            return []
        with open(self.old_metadata_path, 'rb') as f:
            return json.load(f)

    def get_next_bundle_version(self) -> str:
        if self.bundle_version is not None:
            return self.bundle_version
        prev_version = version_tuple(self.prev_bundle_version)
        length = len(prev_version)
        if length <= 3:
            return f"{'.'.join(map(str, prev_version))}.1"
        return '.'.join(map(str, prev_version[:-1])) + '.' + str(prev_version[-1] + 1)

    def old_parse(self):
        x = None
        max_version = (-1, -1, -1)
        for i in self.old_metadata:
            version = version_tuple(i['versionNumber'])
            if version > max_version:
                max_version = version
                x = i
        if x is None:
            return
        self.prev_bundle_version = x.get(self.BUNDLE_VERSION_KEY, None)
        self.app_version = x.get(self.APP_VERSION_KEY, None)
        self.bundle_version = self.get_next_bundle_version()
        self.prev_path_to_hash = x.get(self.PATH_TO_HASH_KEY, {})
        self.prev_path_to_details = x.get(self.PATH_TO_DETAILS_KEY, {})

    def record_old_metadata(self):
        meta_list = self.old_metadata
        x = self.metadata.copy()
        x.pop('added', None)
        x.pop('removed', None)
        meta_list.append(x)
        with open(self.old_metadata_path, 'w') as f:
            json.dump(meta_list, f)

    def get_path_to_details(self) -> dict:
        r = {}
        for i in self.PATH_TO_DETAILS_FILES:
            file_path = os.path.join(self.input_dir, i)
            if os.path.isfile(file_path):
                x = FileParser.from_file(file_path, i)
                r[i] = x.detail_hash_base64
            else:
                r[i] = self.prev_path_to_details.get(i, None)
                if r[i] is None:
                    logger.warning(
                        f'File `{file_path}` not found and not in old metadata')
        return r

    def generate_uuid(self) -> str:
        return os.urandom(16).hex()[:9]

    def parse(self):
        logger.info(f'Parsing input directory `{self.input_dir}`')

        added = []
        removed = []
        path_to_hash = {}
        offset = 0

        count = [0, 0, 0, 0]  # 0: added, 1: changed, 2: unchanged, 3: removed

        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(self.OLD_METADATA_SUFFIX):
                    continue
                file_path = os.path.join(root, file)
                rel_path = std_path(os.path.relpath(file_path, self.input_dir))

                x = FileParser.from_file(file_path, rel_path, offset)

                path_to_hash[rel_path] = x.file_hash_base64

                prev_file_hash = self.prev_path_to_hash.get(rel_path, None)

                if prev_file_hash is None:
                    added.append(x.to_dict())
                    self.file_handler.write(x.data)
                    logger.debug(f'New file `{rel_path}` added')
                    count[0] += 1
                elif x.file_hash_base64 != prev_file_hash:
                    added.append(x.to_dict())
                    removed.append(rel_path)
                    self.file_handler.write(x.data)
                    logger.debug(f'File `{rel_path}` changed')
                    count[1] += 1
                else:
                    logger.debug(f'File `{rel_path}` unchanged')
                    count[2] += 1
                    continue

                offset += x.length

        for i in self.prev_path_to_hash:
            if i not in path_to_hash:
                removed.append(i)
                logger.debug(f'File `{i}` removed')
                count[3] += 1

        self.metadata = {
            self.BUNDLE_VERSION_KEY: self.bundle_version,
            self.PREV_BUNDLE_VERSION_KEY: self.prev_bundle_version,
            self.APP_VERSION_KEY: self.app_version,
            'uuid': self.generate_uuid(),
            'removed': removed,
            'added': added,
            self.PATH_TO_HASH_KEY: path_to_hash,
            self.PATH_TO_DETAILS_KEY: self.get_path_to_details()
        }

        logger.debug(f'Metadata BUNDLE_VERSION: {self.bundle_version}')
        logger.debug(
            f'Metadata PREV_BUNDLE_VERSION: {self.prev_bundle_version}')
        logger.debug(f'Metadata APP_VERSION: {self.app_version}')
        logger.debug(f'Metadata UUID: {self.metadata["uuid"]}')

        json.dump(self.metadata, self.metadata_handler)

        logger.info(
            f'Bundle metadata written to `{self.output_metadata_file}`')

        logger.info(
            f'Bundle file written to `{self.output_file}`: {offset} bytes ({bytes_format(offset)})')

        self.record_old_metadata()
        logger.info(f'Old metadata recorded to `{self.old_metadata_path}`')

        logger.info(
            f'Bundle completed: {count[0]} added, {count[1]} changed, {count[2]} unchanged, {count[3]} removed')


def main():
    parser = argparse.ArgumentParser(
        prog=APP_NAME, description=DESCRIPTION, formatter_class=argparse.RawTextHelpFormatter)
    sub_parsers = parser.add_subparsers(
        description='Choose the action to perform', title='Actions', required=True, dest='action')

    parser.add_argument('--version', '-v', action='version',
                        version=f'{APP_NAME} {APP_VERSION}')
    parser.add_argument('--verbose', '-V', action='store_true',
                        help='Enable verbose logging', default=False, dest='verbose')

    # debundler
    parser_debundle = sub_parsers.add_parser('debundle', aliases=['d'], help='Debundle a file with metadata',
                                             description='Debundle a file with metadata')
    parser_debundle.add_argument(
        '--input', '-i', type=str, help='The input bundle file to debundle', required=True)
    parser_debundle.add_argument(
        '--metadata', '-m', type=str, help='The metadata JSON file to use', required=True)
    parser_debundle.add_argument(
        '--output', '-o', type=str, help='The output directory; it must be empty or absent', default='output')

    parser_debundle.add_argument('--verbose', '-V', action='store_true',
                                 help='Enable verbose logging', default=False, dest='verbose_sub')

    # bundler
    parser_bundle = sub_parsers.add_parser(
        'bundle', aliases=['b'], help='Bundle a directory', description='Bundle a directory')
    parser_bundle.add_argument(
        '--input', '-i', type=str, help='The input directory to bundle', required=True)
    parser_bundle.add_argument(
        '--output', '-o', type=str, help='The output bundle file name; suffix `.cb` is fixed', default='output.cb')
    parser_bundle.add_argument(
        '--metadata', '-m', type=str, help='The output metadata JSON file name; if not given, it will have the same name with bundle file; suffix `.json` is fixed', default=None)
    parser_bundle.add_argument('--old_metadata', '-om', type=str,
                               help='The old metadata file name for incremental update (path relative to input directory; suffix must be `.oldjson`)', default='metadata')

    parser_bundle.add_argument('--app_version', '-av', type=str,
                               help='The app version to use in metadata', default=None)
    parser_bundle.add_argument('--bundle_version', '-bv', type=str,
                               help='The bundle version to use in metadata', default=None)
    parser_bundle.add_argument('--previous_bundle_version', '-pbv', type=str,
                               help='The previous bundle version to use in metadata', default=None)

    parser_bundle.add_argument('--verbose', '-V', action='store_true',
                               help='Enable verbose logging', default=False, dest='verbose_sub')

    ns = parser.parse_args()
    # print(ns)

    VERBOSE = ns.verbose or ns.verbose_sub
    if VERBOSE:
        logger.setLevel(logging.DEBUG)
    try:
        if ns.action in ['debundle', 'd']:
            x = Debundler(ns.input, ns.metadata, ns.output)
            x.parse()
        elif ns.action in ['bundle', 'b']:
            x = Bundler(ns.input, ns.output, ns.metadata, ns.old_metadata)
            x.set_version(ns.app_version, ns.bundle_version,
                          ns.previous_bundle_version)
            x.parse()
    except Exception as e:
        logger.error(e)
        if VERBOSE:
            print_exc()


if __name__ == '__main__':
    main()
