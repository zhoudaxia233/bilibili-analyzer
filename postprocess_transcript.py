import sys
import logging
from pathlib import Path
from rich.console import Console
from bilibili_client import SimpleLLM

console = Console()
logger = logging.getLogger("bilibili_client")


def main():
    if len(sys.argv) < 2:
        console.print(
            "[yellow]Usage: python postprocess_transcript.py <transcript.txt>[/yellow]"
        )
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    if not transcript_path.is_file():
        logger.error(f"File not found: {transcript_path}")
        sys.exit(1)

    transcript = transcript_path.read_text(encoding="utf-8")

    llm = SimpleLLM()
    with console.status(
        "[bold green]Running LLM post-processing (this may take a while)...[/bold green]",
        spinner="dots",
    ):
        corrected = llm.call(transcript)

    output_path = transcript_path.with_name(transcript_path.stem + "_corrected.txt")
    output_path.write_text(corrected, encoding="utf-8")

    console.print(f"[green]Corrected transcript saved to: {output_path}[/green]")


if __name__ == "__main__":
    main()
