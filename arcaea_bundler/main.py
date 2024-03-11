import argparse
import hmac
import json
import logging
import os
from base64 import b64decode, b64encode
from hashlib import sha256
from traceback import print_exc


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


class FileParser:
    KEY = b'\xd4\x1f\xdb\xe37\xd0\x01h\x0c*MC\xaf\xe5p\xc7\x1f\xde\x85\xd8\xf3\xd4\xc4o7\x99\xc1\x8f\x1fP\x82w\xac\xa7\xabc2\x83q\x0c+\xb4\x1a\x07\x8e\xfb\xe7\xc1\x9c\xf0\x87\xa7\xe17u*\xb7X\x1c\x8d\x9c\x0e=\xe9'

    def __init__(self):
        self.file_path: str = None
        self.offset: int = None
        self.length: int = None

        self.data: bytes = None

    def _get_file_data(self) -> bytes:
        with open(self.file_path, 'rb') as f:
            return f.read()

    @property
    def file_hash(self) -> bytes:
        return sha256(self.data).digest()

    @property
    def detail_hash(self) -> bytes:
        return hmac.new(self.KEY, self.data, sha256).digest()

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
    def __init__(self, input_dir, output_file, output_metadata_file):
        self.input_dir = input_dir
        self.output_file = output_file
        self.output_metadata_file = output_metadata_file
        self.metadata = None

        self.file_handler = None
        self.file_handler = self._get_bundle_file_handler()

    def __del__(self):
        if self.file_handler is not None:
            self.file_handler.close()

    def _get_bundle_file_handler(self):
        if os.path.isfile(self.output_file):
            raise FileExistsError(
                f'Bundle file `{self.output_file}` already exists')
        return open(self.output_file, 'wb')

    def parse(self):
        pass


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
        'bundle', aliases=['b'], help='Bundle a directory')

    parser_bundle.add_argument('--verbose', '-V', action='store_true',
                               help='Enable verbose logging', default=False, dest='verbose_sub')

    ns = parser.parse_args()
    # print(ns)

    VERBOSE = ns.verbose or ns.verbose_sub
    if VERBOSE:
        logger.setLevel(logging.DEBUG)
    try:
        if ns.action in ['debundle', 'd']:
            debundler = Debundler(ns.input, ns.metadata, ns.output)
            debundler.parse()
        elif ns.action in ['bundle', 'b']:
            pass
        else:
            pass
    except Exception as e:
        logger.error(e)
        if VERBOSE:
            print_exc()


if __name__ == '__main__':
    main()
