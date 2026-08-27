import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <assembly_file>")
        sys.exit(1)

    # current assembly file (.s) that will be assembled by your code.
    assembly_file = sys.argv[1]

    # Additional code in main goes under here
    # ---------------------------------------

if __name__ == "__main__":
    main()