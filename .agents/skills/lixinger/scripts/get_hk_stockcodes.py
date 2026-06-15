import os
import requests
import argparse


def get_hk_stockcodes(name: str) -> str:
    response = requests.post(
        url="https://open.lixinger.com/api/hk/index",
        json={"token": os.environ.get('LIXINGER_TOKEN')},
    )

    data = response.json()
    for item in data.get("data", []):
        if item.get("name") == name:
            return item.get("stockCode", [])

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    print(get_hk_stockcodes(args.name))
