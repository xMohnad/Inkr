# Inkr - MKV Editer

Inkr is a simple tool for managing MKV files.

## Features

- **Open MKV Files**: Load MKV files.
- **Track Management**:
  - **Add Tracks**: Add new audio, video, or subtitle tracks to the MKV file.
  - **Toggle Tracks**: Enable or disable tracks for inclusion in the output file.
  - **Rearrange Tracks**: Move tracks up or down to change their order.
- **Save Changes**: Save the modified MKV file.

## Installation

### Prerequisites

- **MKVToolNix**: Ensure `mkvtoolnix-cli` is installed on your system. You can install it using your package manager:
  - **Arch Linux**:

    ```bash
    sudo pacman -S mkvtoolnix-cli
    ```

  - **Debian/Ubuntu**:

    ```bash
    sudo apt install mkvtoolnix
    ```

  - **macOS** (with Homebrew):

    ```bash
    brew install mkvtoolnix
    ```

  - **Termux**:

    ```bash
    pkg install mkvtoolnix
    ```

  - **Windows**: Download and install from the [official MKVToolNix website](https://mkvtoolnix.download/downloads.html#windows).

### Install Inkr

You can install Inkr directly via `pip`:

```bash
pip install pyinkr
```

### For Development

If you want to contribute to the project or run it locally:

1. Clone the repository:
   ```bash
   git clone https://github.com/xMohnad/Inkr.git
   cd inkr
   ```
1. Install the project in editable mode:
   ```bash
   pip install -e .
   ```

## Key Bindings

| Key | Action |
|--------------|----------------------------|
| `o` | Open an MKV file |
| `a` | Add a new track |
| `Space` | Toggle track (disables & removes when off) |
| `Alt+Up` | Move track up |
| `Alt+Down` | Move track down |
| `s` | Save the MKV file |

## Dependencies

- [Textual](https://textual.textualize.io/): A Python framework for building terminal-based user interfaces.
- [pymkv2](https://github.com/GitBib/pymkv2): A Python wrapper for the MKVToolNix utilities.
- [Textual-Fspicker](https://github.com/davep/textual-fspicker): A Textual widget library for picking things in the filesystem

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss the proposed changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
