# Arcaea-Bundler

Arcaea Bundler 是一个针对 Arcaea 内容捆绑包（热更新包）进行拆包和打包的工具

相关项目：[Arcaea-Server](https://github.com/Lost-MSth/Arcaea-server/graphs/traffic)

[README English](https://github.com/Lost-MSth/Arcaea-Bundler/blob/main/README)

## 使用说明

```bash
# 解包一对内容捆绑包和元数据
python main.py d -i input.cb -m input.json -o output_dir

# 打包一个文件夹
python main.py b -i input_dir -o output_file_name
# 打包一个文件夹，指定其相应版本
python main.py b -i input_dir -o output_file_name -av app_verion -bv bundle_version

# 获取所有参数说明
python main.py -h  # 总说明
python main.py d -h  # 解包器说明
python main.py b -h  # 打包器说明
```

当你**第一次**打包一个文件夹的时候，请指定版本信息，用 `-av` 指定此包用于的客户端版本号，用 `-bv` 指定包的版本号。第一次之后，程序会在 `metadata.oldjson` 中记录下过去的元数据，下次打包这个文件夹的时候就会自动生成版本号了。同时这意味着，往后对于此文件夹的打包只包含其中的改动项，而非全整合

打包文件夹等同于 `assets` 文件夹，必须包含文件 `songs/songlist`、`songs/packlist` 和 `songs/unlocks`
