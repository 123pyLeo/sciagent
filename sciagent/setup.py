"""交互式配置向导模块"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, Any

# 延迟导入以避免循环依赖
def _lazy_import_agent_llm():
    """延迟导入 AgentsLLM"""
    try:
        from .agent_llm import AgentsLLM
        return AgentsLLM
    except ImportError:
        return None

import questionary
from questionary import Style

from .ui import (
    print_banner,
    print_section_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_step,
    create_info_panel,
    print_key_value,
    print_divider,
    console,
)
from .env_checker import EnvironmentChecker


# 自定义样式主题
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),       # 问题标记
    ('question', 'bold'),                # 问题文本
    ('answer', 'fg:#f44336 bold'),      # 回答
    ('pointer', 'fg:#673ab7 bold'),     # 指针
    ('highlighted', 'fg:#673ab7 bold'), # 高亮
    ('selected', 'fg:#cc5454'),         # 已选择
    ('separator', 'fg:#cc5454'),        # 分隔符
    ('instruction', ''),                 # 指令
    ('text', ''),                        # 文本
    ('disabled', 'fg:#858585 italic')   # 禁用
])


class SetupWizard:
    """配置向导"""

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.workdir: Optional[Path] = None

    def run(self) -> bool:
        """运行配置向导"""
        print_banner()
        
        console.print(
            "[dim]欢迎使用 SciAgent! 让我们通过几个简单的步骤来配置您的环境。[/dim]"
        )
        console.print()
        
        # 检查是否已有配置
        existing_config_path = Path.cwd() / ".sciagent.json"
        if existing_config_path.exists():
            console.print()
            print_warning("⚠️  检测到已存在的配置文件")
            console.print()
            
            try:
                choice = questionary.select(
                    "如何处理现有配置？",
                    choices=[
                        "完全重新配置（覆盖所有设置）",
                        "只更新 AI 配置",
                        "取消，保留现有配置"
                    ],
                    style=custom_style
                ).ask()
                
                if choice == "取消，保留现有配置":
                    print_info("已取消配置")
                    return False
                elif choice == "只更新 AI 配置":
                    # 只运行 AI 配置部分
                    print_info("正在更新 AI 配置...")
                    console.print()
                    return self._update_ai_config_only()
                # else: 继续完整配置流程（覆盖）
                console.print()
                print_warning("将覆盖现有配置...")
                console.print()
            except KeyboardInterrupt:
                console.print()
                print_info("已取消配置")
                return False
        
        # 第一步：环境检测
        if not self._step_environment_check():
            return False
        
        # 第二步：项目配置
        if not self._step_project_setup():
            return False
        
        # 第三步：高级配置
        if not self._step_advanced_config():
            return False
        
        # 第四步：保存配置
        if not self._step_save_config():
            return False
        
        # 完成
        self._step_completion()
        
        return True

    def _step_environment_check(self) -> bool:
        """步骤1：环境检测"""
        print_section_header("📋 步骤 1/4: 环境检测")
        
        print_info("正在检测您的系统环境...")
        console.print()
        
        checker = EnvironmentChecker()
        checker.run_all_checks()
        console.print()
        checker.print_results()
        
        summary = checker.get_summary()
        console.print()
        
        if summary["failed"] > 0:
            print_warning(
                f"发现 {summary['failed']} 个问题，但您仍可以继续。"
            )
            
            continue_anyway = questionary.confirm(
                "是否继续配置？",
                default=True,
                style=custom_style
            ).ask()
            
            if not continue_anyway:
                print_info("配置已取消。")
                return False
        else:
            print_success("所有检测通过！")
        
        console.print()
        return True

    def _step_project_setup(self) -> bool:
        """步骤2：项目配置"""
        print_section_header("🎯 步骤 2/4: 项目配置")
        
        # 工作目录
        default_workdir = Path.cwd()
        workdir_input = questionary.path(
            "选择工作目录:",
            default=str(default_workdir),
            style=custom_style
        ).ask()
        
        if not workdir_input:
            return False
        
        self.workdir = Path(workdir_input).expanduser().resolve()
        self.config["workdir"] = str(self.workdir)
        
        # 项目名称
        project_name = questionary.text(
            "项目名称:",
            default=self.workdir.name,
            style=custom_style
        ).ask()
        
        if not project_name:
            return False
        
        self.config["project_name"] = project_name
        
        # 状态目录
        state_dir = questionary.path(
            "SciAgent 状态保存目录:",
            default=str(self.workdir / ".sciagent"),
            style=custom_style
        ).ask()
        
        if not state_dir:
            return False
        
        self.config["state_dir"] = state_dir
        
        console.print()
        print_success(f"项目名称: {project_name}")
        print_success(f"工作目录: {self.workdir}")
        console.print()
        
        return True

    def _step_advanced_config(self) -> bool:
        """步骤3：高级配置"""
        print_section_header("⚙️  步骤 3/4: 高级配置")
        
        # 是否配置高级选项
        configure_advanced = questionary.confirm(
            "是否配置高级选项？",
            default=False,
            style=custom_style
        ).ask()
        
        if not configure_advanced:
            console.print()
            print_info("跳过高级配置，使用默认设置。")
            console.print()
            return True
        
        console.print()
        
        # 主要监控指标配置
        metric_choice = questionary.select(
            "主要监控指标（用于对比历史运行）如何确定？",
            choices=[
                "自动检测（推荐）- 系统会智能识别最重要的指标",
                "手动指定 - 自己输入指标名称"
            ],
            style=custom_style
        ).ask()
        
        if metric_choice and "手动指定" in metric_choice:
            primary_metric = questionary.text(
                "请输入主要监控指标名称 (如 accuracy, f1_score, loss):",
                default="",
                style=custom_style
            ).ask()
            
            if primary_metric:
                self.config["primary_metric"] = primary_metric
                print_success(f"✓ 主要指标已设置: {primary_metric}")
            else:
                print_info("未设置主要指标，将使用自动检测")
        else:
            print_info("✓ 将使用自动检测（从 accuracy, f1, loss 等常见指标中智能选择）")
        
        console.print()
        
        # 是否启用 Git 集成
        enable_git = questionary.confirm(
            "是否启用 Git 集成 (记录 commit hash)?",
            default=True,
            style=custom_style
        ).ask()
        
        self.config["enable_git"] = enable_git
        
        # 是否启用 AI 分析
        enable_ai = questionary.confirm(
            "是否启用 AI 分析功能 (需要配置 LLM API)?",
            default=True,
            style=custom_style
        ).ask()
        
        self.config["enable_ai"] = enable_ai
        
        if enable_ai:
            console.print()
            print_info("AI 分析功能需要配置 LLM API（如 OpenAI、DeepSeek、通义千问等）")
            print_info("请在 .env 文件中配置相关环境变量")
            print_info("参考: .env.example")
            
            # 询问是否现在配置
            configure_now = questionary.confirm(
                "是否现在配置 LLM API?",
                default=False,
                style=custom_style
            ).ask()
            
            if configure_now:
                self._configure_llm_api()
        
        console.print()
        return True

    def _step_save_config(self) -> bool:
        """步骤4：保存配置"""
        print_section_header("💾 步骤 4/4: 保存配置")
        
        # 显示配置摘要
        console.print("[bold]配置摘要:[/bold]")
        console.print()
        
        print_key_value("项目名称", self.config.get("project_name"))
        print_key_value("工作目录", self.config.get("workdir"))
        print_key_value("状态目录", self.config.get("state_dir"))
        
        if self.config.get("enable_ai"):
            print_key_value("AI 分析", f"已启用 ({self.config.get('llm_provider', 'auto')})")
        else:
            print_key_value("AI 分析", "未启用")
        
        console.print()
        print_divider()
        console.print()
        
        # 确认保存
        confirm_save = questionary.confirm(
            "确认保存配置？",
            default=True,
            style=custom_style
        ).ask()
        
        if not confirm_save:
            print_warning("配置未保存。")
            return False
        
        # 保存配置文件
        config_file = Path(self.config["workdir"]) / ".sciagent.json"
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            console.print()
            print_success(f"配置已保存到: {config_file}")
            
        except Exception as e:
            print_error(f"保存配置失败: {e}")
            return False
        
        console.print()
        return True

    def _configure_llm_api(self):
        """配置 LLM API - 交互式选择（支持重试）"""
        console.print()
        print_info("让我们配置 AI 分析功能所需的 LLM API")
        console.print()
        
        # 外层循环：允许重新选择提供商
        while True:
            result = self._configure_llm_api_inner()
            if result in ["success", "skip"]:
                break
            elif result == "retry_provider":
                console.print()
                print_info("重新选择提供商...")
                console.print()
                continue
            else:  # "cancel"
                print_warning("已取消 AI 配置")
                break
    
    def _configure_llm_api_inner(self):
        """内部配置函数（单次尝试）"""
        # 提供商信息字典
        provider_info = {
            "openai": {
                "name": "OpenAI",
                "default_model": "gpt-5.1",
                "models": ["gpt-5.1", "gpt-5-mini", "gpt-5.1-codex", "gpt-4.1"],
                "api_key_hint": "sk-proj-...",
                "website": "https://platform.openai.com/",
                "need_vpn": True
            },
            "deepseek": {
                "name": "DeepSeek",
                "default_model": "deepseek-chat",
                "models": ["deepseek-chat", "deepseek-reasoner"],
                "api_key_hint": "sk-...",
                "website": "https://platform.deepseek.com/",
                "need_vpn": False
            },
            "qwen": {
                "name": "通义千问 (Qwen)",
                "default_model": "qwen-plus",
                "models": ["qwen-plus", "qwen-max"],
                "api_key_hint": "sk-...",
                "website": "https://dashscope.console.aliyun.com/",
                "need_vpn": False
            },
            "kimi": {
                "name": "Kimi (Moonshot)",
                "default_model": "moonshot-v1-8k",
                "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
                "api_key_hint": "sk-...",
                "website": "https://platform.moonshot.cn/",
                "need_vpn": False
            },
            "zhipu": {
                "name": "智谱 AI (GLM)",
                "default_model": "glm-4.6",
                "models": ["glm-4.6", "glm-4.5", "glm-4.5-air", "glm-4.5-flash"],
                "api_key_hint": "xxx",
                "website": "https://open.bigmodel.cn/",
                "need_vpn": False
            },
            "gemini": {
                "name": "Gemini (Google)",
                "default_model": "gemini-2.5-flash",
                "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
                "api_key_hint": "AIza...",
                "website": "https://ai.google.dev/",
                "need_vpn": True
            },
            "claude": {
                "name": "Claude (Anthropic)",
                "default_model": "claude-sonnet-4-5",
                "models": ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-1"],
                "api_key_hint": "sk-ant-...",
                "website": "https://console.anthropic.com/",
                "need_vpn": True
            },
            "custom": {
                "name": "自定义 API（任何 OpenAI 兼容接口）",
                "default_model": "gpt-3.5-turbo",
                "models": [],
                "api_key_hint": "your-api-key",
                "website": "",
                "need_vpn": False
            }
        }
        
        # 显示提供商列表
        provider_choices = []
        for key, info in provider_info.items():
            vpn_tag = " 🌐需要VPN" if info.get("need_vpn") else ""
            label = f"{info['name']}{vpn_tag}"
            provider_choices.append({"name": label, "value": key})
        
        provider = questionary.select(
            "选择 LLM 提供商:",
            choices=provider_choices,
            style=custom_style
        ).ask()
        
        if not provider:
            return "cancel"
        
        info = provider_info[provider]
        
        # 内层循环：允许重试当前提供商的配置
        while True:
            console.print()
            print_key_value("提供商", info['name'])
            print_key_value("推荐模型", info['default_model'])
            if info['website']:
                print_key_value("获取 API Key", info['website'])
            console.print()
            
            # 选择或输入模型
            if info['models']:
                use_custom_model = False
                model_choices = info['models'] + ["其他（手动输入）"]
                
                model = questionary.select(
                    "选择模型:",
                    choices=model_choices,
                    default=info['default_model'],
                    style=custom_style
                ).ask()
                
                if model == "其他（手动输入）":
                    use_custom_model = True
                
                if use_custom_model or not model:
                    model = questionary.text(
                        "输入模型名称:",
                        default=info['default_model'],
                        style=custom_style
                    ).ask()
            else:
                model = questionary.text(
                    "输入模型名称:",
                    default=info['default_model'],
                    style=custom_style
                ).ask()
            
            # 输入 API Key
            api_key = questionary.password(
                f"输入 API Key (示例: {info['api_key_hint']}):",
                style=custom_style
            ).ask()
            
            if not api_key:
                print_warning("未输入 API Key")
                retry_choice = questionary.select(
                    "接下来?",
                    choices=[
                        "重新输入",
                        "换个提供商",
                        "跳过 AI 配置"
                    ],
                    style=custom_style
                ).ask()
                if retry_choice == "重新输入":
                    continue
                elif retry_choice == "换个提供商":
                    return "retry_provider"
                else:
                    return "skip"
            
            # Base URL 配置
            if provider == "custom":
                base_url = questionary.text(
                    "输入 API Base URL:",
                    default="http://localhost:8080/v1",
                    style=custom_style
                ).ask()
            else:
                base_url = None  # 使用默认
            
            # 测试连接
            console.print()
            test_connection = questionary.confirm(
                "是否测试 API 连接?",
                default=True,
                style=custom_style
            ).ask()
            
            connection_ok = True
            if test_connection:
                if self._test_llm_connection(provider, api_key, base_url, model):
                    console.print()
                    print_success("✓ API 连接测试成功！")
                    console.print()
                else:
                    console.print()
                    print_warning("⚠️  API 连接测试失败")
                    console.print()
                    
                    # 提供多个选项
                    retry_choice = questionary.select(
                        "接下来?",
                        choices=[
                            "重新输入 API Key",
                            "重新选择模型",
                            "换个提供商",
                            "跳过测试，直接保存",
                            "放弃 AI 配置"
                        ],
                        style=custom_style
                    ).ask()
                    
                    if retry_choice == "重新输入 API Key":
                        continue  # 重新开始当前提供商的配置
                    elif retry_choice == "重新选择模型":
                        continue  # 重新开始当前提供商的配置
                    elif retry_choice == "换个提供商":
                        return "retry_provider"  # 回到外层循环
                    elif retry_choice == "跳过测试，直接保存":
                        print_info("跳过测试，保存配置...")
                        connection_ok = True  # 允许保存
                    else:  # "放弃 AI 配置"
                        return "cancel"
            
            # 保存到配置
            self.config["llm_provider"] = provider
            self.config["llm_api_key"] = api_key
            self.config["llm_model"] = model or info['default_model']
            if base_url:
                self.config["llm_base_url"] = base_url
            
            console.print()
            print_success("✓ LLM API 配置已保存")
            print_info(f"提供商: {info['name']}")
            print_info(f"模型: {self.config['llm_model']}")
            console.print()
            
            return "success"
    
    def _test_llm_connection(self, provider: str, api_key: str, base_url: Optional[str], model: str) -> bool:
        """测试 LLM API 连接"""
        try:
            AgentsLLM = _lazy_import_agent_llm()
            if not AgentsLLM:
                print_warning("无法导入 AgentsLLM 模块")
                return False
            
            print_info("正在测试 API 连接...")
            
            # 临时创建 LLM 实例
            llm = AgentsLLM(
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=10
            )
            
            # 发送一个简单的测试请求
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OK' if you can read this."}
            ]
            
            response_text = ""
            for chunk in llm.think(test_messages, temperature=0):
                response_text += chunk
                if len(response_text) > 10:  # 收到响应就算成功
                    break
            
            return True
            
        except Exception as e:
            print_error(f"连接测试失败: {str(e)[:100]}")
            return False
    
    def _create_env_example(self):
        """创建 .env 示例文件"""
        env_example_path = Path(self.config["workdir"]) / ".env.example"
        
        env_content = """# SciAgent LLM 配置示例
# 复制此文件为 .env 并填入实际的 API 密钥

# 通用配置（适用于所有提供商）
# LLM_API_KEY=your_api_key_here
# LLM_BASE_URL=https://api.example.com/v1
# LLM_MODEL_ID=model_name

# OpenAI
# OPENAI_API_KEY=sk-...

# DeepSeek
# DEEPSEEK_API_KEY=sk-...

# 通义千问 (Qwen)
# DASHSCOPE_API_KEY=sk-...

# Kimi (Moonshot)
# KIMI_API_KEY=sk-...
# MOONSHOT_API_KEY=sk-...

# 智谱 AI (GLM)
# ZHIPU_API_KEY=...
# GLM_API_KEY=...

# Ollama (本地)
# OLLAMA_HOST=http://localhost:11434/v1
# OLLAMA_API_KEY=ollama

# 其他参数
# LLM_TEMPERATURE=0.7
# LLM_MAX_TOKENS=2000
# LLM_TIMEOUT=60
"""
        
        try:
            with open(env_example_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            print_success(f".env 示例已保存到: {env_example_path}")
            print_info("请复制 .env.example 为 .env 并填入实际的 API 密钥")
        except Exception as e:
            print_warning(f"保存 .env 示例失败: {e}")
    
    def _step_completion(self):
        """完成步骤"""
        console.print()
        print_divider()
        console.print()
        
        completion_text = (
            "SciAgent 已成功配置！您现在可以开始使用了。\n\n"
            "快速开始:\n"
            f"  sciagent run --cmd 'python train.py' --workdir {self.config['workdir']}\n\n"
            "查看帮助:\n"
            "  sciagent --help\n\n"
            "查看运行历史:\n"
            "  sciagent history"
        )
        
        # 如果启用了 AI，添加相关说明
        if self.config.get("enable_ai"):
            completion_text += (
                "\n\nAI 分析功能:\n"
                "  sciagent analyze              # 分析最新运行\n"
                "  sciagent analyze --run-id XXX  # 分析指定运行\n\n"
                "💡 提示: 请配置 .env 文件以使用 AI 分析功能"
            )
        
        create_info_panel(
            "✨ 配置完成！",
            completion_text,
            style="green"
        )
        
        console.print()
    
    def _update_ai_config_only(self) -> bool:
        """只更新 AI 配置（不改变其他设置）"""
        config_file = Path.cwd() / ".sciagent.json"
        
        # 读取现有配置
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print_success("✓ 已加载现有配置")
            console.print()
        except Exception as e:
            print_error(f"读取配置失败: {e}")
            return False
        
        # 运行 AI 配置
        self._configure_llm_api()
        
        # 保存更新后的配置
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            console.print()
            print_success(f"✓ AI 配置已更新: {config_file}")
            console.print()
            return True
        except Exception as e:
            print_error(f"保存配置失败: {e}")
            return False


def run_init_wizard() -> int:
    """运行初始化向导"""
    wizard = SetupWizard()
    
    try:
        success = wizard.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        console.print()
        print_warning("配置已取消。")
        return 1
    except Exception as e:
        console.print()
        print_error(f"配置过程中发生错误: {e}")
        return 1

