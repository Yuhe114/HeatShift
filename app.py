from agent import HeatShiftAgent


def main():

    print("=" * 60)
    print("              HEATSHIFT")
    print("      Heat Safety Operations Agent")
    print("=" * 60)

    agent = HeatShiftAgent()

    agent.run_once()


if __name__ == "__main__":
    main()