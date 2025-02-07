import grpc_tools.protoc


def replace(file_path, original, replacement):
    # 打开文件并读取内容
    with open(file_path, 'r') as file:
        content = file.read()

    # 进行替换
    updated_content = content.replace(original, replacement)

    # 将更新后的内容写回文件
    with open(file_path, 'w') as file:
        file.write(updated_content)


def main():
    # 定义 proto 文件和输出目录
    proto_root = './proto'
    proto_files = ['remote.proto', 'types.proto', 'gogoproto/gogo.proto']
    output_dir = './prometheus_remote_writer/proto'

    # 调用 protoc 命令生成 Python 文件
    grpc_tools.protoc.main((
        '',
        f'-I{proto_root}',  # 指定 proto 文件的根目录
        f'--python_out={output_dir}',  # 指定生成的 Python 文件的输出目录
        *proto_files,  # 需要编译的 proto 文件
    ))

    # 调用函数并传入文件路径
    replace(f'{output_dir}/remote_pb2.py', 'from gogoproto', 'from .gogoproto')
    replace(f'{output_dir}/remote_pb2.py', 'import types_pb2', 'from . import types_pb2')
    replace(f'{output_dir}/types_pb2.py', 'from gogoproto', 'from .gogoproto')


if __name__ == '__main__':
    main()
