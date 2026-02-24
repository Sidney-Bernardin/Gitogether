import fastapi
import pathlib
import subprocess

repositories_path = pathlib.Path("/home/sidney/gitogether/repositories")

app = fastapi.FastAPI()

@app.post("/{username}/{reponame}")
async def create_repo(username: str, reponame: str):
    repo_path = repositories_path / username / reponame
    repo_path.mkdir(parents=True, exist_ok=True)

    print(subprocess.run(["git", "init"], cwd=repo_path))

    return username

@app.get("/{username}/{reponame}")
async def get_repo(username: str, reponame: str):
    return username
