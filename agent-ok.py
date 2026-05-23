"""主入口：默认启动 Web 界面，也可通过 --cli 使用终端模式"""

import sys

if __name__ == "__main__":
    if "--cli" in sys.argv:
        from cli import run_cli
        run_cli()
    else:
        from app import launch
        launch()
