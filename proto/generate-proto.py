import grpc_tools.protoc


def main():
    # 定义 proto 文件和输出目录
    proto_files = ['./remote.proto', './types.proto', './gogoproto/gogo.proto']
    output_dir = '../src/prometheus_remote_writer'

    # 调用 protoc 命令生成 Python 文件
    grpc_tools.protoc.main((
        '',
        '-I.',  # 指定 proto 文件的根目录
        f'--python_out={output_dir}',  # 指定生成的 Python 文件的输出目录
        *proto_files,  # 需要编译的 proto 文件
    ))


if __name__ == '__main__':
    main()
