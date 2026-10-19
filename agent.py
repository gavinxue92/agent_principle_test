import os
os.environ["HF_HOME"] = r"D:\Tools\huggingface_cache" # 把路径改成你想存放的 D 盘文件夹
import ast
import inspect
import re
from string import Template
from typing import List, Optional, Tuple

import click
from dotenv import load_dotenv
from openai import OpenAI
import platform

from prompt_template import react_system_prompt_template

class ReActAgent:
    def __init__(self, tools: List[callable], model: str = "gpt-4o", project_directory: Optional[str] = None):
        self.tools = {func.__name__: func for func in tools}
        self.model = model
        # 设置项目目录，如果没有提供则使用当前工作目录
        self.project_directory = project_directory or os.getcwd()
        load_dotenv()  # 加载 .env 文件中的环境变量
        self.client = OpenAI(
            base_url=self.get_openrouter_base_url(),
            api_key=self.get_api_key(),
        )

    def run(self, user_question: str) -> str:
        # 构建消息列表
        messages = [
            {"role": "system", "content": self.render_system_prompt(react_system_prompt_template)},
            {"role": "user", "content": f"<question>{user_question}</question>"},
        ]
        while True:
            # 调用模型获取响应
            content = self.call_model(messages)
            # 解析模型响应中的思考内容
            thought_match = re.search(r"<thought>(.*?)</thought>", content, re.DOTALL)
            # 解析模型响应中的行动内容
            if thought_match:
                thought = thought_match.group(1)
                print(f"\n\n💭 Thought: {thought}")

            # 解析模型最终答案
            if "<final_answer>" in content:
                final_answer_match = re.search(r"<final_answer>(.*?)</final_answer>", content, re.DOTALL)
                return final_answer_match.group(1)

            action_match = re.search(r"<action>(.*?)</action>", content, re.DOTALL)
            if not action_match:
                raise ValueError("No <action> found in the model's response.")
            action = action_match.group(1)

            # 解析工具名称和参数
            tool_name, args = self.parse_action(action)
            print(f"\n\n🔧 Action: {tool_name}({', '.join(args)})")

            # 确定是否执行的是 run_terminal_command 工具，如果是，则询问用户是否继续
            should_continue = input("Do you want to continue? (y/n): ").strip().lower() if tool_name == "run_terminal_command" else "y"
            if should_continue.lower() != "y":
                print("Stopping execution as per user request.")
                return "Execution stopped by user."

            # 执行工具并获取观察结果
            try:
                observation = self.tools[tool_name](*args)
            except Exception as e:
                observation = f"Error executing tool {tool_name}: {str(e)}"

            print(f"\n\n🔍 Observation：{observation}")
            obs_message = {"role": "user", "content": f"<observation>{observation}</observation>"}
            messages.append(obs_message)

    # 获取可用工具的列表和描述
    def get_tool_list(self) -> str:
        # 获取可用工具的列表和描述
        tool_descriptions = []
        for tool in self.tools.values():
            name = tool.__name__
            signature = inspect.signature(tool)
            doc = inspect.getdoc(tool) or "No description available."
            tool_descriptions.append(f"{name}{signature}: {doc}")
        return "\n".join(tool_descriptions)

    
    def render_system_prompt(self, template: str) -> str:
        # 渲染系统提示模板，替换工具列表、操作系统信息和当前目录下的文件列表
        tools = self.get_tool_list()
        # 获取当前目录下的文件列表，并将其转换为绝对路径
        file_list = ",".join(
            os.path.abspath(os.path.join(self.project_directory, f)) 
            for f in os.listdir(self.project_directory)
        )
        return Template(template).substitute(
            tool_list=tools,
            operating_system=f"{platform.system()} {platform.release()}",
            file_list=file_list
        )

    # 获取OPENROUTER_API_KEY 
    def get_api_key(self) -> str:
        # 从环境变量中获取 OpenAI API Key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API Key not found in environment variables.")
        return api_key       

    # 获取OPENROUTER_API_BASE_URL
    def get_openrouter_base_url(self) -> str:
        # 从环境变量中获取 OpenRouter API Base URL
        base_url = os.getenv("OPENROUTER_API_BASE_URL")
        if not base_url:
            raise ValueError("OpenRouter API Base URL not found in environment variables.")
        return base_url

    # 调用模型并返回响应内容
    def call_model(self, messages: List[dict]) -> str:
        print("Calling model, Please wait...")
        # 调用模型并返回响应内容
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
            # temperature=0.7,
            # max_tokens=1500
        )
        content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        return content

    # 解析工具名称和参数
    def parse_action(self, action: str) -> Tuple[str, List[str]]:
        # 使用正则表达式解析工具名称和参数
        match = re.match(r"(\w+)\((.*)\)", action, re.DOTALL)
        if not match:
            raise ValueError(f"Invalid action format: {action}")
        tool_name = match.group(1)
        args_str = match.group(2).strip()
          # 手动解析参数，特别处理包含多行内容的字符串
        args = []
        current_arg = ""
        in_string = False
        string_char = None
        i = 0
        paren_depth = 0
        
        while i < len(args_str):
            char = args_str[i]
            
            if not in_string:
                if char in ['"', "'"]:
                    in_string = True
                    string_char = char
                    current_arg += char
                elif char == '(':
                    paren_depth += 1
                    current_arg += char
                elif char == ')':
                    paren_depth -= 1
                    current_arg += char
                elif char == ',' and paren_depth == 0:
                    # 遇到顶层逗号，结束当前参数
                    args.append(self.parse_single_argument(current_arg.strip()))
                    current_arg = ""
                else:
                    current_arg += char
            else:
                current_arg += char
                if char == string_char and (i == 0 or args_str[i-1] != '\\'):
                    in_string = False
                    string_char = None
            
            i += 1
        
        # 添加最后一个参数
        if current_arg.strip():
            args.append(self.parse_single_argument(current_arg.strip()))
        
        return tool_name, args

    def parse_single_argument(self, arg: str) -> str:
        arg = arg.strip()
        if(arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            # 移除外层引号并处理转义字符
            inner_str = arg[1:-1]
            # 处理常见的转义字符
            inner_str = inner_str.replace('\\"', '"').replace("\\'", "'")
            inner_str = inner_str.replace('\\n', '\n').replace('\\t', '\t')
            inner_str = inner_str.replace('\\r', '\r').replace('\\\\', '\\')
            return inner_str
        # 尝试使用 ast.literal_eval 解析其他类型
        try:
            return ast.literal_eval(arg)
        except (SyntaxError, ValueError):
            # 如果解析失败，返回原始字符串
            return arg


# 读取文件内容
def read_file(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

# 写入文件内容
def write_to_file(file_path: str, content: str) -> str:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        return "写入成功"

def run_terminal_command(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return "执行成功" if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error executing command: {str(e)}"

@click.command()
@click.option('--directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
def main(directory: Optional[str] = "snake"):
    # 定义可用工具
    tools = [read_file, write_to_file, run_terminal_command]
    agent = ReActAgent(tools=tools, model="deepseek/deepseek-chat", project_directory=directory)
    user_question = input("请输入你的问题: ")
    final_answer = agent.run(user_question)
    print(f"\n\n✅ Final Answer：{final_answer}")


if __name__ == "__main__":
    main()  # 使用当前工作目录作为项目目录