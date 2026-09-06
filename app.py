from agent import HeatShiftAgent


def main():

    print("=" * 60)
    print("                    HEATSHIFT")
    print("             Heat Safety Operations Agent")
    print("=" * 60)

    try:

        agent = HeatShiftAgent()
        agent.run_once()

    except KeyboardInterrupt:

        print("\nAgent stopped by user.")

    except Exception as e:

        print(f"\n[ERROR] HeatShift failed: {e}")


if __name__ == "__main__":
    main()