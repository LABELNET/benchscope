# 【已废弃 / DEPRECATED】
#
# 本文件已迁移至 benchscope/bench_params.py。
#
# 原因：benchscope/benchs.py（引擎注册表模块）与 benchscope/benchs/（包目录）同名，
# Python 会将 `benchscope.benchs` 解析为模块而非包，导致 `benchscope.benchs.params` 导入失败：
#   ModuleNotFoundError: No module named 'benchscope.benchs.params';
#   'benchscope.benchs' is not a package
#
# 请勿在此添加代码；使用 benchscope.bench_params。
# 该空文件仅因删除操作未获授权而保留，可安全删除整个 benchscope/benchs/ 目录。
