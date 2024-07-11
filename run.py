import subprocess
from app import app

if __name__ == '__main__':
    # Get the current version
    git_command = ["git", "rev-parse", "--short", "HEAD"]
    version = ""

    try:
        # Run the Git command
        result = subprocess.run(
            git_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        if result.returncode == 0:
            # Successfully retrieved the HEAD hash
            head_hash = result.stdout.strip()
            version = head_hash
        else:
            # There was an error running the Git command
            print("Error:", result.stderr)
    except FileNotFoundError:
        # Git executable not found
        print("Git is not installed or not in the system's PATH.")
        version = "N/A"
    except Exception as e:
        # Handle other exceptions
        print("An error occurred:", str(e))

    with open("version.txt", "w") as f:
        f.write(version)

    app.run(host="0.0.0.0", port=50000, debug=True)
