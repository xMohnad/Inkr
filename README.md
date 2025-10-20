# Inkr - MKV Editor

Inkr is a simple tool for managing MKV files.

## Installation

### Prerequisites

- **MKVToolNix**: Required for MKV operations. Install using your package manager:

  | Platform             | Command                                                                  |
  | -------------------- | ------------------------------------------------------------------------ |
  | **Arch Linux**       | `sudo pacman -S mkvtoolnix-cli`                                          |
  | **Debian/Ubuntu**    | `sudo apt install mkvtoolnix`                                            |
  | **macOS** (Homebrew) | `brew install mkvtoolnix`                                                |
  | **Termux**           | `pkg install mkvtoolnix`                                                 |
  | **Windows**          | [Download installer](https://mkvtoolnix.download/downloads.html#windows) |

### Install Inkr

#### Recommended Method (using pipx)

```bash
pipx install pyinkr
```

_Why pipx?_

- Isolates the application in its own environment
- Prevents dependency conflicts
- Easier to uninstall/update

#### Alternative Method (using pip)

```bash
pip install pyinkr
```

> [!NOTE]
> To run the application, use the `inkr` command.

### For Developers

1. Clone the repository:

   ```bash
   git clone https://github.com/xMohnad/Inkr.git
   cd Inkr
   ```

1. Set up development environment:

   ```bash
   make setup

   # run application
   make run
   ```

## Key Bindings

Press `Ctrl+p` to open the command palette
and view all available key bindings.

## Dependencies

- [dacite](https://pypi.org/project/dacite/): A library for creating data classes from dictionaries.
- [python-iso639](https://github.com/jacksonllee/iso639): Library for working with ISO 639 language codes.
- [Textual](https://textual.textualize.io/): A Python framework for building terminal-based user interfaces.
- [Textual-Fspicker](https://github.com/davep/textual-fspicker): A Textual widget library for picking things in the filesystem

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss the proposed changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
