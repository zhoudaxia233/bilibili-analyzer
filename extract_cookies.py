from typing import Dict
from pathlib import Path
import browsercookie
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

console = Console()


def get_bilibili_cookies(browser: str = "chrome") -> Dict[str, str]:
    """
    Extract Bilibili cookies from the specified browser.

    Args:
        browser: 'chrome' or 'firefox'
    Returns:
        Dictionary with SESSDATA, bili_jct, buvid3 if found
    """
    cookies = {}
    try:
        match browser:
            case "chrome":
                cj = browsercookie.chrome()
            case "firefox":
                cj = browsercookie.firefox()
            case _:
                raise ValueError(f"Unsupported browser: {browser}")
        for cookie in cj:
            if ".bilibili.com" in cookie.domain and cookie.name in [
                "SESSDATA",
                "bili_jct",
                "buvid3",
            ]:
                cookies[cookie.name] = cookie.value
        return cookies
    except Exception as e:
        console.print(f"[red]Failed to get cookies: {e}[/red]")
        return {}


def save_to_env(cookies: Dict[str, str], env_path: str = ".env") -> None:
    """
    Save cookies to a .env file, preserving other variables.

    Args:
        cookies: Dictionary of cookies
        env_path: Path to .env file
    """
    env_content = [
        f"BILIBILI_SESSDATA={cookies.get('SESSDATA', '')}",
        f"BILIBILI_BILI_JCT={cookies.get('bili_jct', '')}",
        f"BILIBILI_BUVID3={cookies.get('buvid3', '')}",
    ]
    try:
        env_file = Path(env_path)
        existing_content = []
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                existing_content = [
                    line
                    for line in f.read().splitlines()
                    if not line.startswith(
                        ("BILIBILI_SESSDATA", "BILIBILI_BILI_JCT", "BILIBILI_BUVID3")
                    )
                ]
        all_content = existing_content + env_content
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("\n".join(all_content) + "\n")
        console.print(f"[green]Cookies saved to {env_path}.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to save to .env: {e}[/red]")


def main():
    console.print(
        Panel.fit(
            "[bold cyan]Bilibili Cookie Extractor[/bold cyan]\n[white]This tool helps you extract Bilibili cookies from your browser and save them to a .env file.[/white]\n\n[green]Saving to .env will preserve all other environment variables and only update Bilibili-related ones.[/green]",
            title="Info",
        )
    )
    console.print("-" * 40)
    console.print("[bold]Select browser:[/bold]")
    console.print("[cyan]1.[/cyan] Chrome")
    console.print("[cyan]2.[/cyan] Firefox")
    choice = Prompt.ask("Enter number", default="1")

    match choice:
        case "1":
            browser = "chrome"
        case "2":
            browser = "firefox"
        case _:
            console.print("[yellow]Invalid choice, defaulting to Chrome.[/yellow]")
            browser = "chrome"

    console.print(
        f"\n[bold]Extracting Bilibili cookies from [green]{browser}[/green]...[/bold]"
    )
    cookies = get_bilibili_cookies(browser)
    if not cookies:
        console.print("[red]No Bilibili cookies found. Please ensure:[/red]")
        console.print(
            "  [yellow]1. You are logged in to Bilibili in your browser.[/yellow]"
        )
        console.print("  [yellow]2. You selected the correct browser.[/yellow]")
        console.print(
            "  [yellow]3. The browser is not in incognito/private mode.[/yellow]"
        )
        return

    table = Table(title="Found Bilibili Cookies")
    table.add_column("Name", style="cyan")
    table.add_column("Value (masked)", style="magenta")
    for name, value in cookies.items():
        masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
        table.add_row(name, masked_value)
    console.print(table)

    save = Prompt.ask("\nSave to .env file? (y/n)", default="y").lower()
    if save == "y":
        save_to_env(cookies)
        console.print(
            "[bold green]Tip:[/bold green] Add .env to your .gitignore to avoid committing credentials!"
        )


if __name__ == "__main__":
    main()
