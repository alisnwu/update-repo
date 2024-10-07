import subprocess
import sys
import os

import shutil


"""
This script streamlines the process of copying a file of any type into each workflows directory, 
followed by creating a PR into the GitHub feedstock repository.

How to use:

python /path/.../update-repo.py <filepath-you-want-to-copy-in-your-local-machine> <filepath-in-the-github-repo>
e.g. python /path/.../update-repo.py ../dev/example/test.yml  .github/workflows 

Workflow:

- Walk through all directories to find corresponding filepath
- Copy file to desired directories
- Fetch the user's GitHub username using the GitHub CLI for authentication
- Commit these changes, pushes them to GitHub, and creates a PR
"""

"""
Utility Functions
"""


def run_command(command, cwd=None):
    """Run a shell command in the specified directory."""
    subprocess.run(
        command,
        check=True,
        shell=True,
        text=True,
        cwd=cwd,
    )


"""
Core Functionalities - find all desired directories, copy desired file, and create PR
"""


def sync_with_main_branch(dirpath):
    # Check out main and pull the latest changes
    run_command("git checkout main", cwd=dirpath)
    run_command("git pull upstream main", cwd=dirpath)


def copy_file(source_file, dirpath, workflow_dir, dest_file, username):
    # Create and switch to a new branch named after the new version
    run_command(f"git checkout -b {source_file}", cwd=dirpath)

    # Copy the file
    shutil.copy2(source_file, dest_file)
    print(f'File copied to {workflow_dir}')

    # Create PR
    package_name = dirpath.split('/')[1]
    if package_name.split('.')[0] == "diffpy":
        org_name = "diffpy"
    else:
        org_name = "Billingegroup"
    create_PR(dirpath, source_file, username, package_name, org_name)


def create_PR(cwd, file, username, package_name, org_name):
    """
    Create a PR from a branch name of <new_version>
    to the main branch of the feedstock repository.
    """

    run_command(f"git add workflows/{file}", cwd=cwd)

    # Commit the changes
    run_command(f'git commit -m "Add {file} to workflow"', cwd=cwd)

    # Push the new branch to your origin repository
    run_command(f"git push origin {file}", cwd=cwd)

    run_command(f"gh repo set-default {org_name}/{package_name}", cwd=cwd)

    # Create a pull request using GitHub CLI
    pr_command = (
        f"gh pr create --base main --head {username}:{file} "
        f"--title 'Add {file} to workflows' "
        f"--body 'Added {file} to workflows'"
    )

    # Run the PR create command in the appropriate directory
    run_command(pr_command, cwd=cwd)


"""
GitHub Integration
"""


def get_github_username():
    """Get the GitHub username using the GitHub CLI."""
    try:
        username = subprocess.check_output(
            ["gh", "api", "user", "--jq", ".login"], text=True
        ).strip()
        return username
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "Could not retrieve GitHub username using GitHub CLI. "
            "Please make sure your local machine is authenticated with GitHub."
        )


"""
Main Entry Point
"""


def main():
    source_fp = sys.argv[1]
    repo_fp = sys.argv[2]

    source_file = source_fp.split("/")[-1]
    dest_dir = repo_fp.split("/")[-1]

    # Get the GitHub username using the GitHub CLI
    username = get_github_username()

    for dirpath, dirnames, filenames in os.walk('./'):
        if dest_dir in dirnames:
            workflow_dir = os.path.join(dirpath, str(dest_dir))  # Full path to the workflow directory
            dest_file = os.path.join(workflow_dir, source_file)  # Destination file path

            # Check if the file already exists
            if not os.path.exists(dest_file):
                sync_with_main_branch(dirpath)
                copy_file(source_file, dirpath, workflow_dir, dest_file, username)
            else:
                print(f'File already exists in {workflow_dir}')


if __name__ == "__main__":
    main()
