# Arcaea-Bundler

Arcaea Bundler is a tool to bundle or debundle content bundles of Arcaea.

Related: [Arcaea-Server](https://github.com/Lost-MSth/Arcaea-server)

[README 中文](https://github.com/Lost-MSth/Arcaea-Bundler/blob/main/README.cn.md)

## Usage

```bash
# Unpack a pair of bundle and metadata
# For multi-part bundles, the file names should be `input_0.cb`, `input_1.cb`, etc.
python main.py d -i input.cb -m input.json -o output_dir

# Pack a folder
python main.py b -i input_dir -o output_file_name
# Pack a folder with specifing version
python main.py b -i input_dir -o output_file_name -av app_verion -bv bundle_version

# Get help of all arguments
python main.py -h  # Main help
python main.py d -h  # Debundler help
python main.py b -h  # Bundler help
```

When you bundle a folder at **first** time, please specify version information by giving arguments `-av` and `-bv`. After the first time, the program will record the previous metadata in `metadata.oldjson`, and then the program will automatically generate the next version number. Meanwhile, this means that future packaging of this folder will only include the changes made within it, rather than integrating all files.

Bundle folder is equal to `assets`, which must include `songs/songlist`, `songs/packlist` and `songs/unlocks`.

Since client version 6.14.0, only multi-part bundles are accepted. So the script enables multi-part splitting by default, with a max part size of 100MB. You can also disable multi-part splitting by giving argument `-dp`, which will generate old-version bundle. If multi-part splitting is enabled, the generated bundle files will end with `_0.cb`, `_1.cb`, etc.
