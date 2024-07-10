import os

def main():
    print("Hello, World!")

    # Example of nested file content
    print("Here's an example of a nested file:")
    print(\"\"\"
# File /nested/example.txt
This is a nested file example.
It shouldn't be parsed as a separate file.
# EndFile /nested/example.txt
    \"\"\")

if __name__ == "__main__":
    main()