import subprocess
import os
import sys
import tempfile

def compile_and_run_cpp_code(cpp_code, gpp_path=r"C:\MinGW\bin\g++.exe"):
    """
    将C++代码保存到临时文件，然后编译并运行
    :param cpp_code: C++代码字符串
    :param gpp_path: g++编译器的完整路径
    :return: 运行结果
    """
    try:
        # 创建临时文件保存C++代码
        temp_dir = tempfile.gettempdir()
        temp_cpp_file = os.path.join(temp_dir, "temp_code.cpp")
        with open(temp_cpp_file, "w") as f:
            f.write(cpp_code)

        # 编译C++代码
        output_file = os.path.join(temp_dir, "temp_code.exe")
        compile_command = [gpp_path, "-o", output_file, temp_cpp_file]
        compile_process = subprocess.run(
            compile_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True  # 在Windows上可能需要添加这个参数
        )

        if compile_process.returncode != 0:
            # 编译失败，返回错误信息
            os.remove(temp_cpp_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            return f"编译错误:\n{compile_process.stderr}"

        # 运行编译后的程序
        run_process = subprocess.run(
            [output_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 删除临时文件
        os.remove(temp_cpp_file)
        os.remove(output_file)

        # 返回运行结果
        if run_process.returncode != 0:
            return f"运行错误:\n{run_process.stderr}"
        else:
            return f"程序输出:\n{run_process.stdout}"

    except Exception as e:
        # 删除临时文件（如果存在）
        if os.path.exists(temp_cpp_file):
            os.remove(temp_cpp_file)
        if os.path.exists(output_file):
            os.remove(output_file)
        return f"发生错误: {str(e)}"

if __name__ == "__main__":
    print("请输入C++代码（输入':exit'结束输入并编译运行）：")

    cpp_code = ""
    while True:
        line = input()
        if line == ":exit":
            break
        cpp_code += line + "\n"

    if not cpp_code:
        print("没有输入C++代码！")
        sys.exit(1)

    result = compile_and_run_cpp_code(cpp_code)
    print(result)