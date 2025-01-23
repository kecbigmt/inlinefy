# inlinefy

A CLI tool that converts CSS in style tags to inline styles in HTML files while preserving media queries.

## Use Case

This tool is particularly useful when creating HTML emails. Many email clients don't support `<style>` tags, requiring CSS to be written as inline styles. With inlinefy, you can:

1. Write your HTML email template using style tags for better maintainability
2. Convert it to email-client-friendly HTML with inline styles
3. Keep media queries for responsive design (supported by some email clients)

## Installation

```bash
# Clone the repository
git clone https://github.com/kecbigmt/inlinefy.git
cd inlinefy

# Install dependencies
poetry install
```

## Usage

### Basic Usage

```bash
poetry run python main.py input.html -o output.html
```

### Output to stdout

```bash
poetry run python main.py input.html
```

### Show help

```bash
poetry run python main.py --help
```

## Features

- Converts CSS in style tags to inline styles
- Applies styles considering CSS specificity
- Preserves media queries
- Properly merges with existing inline styles

## Requirements

- Python 3.12+
- Poetry
- beautifulsoup4 4.12.3+

## License

MIT License

