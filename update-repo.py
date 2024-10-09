import subprocess
import sys
import os

import shutil
from jinja2 import Template


"""
This script streamlines the process of copying a file of any type into each workflows directory
along with a corresponding news file, followed by creating a PR into the GitHub feedstock repository.

How to use:

python /path/update-repo.py <filepath-you-want-to-copy-in-your-local-machine> <filepath-in-the-github-repo> <news-file>
e.g. python /path/update-repo.py ../dev/example/test.yml  .github/workflows ../dev/example/build-workflow.rst

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
Core Functionalities - sync with the main branch, copy desired file, 
                       pass a variable to the file, and create PR
"""


def sync_with_main_branch(package_dir_path):
    # Check out main and pull the latest changes
    run_command("git checkout main", cwd=package_dir_path)
    run_command("git pull upstream main", cwd=package_dir_path)


def update_project_name(dest_file_path, package_name):
    # Read the content of the file as a Jinja template
    with open(dest_file_path, 'r') as file:
        content = file.read()

    # Create a Jinja2 template from the file content
    template = Template(content)

    # Render the template with the package name
    updated = template.render(project_name=package_name)

    # Write the rendered content back to the file
    with open(dest_file_path, 'w') as file:
        file.write(updated)


def new_branch(package_dir_path, source_file):
    run_command(f"git checkout -b {source_file}", cwd=package_dir_path)


def copy_file(source_file, package_dir_path, package_workflow_dir_path, dest_file_path, username):
    # Copy the file
    shutil.copy2(source_file, dest_file_path)
    print(f'File copied to {package_workflow_dir_path}')
    print(source_file)

    if source_file != "build-workflow.rst":
        # Pass the package name into the file
        package_name = package_dir_path.split('/')[1]
        update_project_name(dest_file_path, package_name)

        # Create PR
        if package_name.split('.')[0] == "diffpy":
            org_name = "diffpy"
        else:
            org_name = "Billingegroup"
        create_PR(package_dir_path, source_file, username, package_name, org_name)


def create_PR(cwd, file, username, package_name, org_name):
    """
    Create a PR from a branch name of <new_version>
    to the main branch of the feedstock repository.
    """

    run_command(f"git add workflows/{file}", cwd=cwd)
    run_command(f"git add ../news/build-workflow.rst", cwd=cwd)

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
    source_file_path = sys.argv[1]
    repo_file_path = sys.argv[2]
    news_file_path = sys.argv[3]

    source_file = source_file_path.split("/")[-1]
    news_file = news_file_path.split("/")[-1]
    dest_dir = repo_file_path.split("/")[-1]

    # Get the GitHub username using the GitHub CLI
    username = get_github_username()

    for package_dir_path, dirnames, filenames in os.walk('./'):
        if dest_dir in dirnames:
            package_workflow_dir_path = os.path.join(package_dir_path, str(dest_dir))  # Full path to the workflow directory
            dest_file_path = os.path.join(package_workflow_dir_path, source_file)  # Destination file path

            # Check if the file already exists
            if not os.path.exists(dest_file_path):
                print("here")
                copy_file(source_file, package_dir_path, package_workflow_dir_path, dest_file_path, username)
            else:
                print(f'File already exists in {package_workflow_dir_path}')

        elif 'news' in dirnames:
            package_news_dir_path = os.path.join(package_dir_path, 'news')  # Full path to the workflow directory
            dest_news_file_path = os.path.join(package_news_dir_path, news_file)  # Destination file path

            # Check if the file already exists
            if not os.path.exists(dest_news_file_path):
                sync_with_main_branch(package_dir_path)
                new_branch(package_dir_path, source_file)
                copy_file(news_file, package_dir_path, package_news_dir_path, dest_news_file_path, username)
            else:
                print(f'File already exists in {package_news_dir_path}')


if __name__ == "__main__":
    main()
