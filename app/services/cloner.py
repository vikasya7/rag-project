"""
Clones a public GitHub repo into a temp directory so it can be indexed.

v1 scope: public repos only — no GitHub OAuth for private repos yet.
"""

import shutil
import tempfile
import git


class CloneError(Exception):
    pass

def clone_repo(github_url:str)->str:
     """Clones the given GitHub URL into a fresh temp directory and returns
    the local path. Caller is responsible for cleanup via cleanup_repo()."""
     temp_dir=tempfile.mkdtemp(prefix="responage_")
     try:
          git.Repo.clone(github_url,temp_dir,depth=1)
     except git.exc.GitCommandError as e:
          shutil.rmtree(temp_dir,ignore_errors=True)
          raise CloneError(f"Failed to clone {github_url}: {e}")
     return temp_dir

def cleanup_repo(local_path:str)->None:
     """Removes the cloned repo from disk after indexing completes."""
     shutil.rmtree(local_path,ignore_errors=True)

    