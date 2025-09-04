#!/usr/bin/env python3
"""
Intuitive File Mover - Move files effortlessly between directories.

A terminal-based file moving utility with smart search capabilities.
Features:
- Navigate directories with arrow keys
- Search within current directory tree
- Multi-select files with previews
- Clean, terminal-native interface

Usage: python file_mover.py
"""

import os
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import required libraries with error handling
try:
    from rich.console import Console
    from rich.tree import Tree
    from rich.panel import Panel
    from rich.text import Text
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import inquirer
except ImportError:
    print("Required packages not found. Please install with:")
    print("pip install rich inquirer")
    exit(1)

# Initialize rich console for beautiful terminal output
console = Console()

class FileMover:
    """
    Main class handling all file moving operations and user interactions.

    Provides a clean terminal interface for navigating directories,
    searching for files, and moving them between locations.
    """

    def __init__(self):
        """Initialize the FileMover with default settings and caches."""
        self.console = console
        # Cache dictionaries for search functionality
        self.directory_cache: Dict[str, Path] = {} # Stores directory search results
        self.file_cache: Dict[str, Path] = {} # Stores file search results
        self.cache_built = False # Track if search index is built

        # Directories to skip during search for better performance
        # These are typically system directories or build artifacts
        self.skip_dirs = {
            '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.cache',
            '.tmp', 'temp', '.vscode', '.idea', '.DS_Store', 'Library',
            'System', 'Applications', '.Trash', 'Trash', '.local/share/Trash',
            'AppData', 'Windows', 'Program Files', 'Program Files (x86)'
        }

    def build_local_directory_index(self, root_path: Path, max_depth: int = 4) -> Dict[str, Path]:
        """
        Build a search index for directories within the current path and subfolders

        This creates a searchable cache of all directories under the root path,
        making directory searches fast and responsive.

        Args:
            root_path: The root directory to start scanning from
            max_depth: Maximum depth to scan (prevents infinite recursion)
        Returns:
            Dictionary mapping directory names to their Path objects

        """
        cache = {}
        scanned_count = 0
        max_items = 500  # Reasonable limit for local search

        # Show progress bar while scanning directories
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]Scanning local directories..."),
            console=self.console
        ) as progress:
            task = progress.add_task("Indexing local directories", total=None)

            def scan_local_directory(current_path: Path, depth: int = 0):
                """
                Recursively scan directories and add them to the cache.

                Uses os.scandir for better performance than Path.iterdir().
                Includes safety checks for permissions and depth limits.
                """
                nonlocal scanned_count, max_items

                # Stop if we've gone too deep or found enough items
                if depth > max_depth or scanned_count > max_items:
                    return

                # Use os.scandir for better performance
                try:
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            # Break if we've hit our item limit
                            if scanned_count > max_items:
                                break

                            # Skip hidden directories and non-directories
                            if not entry.is_dir() or entry.name.startswith('.'):
                                continue

                            # Skip common system/build directories for performance
                            if entry.name.lower() in self.skip_dirs:
                                continue

                            try:
                                dir_path = Path(entry.path)

                                # Cache the directory name for quick lookup
                                cache[entry.name.lower()] = dir_path

                                # Also cache the relative path from root for better matching
                                # This allows searching for "docs/projects" style paths
                                try:
                                    rel_path = str(dir_path.relative_to(root_path)).lower()
                                    cache[rel_path] = dir_path
                                except ValueError:
                                    pass  # Skip if can't make relative path

                                scanned_count += 1

                                # Recursively scan this directory's subdirectories
                                scan_local_directory(dir_path, depth + 1)

                            except (OSError, PermissionError):
                                # Skip directories we can't access
                                continue

                except (PermissionError, OSError, FileNotFoundError):
                    # Skip directories we can't read
                    pass

            # Start the recursive scan from root
            scan_local_directory(root_path)

        return cache

    def simple_search(self, query: str, cache: Dict[str, Path], limit: int = 10) -> List[Tuple[str, Path]]:
        """
        Perform simple, predictable search without fuzzy mathcing complexity.

        Uses straightforward matching criteria to find relevant directories/files:
        - Exact matches get highest priority
        - "Starts with" matches get high priority
        - "Contains" matches get medium priority

        Args:
            query: Search term entered by user
            cache: Dictorionary of cached paths to search through
            limit: Maximum number of results to return
        
        Returns:
            List of tuples containing (display_path, actual_path)
        """
        if not query.strip():
            return []

        query_lower = query.lower()
        matches = []

        # Search through all cached entries
        for key, path in cache.items():
            name_only = path.name.lower()

            # Score matches based on how well they match the query
            match_score = 0

            if query_lower == name_only:
                match_score = 100  # Exact match
            elif name_only.startswith(query_lower):
                match_score = 90   # Starts with query - higher prio
            elif query_lower in name_only:
                match_score = 80   # Contains query in name - medium prio
            elif query_lower in key:  # Also check full/relative path
                match_score = 70   # Contains in path - lower prio

            # Only include matches that scored above 0
            if match_score > 0:
                matches.append((str(path), path, match_score))

        # Sort by score (highest first), then alphabetically for consistency
        matches.sort(key=lambda x: (-x[2], x[0]))

        # Return without score for cleaner display to user
        return [(display, path) for display, path, score in matches[:limit]]

    def get_directories(self, base_path: Path) -> List[str]:
        """
        Get all directories in the given path for the selection menu.

        Builds the list options shown to the user when navigating directories.
        Includes search option, parent directory navigation, subdirectories,
        and option to user current directory.

        Args:
            base_path: The current directory to list contents from
        
        Returns:
            Lst of formatted strings for the inquirer menu.
        """
        try:
            directories = []

            # Add search option at the top of the menu
            directories.append("🔍 Search directories anywhere...")

            # Add parent directory option if we're not at the filesystem root
            if base_path.parent != base_path:
                directories.append("📁 .. (Go up)")

            # Add all subdirectories in alphabetical order
            for item in sorted(base_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    directories.append(f"📁 {item.name}")

            # Add option to select current directory as destination
            directories.append(f"✅ Use this directory ({base_path.name})")

            return directories
        
        except PermissionError:
            # Handle case where we can't read the directory
            self.console.print(f"[red]Permission denied accessing {base_path}[/red]")
            return ["🔍 Search directories anywhere...", "📁 .. (Go up)"]

    def get_files(self, directory: Path) -> List[str]:
        """
        Get all files in the given directory for the selection menu.

        Creates the list of files shown to the user for selection,
        including file sizes and a search option.

        Args:
            directory: The directory to list files from
        
        Returns:
            List of formatted strings showing files with their size
        """
        try:
            files = []

            # Add search option at the top of the file list
            files.append("🔍 Search files in this directory...")

            # Add all files with their sizes, sorted alphabetically
            for item in sorted(directory.iterdir()):
                if item.is_file() and not item.name.startswith('.'):
                    # Get file size in human-readable format
                    size = self.format_file_size(item.stat().st_size)
                    files.append(f"📄 {item.name} ({size})")
            return files
        
        except PermissionError:
            # Handle cases where we can't read the directory
            self.console.print(f"[red]Permission denied accessing {directory}[/red]")
            return ["🔍 Search files in this directory..."]

    def format_file_size(self, size_bytes: int) -> str:
        """
        Convert file size from bytes to human-readable format.

        Args:
            size_bytes: File size in bytes
        
        Returns:
            Formatted string like "2.3 MB"
        """
        # Convert bytes to appropriate units
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"

    def select_directory(self, prompt_text: str, current_path: Optional[Path] = None) -> Path:
        """
        Interactive directory selection with navigation.

        Provides a menu-driven interface for browsing directories with:
        - Arrow key navigation
        - Parent directory traversal
        - Search functionality
        - Visual current location display

        Args:
            prompt_text: Message shown to user in the selection menu
            current_path: Starting directory (defaults to user's home)
        
        Return:
            Path object of the selected directory
        """
        # Starts from the user's home directory if no path specified
        if current_path is None:
            current_path = Path.home()

        # Navigation loop - continues until user makes a selection
        while True:
            # Clear screen and show current locatiom
            self.console.clear()
            self.console.print(Panel(
                f"[bold blue]Current Location:[/bold blue] {current_path}",
                expand=False
            ))

            # Get available directories and options
            directories = self.get_directories(current_path)

            # Handle case where no directories are accessible
            if not directories:
                self.console.print("[yellow]No accessible directories found[/yellow]")
                return current_path

            # Show selection menu to user
            questions = [
                inquirer.List(
                    'directory',
                    message=prompt_text,
                    choices=directories,
                )
            ]

            # Get user's selection
            answer = inquirer.prompt(questions)
            if not answer:
                return current_path

            selection = answer['directory']

            # Handle different types of selections
            if selection.startswith("🔍 Search directories"):
                # User wants to search - trigger search mode
                search_result = self.search_directories(current_path)
                if search_result:
                    return search_result
                # If search cancelled, continue with current path
            
            elif selection.startswith("📁 .. (Go up)"):
                # User wants to go up one directory level
                current_path = current_path.parent

            elif selection.startswith("✅ Use this directory"):
                # User selected current directory as final choice
                return current_path
            
            else:
                # User selected a subdirectory - navigate into it
                # Extract directory name (remvoe emoji and formatting)
                dir_name = selection.replace("📁 ", "")
                new_path = current_path / dir_name
                if new_path.exists() and new_path.is_dir():
                    current_path = new_path

    def select_files(self, directory: Path) -> List[Path]:
        """
        Allow user to select multiple files from a directory.

        Shows a checkbox-style menu where users can:
        - Select multiple files with spacebar
        - See file sizes for each file
        - Access search functionality
        - Navigate with arrowk keys

        Args:
            directory: Directory to select files from
        
        Returns:
            List of Path objects from selected files
        """
        self.console.clear()

        # Show which directory we're selecting files from
        self.console.print(Panel(
            f"[bold green]Selecting files from:[/bold green] {directory}",
            expand=False
        ))

        # Get list of available files
        files = self.get_files(directory)

        # Handle cases where directory has no files
        if not files:
            self.console.print("[yellow]No files found in this directory[/yellow]")
            return []

        # Create checkbox-style selection menu
        questions = [
            inquirer.Checkbox(
                'files',
                message="Select files to move (use SPACE to select, ENTER to confirm)",
                choices=files,
            )
        ]

        # Get user's file selections
        answer = inquirer.prompt(questions)
        if not answer or not answer['files']:
            return []

        # Check if user selected search option
        if "🔍 Search files in this directory..." in answer['files']:
            return self.search_files_in_directory(directory)

        # Convert display strings back to actual file paths
        selected_files = []
        for file_display in answer['files']:
            if file_display.startswith("📄"):
                # Extract filename (remove emoji and size info)
                filename = file_display.replace("📄 ", "").split(" (")[0]
                file_path = directory / filename
                if file_path.exists():
                    selected_files.append(file_path)

        return selected_files

    def search_directories(self, current_path: Path) -> Optional[Path]:
        """
        Search for directories within current path and subfolders.

        Provides a fast text-based search interface that scans the current directory
        tree and allows users to quickly find and navigate to specific folders.

        Args:
            current_path: The root directory to search within
        
        Returns:
            Path object of selected directory, or None if cancelled
        """
        self.console.clear()
        self.console.print(Panel(
            f"[bold blue]🔍 Local Directory Search[/bold blue]\n"
            f"Searching in: {current_path}\n"
            "Type to search subdirectories. Press Enter to select, or 'q' to go back.",
            expand=False
        ))

        # Build search index of all local directories under current path
        local_cache = self.build_local_directory_index(current_path)

        # Handle case where no subdirectories were found
        if not local_cache:
            self.console.print("[yellow]No subdirectories found to search.[/yellow]")
            input("Press Enter to continue...")
            return None

        # Search loop - continues until user makes a selection or quits
        while True:
            query = input(f"\nSearch local directories: ").strip()

            # Allow user to quit search with 'q' or empty input
            if query.lower() in ['q', 'quit', 'exit', '']:
                return None  # Go back to manual navigation

            # Find matching directories based on search query    
            matches = self.simple_search(query, local_cache, limit=10)

            # Handle case where no matches were found
            if not matches:
                self.console.print(f"[yellow]No directories found matching '{query}'. Try different terms or 'q' to go back.[/yellow]")
                continue

            # Format search results for display
            choices = []
            for display_path, actual_path in matches:
                try:
                    # Show relative path from current directory for clarity
                    rel_path = actual_path.relative_to(current_path)
                    choices.append(f"📁 {actual_path.name} → {rel_path}")
                except ValueError:
                    # Fallback to full path if relative path calculation fails
                    choices.append(f"📁 {actual_path.name} → {actual_path}")

            # add options for search refinement and manual browsing
            choices.extend(["🔄 Search again", "📂 Browse manually instead"])

            # Show selection menu for search results
            questions = [
                inquirer.List(
                    'selection',
                    message=f"Found {len(matches)} directories matching '{query}':",
                    choices=choices,
                )
            ]

            answer = inquirer.prompt(questions)
            if not answer:
                continue

            selection = answer['selection']

            # Handle user's choice from search result
            if selection == "🔄 Search again":
                continue # Go back to search input
            elif selection == "📂 Browse manually instead":
                return None  # Exit search mode
            else:
                # User selected a directory - find the corresponding path
                for i, (display_path, actual_path) in enumerate(matches):
                    if choices[i] == selection:
                        return actual_path

    def search_files_in_directory(self, directory: Path, initial_query: str = "") -> List[Path]:
        """Search files within a specific directory - simplified version"""
        self.console.clear()
        self.console.print(Panel(
            f"[bold green]🔍 File Search[/bold green]\n"
            f"Searching files in: {directory}\n"
            "Type to search files, or press Enter with empty query to see all files.",
            expand=False
        ))

        # Get all files in directory
        all_files = {}
        try:
            for item in directory.iterdir():
                if item.is_file() and not item.name.startswith('.'):
                    all_files[item.name.lower()] = item
        except (PermissionError, OSError):
            self.console.print(f"[red]Cannot access directory: {directory}[/red]")
            return []

        if not all_files:
            self.console.print("[yellow]No files found in this directory[/yellow]")
            input("Press Enter to continue...")
            return []

        while True:
            query = input(f"\nSearch files: ").strip()

            if query.lower() in ['q', 'quit', 'exit']:
                return []

            if query:
                matches = self.simple_search(query, all_files, limit=15)
            else:
                # Show all files if no query
                matches = [(str(path), path) for path in all_files.values()]
                matches.sort(key=lambda x: x[1].name.lower())

            if not matches:
                self.console.print(f"[yellow]No files found matching '{query}'.[/yellow]")
                continue

            # Format choices for inquirer
            choices = []
            for display_path, actual_path in matches:
                size = self.format_file_size(actual_path.stat().st_size)
                file_name = actual_path.name
                choices.append(f"📄 {file_name} ({size})")

            choices.extend(["🔄 Search again", "✅ Done selecting"])

            questions = [
                inquirer.Checkbox(
                    'files',
                    message=f"Select files (SPACE to select, ENTER to confirm):",
                    choices=choices,
                )
            ]

            answer = inquirer.prompt(questions)
            if not answer:
                continue

            selected = answer['files']

            if "🔄 Search again" in selected:
                continue

            # Convert selections back to file paths
            selected_files = []
            for choice in selected:
                if choice.startswith("📄") and choice != "✅ Done selecting":
                    file_name = choice.split("📄 ")[1].split(" (")[0]
                    file_path = directory / file_name
                    if file_path.exists():
                        selected_files.append(file_path)

            if selected_files or "✅ Done selecting" in selected:
                return selected_files

    def show_move_preview(self, files: List[Path], destination: Path):
        """Show a preview of what will be moved"""
        table = Table(title="Move Preview")
        table.add_column("File", style="cyan")
        table.add_column("From", style="yellow")
        table.add_column("To", style="green")

        for file in files:
            table.add_row(
                file.name,
                str(file.parent),
                str(destination)
            )

        self.console.print(table)

    def move_files(self, files: List[Path], destination: Path) -> bool:
        """Move files to destination with progress feedback"""
        try:
            moved_files = []

            for file in files:
                dest_file = destination / file.name

                # Check if file already exists
                if dest_file.exists():
                    overwrite = Confirm.ask(
                        f"File {file.name} already exists in destination. Overwrite?"
                    )
                    if not overwrite:
                        self.console.print(f"[yellow]Skipped {file.name}[/yellow]")
                        continue

                # Move the file
                shutil.move(str(file), str(dest_file))
                moved_files.append(file.name)
                self.console.print(f"[green]✓[/green] Moved {file.name}")

            if moved_files:
                self.console.print(f"\n[bold green]Successfully moved {len(moved_files)} files![/bold green]")
                return True
            else:
                self.console.print("[yellow]No files were moved[/yellow]")
                return False

        except Exception as e:
            self.console.print(f"[red]Error moving files: {e}[/red]")
            return False

    def run(self):
        """
        Main application loop that orchestrates the entire file moving process.

        Guides the user through a 4-step process:
        1. Select source directory containing files to move
        2. Select specific files to move from that directory
        3. Select destination directory for the files
        4. Preview and confirm the move operation

        Includes error handling for user cancellation and validation checks.
        """
        # Clear screen and show welcome message
        self.console.clear()
        welcome_text = Text("🚀 Intuitive File Mover 🚀", style="bold magenta")
        self.console.print(Panel(welcome_text, expand=False))

        try:
            # STEP 1: Select source directory
            # User picks specific files from the source directory
            self.console.print("\n[bold]Step 1: Select source directory[/bold]")
            source_dir = self.select_directory("Choose the directory containing files to move:")

            # STEP 2: Select files to move
            # User picks specific files from the source directory
            self.console.print("\n[bold]Step 2: Select files to move[/bold]")
            selected_files = self.select_files(source_dir)
            
            # Validate that user actually selected some files
            if not selected_files:
                self.console.print("[yellow]No files selected. Exiting.[/yellow]")
                return

            # STEP 3: Select destination directory
            # User navigates to find where they want to move the files
            self.console.print("\n[bold]Step 3: Select destination directory[/bold]")
            dest_dir = self.select_directory("Choose destination directory:")

            # Safety check: prevent moving files to the same directory they're already in
            if source_dir.resolve() == dest_dir.resolve():
                self.console.print("[red]Source and destination are the same! Exiting.[/red]")
                return

            # STEP 4: Preview and confirm the move opeartion
            # Show user exactly what will happen before making any changes
            self.console.clear()
            self.console.print("[bold]Step 4: Confirm the move[/bold]\n")
            self.show_move_preview(selected_files, dest_dir)
            
            # Get final confirmation from user
            if Confirm.ask("\nProceed with moving these files?"):
                self.move_files(selected_files, dest_dir)
            else:
                # User cancelled at the last step
                self.console.print("[yellow]Move operation cancelled[/yellow]")

        except KeyboardInterrupt:
            # Handle user pressing Ctrl + c to cancel
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            # Handle any other unexpected errors
            self.console.print(f"\n[red]An error occurred: {e}[/red]")

def main():
    """
    Entry point for the application.

    Creates a FileMover instance and starts the interactive process.
    This function is called when the script is run directly.
    """
    mover = FileMover()
    mover.run()

if __name__ == "__main__":
    main()
