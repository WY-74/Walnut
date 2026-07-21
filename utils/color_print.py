class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def system_print(message):
    print(f"{Colors.YELLOW}WALNUT:{Colors.RESET} {message}")
