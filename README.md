# Inkr - MKV Editer

Inkr is a simple tool for managing MKV files.

## Installation

### Prerequisites

- **MKVToolNix**: Required for MKV operations. Install using your package manager:

  | Platform | Command |
  |----------|---------|
  | **Arch Linux** | `sudo pacman -S mkvtoolnix-cli` |
  | **Debian/Ubuntu** | `sudo apt install mkvtoolnix` |
  | **macOS** (Homebrew) | `brew install mkvtoolnix` |
  | **Termux** | `pkg install mkvtoolnix` |
  | **Windows** | [Download installer](https://mkvtoolnix.download/downloads.html#windows) |

### Install Inkr

#### Recommended Method (using pipx)

```bash
pipx install pyinkr
```

*Why pipx?*

- Isolates the application in its own environment
- Prevents dependency conflicts
- Easier to uninstall/update

#### Alternative Method (using pip)

```bash
pip install pyinkr
```

### For Developers

1. Clone the repository:

   ```bash
   git clone https://github.com/xMohnad/Inkr.git
   cd Inkr
   ```

1. Set up development environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate    # Windows
   ```

1. Install in editable mode with dev dependencies:

   ```bash
   pip install -e .
   ```

## Key Bindings

### App-Level Bindings

| Key | Action | Visible |
|-----|--------|---------|
| `o` | Open MKV file | ✓ |
| `s` | Save MKV file | ✓ |

### Track Management

| Key | Action | Visible |
|-----|--------|---------|
| `a` | Add new track | ✓ |
| `n` | Edit track name | ✓ |
| `l` | Edit track language | ✓ |
| `d` | Toggle default track status | ✓ |
| `Space` | Toggle track selection (disables when off) | ✕ |
| `Alt+↑` | Move track up | ✕ |
| `Alt+↓` | Move track down | ✕ |

### Navigation

| Key | Action | Visible |
|-----|--------|---------|
| `↑` | Move cursor up | ✕ |
| `↓` | Move cursor down | ✕ |
| `Tab` | Focus next element | ✕ |
| `Shift+Tab` | Focus previous element | ✕ |
| `Esc` | Close modal/cancel action | ✓ |

## Dependencies

- [Textual](https://textual.textualize.io/): A Python framework for building terminal-based user interfaces.
- [pymkv2](https://github.com/GitBib/pymkv2): A Python wrapper for the MKVToolNix utilities.
- [Textual-Fspicker](https://github.com/davep/textual-fspicker): A Textual widget library for picking things in the filesystem

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss the proposed changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
