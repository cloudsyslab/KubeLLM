import sys
import ast

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <file_path1> [<file_path2> ...]")
        sys.exit(1)

    file_paths = sys.argv[1:]  # Get all arguments after script name
    print(f"Processing {len(file_paths)} file(s)")

    for file_path in file_paths:
        print(f"\nAttempting to open file: {file_path}")
        
        try:
            with open(file_path, 'r') as file:
                print("File opened successfully")
                metadata = None
                for line in file:
                    line = line.strip()
                    if not line or line.startswith("-----"):  # Skip empty lines and separators
                        continue

                    if line.startswith("("):  # Metadata line
                        metadata = line
                    elif line.startswith("Result: ") and metadata:  # Result line
                        try:
                            dict_str = line[len("Result: "):]  # Extract dictionary part
                            date, rest = metadata.split(" : ", 1)
                            date = date.strip("()")
                            info_parts = rest.split(", ")
                            info = {}
                            for part in info_parts:
                                key, value = part.split(" - ", 1)
                                info[key.strip()] = value.strip()

                            model = info["Model"]
                            technique = info["Technique"]
                            test_name = info["Test Name"]

                            results = ast.literal_eval(dict_str)
                            times = [run['TimeTaken'] for run in results.values()]
                            average_time = sum(times) / len(times)
                            true_count = sum(1 for run in results.values() if run['Result'])
                            accuracy = true_count / len(results)

                            print(f"Model: {model}, Technique: {technique}, Test Name: {test_name}, "
                                  f"Average Time: {average_time:.2f}, Accuracy: {accuracy:.2f}")

                            metadata = None  # Reset for next test
                        except Exception as e:
                            print(f"Error processing test: {e}")
                    else:
                        print(f"Unexpected line format: {line[:50]}...")
        except Exception as e:
            print(f"Error opening file: {e}")
