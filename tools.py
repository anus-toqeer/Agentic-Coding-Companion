import os
import sys
import subprocess
import difflib
from pathlib import Path

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_tavily import TavilySearch

load_dotenv()


# =========================================================
# WORKING DIRECTORY
# =========================================================

WORK_DIR = Path(os.environ["WORK_DIR"]).expanduser().resolve()
WORK_DIR.mkdir(parents=True, exist_ok=True)


def safe_path(path: str) -> Path:
    """
    Convert a path into a path inside WORK_DIR.
    Reject anything outside WORK_DIR.
    """

    requested = Path(path).expanduser()

    if not requested.is_absolute():
        requested = WORK_DIR / requested

    target = requested.resolve(strict=False)

    try:
        target.relative_to(WORK_DIR)
    except ValueError:
        raise ValueError(
            "Access denied: this path is outside the allowed working folder."
        )

    return target


# =========================================================
# 1. LIST FILES
# =========================================================

@tool
def list_files(path: str = ".") -> str:
    """List files and folders inside the allowed working folder.

    Args:
        path: Folder path relative to the working folder.
    """

    try:
        folder = safe_path(path)

        if not folder.exists():
            return f"Error: '{path}' does not exist."

        if not folder.is_dir():
            return f"Error: '{path}' is not a folder."

        entries = sorted(
            folder.iterdir(),
            key=lambda item: item.name.lower()
        )

        if not entries:
            return f"'{path}' is empty."

        result = []

        for item in entries:
            if item.is_dir():
                result.append(f"[folder] {item.name}")
            else:
                result.append(f"[file]   {item.name}")

        return "\n".join(result)

    except Exception as e:
        return f"Error: {e}"


# =========================================================
# 2. READ FILE
# =========================================================

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "cpp": ".cpp",
    "c++": ".cpp",
    "c": ".c",
    "java": ".java",
    "javascript": ".js",
    "typescript": ".ts",
    "html": ".html",
    "css": ".css",
    "php": ".php",
    "sql": ".sql",
    "text": ".txt",
}


def get_correct_filename(filename: str, language: str) -> str:
    extension = LANGUAGE_EXTENSIONS.get(language.strip().lower())

    if extension is None:
        raise ValueError(f"Unsupported language: {language}")

    path = Path(filename)

    if path.suffix.lower() == extension:
        return str(path)

    if path.suffix.lower() == ".txt":
        return str(path.with_suffix(extension))

    if not path.suffix:
        return str(path.with_suffix(extension))

    raise ValueError(
        f"Filename extension {path.suffix} does not match {language}."
    )

@tool
def read_file(path: str) -> str:
    """Read a text file inside the allowed working folder.

    Args:
        path: File path relative to the working folder.
    """

    try:
        file_path = safe_path(path)

        if not file_path.exists():
            return f"Error: '{path}' does not exist."

        if not file_path.is_file():
            return f"Error: '{path}' is not a file."

        return file_path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return f"Error: '{path}' is not a supported text file."

    except Exception as e:
        return f"Error: {e}"


# =========================================================
# 3. WRITE FILE
# =========================================================

@tool
def write_file(path: str, content: str) -> str:
    """Create or overwrite a text file inside the working folder.

    Args:
        path: File path relative to the working folder.
        content: Complete contents of the file.
    """

    try:
        file_path = safe_path(path)

        if file_path == WORK_DIR:
            return "Error: cannot overwrite the working folder."

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return (
            f"Wrote {len(content.splitlines())} lines to "
            f"'{file_path.relative_to(WORK_DIR)}'."
        )

    except Exception as e:
        return f"Error: {e}"


# =========================================================
# 4. SEARCH CODE
# =========================================================

@tool
def search_in_files(query: str) -> str:
    """Search for text, functions, classes, variables or code patterns
    inside files in the working folder.

    Args:
        query: Text or code pattern to search for.
    """

    try:
        results = []

        for file_path in WORK_DIR.rglob("*"):

            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(
                    encoding="utf-8"
                )
            except (UnicodeDecodeError, OSError):
                continue

            for line_number, line in enumerate(
                content.splitlines(),
                start=1
            ):

                if query.lower() in line.lower():

                    relative_path = file_path.relative_to(
                        WORK_DIR
                    )

                    results.append(
                        f"{relative_path}:{line_number}: {line.strip()}"
                    )

        if not results:
            return f"No matches found for '{query}'."

        return "\n".join(results[:100])

    except Exception as e:
        return f"Error: {e}"


# =========================================================
# 5. RUN FILE
# =========================================================

@tool
def run_file(path: str) -> str:
    """Run a supported source file inside the working folder
    and return its output.

    Supported files are Python and JavaScript.

    Args:
        path: Source file path relative to the working folder.
    """

    try:
        file_path = safe_path(path)

        if not file_path.exists():
            return f"Error: '{path}' does not exist."

        if not file_path.is_file():
            return f"Error: '{path}' is not a file."

        extension = file_path.suffix.lower()

        if extension == ".py":

            command = [
                sys.executable,
                str(file_path)
            ]

        elif extension == ".js":

            command = [
                "node",
                str(file_path)
            ]

        else:

            return (
                f"Cannot run '{path}'. "
                "Currently supported execution types: "
                ".py and .js."
            )

        result = subprocess.run(
            command,
            cwd=str(WORK_DIR),
            capture_output=True,
            text=True,
            timeout=15
        )

        output = [
            f"Exit code: {result.returncode}"
        ]

        if result.stdout.strip():
            output.append(
                f"STDOUT:\n{result.stdout.strip()}"
            )

        if result.stderr.strip():
            output.append(
                f"STDERR:\n{result.stderr.strip()}"
            )

        return "\n".join(output)

    except subprocess.TimeoutExpired:

        return (
            "Error: program exceeded the "
            "15-second execution limit."
        )

    except Exception as e:

        return f"Error: {e}"


# =========================================================
# 6. DELETE FILE
# =========================================================

@tool
def delete_file(
    path: str,
    confirm: bool = False
) -> str:
    """Delete a file inside the working folder.

    Deletion is allowed only after the user explicitly asks
    for the file to be deleted.

    Args:
        path: File path relative to the working folder.
        confirm: Must be True for an explicitly requested deletion.
    """

    try:

        if not confirm:
            return (
                "Deletion refused. "
                "The user must explicitly request deletion."
            )

        file_path = safe_path(path)

        if not file_path.exists():
            return f"Error: '{path}' does not exist."

        if not file_path.is_file():
            return "Error: this tool deletes files only."

        file_path.unlink()

        return f"Deleted '{path}'."

    except Exception as e:

        return f"Error: {e}"


# =========================================================
# 7. LANGUAGE / EXTENSION DETECTION
# =========================================================

@tool
def detect_language(path: str) -> str:
    """Detect the programming language from a file extension.

    Args:
        path: File path relative to the working folder.
    """

    try:

        file_path = safe_path(path)

        if not file_path.exists():
            return f"Error: '{path}' does not exist."

        extensions = {

            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",

            ".jsx": "React JavaScript",
            ".tsx": "React TypeScript",

            ".java": "Java",

            ".c": "C",
            ".h": "C/C++ Header",

            ".cpp": "C++",
            ".hpp": "C++ Header",

            ".cs": "C#",
            ".php": "PHP",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",

            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL",
            ".sh": "Shell"
        }

        extension = file_path.suffix.lower()

        language = extensions.get(extension)

        if language:

            return (
                f"File: {path}\n"
                f"Language: {language}\n"
                f"Extension: {extension}"
            )

        return (
            f"Unknown or unsupported file type: "
            f"{extension or '[no extension]'}"
        )

    except Exception as e:

        return f"Error: {e}"


# =========================================================
# 8. COMPARE FILES
# =========================================================

@tool
def compare_files(
    first_path: str,
    second_path: str
) -> str:
    """Compare two text files inside the working folder.

    Args:
        first_path: First file path.
        second_path: Second file path.
    """

    try:

        first = safe_path(first_path)
        second = safe_path(second_path)

        if not first.is_file() or not second.is_file():
            return "Error: both paths must be files."

        first_lines = first.read_text(
            encoding="utf-8"
        ).splitlines()

        second_lines = second.read_text(
            encoding="utf-8"
        ).splitlines()

        difference = difflib.unified_diff(
            first_lines,
            second_lines,
            fromfile=first_path,
            tofile=second_path,
            lineterm=""
        )

        difference = list(difference)

        if not difference:
            return "The files are identical."

        return "\n".join(difference[:300])

    except Exception as e:

        return f"Error: {e}"


# =========================================================
# 9. TAVILY WEB SEARCH
# =========================================================

tavily_search = TavilySearch(
    max_results=3,
    tavily_api_key=os.getenv("TAVILY_API_KEY")
)


@tool
def tavily_web_search(query: str) -> str:
    """Search the web for current programming documentation,
    library information, error explanations and technical solutions.

    Args:
        query: Programming or technical question to search for.
    """

    if not os.getenv("TAVILY_API_KEY"):
        return "Error: TAVILY_API_KEY is not configured."

    try:

        results = tavily_search.invoke(query)

        return str(results)

    except Exception as e:

        return f"Error during web search: {e}"


# =========================================================
# ALL AGENT TOOLS
# =========================================================

CODING_TOOLS = [
    list_files,
    read_file,
    write_file,
    search_in_files,
    run_file,
    delete_file,
    detect_language,
    compare_files,
    tavily_web_search
]