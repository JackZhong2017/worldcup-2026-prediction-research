from pathlib import Path

from .statsbomb import collect


def main() -> None:
    output = Path("data/processed/statsbomb-international-xg.json")
    records = collect(output)
    print(f"Saved {len(records)} matches to {output}")


if __name__ == "__main__":
    main()
