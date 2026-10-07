# dnf-rev

可公开、可独立构建的原生资源工具基础层。包含 C++17 NPK/IMG v2 解码器、Python/SDL2 素材查看器，以及无需原游戏素材的合成测试。

本仓库是现有工作的公开子集，不代表全部成果。

这不是完整游戏移植或安装包。人物移动、战斗、HP、AI、联网和完整倒地流程不在本仓库的可运行范围内。历史研究与条件场景没有通过删依赖的方式塞入这里。

## 当前内容

- 数值目录与有界 IMG v2 解码，支持已覆盖的像素格式、压缩和帧引用
- 可选名称目录读取；资源内部名称不作为输出文件路径
- 原生共享库、SDL2 本地查看器、输入状态与最终呈现四边形的有限模型
- 合成像素、损坏输入、输出保护、平台加载和 C++ 单元测试
- 自行生成的色块示例，不包含原角色、地图或声音

详细范围见 [docs/STATUS.md](docs/STATUS.md)，输入约定见 [docs/ASSETS.md](docs/ASSETS.md)。

## 依赖

需要本机 C++17 编译器、zlib 开发头文件和库、Python 3.10+。打开窗口还需要与 Python 进程架构一致的 SDL2 动态库。没有 pip 依赖，也不会自动下载或安装软件。

构建脚本支持 Linux 和 macOS。Mac 还需要 Apple 编译工具及 SDK；脚本默认目标为 x86_64 / macOS 15.0，Apple Silicon 可显式选择 arm64。Mac 实机窗口和音频尚未验收，Linux 动态库不能改名后当作 Mac 库使用。

## 不使用原版资产也能构建和测试

```sh
sh build.sh
python3 -B -m unittest discover -s tests -v
python3 -B -O -m unittest discover -s tests -v
```

Mac 的 arm64 构建选项：

```sh
DNF_MACOS_ARCH=arm64 sh build.sh
```

生成三个原创色块帧并查看：

```sh
python3 tools/generate_demo.py artifacts/demo/shapes.NPK
./build/npk_preview --inspect artifacts/demo/shapes.NPK
python3 native_viewer.py --samples artifacts/demo --receipt artifacts/demo-session.json
```

输出路径必须尚未存在。再次执行时使用新的输出路径。查看器按键：左右箭头切帧、空格播放/暂停、上箭头切条目、Tab切包、加减号缩放、Esc或关闭窗口退出。播放速度是展示选择。

安装SDL2后可运行不打开可见窗口的合成资源烟测：

```sh
python3 -B tests/native_smoke.py
```

也可通过 `--samples` 指向自己有权使用的本地 NPK 目录。不得将那些文件提交到仓库。自定义 SDL2 路径可通过 `DNF_SDL2_LIBRARY` 指定；该路径只在本机使用。

## 发布边界

不分发原游戏 EXE/DLL、PVF、NPK、角色图片、音视频、转储、凭据、机器路径、私有链接或原进程地址/反汇编资料。代码中保留的是有限且已测试的资源工具，不能据此宣称原客户端、完整战斗或原 GPU 像素已复现。

仓库暂未指定开源许可证；此 README 不授予第三方游戏资产的使用或再分发权。
