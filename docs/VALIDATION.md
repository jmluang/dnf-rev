# 本次公开导出的验证

日期：2026-10-07 UTC。

在 Linux x86_64、Python 3.12、现有本机编译器/zlib/SDL2 环境中执行：

- `sh build.sh`：C++17编译通过；22项输入契约检查通过；四边形的4组尺寸、布局/UV/拓扑以及5个非法尺寸检查通过。
- `python3 -B -m unittest discover -s tests -v`：43项通过，零跳过。
- `python3 -B -O -m unittest discover -s tests -v`：43项通过，零跳过。
- `python3 -B tests/native_smoke.py`：真实SDL2 dummy后端和C++解码器运行3帧，1个纹理和1个包均释放。

测试只使用代码生成的颜色像素和格式结构，没有读取原游戏安装、图片、音频、PVF、EXE或DLL。单元测试中对无效路径的字符串是人工测试数据，不是机器路径或私人资料。

上述结果不等于macOS实机、原游戏行为、全部资源版本或原GPU像素的验收。实际NPK文件兼容性需要用户在其授权范围内另行验证，不能把缺少原素材的测试列作已通过。
